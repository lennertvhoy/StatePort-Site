from __future__ import annotations

import json
import math
import os
from pathlib import Path
import re
import secrets
import signal
import shutil
import shlex
import stat
import subprocess
import sys
import threading
import time
from datetime import datetime, timezone
from typing import Any

import yaml

from execution_host.contracts import AgentRunSpec, BackendCapabilities, CapabilityRequest, TERMINATION_CLASSIFICATIONS, negotiate, validate_run_result
from codex_adapter import CodexAdapter
from external_engine_runtime import ProcessIdentity, ProcessResult, ProcessRuntimeError, ProcessSpec, TemporaryWorkspace, decode_jsonl, filtered_environment, probe_executable, run_process
from run_bundle import RunBundleWriter
from run_bundle import verify_bundle
from stateport_persistent_app import initialize_instance_repository
try:
    from governed_runner import (
        InstanceLease,
        InstanceLeaseError,
        diff_snapshots,
        digest_snapshot,
        restore_snapshot,
        snapshot_files,
    )
except ModuleNotFoundError:  # Source-tree consumers may not pre-install sibling packages.
    governed_src = Path(__file__).resolve().parents[4] / "packages" / "governed-runner" / "src"
    if governed_src.is_dir():
        sys.path.insert(0, str(governed_src))
    from governed_runner import (
        InstanceLease,
        InstanceLeaseError,
        diff_snapshots,
        digest_snapshot,
        restore_snapshot,
        snapshot_files,
    )

try:
    from sandbox_runtime import SandboxBoundary, SandboxPolicy
except ModuleNotFoundError:  # Source-tree consumers may not pre-install sibling packages.
    sandbox_src = Path(__file__).resolve().parents[4] / "packages" / "sandbox-runtime" / "src"
    if sandbox_src.is_dir():
        sys.path.insert(0, str(sandbox_src))
    from sandbox_runtime import SandboxBoundary, SandboxPolicy

from .context import compile_context
from .contracts import (
    RUN_FORMAT,
    ActionContract,
    ApplicationDescriptor,
    EngineProfile,
    digest,
)
from .portability import export_portable, import_portable, inspect_portable
from .registry import discover_application_descriptors
from .store import RunStore


class PortableExecutionError(ValueError):
    pass


class PortableImportError(PortableExecutionError):
    """A portable-import refusal with a stable, public classification code."""

    def __init__(self, code: str, message: str):
        self.code = code
        super().__init__(message)


class EnvironmentGatedExecution(PortableExecutionError):
    """A durable preparation result that cannot be executed in this host."""

    def __init__(self, payload: dict[str, Any]):
        self.payload = payload
        super().__init__(json.dumps({"code": "capability_negotiation_failed", **payload}, sort_keys=True))


class WorkerExecutionError(PortableExecutionError):
    """A worker termination with only the safe, durable observation attached."""

    def __init__(self, classification: str, process: dict[str, Any], message: str):
        if classification not in TERMINATION_CLASSIFICATIONS - {"success"}:
            raise ValueError("worker termination classification is invalid")
        self.classification = classification
        self.process = process
        super().__init__(message)


def _is_development_candidate_gate(exc: BaseException) -> bool:
    """True when an action-list failure is the deliberate candidate gate.

    An instance locked to an unresolved development candidate is intentionally
    not auto-resolved for normal action listing; the prepare/execute gates stay
    authoritative. This recognises that specific refusal through the exception
    chain so listing can report an honest empty result instead of a hard failure.
    """
    cursor: BaseException | None = exc
    seen = 0
    while cursor is not None and seen < 8:
        if "development candidate" in str(cursor):
            return True
        cursor = cursor.__cause__ or cursor.__context__
        seen += 1
    return False


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


_CAPABILITY_NAMES = (
    "structuredEvents", "nonInteractiveExecution", "cancellation", "sessionResume",
    "repositoryInstructions", "customTools", "mcpEquivalent", "approvalIntegration",
    "sandboxSupport", "changedFileReporting", "tokenTelemetry", "costTelemetry",
)
_MAX_BROWSER_FIXTURE_ENTRIES = 4096
_MAX_BROWSER_FIXTURE_BYTES = 64 * 1024 * 1024
_PUBLIC_MATRIX_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$")
_PUBLIC_MATRIX_DIGEST = re.compile(r"^sha256:[0-9a-f]{64}$")
_RUN_CLOSURE_RECEIPT_FORMAT = "stateport.governed-run-closure-receipt/v1"
_RUN_CLOSURE_RECEIPT_ID = re.compile(r"^governed-run\.run-[0-9a-f]{20}\.[0-9a-f]{12}$")
_RUN_CLOSURE_TIMESTAMP = re.compile(
    r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$"
)


def _public_matrix_id(value: object, label: str) -> str:
    if not isinstance(value, str) or _PUBLIC_MATRIX_ID.fullmatch(value) is None:
        raise PortableExecutionError(f"StateBench {label} is not safe for browser projection")
    return value


def _public_capability_degradations(value: object) -> list[dict[str, str]]:
    """Project only bounded degradation codes; discard producer prose/paths."""

    if not isinstance(value, list) or len(value) > 64:
        raise PortableExecutionError("StateBench capability degradations are malformed")
    projected: list[dict[str, str]] = []
    for item in value:
        if isinstance(item, str):
            projected.append({"id": _public_matrix_id(item, "degradation identity")})
            continue
        if not isinstance(item, dict):
            raise PortableExecutionError("StateBench capability degradation is malformed")
        identity = item.get("id", item.get("capability"))
        result = {"id": _public_matrix_id(identity, "degradation identity")}
        status = item.get("status")
        if status is not None:
            result["status"] = _public_matrix_id(status, "degradation status")
        projected.append(result)
    return projected


def _public_statebench_row(row: dict[str, Any]) -> dict[str, Any]:
    """Apply a closed output schema to an untrusted producer evidence row."""

    bundle_digest = row.get("bundleDigest")
    if not isinstance(bundle_digest, str) or _PUBLIC_MATRIX_DIGEST.fullmatch(bundle_digest) is None:
        raise PortableExecutionError("StateBench bundle digest is malformed")
    for label in ("statePreserved", "acceptedRun"):
        if not isinstance(row.get(label), bool):
            raise PortableExecutionError(f"StateBench {label} is malformed")
    usage_available = row.get("usageAvailable")
    if usage_available is not None and not isinstance(usage_available, bool):
        raise PortableExecutionError("StateBench usage availability is malformed")
    latency = row.get("latencyMs")
    if latency is not None and (
        isinstance(latency, bool)
        or not isinstance(latency, (int, float))
        or not math.isfinite(latency)
        or latency < 0
        or latency > 86_400_000
    ):
        raise PortableExecutionError("StateBench latency is malformed")
    unauthorized = row.get("unauthorizedMutations")
    file_count = row.get("bundleFileCount")
    if (
        isinstance(unauthorized, bool)
        or not isinstance(unauthorized, int)
        or unauthorized < 0
        or unauthorized > 1_000_000
        or isinstance(file_count, bool)
        or not isinstance(file_count, int)
        or not 0 <= file_count <= 1024
    ):
        raise PortableExecutionError("StateBench bounded counters are malformed")
    return {
        "formatVersion": "statebench.run-bundle-row/v1",
        "integrityStatus": "verified",
        "authoritative": False,
        "producerClaimsTrusted": False,
        "bundleDigest": bundle_digest,
        "runId": _public_matrix_id(row.get("runId"), "run identity"),
        "applicationId": _public_matrix_id(row.get("applicationId"), "application identity"),
        "engineId": _public_matrix_id(row.get("engineId"), "engine identity"),
        "adapterId": _public_matrix_id(row.get("adapterId"), "adapter identity"),
        "status": _public_matrix_id(row.get("status"), "run status"),
        "statePreserved": row["statePreserved"],
        "capabilityDegradations": _public_capability_degradations(row.get("capabilityDegradations")),
        "acceptedRun": row["acceptedRun"],
        "usageAvailable": usage_available,
        "latencyMs": latency,
        "unauthorizedMutations": unauthorized,
        "bundleFileCount": file_count,
    }


def _caps(**overrides: str) -> dict[str, str]:
    result = {name: "unsupported" for name in _CAPABILITY_NAMES}
    result.update(overrides)
    return result


def _optional_engine_profile(engine_id: str, executable: str, adapter_id: str) -> EngineProfile:
    """Probe only executable metadata; never inspect credentials or claim equivalence."""

    resolved = probe_executable(executable)
    if resolved is None:
        return EngineProfile(engine_id, adapter_id, "unavailable", "unavailable", "unavailable", "subscription_or_operator", _caps(), "unknown", False, (f"{executable} is not installed; no live execution performed.",))
    try:
        result = run_process(ProcessSpec((resolved, "--version"), Path.cwd(), timeout_seconds=5, max_output_bytes=16 * 1024, environment=filtered_environment()))
        version = (result.stdout or result.stderr).strip().splitlines()[0][:128] if (result.stdout or result.stderr).strip() else "unknown"
    except Exception:  # noqa: BLE001 - availability observation is fail-closed
        version = "unknown"
    return EngineProfile(engine_id, adapter_id, version, "environment_gated", version, "subscription_or_operator", _caps(), "unknown", False, ("Executable is present but automation and authentication routes were not verified; no live smoke performed.",))


def engine_profiles() -> list[EngineProfile]:
    codex = CodexAdapter()
    codex_probe = codex.probe
    codex_profile = EngineProfile(
        "codex",
        "codex-cli",
        codex_probe.version,
        "environment_gated",
        codex_probe.version,
        "operator_authenticated_unverified",
        codex.capabilities().capabilities,
        "gpt-5.6-luna",
        False,
        (codex_probe.reason, "Live execution remains gated until an operator-authenticated route is explicitly available."),
    )
    return [
        EngineProfile("synthetic", "synthetic-action", "1.0.0", "available", "local", "local_operator", _caps(**{name: "supported" for name in _CAPABILITY_NAMES}), "synthetic/local-alpha", False, ("Deterministic fixture; production-ineligible.",)),
        EngineProfile("api-native", "api-native-deterministic", "1.0.0", "available", "local", "local_operator", _caps(structuredEvents="supported", nonInteractiveExecution="supported", cancellation="supported", approvalIntegration="supported", tokenTelemetry="unavailable", costTelemetry="unavailable"), "deterministic/local", False, ("Provider-neutral deterministic transport; no provider SDK or credentials.",)),
        _optional_engine_profile("pi", "pi", "pi-reference"),
        codex_profile,
        _optional_engine_profile("opencode", "opencode", "opencode-adapter"),
    ]


class PortableExecutionService:
    def __init__(self, app: Any, repo_root: Path):
        self.app = app
        self.repo_root = repo_root
        self.store = RunStore(app.layout.operations_root / "portable-runs.json")
        self.bundle_root = app.layout.operations_root / "run-bundles"
        self.apply_snapshot_root = app.layout.operations_root / "apply-snapshots"
        self.apply_snapshot_root.mkdir(parents=True, exist_ok=True, mode=0o700)
        os.chmod(self.apply_snapshot_root, 0o700)
        self._active_processes: dict[str, threading.Event] = {}
        self._active_lock = threading.Lock()
        self._recover_interrupted_applies()

    @staticmethod
    def _process_identity(pid: int) -> tuple[str, int, int, str] | None:
        """Return Linux start ticks, process group, session, and state."""

        try:
            value = Path(f"/proc/{pid}/stat").read_text(encoding="utf-8")
            fields = value.rsplit(")", 1)[1].strip().split()
            start_ticks, group, session, state = (
                fields[19], int(fields[2]), int(fields[3]), fields[0],
            )
            if not start_ticks.isdigit():
                return None
            return start_ticks, group, session, state
        except (OSError, IndexError, ValueError):
            return None

    @classmethod
    def _current_supervisor(cls) -> dict[str, Any]:
        identity = cls._process_identity(os.getpid())
        if identity is None:
            raise PortableExecutionError("service process identity is unavailable")
        return {"pid": os.getpid(), "startTimeTicks": identity[0]}

    @classmethod
    def _supervisor_alive(cls, value: Any) -> bool:
        if not isinstance(value, dict):
            return False
        pid, ticks = value.get("pid"), value.get("startTimeTicks")
        if isinstance(pid, bool) or not isinstance(pid, int) or not isinstance(ticks, str):
            return False
        current = cls._process_identity(pid)
        return current is not None and current[0] == ticks and current[3] != "Z"

    @staticmethod
    def _process_generation(pid: int) -> str | None:
        try:
            values = Path(f"/proc/{pid}/environ").read_bytes().split(b"\0")
        except OSError:
            return None
        prefix = b"STATEPORT_PROCESS_GENERATION="
        matches = [item[len(prefix):] for item in values if item.startswith(prefix)]
        if len(matches) != 1:
            return None
        try:
            value = matches[0].decode("ascii")
        except UnicodeDecodeError:
            return None
        return value if re.fullmatch(r"generation\.[0-9a-f]{64}", value) else None

    @classmethod
    def _exact_apply_members(
        cls, group: int, session: int,
    ) -> tuple[tuple[int, str, str], ...]:
        try:
            entries = tuple(Path("/proc").iterdir())
        except OSError as exc:
            raise PortableExecutionError(
                "recorded apply process membership could not be observed"
            ) from exc
        members: list[tuple[int, str, str]] = []
        for entry in entries:
            if not entry.name.isdigit():
                continue
            identity = cls._process_identity(int(entry.name))
            if identity is not None and identity[1:3] == (group, session):
                members.append((int(entry.name), identity[0], identity[3]))
        return tuple(sorted(members))

    @classmethod
    def _exact_generation_members(
        cls, generation: str,
    ) -> tuple[tuple[int, str, str, int, int], ...]:
        """Return all processes retaining the pre-exec apply generation.

        Process group/session membership alone is insufficient because a
        descendant can create a new session. The random generation remains
        the cross-session ownership signal used for cleanup and restart.
        """

        if not re.fullmatch(r"generation\.[0-9a-f]{64}", generation):
            raise PortableExecutionError("recorded apply process generation is invalid")
        try:
            entries = tuple(Path("/proc").iterdir())
        except OSError as exc:
            raise PortableExecutionError(
                "recorded apply process generation could not be observed"
            ) from exc
        members: list[tuple[int, str, str, int, int]] = []
        for entry in entries:
            if not entry.name.isdigit():
                continue
            pid = int(entry.name)
            identity = cls._process_identity(pid)
            if identity is None or cls._process_generation(pid) != generation:
                continue
            started, group, session, state = identity
            members.append((pid, started, state, group, session))
        return tuple(sorted(members))

    @staticmethod
    def _process_group_exists(group: int) -> bool:
        try:
            os.killpg(group, 0)
            return True
        except ProcessLookupError:
            return False
        except PermissionError:
            return True

    @staticmethod
    def _fsync_directory(path: Path) -> None:
        descriptor = os.open(path, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
        try:
            os.fsync(descriptor)
        finally:
            os.close(descriptor)

    def _apply_snapshot_path(self, key: str) -> Path:
        if not re.fullmatch(r"[0-9a-f]{64}", key):
            raise PortableExecutionError("apply snapshot identity is invalid")
        path = self.apply_snapshot_root / key
        if path.is_symlink():
            raise PortableExecutionError("apply snapshot may not be a symlink")
        return path

    def _persist_apply_snapshot(self, run_id: str, before: Any) -> tuple[str, str]:
        snapshot_digest = digest_snapshot(before)
        key = digest({"runId": run_id, "snapshotDigest": snapshot_digest})[7:]
        destination = self._apply_snapshot_path(key)
        if destination.exists():
            raise PortableExecutionError("apply snapshot identity already exists")
        temporary = self.apply_snapshot_root / f".{key}.{os.getpid()}.{secrets.token_hex(4)}"
        temporary.mkdir(mode=0o700)
        try:
            instance = temporary / "instance"
            instance.mkdir(mode=0o700)
            restore_snapshot(instance, before)
            for item in sorted(instance.rglob("*"), reverse=True):
                if item.is_symlink():
                    raise PortableExecutionError("durable apply snapshot contains a symlink")
                if item.is_file():
                    os.chmod(item, 0o600)
                    descriptor = os.open(item, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0))
                    try:
                        os.fsync(descriptor)
                    finally:
                        os.close(descriptor)
                elif item.is_dir():
                    os.chmod(item, 0o700)
                    self._fsync_directory(item)
                else:
                    raise PortableExecutionError("durable apply snapshot contains an unsafe entry")
            manifest = temporary / "manifest.json"
            payload = json.dumps({
                "formatVersion": "stateport.apply-snapshot/v1",
                "runId": run_id,
                "snapshotDigest": snapshot_digest,
            }, sort_keys=True, separators=(",", ":")).encode("utf-8") + b"\n"
            descriptor = os.open(
                manifest,
                os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0),
                0o600,
            )
            try:
                os.write(descriptor, payload)
                os.fsync(descriptor)
            finally:
                os.close(descriptor)
            self._fsync_directory(instance)
            self._fsync_directory(temporary)
            os.replace(temporary, destination)
            self._fsync_directory(self.apply_snapshot_root)
            return key, snapshot_digest
        except Exception:
            shutil.rmtree(temporary, ignore_errors=True)
            raise

    def _load_apply_snapshot(self, run_id: str, key: str, expected_digest: str) -> Any:
        directory = self._apply_snapshot_path(key)
        if not directory.is_dir():
            raise PortableExecutionError("durable apply snapshot is missing")
        manifest_path = directory / "manifest.json"
        if manifest_path.is_symlink() or not manifest_path.is_file():
            raise PortableExecutionError("durable apply snapshot manifest is missing")
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        if manifest != {
            "formatVersion": "stateport.apply-snapshot/v1",
            "runId": run_id,
            "snapshotDigest": expected_digest,
        }:
            raise PortableExecutionError("durable apply snapshot manifest drifted")
        snapshot = snapshot_files(directory / "instance")
        if digest_snapshot(snapshot) != expected_digest:
            raise PortableExecutionError("durable apply snapshot content drifted")
        return snapshot

    def _discard_apply_snapshot(self, key: str) -> None:
        directory = self._apply_snapshot_path(key)
        if directory.exists():
            if not directory.is_dir():
                raise PortableExecutionError("apply snapshot cleanup target is unsafe")
            shutil.rmtree(directory)
            self._fsync_directory(self.apply_snapshot_root)

    @classmethod
    def _terminate_apply_process(cls, value: Any) -> str:
        if not isinstance(value, dict) or value.get("state") not in {"active", "starting"}:
            return "no_active_registered_process"
        pid, group, ticks = value.get("pid"), value.get("processGroupId"), value.get("startTimeTicks")
        generation = value.get("processGeneration")
        if (
            isinstance(pid, bool) or not isinstance(pid, int) or pid <= 1
            or group != pid or not isinstance(ticks, str) or not ticks.isdigit()
            or not isinstance(generation, str)
            or not re.fullmatch(r"generation\.[0-9a-f]{64}", generation)
        ):
            raise PortableExecutionError("recorded apply process identity is invalid")
        current = cls._process_identity(pid)
        leader_mismatch = current is not None and (
            current[0] != ticks or current[1] != group or current[2] != pid
        )
        session_members = cls._exact_apply_members(group, pid)
        generation_members = cls._exact_generation_members(generation)
        if not session_members and not generation_members:
            if leader_mismatch:
                return "identity_mismatch_original_absent"
            if cls._process_group_exists(group):
                raise PortableExecutionError(
                    "recorded apply process group was reused without its generation"
                )
            return "already_absent"
        for signal_value, timeout in ((signal.SIGTERM, 0.25), (signal.SIGKILL, 1.0)):
            deadline = time.monotonic() + timeout
            while True:
                session_members = cls._exact_apply_members(group, pid)
                generation_members = cls._exact_generation_members(generation)
                targets: dict[int, tuple[str, str]] = {
                    member_pid: (member_ticks, state)
                    for member_pid, member_ticks, state, _group, _session
                    in generation_members
                }
                for member_pid, member_ticks, state in session_members:
                    if state != "Z" and cls._process_generation(member_pid) != generation:
                        raise PortableExecutionError(
                            "recorded apply process generation could not be proven"
                        )
                    targets.setdefault(member_pid, (member_ticks, state))
                if not targets:
                    if cls._process_group_exists(group):
                        raise PortableExecutionError(
                            "recorded apply process group cleanup could not be proven"
                        )
                    return "terminated_exact_process_group"
                for member_pid, (member_ticks, state) in targets.items():
                    if state == "Z":
                        try:
                            os.waitpid(member_pid, os.WNOHANG)
                        except (ChildProcessError, OSError):
                            pass
                        continue
                    observed = cls._process_identity(member_pid)
                    if observed is None or observed[0] != member_ticks:
                        continue
                    if cls._process_generation(member_pid) != generation:
                        raise PortableExecutionError(
                            "recorded apply process generation could not be proven"
                        )
                    try:
                        os.kill(member_pid, signal_value)
                    except ProcessLookupError:
                        continue
                    except PermissionError as exc:
                        raise PortableExecutionError(
                            "recorded apply process could not be signalled"
                        ) from exc
                if time.monotonic() >= deadline:
                    break
                time.sleep(0.01)
        raise PortableExecutionError("recorded apply process generation could not be terminated")

    def _recover_interrupted_applies(self) -> None:
        """Restore crash-interrupted canonical applies before accepting new work."""

        still_owned: set[str] = set()
        for record in self.store.all():
            transaction = record.get("applyTransaction")
            key = transaction.get("snapshotKey") if isinstance(transaction, dict) else None
            if record.get("status") != "applying":
                rollback = record.get("rollback")
                if (
                    record.get("status") == "interrupted"
                    and isinstance(rollback, dict)
                    and rollback.get("operatorInspectionRequired") is True
                ):
                    # The fsynced pre-apply snapshot is the only deterministic
                    # recovery artifact. Retain it across every restart until
                    # an explicit operator recovery proves rollback or closes
                    # the incident with separate evidence.
                    continue
                if isinstance(key, str):
                    try:
                        self._discard_apply_snapshot(key)
                    except PortableExecutionError:
                        pass
                continue
            run_id = str(record.get("runId", ""))
            if self._supervisor_alive(record.get("applySupervisor")):
                still_owned.add(run_id)
                continue
            try:
                action = self._terminate_apply_process(record.get("applyProcess"))
                if not isinstance(transaction, dict) or not isinstance(key, str):
                    raise PortableExecutionError("interrupted apply lacks a durable snapshot reference")
                expected = transaction.get("snapshotDigest")
                if not isinstance(expected, str):
                    raise PortableExecutionError("interrupted apply lacks a durable snapshot digest")
                before = self._load_apply_snapshot(run_id, key, expected)
                _entry, root = self.app._entry(record["instanceId"])
                with InstanceLease(
                    self.app.layout.operations_root / "leases", root,
                    owner=f"portable-recovery:{run_id}",
                ):
                    restore_snapshot(root, before)
                    restored = digest_snapshot(snapshot_files(root))
                    if restored != expected:
                        raise PortableExecutionError("recovery rollback digest did not match")
                    recovered_transaction = dict(transaction)
                    recovered_transaction.update({
                        "rollbackStatus": "completed_after_restart",
                        "processRecovery": action,
                    })
                    self.store.transition(
                        run_id, "apply_failed", actor="stateport-recovery",
                        reason="service restart restored the fsynced pre-apply snapshot",
                        diagnostic="crash-interrupted apply restored byte-identically",
                        applyTransaction=recovered_transaction,
                        canonicalStateAfter=restored,
                        rollback={
                            "status": "completed", "byteIdentical": True,
                            "restoredDigest": restored,
                            "recoveryClassification": "service_restart",
                        },
                    )
                self._discard_apply_snapshot(key)
            except Exception as exc:  # noqa: BLE001 - persist an explicit unknown boundary
                try:
                    self.store.transition(
                        run_id, "interrupted", actor="stateport-recovery",
                        reason="service restart could not prove canonical rollback",
                        diagnostic="operator inspection is required after interrupted apply",
                        rollback={
                            "status": "unknown", "byteIdentical": False,
                            "operatorInspectionRequired": True,
                        },
                    )
                except Exception:
                    raise PortableExecutionError(
                        "interrupted apply could not be reconciled safely"
                    ) from exc
        self.store.recover_orphans(active_run_ids=still_owned)

    def _instance_requires_operator_recovery(self, instance_id: str) -> bool:
        return any(
            record.get("instanceId") == instance_id
            and record.get("status") == "interrupted"
            and isinstance(record.get("rollback"), dict)
            and record["rollback"].get("operatorInspectionRequired") is True
            for record in self.store.all()
        )

    @staticmethod
    def _safe_relative(value: Any, label: str) -> str:
        if not isinstance(value, str) or not value:
            raise PortableExecutionError(f"{label} is missing")
        path = Path(value)
        if path.is_absolute() or "\\" in value or any(part in {"", ".", ".."} for part in path.parts):
            raise PortableExecutionError(f"{label} is unsafe")
        return path.as_posix()

    @classmethod
    def _executor_identity(cls, source_root: Path, value: Any) -> dict[str, str]:
        relative = cls._safe_relative(value, "application executor")
        source = source_root.resolve(strict=True)
        target = source / relative
        cursor = source
        for part in Path(relative).parts:
            cursor = cursor / part
            if cursor.is_symlink():
                raise PortableExecutionError("application executor may not traverse a symlink")
        if not target.is_file():
            raise PortableExecutionError("application executor is missing")
        target.resolve(strict=True).relative_to(source)
        return {"path": relative, "digest": digest(target.read_bytes())}

    @classmethod
    def _proposal_paths(cls, proposal: Any) -> tuple[str, ...]:
        if not isinstance(proposal, dict):
            raise PortableExecutionError("state-change proposal must be an object")
        raw: list[Any] = []
        operation = proposal.get("operation")
        if isinstance(operation, dict):
            raw.append(operation.get("path"))
        operations = proposal.get("operations")
        if operations is not None:
            if not isinstance(operations, list):
                raise PortableExecutionError("proposal operations must be an array")
            for item in operations:
                if not isinstance(item, dict):
                    raise PortableExecutionError("proposal operation must be an object")
                raw.append(item.get("path"))
        if not raw:
            raise PortableExecutionError("proposal must declare every writable path")
        paths = tuple(sorted(cls._safe_relative(value, "proposal path") for value in raw))
        if len(set(paths)) != len(paths):
            raise PortableExecutionError("proposal paths must be unique")
        return paths

    @staticmethod
    def _ownership(root: Path, descriptor: dict[str, Any]) -> dict[str, str]:
        result: dict[str, str] = {}
        state_layout = descriptor.get("stateLayout")
        if isinstance(state_layout, dict) and isinstance(state_layout.get("ownership"), dict):
            for path, owner in state_layout["ownership"].items():
                if isinstance(path, str) and isinstance(owner, str):
                    result[path] = owner
        manifest = root / ".statedd/manifest.yaml"
        if manifest.is_file() and not manifest.is_symlink():
            value = yaml.safe_load(manifest.read_text(encoding="utf-8")) or {}
            assets = value.get("assets") if isinstance(value, dict) else None
            if isinstance(assets, list):
                for asset in assets:
                    if isinstance(asset, dict) and isinstance(asset.get("path"), str) and isinstance(asset.get("owner"), str):
                        result[asset["path"]] = asset["owner"]
        return result

    @classmethod
    def _validate_proposal_authority(
        cls, root: Path, descriptor: dict[str, Any], proposal: dict[str, Any],
    ) -> tuple[str, ...]:
        paths = cls._proposal_paths(proposal)
        ownership = cls._ownership(root, descriptor)
        for path in paths:
            if ownership.get(path) != "instance":
                raise PortableExecutionError(
                    "proposal path is not machine-readably instance-owned"
                )
        return paths

    @staticmethod
    def _validate_application_receipt(
        value: Any, proposal: dict[str, Any], observed_after: str,
        *, base_git: str, final_git: str,
    ) -> dict[str, Any]:
        if not isinstance(value, dict):
            raise PortableExecutionError("application writer receipt must be an object")
        required = {
            "formatVersion", "proposalId", "preStateDigest", "postStateDigest", "validation",
        }
        if not required.issubset(value) or not isinstance(value.get("formatVersion"), str):
            raise PortableExecutionError("application writer receipt is incomplete")
        if value.get("proposalId") != proposal.get("proposalId"):
            raise PortableExecutionError("application writer receipt is not bound to the approved proposal")
        if value.get("preStateDigest") != proposal.get("preStateDigest"):
            raise PortableExecutionError("application writer receipt has the wrong pre-state identity")
        if value.get("validation") != "passed":
            raise PortableExecutionError("application writer did not report passed validation")
        if not isinstance(value.get("postStateDigest"), str) or not value["postStateDigest"].startswith("sha256:"):
            raise PortableExecutionError("application writer receipt lacks a post-state digest")
        return {
            "formatVersion": "stateport.application-apply-receipt/v1",
            "proposalId": value["proposalId"],
            "preStateDigest": value["preStateDigest"],
            "postStateDigest": observed_after,
            "postStateDigestAuthority": "stateport_full_regular_tree_snapshot",
            "baseGit": base_git,
            "finalGit": final_git,
            "applicationReceipt": {
                "formatVersion": value["formatVersion"],
                "postStateDigest": value["postStateDigest"],
                "digest": digest(value),
            },
            "validation": "passed",
        }

    @classmethod
    def _build_run_closure_receipt(
        cls,
        record: dict[str, Any],
        *,
        created_at: str | None = None,
    ) -> dict[str, Any]:
        """Build the exact receipt only from an authoritatively closed run.

        The application writer receipt proves its bounded staging operation.
        This separate receipt is StatePort's closure projection: it is created
        only after StatePort-selected post-apply validation passed and the
        applied RunBundle was sealed. The caller persists it in the same
        locked store transition that records ``CLOSED``.
        """

        if (
            record.get("formatVersion") != RUN_FORMAT
            or record.get("status") != "applied"
            or record.get("lifecycleState") not in {"POST_VALIDATED", "CLOSED"}
            or record.get("lifecycleVersion") != "stateport.run-lifecycle/v1"
        ):
            raise PortableExecutionError(
                "run closure receipt requires an applied, post-validated governed run"
            )
        run_id = record.get("runId")
        instance_id = record.get("instanceId")
        application_id = record.get("applicationId")
        action_id = record.get("actionId")
        engine = record.get("engine")
        engine_id = engine.get("engineId") if isinstance(engine, dict) else None
        if not all(
            isinstance(value, str) and value
            for value in (run_id, instance_id, application_id, action_id, engine_id)
        ):
            raise PortableExecutionError(
                "run closure receipt lacks exact application or run identity"
            )

        proposal = record.get("proposal")
        proposal_digest = record.get("proposalDigest")
        proposal_id = proposal.get("proposalId") if isinstance(proposal, dict) else None
        if (
            not isinstance(proposal, dict)
            or not isinstance(proposal_id, str)
            or not isinstance(proposal_digest, str)
            or _PUBLIC_MATRIX_DIGEST.fullmatch(proposal_digest) is None
            or digest(proposal) != proposal_digest
        ):
            raise PortableExecutionError(
                "run closure receipt proposal identity is invalid"
            )

        approval = record.get("proposalApproval")
        approval_digest = (
            approval.get("approvalDigest") if isinstance(approval, dict) else None
        )
        unsigned_approval = dict(approval) if isinstance(approval, dict) else {}
        unsigned_approval.pop("approvalDigest", None)
        if (
            not isinstance(approval, dict)
            or not isinstance(approval_digest, str)
            or _PUBLIC_MATRIX_DIGEST.fullmatch(approval_digest) is None
            or digest(unsigned_approval) != approval_digest
            or approval.get("runId") != run_id
            or approval.get("proposalDigest") != proposal_digest
        ):
            raise PortableExecutionError(
                "run closure receipt proposal approval identity is invalid"
            )

        application_receipt = record.get("receipt")
        required_application_receipt = {
            "formatVersion",
            "proposalId",
            "preStateDigest",
            "postStateDigest",
            "postStateDigestAuthority",
            "baseGit",
            "finalGit",
            "applicationReceipt",
            "validation",
        }
        if (
            not isinstance(application_receipt, dict)
            or set(application_receipt) != required_application_receipt
            or application_receipt.get("formatVersion")
            != "stateport.application-apply-receipt/v1"
            or application_receipt.get("proposalId") != proposal_id
            or application_receipt.get("validation") != "passed"
        ):
            raise PortableExecutionError(
                "run closure receipt application receipt identity is invalid"
            )

        run_spec_digest = record.get("runSpecDigest")
        descriptor_digest = record.get("descriptorDigest")
        action_contract_digest = record.get("actionContractDigest")
        before_digest = record.get("canonicalStateBefore")
        after_digest = record.get("canonicalStateAfter")
        base_git = record.get("baseGit")
        final_git = application_receipt.get("finalGit")
        digest_values = (
            run_spec_digest,
            descriptor_digest,
            action_contract_digest,
            before_digest,
            after_digest,
        )
        if any(
            not isinstance(value, str)
            or _PUBLIC_MATRIX_DIGEST.fullmatch(value) is None
            for value in digest_values
        ):
            raise PortableExecutionError(
                "run closure receipt carries an invalid governed digest"
            )
        if (
            not isinstance(base_git, str)
            or re.fullmatch(r"[0-9a-f]{40,64}", base_git) is None
            or final_git != base_git
            or application_receipt.get("baseGit") != base_git
            or application_receipt.get("postStateDigest") != after_digest
        ):
            raise PortableExecutionError(
                "run closure receipt final repository or state identity drifted"
            )

        transaction = record.get("applyTransaction")
        if (
            not isinstance(transaction, dict)
            or transaction.get("beforeDigest") != before_digest
            or transaction.get("afterDigest") != after_digest
            or transaction.get("baseGit") != base_git
            or transaction.get("finalGit") != final_git
            or transaction.get("rollbackStatus") != "not_required"
        ):
            raise PortableExecutionError(
                "run closure receipt transaction identity is invalid"
            )
        validation = record.get("postApplyValidation")
        if (
            not isinstance(validation, dict)
            or validation.get("status") != "passed"
            or not isinstance(validation.get("commandDigest"), str)
            or _PUBLIC_MATRIX_DIGEST.fullmatch(validation["commandDigest"]) is None
        ):
            raise PortableExecutionError(
                "run closure receipt requires exact local validation evidence"
            )
        applied_bundle = record.get("appliedRunBundle")
        if (
            not isinstance(applied_bundle, dict)
            or applied_bundle.get("formatVersion") != "stateport.run-bundle/v1"
            or applied_bundle.get("runId") != run_id
            or not isinstance(applied_bundle.get("contentDigest"), str)
            or _PUBLIC_MATRIX_DIGEST.fullmatch(applied_bundle["contentDigest"]) is None
        ):
            raise PortableExecutionError(
                "run closure receipt requires the exact applied RunBundle"
            )

        timestamp = created_at or _now()
        if (
            not isinstance(timestamp, str)
            or _RUN_CLOSURE_TIMESTAMP.fullmatch(timestamp) is None
        ):
            raise PortableExecutionError(
                "run closure receipt timestamp is invalid"
            )
        identity_digest = digest(
            {
                "runId": run_id,
                "instanceId": instance_id,
                "applicationId": application_id,
                "runSpecDigest": run_spec_digest,
                "proposalDigest": proposal_digest,
                "canonicalStateAfter": after_digest,
                "appliedRunBundleDigest": applied_bundle["contentDigest"],
            }
        )
        receipt_id = f"governed-run.{run_id}.{identity_digest[7:19]}"
        if _RUN_CLOSURE_RECEIPT_ID.fullmatch(receipt_id) is None:
            raise PortableExecutionError("run closure receipt identity is invalid")

        return {
            "formatVersion": _RUN_CLOSURE_RECEIPT_FORMAT,
            "receiptId": receipt_id,
            "receiptType": _RUN_CLOSURE_RECEIPT_FORMAT,
            "action": "governed_run.apply",
            "status": "applied",
            "createdAt": timestamp,
            "sourceKind": "governed_run",
            "actor": "system",
            "applicationId": application_id,
            "instanceId": instance_id,
            "runId": run_id,
            "actionId": action_id,
            "engineId": engine_id,
            "runSpecDigest": run_spec_digest,
            "descriptorDigest": descriptor_digest,
            "actionContractDigest": action_contract_digest,
            "sourceIdentityDigest": digest(record.get("sourceIdentity", {})),
            "proposalId": proposal_id,
            "proposalDigest": proposal_digest,
            "proposalApprovalDigest": approval_digest,
            "baseGit": base_git,
            "finalGit": final_git,
            "canonicalStateBefore": before_digest,
            "canonicalStateAfter": after_digest,
            "applicationReceiptDigest": digest(application_receipt),
            "appliedRunBundleDigest": applied_bundle["contentDigest"],
            "validation": {
                "state": "validated",
                "detail": (
                    "StatePort-selected post-apply validation passed locally; "
                    "human and remote acceptance are not recorded."
                ),
            },
            "postApplyValidation": dict(validation),
            "claimState": {
                "applied": True,
                "locallyValidated": True,
                "humanAccepted": False,
                "remotelyAccepted": False,
            },
            "summary": "StatePort applied the exact approved governed-run proposal.",
            "beforeSummary": "Canonical application state matched the approved pre-state and Git base.",
            "afterSummary": "The approved filesystem transaction was applied and locally validated.",
        }

    @classmethod
    def _validate_run_closure_receipt(
        cls,
        record: dict[str, Any],
        value: Any,
    ) -> dict[str, Any]:
        if not isinstance(value, dict):
            raise PortableExecutionError("run closure receipt is not an object")
        expected = cls._build_run_closure_receipt(
            record,
            created_at=value.get("createdAt"),
        )
        if value != expected:
            raise PortableExecutionError(
                "persisted run closure receipt does not match the governed run"
            )
        return dict(value)

    @classmethod
    def _remove_transaction_ephemera(
        cls, root: Path, before: Any, descriptor: dict[str, Any],
    ) -> None:
        """Remove only descriptor-declared, empty operational lock artifacts."""

        declared = descriptor.get("transactionEphemeralPaths", [])
        if not isinstance(declared, list):
            raise PortableExecutionError("transaction ephemeral paths must be an array")
        for value in declared:
            relative = cls._safe_relative(value, "transaction ephemeral path")
            path = root / relative
            if relative in before:
                if not path.is_file() or path.is_symlink() or path.read_bytes() != before[relative]:
                    raise PortableExecutionError("transaction ephemeral path changed durable content")
                continue
            if not path.exists():
                continue
            if path.is_symlink() or not path.is_file() or path.read_bytes() != b"":
                raise PortableExecutionError("transaction ephemeral output is not an empty regular lock file")
            path.unlink()

    @staticmethod
    def _git_identity(root: Path) -> str | None:
        if not (root / ".git").exists():
            return None
        try:
            top = subprocess.run(
                ["git", "-C", str(root), "rev-parse", "--show-toplevel"],
                check=True, capture_output=True, text=True, timeout=5,
                env=filtered_environment(),
            ).stdout.strip()
            if Path(top).resolve() != root.resolve():
                return None
            value = subprocess.run(
                ["git", "-C", str(root), "rev-parse", "HEAD"],
                check=True, capture_output=True, text=True, timeout=5,
                env=filtered_environment(),
            ).stdout.strip()
        except (OSError, subprocess.SubprocessError):
            raise PortableExecutionError("instance Git identity could not be observed")
        if not re.fullmatch(r"[0-9a-f]{40,64}", value):
            raise PortableExecutionError("instance Git identity is invalid")
        return value

    def applications(self) -> list[dict[str, Any]]:
        descriptors = discover_application_descriptors(self.repo_root)
        return descriptors

    def engines(self) -> list[dict[str, Any]]:
        return [profile.to_dict() for profile in engine_profiles()]

    def _application_descriptor(self, application_id: str) -> dict[str, Any]:
        for descriptor in self.applications():
            if descriptor.get("applicationId") == application_id:
                return descriptor
        raise PortableExecutionError("application descriptor is not registered")

    def application_identity(self, application_id: str) -> dict[str, str]:
        """Return a stable identity without the repository-local source path."""

        descriptor = self._application_descriptor(application_id)
        portable = {key: value for key, value in descriptor.items() if key != "descriptorPath"}
        return {
            "formatVersion": str(portable.get("formatVersion", "")),
            "applicationId": application_id,
            "descriptorDigest": digest(portable),
        }

    def _browser_fixture_contract(
        self,
        application_id: str,
    ) -> tuple[dict[str, Any], dict[str, str], str, Path, str]:
        """Resolve the single fail-closed contract used by catalog and install."""

        descriptor = self._application_descriptor(application_id)
        application_identity = self.application_identity(application_id)
        if (
            descriptor.get("privacyClassification") != "public_safe"
            or descriptor.get("productionEligible") is not False
        ):
            raise PortableExecutionError(
                "browser fixture installation is limited to public-safe non-production packages"
            )
        profile = descriptor.get("sourceProfile")
        if not isinstance(profile, str) or not profile.startswith("fixture:"):
            raise PortableExecutionError(
                "only descriptor-declared fixture sources may be installed by this operation"
            )
        descriptor_path = descriptor.get("descriptorPath")
        relative_descriptor = Path(descriptor_path) if isinstance(descriptor_path, str) else Path()
        if (
            not descriptor_path
            or relative_descriptor.is_absolute()
            or any(part in {"", ".", ".."} for part in relative_descriptor.parts)
        ):
            raise PortableExecutionError("fixture descriptor path is unsafe")
        descriptor_file = self.repo_root / relative_descriptor
        if descriptor_file.is_symlink() or not descriptor_file.is_file():
            raise PortableExecutionError("fixture descriptor is unavailable")
        source_root = descriptor_file.parent.resolve()
        fixture_root = (self.repo_root / "fixtures/apps").resolve()
        try:
            source_root.relative_to(fixture_root)
        except ValueError as exc:
            raise PortableExecutionError("fixture source escaped the public fixture root") from exc

        actions_path = descriptor.get("actionsPath")
        relative_actions = Path(actions_path) if isinstance(actions_path, str) else Path()
        if (
            not actions_path
            or relative_actions.is_absolute()
            or any(part in {"", ".", ".."} for part in relative_actions.parts)
        ):
            raise PortableExecutionError("fixture action contract path is unsafe")
        actions_file = source_root / relative_actions
        try:
            resolved_actions = actions_file.resolve(strict=True)
            resolved_actions.relative_to(source_root)
        except (OSError, ValueError) as exc:
            raise PortableExecutionError("fixture action contract is unavailable") from exc
        if actions_file.is_symlink() or not resolved_actions.is_file():
            raise PortableExecutionError("fixture action contract is unavailable")
        if resolved_actions.stat().st_size > 1024 * 1024:
            raise PortableExecutionError("fixture action contract exceeds the browser-install bound")
        try:
            actions_document = yaml.safe_load(resolved_actions.read_text(encoding="utf-8")) or {}
        except (OSError, UnicodeError, yaml.YAMLError) as exc:
            raise PortableExecutionError("fixture action contract cannot be validated") from exc
        actions = actions_document.get("actions") if isinstance(actions_document, dict) else None
        if not isinstance(actions, list) or not actions or any(
            not isinstance(action, dict) or action.get("networkPolicy") != "disabled"
            for action in actions
        ):
            raise PortableExecutionError("browser fixture actions must disable network access")
        package_digest = self._fixture_tree_digest(source_root)
        return descriptor, application_identity, profile, source_root, package_digest

    @staticmethod
    def _fixture_tree_digest(source_root: Path) -> str:
        """Digest the exact bounded regular-file tree without following links."""

        entries: list[tuple[object, ...]] = []
        total_bytes = 0
        for path in sorted(source_root.rglob("*"), key=lambda item: item.relative_to(source_root).as_posix()):
            relative = path.relative_to(source_root)
            if "__pycache__" in relative.parts or path.suffix == ".pyc":
                continue
            if len(entries) >= _MAX_BROWSER_FIXTURE_ENTRIES:
                raise PortableExecutionError("fixture package exceeds the browser-install entry bound")
            info = path.lstat()
            name = relative.as_posix()
            if stat.S_ISLNK(info.st_mode):
                raise PortableExecutionError("fixture package may not contain symbolic links")
            if stat.S_ISDIR(info.st_mode):
                entries.append(("directory", name))
                continue
            if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
                raise PortableExecutionError("fixture package may contain only private regular files")
            flags = os.O_RDONLY | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0)
            try:
                file_fd = os.open(path, flags)
            except OSError as exc:
                raise PortableExecutionError("fixture package file cannot be read safely") from exc
            try:
                before = os.fstat(file_fd)
                if (
                    not stat.S_ISREG(before.st_mode)
                    or before.st_nlink != 1
                    or (before.st_dev, before.st_ino) != (info.st_dev, info.st_ino)
                ):
                    raise PortableExecutionError("fixture package changed during validation")
                chunks = bytearray()
                while True:
                    chunk = os.read(file_fd, min(1024 * 1024, _MAX_BROWSER_FIXTURE_BYTES + 1))
                    if not chunk:
                        break
                    chunks.extend(chunk)
                    total_bytes += len(chunk)
                    if total_bytes > _MAX_BROWSER_FIXTURE_BYTES:
                        raise PortableExecutionError("fixture package exceeds the browser-install size bound")
                after = os.fstat(file_fd)
                before_identity = (
                    before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns, before.st_nlink,
                )
                after_identity = (
                    after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns, after.st_nlink,
                )
                if before_identity != after_identity:
                    raise PortableExecutionError("fixture package changed during validation")
                entries.append((
                    "file",
                    name,
                    bool(before.st_mode & (stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)),
                    digest(bytes(chunks)),
                ))
            finally:
                os.close(file_fd)
        return digest(entries)

    def browser_fixture_install_eligibility(self, application_id: str) -> dict[str, Any]:
        """Return a content-free catalog decision from the installer contract."""

        try:
            *_, package_digest = self._browser_fixture_contract(application_id)
        except PortableExecutionError:
            return {
                "eligible": False,
                "reasons": ["browser_fixture_contract_invalid"],
                "networkPolicy": "not_evaluated",
            }
        return {
            "eligible": True,
            "reasons": [],
            "networkPolicy": "disabled",
            "packageDigest": package_digest,
        }

    def _source_root(
        self,
        instance_id: str,
        *,
        allow_development_candidate: bool = False,
    ) -> tuple[Path, Path, dict[str, Any]]:
        entry, root = self.app._entry(instance_id)
        descriptor = self._application_descriptor(str(entry.get("applicationId", "")))
        profile = descriptor.get("sourceProfile")
        if not isinstance(profile, str) or not profile:
            raise PortableExecutionError("application source profile is missing")
        try:
            if profile.startswith("fixture:"):
                descriptor_path = descriptor.get("descriptorPath")
                if not isinstance(descriptor_path, str):
                    raise PortableExecutionError("fixture descriptor path is missing")
                source_root = (self.repo_root / descriptor_path).parent.resolve()
                fixture_root = (self.repo_root / "fixtures/apps").resolve()
                source_root.relative_to(fixture_root)
                package_digest = self._fixture_tree_digest(source_root)
                # A registered raw development fixture may expose the descriptor and
                # actions without the install-time instance/lock materialization; in
                # that case the immutable repository fixture is the authoritative
                # source. When a lock is present it must still match these bytes.
                try:
                    locked = self.app.locked_source(instance_id).get("source", {})
                except Exception:  # noqa: BLE001 - no materialized lock for a raw fixture
                    locked = {}
                if locked:
                    if locked.get("resolvedCommit") != "fixture:" + str(locked.get("manifestDigest", ""))[7:]:
                        raise PortableExecutionError("fixture source lock identity is malformed")
                    if (
                        locked.get("resolvedCommit") != "fixture:" + package_digest[7:]
                        or locked.get("resolvedTree") != package_digest[7:]
                        or locked.get("manifestDigest") != package_digest
                    ):
                        raise PortableExecutionError("fixture source bytes differ from the installed lock")
                return root, source_root, descriptor
            resolved = self.app.bind_installed_source(
                instance_id,
                profile,
                allow_development_candidate=allow_development_candidate,
            )
            return root, resolved.root, descriptor
        except PortableExecutionError:
            raise
        except Exception as exc:  # noqa: BLE001
            raise PortableExecutionError("application source is unavailable for action preparation") from exc

    def _actions(
        self,
        instance_id: str,
        *,
        allow_development_candidate: bool = False,
    ) -> dict[str, ActionContract]:
        _, source_root, descriptor = self._source_root(
            instance_id,
            allow_development_candidate=allow_development_candidate,
        )
        action_path = descriptor.get("actionsPath")
        if not isinstance(action_path, str) or not action_path or Path(action_path).is_absolute() or ".." in Path(action_path).parts:
            raise PortableExecutionError("application action path is unsafe")
        path = source_root / action_path
        if not path.is_file():
            raise PortableExecutionError("application action contract is not present in the immutable source")
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        actions = data.get("actions") if isinstance(data, dict) else None
        if not isinstance(actions, list):
            raise PortableExecutionError("application action contract is invalid")
        result: dict[str, ActionContract] = {}
        for item in actions:
            if not isinstance(item, dict):
                continue
            item = dict(item)
            if "executorCommand" not in item and isinstance(descriptor.get("executorCommand"), str):
                item["executorCommand"] = descriptor["executorCommand"]
            if isinstance(item.get("contextPolicy"), dict) and "categoryPaths" not in item["contextPolicy"] and isinstance(descriptor.get("contextCategoryPaths"), dict):
                item["contextPolicy"] = dict(item["contextPolicy"])
                item["contextPolicy"]["categoryPaths"] = descriptor["contextCategoryPaths"]
            action = ActionContract.from_dict(item)
            result[action.action_id] = action
        return result

    def install_fixture_instance(
        self,
        application_id: str,
        instance_id: str,
        name: str | None = None,
        *,
        expected_descriptor_digest: str | None = None,
        expected_package_digest: str | None = None,
        experience_descriptor_digest: str | None = None,
        consent: str = "trusted_internal",
        actor_id: str = "local-operator",
    ) -> dict[str, Any]:
        """Install one descriptor-declared public fixture through the catalog."""

        if not application_id or not instance_id or any(char not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789._-" for char in instance_id):
            raise PortableExecutionError("fixture instance identity is unsafe")
        (
            descriptor,
            application_identity,
            profile,
            source_root,
            package_digest,
        ) = self._browser_fixture_contract(application_id)
        if expected_descriptor_digest is not None and not secrets.compare_digest(
            expected_descriptor_digest, application_identity["descriptorDigest"],
        ):
            raise PortableExecutionError("application descriptor changed before installation")
        if consent == "explicit_browser_confirmation":
            if expected_descriptor_digest is None:
                raise PortableExecutionError("browser installation requires the exact application descriptor")
            if not isinstance(expected_package_digest, str) or not secrets.compare_digest(
                expected_package_digest, package_digest,
            ):
                raise PortableExecutionError("browser installation requires the exact fixture package")
            if not isinstance(experience_descriptor_digest, str) or not re.fullmatch(r"sha256:[0-9a-f]{64}", experience_descriptor_digest):
                raise PortableExecutionError("browser installation requires the exact experience descriptor")
        elif consent != "trusted_internal":
            raise PortableExecutionError("fixture installation consent route is unsupported")
        destination = (self.app.layout.instances_root / instance_id).resolve()
        destination.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        if destination.exists() or destination.is_symlink():
            raise PortableExecutionError("fixture instance destination already exists")
        catalog_registered = False
        try:
            shutil.copytree(source_root, destination, symlinks=False, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
            copied_digest = self._fixture_tree_digest(destination)
            if not secrets.compare_digest(copied_digest, package_digest):
                raise PortableExecutionError("fixture package changed while it was being copied")
            source_digest = package_digest
            (destination / "instance.yaml").write_text(yaml.safe_dump({"formatVersion": "stateport.application-instance/v1", "metadata": {"id": instance_id, "name": name or descriptor.get("displayName", instance_id)}, "spec": {"applicationId": application_id, "mode": "fixture"}}, sort_keys=False), encoding="utf-8")
            (destination / ".statedd").mkdir(parents=True, exist_ok=True)
            (destination / ".statedd/lock.yaml").write_text(yaml.safe_dump({"formatVersion": "stateport.application-lock/v1", "instanceId": instance_id, "template": {"id": application_id, "version": "fixture", "source": {"profile": profile, "resolvedCommit": "fixture:" + source_digest[7:], "resolvedTree": source_digest[7:], "manifestDigest": source_digest}}, "files": []}, sort_keys=False), encoding="utf-8")
            base_git = initialize_instance_repository(destination)
            entry = self.app.catalog.register(destination, instance_id=instance_id, name=name or str(descriptor.get("displayName", instance_id)), source={"templateId": application_id, "resolvedCommit": "fixture:" + source_digest[7:], "resolvedTree": source_digest[7:], "manifestDigest": source_digest})
            catalog_registered = True
            public_entry = {key: value for key, value in entry.items() if key not in {"path", "filesystem", "metadata"}}
            receipt = {
                "formatVersion": "stateport.application-install-receipt/v1",
                "receiptId": f"application-install.{instance_id}.{base_git[:12]}",
                "operation": "install_public_fixture",
                "applicationId": application_id,
                "instanceId": instance_id,
                "actor": {"actorId": actor_id, "route": consent},
                "descriptorIdentities": {
                    "application": {**application_identity, "packageDigest": package_digest},
                    "experience": {"descriptorDigest": experience_descriptor_digest or "trusted_internal_not_supplied"},
                },
                "source": {"digest": source_digest, "profile": profile, "networkPolicy": "disabled", "productionEligible": False},
                "baseGit": base_git,
                "catalogIdentity": public_entry,
                "consent": consent,
                "createdAt": _now(),
            }
            receipt_digest = self.app.record_application_install_receipt(receipt)
            return {
                "ok": True,
                "entry": public_entry,
                "source": receipt["source"],
                "baseGit": base_git,
                "receipt": {"formatVersion": receipt["formatVersion"], "receiptId": receipt["receiptId"], "receiptDigest": receipt_digest},
            }
        except Exception as exc:
            cleanup_failed = False
            if catalog_registered:
                try:
                    self.app.catalog.forget(instance_id)
                except Exception:  # noqa: BLE001 - preserve the primary failure and surface rollback uncertainty
                    cleanup_failed = True
            try:
                self.app.discard_application_install_receipt(instance_id)
            except Exception:  # noqa: BLE001 - fail closed when operational evidence cannot be removed
                cleanup_failed = True
            shutil.rmtree(destination, ignore_errors=True)
            if destination.exists():
                cleanup_failed = True
            if cleanup_failed:
                raise PortableExecutionError("fixture installation rollback requires operator inspection") from exc
            raise

    def action_list(
        self,
        instance_id: str,
        *,
        allow_development_candidate: bool = False,
    ) -> list[dict[str, Any]]:
        try:
            actions = self._actions(
                instance_id,
                allow_development_candidate=allow_development_candidate,
            )
        except PortableExecutionError as exc:
            if _is_development_candidate_gate(exc):
                return []
            raise
        return [action.to_dict() for action in actions.values()]

    @staticmethod
    def _validate_input(action: ActionContract, inputs: dict[str, Any]) -> None:
        schema = action.input_schema
        if schema.get("type") not in {None, "object"} or not isinstance(inputs, dict):
            raise PortableExecutionError("action input does not match its object schema")
        properties = schema.get("properties") if isinstance(schema.get("properties"), dict) else {}
        required = schema.get("required") if isinstance(schema.get("required"), list) else []
        missing = [name for name in required if name not in inputs]
        if missing:
            raise PortableExecutionError("action input is missing required fields: " + ", ".join(str(item) for item in missing))
        if schema.get("additionalProperties") is False:
            unknown = sorted(set(inputs) - set(properties))
            if unknown:
                raise PortableExecutionError("action input contains undeclared fields: " + ", ".join(unknown))
        for name, value in inputs.items():
            rule = properties.get(name) if isinstance(properties, dict) else None
            expected = rule.get("type") if isinstance(rule, dict) else None
            if expected == "string" and not isinstance(value, str):
                raise PortableExecutionError(f"action input field {name} must be a string")
            if expected == "integer" and (isinstance(value, bool) or not isinstance(value, int)):
                raise PortableExecutionError(f"action input field {name} must be an integer")
            if expected == "boolean" and not isinstance(value, bool):
                raise PortableExecutionError(f"action input field {name} must be a boolean")

    @staticmethod
    def _validate_result(action: ActionContract, result: dict[str, Any]) -> None:
        required = action.output_schema.get("required") if isinstance(action.output_schema, dict) else None
        if isinstance(required, list) and any(field not in result for field in required):
            raise PortableExecutionError("typed action result is missing a required field")

    @staticmethod
    def _state_digest(root: Path) -> str:
        try:
            return digest_snapshot(snapshot_files(root))
        except ValueError as exc:
            raise PortableExecutionError("canonical instance snapshot is unsafe") from exc

    def _profile(self, engine_id: str) -> EngineProfile:
        for profile in engine_profiles():
            if profile.engine_id == engine_id:
                return profile
        raise PortableExecutionError("unknown execution engine")

    def prepare(
        self,
        instance_id: str,
        action_id: str,
        engine_id: str,
        inputs: dict[str, Any] | None = None,
        *,
        allow_development_candidate: bool = False,
    ) -> dict[str, Any]:
        inputs = dict(inputs or {})
        actions = self._actions(
            instance_id,
            allow_development_candidate=allow_development_candidate,
        )
        action = actions.get(action_id)
        if action is None:
            raise PortableExecutionError("action is not declared by the application")
        if self._instance_requires_operator_recovery(instance_id):
            raise PortableExecutionError(
                "instance remains quarantined pending explicit operator recovery"
            )
        self._validate_input(action, inputs)
        profile = self._profile(engine_id)
        execution_gate = None
        if profile.availability != "available":
            # Preparation remains durable even when an external engine cannot
            # be safely started.  Operators must be able to inspect the exact
            # RunSpec and its typed environment gate instead of receiving an
            # unbound exception with no auditable run identity.
            execution_gate = {
                "status": "environment_gated",
                "engine": profile.engine_id,
                "reason": profile.limitations[0] if profile.limitations else "engine availability is not verified",
            }
        root, source_root, descriptor = self._source_root(
            instance_id,
            allow_development_candidate=allow_development_candidate,
        )
        base_git = self._git_identity(root)
        if action.mutation_policy == "propose_only" and base_git is None:
            raise PortableExecutionError(
                "write-capable runs require an exact instance Git HEAD"
            )
        inspected = self.app.inspect(instance_id)
        source_identity = dict(inspected.get("source", {})) if isinstance(inspected.get("source"), dict) else {}
        source_revision = str(source_identity.get("sourceDigest") or source_identity.get("resolvedCommit") or digest({"instance": instance_id}))
        context = compile_context(root, action_id, action.context_policy, int(action.budget_defaults.get("token", 1000)))
        run_id = "run-" + secrets.token_hex(10)
        required = tuple(CapabilityRequest(name, False) for name in action.required_capabilities)
        run_spec = AgentRunSpec(
            run_id, instance_id, source_revision, action.purpose,
            f"ephemeral:statepack/{context.digest[7:]}", context.digest, required, action.optional_capabilities,
            profile.engine_id, profile.adapter_id, profile.adapter_version, profile.model_identity,
            profile.authentication_route_class, (), "read-only", action.budget_defaults,
            (str(action.validation_policy["command"]),) if isinstance(action.validation_policy.get("command"), str) else (),
            ("artifacts/result.json",), {
                "application": str(descriptor.get("applicationId")),
                "action": action_id,
                "engine": engine_id,
                **({"baseGit": base_git} if base_git is not None else {}),
            }, approval_required_level="local_operator",
        )
        capabilities = BackendCapabilities(profile.engine_id, profile.adapter_id, profile.adapter_version, "reference", profile.capabilities, (profile.authentication_route_class,), (), not profile.production_eligible, profile.production_eligible)
        negotiation = negotiate(run_spec, capabilities)
        executor_identity = self._executor_identity(source_root, action.executor_command)
        record = {
            "formatVersion": "stateport.governed-action-run/v1", "runId": run_id,
            "instanceId": instance_id, "applicationId": descriptor.get("applicationId"),
            "actionId": action_id, "actionContractDigest": digest(action.to_dict()),
            "mutationPolicy": action.mutation_policy,
            "executorCommand": action.executor_command, "executorIdentity": executor_identity,
            "descriptorDigest": digest(descriptor), "engine": profile.to_dict(), "inputs": inputs,
            "status": "requested", "requestedAt": _now(), "sourceIdentity": source_identity,
            "sourceAccessClass": (
                "development_candidate" if allow_development_candidate else "installed_default"
            ),
            "statePack": {"digest": context.digest, "manifest": context.manifest, "text": context.text},
            "runSpec": run_spec.to_dict(), "runSpecDigest": run_spec.digest,
            "negotiation": negotiation, "executionGate": execution_gate,
            "canonicalStateBefore": self._state_digest(root), "baseGit": base_git,
            "baseIdentityClassification": "git_sha_plus_full_regular_tree_snapshot" if base_git is not None else "full_regular_tree_snapshot_read_only",
            "sideEffectClassification": "filesystem_transaction" if action.mutation_policy == "propose_only" else "none",
            "result": None, "proposal": None, "proposalPaths": [], "approval": None, "events": [],
        }
        self.store.create(record)
        if not negotiation["acceptedRun"] or execution_gate is not None:
            diagnostic = "capability negotiation blocked preparation" if not negotiation["acceptedRun"] else "engine execution is environment-gated"
            self.store.transition(run_id, "planned", diagnostic=diagnostic)
            failed = self.store.transition(
                run_id,
                "failed",
                lifecycleState="BLOCKED_CAPABILITY",
                diagnostic=diagnostic,
            )
            try:
                failed = self.store.update(run_id, runResult=self._engine_result(failed, execution_status="failed", termination_classification="launch_failure"))
                failed = self.store.update(run_id, runBundle=self._write_run_bundle(failed))
            except Exception:  # noqa: BLE001 - the blocked lifecycle remains authoritative
                pass
            payload = {"run": failed, "approvalRequired": False, "executionGate": execution_gate or {"status": "blocked_capability", "negotiation": negotiation}}
            if execution_gate is not None:
                raise EnvironmentGatedExecution(payload)
            raise PortableExecutionError(json.dumps({"code": "capability_negotiation_failed", "runId": run_id, "negotiation": negotiation}, sort_keys=True))
        self.store.transition(run_id, "planned")
        prepared = self.store.transition(run_id, "awaiting_approval")
        return self.inspect(run_id) | {"approvalRequired": True}

    def approve_run(self, run_id: str, operator_id: str = "local-operator", *, expected_instance_id: str | None = None, expected_revision: int | None = None) -> dict[str, Any]:
        record = self.store.require_binding(run_id, expected_instance_id=expected_instance_id, expected_revision=expected_revision)
        if not record or record.get("status") != "awaiting_approval":
            raise PortableExecutionError("run is not awaiting exact approval")
        approval = {"formatVersion": "stateport.run-approval/v1", "runId": run_id, "runSpecDigest": record["runSpecDigest"], "operatorId": operator_id, "approvedAt": _now()}
        approval["approvalDigest"] = digest(approval)
        return self.store.transition(run_id, "approved", approval=approval, expected_instance_id=expected_instance_id, expected_revision=expected_revision)

    def cancel(self, run_id: str, operator_id: str = "local-operator", *, expected_instance_id: str | None = None, expected_revision: int | None = None) -> dict[str, Any]:
        """Cancel a run idempotently; a process owner may later attach cleanup."""

        try:
            record = self.store.require_binding(run_id, expected_instance_id=expected_instance_id, expected_revision=expected_revision)
        except KeyError as exc:
            raise PortableExecutionError("unknown run") from exc
        status = record.get("status")
        if status == "cancelled":
            return record
        if status == "running":
            with self._active_lock:
                cancel_event = self._active_processes.get(run_id)
            self.store.transition(run_id, "cancelling", actor=operator_id, reason="operator cancellation requested", expected_instance_id=expected_instance_id, expected_revision=expected_revision)
            if cancel_event is not None:
                cancel_event.set()
                result = self.store.get(run_id) or record
            else:
                result = self.store.transition(run_id, "cancelled", actor=operator_id, reason="no live process was attached")
        elif status == "cancelling":
            with self._active_lock:
                cancel_event = self._active_processes.get(run_id)
            if cancel_event is not None:
                cancel_event.set()
            result = self.store.get(run_id) or record
        elif status in {"awaiting_approval", "approved", "prepared", "interrupted"}:
            result = self.store.transition(run_id, "cancelled", actor=operator_id, reason="operator cancellation requested", expected_instance_id=expected_instance_id, expected_revision=expected_revision)
        else:
            raise PortableExecutionError(f"run cannot be cancelled from {status}")
        try:
            self.store.update(run_id, runBundle=self._write_run_bundle(result))
            result = self.store.get(run_id) or result
        except Exception:  # noqa: BLE001 - termination state remains authoritative
            pass
        return result

    @staticmethod
    def _copy_tree_without_symlinks(source: Path, destination: Path) -> None:
        """Create a staging copy while rejecting symlink-based escapes."""

        for candidate in source.rglob("*"):
            if candidate.is_symlink():
                raise PortableExecutionError(f"staging source contains a symlink: {candidate.relative_to(source)}")
        shutil.copytree(source, destination, symlinks=False)

    @staticmethod
    def _worker_process_observation(
        *,
        launch_status: str,
        result: ProcessResult | None = None,
        result_artifact_present: bool = False,
    ) -> dict[str, Any]:
        """Return the complete allowlist for durable worker diagnostics.

        ProcessResult intentionally contains command and captured output.  Those
        fields must remain transient: a governed run persists only termination
        facts, never prompts, model output, standard streams, argv, or env.
        """

        if launch_status not in {"not_started", "launched"}:
            raise ValueError("worker launch status is invalid")
        returncode = result.returncode if result is not None else None
        return {
            "launchStatus": launch_status,
            "exitCode": returncode if isinstance(returncode, int) and returncode >= 0 else None,
            "terminatingSignal": -returncode if isinstance(returncode, int) and returncode < 0 else None,
            "durationMs": result.duration_ms if result is not None else None,
            "timedOut": result.timed_out if result is not None else False,
            "cancelled": result.cancelled if result is not None else False,
            "outputLimited": result.output_limited if result is not None else False,
            "resultArtifactPresent": result_artifact_present,
        }

    @staticmethod
    def _classify_worker_termination(
        process: dict[str, Any], *, invalid_result: bool = False,
    ) -> str:
        """Choose one mutually-exclusive public termination classification."""

        if process.get("launchStatus") != "launched":
            return "launch_failure"
        if process.get("timedOut"):
            return "timeout"
        if process.get("cancelled"):
            return "cancelled"
        if process.get("outputLimited"):
            return "output_limit"
        if process.get("exitCode") not in {None, 0} or process.get("terminatingSignal") is not None:
            return "worker_nonzero_exit"
        if not process.get("resultArtifactPresent"):
            return "result_artifact_missing"
        if invalid_result:
            return "result_artifact_invalid"
        return "success"

    def _record_worker_started(self, run_id: str) -> Any:
        """Build the pre-exec callback that durably proves a worker launched."""

        def started(_identity: ProcessIdentity) -> None:
            # PID/PGID/start ticks are intentionally *not* retained here.  The
            # worker is staging-only and this record is a termination receipt,
            # not a process-control ledger.
            self.store.update(
                run_id,
                process=self._worker_process_observation(launch_status="launched"),
            )

        return started

    def _execute_in_staging(self, record: dict[str, Any], root: Path, source_root: Path, *, cancel_event: threading.Event | None = None) -> tuple[dict[str, Any], list[dict[str, Any]], dict[str, Any]]:
        """Execute an action without mounting or passing canonical state to an engine."""

        spec = AgentRunSpec.from_dict(record["runSpec"])
        timeout = float(spec.budgets["timeSeconds"])
        output_limit = min(max(int(spec.budgets["steps"]), 1) * 256 * 1024, 4 * 1024 * 1024)
        policy = SandboxPolicy(self.app.layout.operations_root, network="disabled", output_limit_bytes=output_limit, timeout_seconds=int(timeout))
        boundary = SandboxBoundary(policy)
        # This path starts a host process in a disposable copy.  A Podman
        # availability probe would not prove that this particular process was
        # containerized, so retain only the staging-copy observation here.
        sandbox_observation = boundary.observe_staging_copy().to_dict()
        executor = record.get("executorCommand")
        if not isinstance(executor, str) or not executor or Path(executor).is_absolute() or ".." in Path(executor).parts:
            raise PortableExecutionError("application executor is missing or unsafe")
        application_prefix = str(record.get("applicationId", "")) + "."
        action_identifier = str(record.get("actionId", ""))
        if not application_prefix.strip(".") or not action_identifier.startswith(application_prefix):
            raise PortableExecutionError("application action identity is not bound to its application")
        action_name = action_identifier[len(application_prefix):].rsplit("/v1", 1)[0]
        if not action_name or "/" in action_name or ".." in action_name:
            raise PortableExecutionError("application action name is unsafe")
        inputs_json = json.dumps(record["inputs"], sort_keys=True, separators=(",", ":"))
        # Host JSONL can contain agent messages.  It is parsed transiently for
        # a typed result but is never retained in the run record or bundle.
        events: list[dict[str, Any]] = []
        process = self._worker_process_observation(launch_status="not_started")
        started = self._record_worker_started(str(record["runId"]))
        with boundary.staging() as staging:
            staged_instance = staging / "instance"
            staged_source = staging / "application"
            self._copy_tree_without_symlinks(root, staged_instance)
            self._copy_tree_without_symlinks(source_root, staged_source)
            context_path = staging / "context/state-pack.txt"
            context_path.parent.mkdir(parents=True, exist_ok=True)
            context_path.write_text(str(record.get("statePack", {}).get("text", "")), encoding="utf-8")
            (staging / "home").mkdir()
            (staging / "tmp").mkdir()
            sandbox_environment = boundary.environment({"HOME": str(staging / "home"), "TMPDIR": str(staging / "tmp")})
            if record["engine"]["engineId"] == "codex":
                adapter = CodexAdapter()
                try:
                    result = adapter.execute(
                        spec, staging, cancel_event=cancel_event,
                        environment=sandbox_environment, on_started=started,
                    )
                except (OSError, ProcessRuntimeError, RuntimeError) as exc:
                    raise WorkerExecutionError("launch_failure", process, "worker could not be launched") from exc
                process = self._worker_process_observation(launch_status="launched", result=result)
                self.store.update(str(record["runId"]), process=process)
                classification = self._classify_worker_termination(process)
                if classification != "result_artifact_missing":
                    if classification != "success":
                        raise WorkerExecutionError(classification, process, "worker terminated before producing a result")
                try:
                    decoded_events = decode_jsonl(result.stdout)
                except Exception as exc:  # noqa: BLE001 - malformed engine output is a typed run failure
                    raise WorkerExecutionError("result_artifact_invalid", process, "worker emitted an invalid typed result") from exc
                artifact = staging / "artifacts/result.json"
                if artifact.is_file():
                    process = self._worker_process_observation(
                        launch_status="launched", result=result,
                        result_artifact_present=True,
                    )
                    self.store.update(str(record["runId"]), process=process)
                    try:
                        value = json.loads(artifact.read_text(encoding="utf-8"))
                    except (OSError, json.JSONDecodeError) as exc:
                        raise WorkerExecutionError("result_artifact_invalid", process, "worker result artifact is invalid") from exc
                else:
                    final_events = [event for event in decoded_events if event.get("type") in {"stateport.result", "result"} and isinstance(event.get("result"), dict)]
                    if not final_events:
                        raise WorkerExecutionError("result_artifact_missing", process, "worker did not produce the required typed result artifact")
                    value = final_events[-1]["result"]
                    process = self._worker_process_observation(
                        launch_status="launched", result=result,
                        result_artifact_present=True,
                    )
                    self.store.update(str(record["runId"]), process=process)
            else:
                command = ["python3", str(staged_source / executor), "--root", str(staged_instance), "--action", action_name, "--inputs", inputs_json]
                try:
                    process_result = run_process(
                        ProcessSpec(
                            tuple(command), staged_source, timeout_seconds=timeout,
                            max_output_bytes=output_limit, environment=sandbox_environment,
                            on_started=started,
                        ),
                        cancel_event=cancel_event,
                    )
                except (OSError, ProcessRuntimeError) as exc:
                    raise WorkerExecutionError("launch_failure", process, "worker could not be launched") from exc
                process = self._worker_process_observation(launch_status="launched", result=process_result)
                self.store.update(str(record["runId"]), process=process)
                classification = self._classify_worker_termination(process)
                if classification != "result_artifact_missing":
                    if classification != "success":
                        raise WorkerExecutionError(classification, process, "worker terminated before producing a result")
                try:
                    value = json.loads(process_result.stdout)
                except json.JSONDecodeError as exc:
                    raise WorkerExecutionError("result_artifact_invalid", process, "worker emitted an invalid typed result") from exc
                process = self._worker_process_observation(
                    launch_status="launched", result=process_result,
                    result_artifact_present=True,
                )
                self.store.update(str(record["runId"]), process=process)
        if not isinstance(value, dict):
            raise WorkerExecutionError("result_artifact_invalid", process, "worker result artifact is invalid")
        return value, events, process

    @staticmethod
    def _engine_result(
        record: dict[str, Any], *, execution_status: str,
        termination_classification: str, process: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Build and validate the engine-neutral result envelope for every termination."""

        if termination_classification not in TERMINATION_CLASSIFICATIONS:
            raise ValueError("termination classification is invalid")
        spec = AgentRunSpec.from_dict(record["runSpec"])
        engine = record.get("engine", {})
        process_observation = dict(process or {})
        sandbox_observation = process_observation.pop("sandbox", None)
        if not isinstance(sandbox_observation, dict):
            sandbox_observation = {
                "executionBoundary": "staging_copy_only",
                "containerEnforced": False,
                "networkIsolation": "unproven",
                "canonicalAccessIsolation": "unproven",
            }
        value = {
            "formatVersion": "stateport.run-result/v1",
            "runId": spec.run_id,
            "runSpecDigest": spec.digest,
            "backend": {"id": spec.backend_id, "adapter": {"id": spec.adapter_id, "version": spec.adapter_version}},
            "model": spec.model_identifier,
            "authenticationRouteClass": spec.authentication_route_class,
            "statePack": {"reference": spec.statepack_reference, "digest": spec.statepack_digest},
            "toolPolicy": {"permittedCapabilities": list(spec.permitted_capabilities)},
            "sandbox": {"profile": spec.sandbox_profile, **sandbox_observation, "process": process_observation},
            "executionStatus": execution_status,
            "verificationStatus": "synthetic_test_only" if spec.backend_id in {"synthetic", "api-native"} else "host_observed",
            "timestamps": {"startedAt": record.get("requestedAt", _now()), "finishedAt": _now()},
            "failureClassification": None if termination_classification == "success" else termination_classification,
            "terminationClassification": termination_classification,
            "usage": {"token": {"quality": "unavailable", "value": None}, "cost": {"quality": "unavailable", "value": None}},
            "changedFiles": [],
            "validationOutcomes": [{"id": "typed-action-result", "status": "passed"}] if execution_status == "completed" else [],
            "producedArtifacts": ["execution/result.json"] if execution_status == "completed" else [],
            "approvalReference": (record.get("approval") or {}).get("approvalDigest") if isinstance(record.get("approval"), dict) else None,
            "auditReferences": [spec.run_id],
            "warnings": list(engine.get("limitations", [])) if isinstance(engine.get("limitations"), list) else [],
            "degradations": list(record.get("negotiation", {}).get("degraded", [])),
        }
        return validate_run_result(value, spec)

    def execute(self, run_id: str, *, expected_instance_id: str | None = None, expected_revision: int | None = None) -> dict[str, Any]:
        record = self.store.require_binding(run_id, expected_instance_id=expected_instance_id, expected_revision=expected_revision)
        if not record or record.get("status") != "approved":
            raise PortableExecutionError("run requires exact approval before execution")
        self.store.transition(run_id, "preparing", expected_instance_id=expected_instance_id, expected_revision=expected_revision)
        self.store.transition(run_id, "prepared")
        self.store.transition(run_id, "running")
        allow_development_candidate = record.get("sourceAccessClass") == "development_candidate"
        root, source_root, descriptor = self._source_root(
            record["instanceId"],
            allow_development_candidate=allow_development_candidate,
        )
        cancel_event = threading.Event()
        with self._active_lock:
            if run_id in self._active_processes:
                raise PortableExecutionError("run already has an active process")
            self._active_processes[run_id] = cancel_event
        process: dict[str, Any] | None = None
        try:
            result, events, process = self._execute_in_staging(record, root, source_root, cancel_event=cancel_event)
            actions = (
                self._actions(record["instanceId"], allow_development_candidate=True)
                if allow_development_candidate
                else self._actions(record["instanceId"])
            )
            action = actions.get(record["actionId"])
            if action is None:
                raise PortableExecutionError("action disappeared from the immutable source")
            if digest(action.to_dict()) != record.get("actionContractDigest"):
                raise PortableExecutionError("application action contract drifted after preparation")
            if digest(descriptor) != record.get("descriptorDigest"):
                raise PortableExecutionError("application descriptor drifted after preparation")
            if self._executor_identity(source_root, action.executor_command) != record.get("executorIdentity"):
                raise PortableExecutionError("application executor drifted after preparation")
            self._validate_result(action, result)
        except WorkerExecutionError as exc:
            process = exc.process
            classification = exc.classification
            target = "timed_out" if classification == "timeout" else "cancelled" if classification == "cancelled" else "failed"
            execution_status = "timed_out" if classification == "timeout" else "cancelled" if classification == "cancelled" else "failed"
            failed = self.store.transition(run_id, target, events=[], diagnostic="worker execution terminated")
            try:
                failed = self.store.update(run_id, process=process)
                failed = self.store.update(run_id, runResult=self._engine_result(
                    failed, execution_status=execution_status,
                    termination_classification=classification, process=process,
                ))
                self.store.update(run_id, runBundle=self._write_run_bundle(failed))
            except Exception:  # noqa: BLE001 - preserve the primary termination result
                pass
            raise PortableExecutionError("worker execution terminated") from exc
        except (OSError, ProcessRuntimeError, subprocess.SubprocessError, json.JSONDecodeError, PortableExecutionError) as exc:
            process = process or self._worker_process_observation(launch_status="not_started")
            classification = self._classify_worker_termination(
                process, invalid_result=process.get("launchStatus") == "launched",
            )
            failed = self.store.transition(run_id, "failed", events=[], diagnostic="worker execution failed")
            try:
                failed = self.store.update(run_id, process=process)
                failed = self.store.update(run_id, runResult=self._engine_result(
                    failed, execution_status="failed",
                    termination_classification=classification, process=process,
                ))
                self.store.update(run_id, runBundle=self._write_run_bundle(failed))
            except Exception:  # noqa: BLE001 - preserve the primary execution failure
                pass
            raise PortableExecutionError("worker execution failed") from exc
        finally:
            with self._active_lock:
                self._active_processes.pop(run_id, None)
        after = self._state_digest(root)
        result["canonicalStateUnchanged"] = after == record["canonicalStateBefore"]
        result["engineIdentity"] = {"id": record["engine"]["engineId"], "adapter": record["engine"]["adapterId"], "model": record["engine"]["modelIdentity"]}
        result["latencyMs"] = process.get("durationMs")
        result["usageAvailable"] = isinstance(result.get("usage"), dict)
        observation = process.get("sandbox") if isinstance(process.get("sandbox"), dict) else {}
        result["sandbox"] = {
            **observation,
            "executionBoundary": "staging_copy_only",
            "containerEnforced": False,
            "networkIsolation": "unproven",
            "canonicalAccessIsolation": "unproven",
        }
        current = self.store.update(run_id, events=events, process=process)
        current = self.store.update(run_id, runResult=self._engine_result(current, execution_status="completed", termination_classification="success", process=process))
        current = self.store.transition(run_id, "completed", result=result, canonicalStateAfter=after)
        self.store.transition(run_id, "result_validating")
        proposals = result.get("stateChangeProposals") or []
        if proposals:
            try:
                if action.mutation_policy != "propose_only":
                    raise PortableExecutionError("action is not permitted to propose canonical mutation")
                if not isinstance(proposals, list) or len(proposals) != 1:
                    raise PortableExecutionError("exactly one typed state-change proposal is required")
                proposal = proposals[0]
                paths = self._validate_proposal_authority(root, descriptor, proposal)
            except PortableExecutionError as exc:
                rejected = self.store.transition(run_id, "result_rejected", diagnostic=str(exc))
                try:
                    self.store.update(run_id, runBundle=self._write_run_bundle(rejected))
                except Exception:  # noqa: BLE001 - rejection remains authoritative
                    pass
                raise
            current = self.store.transition(
                run_id, "state_change_proposed", proposal=proposal,
                proposalDigest=digest(proposal), proposalPaths=list(paths),
            )
        else:
            current = self.store.lifecycle_transition(run_id, "NO_MUTATION", reason="typed result contained no state-change proposal")
            current = self.store.lifecycle_transition(run_id, "CLOSED", reason="run completed without canonical mutation")
        bundle = self._write_run_bundle(self.store.get(run_id) or {})
        self.store.update(run_id, runBundle=bundle)
        return self.inspect(run_id)

    def approve_proposal(self, run_id: str, operator_id: str = "local-operator", *, expected_instance_id: str | None = None, expected_revision: int | None = None) -> dict[str, Any]:
        record = self.store.require_binding(run_id, expected_instance_id=expected_instance_id, expected_revision=expected_revision)
        if not record or record.get("status") != "state_change_proposed":
            raise PortableExecutionError("run has no pending state-change proposal")
        proposal = record.get("proposal")
        proposal_digest = digest(proposal)
        if proposal_digest != record.get("proposalDigest"):
            raise PortableExecutionError("pending proposal identity drifted before approval")
        approval = {
            "formatVersion": "stateport.proposal-approval/v1", "runId": run_id,
            "proposalDigest": proposal_digest,
            "canonicalStateBefore": record.get("canonicalStateBefore"),
            "baseGit": record.get("baseGit"),
            "executorDigest": (record.get("executorIdentity") or {}).get("digest"),
            "paths": list(record.get("proposalPaths") or []),
            "operatorId": operator_id, "approvedAt": _now(),
        }
        approval["approvalDigest"] = digest(approval)
        return self.store.transition(
            run_id, "state_change_approved", proposalApproval=approval,
            expected_instance_id=expected_instance_id, expected_revision=expected_revision,
        )

    def reject_proposal(self, run_id: str, operator_id: str = "local-operator", *, expected_instance_id: str | None = None, expected_revision: int | None = None) -> dict[str, Any]:
        self.store.require_binding(run_id, expected_instance_id=expected_instance_id, expected_revision=expected_revision)
        result = self.store.transition(run_id, "state_change_rejected", rejection={"operatorId": operator_id, "rejectedAt": _now()}, expected_instance_id=expected_instance_id, expected_revision=expected_revision)
        return self.store.lifecycle_transition(run_id, "CLOSED", actor=operator_id, reason="proposal rejected")

    @staticmethod
    def _sandbox_python_executable() -> str:
        """Resolve the running system Python inside the read-only sandbox.

        Distribution Python lives below ``/usr/bin`` on the reference host,
        while the official Python container image installs it below
        ``/usr/local/bin``.  Binding ``/usr`` already covers both layouts; a
        fixed ``/usr/bin/python3`` path made every Compose apply fail before
        the application writer could start.
        """

        try:
            executable = Path(sys.executable).resolve(strict=True)
        except OSError as exc:
            raise PortableExecutionError(
                "sandbox Python executable could not be resolved"
            ) from exc
        if (
            not executable.is_file()
            or Path("/usr") not in executable.parents
            or not os.access(executable, os.X_OK)
        ):
            raise PortableExecutionError(
                "sandbox Python executable is outside the read-only system tree"
            )
        return executable.as_posix()

    @staticmethod
    def _bubblewrap_command(
        *, source_root: Path, instance_root: Path, writable_instance: bool,
        working_directory: str, command: tuple[str, ...],
        process_generation: str,
    ) -> tuple[str, ...]:
        executable = probe_executable("bwrap")
        if executable is None:
            raise PortableExecutionError(
                "canonical apply requires the bubblewrap sandbox boundary"
            )
        arguments = [
            executable,
            "--unshare-all", "--die-with-parent", "--new-session",
            "--clearenv",
            "--setenv", "PATH", "/usr/local/bin:/usr/bin:/bin",
            "--setenv", "LD_LIBRARY_PATH", "/usr/local/lib:/usr/lib:/usr/lib64",
            "--setenv", "HOME", "/home",
            "--setenv", "TMPDIR", "/tmp",
            "--setenv", "LANG", "C.UTF-8",
            "--setenv", "LC_ALL", "C.UTF-8",
            "--setenv", "PYTHONDONTWRITEBYTECODE", "1",
            "--setenv", "STATEPORT_PROCESS_GENERATION", process_generation,
            "--ro-bind", "/usr", "/usr",
        ]
        for system_path in ("/lib", "/lib64"):
            if Path(system_path).exists():
                arguments.extend(("--ro-bind", system_path, system_path))
        arguments.extend((
            # A nested Bubblewrap process in the rootless Podman reference
            # environment cannot create fresh proc/dev mounts under the outer
            # SELinux container label.  The action and validator require
            # neither procfs nor the outer container device tree.  Give them
            # only an empty /dev with the four standard character devices.
            "--tmpfs", "/tmp", "--dir", "/home", "--dir", "/dev",
            "--dev-bind", "/dev/null", "/dev/null",
            "--dev-bind", "/dev/zero", "/dev/zero",
            "--dev-bind", "/dev/random", "/dev/random",
            "--dev-bind", "/dev/urandom", "/dev/urandom",
            "--ro-bind", str(source_root), "/application",
            "--bind" if writable_instance else "--ro-bind",
            str(instance_root), "/instance",
            "--chdir", working_directory,
            "--",
            *command,
        ))
        return tuple(arguments)

    def _process_observers(self, run_id: str, phase: str) -> tuple[Any, Any]:
        def started(identity: ProcessIdentity) -> None:
            if (
                identity.process_group_id != identity.pid
                or not isinstance(identity.start_time_ticks, str)
                or not identity.start_time_ticks.isdigit()
                or not isinstance(identity.process_generation, str)
            ):
                raise PortableExecutionError(
                    "sandbox process lacks an exact session-leader identity"
                )
            self.store.update(run_id, applyProcess={
                "phase": phase,
                "state": "active",
                "pid": identity.pid,
                "processGroupId": identity.process_group_id,
                "startTimeTicks": identity.start_time_ticks,
                "processGeneration": identity.process_generation,
                "registeredAt": _now(),
            })

        def finished(identity: ProcessIdentity) -> None:
            record = self.store.get(run_id) or {}
            process = record.get("applyProcess")
            if not isinstance(process, dict) or (
                process.get("pid"), process.get("processGroupId"),
                process.get("startTimeTicks"), process.get("processGeneration"),
                process.get("phase"),
            ) != (
                identity.pid, identity.process_group_id,
                identity.start_time_ticks, identity.process_generation, phase,
            ):
                raise PortableExecutionError("sandbox process completion identity drifted")
            completed = dict(process)
            completed.update({"state": "reaped", "finishedAt": _now()})
            self.store.update(run_id, applyProcess=completed)

        return started, finished

    def _run_post_apply_validation(
        self, root: Path, source_root: Path, descriptor: dict[str, Any],
        runtime: Path, run_id: str,
    ) -> dict[str, Any]:
        command_text = descriptor.get("validationCommand")
        if not isinstance(command_text, str) or not command_text.strip():
            raise PortableExecutionError("application lacks a StatePort-selected post-apply validator")
        try:
            command = tuple(shlex.split(command_text))
        except ValueError as exc:
            raise PortableExecutionError("application validation command is invalid") from exc
        if not command:
            raise PortableExecutionError("application validation command is empty")
        environment = filtered_environment(
            allow=("PATH", "LANG", "LC_ALL", "PYTHONDONTWRITEBYTECODE"),
            overrides={
                "PYTHONDONTWRITEBYTECODE": "1",
            },
        )
        if command[0] in {"python", "python3"}:
            command = (self._sandbox_python_executable(), *command[1:])
        process_generation = "generation." + secrets.token_hex(32)
        sandboxed = self._bubblewrap_command(
            source_root=source_root,
            instance_root=root,
            writable_instance=False,
            working_directory="/instance",
            command=command,
            process_generation=process_generation,
        )
        started, finished = self._process_observers(run_id, "post_apply_validation")
        result = run_process(ProcessSpec(
            sandboxed, runtime, timeout_seconds=30, max_output_bytes=65_536,
            environment=environment, on_started=started, on_finished=finished,
            process_generation=process_generation,
        ))
        if not result.ok:
            raise PortableExecutionError("StatePort-selected post-apply validation failed")
        return {
            "status": "passed", "commandDigest": digest(list(command)),
            "returncode": result.returncode, "durationMs": result.duration_ms,
            "outputLimited": result.output_limited, "cleanup": result.cleanup,
            "sandbox": {
                "engine": "bubblewrap", "network": "disabled_namespace",
                "instanceMount": "read_only", "sourceMount": "read_only",
                "hostHomeMount": "absent", "hostContainerSocket": "absent",
            },
        }

    def _rollback_apply(
        self, run_id: str, root: Path, before: Any, *, diagnostic: str,
        snapshot_key: str | None = None,
    ) -> None:
        rollback: dict[str, Any]
        try:
            restore_snapshot(root, before)
            restored = digest_snapshot(snapshot_files(root))
            if restored != digest_snapshot(before):
                raise PortableExecutionError("rollback digest did not match the captured snapshot")
            rollback = {
                "status": "completed", "byteIdentical": True,
                "restoredDigest": restored,
            }
            current = self.store.get(run_id) or {}
            transaction = dict(current.get("applyTransaction") or {})
            transaction["rollbackStatus"] = "completed"
            failed = self.store.transition(
                run_id, "apply_failed", diagnostic=diagnostic, rollback=rollback,
                canonicalStateAfter=restored, applyTransaction=transaction,
            )
        except Exception as rollback_error:  # noqa: BLE001 - retain explicit unknown state
            rollback = {
                "status": "failed", "byteIdentical": False,
                "operatorInspectionRequired": True,
            }
            failed = self.store.transition(
                run_id, "failed", diagnostic="canonical rollback could not be proven",
                rollback=rollback,
            )
            raise PortableExecutionError("canonical rollback could not be proven") from rollback_error
        try:
            self.store.update(
                run_id,
                runBundle=self._write_run_bundle(
                    failed, suffix="-apply-failed", state_after=rollback["restoredDigest"],
                ),
            )
        except Exception:  # noqa: BLE001 - rollback truth remains authoritative
            pass
        if snapshot_key is not None:
            try:
                self._discard_apply_snapshot(snapshot_key)
            except PortableExecutionError:
                self.store.update(run_id, applySnapshotDisposition="retained_cleanup_failed")

    def apply_proposal(self, run_id: str, *, expected_instance_id: str | None = None, expected_revision: int | None = None) -> dict[str, Any]:
        record = self.store.require_binding(run_id, expected_instance_id=expected_instance_id, expected_revision=expected_revision)
        if not record or record.get("status") != "state_change_approved":
            raise PortableExecutionError("proposal requires exact approval before apply")
        allow_development_candidate = record.get("sourceAccessClass") == "development_candidate"
        root, source_root, descriptor = self._source_root(
            record["instanceId"],
            allow_development_candidate=allow_development_candidate,
        )
        try:
            lease = InstanceLease(
                self.app.layout.operations_root / "leases", root,
                owner=f"portable-apply:{run_id}",
            )
        except InstanceLeaseError as exc:
            raise PortableExecutionError("instance writer lease is unavailable") from exc
        try:
            with lease:
                record = self.store.get(run_id) or {}
                if record.get("status") != "state_change_approved":
                    raise PortableExecutionError("proposal approval changed before apply")
                if self._instance_requires_operator_recovery(record.get("instanceId", "")):
                    raise PortableExecutionError(
                        "instance remains quarantined pending explicit operator recovery"
                    )
                base_git = record.get("baseGit")
                if not isinstance(base_git, str) or not re.fullmatch(r"[0-9a-f]{40,64}", base_git):
                    raise PortableExecutionError(
                        "canonical apply requires a non-null exact base Git SHA"
                    )
                approval = record.get("proposalApproval")
                if not isinstance(approval, dict):
                    raise PortableExecutionError("proposal lacks exact operator approval")
                supplied_approval_digest = approval.get("approvalDigest")
                unsigned_approval = dict(approval)
                unsigned_approval.pop("approvalDigest", None)
                if supplied_approval_digest != digest(unsigned_approval):
                    raise PortableExecutionError("proposal approval digest is invalid")
                proposal = record.get("proposal")
                if not isinstance(proposal, dict) or digest(proposal) != record.get("proposalDigest"):
                    raise PortableExecutionError("approved proposal identity drifted")
                paths = self._validate_proposal_authority(root, descriptor, proposal)
                if list(paths) != record.get("proposalPaths") or approval.get("paths") != list(paths):
                    raise PortableExecutionError("approved proposal path scope drifted")
                if approval.get("proposalDigest") != record.get("proposalDigest"):
                    raise PortableExecutionError("approval is not bound to the proposal")
                if approval.get("baseGit") != base_git:
                    raise PortableExecutionError("proposal approval is not bound to the base Git SHA")
                if digest(descriptor) != record.get("descriptorDigest"):
                    raise PortableExecutionError("application descriptor drifted before apply")
                current_actions = (
                    self._actions(record["instanceId"], allow_development_candidate=True)
                    if allow_development_candidate
                    else self._actions(record["instanceId"])
                )
                current_action = current_actions.get(record.get("actionId"))
                if current_action is None or digest(current_action.to_dict()) != record.get("actionContractDigest"):
                    raise PortableExecutionError("application action contract drifted before apply")
                inspected = self.app.inspect(record["instanceId"])
                current_source = inspected.get("source") if isinstance(inspected.get("source"), dict) else {}
                if current_source != record.get("sourceIdentity"):
                    raise PortableExecutionError("application source identity drifted before apply")
                executor_identity = self._executor_identity(source_root, record.get("executorCommand"))
                if executor_identity != record.get("executorIdentity") or approval.get("executorDigest") != executor_identity["digest"]:
                    raise PortableExecutionError("approved application executor identity drifted")
                before = snapshot_files(root)
                before_digest = digest_snapshot(before)
                if before_digest != record.get("canonicalStateBefore"):
                    self.store.transition(run_id, "failed", diagnostic="canonical state changed after proposal")
                    raise PortableExecutionError("proposal is stale because canonical state changed")
                if self._git_identity(root) != base_git:
                    self.store.transition(run_id, "failed", diagnostic="instance Git identity changed after proposal")
                    raise PortableExecutionError("proposal base Git identity drifted")
                snapshot_key, snapshot_digest = self._persist_apply_snapshot(run_id, before)
                try:
                    self.store.transition(
                        run_id, "applying",
                        expected_instance_id=expected_instance_id,
                        expected_revision=expected_revision,
                        applySupervisor=self._current_supervisor(),
                        applyProcess={"phase": "writer", "state": "pending_gate"},
                        applyTransaction={
                            "formatVersion": "stateport.filesystem-transaction/v1",
                            "beforeDigest": before_digest,
                            "baseGit": base_git,
                            "paths": list(paths),
                            "sideEffectClassification": "filesystem_transaction",
                            "enforcement": "sandboxed_staging_then_trusted_commit",
                            "snapshotKey": snapshot_key,
                            "snapshotDigest": snapshot_digest,
                            "rollbackStatus": "prepared_fsynced",
                        },
                    )
                except Exception:
                    self._discard_apply_snapshot(snapshot_key)
                    raise
                runtime_parent = self.app.layout.operations_root / "apply-runtime"
                runtime_parent.mkdir(parents=True, exist_ok=True, mode=0o700)
                try:
                    with TemporaryWorkspace(runtime_parent, prefix=f".{run_id}-") as runtime:
                        staged_instance = runtime / "instance"
                        self._copy_tree_without_symlinks(root, staged_instance)
                        environment = filtered_environment(
                            allow=("PATH", "LANG", "LC_ALL", "PYTHONDONTWRITEBYTECODE"),
                            overrides={"PYTHONDONTWRITEBYTECODE": "1"},
                        )
                        application_command = (
                            self._sandbox_python_executable(),
                            "/application/" + executor_identity["path"],
                            "--root", "/instance", "--apply-proposal",
                        )
                        process_generation = "generation." + secrets.token_hex(32)
                        command = self._bubblewrap_command(
                            source_root=source_root,
                            instance_root=staged_instance,
                            writable_instance=True,
                            working_directory="/application",
                            command=application_command,
                            process_generation=process_generation,
                        )
                        started, finished = self._process_observers(run_id, "writer")
                        process = run_process(ProcessSpec(
                            command, runtime, timeout_seconds=30,
                            max_output_bytes=65_536, environment=environment,
                            stdin_text=json.dumps(proposal, sort_keys=True, separators=(",", ":")),
                            on_started=started, on_finished=finished,
                            process_generation=process_generation,
                        ))
                        if not process.ok:
                            raise PortableExecutionError("application transactional writer failed")
                        try:
                            raw_receipt = json.loads(process.stdout)
                        except json.JSONDecodeError as exc:
                            raise PortableExecutionError("application writer emitted malformed receipt JSON") from exc
                        self._remove_transaction_ephemera(staged_instance, before, descriptor)
                        after_writer = snapshot_files(staged_instance)
                        observed_after = digest_snapshot(after_writer)
                        changes = diff_snapshots(before, after_writer)
                        if set(changes["filesChanged"]) != set(paths):
                            raise PortableExecutionError("application writer changed paths outside the approved transaction")
                        staged_git = self._git_identity(staged_instance)
                        if staged_git != base_git:
                            raise PortableExecutionError("sandbox writer changed the instance Git base")
                        receipt = self._validate_application_receipt(
                            raw_receipt, proposal, observed_after,
                            base_git=base_git, final_git=staged_git,
                        )
                        validation_before = observed_after
                        validation = self._run_post_apply_validation(
                            staged_instance, source_root, descriptor, runtime, run_id,
                        )
                        self._remove_transaction_ephemera(staged_instance, before, descriptor)
                        validated_snapshot = snapshot_files(staged_instance)
                        validation_after = digest_snapshot(validated_snapshot)
                        if validation_after != validation_before:
                            raise PortableExecutionError("post-apply validator mutated canonical state")
                        # Only StatePort writes canonical state.  The untrusted
                        # application and validator saw a bubblewrap-confined
                        # staging copy with no canonical or host-home mount.
                        if (
                            digest_snapshot(snapshot_files(root)) != before_digest
                            or self._git_identity(root) != base_git
                        ):
                            raise PortableExecutionError(
                                "canonical state drifted while the apply lease was held"
                            )
                        restore_snapshot(root, validated_snapshot)
                        canonical_after = digest_snapshot(snapshot_files(root))
                        if canonical_after != validation_after or self._git_identity(root) != base_git:
                            raise PortableExecutionError("trusted canonical commit did not match the verified staging snapshot")
                        transaction = {
                            "formatVersion": "stateport.filesystem-transaction/v1",
                            "beforeDigest": before_digest, "afterDigest": canonical_after,
                            "baseGit": base_git, "finalGit": base_git,
                            "paths": list(paths), "changedPaths": list(changes["filesChanged"]),
                            "sideEffectClassification": "filesystem_transaction",
                            "enforcement": "sandboxed_staging_then_trusted_commit",
                            "snapshotKey": snapshot_key,
                            "snapshotDigest": snapshot_digest,
                            "sandbox": {
                                "engine": "bubblewrap",
                                "canonicalMount": "absent_from_untrusted_processes",
                                "stagingMount": "writable_writer_read_only_validator",
                                "sourceMount": "read_only",
                                "network": "disabled_namespace",
                                "hostHomeMount": "absent",
                                "hostContainerSocket": "absent",
                                "privileged": False,
                            },
                            "writer": {
                                "returncode": process.returncode, "durationMs": process.duration_ms,
                                "timedOut": process.timed_out, "outputLimited": process.output_limited,
                                "cleanup": process.cleanup,
                            },
                            "rollbackStatus": "not_required",
                        }
                        self.store.transition(
                            run_id, "applied", receipt=receipt,
                            applyTransaction=transaction, canonicalStateAfter=canonical_after,
                        )
                        self.store.lifecycle_transition(
                            run_id, "POST_VALIDATED", reason="StatePort-selected validation passed",
                            postApplyValidation=validation,
                        )
                        post_validated = self.store.get(run_id) or {}
                        bundle = self._write_run_bundle(
                            post_validated,
                            suffix="-applied",
                            state_after=canonical_after,
                        )
                        closing = self.store.update(run_id, appliedRunBundle=bundle)
                        closure_receipt = self._build_run_closure_receipt(closing)
                        self.store.lifecycle_transition(
                            run_id,
                            "CLOSED",
                            reason="post-apply evidence sealed",
                            closureReceipt=closure_receipt,
                            receiptId=closure_receipt["receiptId"],
                        )
                        try:
                            self._discard_apply_snapshot(snapshot_key)
                            self.store.update(run_id, applySnapshotDisposition="destroyed_after_commit")
                        except PortableExecutionError:
                            self.store.update(run_id, applySnapshotDisposition="retained_cleanup_failed")
                except Exception as exc:
                    self._rollback_apply(
                        run_id, root, before,
                        diagnostic="filesystem transaction failed and was restored",
                        snapshot_key=snapshot_key,
                    )
                    if isinstance(exc, PortableExecutionError):
                        raise
                    raise PortableExecutionError("filesystem transaction failed") from exc
        except InstanceLeaseError as exc:
            raise PortableExecutionError("instance already has an active writer lease") from exc
        return self.inspect(run_id)

    def _write_run_bundle(self, record: dict[str, Any], *, suffix: str = "", state_after: str | None = None) -> dict[str, Any]:
        """Persist a redacted immutable audit bundle for every completed run."""

        run_id = str(record.get("runId", ""))
        if not run_id:
            raise PortableExecutionError("cannot bundle an unidentified run")
        destination = self.bundle_root / f"{run_id}{suffix}"
        artifacts: dict[str, Any] = {
            "identities/package.json": {"applicationId": record.get("applicationId"), "sourceRevision": record.get("runSpec", {}).get("instance", {}).get("sourceRevision"), "sourceIdentity": record.get("sourceIdentity", {})},
            "identities/instance.json": {"instanceId": record.get("instanceId"), "sourceRevision": record.get("runSpec", {}).get("instance", {}).get("sourceRevision"), "sourceIdentity": record.get("sourceIdentity", {}), "baseGit": record.get("baseGit"), "finalGit": (record.get("receipt") or {}).get("finalGit")},
            "identities/state-before.json": {"digest": record.get("canonicalStateBefore")},
            "action/descriptor.json": {"applicationId": record.get("applicationId"), "actionId": record.get("actionId")},
            "action/input.json": record.get("inputs", {}),
            "context/policy.json": record.get("statePack", {}).get("manifest", {}),
            "context/included.json": record.get("statePack", {}).get("manifest", {}).get("included", []),
            "context/excluded.json": record.get("statePack", {}).get("manifest", {}).get("excluded", []),
            "context/provenance.json": {"digest": record.get("statePack", {}).get("digest")},
            "context/state-pack.txt": record.get("statePack", {}).get("text", ""),
            "execution/agent-run-spec.json": record.get("runSpec", {}),
            "execution/capability-negotiation.json": record.get("negotiation", {}),
            "execution/adapter.json": record.get("engine", {}),
            "execution/engine.json": record.get("engine", {}),
            "execution/events.jsonl": "".join(json.dumps(event, sort_keys=True) + "\n" for event in record.get("events", [])),
            "execution/result.json": record.get("result") or {"status": record.get("status")},
            "execution/run-result.json": record.get("runResult") or {},
            # RunResult uses the contract names `token` and `cost`; the
            # bundle writer uses telemetry-specific names so the generic
            # secret scanner cannot confuse a measured token count with an
            # authentication token.
            "execution/usage.json": {
                "tokenMetric": (record.get("runResult") or {}).get("usage", {}).get("token", {"quality": "unavailable", "value": None}),
                "costMetric": (record.get("runResult") or {}).get("usage", {}).get("cost", {"quality": "unavailable", "value": None}),
            },
            "execution/process.json": record.get("process", {}),
            "execution/sandbox.json": (record.get("result") or {}).get("sandbox", {}) if isinstance(record.get("result"), dict) else {},
            "execution/degradations.json": {"capability": record.get("negotiation", {}).get("degraded", []), "engine": record.get("engine", {}).get("limitations", [])},
            "execution/lifecycle.json": {"status": record.get("status"), "lifecycleState": record.get("lifecycleState"), "lifecycleVersion": record.get("lifecycleVersion")},
            "approvals/run-approval.json": record.get("approval") or {},
            "validation/pre-run.json": {"stateDigest": record.get("canonicalStateBefore")},
            "validation/post-run.json": {"stateDigest": record.get("canonicalStateAfter"), "unchanged": record.get("result", {}).get("canonicalStateUnchanged") if isinstance(record.get("result"), dict) else None},
            "validation/post-apply.json": record.get("postApplyValidation", {"status": "passed" if record.get("receipt") else "not_applied", "receipt": record.get("receipt")}),
            "identities/state-after.json": {"digest": state_after or record.get("canonicalStateAfter")},
        }
        if record.get("proposal") is not None:
            artifacts["mutation/proposal.json"] = record["proposal"]
            artifacts["approvals/proposal-approval.json"] = record.get("proposalApproval", {})
        if record.get("receipt") is not None:
            artifacts["mutation/apply-receipt.json"] = record["receipt"]
        return RunBundleWriter(destination).write(
            manifest={
                "runId": run_id,
                "instanceId": record.get("instanceId"),
                "applicationId": record.get("applicationId"),
                "status": record.get("status"),
                "runSpecDigest": record.get("runSpecDigest"),
                "stateBefore": record.get("canonicalStateBefore"),
                "stateAfter": state_after or record.get("canonicalStateAfter"),
                "baseGit": record.get("baseGit"),
                "finalGit": (record.get("receipt") or {}).get("finalGit"),
                "sourceIdentity": record.get("sourceIdentity", {}),
                "lifecycleState": record.get("lifecycleState"),
            },
            artifacts=artifacts,
        )

    def inspect(self, run_id: str) -> dict[str, Any]:
        record = self.store.get(run_id)
        if record is None:
            raise PortableExecutionError("unknown run")
        return {"run": record}

    def bundle(self, run_id: str, *, applied: bool | None = None) -> dict[str, Any]:
        record = self.store.get(run_id)
        if record is None:
            raise PortableExecutionError("unknown run")
        use_applied = (
            isinstance(record.get("appliedRunBundle"), dict)
            if applied is None
            else applied
        )
        reference = (
            record.get("appliedRunBundle")
            if use_applied
            else record.get("runBundle")
        )
        if not isinstance(reference, dict) or not isinstance(reference.get("path"), str):
            raise PortableExecutionError("run has no immutable RunBundle")
        path = Path(reference["path"]).resolve()
        path.relative_to(self.bundle_root.resolve())
        return {
            "runId": run_id,
            "applied": use_applied,
            "bundle": reference,
            "verification": verify_bundle(path),
        }

    def statebench(self, run_id: str, *, applied: bool | None = None) -> dict[str, Any]:
        bundle = self.bundle(run_id, applied=applied)
        try:
            from statebench import ingest_run_bundle
        except ModuleNotFoundError as exc:  # pragma: no cover - service packaging guard
            raise PortableExecutionError("StateBench ingestion is unavailable in this service process") from exc
        return {
            "runId": run_id,
            "applied": bundle["applied"],
            "row": ingest_run_bundle(bundle["bundle"]["path"]),
        }

    def statebench_matrix(self, *, maximum_rows: int = 100) -> dict[str, Any]:
        """Return a bounded, path-free operator projection of verified bundles.

        This is evidence inspection, not a ranking surface. Invalid or
        unverified producer artifacts never become matrix rows and their
        filesystem locations are never returned to the browser.
        """

        if isinstance(maximum_rows, bool) or not isinstance(maximum_rows, int) or not 1 <= maximum_rows <= 100:
            raise PortableExecutionError("StateBench matrix row bound is invalid")
        try:
            from statebench import RunBundleIngestionError, ingest_run_bundle
        except ModuleNotFoundError as exc:  # pragma: no cover - service packaging guard
            raise PortableExecutionError("StateBench ingestion is unavailable in this service process") from exc
        root = self.bundle_root.resolve()
        rows: list[dict[str, Any]] = []
        rejected = 0
        candidates = sorted(
            self.store.all(),
            key=lambda item: (str(item.get("applicationId", "")), str(item.get("runId", ""))),
        )
        for record in candidates:
            reference = record.get("appliedRunBundle") or record.get("runBundle")
            raw_path = reference.get("path") if isinstance(reference, dict) else None
            if not isinstance(raw_path, str):
                continue
            try:
                path = Path(raw_path)
                if path.is_symlink():
                    raise RunBundleIngestionError("RunBundle path is unsafe")
                resolved = path.resolve(strict=True)
                resolved.relative_to(root)
                row = ingest_run_bundle(resolved)
                if row.get("integrityStatus") != "verified":
                    raise RunBundleIngestionError("RunBundle integrity is not verified")
                projected = _public_statebench_row(row)
            except (OSError, ValueError, PortableExecutionError, RunBundleIngestionError):
                rejected += 1
                continue
            rows.append(projected)
        rows.sort(key=lambda row: (str(row.get("applicationId")), str(row.get("engineId")), str(row.get("runId"))))
        total = len(rows)
        rows = rows[:maximum_rows]
        return {
            "formatVersion": "stateport.platform-statebench-view/v1",
            "rows": rows,
            "verifiedRowCount": total,
            "rejectedOrUnverifiedCount": rejected,
            "truncated": total > len(rows),
            "hardOutcomeOnly": True,
            "authoritativePerformanceClaim": False,
            "calibrationMeaning": "Harness behavior only; comparative performance is not established.",
        }

    def history(self, instance_id: str) -> list[dict[str, Any]]:
        return self.store.all(instance_id)

    def closure_receipts(self, instance_id: str) -> list[dict[str, Any]]:
        """Return exact persisted closure receipts for the operational index.

        Historical runs without this receipt format are not backfilled with an
        invented closure timestamp. A run that does claim a receipt must still
        match every persisted governed identity.
        """

        receipts: list[dict[str, Any]] = []
        for record in self.store.all(instance_id):
            value = record.get("closureReceipt")
            receipt_id = record.get("receiptId")
            if value is None and receipt_id is None:
                continue
            if (
                not isinstance(value, dict)
                or not isinstance(receipt_id, str)
                or value.get("receiptId") != receipt_id
            ):
                raise PortableExecutionError(
                    "governed run closure receipt identity drifted"
                )
            receipts.append(self._validate_run_closure_receipt(record, value))
        return receipts

    def pending_approval_sources(self, *, maximum_rows: int = 200) -> list[dict[str, Any]]:
        """Return bounded, exact run records whose existing decision routes apply.

        The run store remains the authority.  This method deliberately exposes
        no second approval state machine: callers receive copies of only the
        two persisted states accepted by ``approve_run`` or
        ``approve_proposal``/``reject_proposal``.
        """

        if isinstance(maximum_rows, bool) or not isinstance(maximum_rows, int) or maximum_rows < 1:
            raise ValueError("maximum_rows must be a positive integer")
        pending: list[dict[str, Any]] = []
        for record in self.store.all():
            status = record.get("status")
            if status not in {"awaiting_approval", "state_change_proposed"}:
                continue
            run_id = record.get("runId")
            instance_id = record.get("instanceId")
            revision = record.get("revision")
            requested_at = record.get("requestedAt")
            digest_value = (
                record.get("runSpecDigest")
                if status == "awaiting_approval"
                else record.get("proposalDigest")
            )
            if (
                not isinstance(run_id, str)
                or re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._:-]{0,159}", run_id) is None
                or not isinstance(instance_id, str)
                or re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._:-]{0,127}", instance_id) is None
                or isinstance(revision, bool)
                or not isinstance(revision, int)
                or revision < 0
                or not isinstance(requested_at, str)
                or not isinstance(digest_value, str)
                or re.fullmatch(r"sha256:[0-9a-f]{64}", digest_value) is None
            ):
                continue
            try:
                datetime.fromisoformat(requested_at.replace("Z", "+00:00"))
            except ValueError:
                continue
            if status == "state_change_proposed":
                proposal = record.get("proposal")
                paths = record.get("proposalPaths")
                try:
                    proposal_matches = isinstance(proposal, dict) and digest(proposal) == digest_value
                except (TypeError, ValueError):
                    proposal_matches = False
                if (
                    not proposal_matches
                    or not isinstance(paths, list)
                    or any(not isinstance(path, str) or not path for path in paths)
                ):
                    continue
            pending.append(dict(record))
        pending.sort(
            key=lambda item: (
                str(item.get("requestedAt", "")),
                str(item.get("runId", "")),
            ),
            reverse=True,
        )
        # Additive presentation hint: surfaces may render the declared action
        # display name instead of the raw action identifier.  The run record
        # stays the authority; failures to resolve the contract only omit the
        # hint, never the pending decision.
        display_names: dict[str, dict[str, str]] = {}
        for item in pending:
            action_id = item.get("actionId")
            if not isinstance(action_id, str) or not action_id:
                continue
            instance_key = str(item["instanceId"])
            if instance_key not in display_names:
                try:
                    display_names[instance_key] = {
                        contract.action_id: contract.display_name
                        for contract in self._actions(instance_key).values()
                        if contract.display_name
                    }
                except (OSError, ValueError, PortableExecutionError):
                    display_names[instance_key] = {}
            display_name = display_names[instance_key].get(action_id)
            if display_name:
                item["actionDisplayName"] = display_name
        return pending[:maximum_rows]

    def export_instance(self, instance_id: str) -> dict[str, Any]:
        _, root = self.app._entry(instance_id)
        self.app.locked_source(instance_id)
        destination = self.app.layout.operations_root / "portable" / f"{instance_id}.zip"
        return export_portable(root, destination)

    def inspect_instance_archive(self, archive_path: str | os.PathLike[str]) -> dict[str, Any]:
        return inspect_portable(archive_path)

    @staticmethod
    def _portable_import_id(value: object, label: str) -> str:
        if not isinstance(value, str) or re.fullmatch(r"[a-z][a-z0-9._-]{1,127}", value) is None:
            raise PortableImportError("portable_import_identity_invalid", f"portable import {label} is invalid")
        return value

    @staticmethod
    def _portable_import_digest(value: object, label: str) -> str:
        if not isinstance(value, str) or re.fullmatch(r"sha256:[0-9a-f]{64}", value) is None:
            raise PortableImportError("portable_import_identity_invalid", f"portable import {label} is invalid")
        return value

    def _portable_import_plan(
        self,
        archive_path: Path,
        destination: Path,
        *,
        expected_archive_digest: object,
        expected_archive_file_digest: object,
        destination_instance_id: object,
        identity_policy: object,
    ) -> dict[str, Any]:
        """Bind an import to archive bytes, manifest payload, and target identity."""

        instance_id = self._portable_import_id(destination_instance_id, "destination instance identity")
        expected_payload = self._portable_import_digest(expected_archive_digest, "archive payload digest")
        expected_file = self._portable_import_digest(expected_archive_file_digest, "archive file digest")
        if identity_policy not in {"preserve", "reidentify"}:
            raise PortableImportError("portable_import_identity_invalid", "portable import identity policy is invalid")
        expected_destination = self.app.layout.instances_root / instance_id
        if destination != expected_destination:
            raise PortableImportError("portable_import_destination_refused", "portable import destination does not match its instance identity")
        try:
            portable = inspect_portable(archive_path)
        except Exception as exc:  # archive parser errors remain a single public class
            raise PortableImportError("portable_import_archive_refused", "portable archive inspection was refused") from exc
        archive_digest = portable.get("archiveDigest")
        archive_file_digest = portable.get("archiveFileDigest")
        source_instance_id = portable.get("instanceId")
        source_identity = portable.get("sourceIdentity")
        if (
            not isinstance(archive_digest, str)
            or not isinstance(archive_file_digest, str)
            or not isinstance(source_instance_id, str)
            or not isinstance(source_identity, dict)
        ):
            raise PortableImportError("portable_import_archive_refused", "portable archive identity is incomplete")
        if not secrets.compare_digest(expected_payload, archive_digest) or not secrets.compare_digest(expected_file, archive_file_digest):
            raise PortableImportError("portable_import_stale", "portable archive identity changed; preview it again")
        if identity_policy == "preserve" and source_instance_id != instance_id:
            raise PortableImportError("portable_import_identity_mismatch", "preserved archive identity does not match destination instance identity")
        plan = {
            "formatVersion": "stateport.portable-import-plan/v1",
            "operation": "portable-instance-import",
            "archiveDigest": archive_digest,
            "archiveFileDigest": archive_file_digest,
            "sourceInstanceId": source_instance_id,
            "sourceIdentity": source_identity,
            "destinationInstanceId": instance_id,
            "identityPolicy": identity_policy,
            "fileCount": portable.get("fileCount"),
            "approvalRequired": True,
        }
        if not isinstance(plan["fileCount"], int) or isinstance(plan["fileCount"], bool) or plan["fileCount"] < 1:
            raise PortableImportError("portable_import_archive_refused", "portable archive file inventory is invalid")
        plan["planDigest"] = digest(plan)
        return plan

    def preview_portable_import(
        self,
        archive_path: Path,
        destination: Path,
        *,
        expected_archive_digest: object,
        expected_archive_file_digest: object,
        destination_instance_id: object,
        identity_policy: object,
    ) -> dict[str, Any]:
        plan = self._portable_import_plan(
            archive_path, destination,
            expected_archive_digest=expected_archive_digest,
            expected_archive_file_digest=expected_archive_file_digest,
            destination_instance_id=destination_instance_id,
            identity_policy=identity_policy,
        )
        try:
            # This exercises the complete archive validator and target conflict
            # boundary without creating a directory or registering a catalog row.
            import_portable(
                archive_path, destination,
                new_instance_id=plan["destinationInstanceId"] if identity_policy == "reidentify" else None,
                dry_run=True,
            )
        except Exception as exc:
            raise PortableImportError("portable_import_preview_refused", "portable import preview was refused") from exc
        return {**plan, "dryRun": True, "destinationMutated": False}

    def _portable_import_receipt_path(self, instance_id: str, plan_digest: str) -> Path:
        root = self.app.layout.operations_root / "portable-imports"
        if root.exists() and root.is_symlink():
            raise PortableImportError("portable_import_receipt_refused", "portable import receipt store is unsafe")
        root.mkdir(parents=True, exist_ok=True, mode=0o700)
        os.chmod(root, 0o700)
        return root / f"{instance_id}-{plan_digest[7:]}.json"

    @staticmethod
    def _read_portable_import_receipt(path: Path) -> dict[str, Any] | None:
        if not path.exists():
            return None
        if path.is_symlink() or not path.is_file():
            raise PortableImportError("portable_import_receipt_refused", "portable import receipt is unsafe")
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise PortableImportError("portable_import_receipt_refused", "portable import receipt is unreadable") from exc
        if not isinstance(value, dict):
            raise PortableImportError("portable_import_receipt_refused", "portable import receipt is malformed")
        return value

    @staticmethod
    def _write_portable_import_receipt(path: Path, receipt: dict[str, Any]) -> None:
        if path.exists() or path.is_symlink():
            raise PortableImportError("portable_import_receipt_refused", "portable import receipt already exists")
        raw = (json.dumps(receipt, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n").encode("utf-8")
        temporary = path.with_name(f".{path.name}.{secrets.token_hex(8)}.tmp")
        try:
            with temporary.open("xb") as handle:
                handle.write(raw)
                handle.flush()
                os.fsync(handle.fileno())
            os.chmod(temporary, 0o600)
            if path.exists() or path.is_symlink():
                raise PortableImportError("portable_import_receipt_refused", "portable import receipt appeared during write")
            os.replace(temporary, path)
        except OSError as exc:
            raise PortableImportError("portable_import_receipt_refused", "portable import receipt could not be persisted") from exc
        finally:
            temporary.unlink(missing_ok=True)

    def _portable_import_replay(self, receipt: dict[str, Any], plan: dict[str, Any]) -> dict[str, Any]:
        if receipt.get("planDigest") != plan["planDigest"]:
            raise PortableImportError("portable_import_replay_refused", "destination has a receipt for a different portable import")
        instance_id = str(plan["destinationInstanceId"])
        try:
            _entry, root = self.app._entry(instance_id)
            if root != self.app.layout.instances_root / instance_id:
                raise ValueError("unexpected catalog path")
            locked = self.app.locked_source(instance_id)
        except Exception as exc:  # no replay claim when the adopted instance cannot be verified
            raise PortableImportError("portable_import_replay_refused", "recorded portable import destination is no longer intact") from exc
        archived_source = plan["sourceIdentity"]
        if not isinstance(archived_source, dict):
            raise PortableImportError("portable_import_replay_refused", "recorded portable import source identity is malformed")
        expected_locked_source = {
            key: value for key, value in archived_source.items()
            if key not in {"checkoutLocation", "profile"}
        }
        if digest(locked.get("source")) != digest(expected_locked_source):
            raise PortableImportError("portable_import_replay_refused", "recorded portable import source identity no longer matches")
        return {"receipt": receipt, "idempotentReplay": True, "destinationMutated": False}

    def _rollback_portable_import_destination(self, destination: Path, instance_id: str) -> None:
        """Remove only the newly restored, confined target after a failed apply."""

        try:
            try:
                self.app.catalog.forget(instance_id)
            except Exception:
                pass
            if destination.exists() and destination.is_dir() and not destination.is_symlink():
                shutil.rmtree(destination)
        except OSError as exc:
            raise PortableImportError("portable_import_rollback_failed", "portable import failed and destination cleanup was refused") from exc

    def apply_portable_import(
        self,
        archive_path: Path,
        destination: Path,
        *,
        expected_archive_digest: object,
        expected_archive_file_digest: object,
        destination_instance_id: object,
        identity_policy: object,
        expected_plan_digest: object,
        approval: dict[str, str],
    ) -> dict[str, Any]:
        plan = self._portable_import_plan(
            archive_path, destination,
            expected_archive_digest=expected_archive_digest,
            expected_archive_file_digest=expected_archive_file_digest,
            destination_instance_id=destination_instance_id,
            identity_policy=identity_policy,
        )
        if not isinstance(expected_plan_digest, str) or not secrets.compare_digest(expected_plan_digest, plan["planDigest"]):
            raise PortableImportError("portable_import_stale", "portable import preview changed; preview it again")
        receipt_path = self._portable_import_receipt_path(str(plan["destinationInstanceId"]), plan["planDigest"])
        prior = self._read_portable_import_receipt(receipt_path)
        if prior is not None:
            return self._portable_import_replay(prior, plan)
        created = False
        try:
            # Re-run the dry preview immediately before the mutating restore so
            # a destination race is classified before any catalog operation.
            self.preview_portable_import(
                archive_path, destination,
                expected_archive_digest=expected_archive_digest,
                expected_archive_file_digest=expected_archive_file_digest,
                destination_instance_id=destination_instance_id,
                identity_policy=identity_policy,
            )
            result = self.import_instance_archive(
                archive_path, destination,
                new_instance_id=str(plan["destinationInstanceId"]) if identity_policy == "reidentify" else None,
            )
            created = True
            restored_manifest = result.get("manifest")
            if (
                result.get("archiveDigest") != plan["archiveDigest"]
                or not isinstance(restored_manifest, dict)
                or restored_manifest.get("archiveFileDigest") != plan["archiveFileDigest"]
            ):
                raise PortableImportError("portable_import_stale", "portable archive changed during import; destination was rolled back")
            receipt = {
                "formatVersion": "stateport.portable-import-receipt/v1",
                "receiptId": f"portable-import.{plan['destinationInstanceId']}.{plan['planDigest'][7:19]}",
                "status": "applied",
                "planDigest": plan["planDigest"],
                "archiveDigest": plan["archiveDigest"],
                "archiveFileDigest": plan["archiveFileDigest"],
                "sourceInstanceId": plan["sourceInstanceId"],
                "sourceIdentity": plan["sourceIdentity"],
                "destinationInstanceId": plan["destinationInstanceId"],
                "identityPolicy": plan["identityPolicy"],
                "fileCount": plan["fileCount"],
                "approval": approval,
                "catalogEntry": result.get("catalogEntry"),
                "appliedAt": _now(),
            }
            self._write_portable_import_receipt(receipt_path, receipt)
            return {"receipt": receipt, "idempotentReplay": False, "destinationMutated": True}
        except PortableImportError:
            if created:
                self._rollback_portable_import_destination(destination, str(plan["destinationInstanceId"]))
            raise
        except Exception as exc:
            if created:
                self._rollback_portable_import_destination(destination, str(plan["destinationInstanceId"]))
            raise PortableImportError("portable_import_apply_refused", "portable import apply was refused; destination was unchanged") from exc

    def import_instance_archive(self, archive_path: str | os.PathLike[str], destination: str | os.PathLike[str], *, new_instance_id: str | None = None, dry_run: bool = False) -> dict[str, Any]:
        result = import_portable(archive_path, destination, new_instance_id=new_instance_id, dry_run=dry_run)
        if dry_run:
            return result
        source = result.get("manifest", {}).get("sourceIdentity")
        instance_id = str(result.get("instanceId"))
        try:
            if not isinstance(source, dict):
                raise PortableExecutionError("portable archive has no exact source identity")
            result["catalogEntry"] = self.app.register_portable_import(
                destination, instance_id=instance_id, name=instance_id, expected_source=source,
            )
            return result
        except Exception:
            target = Path(destination)
            if target.exists() and target.is_dir() and not target.is_symlink():
                shutil.rmtree(target)
            raise
