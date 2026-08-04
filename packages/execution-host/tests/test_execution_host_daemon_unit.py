"""Unit tests for the execution-host daemon core.

Uses a fake in-memory engine; no container runtime is invoked.  Covers the
sealed contract shapes, the hardened argv builder, the crash-recovery
matrix, and supervision timeouts over a real confined Unix socket.
"""

from __future__ import annotations

import json
import os
import socket
import sys
import time
from pathlib import Path
from typing import Any, Mapping

import pytest

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "packages" / "execution-host" / "src"))

from execution_host import daemon_contract as contract
from execution_host.client import (
    ExecutionHostClient,
    ExecutionHostRefusal,
    ExecutionHostTransportError,
)
from execution_host.daemon import DaemonBootError, DaemonConfig, ExecutionHostDaemon
from execution_host.engine import (
    EngineError,
    PodmanCliEngine,
    build_create_argv,
    container_name,
)
from execution_host.ledger import OperationLedger, reconcile_on_boot

DIGEST = "sha256:" + "a" * 64
IMAGE = f"docker.io/library/python@{'b' * 64}".replace("python@", "python@sha256:")


class FakeEngine:
    """In-memory engine honouring the PodmanCliEngine surface."""

    def __init__(self) -> None:
        self.containers: dict[str, dict[str, Any]] = {}
        self.identity = {"engine": "fake-cli", "socket": "fake"}
        self.stopped: list[str] = []
        self.removed: list[str] = []

    def version(self) -> dict[str, str]:
        return {"engine": "fake", "engineVersion": "0.0.0-test"}

    def create(self, spec: Mapping[str, Any]) -> str:
        name = container_name(spec["workloadId"])
        self.containers[spec["workloadId"]] = {
            "name": name,
            "running": False,
            "exitStatus": None,
            "labels": {"io.stateport.execution.workload": spec["workloadId"]},
        }
        return "fake-container-" + spec["workloadId"]

    def start(self, workload_id: str) -> None:
        self.containers[workload_id]["running"] = True

    def stop(self, workload_id: str, *, timeout: int = 2) -> None:
        if workload_id in self.containers:
            self.containers[workload_id]["running"] = False
            self.containers[workload_id]["exitStatus"] = 137
            self.stopped.append(workload_id)

    def kill(self, workload_id: str) -> None:
        self.stop(workload_id, timeout=0)

    def remove(self, workload_id: str, *, force: bool = True) -> None:
        self.containers.pop(workload_id, None)
        self.removed.append(workload_id)

    def inspect(self, workload_id: str) -> dict[str, Any]:
        item = self.containers.get(workload_id)
        if item is None:
            return {"present": False}
        return {
            "present": True,
            "status": "running" if item["running"] else "exited",
            "running": item["running"],
            "exitStatus": item["exitStatus"],
            "startedAt": None,
            "finishedAt": None,
            "imageDigest": DIGEST,
            "labels": item["labels"],
        }

    def logs(self, workload_id: str, *, max_bytes: int) -> dict[str, Any]:
        data = b"fake-output" * 100
        return {
            "bytes": data[:max_bytes].decode(),
            "byteCount": min(len(data), max_bytes),
            "truncated": len(data) > max_bytes,
        }

    def list_managed(self) -> list[dict[str, Any]]:
        return [
            {
                "workloadId": workload_id,
                "state": "running" if item["running"] else "exited",
                "labels": item["labels"],
            }
            for workload_id, item in self.containers.items()
        ]


def spec(workload_id: str = "wl-test", kind: str = "terminal", **changes: Any) -> dict[str, Any]:
    value: dict[str, Any] = {
        "kind": kind,
        "workloadId": workload_id,
        "image": {"reference": IMAGE},
        "parameters": {"sessionId": "sess-1", "workSeconds": 60, "emitBytes": 0},
        "timeoutSeconds": 30,
        "outputByteBound": 4096,
        "resources": {"memoryMaxBytes": 268435456, "pidsMax": 128},
    }
    if kind == "agent-run":
        value["parameters"] = {"runSpecDigest": DIGEST, "statePackReference": "statepack:test", "workSeconds": 60, "emitBytes": 0}
    value.update(changes)
    return value


# --------------------------------------------------------------- contract


def test_sealed_spec_accepts_every_kind() -> None:
    for kind, identity in (
        ("agent-run", {"runSpecDigest": DIGEST, "statePackReference": "statepack:test"}),
        ("capsule-service", {"serviceName": "svc-1"}),
        ("browser-journey", {"journeyId": "journey-1"}),
        ("terminal", {"sessionId": "sess-1"}),
    ):
        validated = contract.validate_workload_spec(
            spec(kind=kind, parameters={**identity, "workSeconds": 5, "emitBytes": 0})
        )
        assert validated["kind"] == kind


@pytest.mark.parametrize(
    "mutation",
    [
        lambda s: s.update(kind="arbitrary-shell"),
        lambda s: s.update(command=["rm", "-rf", "/"]),
        lambda s: s["image"].update(reference="docker.io/library/python:latest"),
        lambda s: s.update(timeoutSeconds=0),
        lambda s: s.update(outputByteBound=contract.MAX_OUTPUT_BYTES + 1),
        lambda s: s["parameters"].update(workSeconds=contract.MAX_WORK_SECONDS + 1),
        lambda s: s.update(apiKey="nope"),
        lambda s: s["resources"].update(pidsMax=4),
    ],
)
def test_sealed_spec_refuses_escape_hatches(mutation) -> None:
    value = spec()
    mutation(value)
    with pytest.raises(ValueError):
        contract.validate_workload_spec(value)


def test_request_envelope_and_digest_binding() -> None:
    request = {
        "formatVersion": contract.OPERATION_FORMAT,
        "operationId": "op-1",
        "operation": "createWorkload",
        "requester": {"grantId": "grant-1", "authorityGrantDigest": DIGEST},
        "timeoutSeconds": 30,
        "outputByteBound": 4096,
        "payload": {"workload": spec()},
    }
    validated = contract.validate_operation_request(request)
    assert validated["operation"] == "createWorkload"
    payload = contract.validate_request_payload(validated, request["payload"])
    assert payload["workload"]["workloadId"] == "wl-test"
    assert contract.canonical_digest(request) == contract.canonical_digest(dict(request))
    broken = dict(request, operation="execShell")
    with pytest.raises(ValueError):
        contract.validate_operation_request(broken)


def test_receipt_validation_round_trip() -> None:
    receipt = contract.refusal_receipt(
        DIGEST,
        "op-1",
        {"uid": 1, "gid": 1, "pid": 2, "grantId": "grant-1"},
        "contract-violation",
        "bad shape",
        received_at="2026-08-02T00:00:00Z",
        completed_at="2026-08-02T00:00:01Z",
    )
    assert contract.validate_receipt(receipt)["accepted"] is False


# ------------------------------------------------------------------ engine


def test_create_argv_is_hardened_and_sealed() -> None:
    argv = build_create_argv(contract.validate_workload_spec(spec()))
    assert "--privileged" not in argv
    assert "--network" in argv and argv[argv.index("--network") + 1] == "none"
    assert "--read-only" in argv
    assert "--cap-drop" in argv
    joined = " ".join(argv)
    assert "podman.sock" not in joined and "docker.sock" not in joined
    with pytest.raises(EngineError):
        from execution_host.engine import assert_create_argv_hardened

        assert_create_argv_hardened(["create", "--privileged", IMAGE])


@pytest.mark.parametrize(
    "socket_path",
    ["/run/podman/podman.sock", "/var/run/docker.sock", "relative.sock"],
)
def test_engine_refuses_control_plane_and_relative_sockets(socket_path: str) -> None:
    with pytest.raises(EngineError):
        PodmanCliEngine(socket_path=socket_path)


def test_engine_uses_owned_socket_via_container_host() -> None:
    engine = PodmanCliEngine(socket_path="/run/stateport-engine/podman.sock")
    env = engine._env()
    assert env["CONTAINER_HOST"] == "unix:///run/stateport-engine/podman.sock"
    assert "DOCKER_HOST" not in env


# --------------------------------------------------------- crash recovery


def _ledger_with(state_dir: Path, workload_id: str, state: str) -> OperationLedger:
    ledger = OperationLedger(state_dir)
    entry = ledger.record_created(
        contract.validate_workload_spec(spec(workload_id)), at="2026-08-02T00:00:00Z", container_id="c"
    )
    if state != "created":
        ledger.transition(workload_id, state, at="2026-08-02T00:00:01Z")
    return ledger


@pytest.mark.parametrize("container_present", [True, False])
def test_recovery_interrupts_non_terminal_workloads(tmp_path: Path, container_present: bool) -> None:
    ledger = _ledger_with(tmp_path, "wl-crash", "running")
    engine = FakeEngine()
    if container_present:
        engine.create(spec("wl-crash"))
        engine.start("wl-crash")
    report = reconcile_on_boot(ledger, engine, at="2026-08-02T01:00:00Z")
    assert report["interrupted"] == ["wl-crash"]
    assert ledger.get("wl-crash")["state"] == "interrupted"
    assert ledger.get("wl-crash")["receipts"][-1]["kind"] == "restart-recovery"
    assert "wl-crash" not in engine.containers


def test_recovery_removes_orphan_containers_and_terminal_leftovers(tmp_path: Path) -> None:
    ledger = _ledger_with(tmp_path, "wl-done", "exited")
    engine = FakeEngine()
    engine.create(spec("wl-done"))  # leftover container for a terminal entry
    engine.create(spec("wl-ghost"))  # orphan with no ledger entry at all
    report = reconcile_on_boot(ledger, engine, at="2026-08-02T01:00:00Z")
    assert sorted(report["orphansRemoved"]) == ["wl-done", "wl-ghost"]
    assert engine.containers == {}
    assert ledger.get("wl-done")["state"] == "exited"


def test_recovery_journal_is_durable(tmp_path: Path) -> None:
    ledger = _ledger_with(tmp_path / "sub", "wl-journal", "running")
    reconcile_on_boot(ledger, FakeEngine(), at="2026-08-02T01:00:00Z")
    journal = list((tmp_path / "sub" / "recovery").glob("recovery-*.json"))
    assert len(journal) == 1
    assert json.loads(journal[0].read_text())["report"]["interrupted"] == ["wl-journal"]


# ------------------------------------------------- supervision over socket


def _boot(tmp_path: Path, engine: FakeEngine, interval: float = 0.05) -> ExecutionHostDaemon:
    socket_dir = tmp_path / "execution-control"
    socket_dir.mkdir()
    os.chmod(socket_dir, 0o750)
    config = DaemonConfig(
        socket_path=socket_dir / "control.sock",
        state_dir=tmp_path / "state",
        socket_group_gid=os.getegid(),
        supervise_interval_seconds=interval,
    )
    daemon = ExecutionHostDaemon(config, engine)
    daemon.boot()
    import threading

    threading.Thread(target=daemon.serve_forever, daemon=True).start()
    return daemon


def _client(tmp_path: Path, **changes: Any) -> ExecutionHostClient:
    return ExecutionHostClient(
        tmp_path / "execution-control" / "control.sock",
        grant_id="grant-test",
        authority_grant_digest=DIGEST,
        **changes,
    )


def test_daemon_lifecycle_timeout_and_cancel_over_socket(tmp_path: Path) -> None:
    engine = FakeEngine()
    daemon = _boot(tmp_path, engine)
    try:
        client = _client(tmp_path)
        capabilities = client.describe_capabilities()
        assert capabilities["result"]["sealedWorkloadsOnly"] is True
        assert capabilities["result"]["transport"] == "confined-host-unix-socket"
        receipt = client.create_workload(spec("wl-unit"))
        assert receipt["result"]["state"] == "created"
        client.start("wl-unit")
        assert client.status("wl-unit")["result"]["state"] == "running"
        logs = _client(tmp_path, output_byte_bound=64).logs("wl-unit")
        assert logs["result"]["truncated"] is True
        assert logs["result"]["byteCount"] == 64
        assert logs["result"]["outputByteBound"] == 64
        client.cancel("wl-unit")
        assert client.status("wl-unit")["result"]["state"] == "cancelled"
        client.remove_workload("wl-unit")
        assert "wl-unit" not in engine.containers
        garbage = client.collect_garbage()
        assert garbage["result"]["removedWorkloads"] == []
    finally:
        daemon.shutdown()


def test_supervision_marks_timeout(tmp_path: Path) -> None:
    engine = FakeEngine()
    daemon = _boot(tmp_path, engine)
    try:
        client = _client(tmp_path)
        client.create_workload(spec("wl-slow", timeoutSeconds=1))
        client.start("wl-slow")
        deadline = time.time() + 10
        state = "running"
        while time.time() < deadline:
            state = client.status("wl-slow")["result"]["state"]
            if state == "timed_out":
                break
            time.sleep(0.1)
        assert state == "timed_out"
        entry = OperationLedger(tmp_path / "state").get("wl-slow")
        assert entry["receipts"][-1]["kind"] == "supervision-timeout"
    finally:
        daemon.shutdown()


def test_refusals_are_typed(tmp_path: Path) -> None:
    daemon = _boot(tmp_path, FakeEngine())
    try:
        client = _client(tmp_path)
        with pytest.raises(ExecutionHostRefusal, match="unknown-workload"):
            client.status("wl-missing")
        client.create_workload(spec("wl-dupe"))
        with pytest.raises(ExecutionHostRefusal, match="duplicate-workload"):
            client.create_workload(spec("wl-dupe"))
        client.start("wl-dupe")
        with pytest.raises(ExecutionHostRefusal, match="invalid-state"):
            client.start("wl-dupe")
    finally:
        daemon.shutdown()


def test_boot_refusals(tmp_path: Path) -> None:
    engine = FakeEngine()
    missing = DaemonConfig(
        socket_path=tmp_path / "absent" / "control.sock",
        state_dir=tmp_path / "state",
        socket_group_gid=os.getegid(),
    )
    with pytest.raises(DaemonBootError, match="absent"):
        ExecutionHostDaemon(missing, engine).boot()

    wrong_group_dir = tmp_path / "wrong-group"
    wrong_group_dir.mkdir()
    os.chmod(wrong_group_dir, 0o750)
    wrong_group = DaemonConfig(
        socket_path=wrong_group_dir / "control.sock",
        state_dir=tmp_path / "state",
        socket_group_gid=os.getegid() + 1,
    )
    with pytest.raises(DaemonBootError, match="group confinement failed"):
        ExecutionHostDaemon(wrong_group, engine).boot()

    wrong_mode_dir = tmp_path / "wrong-mode"
    wrong_mode_dir.mkdir()
    os.chmod(wrong_mode_dir, 0o755)
    wrong_mode = DaemonConfig(
        socket_path=wrong_mode_dir / "control.sock",
        state_dir=tmp_path / "state",
        socket_group_gid=os.getegid(),
    )
    with pytest.raises(DaemonBootError, match="0o750"):
        ExecutionHostDaemon(wrong_mode, engine).boot()


def test_client_socket_absent_is_typed(tmp_path: Path) -> None:
    client = _client(tmp_path)
    with pytest.raises(ExecutionHostTransportError, match="socket-absent"):
        client.describe_capabilities()
