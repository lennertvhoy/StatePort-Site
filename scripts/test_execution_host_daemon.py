"""Integration tests for the execution-host daemon on real rootless Podman.

Boots the daemon as a real subprocess on a group-confined Unix socket,
drives sealed workloads through the typed client, and proves timeout
supervision, cancellation, output bounds, kill -9 restart reconciliation,
cleanup receipts, and boot/client refusals.  No control-plane Podman socket
is ever used; the test asserts the refusal instead.

Heavy-task policy: set STATEPORT_HEAVY_TASK_LOCK to a lock file path and the
whole session runs under flock so concurrent heavy runs cannot invalidate
evidence.
"""

from __future__ import annotations

import fcntl
import json
import os
import signal
import socket
import subprocess
import sys
import time
import uuid
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "packages" / "execution-host" / "src"))

from execution_host.client import (
    ExecutionHostClient,
    ExecutionHostRefusal,
    ExecutionHostTransportError,
)

GRANT_DIGEST = "sha256:" + "c" * 64
WORKLOAD_IMAGE = (
    "docker.io/library/python:3.13-alpine3.23"
    "@sha256:9fdbf2e3e82628351513560b121e2ee6ce31cac212be9e070c5a5e2769fb5e76"
)
PYTHONPATH = os.pathsep.join(
    [
        str(ROOT / "packages" / "execution-host" / "src"),
        str(ROOT / "apps" / "execution-host" / "src"),
    ]
)


def _podman(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["podman", *args], capture_output=True, text=True, timeout=300)


@pytest.fixture(scope="session", autouse=True)
def _heavy_task_lock():
    lock_path = os.environ.get("STATEPORT_HEAVY_TASK_LOCK")
    if not lock_path:
        yield
        return
    handle = open(lock_path, "a", encoding="utf-8")
    fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
    try:
        yield
    finally:
        fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
        handle.close()


@pytest.fixture(scope="session", autouse=True)
def _workload_image(_heavy_task_lock):
    if shutil_which_podman() is None:
        pytest.skip("podman is not available on this host")
    if _podman("image", "exists", WORKLOAD_IMAGE).returncode != 0:
        pulled = _podman("pull", WORKLOAD_IMAGE)
        if pulled.returncode != 0 or _podman("image", "exists", WORKLOAD_IMAGE).returncode != 0:
            pytest.skip(f"pinned workload image unavailable: {pulled.stderr.strip()[:200]}")
    yield
    leftover = _podman(
        "ps", "-a", "--filter", "label=io.stateport.execution.managed=true",
        "--filter", "label=io.stateport.execution.test=wt1", "--format", "{{.ID}}",
    )
    for container_id in leftover.stdout.split():
        _podman("rm", "--force", container_id)


def shutil_which_podman() -> str | None:
    for candidate in ("/usr/bin/podman", "/usr/local/bin/podman", "/bin/podman"):
        if Path(candidate).exists():
            return candidate
    return None


class DaemonHandle:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.socket_dir = root / "execution-control"
        self.socket_dir.mkdir(parents=True, exist_ok=True)
        os.chmod(self.socket_dir, 0o750)
        self.state_dir = root / "state"
        self.socket_path = self.socket_dir / "control.sock"
        self.process: subprocess.Popen[str] | None = None

    def env(self) -> dict[str, str]:
        env = dict(os.environ)
        env.pop("CONTAINER_HOST", None)
        env.pop("DOCKER_HOST", None)
        env.update(
            {
                "PYTHONPATH": PYTHONPATH,
                "PYTHONDONTWRITEBYTECODE": "1",
                "STATEPORT_EXECUTION_HOST_SOCKET": str(self.socket_path),
                "STATEPORT_EXECUTION_HOST_STATE_DIR": str(self.state_dir),
                "STATEPORT_EXECUTION_HOST_SOCKET_GROUP_GID": str(os.getegid()),
            }
        )
        return env

    def boot(self) -> None:
        self.process = subprocess.Popen(
            [sys.executable, "-m", "stateport_execution_host"],
            env=self.env(),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )
        deadline = time.time() + 60
        while time.time() < deadline:
            if self.process.poll() is not None:
                output = self.process.stdout.read() if self.process.stdout else ""
                raise AssertionError(f"daemon exited during boot: {output[-500:]}")
            if self.socket_path.exists():
                try:
                    probe = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
                    probe.settimeout(2)
                    probe.connect(str(self.socket_path))
                    probe.close()
                    return
                except OSError:
                    # Stale socket from a previous epoch; the daemon reclaims it.
                    pass
            time.sleep(0.1)
        raise AssertionError("daemon did not create its control socket within 60s")

    def stop(self) -> None:
        if self.process is None:
            return
        self.process.terminate()
        try:
            self.process.wait(timeout=30)
        except subprocess.TimeoutExpired:
            self.process.kill()
            self.process.wait(timeout=30)
        self.process = None


def _client(handle: DaemonHandle, **changes) -> ExecutionHostClient:
    return ExecutionHostClient(
        handle.socket_path, grant_id="grant-wt1", authority_grant_digest=GRANT_DIGEST, **changes
    )


def _spec(workload_id: str, **changes) -> dict:
    value = {
        "kind": "terminal",
        "workloadId": workload_id,
        "image": {"reference": WORKLOAD_IMAGE},
        "parameters": {"sessionId": "sess-wt1", "workSeconds": 300, "emitBytes": 0},
        "timeoutSeconds": 600,
        "outputByteBound": 1048576,
        "resources": {"memoryMaxBytes": 268435456, "pidsMax": 128},
    }
    parameters = changes.pop("parameters", {})
    value.update(changes)
    value["parameters"].update(parameters)
    return value


def _workload_id(prefix: str) -> str:
    return f"wt1-{prefix}-{uuid.uuid4().hex[:12]}"


def _wait_state(client: ExecutionHostClient, workload_id: str, state: str, timeout: float) -> dict:
    deadline = time.time() + timeout
    last: dict | None = None
    while time.time() < deadline:
        last = client.status(workload_id)["result"]
        if last["state"] == state:
            return last
        time.sleep(0.5)
    raise AssertionError(f"workload {workload_id} never reached {state}; last={last}")


def test_sealed_workload_run_and_output_bound(tmp_path: Path) -> None:
    handle = DaemonHandle(tmp_path)
    handle.boot()
    try:
        client = _client(handle)
        capabilities = client.describe_capabilities()
        assert capabilities["result"]["formatVersion"] == "stateport.execution-host-contract/v1"
        assert capabilities["result"]["sealedWorkloadsOnly"] is True
        assert capabilities["observed"]["engineVersion"]

        workload_id = _workload_id("run")
        created = client.create_workload(
            _spec(workload_id, parameters={"workSeconds": 5, "emitBytes": 100000})
        )
        assert created["result"]["state"] == "created"
        client.start(workload_id)
        final = _wait_state(client, workload_id, "exited", 60)
        assert final["exitStatus"] == 0
        logs = _client(handle, output_byte_bound=1024).logs(workload_id)
        assert logs["result"]["truncated"] is True
        assert logs["result"]["byteCount"] == 1024
        full = _client(handle, output_byte_bound=1048576).logs(workload_id)
        assert full["result"]["truncated"] is False
        assert "stateport-workload-start kind=terminal" in full["result"]["output"]
        assert "stateport-workload-complete" in full["result"]["output"]
        status = client.status(workload_id)
        assert status["observed"]["imageDigest"] and status["observed"]["imageDigest"].startswith(
            "sha256:"
        )
        client.remove_workload(workload_id)
        assert client.status(workload_id)["result"]["state"] == "removed"
    finally:
        handle.stop()


def test_timeout_supervision_and_cancel(tmp_path: Path) -> None:
    handle = DaemonHandle(tmp_path)
    handle.boot()
    try:
        client = _client(handle)
        slow = _workload_id("slow")
        client.create_workload(_spec(slow, timeoutSeconds=2, parameters={"workSeconds": 300}))
        client.start(slow)
        timed = _wait_state(client, slow, "timed_out", 60)
        assert timed["engineStatus"] in {"exited", "absent"}
        ledger_entry = json.loads(
            (handle.state_dir / "workloads" / f"{slow}.json").read_text(encoding="utf-8")
        )
        assert ledger_entry["receipts"][-1]["kind"] == "supervision-timeout"
        assert ledger_entry["receipts"][-1]["cleanup"] == "performed"
        client.remove_workload(slow)

        doomed = _workload_id("cancel")
        client.create_workload(_spec(doomed, parameters={"workSeconds": 300}))
        client.start(doomed)
        cancelled = client.cancel(doomed)
        assert cancelled["result"]["state"] == "cancelled"
        assert cancelled["cleanup"]["outcome"] == "performed"
        assert _wait_state(client, doomed, "cancelled", 10)["state"] == "cancelled"
        inspect = _podman("inspect", "--format", "{{.State.Running}}", f"stateport-exec-{doomed}")
        assert inspect.stdout.strip() == "false"
        with pytest.raises(ExecutionHostRefusal, match="invalid-state"):
            client.cancel(doomed)
        client.remove_workload(doomed)
        garbage = client.collect_garbage()
        assert garbage["result"]["removedWorkloads"] == []
    finally:
        handle.stop()


def test_kill9_restart_reconciles_ledger_and_container(tmp_path: Path) -> None:
    handle = DaemonHandle(tmp_path)
    handle.boot()
    victim = _workload_id("victim")
    client = _client(handle)
    client.create_workload(_spec(victim, parameters={"workSeconds": 300}))
    client.start(victim)
    assert client.status(victim)["result"]["state"] == "running"
    assert handle.process is not None
    handle.process.send_signal(signal.SIGKILL)
    handle.process.wait(timeout=30)
    handle.process = None
    # The container survives the daemon; the restart must reconcile it.
    running = _podman("inspect", "--format", "{{.State.Running}}", f"stateport-exec-{victim}")
    assert running.stdout.strip() == "true"

    restarted = DaemonHandle(tmp_path)
    restarted.boot()
    try:
        entry = json.loads(
            (handle.state_dir / "workloads" / f"{victim}.json").read_text(encoding="utf-8")
        )
        assert entry["state"] == "interrupted"
        assert entry["receipts"][-1]["kind"] == "restart-recovery"
        assert entry["receipts"][-1]["cleanup"] == "performed"
        recovery = sorted((handle.state_dir / "recovery").glob("recovery-*.json"))
        assert recovery, "restart recovery journal is missing"
        assert victim in json.loads(recovery[-1].read_text(encoding="utf-8"))["report"]["interrupted"]
        gone = _podman("inspect", "--format", "{{.State.Running}}", f"stateport-exec-{victim}")
        assert gone.returncode != 0, "reconciled container must be removed"
        client2 = _client(restarted)
        assert client2.status(victim)["result"]["state"] == "interrupted"
        # The restarted daemon accepts fresh work.
        fresh = _workload_id("fresh")
        client2.create_workload(_spec(fresh, parameters={"workSeconds": 1}))
        client2.start(fresh)
        assert _wait_state(client2, fresh, "exited", 60)["exitStatus"] == 0
        client2.remove_workload(fresh)
        client2.remove_workload(victim)
    finally:
        restarted.stop()


def test_boot_and_client_refusals(tmp_path: Path) -> None:
    # Wrong group on the operator-provisioned directory: boot must refuse.
    wrong_group = DaemonHandle(tmp_path / "wrong-group")
    env = wrong_group.env()
    env["STATEPORT_EXECUTION_HOST_SOCKET_GROUP_GID"] = str(os.getegid() + 1)
    refused = subprocess.run(
        [sys.executable, "-m", "stateport_execution_host"],
        env=env,
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert refused.returncode == 2
    assert "group confinement failed" in refused.stderr

    # Control-plane engine socket: the daemon must refuse to touch it.
    control_plane = DaemonHandle(tmp_path / "control-plane")
    env = control_plane.env()
    env["STATEPORT_ENGINE_SOCKET"] = "/run/podman/podman.sock"
    refused = subprocess.run(
        [sys.executable, "-m", "stateport_execution_host"],
        env=env,
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert refused.returncode == 2
    assert "control-plane" in refused.stderr

    # Client against an absent socket: typed transport error, never a guess.
    absent = ExecutionHostClient(
        tmp_path / "nowhere" / "control.sock",
        grant_id="grant-wt1",
        authority_grant_digest=GRANT_DIGEST,
    )
    with pytest.raises(ExecutionHostTransportError, match="socket-absent"):
        absent.describe_capabilities()


def test_no_control_plane_socket_in_workload_construction(tmp_path: Path) -> None:
    handle = DaemonHandle(tmp_path)
    handle.boot()
    try:
        client = _client(handle)
        workload_id = _workload_id("audit")
        client.create_workload(_spec(workload_id, parameters={"workSeconds": 1}))
        client.start(workload_id)
        _wait_state(client, workload_id, "exited", 60)
        inspect = _podman("inspect", f"stateport-exec-{workload_id}")
        assert inspect.returncode == 0
        import json as _json

        document = _json.loads(inspect.stdout)[0]
        mounts = _json.dumps(document.get("Mounts", [])) + _json.dumps(document.get("HostConfig", {}))
        assert "podman.sock" not in mounts
        assert "docker.sock" not in mounts
        assert document["HostConfig"]["NetworkMode"].startswith("none")
        assert document["HostConfig"]["ReadonlyRootfs"] is True
        assert document["HostConfig"]["Privileged"] is False
        labels = document["Config"]["Labels"]
        assert labels["io.stateport.execution.managed"] == "true"
        assert labels["io.stateport.execution.workload"] == workload_id
        client.remove_workload(workload_id)
        # The daemon's own process environment never points at a control-plane socket.
        assert handle.env().get("CONTAINER_HOST") is None
        assert handle.env().get("DOCKER_HOST") is None
    finally:
        handle.stop()
