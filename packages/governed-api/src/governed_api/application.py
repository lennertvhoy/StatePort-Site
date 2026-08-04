"""A deterministic request dispatcher for the first governed API slice."""

from __future__ import annotations

import hashlib
import json
import math
import secrets
from datetime import datetime, timezone
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

from statedd_core import (
    LifecycleError,
    MANIFEST_V2_FORMAT,
    build_state_ir,
    build_state_pack,
    load_template_manifest,
    compare_state_packs,
    materialize_instance,
    parse_yaml_text,
    detect_overrides,
    inspect_state_pack,
    plan_upgrade,
)
from template_validator.validator import validate_instance, validate_template
from approval_gate import ApprovalGate
from audit_log import AuditLog
from quota_engine import QuotaEngine, QuotaPolicy, UsageLedger, UsageSnapshot
from governed_api.identity import Identity, IdentityDirectory

try:
    from container_runner import ExecutionPlan, is_immutable_image_reference
    from governed_runner import (
        CONTAINER_ECHO_COMMAND,
        CONTAINER_JOB_PAYLOAD_FORMAT,
        InstanceLease,
        InstanceLeaseBusy,
        JobQueue,
        RunLedger,
        diff_snapshots,
        digest_snapshot,
        restore_snapshot,
        snapshot_files,
    )
    from runner import run_instance
except ModuleNotFoundError as exc:  # Keep the read-only API importable as a standalone package.
    if exc.name not in {"container_runner", "governed_runner", "runner"}:
        raise
    ExecutionPlan = None  # type: ignore[assignment]
    is_immutable_image_reference = None  # type: ignore[assignment]
    JobQueue = None  # type: ignore[assignment]
    RunLedger = None  # type: ignore[assignment]
    InstanceLease = InstanceLeaseBusy = None  # type: ignore[assignment]
    CONTAINER_ECHO_COMMAND = ()  # type: ignore[assignment]
    CONTAINER_JOB_PAYLOAD_FORMAT = ""  # type: ignore[assignment]
    diff_snapshots = digest_snapshot = restore_snapshot = snapshot_files = None  # type: ignore[assignment]
    run_instance = None  # type: ignore[assignment]


API_VERSION = "stateport.api/v1"
_JSON_HEADERS = {"content-type": "application/json; charset=utf-8"}


@dataclass(frozen=True)
class Response:
    """Transport-neutral API response."""

    status: int
    body: dict[str, Any]
    headers: dict[str, str]

    def json_bytes(self) -> bytes:
        return (json.dumps(self.body, ensure_ascii=False, sort_keys=True) + "\n").encode(
            "utf-8"
        )


class APIError(ValueError):
    """A safe client-facing error with an HTTP status."""

    def __init__(self, message: str, status: int = 400, code: str = "invalid_request"):
        super().__init__(message)
        self.status = status
        self.code = code


def _result_payload(result: Any) -> dict[str, Any]:
    return {
        "valid": bool(result.ok),
        "issues": [{"path": issue.path, "message": issue.message} for issue in result.issues],
    }


class GovernedAPI:
    """Dispatch JSON requests against a confined StatePort workspace.

    Read operations remain available without an identity. Mutation requests
    require an explicitly configured identity, a capability intersection, a
    quota decision, and a separately approved request. The loopback adapter is
    not an authentication system; callers must put a trusted identity source
    in front of it before exposing it beyond a local development boundary.
    """

    _MUTATION_CAPABILITIES = {"materialize-instance": "write_state"}

    def __init__(
        self,
        workspace: Path | str,
        *,
        identities: Mapping[str, Any] | None = None,
        operator_allowed_capabilities: Mapping[str, Any] | list[str] | tuple[str, ...] | set[str] | None = None,
        container_engine: str = "podman",
        runner_image: str = "stateport/runner:local",
    ):
        self.workspace = Path(workspace).resolve()
        if not self.workspace.is_dir():
            raise ValueError(f"workspace is not a directory: {workspace}")
        self.identities = IdentityDirectory(identities)
        if operator_allowed_capabilities is None:
            self.operator_allowed_capabilities: frozenset[str] = frozenset()
        elif isinstance(operator_allowed_capabilities, Mapping):
            values = operator_allowed_capabilities.get("capabilities", ())
            self.operator_allowed_capabilities = self._capability_values(values, "operatorAllowed")
        else:
            self.operator_allowed_capabilities = self._capability_values(
                operator_allowed_capabilities, "operatorAllowed"
            )
        if container_engine not in {"docker", "podman"}:
            raise ValueError("container_engine must be docker or podman")
        if (
            not isinstance(runner_image, str)
            or not runner_image.strip()
            or runner_image.startswith("-")
            or any(char.isspace() for char in runner_image)
        ):
            raise ValueError("runner_image must be a single non-empty image reference")
        self.container_engine = container_engine
        self.runner_image = runner_image
        operational = self.workspace / ".stateport"
        self.operational = operational
        if operational.exists() and (operational.is_symlink() or not operational.is_dir()):
            raise ValueError("workspace .stateport must be a real directory")
        for filename in (
            "approvals.json",
            "audit.jsonl",
            "runs.json",
            "jobs.sqlite3",
            "usage.sqlite3",
        ):
            candidate = operational / filename
            if candidate.is_symlink():
                raise ValueError(f"workspace .stateport/{filename} may not be a symlink")
        self.approvals = ApprovalGate(operational / "approvals.json")
        self.audit = AuditLog(operational / "audit.jsonl")
        run_ledger_path = operational / "runs.json"
        if run_ledger_path.is_symlink():
            raise ValueError("workspace .stateport/runs.json may not be a symlink")
        self.runs = RunLedger(run_ledger_path) if RunLedger is not None else None
        self._jobs: Any = None
        self._durable_usage: UsageLedger | None = None

    @property
    def _mutation_enabled(self) -> bool:
        return bool(self.operator_allowed_capabilities and self.identities.all())

    def _job_queue(self) -> Any:
        if JobQueue is None:
            raise APIError("job queue dependency is unavailable", 503, "queue_unavailable")
        if self._jobs is None:
            self._jobs = JobQueue(self.operational / "jobs.sqlite3")
        return self._jobs

    def _usage_ledger(self) -> UsageLedger:
        if self._durable_usage is None:
            self._durable_usage = UsageLedger(self.operational / "usage.sqlite3")
        return self._durable_usage

    def dispatch(
        self,
        method: str,
        path: str,
        body: Mapping[str, Any] | None = None,
    ) -> Response:
        """Return a structured response for one request.

        ``body`` must already be decoded JSON.  The method/path API keeps the
        contract usable by a CLI, an HTTP adapter, and future clients without
        coupling core policy to a web framework.
        """

        try:
            normalized_method = method.upper()
            normalized_path = path.split("?", 1)[0]
            payload = body if body is not None else {}
            if not isinstance(payload, Mapping):
                raise APIError("request body must be a JSON object")
            if normalized_method == "GET" and normalized_path == "/health":
                return self._ok(
                    {
                        "apiVersion": API_VERSION,
                        "service": "stateport",
                        "status": "ok",
                        "readOnly": not self._mutation_enabled,
                        "mutationMode": "approval-backed" if self._mutation_enabled else "disabled",
                    }
                )
            if normalized_method == "GET" and normalized_path == "/v1/capabilities":
                operations = [
                    "validate-template",
                    "validate-instance",
                    "inspect-overrides",
                    "plan-upgrade",
                    "context-build",
                    "context-inspect",
                    "context-compare",
                    "policy-check",
                    "quota-check",
                    "identity-check",
                    "list-approvals",
                    "inspect-usage",
                ]
                if self.runs is not None:
                    operations.extend(["plan-run", "execute-run", "list-runs", "inspect-run"])
                    if JobQueue is not None:
                        operations.extend(
                            [
                                "request-run-execution",
                                "enqueue-run",
                                "list-jobs",
                                "inspect-job",
                            ]
                        )
                return self._ok(
                    {
                        "apiVersion": API_VERSION,
                        "readOnly": not self._mutation_enabled,
                        "operations": operations,
                        "mutations": sorted(self._MUTATION_CAPABILITIES) if self._mutation_enabled else [],
                        "identity": {
                            "configured": bool(self.identities.all()),
                            "authentication": "external-required",
                        },
                    }
                )
            if normalized_method != "POST":
                raise APIError("method is not supported for this route", 405, "method_not_allowed")

            routes = {
                "/v1/validate/template": self._validate_template,
                "/v1/validate/instance": self._validate_instance,
                "/v1/lifecycle/overrides": self._inspect_overrides,
                "/v1/lifecycle/upgrade-plan": self._plan_upgrade,
                "/v1/context/build": self._context_build,
                "/v1/context/inspect": self._context_inspect,
                "/v1/context/compare": self._context_compare,
                "/v1/policy/check": self._policy_check,
                "/v1/quota/check": self._quota_check,
                "/v1/identity/check": self._identity_check,
                "/v1/mutations/request": self._request_mutation,
                "/v1/approvals/decide": self._decide_approval,
                "/v1/approvals/list": self._list_approvals,
                "/v1/mutations/apply": self._apply_mutation,
                "/v1/runs/plan": self._plan_run,
                "/v1/runs/execute": self._execute_run,
                "/v1/runs/list": self._list_runs,
                "/v1/runs/inspect": self._inspect_run,
                "/v1/runs/request-execution": self._request_run_execution,
                "/v1/runs/enqueue": self._enqueue_run,
                "/v1/jobs/list": self._list_jobs,
                "/v1/jobs/inspect": self._inspect_job,
                "/v1/usage/inspect": self._inspect_usage,
            }
            handler = routes.get(normalized_path)
            if handler is None:
                raise APIError("route was not found", 404, "not_found")
            return self._ok(handler(payload))
        except APIError as exc:
            return self._error(exc.status, exc.code, str(exc))
        except (LifecycleError, OSError, TypeError, ValueError) as exc:
            return self._error(400, "operation_failed", str(exc))
        except Exception:
            return self._error(500, "internal_error", "the operation failed")

    def _path(self, value: Any, field: str) -> Path:
        if not isinstance(value, str) or not value.strip():
            raise APIError(f"{field} must be a non-empty path")
        raw = Path(value)
        candidate = raw if raw.is_absolute() else self.workspace / raw
        try:
            relative_candidate = candidate.relative_to(self.workspace)
        except ValueError as exc:
            raise APIError(f"{field} must stay inside the API workspace", 403, "path_forbidden") from exc
        cursor = self.workspace
        for part in relative_candidate.parts:
            cursor = cursor / part
            if cursor.is_symlink():
                raise APIError(f"{field} may not traverse a symlink", 403, "path_forbidden")
        resolved = candidate.resolve()
        if not resolved.is_relative_to(self.workspace):
            raise APIError(f"{field} must stay inside the API workspace", 403, "path_forbidden")
        return resolved

    def _pack(self, value: Any, field: str) -> dict[str, Any]:
        if isinstance(value, Mapping):
            return dict(value)
        path = self._path(value, field)
        try:
            loaded = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise APIError(f"{field} could not be read as JSON: {exc}") from exc
        if not isinstance(loaded, Mapping):
            raise APIError(f"{field} must contain a JSON object")
        return dict(loaded)

    def _validate_template(self, body: Mapping[str, Any]) -> dict[str, Any]:
        return _result_payload(validate_template(self._path(body.get("path"), "path")))

    def _validate_instance(self, body: Mapping[str, Any]) -> dict[str, Any]:
        return _result_payload(validate_instance(self._path(body.get("path"), "path")))

    def _inspect_overrides(self, body: Mapping[str, Any]) -> dict[str, Any]:
        return detect_overrides(
            self._path(body.get("instancePath"), "instancePath"),
            self._path(body.get("templatePath"), "templatePath"),
        )

    def _plan_upgrade(self, body: Mapping[str, Any]) -> dict[str, Any]:
        return plan_upgrade(
            self._path(body.get("instancePath"), "instancePath"),
            self._path(body.get("templatePath"), "templatePath"),
        )

    def _context_build(self, body: Mapping[str, Any]) -> dict[str, Any]:
        ir = build_state_ir(
            self._path(body.get("instancePath"), "instancePath"),
            template_path=self._path(body["templatePath"], "templatePath")
            if body.get("templatePath") is not None
            else None,
            operator_allowed_sensitivities=body.get("operatorAllowedSensitivities"),
            instance_granted_sensitivities=body.get("instanceGrantedSensitivities"),
            template_sensitivities=body.get("templateSensitivities"),
        )
        pack = build_state_pack(
            ir,
            task=body.get("task"),
            model=body.get("model"),
            budget_tokens=body.get("budgetTokens"),
            profile=body.get("profile", "compact"),
            selection=body.get("selection", "eager"),
        )
        return pack.to_dict()

    def _context_inspect(self, body: Mapping[str, Any]) -> dict[str, Any]:
        return inspect_state_pack(self._pack(body.get("pack"), "pack"))

    def _context_compare(self, body: Mapping[str, Any]) -> dict[str, Any]:
        return compare_state_packs(
            self._pack(body.get("left"), "left"), self._pack(body.get("right"), "right")
        )

    def _policy_check(self, body: Mapping[str, Any]) -> dict[str, Any]:
        decision = self.approvals.capability(
            str(body.get("operation", "")),
            str(body.get("capability", "")),
            body.get("templateRequested", ()),
            body.get("instanceGranted", ()),
            body.get("operatorAllowed", ()),
        )
        return decision.to_dict()

    def _quota_check(self, body: Mapping[str, Any]) -> dict[str, Any]:
        policy = QuotaPolicy(
            runs_per_day=body.get("runsPerDay"),
            messages_per_day=body.get("messagesPerDay"),
            monthly_euro_estimate=body.get("monthlyEuroEstimate"),
        )
        usage = UsageSnapshot(
            runs_today=body.get("runsToday", 0),
            messages_today=body.get("messagesToday", 0),
            monthly_euro_estimate=body.get("monthlyEuroUsed", 0.0),
        )
        return QuotaEngine(policy).evaluate(
            usage,
            operation=str(body.get("operation", "run")),
            estimated_cost=body.get("estimatedCost", 0.0),
        ).to_dict()

    @staticmethod
    def _capability_values(value: Any, field: str) -> frozenset[str]:
        if not isinstance(value, (list, tuple, set, frozenset)):
            raise ValueError(f"{field} must be a collection of capability strings")
        result: set[str] = set()
        for item in value:
            if not isinstance(item, str) or not item.strip():
                raise ValueError(f"{field} contains an invalid capability")
            result.add(item.strip())
        return frozenset(result)

    @staticmethod
    def _estimated_cost(value: Any) -> float:
        if (
            isinstance(value, bool)
            or not isinstance(value, (int, float))
            or not math.isfinite(float(value))
            or value < 0
        ):
            raise APIError("estimatedCost must be finite and non-negative")
        return float(value)

    @staticmethod
    def _utc_now() -> str:
        return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")

    def _identity(self, body: Mapping[str, Any], *, instance_id: str | None = None, approver: bool = False, operator: bool = False) -> Identity:
        actor = body.get("actor")
        if actor is None and isinstance(body.get("identity"), Mapping):
            actor = body["identity"].get("id")
        identity = self.identities.get(actor)
        if identity is None:
            raise APIError("a configured identity is required", 401, "identity_required")
        if instance_id and not identity.can_access(instance_id):
            raise APIError("identity is not scoped to this instance", 403, "instance_forbidden")
        if approver and not identity.is_approver():
            raise APIError("identity may not approve requests", 403, "approval_forbidden")
        if operator and not identity.is_operator():
            raise APIError("identity may not apply mutations", 403, "mutation_forbidden")
        return identity

    def _identity_check(self, body: Mapping[str, Any]) -> dict[str, Any]:
        identity = self._identity(body)
        instance_id = body.get("instanceId")
        if instance_id is not None and (not isinstance(instance_id, str) or not instance_id.strip()):
            raise APIError("instanceId must be a non-empty string")
        if instance_id and not identity.can_access(instance_id):
            raise APIError("identity is not scoped to this instance", 403, "instance_forbidden")
        return {"valid": True, "identity": identity.to_dict(), "instanceId": instance_id}

    def _yaml_mapping(self, path: Path, field: str) -> dict[str, Any]:
        try:
            value = parse_yaml_text(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, ValueError) as exc:
            raise APIError(f"{field} could not be read: {exc}") from exc
        if not isinstance(value, dict):
            raise APIError(f"{field} must contain a YAML mapping")
        return value

    def _template_capabilities(self, template_path: Path) -> list[str]:
        manifest = load_template_manifest(template_path)
        if manifest.get("formatVersion") == MANIFEST_V2_FORMAT:
            return sorted(
                {
                    capability
                    for module in manifest.get("modules", [])
                    for capability in module.get("capabilities", [])
                }
            )
        data = self._yaml_mapping(template_path / "template.yaml", "template")
        spec = data.get("spec")
        if not isinstance(spec, Mapping):
            return []
        explicit = spec.get("requestedCapabilities", spec.get("capabilities"))
        if explicit is not None:
            return sorted(self._capability_values(explicit, "templateRequested"))
        actions = spec.get("allowedActions", ())
        if not isinstance(actions, list):
            return []
        return sorted(
            {item.get("name") for item in actions if isinstance(item, Mapping) and isinstance(item.get("name"), str) and item.get("name").strip()}
        )

    def _instance_capabilities(self, instance_path: Path) -> tuple[str, list[str]]:
        data = self._yaml_mapping(instance_path / "instance.yaml", "instance")
        metadata = data.get("metadata")
        spec = data.get("spec")
        if not isinstance(metadata, Mapping) or not isinstance(metadata.get("id"), str) or not metadata["id"].strip():
            raise APIError("instance metadata.id is required")
        if not isinstance(spec, Mapping):
            return metadata["id"], ""
        explicit = spec.get("grantedCapabilities", spec.get("allowedCapabilities", ()))
        return metadata["id"], sorted(self._capability_values(explicit, "instanceGranted"))

    def _template_quota(self, template_path: Path, instance_path: Path) -> QuotaPolicy:
        manifest = load_template_manifest(template_path)
        template = (
            {}
            if manifest.get("formatVersion") == MANIFEST_V2_FORMAT
            else self._yaml_mapping(template_path / "template.yaml", "template")
        )
        instance = self._yaml_mapping(instance_path / "instance.yaml", "instance")
        template_spec = template.get("spec") if isinstance(template.get("spec"), Mapping) else {}
        instance_spec = instance.get("spec") if isinstance(instance.get("spec"), Mapping) else {}
        raw = instance_spec.get("quotas") or template_spec.get("quotas") or {}
        if not isinstance(raw, Mapping):
            raise APIError("quota configuration must be a mapping")
        return QuotaPolicy(
            runs_per_day=raw.get("runsPerDay"),
            messages_per_day=raw.get("messagesPerDay"),
            monthly_euro_estimate=raw.get("monthlyEuroEstimate"),
        )

    @staticmethod
    def _operation_quota_policy(policy: QuotaPolicy, operation: str) -> QuotaPolicy:
        return QuotaPolicy(
            runs_per_day=policy.runs_per_day if operation == "run" else None,
            messages_per_day=policy.messages_per_day if operation == "message" else None,
            monthly_euro_estimate=policy.monthly_euro_estimate,
        )

    def _assert_instance_template(self, instance_path: Path, template_path: Path) -> None:
        """Ensure a caller cannot plan against a template different from the instance ref."""

        data = self._yaml_mapping(instance_path / "instance.yaml", "instance")
        spec = data.get("spec")
        reference = spec.get("templateRef") if isinstance(spec, Mapping) else None
        reference_path = reference.get("path") if isinstance(reference, Mapping) else None
        if not isinstance(reference_path, str) or not reference_path.strip():
            raise APIError("instance templateRef.path is required")
        resolved_reference = self._path((instance_path / reference_path).as_posix(), "instance templateRef.path")
        if resolved_reference != template_path:
            raise APIError("templatePath does not match the instance templateRef.path", 409, "template_mismatch")

    def _audit(self, event_type: str, actor: str, subject: str, data: dict[str, Any]) -> None:
        self.audit.append(event_type=event_type, actor=actor, subject=subject, timestamp=self._utc_now(), data=data)

    def _audit_once(
        self,
        event_type: str,
        actor: str,
        subject: str,
        data: dict[str, Any],
        *,
        correlation_keys: tuple[str, ...],
    ) -> None:
        self.audit.append_once(
            event_type=event_type,
            actor=actor,
            subject=subject,
            timestamp=self._utc_now(),
            data=data,
            correlation_keys=correlation_keys,
        )

    def _request_mutation(self, body: Mapping[str, Any]) -> dict[str, Any]:
        operation = body.get("operation")
        if operation not in self._MUTATION_CAPABILITIES:
            raise APIError("operation is not supported by this mutation boundary", 400, "unsupported_mutation")
        capability = self._MUTATION_CAPABILITIES[operation]
        instance_path = self._path(body.get("instancePath"), "instancePath")
        template_path = self._path(body.get("templatePath"), "templatePath")
        if not instance_path.is_dir() or not template_path.is_dir():
            raise APIError("instancePath and templatePath must be directories")
        self._assert_instance_template(instance_path, template_path)
        instance_id, instance_granted = self._instance_capabilities(instance_path)
        identity = self._identity(body, instance_id=instance_id)
        template_requested = self._template_capabilities(template_path)
        decision = self.approvals.capability(operation, capability, template_requested, instance_granted, self.operator_allowed_capabilities)
        if not decision.allowed:
            self._audit("mutation.denied", identity.id, instance_id, {"operation": operation, "reason": decision.reason})
            raise APIError("capability intersection denies mutation", 403, "capability_denied")
        estimated_cost = self._estimated_cost(body.get("estimatedCost", 0.0))
        policy = self._template_quota(template_path, instance_path)
        usage = self._usage_ledger().snapshot(instance_id)
        quota = QuotaEngine(self._operation_quota_policy(policy, "mutation")).evaluate(
            usage, operation="mutation", estimated_cost=estimated_cost
        )
        if not quota.allowed:
            self._audit("mutation.denied", identity.id, instance_id, {"operation": operation, "reason": quota.reason})
            raise APIError(quota.reason, 429, quota.code)
        request = self.approvals.request(
            operation=operation,
            capability=capability,
            instance_id=instance_id,
            actor=identity.id,
            instance_path=instance_path.as_posix(),
            reason=str(body.get("reason", "")),
            metadata={
                "templatePath": template_path.as_posix(),
                "templateRequested": template_requested,
                "instanceGranted": instance_granted,
                "operatorAllowed": sorted(self.operator_allowed_capabilities),
                "estimatedCost": estimated_cost,
            },
        )
        self._audit("mutation.requested", identity.id, instance_id, {"approvalId": request.id, "operation": operation})
        return {"approval": request.to_dict(), "policy": decision.to_dict(), "quota": quota.to_dict()}

    def _approval_for_body(self, body: Mapping[str, Any]):
        approval_id = body.get("approvalId")
        if not isinstance(approval_id, str) or not approval_id.strip():
            raise APIError("approvalId must be a non-empty string")
        request = self.approvals.get(approval_id)
        if request is None:
            raise APIError("approval request was not found", 404, "approval_not_found")
        return request

    def _decide_approval(self, body: Mapping[str, Any]) -> dict[str, Any]:
        request = self._approval_for_body(body)
        identity = self._identity(body, instance_id=request.instance_id, approver=True)
        if request.actor == identity.id and "admin" not in identity.roles:
            raise APIError("the requester may not approve their own request", 403, "self_approval_forbidden")
        status = body.get("status")
        if status not in {"approved", "rejected", "cancelled"}:
            raise APIError("status must be approved, rejected, or cancelled")
        try:
            updated = self.approvals.transition(request.id, status, str(body.get("reason", "")))
        except (KeyError, ValueError) as exc:
            raise APIError(str(exc), 409, "approval_transition_failed") from exc
        event_prefix = "run" if request.operation == "execute-run" else "mutation"
        self._audit(f"{event_prefix}.{status}", identity.id, request.instance_id, {"approvalId": request.id})
        return {"approval": updated.to_dict()}

    def _list_approvals(self, body: Mapping[str, Any]) -> dict[str, Any]:
        identity = self._identity(body)
        requests = [request.to_dict() for request in self.approvals.all() if identity.can_access(request.instance_id)]
        return {"approvals": requests}

    def _run_policy(self, template_path: Path, instance_path: Path, identity: Identity, *, estimated_cost: float = 0.0) -> tuple[dict[str, Any], dict[str, Any], Any]:
        instance_id, instance_granted = self._instance_capabilities(instance_path)
        template_requested = self._template_capabilities(template_path)
        decision = self.approvals.capability("run-instance", "read_state", template_requested, instance_granted, self.operator_allowed_capabilities)
        if not decision.allowed:
            self._audit("run.denied", identity.id, instance_id, {"reason": decision.reason})
            raise APIError("capability intersection denies run", 403, "capability_denied")
        quota_policy = self._template_quota(template_path, instance_path)
        usage = self._usage_ledger().snapshot(instance_id)
        quota = QuotaEngine(self._operation_quota_policy(quota_policy, "run")).evaluate(
            usage, operation="run", estimated_cost=estimated_cost
        )
        if not quota.allowed:
            self._audit("run.denied", identity.id, instance_id, {"reason": quota.reason})
            raise APIError(quota.reason, 429, quota.code)
        return decision.to_dict(), quota.to_dict(), instance_id

    def _plan_run(self, body: Mapping[str, Any]) -> dict[str, Any]:
        if self.runs is None or ExecutionPlan is None:
            raise APIError("governed runner dependencies are unavailable", 503, "runner_unavailable")
        mode = body.get("mode", "echo")
        if mode not in {"echo", "container_echo"}:
            raise APIError("mode must be echo or container_echo", 400, "unsupported_run_mode")
        estimated_cost = self._estimated_cost(body.get("estimatedCost", 0.0))
        instance_path = self._path(body.get("instancePath"), "instancePath")
        template_path = self._path(body.get("templatePath"), "templatePath")
        if not instance_path.is_dir() or not template_path.is_dir():
            raise APIError("instancePath and templatePath must be directories")
        self._assert_instance_template(instance_path, template_path)
        instance_id, _ = self._instance_capabilities(instance_path)
        identity = self._identity(body, instance_id=instance_id)
        policy, quota, _ = self._run_policy(
            template_path,
            instance_path,
            identity,
            estimated_cost=estimated_cost,
        )
        # The runtime path is a plan-only path. No runtime directory or process
        # is created by this contract.
        run_id_preview = "run:" + secrets.token_hex(12)
        execution_plan = ExecutionPlan(
            template_path.as_posix(),
            instance_path.as_posix(),
            (self.workspace / ".stateport" / "runtime" / run_id_preview).as_posix(),
            run_id_preview,
        ).to_dict()
        record = self.runs.create(
            actor=identity.id,
            instance_id=instance_id,
            instance_path=instance_path.as_posix(),
            template_path=template_path.as_posix(),
            capability="read_state",
            policy=policy,
            quota=quota,
            execution_plan=execution_plan,
            estimated_cost=estimated_cost,
            run_id=run_id_preview,
            mode=mode,
            command=list(CONTAINER_ECHO_COMMAND) if mode == "container_echo" else None,
            container_engine=self.container_engine if mode == "container_echo" else None,
            runner_image=self.runner_image if mode == "container_echo" else None,
        )
        self._audit("run.planned", identity.id, instance_id, {"runId": record["runId"], "mode": mode})
        return {
            "run": record,
            "approvalRequired": mode == "container_echo",
            "mode": mode,
        }

    def _run_for_body(self, body: Mapping[str, Any]) -> dict[str, Any]:
        if self.runs is None:
            raise APIError("governed runner dependencies are unavailable", 503, "runner_unavailable")
        run_id = body.get("runId")
        if not isinstance(run_id, str) or not run_id.strip():
            raise APIError("runId must be a non-empty string")
        record = self.runs.get(run_id)
        if record is None:
            raise APIError("run was not found", 404, "run_not_found")
        return record

    def _execute_run(self, body: Mapping[str, Any]) -> dict[str, Any]:
        if self.runs is None or run_instance is None or snapshot_files is None or diff_snapshots is None or restore_snapshot is None:
            raise APIError("governed runner dependencies are unavailable", 503, "runner_unavailable")
        record = self._run_for_body(body)
        identity = self._identity(body, instance_id=record["instanceId"])
        if record.get("mode", "echo") != "echo":
            raise APIError(
                "container runs must use approval-bound queue execution",
                409,
                "queue_required",
            )
        if record["status"] == "completed":
            return {"run": record, "idempotent": True}
        if record["status"] != "planned":
            raise APIError("run is not executable in its current state", 409, "run_transition_failed")
        instance_path = self._path(record["instancePath"], "instancePath")
        template_path = self._path(record["templatePath"], "templatePath")
        self._assert_instance_template(instance_path, template_path)
        if InstanceLease is None or InstanceLeaseBusy is None:
            raise APIError("instance lease dependency is unavailable", 503, "lease_unavailable")
        try:
            with InstanceLease(
                self.operational / "leases",
                instance_path,
                owner=f"api-run:{identity.id}",
            ):
                return self._execute_run_locked(
                    record,
                    identity,
                    instance_path,
                    template_path,
                )
        except InstanceLeaseBusy as exc:
            raise APIError(
                "instance currently has an active writer lease",
                409,
                "instance_busy",
            ) from exc

    def _execute_run_locked(
        self,
        record: dict[str, Any],
        identity: Identity,
        instance_path: Path,
        template_path: Path,
    ) -> dict[str, Any]:
        """Execute deterministic echo mode under the system writer lease."""

        policy, quota, instance_id = self._run_policy(
            template_path,
            instance_path,
            identity,
            estimated_cost=self._estimated_cost(record.get("estimatedCost", 0.0)),
        )
        if policy.get("effectiveCapabilities") != record["policy"].get("effectiveCapabilities"):
            raise APIError("run policy changed since planning", 409, "policy_changed")
        reservation_id = f"usage:{record['runId']}"
        reservation = self._usage_ledger().reserve(
            reservation_id,
            instance_id,
            "run",
            self._template_quota(template_path, instance_path),
            estimated_cost=self._estimated_cost(record.get("estimatedCost", 0.0)),
        )
        if not reservation.allowed:
            raise APIError(
                reservation.decision.reason,
                429,
                reservation.decision.code,
            )
        before = snapshot_files(instance_path)
        self.runs.update(record["runId"], status="running")
        try:
            result = run_instance(instance_path)
            after = snapshot_files(instance_path)
            state_diff = diff_snapshots(before, after)
            restoration_diff = None
            integrity = "preserved"
            errors = list(result.errors)
            if state_diff["filesChanged"]:
                restore_snapshot(instance_path, before)
                restored = snapshot_files(instance_path)
                restoration_diff = diff_snapshots(before, restored)
                integrity = "restored_unexpected_write"
                errors.append("runner changed canonical instance files")
            outcome = {
                "ok": not errors and integrity == "preserved",
                "status": result.status,
                "logs": list(result.logs),
                "errors": errors,
                "filesRead": sorted(before),
                "filesChanged": list(state_diff["filesChanged"]),
                "stateDiff": state_diff,
                "restorationDiff": restoration_diff,
                "stateIntegrity": integrity,
            }
            final_status = "completed" if outcome["ok"] else "failed"
            updated = self.runs.update(record["runId"], status=final_status, outcome=outcome, policy=policy, quota=quota)
            self._usage_ledger().commit(reservation_id, actual_cost=0.0)
            self._audit("run.completed" if outcome["ok"] else "run.failed", identity.id, instance_id, {"runId": record["runId"], "stateIntegrity": integrity})
            return {"run": updated, "idempotent": False}
        except Exception as exc:
            try:
                self._usage_ledger().commit(reservation_id, actual_cost=0.0)
            except ValueError:
                pass
            try:
                failed = self.runs.update(record["runId"], status="failed", outcome={"ok": False, "errors": [str(exc)], "stateIntegrity": "unknown"})
            except (KeyError, ValueError):
                failed = record
            self._audit("run.failed", identity.id, instance_id, {"runId": record["runId"], "reason": str(exc)})
            if isinstance(exc, APIError):
                raise
            return {"run": failed, "idempotent": False}

    def _list_runs(self, body: Mapping[str, Any]) -> dict[str, Any]:
        if self.runs is None:
            raise APIError("governed runner dependencies are unavailable", 503, "runner_unavailable")
        identity = self._identity(body)
        return {"runs": [record for record in self.runs.all() if identity.can_access(record.get("instanceId", ""))]}

    def _inspect_run(self, body: Mapping[str, Any]) -> dict[str, Any]:
        record = self._run_for_body(body)
        self._identity(body, instance_id=record["instanceId"])
        return {"run": record}

    @staticmethod
    def _canonical_digest(value: Mapping[str, Any]) -> str:
        try:
            encoded = json.dumps(
                dict(value),
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
                allow_nan=False,
            ).encode("utf-8")
        except (TypeError, ValueError) as exc:
            raise APIError("execution plan is not canonical JSON") from exc
        return "sha256:" + hashlib.sha256(encoded).hexdigest()

    def _run_execution_policy(
        self,
        template_path: Path,
        instance_path: Path,
        identity: Identity,
        *,
        estimated_cost: float,
    ) -> tuple[dict[str, Any], dict[str, Any], str]:
        instance_id, instance_granted = self._instance_capabilities(instance_path)
        if not identity.can_access(instance_id):
            raise APIError("identity is not scoped to this instance", 403, "instance_forbidden")
        template_requested = self._template_capabilities(template_path)
        decision = self.approvals.capability(
            "execute-run",
            "execute_container",
            template_requested,
            instance_granted,
            self.operator_allowed_capabilities,
        )
        if not decision.allowed:
            self._audit("run.execution_denied", identity.id, instance_id, {"reason": decision.reason})
            raise APIError(
                "capability intersection denies container execution",
                403,
                "capability_denied",
            )
        policy = self._template_quota(template_path, instance_path)
        usage = self._usage_ledger().snapshot(instance_id)
        quota = QuotaEngine(self._operation_quota_policy(policy, "run")).evaluate(
            usage,
            operation="run",
            estimated_cost=estimated_cost,
        )
        if not quota.allowed:
            self._audit("run.execution_denied", identity.id, instance_id, {"reason": quota.reason})
            raise APIError(quota.reason, 429, quota.code)
        return decision.to_dict(), quota.to_dict(), instance_id

    def _request_run_execution(self, body: Mapping[str, Any]) -> dict[str, Any]:
        if self.runs is None or JobQueue is None or snapshot_files is None or digest_snapshot is None:
            raise APIError("job queue dependency is unavailable", 503, "queue_unavailable")
        record = self._run_for_body(body)
        identity = self._identity(body, instance_id=record["instanceId"])
        if identity.id != record.get("actor"):
            raise APIError("only the run actor may request execution", 403, "run_actor_required")
        if record.get("mode") != "container_echo":
            raise APIError("only container_echo runs require execution approval", 409, "approval_not_required")
        if (
            is_immutable_image_reference is None
            or not is_immutable_image_reference(record.get("runnerImage"))
        ):
            raise APIError(
                "container execution requires an immutable sha256 runner image",
                409,
                "runner_image_untrusted",
            )
        if record.get("status") != "planned":
            raise APIError("run is not awaiting execution approval", 409, "run_transition_failed")
        instance_path = self._path(record.get("instancePath"), "instancePath")
        template_path = self._path(record.get("templatePath"), "templatePath")
        self._assert_instance_template(instance_path, template_path)
        estimated_cost = self._estimated_cost(record.get("estimatedCost", 0.0))
        policy, quota, instance_id = self._run_execution_policy(
            template_path,
            instance_path,
            identity,
            estimated_cost=estimated_cost,
        )
        plan = record.get("executionPlan")
        if not isinstance(plan, Mapping):
            raise APIError("run execution plan is invalid", 409, "plan_changed")
        plan_digest = self._canonical_digest(plan)
        template_digest = digest_snapshot(snapshot_files(template_path))
        command = list(record.get("command", ()))
        if tuple(command) != tuple(CONTAINER_ECHO_COMMAND):
            raise APIError("run command is not the fixed container echo command", 409, "command_changed")
        approval_id = hashlib.sha256(
            f"execute-run\0{record['runId']}".encode("utf-8")
        ).hexdigest()[:24]
        approval_metadata = {
                "runId": record["runId"],
                "executionPlanDigest": plan_digest,
                "templateDigest": template_digest,
                "containerEngine": record.get("containerEngine"),
                "runnerImage": record.get("runnerImage"),
                "command": command,
                "estimatedCost": estimated_cost,
                "policy": policy,
            }
        try:
            approval, idempotent = self.approvals.request_once(
                approval_id,
                operation="execute-run",
                capability="execute_container",
                instance_id=instance_id,
                actor=identity.id,
                instance_path=instance_path.as_posix(),
                reason=str(body.get("reason", "")),
                metadata=approval_metadata,
            )
        except ValueError as exc:
            raise APIError(
                "run execution request changed after its approval identity was bound",
                409,
                "approval_binding_changed",
            ) from exc
        if not idempotent:
            self._audit(
                "run.execution_requested",
                identity.id,
                instance_id,
                {"runId": record["runId"], "approvalId": approval.id},
            )
        return {
            "approval": approval.to_dict(),
            "policy": policy,
            "quota": quota,
            "idempotent": idempotent,
        }

    def _enqueue_run(self, body: Mapping[str, Any]) -> dict[str, Any]:
        if self.runs is None or JobQueue is None or snapshot_files is None or digest_snapshot is None:
            raise APIError("job queue dependency is unavailable", 503, "queue_unavailable")
        approval = self._approval_for_body(body)
        if approval.operation != "execute-run" or approval.capability != "execute_container":
            raise APIError("approval is not a container run approval", 409, "approval_mismatch")
        identity = self._identity(body, instance_id=approval.instance_id, operator=True)
        if approval.status != "approved":
            raise APIError("run enqueue requires an approved request", 409, "approval_required")
        run_id = approval.metadata.get("runId")
        record = self.runs.get(run_id)
        if record is None:
            raise APIError("approved run was not found", 404, "run_not_found")
        if record.get("actor") != approval.actor or record.get("instanceId") != approval.instance_id:
            raise APIError("approval identity does not match the run", 409, "approval_mismatch")
        if record.get("mode") != "container_echo":
            raise APIError("approved run is not a container_echo run", 409, "approval_mismatch")
        if (
            record.get("containerEngine") != self.container_engine
            or record.get("runnerImage") != self.runner_image
        ):
            raise APIError("executor configuration changed since run planning", 409, "executor_changed")
        queue = self._job_queue()
        job_id = f"job:{approval.id}"
        if record.get("status") == "queued":
            if record.get("jobId") != job_id:
                raise APIError("run is bound to a different job", 409, "job_binding_changed")
            existing = queue.get(job_id)
            if existing is not None:
                self._audit_once(
                    "job.enqueued",
                    identity.id,
                    approval.instance_id,
                    {
                        "jobId": job_id,
                        "runId": record["runId"],
                        "approvalId": approval.id,
                    },
                    correlation_keys=("jobId", "runId"),
                )
                return {"job": self._public_job(existing), "run": record, "idempotent": True}
        elif record.get("status") != "planned":
            raise APIError("run is not enqueueable in its current state", 409, "run_transition_failed")
        instance_path = self._path(record.get("instancePath"), "instancePath")
        template_path = self._path(record.get("templatePath"), "templatePath")
        self._assert_instance_template(instance_path, template_path)
        estimated_cost = self._estimated_cost(record.get("estimatedCost", 0.0))
        current_policy, current_quota, instance_id = self._run_execution_policy(
            template_path,
            instance_path,
            identity,
            estimated_cost=estimated_cost,
        )
        plan = record.get("executionPlan")
        if not isinstance(plan, Mapping):
            raise APIError("run execution plan is invalid", 409, "plan_changed")
        plan_digest = self._canonical_digest(plan)
        template_digest = digest_snapshot(snapshot_files(template_path))
        command = list(record.get("command", ()))
        if (
            approval.metadata.get("executionPlanDigest") != plan_digest
            or approval.metadata.get("templateDigest") != template_digest
            or approval.metadata.get("containerEngine") != self.container_engine
            or approval.metadata.get("runnerImage") != self.runner_image
            or tuple(approval.metadata.get("command", ())) != tuple(command)
            or tuple(command) != tuple(CONTAINER_ECHO_COMMAND)
        ):
            raise APIError("run plan changed since approval", 409, "plan_changed")
        reservation_id = f"usage:{job_id}"
        usage = self._usage_ledger().reserve(
            reservation_id,
            instance_id,
            "run",
            self._template_quota(template_path, instance_path),
            estimated_cost=estimated_cost,
        )
        if not usage.allowed:
            self._audit("job.denied", identity.id, instance_id, {"reason": usage.decision.reason})
            raise APIError(usage.decision.reason, 429, usage.decision.code)
        payload = {
            "formatVersion": CONTAINER_JOB_PAYLOAD_FORMAT,
            "jobType": "container_echo",
            "runId": record["runId"],
            "approvalId": approval.id,
            "actor": record["actor"],
            "instanceId": instance_id,
            "executionPlan": dict(plan),
            "executionPlanDigest": plan_digest,
            "templateDigest": template_digest,
            "containerEngine": self.container_engine,
            "runnerImage": self.runner_image,
            "command": command,
            "usageReservationId": reservation_id,
        }
        updated_run = record
        enqueue_idempotent = record.get("status") == "queued"
        if record.get("status") == "planned":
            try:
                updated_run = self.runs.update(
                    record["runId"],
                    status="queued",
                    jobId=job_id,
                    approvalId=approval.id,
                    executionPolicy=current_policy,
                    quota=current_quota,
                    templateDigest=template_digest,
                )
            except ValueError as exc:
                refreshed = self.runs.get(record["runId"])
                if (
                    refreshed is None
                    or refreshed.get("status") != "queued"
                    or refreshed.get("jobId") != job_id
                    or refreshed.get("approvalId") != approval.id
                    or refreshed.get("templateDigest") != template_digest
                ):
                    if not usage.idempotent:
                        try:
                            self._usage_ledger().release(reservation_id)
                        except ValueError:
                            pass
                    raise APIError(
                        "run binding changed during enqueue",
                        409,
                        "job_binding_changed",
                    ) from exc
                updated_run = refreshed
                enqueue_idempotent = True
        self.approvals.mark_executed(
            approval.id,
            metadata={
                "execution": {
                    "enqueued": True,
                    "jobId": job_id,
                    "actor": identity.id,
                    "at": self._utc_now(),
                }
            },
        )
        try:
            job = queue.enqueue(
                idempotency_key=approval.id,
                payload=payload,
                job_id=job_id,
            )
        except Exception:
            # The durable reservation and queued run binding are intentionally
            # retained. A retry can idempotently publish the same immutable job;
            # releasing the reservation would make the fixed reservation id
            # permanently unusable and could bypass the original quota decision.
            raise
        self._audit_once(
            "job.enqueued",
            identity.id,
            instance_id,
            {"jobId": job_id, "runId": record["runId"], "approvalId": approval.id},
            correlation_keys=("jobId", "runId"),
        )
        return {
            "job": self._public_job(job),
            "run": updated_run,
            "idempotent": enqueue_idempotent,
        }

    @staticmethod
    def _public_job(job: Mapping[str, Any]) -> dict[str, Any]:
        result = dict(job)
        lease = result.get("lease")
        if isinstance(lease, Mapping):
            public_lease = dict(lease)
            public_lease.pop("token", None)
            result["lease"] = public_lease
        return result

    def _job_for_body(self, body: Mapping[str, Any]) -> dict[str, Any]:
        job_id = body.get("jobId")
        if not isinstance(job_id, str) or not job_id.strip():
            raise APIError("jobId must be a non-empty string")
        job = self._job_queue().get(job_id)
        if job is None:
            raise APIError("job was not found", 404, "job_not_found")
        return job

    def _list_jobs(self, body: Mapping[str, Any]) -> dict[str, Any]:
        identity = self._identity(body)
        status = body.get("status")
        jobs = []
        for job in self._job_queue().list(status=status):
            payload = job.get("payload")
            if isinstance(payload, Mapping) and identity.can_access(str(payload.get("instanceId", ""))):
                jobs.append(self._public_job(job))
        return {"jobs": jobs}

    def _inspect_job(self, body: Mapping[str, Any]) -> dict[str, Any]:
        job = self._job_for_body(body)
        payload = job.get("payload")
        instance_id = payload.get("instanceId") if isinstance(payload, Mapping) else None
        if not isinstance(instance_id, str):
            raise APIError("job instance binding is invalid", 409, "job_binding_invalid")
        self._identity(body, instance_id=instance_id)
        return {"job": self._public_job(job)}

    def _inspect_usage(self, body: Mapping[str, Any]) -> dict[str, Any]:
        instance_id = body.get("instanceId")
        if not isinstance(instance_id, str) or not instance_id.strip():
            raise APIError("instanceId must be a non-empty string")
        self._identity(body, instance_id=instance_id)
        snapshot = self._usage_ledger().snapshot(instance_id)
        return {
            "subjectId": instance_id,
            "usage": snapshot.__dict__.copy(),
            "costSemantics": "quota estimate or observed cost; not billing",
        }

    @staticmethod
    def _snapshot(root: Path) -> dict[str, bytes]:
        if not root.exists():
            return {}
        snapshot: dict[str, bytes] = {}
        for item in root.rglob("*"):
            if item.is_symlink():
                raise APIError("mutation target contains a symlink", 403, "path_forbidden")
            if item.is_file():
                snapshot[item.relative_to(root).as_posix()] = item.read_bytes()
        return snapshot

    @staticmethod
    def _restore(root: Path, snapshot: dict[str, bytes]) -> None:
        if not root.exists():
            return
        for item in sorted(root.rglob("*"), reverse=True):
            if item.is_symlink():
                item.unlink()
            elif item.is_file() and item.relative_to(root).as_posix() not in snapshot:
                item.unlink()
        for relative, content in snapshot.items():
            target = root / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(content)

    def _apply_mutation(self, body: Mapping[str, Any]) -> dict[str, Any]:
        if InstanceLease is None or InstanceLeaseBusy is None:
            raise APIError("instance lease dependency is unavailable", 503, "lease_unavailable")
        request = self._approval_for_body(body)
        identity = self._identity(body, instance_id=request.instance_id, operator=True)
        if request.status != "approved":
            raise APIError("mutation requires an approved request", 409, "approval_required")
        if request.metadata.get("execution", {}).get("applied"):
            return {"applied": True, "idempotent": True, "approval": request.to_dict()}
        template_path = self._path(request.metadata.get("templatePath"), "templatePath")
        instance_path = self._path(request.instance_path, "instancePath")
        try:
            with InstanceLease(
                self.operational / "leases",
                instance_path,
                owner=f"api:{identity.id}",
            ):
                return self._apply_mutation_locked(
                    request,
                    identity,
                    template_path,
                    instance_path,
                )
        except InstanceLeaseBusy as exc:
            raise APIError(
                "instance currently has an active writer lease",
                409,
                "instance_busy",
            ) from exc

    def _apply_mutation_locked(
        self,
        request: Any,
        identity: Identity,
        template_path: Path,
        instance_path: Path,
    ) -> dict[str, Any]:
        """Apply one approved mutation while holding the system writer lease."""

        current_id, current_grants = self._instance_capabilities(instance_path)
        current_requested = self._template_capabilities(template_path)
        decision = self.approvals.capability(request.operation, request.capability, current_requested, current_grants, self.operator_allowed_capabilities)
        if current_id != request.instance_id or not decision.allowed:
            raise APIError("mutation policy changed since approval", 409, "policy_changed")
        estimated_cost = self._estimated_cost(request.metadata.get("estimatedCost", 0.0))
        reservation_id = f"usage:mutation:{request.id}"
        reservation = self._usage_ledger().reserve(
            reservation_id,
            request.instance_id,
            "mutation",
            self._template_quota(template_path, instance_path),
            estimated_cost=estimated_cost,
        )
        if not reservation.allowed:
            raise APIError(
                reservation.decision.reason,
                429,
                reservation.decision.code,
            )
        snapshot = self._snapshot(instance_path)
        self._audit("mutation.started", identity.id, request.instance_id, {"approvalId": request.id, "operation": request.operation})
        try:
            if request.operation != "materialize-instance":
                raise APIError("operation is not supported by this mutation boundary", 400, "unsupported_mutation")
            lock = materialize_instance(template_path, instance_path)
            validation = _result_payload(validate_instance(instance_path))
            if not validation["valid"]:
                self._restore(instance_path, snapshot)
                self._audit("mutation.rolled_back", identity.id, request.instance_id, {"approvalId": request.id, "reason": "post-mutation validation failed"})
                raise APIError("post-mutation validation failed", 409, "validation_failed")
        except Exception:
            if instance_path.exists():
                self._restore(instance_path, snapshot)
            try:
                self._usage_ledger().commit(
                    reservation_id,
                    actual_cost=estimated_cost,
                )
            except ValueError:
                pass
            raise
        updated = self.approvals.mark_executed(request.id, metadata={"execution": {"applied": True, "actor": identity.id, "at": self._utc_now()}})
        self._usage_ledger().commit(
            reservation_id,
            actual_cost=estimated_cost,
        )
        self._audit("mutation.applied", identity.id, request.instance_id, {"approvalId": request.id, "files": len(lock.get("files", []))})
        return {"applied": True, "idempotent": False, "approval": updated.to_dict(), "lock": lock, "validation": validation}

    @staticmethod
    def _ok(body: dict[str, Any]) -> Response:
        return Response(200, {"ok": True, "result": body}, dict(_JSON_HEADERS))

    @staticmethod
    def _error(status: int, code: str, message: str) -> Response:
        return Response(
            status,
            {"ok": False, "error": {"code": code, "message": message}},
            dict(_JSON_HEADERS),
        )


__all__ = ["API_VERSION", "GovernedAPI", "Response"]
