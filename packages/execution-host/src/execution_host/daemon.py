"""Execution-host daemon: versioned JSON over a group-confined Unix socket.

Boot sequence is fail-closed: private state directory, operator-provisioned
socket directory with exact owner/group/mode, engine socket confinement, then
ledger/engine crash reconciliation — and only then does the socket accept
work.  There is no HTTP listener and no mTLS in the alpha; the confinement
boundary is host filesystem ownership plus SO_PEERCRED observation.
"""

from __future__ import annotations

import grp
import json
import os
import pwd
import socket
import struct
import threading
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Mapping

from . import daemon_contract as contract
from .engine import EngineError, PodmanCliEngine
from .ledger import LedgerError, OperationLedger, reconcile_on_boot


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


class DaemonBootError(RuntimeError):
    """Boot refusal: the daemon never starts on a failed safety boundary."""


@dataclass(frozen=True)
class DaemonConfig:
    socket_path: Path
    state_dir: Path
    socket_group_name: str = "stateport-execution-control"
    socket_group_gid: int | None = None
    allowed_client_user: str = "stateport-control"
    allowed_client_uid: int | None = None
    supervise_interval_seconds: float = 0.5
    clock: Callable[[], str] = field(default=_utcnow, compare=False)

    @classmethod
    def from_env(cls, env: Mapping[str, str] | None = None) -> "DaemonConfig":
        env = dict(os.environ if env is None else env)
        socket_path = Path(
            env.get(
                "STATEPORT_EXECUTION_HOST_SOCKET",
                env.get("STATEPORT_HOST_SOCKET", "/run/stateport/execution-control/control.sock"),
            )
        )
        gid_raw = env.get("STATEPORT_EXECUTION_HOST_SOCKET_GROUP_GID")
        uid_raw = env.get("STATEPORT_EXECUTION_HOST_ALLOWED_CLIENT_UID")
        return cls(
            socket_path=socket_path,
            state_dir=Path(
                env.get("STATEPORT_EXECUTION_HOST_STATE_DIR", "/var/lib/stateport/execution-host")
            ),
            socket_group_name=env.get(
                "STATEPORT_EXECUTION_HOST_SOCKET_GROUP", "stateport-execution-control"
            ),
            socket_group_gid=int(gid_raw) if gid_raw else None,
            allowed_client_user=env.get(
                "STATEPORT_EXECUTION_HOST_ALLOWED_CLIENT_USER", "stateport-control"
            ),
            allowed_client_uid=int(uid_raw) if uid_raw else None,
        )


class ExecutionHostDaemon:
    def __init__(self, config: DaemonConfig, engine: Any) -> None:
        self._config = config
        self._engine = engine
        self._ledger: OperationLedger | None = None
        self._server: socket.socket | None = None
        self._shutdown = threading.Event()
        self._threads: list[threading.Thread] = []
        self.recovery_report: dict[str, Any] | None = None

    # ------------------------------------------------------------------ boot

    def _expected_socket_gid(self) -> int | None:
        if self._config.socket_group_gid is not None:
            return self._config.socket_group_gid
        try:
            return grp.getgrnam(self._config.socket_group_name).gr_gid
        except KeyError:
            return None

    def _allowed_peer_uids(self) -> set[int]:
        allowed = {os.geteuid()}
        if self._config.allowed_client_uid is not None:
            allowed.add(self._config.allowed_client_uid)
        try:
            allowed.add(pwd.getpwnam(self._config.allowed_client_user).pw_uid)
        except KeyError:
            pass
        return allowed

    def _assert_socket_directory(self) -> None:
        directory = self._config.socket_path.parent
        if not directory.is_dir():
            raise DaemonBootError(
                f"socket directory {directory} is absent; it is operator-provisioned (tmpfiles) "
                "and the daemon must not create it"
            )
        stat = directory.stat()
        if stat.st_uid != os.geteuid():
            raise DaemonBootError(
                f"socket directory {directory} is owned by uid {stat.st_uid}, not the daemon uid {os.geteuid()}"
            )
        expected_gid = self._expected_socket_gid()
        if expected_gid is None:
            raise DaemonBootError(
                f"socket group {self._config.socket_group_name!r} is not resolvable; refusing to guess confinement"
            )
        if stat.st_gid != expected_gid:
            raise DaemonBootError(
                f"socket directory {directory} has group {stat.st_gid}, expected {expected_gid} "
                f"({self._config.socket_group_name}); group confinement failed"
            )
        if stat.st_mode & 0o777 != 0o750:
            raise DaemonBootError(
                f"socket directory {directory} has mode {oct(stat.st_mode & 0o777)}, expected 0o750"
            )

    def _assert_state_directory(self) -> None:
        state_dir = self._config.state_dir
        state_dir.mkdir(parents=True, exist_ok=True)
        stat = state_dir.stat()
        if stat.st_uid != os.geteuid():
            raise DaemonBootError(f"state directory {state_dir} is not owned by the daemon uid")
        os.chmod(state_dir, 0o700)

    def boot(self) -> None:
        self._assert_state_directory()
        self._assert_socket_directory()
        self._ledger = OperationLedger(self._config.state_dir)
        self.recovery_report = reconcile_on_boot(
            self._ledger, self._engine, at=self._config.clock()
        )
        if self.recovery_report["failures"]:
            raise DaemonBootError(
                f"restart reconciliation failed: {self.recovery_report['failures']}"
            )
        server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        if self._config.socket_path.exists():
            # A stale socket from a killed epoch is safe to reclaim; a live
            # daemon behind the path is a second writer and fails closed.
            probe = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            try:
                probe.connect(str(self._config.socket_path))
            except OSError:
                self._config.socket_path.unlink()
            else:
                probe.close()
                server.close()
                raise DaemonBootError(
                    f"a live daemon already owns {self._config.socket_path}; refusing a second writer"
                )
            finally:
                probe.close()
        try:
            server.bind(str(self._config.socket_path))
        except OSError:
            server.close()
            raise DaemonBootError(f"cannot bind {self._config.socket_path}")
        expected_gid = self._expected_socket_gid()
        os.chown(self._config.socket_path, os.geteuid(), expected_gid)
        os.chmod(self._config.socket_path, 0o660)
        server.listen(16)
        server.settimeout(0.5)
        self._server = server
        supervisor = threading.Thread(target=self._supervise, name="exec-host-supervisor", daemon=True)
        supervisor.start()
        self._threads.append(supervisor)

    def shutdown(self) -> None:
        self._shutdown.set()
        if self._server is not None:
            try:
                self._server.close()
            except OSError:
                pass
        for thread in self._threads:
            thread.join(timeout=5)
        if self._config.socket_path.exists():
            try:
                self._config.socket_path.unlink()
            except OSError:
                pass

    # ------------------------------------------------------------ supervision

    def _supervise(self) -> None:
        while not self._shutdown.wait(self._config.supervise_interval_seconds):
            ledger = self._ledger
            if ledger is None:
                continue
            for entry in ledger.all():
                if entry["state"] != "running" or not entry.get("startedAt"):
                    continue
                try:
                    started = datetime.fromisoformat(entry["startedAt"].replace("Z", "+00:00"))
                    elapsed = (datetime.now(timezone.utc) - started).total_seconds()
                except (ValueError, TypeError):
                    continue
                if elapsed <= entry["spec"]["timeoutSeconds"]:
                    continue
                workload_id = entry["workloadId"]
                cleanup = "performed"
                try:
                    self._engine.stop(workload_id, timeout=2)
                except EngineError as exc:
                    cleanup = f"failed: {exc}"[:200]
                observed = self._safe_inspect(workload_id)
                ledger.transition(
                    workload_id,
                    "timed_out",
                    at=self._config.clock(),
                    exit_status=observed.get("exitStatus"),
                    finished_at=self._config.clock(),
                    receipt={
                        "kind": "supervision-timeout",
                        "detail": f"workload exceeded its {entry['spec']['timeoutSeconds']}s timeout and was stopped",
                        "cleanup": cleanup,
                    },
                )

    # --------------------------------------------------------------- serving

    def serve_forever(self) -> None:
        server = self._server
        if server is None:
            raise DaemonBootError("boot() must complete before serve_forever()")
        while not self._shutdown.is_set():
            try:
                connection, _ = server.accept()
            except socket.timeout:
                continue
            except OSError:
                break
            thread = threading.Thread(
                target=self._serve_connection, args=(connection,), daemon=True
            )
            thread.start()
            self._threads.append(thread)

    def _peer_credentials(self, connection: socket.socket) -> dict[str, int]:
        raw = connection.getsockopt(socket.SOL_SOCKET, socket.SO_PEERCRED, struct.calcsize("3i"))
        pid, uid, gid = struct.unpack("3i", raw)
        return {"pid": pid, "uid": uid, "gid": gid}

    def _serve_connection(self, connection: socket.socket) -> None:
        try:
            peer = self._peer_credentials(connection)
            buffer = b""
            while not self._shutdown.is_set():
                try:
                    chunk = connection.recv(65536)
                except OSError:
                    break
                if not chunk:
                    break
                buffer += chunk
                if len(buffer) > contract.MAX_REQUEST_BYTES:
                    break
                while b"\n" in buffer:
                    line, buffer = buffer.split(b"\n", 1)
                    if not line.strip():
                        continue
                    receipt = self._handle_line(line, peer)
                    connection.sendall(
                        (contract.canonical_json(receipt) + "\n").encode("utf-8")
                    )
        except OSError:
            pass
        finally:
            try:
                connection.close()
            except OSError:
                pass

    def _handle_line(self, line: bytes, peer: Mapping[str, int]) -> dict[str, Any]:
        received_at = self._config.clock()
        try:
            raw = json.loads(line)
            request = contract.validate_operation_request(raw)
        except (ValueError, TypeError):
            digest = "sha256:" + __import__("hashlib").sha256(line).hexdigest()
            return contract.refusal_receipt(
                digest,
                "malformed-request",
                {**peer, "grantId": "unknown"},
                "contract-violation",
                "request is not a valid stateport.execution-host-operation/v1 document",
                received_at=received_at,
                completed_at=self._config.clock(),
            )
        request_digest = contract.canonical_digest(raw)
        peer_record = {**peer, "grantId": request["requester"]["grantId"]}
        if peer["uid"] not in self._allowed_peer_uids():
            return contract.refusal_receipt(
                request_digest,
                request["operationId"],
                peer_record,
                "peer-not-authorized",
                "peer uid is not the daemon user or the declared allowed client user",
                received_at=received_at,
                completed_at=self._config.clock(),
            )
        try:
            payload = contract.validate_request_payload(request, raw.get("payload"))
        except ValueError as exc:
            return contract.refusal_receipt(
                request_digest,
                request["operationId"],
                peer_record,
                "contract-violation",
                str(exc),
                received_at=received_at,
                completed_at=self._config.clock(),
            )
        try:
            result, observed, cleanup = self._dispatch(request, payload)
        except _Refusal as refusal:
            return contract.refusal_receipt(
                request_digest,
                request["operationId"],
                peer_record,
                refusal.reason,
                refusal.detail,
                received_at=received_at,
                completed_at=self._config.clock(),
            )
        receipt = {
            "formatVersion": contract.RECEIPT_FORMAT,
            "operationId": request["operationId"],
            "requestDigest": request_digest,
            "accepted": True,
            "refusal": None,
            "requester": peer_record,
            "result": result,
            "observed": observed,
            "cleanup": cleanup,
            "timestamps": {"receivedAt": received_at, "completedAt": self._config.clock()},
        }
        return contract.validate_receipt(receipt)

    def _empty_observed(self) -> dict[str, Any]:
        identity = self._engine.identity
        return {
            "engine": identity["engine"],
            "engineVersion": None,
            "imageDigest": None,
            "exitStatus": None,
            "startedAt": None,
            "finishedAt": None,
        }

    def _safe_inspect(self, workload_id: str) -> dict[str, Any]:
        try:
            return self._engine.inspect(workload_id)
        except EngineError:
            return {"present": False}

    def _observed_for(self, workload_id: str) -> dict[str, Any]:
        observed = self._empty_observed()
        info = self._safe_inspect(workload_id)
        observed["imageDigest"] = info.get("imageDigest")
        observed["exitStatus"] = info.get("exitStatus")
        observed["startedAt"] = info.get("startedAt")
        observed["finishedAt"] = info.get("finishedAt")
        return observed

    # -------------------------------------------------------------- dispatch

    def _dispatch(
        self, request: Mapping[str, Any], payload: Mapping[str, Any]
    ) -> tuple[dict[str, Any], dict[str, Any], dict[str, str]]:
        operation = request["operation"]
        handler = {
            "describeCapabilities": self._op_describe,
            "createWorkload": self._op_create,
            "start": self._op_start,
            "stop": self._op_stop,
            "status": self._op_status,
            "logs": self._op_logs,
            "cancel": self._op_cancel,
            "removeWorkload": self._op_remove,
            "collectGarbage": self._op_collect_garbage,
        }[operation]
        return handler(request, payload)

    def _ledger_required(self) -> OperationLedger:
        if self._ledger is None:
            raise _Refusal("daemon-not-ready", "daemon boot has not completed")
        return self._ledger

    def _entry_required(self, workload_id: str) -> dict[str, Any]:
        entry = self._ledger_required().get(workload_id)
        if entry is None:
            raise _Refusal("unknown-workload", f"workload {workload_id} has no ledger entry")
        return entry

    def _op_describe(
        self, request: Mapping[str, Any], payload: Mapping[str, Any]
    ) -> tuple[dict[str, Any], dict[str, Any], dict[str, str]]:
        observed = self._empty_observed()
        try:
            observed.update(self._engine.version())
        except EngineError:
            observed["engineVersion"] = "unavailable"
        result = {
            "formatVersion": "stateport.execution-host-contract/v1",
            "contractVersion": contract.CONTRACT_VERSION,
            "clientCompatibility": dict(contract.CLIENT_COMPATIBILITY),
            "transport": "confined-host-unix-socket",
            "workloadKinds": list(contract.WORKLOAD_KINDS),
            "operations": list(contract.OPERATIONS),
            "sealedWorkloadsOnly": True,
            "limits": {
                "maxTimeoutSeconds": contract.MAX_TIMEOUT_SECONDS,
                "maxOutputBytes": contract.MAX_OUTPUT_BYTES,
                "maxWorkloads": contract.MAX_WORKLOADS,
            },
        }
        return result, observed, {"outcome": "not-required", "detail": "read-only operation"}

    def _op_create(
        self, request: Mapping[str, Any], payload: Mapping[str, Any]
    ) -> tuple[dict[str, Any], dict[str, Any], dict[str, str]]:
        ledger = self._ledger_required()
        spec = payload["workload"]
        if len(ledger.all()) >= contract.MAX_WORKLOADS:
            raise _Refusal("workload-limit", "daemon workload capacity is exhausted")
        if ledger.get(spec["workloadId"]) is not None:
            raise _Refusal("duplicate-workload", f"workload {spec['workloadId']} already exists")
        try:
            container_id = self._engine.create(spec)
        except EngineError as exc:
            raise _Refusal("engine-failure", str(exc)) from exc
        ledger.record_created(spec, at=self._config.clock(), container_id=container_id)
        observed = self._observed_for(spec["workloadId"])
        return (
            {"workloadId": spec["workloadId"], "state": "created", "specDigest": ledger.get(spec["workloadId"])["specDigest"]},
            observed,
            {"outcome": "not-required", "detail": "workload created; removal is an explicit operation"},
        )

    def _op_start(
        self, request: Mapping[str, Any], payload: Mapping[str, Any]
    ) -> tuple[dict[str, Any], dict[str, Any], dict[str, str]]:
        ledger = self._ledger_required()
        entry = self._entry_required(payload["workloadId"])
        if entry["state"] != "created":
            raise _Refusal(
                "invalid-state", f"workload is {entry['state']}; only a created workload can start"
            )
        try:
            self._engine.start(entry["workloadId"])
        except EngineError as exc:
            raise _Refusal("engine-failure", str(exc)) from exc
        started_at = self._config.clock()
        ledger.transition(entry["workloadId"], "running", at=started_at, started_at=started_at)
        return (
            {"workloadId": entry["workloadId"], "state": "running"},
            self._observed_for(entry["workloadId"]),
            {"outcome": "not-required", "detail": "workload running under daemon supervision"},
        )

    def _op_stop(
        self, request: Mapping[str, Any], payload: Mapping[str, Any]
    ) -> tuple[dict[str, Any], dict[str, Any], dict[str, str]]:
        ledger = self._ledger_required()
        entry = self._entry_required(payload["workloadId"])
        if entry["state"] in contract.TERMINAL_STATES:
            raise _Refusal("invalid-state", f"workload is already {entry['state']}")
        try:
            self._engine.stop(entry["workloadId"], timeout=2)
        except EngineError as exc:
            raise _Refusal("engine-failure", str(exc)) from exc
        info = self._safe_inspect(entry["workloadId"])
        finished_at = self._config.clock()
        exit_status = info.get("exitStatus")
        ledger.transition(
            entry["workloadId"],
            "exited",
            at=finished_at,
            exit_status=exit_status,
            finished_at=finished_at,
        )
        return (
            {"workloadId": entry["workloadId"], "state": "exited", "exitStatus": exit_status},
            self._observed_for(entry["workloadId"]),
            {"outcome": "performed", "detail": "workload stopped on explicit request"},
        )

    def _op_status(
        self, request: Mapping[str, Any], payload: Mapping[str, Any]
    ) -> tuple[dict[str, Any], dict[str, Any], dict[str, str]]:
        entry = self._entry_required(payload["workloadId"])
        info = self._safe_inspect(entry["workloadId"])
        state = entry["state"]
        if state == "running" and info.get("present") and not info.get("running"):
            finished_at = self._config.clock()
            self._ledger_required().transition(
                entry["workloadId"],
                "exited",
                at=finished_at,
                exit_status=info.get("exitStatus"),
                finished_at=finished_at,
            )
            state = "exited"
            entry = self._entry_required(payload["workloadId"])
        return (
            {
                "workloadId": entry["workloadId"],
                "state": state,
                "exitStatus": entry.get("exitStatus"),
                "engineStatus": info.get("status") if info.get("present") else "absent",
            },
            self._observed_for(entry["workloadId"]),
            {"outcome": "not-required", "detail": "read-only operation"},
        )

    def _op_logs(
        self, request: Mapping[str, Any], payload: Mapping[str, Any]
    ) -> tuple[dict[str, Any], dict[str, Any], dict[str, str]]:
        entry = self._entry_required(payload["workloadId"])
        bound = min(request["outputByteBound"], entry["spec"]["outputByteBound"])
        try:
            logs = self._engine.logs(entry["workloadId"], max_bytes=bound)
        except EngineError as exc:
            raise _Refusal("engine-failure", str(exc)) from exc
        return (
            {
                "workloadId": entry["workloadId"],
                "state": entry["state"],
                "output": logs["bytes"],
                "byteCount": logs["byteCount"],
                "truncated": logs["truncated"],
                "outputByteBound": bound,
            },
            self._observed_for(entry["workloadId"]),
            {"outcome": "not-required", "detail": "read-only operation"},
        )

    def _op_cancel(
        self, request: Mapping[str, Any], payload: Mapping[str, Any]
    ) -> tuple[dict[str, Any], dict[str, Any], dict[str, str]]:
        ledger = self._ledger_required()
        entry = self._entry_required(payload["workloadId"])
        if entry["state"] in contract.TERMINAL_STATES:
            raise _Refusal("invalid-state", f"workload is already {entry['state']}")
        cleanup = "performed"
        try:
            self._engine.kill(entry["workloadId"])
        except EngineError as exc:
            cleanup = f"failed: {exc}"[:200]
        finished_at = self._config.clock()
        ledger.transition(entry["workloadId"], "cancelled", at=finished_at, finished_at=finished_at)
        return (
            {"workloadId": entry["workloadId"], "state": "cancelled"},
            self._observed_for(entry["workloadId"]),
            {"outcome": "performed" if cleanup == "performed" else "failed", "detail": f"workload cancelled; engine cleanup {cleanup}"},
        )

    def _op_remove(
        self, request: Mapping[str, Any], payload: Mapping[str, Any]
    ) -> tuple[dict[str, Any], dict[str, Any], dict[str, str]]:
        ledger = self._ledger_required()
        entry = self._entry_required(payload["workloadId"])
        if entry["state"] in {"created", "running"}:
            try:
                self._engine.stop(entry["workloadId"], timeout=2)
            except EngineError as exc:
                raise _Refusal("engine-failure", str(exc)) from exc
        try:
            self._engine.remove(entry["workloadId"], force=True)
        except EngineError as exc:
            raise _Refusal("engine-failure", str(exc)) from exc
        ledger.transition(entry["workloadId"], "removed", at=self._config.clock())
        return (
            {"workloadId": entry["workloadId"], "state": "removed"},
            self._empty_observed(),
            {"outcome": "performed", "detail": "workload container removed; ledger entry retained for audit"},
        )

    def _op_collect_garbage(
        self, request: Mapping[str, Any], payload: Mapping[str, Any]
    ) -> tuple[dict[str, Any], dict[str, Any], dict[str, str]]:
        ledger = self._ledger_required()
        active = ledger.active_workload_ids()
        removed: list[str] = []
        failures: list[str] = []
        for item in self._engine.list_managed():
            workload_id = item.get("workloadId")
            if not workload_id or workload_id in active:
                continue
            try:
                self._engine.remove(workload_id, force=True)
                removed.append(workload_id)
            except EngineError as exc:
                failures.append(f"{workload_id}: {exc}"[:200])
        if failures:
            raise _Refusal("engine-failure", "; ".join(failures))
        return (
            {"removedWorkloads": sorted(removed), "activeWorkloads": sorted(active)},
            self._empty_observed(),
            {"outcome": "performed", "detail": f"removed {len(removed)} terminated managed containers"},
        )


class _Refusal(Exception):
    def __init__(self, reason: str, detail: str) -> None:
        super().__init__(detail)
        self.reason = reason
        self.detail = detail
