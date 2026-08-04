"""Tests for the stable execution-host provisioning plan renderer."""

from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "packages" / "release-contracts" / "src"))

import provision_execution_host as provisioning  # noqa: E402
import test_release_contracts as fixtures  # noqa: E402
from stateport_release.contract import ReleaseContractError, verify_release_index  # noqa: E402


def _plan() -> dict:
    verified = verify_release_index(
        fixtures.release_index(), policy=fixtures._policy(), verifier=fixtures._EphemeralTestVerifier()
    )
    return provisioning.render_provisioning_plan(
        verified.target,
        verified.index.document["signed"]["images"],
        verification_basis="signature-verified-test",
    )


def test_plan_binds_exact_host_identity_and_contract() -> None:
    plan = _plan()
    assert plan["schema"] == "stateport.execution-host-provisioning/v1"
    assert plan["executionUser"] == "stateport-exec"
    assert plan["executionControlGroup"] == "stateport-execution-control"
    assert plan["allowedClientUser"] == "stateport-control"
    assert plan["socketDirectory"] == "/run/stateport/execution-control"
    assert plan["socketDirectoryMode"] == "0750"
    assert plan["socketMode"] == "0660"
    assert plan["planDigest"]

    tmpfiles = next(write for write in plan["writes"] if write["path"].endswith(".conf"))
    assert tmpfiles["content"] == (
        "d /run/stateport/execution-control 0750 stateport-exec stateport-execution-control -\n"
    )
    quadlets = [write for write in plan["writes"] if write["path"].endswith(".container")]
    assert len(quadlets) == 1
    assert quadlets[0]["path"] == (
        "/var/lib/stateport-exec/.config/containers/systemd/stateport-execution-host.container"
    )
    assert quadlets[0]["owner"] == "stateport-exec:stateport-exec"
    assert "%t/podman/podman.sock:/run/stateport-engine/podman.sock:rw" in quadlets[0]["content"]
    assert "stateport-execution-host@" in quadlets[0]["content"]
    assert "/run/podman/podman.sock" not in quadlets[0]["content"]
    assert "/var/run/docker.sock" not in quadlets[0]["content"]


def test_steps_are_ordered_and_confined() -> None:
    plan = _plan()
    order = [step["step"] for step in plan["steps"]]
    assert order == [
        "ensure-execution-control-group",
        "ensure-stateport-exec-user",
        "confine-control-plane-client",
        "enable-exec-user-linger",
        "write-confined-socket-tmpfiles",
        "install-stable-host-quadlets",
        "start-exec-user-engine-socket",
        "start-execution-host-daemon",
    ]
    flat = [argv for step in plan["steps"] for argv in step.get("commands", [])]
    assert ["groupadd", "--system", "stateport-execution-control"] in flat
    assert any(argv[0] == "useradd" and "stateport-exec" in argv for argv in flat)
    assert ["usermod", "--append", "--groups", "stateport-execution-control", "stateport-control"] in flat
    assert any(argv[-2:] == ["--now", "podman.socket"] for argv in flat)
    assert any(argv[-2:] == ["--now", "stateport-execution-host"] for argv in flat)
    # The plan is deterministic for a fixed verified release.
    assert _plan()["planDigest"] == plan["planDigest"]


def test_plan_refuses_a_target_without_stable_execution_host() -> None:
    value = fixtures.release_index()
    target = value["signed"]["targets"][0]
    target["executionHostMode"] = "none"
    target["executionContract"] = None
    target["hostServices"] = []
    with pytest.raises(ReleaseContractError, match="no stable execution host"):
        provisioning.render_provisioning_plan(
            target, value["signed"]["images"], verification_basis="test"
        )


def test_apply_receipts_every_step_and_refuses_failure(tmp_path: Path) -> None:
    plan = json.loads(json.dumps(_plan()))
    # Redirect writes into the test sandbox; command steps run against the fake runner.
    for write in plan["writes"]:
        write["path"] = str(tmp_path / Path(write["path"]).name)
    # Apply as non-root fails closed before any side effect.
    with pytest.raises(ReleaseContractError, match="as root"):
        provisioning.apply_plan(plan)

    calls: list[list[str]] = []

    def fake_runner(command, **kwargs):
        calls.append(list(command))
        if command[0] == "groupadd":
            return subprocess.CompletedProcess(command, 1, "", "groupadd: group 'stateport-execution-control' already exists")
        return subprocess.CompletedProcess(command, 0, "", "")

    import os

    original_geteuid = os.geteuid
    provisioning.os.geteuid = lambda: 0  # noqa: SLF001 (test double)
    try:
        receipts = provisioning.apply_plan(plan, runner=fake_runner)
    finally:
        provisioning.os.geteuid = original_geteuid  # noqa: SLF001
    assert all(receipt["result"] == "applied" for receipt in receipts if "step" in receipt)
    groupadd_receipt = next(r for r in receipts if r.get("step") == "ensure-execution-control-group")
    assert groupadd_receipt["returncode"] == 1  # idempotent "already exists" tolerated
    write_receipts = [r for r in receipts if "write" in r]
    assert len(write_receipts) == len(plan["writes"])

    def failing_runner(command, **kwargs):
        return subprocess.CompletedProcess(command, 1, "", "boom")

    provisioning.os.geteuid = lambda: 0  # noqa: SLF001
    try:
        with pytest.raises(ReleaseContractError, match="provisioning step"):
            provisioning.apply_plan(plan, runner=failing_runner)
    finally:
        provisioning.os.geteuid = original_geteuid  # noqa: SLF001
