"""Typed execution-host daemon contract (fail-closed, sealed workloads).

The daemon speaks a versioned JSON contract over a group-confined Unix
socket.  Workloads are sealed typed shapes — the client supplies only typed
fields and the daemon owns every container argument; arbitrary command lines
do not exist in this contract.  No HTTP and no mTLS in the alpha: the
confinement boundary is the host socket directory ownership plus peer
credentials.
"""

from __future__ import annotations

import hashlib
import json
import re
from typing import Any, Mapping


OPERATION_FORMAT = "stateport.execution-host-operation/v1"
RECEIPT_FORMAT = "stateport.execution-host-receipt/v1"
CONTRACT_VERSION = 1
CLIENT_COMPATIBILITY = {"minimum": 1, "maximum": 2}

WORKLOAD_KINDS = ("agent-run", "capsule-service", "browser-journey", "terminal")
OPERATIONS = (
    "describeCapabilities",
    "createWorkload",
    "start",
    "stop",
    "status",
    "logs",
    "cancel",
    "removeWorkload",
    "collectGarbage",
)
WORKLOAD_STATES = (
    "created",
    "running",
    "exited",
    "timed_out",
    "cancelled",
    "interrupted",
    "failed",
    "removed",
)
TERMINAL_STATES = frozenset({"exited", "timed_out", "cancelled", "interrupted", "failed", "removed"})

MAX_REQUEST_BYTES = 1024 * 1024
MAX_TIMEOUT_SECONDS = 86400
MAX_REQUEST_TIMEOUT_SECONDS = 600
MAX_OUTPUT_BYTES = 4 * 1024 * 1024
MAX_WORK_SECONDS = 3600
MAX_EMIT_BYTES = 16 * 1024 * 1024
MAX_WORKLOADS = 64
DEFAULT_MEMORY_MAX_BYTES = 268435456
MAX_MEMORY_MAX_BYTES = 1073741824
DEFAULT_PIDS_MAX = 128
MAX_PIDS_MAX = 512

_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$")
_DIGEST = re.compile(r"^sha256:[0-9a-f]{64}$")
_IMAGE = re.compile(r"^[a-z0-9][a-z0-9._/:-]{0,255}@sha256:[0-9a-f]{64}$")
_SECRET_KEY = re.compile(
    r"(?:api[_-]?key|authorization|cookie|credential|password|secret|access[_-]?token|refresh[_-]?token)",
    re.I,
)

# Per-kind sealed parameter identity fields.  Values are validated below;
# nothing in a spec is ever spliced into a command line.
_KIND_IDENTITY_FIELDS = {
    "agent-run": {"runSpecDigest", "statePackReference"},
    "capsule-service": {"serviceName"},
    "browser-journey": {"journeyId"},
    "terminal": {"sessionId"},
}


def canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def canonical_digest(value: Any) -> str:
    return "sha256:" + hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def _string(value: Any, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be a non-empty string")
    return value


def _id(value: Any, name: str) -> str:
    value = _string(value, name)
    if not _ID.fullmatch(value):
        raise ValueError(f"{name} has invalid characters")
    return value


def _digest(value: Any, name: str) -> str:
    value = _string(value, name)
    if not _DIGEST.fullmatch(value):
        raise ValueError(f"{name} must be a sha256 digest")
    return value


def _int(value: Any, name: str, minimum: int, maximum: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or not minimum <= value <= maximum:
        raise ValueError(f"{name} must be an integer in [{minimum}, {maximum}]")
    return value


def _mapping(value: Any, name: str, keys: set[str]) -> Mapping[str, Any]:
    if not isinstance(value, Mapping) or set(value) != keys:
        raise ValueError(f"{name} has an invalid shape")
    return value


def _no_secrets(value: Any, path: str = "$") -> None:
    if isinstance(value, Mapping):
        for key, item in value.items():
            if not isinstance(key, str):
                raise ValueError(f"{path} keys must be strings")
            if _SECRET_KEY.search(key):
                raise ValueError(f"credential-like field is forbidden at {path}.{key}")
            _no_secrets(item, f"{path}.{key}")
    elif isinstance(value, list):
        for index, item in enumerate(value):
            _no_secrets(item, f"{path}[{index}]")


def validate_image_reference(value: Any) -> str:
    reference = _string(value, "image.reference")
    if not _IMAGE.fullmatch(reference):
        raise ValueError("image.reference must be a digest-pinned lowercase OCI reference")
    return reference


def validate_workload_spec(value: Any) -> dict[str, Any]:
    """Validate a sealed workload spec; unknown kinds and fields refuse."""

    _no_secrets(value)
    data = _mapping(
        value, "workload spec", {"kind", "workloadId", "image", "parameters", "timeoutSeconds", "outputByteBound", "resources"}
    )
    kind = data["kind"]
    if kind not in WORKLOAD_KINDS:
        raise ValueError(f"unknown sealed workload kind: {kind!r}")
    workload_id = _id(data["workloadId"], "workloadId")
    image = _mapping(data["image"], "image", {"reference"})
    reference = validate_image_reference(image["reference"])
    parameters = _mapping(
        data["parameters"], "parameters", _KIND_IDENTITY_FIELDS[kind] | {"workSeconds", "emitBytes"}
    )
    normalized_parameters: dict[str, Any] = {}
    for field in sorted(_KIND_IDENTITY_FIELDS[kind]):
        raw = parameters[field]
        if field == "runSpecDigest":
            normalized_parameters[field] = _digest(raw, f"parameters.{field}")
        elif field == "statePackReference":
            normalized_parameters[field] = _string(raw, f"parameters.{field}")
        else:
            normalized_parameters[field] = _id(raw, f"parameters.{field}")
    normalized_parameters["workSeconds"] = _int(
        parameters.get("workSeconds", 0), "parameters.workSeconds", 0, MAX_WORK_SECONDS
    )
    normalized_parameters["emitBytes"] = _int(
        parameters.get("emitBytes", 0), "parameters.emitBytes", 0, MAX_EMIT_BYTES
    )
    resources = _mapping(data["resources"], "resources", {"memoryMaxBytes", "pidsMax"})
    normalized = {
        "kind": kind,
        "workloadId": workload_id,
        "image": {"reference": reference},
        "parameters": normalized_parameters,
        "timeoutSeconds": _int(data["timeoutSeconds"], "timeoutSeconds", 1, MAX_TIMEOUT_SECONDS),
        "outputByteBound": _int(data["outputByteBound"], "outputByteBound", 1, MAX_OUTPUT_BYTES),
        "resources": {
            "memoryMaxBytes": _int(
                resources["memoryMaxBytes"], "resources.memoryMaxBytes", 16 * 1024 * 1024, MAX_MEMORY_MAX_BYTES
            ),
            "pidsMax": _int(resources["pidsMax"], "resources.pidsMax", 16, MAX_PIDS_MAX),
        },
    }
    return normalized


def validate_operation_request(value: Any) -> dict[str, Any]:
    """Validate one daemon request envelope (no peer identity; that is observed)."""

    _no_secrets(value)
    if not isinstance(value, Mapping):
        raise ValueError("operation request has an invalid shape")
    base_keys = {"formatVersion", "operationId", "operation", "requester", "timeoutSeconds", "outputByteBound"}
    if set(value) != base_keys and set(value) != base_keys | {"payload"}:
        raise ValueError("operation request has an invalid shape")
    data = value
    if data["formatVersion"] != OPERATION_FORMAT:
        raise ValueError("operation request has an invalid formatVersion")
    operation = data["operation"]
    if operation not in OPERATIONS:
        raise ValueError(f"unknown operation: {operation!r}")
    requester = _mapping(data["requester"], "requester", {"grantId", "authorityGrantDigest"})
    normalized = {
        "formatVersion": OPERATION_FORMAT,
        "operationId": _id(data["operationId"], "operationId"),
        "operation": operation,
        "requester": {
            "grantId": _id(requester["grantId"], "requester.grantId"),
            "authorityGrantDigest": _digest(
                requester["authorityGrantDigest"], "requester.authorityGrantDigest"
            ),
        },
        "timeoutSeconds": _int(data["timeoutSeconds"], "timeoutSeconds", 1, MAX_REQUEST_TIMEOUT_SECONDS),
        "outputByteBound": _int(data["outputByteBound"], "outputByteBound", 1, MAX_OUTPUT_BYTES),
    }
    return normalized


def validate_request_payload(request: Mapping[str, Any], payload: Any) -> dict[str, Any]:
    """Validate the operation-specific payload of an already-validated request."""

    operation = request["operation"]
    if operation == "createWorkload":
        data = _mapping(payload, "createWorkload payload", {"workload"})
        return {"workload": validate_workload_spec(data["workload"])}
    if operation in {"start", "stop", "status", "logs", "cancel", "removeWorkload"}:
        data = _mapping(payload, f"{operation} payload", {"workloadId"})
        return {"workloadId": _id(data["workloadId"], "workloadId")}
    if payload is not None:
        raise ValueError(f"{operation} must not carry a payload")
    return {}


def refusal_receipt(
    request_digest: str,
    operation_id: str,
    peer: Mapping[str, Any],
    reason: str,
    detail: str,
    *,
    received_at: str,
    completed_at: str,
) -> dict[str, Any]:
    return {
        "formatVersion": RECEIPT_FORMAT,
        "operationId": operation_id,
        "requestDigest": request_digest,
        "accepted": False,
        "refusal": {"reason": _id(reason, "refusal.reason"), "detail": str(detail)[:500]},
        "requester": dict(peer),
        "result": None,
        "observed": {
            "engine": None,
            "engineVersion": None,
            "imageDigest": None,
            "exitStatus": None,
            "startedAt": None,
            "finishedAt": None,
        },
        "cleanup": {"outcome": "not-required", "detail": "request refused before execution"},
        "timestamps": {"receivedAt": received_at, "completedAt": completed_at},
    }


def validate_receipt(value: Any) -> dict[str, Any]:
    _no_secrets(value)
    data = _mapping(
        value,
        "execution receipt",
        {
            "formatVersion",
            "operationId",
            "requestDigest",
            "accepted",
            "refusal",
            "requester",
            "result",
            "observed",
            "cleanup",
            "timestamps",
        },
    )
    if data["formatVersion"] != RECEIPT_FORMAT:
        raise ValueError("receipt has an invalid formatVersion")
    _id(data["operationId"], "operationId")
    _digest(data["requestDigest"], "requestDigest")
    if not isinstance(data["accepted"], bool):
        raise ValueError("receipt.accepted must be boolean")
    if data["accepted"]:
        if data["refusal"] is not None:
            raise ValueError("accepted receipt must not carry a refusal")
    else:
        refusal = _mapping(data["refusal"], "refusal", {"reason", "detail"})
        _id(refusal["reason"], "refusal.reason")
        _string(refusal["detail"], "refusal.detail")
    requester = _mapping(data["requester"], "receipt.requester", {"uid", "gid", "pid", "grantId"})
    for field in ("uid", "gid", "pid"):
        _int(requester[field], f"requester.{field}", -1, 2**31)
    _id(requester["grantId"], "requester.grantId")
    observed = _mapping(
        data["observed"],
        "observed",
        {"engine", "engineVersion", "imageDigest", "exitStatus", "startedAt", "finishedAt"},
    )
    for field in ("engine", "engineVersion", "imageDigest", "startedAt", "finishedAt"):
        if observed[field] is not None and not isinstance(observed[field], str):
            raise ValueError(f"observed.{field} must be a string or null")
    if observed["exitStatus"] is not None:
        _int(observed["exitStatus"], "observed.exitStatus", -1, 255)
    cleanup = _mapping(data["cleanup"], "cleanup", {"outcome", "detail"})
    if cleanup["outcome"] not in {"not-required", "performed", "failed"}:
        raise ValueError("cleanup.outcome is invalid")
    _string(cleanup["detail"], "cleanup.detail")
    _mapping(data["timestamps"], "timestamps", {"receivedAt", "completedAt"})
    return dict(data)
