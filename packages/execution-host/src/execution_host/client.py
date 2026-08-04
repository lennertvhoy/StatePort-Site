"""Typed Unix-socket client for the execution-host daemon.

Speaks ``stateport.execution-host-operation/v1`` NDJSON over the confined
socket.  Transport failures (absent socket, refused connection) and daemon
refusals are distinct typed errors; every receipt is contract-validated and
bound to the exact request digest before it is returned.
"""

from __future__ import annotations

import hashlib
import json
import socket
import uuid
from pathlib import Path
from typing import Any, Mapping

from . import daemon_contract as contract


class ExecutionHostError(RuntimeError):
    """Base class for typed client failures."""


class ExecutionHostTransportError(ExecutionHostError):
    """The confined socket is absent, refused, or broke mid-request."""


class ExecutionHostRefusal(ExecutionHostError):
    """The daemon executed a refusal receipt for this request."""

    def __init__(self, receipt: Mapping[str, Any]) -> None:
        refusal = receipt.get("refusal") or {}
        super().__init__(f"{refusal.get('reason')}: {refusal.get('detail')}")
        self.receipt = dict(receipt)
        self.reason = str(refusal.get("reason"))


class ExecutionHostContractError(ExecutionHostError):
    """The peer answered with bytes outside the receipt contract."""


class ExecutionHostClient:
    def __init__(
        self,
        socket_path: str | Path,
        *,
        grant_id: str,
        authority_grant_digest: str,
        timeout_seconds: int = 30,
        output_byte_bound: int = contract.MAX_OUTPUT_BYTES,
    ) -> None:
        self._socket_path = Path(socket_path)
        self._grant_id = grant_id
        self._grant_digest = authority_grant_digest
        self._timeout_seconds = timeout_seconds
        self._output_byte_bound = output_byte_bound

    def _request(self, operation: str, payload: Mapping[str, Any] | None = None) -> dict[str, Any]:
        request: dict[str, Any] = {
            "formatVersion": contract.OPERATION_FORMAT,
            "operationId": f"op-{uuid.uuid4().hex[:24]}",
            "operation": operation,
            "requester": {
                "grantId": self._grant_id,
                "authorityGrantDigest": self._grant_digest,
            },
            "timeoutSeconds": self._timeout_seconds,
            "outputByteBound": self._output_byte_bound,
        }
        if payload is not None:
            request["payload"] = dict(payload)
        contract.validate_operation_request(request)
        contract.validate_request_payload(request, request.get("payload"))
        line = (contract.canonical_json(request) + "\n").encode("utf-8")
        if not self._socket_path.exists():
            raise ExecutionHostTransportError(
                f"socket-absent: {self._socket_path} does not exist; the execution host is not provisioned or not running"
            )
        connection = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        connection.settimeout(self._timeout_seconds + 5)
        try:
            try:
                connection.connect(str(self._socket_path))
            except OSError as exc:
                raise ExecutionHostTransportError(
                    f"socket-refused: cannot connect to {self._socket_path}: {exc}"
                ) from exc
            connection.sendall(line)
            buffer = b""
            while b"\n" not in buffer:
                chunk = connection.recv(65536)
                if not chunk:
                    raise ExecutionHostTransportError("socket-closed: daemon hung up mid-request")
                buffer += chunk
                if len(buffer) > contract.MAX_REQUEST_BYTES:
                    raise ExecutionHostTransportError("daemon response exceeded the byte bound")
        except socket.timeout as exc:
            raise ExecutionHostTransportError(
                f"socket-timeout: daemon did not answer within the request timeout"
            ) from exc
        finally:
            connection.close()
        try:
            receipt = json.loads(buffer.split(b"\n", 1)[0])
            receipt = contract.validate_receipt(receipt)
        except (ValueError, TypeError) as exc:
            raise ExecutionHostContractError(f"daemon receipt violates the contract: {exc}") from exc
        if receipt["operationId"] != request["operationId"]:
            raise ExecutionHostContractError("receipt is not bound to this request operation id")
        if receipt["requestDigest"] != contract.canonical_digest(request):
            raise ExecutionHostContractError("receipt is not bound to this exact request digest")
        if not receipt["accepted"]:
            raise ExecutionHostRefusal(receipt)
        return receipt

    def describe_capabilities(self) -> dict[str, Any]:
        return self._request("describeCapabilities")

    def create_workload(self, spec: Mapping[str, Any]) -> dict[str, Any]:
        return self._request("createWorkload", {"workload": dict(spec)})

    def start(self, workload_id: str) -> dict[str, Any]:
        return self._request("start", {"workloadId": workload_id})

    def stop(self, workload_id: str) -> dict[str, Any]:
        return self._request("stop", {"workloadId": workload_id})

    def status(self, workload_id: str) -> dict[str, Any]:
        return self._request("status", {"workloadId": workload_id})

    def logs(self, workload_id: str) -> dict[str, Any]:
        return self._request("logs", {"workloadId": workload_id})

    def cancel(self, workload_id: str) -> dict[str, Any]:
        return self._request("cancel", {"workloadId": workload_id})

    def remove_workload(self, workload_id: str) -> dict[str, Any]:
        return self._request("removeWorkload", {"workloadId": workload_id})

    def collect_garbage(self) -> dict[str, Any]:
        return self._request("collectGarbage")
