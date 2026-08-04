"""Installed-authority adapter and updater CLI control-plane seam tests."""

from __future__ import annotations

from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path
import shutil
import sys
from typing import Any, Callable, Mapping

import pytest


ROOT = Path(__file__).resolve().parents[1]
for source in (
    ROOT,
    ROOT / "packages/release-contracts/src",
    ROOT / "packages/governed-runner/src",
    ROOT / "packages/updater/src",
):
    if str(source) not in sys.path:
        sys.path.insert(0, str(source))

from stateport_release import (  # noqa: E402
    canonical_digest,
    validate_update_authority_link,
    validate_update_receipt,
    validate_update_status,
)
from stateport_release.cosign import (  # noqa: E402
    bundle_slot,
    retain_bundle,
    signature_bundle_name,
)
from stateport_updater import UpdateEngine, UpdateError, UpdateStore  # noqa: E402
from stateport_updater.authority import UpdateAuthorityError, _validate_receipt  # noqa: E402
from stateport_updater.cli import main  # noqa: E402
from stateport_updater.engine import TARGET_ID  # noqa: E402
from stateport_updater.installed import (  # noqa: E402
    AUTHORIZATION_BUNDLE_SCHEMA,
    IDENTITY_SCHEMA,
    ControlPlaneBinding,
    InstalledAuthorityAdapter,
)
from scripts.test_stateport_updater import (  # noqa: E402
    NOW,
    POLICY,
    FixtureHost,
    OneShotCrash,
    SimulatedCrash,
    _EphemeralTestVerifier,
    initialized_engine,
    initialized_pinned_engine,
)


INSTALLER_DIGEST = "sha256:" + "0" * 64
INSTALLER_ORIGIN = "https://github.com/stateport/stateport-installer.git"
INSTALLER_VERSION = "0.1.0"
INSTALLER_ACTOR = "stateport-installer"
UPDATER_ROOT = "updater"


def inject(tmp_path: Path) -> dict[str, Any]:
    store = UpdateStore.open_existing(tmp_path / UPDATER_ROOT)
    return InstalledAuthorityAdapter.install(
        store,
        installer_digest=INSTALLER_DIGEST,
        installer_origin=INSTALLER_ORIGIN,
        installer_version=INSTALLER_VERSION,
        actor_id=INSTALLER_ACTOR,
        clock=lambda: NOW,
    )


def adapter_engine(
    tmp_path: Path,
    host: FixtureHost,
    *,
    failpoint: Callable[[str], None] | None = None,
) -> tuple[UpdateEngine, InstalledAuthorityAdapter]:
    store = UpdateStore.open_existing(tmp_path / UPDATER_ROOT)
    adapter = InstalledAuthorityAdapter(store, clock=lambda: NOW)
    engine = UpdateEngine(
        store,
        host,
        adapter,
        verification_policy=POLICY,
        signature_verifier=_EphemeralTestVerifier(),
        clock=lambda: NOW,
        failpoint=failpoint,
    )
    return engine, adapter


def binding(host: FixtureHost) -> ControlPlaneBinding:
    return ControlPlaneBinding(
        host=host,
        signature_verifier=_EphemeralTestVerifier(),
        verification_policy=POLICY,
        clock=lambda: NOW,
    )


def cli_args(tmp_path: Path, *argv: str) -> list[str]:
    return ["--state-root", str(tmp_path / UPDATER_ROOT), *argv]


def payload(capsysbinary: pytest.CaptureFixture[bytes]) -> Any:
    return json.loads(capsysbinary.readouterr().out)


def test_install_injects_genesis_identity_from_durable_truth(tmp_path: Path) -> None:
    updater, _host, _authority, _successor, _document = initialized_engine(tmp_path)
    record = inject(tmp_path)
    store = UpdateStore.open_existing(tmp_path / UPDATER_ROOT)
    status = updater.status()
    native = os.lstat(store.root)

    assert record["schema"] == IDENTITY_SCHEMA
    assert record["installationId"] == store.installation_id
    assert record["releaseId"] == status["current"]["releaseId"]
    assert record["version"] == status["current"]["version"]
    assert record["signedPayloadDigest"] == status["current"]["signedPayloadDigest"]
    assert record["targetId"] == TARGET_ID
    assert record["channel"] == "alpha"
    assert record["stateRootDevice"] == int(native.st_dev)
    assert record["stateRootInode"] == int(native.st_ino)
    assert record["installerDigest"] == INSTALLER_DIGEST
    assert record["installerOrigin"] == INSTALLER_ORIGIN
    assert record["installerVersion"] == INSTALLER_VERSION
    assert record["actorId"] == INSTALLER_ACTOR
    assert record["predecessorReleaseId"] is None
    assert record["predecessorSignedPayloadDigest"] is None
    assert record["predecessorIdentityDigest"] is None
    body = {
        key: value for key, value in record.items() if key not in {"identityId", "identityDigest"}
    }
    assert canonical_digest(body) == record["identityDigest"]
    assert record["identityId"] == (
        f"installed_identity_{record['identityDigest'].removeprefix('sha256:')[:32]}"
    )
    admission = json.loads(
        next((tmp_path / UPDATER_ROOT / "release-admissions").glob("*.json")).read_text()
    )
    assert record["releaseIndexDigest"] == admission["releaseIndexDigest"]

    adapter = InstalledAuthorityAdapter(store, clock=lambda: NOW)
    identity_files = list(adapter.identity_dir.glob("*.json"))
    assert len(identity_files) == 1
    assert identity_files[0].stat().st_mode & 0o777 == 0o600
    assert adapter._current_identity() == record


def test_install_refuses_before_durable_status(tmp_path: Path) -> None:
    UpdateStore.create(tmp_path / UPDATER_ROOT)
    with pytest.raises(UpdateAuthorityError) as failure:
        inject(tmp_path)
    assert failure.value.code == "installed_status_missing"
    assert not (tmp_path / UPDATER_ROOT / "installed-authority").exists()


def test_install_injects_genesis_identity_for_pinned_admission(tmp_path: Path) -> None:
    initialized_pinned_engine(tmp_path)
    record = inject(tmp_path)
    admission = json.loads(
        next((tmp_path / UPDATER_ROOT / "release-admissions").glob("*.json")).read_text()
    )
    assert admission["trustMode"] == "pinned-public-key"
    assert record["releaseId"] == admission["releaseId"]
    assert record["releaseIndexDigest"] == admission["releaseIndexDigest"]
    assert record["signedPayloadDigest"] == admission["signedPayloadDigest"]


def test_install_refuses_second_injection(tmp_path: Path) -> None:
    initialized_engine(tmp_path)
    inject(tmp_path)
    with pytest.raises(UpdateAuthorityError) as failure:
        inject(tmp_path)
    assert failure.value.code == "installed_identity_exists"
    adapter = InstalledAuthorityAdapter(UpdateStore.open_existing(tmp_path / UPDATER_ROOT))
    assert len(list(adapter.identity_dir.glob("*.json"))) == 1


def test_installed_update_roundtrip_advances_identity_chain(tmp_path: Path) -> None:
    _updater, host, _authority, successor, _document = initialized_engine(tmp_path)
    store = UpdateStore.open_existing(tmp_path / UPDATER_ROOT)
    genesis = inject(tmp_path)
    engine, adapter = adapter_engine(tmp_path, host)

    plan = engine.plan(successor)
    authorization = adapter.reserve(plan)
    decision = authorization["decision"]
    assert decision["action"] == "apply_update"
    assert decision["actorId"] == INSTALLER_ACTOR
    assert decision["authorizedBy"] == {
        "type": "grant",
        "id": f"grant_installed_{store.installation_id}",
        "digest": genesis["identityDigest"],
    }
    assert decision["scope"] == {
        "repository": {
            "origin": INSTALLER_ORIGIN,
            "repositoryKey": store.installation_id,
            "repositoryRoot": str(store.root),
        },
        "branch": None,
        "sliceId": None,
        "applicationId": "stateport",
        "runId": plan["planDigest"],
        "paths": [str(store.root)],
    }
    assert decision["profile"] == "balanced"
    assert decision["configuredPolicy"] == decision["policy"] == "auto_with_receipt"

    receipt = engine.apply(plan["planId"], authorization)
    assert validate_update_receipt(receipt).document["result"] == "accepted"
    status = validate_update_status(engine.status()).document
    assert status["current"]["releaseId"].endswith("0.2.0-rc.1")

    head = adapter._current_identity()
    assert head["releaseId"] == status["current"]["releaseId"]
    assert head["signedPayloadDigest"] == status["current"]["signedPayloadDigest"]
    assert head["predecessorReleaseId"] == genesis["releaseId"]
    assert head["predecessorSignedPayloadDigest"] == genesis["signedPayloadDigest"]
    assert head["predecessorIdentityDigest"] == genesis["identityDigest"]
    assert head["releaseIndexDigest"] == receipt["releaseIndexDigest"]
    assert len(list(adapter.identity_dir.glob("*.json"))) == 2

    request_id = decision["requestId"]
    assert adapter.recover_claim(request_id) is not None
    terminal = adapter.terminal_receipt(request_id)
    assert terminal is not None
    _validate_receipt(terminal)
    assert terminal["result"] == {
        "status": "succeeded",
        "code": None,
        "summary": "StatePort accepted the exact verified successor",
        "resource": terminal["result"]["resource"],
    }
    assert terminal["authorizedBy"]["digest"] == genesis["identityDigest"]
    record = json.loads((adapter.reservations_dir / f"{request_id}.json").read_text())
    assert record["identityDigest"] == genesis["identityDigest"]

    links = list((tmp_path / UPDATER_ROOT / "authority-links").glob("*.json"))
    assert len(links) == 1
    assert validate_update_authority_link(json.loads(links[0].read_text())).digest


def test_installed_rollback_roundtrip_returns_identity_to_predecessor(tmp_path: Path) -> None:
    _updater, host, _authority, successor, _document = initialized_engine(tmp_path)
    genesis = inject(tmp_path)
    engine, adapter = adapter_engine(tmp_path, host)
    plan = engine.plan(successor)
    receipt = engine.apply(plan["planId"], adapter.reserve(plan))
    assert receipt["result"] == "accepted"
    host.current = host.accepted
    successor_identity = adapter._current_identity()

    rollback = engine.plan(operation="rollback")
    rollback_authorization = adapter.reserve(rollback)
    assert rollback_authorization["decision"]["action"] == "rollback_update"
    rollback_receipt = engine.apply(rollback["planId"], rollback_authorization)
    assert validate_update_receipt(rollback_receipt).document["operation"] == "rollback"
    status = validate_update_status(engine.status()).document
    assert status["current"]["releaseId"].endswith("0.1.0-rc.1")

    head = adapter._current_identity()
    assert head["releaseId"] == genesis["releaseId"]
    assert head["signedPayloadDigest"] == genesis["signedPayloadDigest"]
    assert head["identityDigest"] != genesis["identityDigest"]
    assert head["predecessorReleaseId"] == successor_identity["releaseId"]
    assert head["predecessorIdentityDigest"] == successor_identity["identityDigest"]
    assert len(list(adapter.identity_dir.glob("*.json"))) == 3
    terminal = adapter.terminal_receipt(rollback_authorization["decision"]["requestId"])
    assert terminal is not None
    _validate_receipt(terminal)


def test_copied_state_root_is_refused_as_foreign(tmp_path: Path) -> None:
    updater, host, _authority, successor, _document = initialized_engine(tmp_path)
    inject(tmp_path)
    copied = tmp_path / "copied-updater"
    shutil.copytree(tmp_path / UPDATER_ROOT, copied)
    foreign = InstalledAuthorityAdapter(
        UpdateStore.open_existing(copied),
        clock=lambda: NOW,
    )
    with pytest.raises(UpdateAuthorityError) as failure:
        foreign._current_identity()
    assert failure.value.code == "foreign_state_refused"

    plan = updater.plan(successor)
    with pytest.raises(UpdateAuthorityError) as reserve_failure:
        foreign.reserve(plan)
    assert reserve_failure.value.code == "foreign_state_refused"

    engine, adapter = adapter_engine(tmp_path, host)
    original = engine.plan(successor)
    assert adapter.reserve(original)["decision"]["action"] == "apply_update"


def test_forged_authorization_without_durable_reservation_is_refused(tmp_path: Path) -> None:
    _updater, host, _authority, successor, _document = initialized_engine(tmp_path)
    inject(tmp_path)
    engine, adapter = adapter_engine(tmp_path, host)
    plan = engine.plan(successor)
    forged_decision = adapter._decision(
        action="apply_update",
        run_id=plan["planDigest"],
        identity=adapter._current_identity(),
        decided_at="2026-08-01T12:00:00Z",
        estimated_seconds=3600,
    )
    forged_reservation = adapter._reservation(
        forged_decision,
        reserved_at="2026-08-01T12:00:00Z",
    )
    with pytest.raises(UpdateAuthorityError) as failure:
        adapter.validate_reservation(
            plan,
            {"decision": forged_decision, "reservation": forged_reservation},
        )
    assert failure.value.code == "authority_reservation_unknown"


def test_stale_authorization_after_accepted_update_is_refused(tmp_path: Path) -> None:
    _updater, host, _authority, successor, _document = initialized_engine(tmp_path)
    inject(tmp_path)
    engine, adapter = adapter_engine(tmp_path, host)
    plan = engine.plan(successor)
    authorization = adapter.reserve(plan)
    assert engine.apply(plan["planId"], authorization)["result"] == "accepted"

    with pytest.raises(UpdateError) as failure:
        engine.apply(plan["planId"], authorization)
    assert failure.value.code == "installed_identity_changed"
    with pytest.raises(UpdateAuthorityError) as refusal:
        adapter.reserve(plan)
    assert refusal.value.code == "authority_terminal_conflict"


def test_refused_reservation_is_receipted_not_executed(tmp_path: Path) -> None:
    _updater, host, _authority, successor, _document = initialized_engine(tmp_path)
    inject(tmp_path)
    engine, adapter = adapter_engine(tmp_path, host)
    plan = deepcopy(engine.plan(successor))
    plan["policy"]["channel"] = "stable"

    with pytest.raises(UpdateAuthorityError) as failure:
        adapter.reserve(plan)
    assert failure.value.code == "channel_mismatch"
    receipt = failure.value.receipt
    assert receipt is not None
    _validate_receipt(receipt)
    assert receipt["decision"] == "denied"
    assert receipt["result"]["status"] == "not_executed"
    assert receipt["result"]["code"] == "channel_mismatch"
    assert adapter.terminal_receipt(receipt["requestId"]) == receipt


def test_tampered_identity_record_breaks_status_binding(tmp_path: Path) -> None:
    _updater, host, _authority, successor, _document = initialized_engine(tmp_path)
    inject(tmp_path)
    engine, adapter = adapter_engine(tmp_path, host)
    plan = engine.plan(successor)

    identity_path = next(adapter.identity_dir.glob("*.json"))
    record = json.loads(identity_path.read_text())
    record["releaseId"] = "stateport-alpha-9.9.9-rc.9"
    record["version"] = "9.9.9-rc.9"
    body = {
        key: value for key, value in record.items() if key not in {"identityId", "identityDigest"}
    }
    digest = canonical_digest(body)
    identity_path.unlink()
    record["identityDigest"] = digest
    record["identityId"] = f"installed_identity_{digest.removeprefix('sha256:')[:32]}"
    replacement = adapter.identity_dir / f"{record['identityId']}.json"
    replacement.write_text(json.dumps(record), encoding="utf-8")
    replacement.chmod(0o600)

    with pytest.raises(UpdateAuthorityError) as failure:
        adapter.reserve(plan)
    assert failure.value.code == "installed_identity_unresolved"


def test_installed_crash_after_claim_recovers_through_reconcile(tmp_path: Path) -> None:
    _updater, host, _authority, successor, _document = initialized_engine(tmp_path)
    inject(tmp_path)
    engine, adapter = adapter_engine(
        tmp_path,
        host,
        failpoint=OneShotCrash("after_authority_claim_before_journal"),
    )
    plan = engine.plan(successor)
    authorization = adapter.reserve(plan)
    request_id = authorization["decision"]["requestId"]
    with pytest.raises(SimulatedCrash):
        engine.apply(plan["planId"], authorization)
    assert adapter.recover_claim(request_id) is not None
    assert adapter.terminal_receipt(request_id) is None
    assert len(list(adapter.identity_dir.glob("*.json"))) == 1

    reopened, _adapter = adapter_engine(tmp_path, host)
    recovered = reopened.reconcile()
    assert recovered["accepted"]["releaseId"].endswith("0.2.0-rc.1")
    terminal = adapter.terminal_receipt(request_id)
    assert terminal is not None
    _validate_receipt(terminal)
    assert len(list(adapter.identity_dir.glob("*.json"))) == 2
    assert len(list(adapter.receipts_dir.glob("*.json"))) == 1


def test_installed_crash_after_finalize_reconciles_without_duplicates(tmp_path: Path) -> None:
    _updater, host, _authority, successor, _document = initialized_engine(tmp_path)
    inject(tmp_path)
    engine, adapter = adapter_engine(
        tmp_path,
        host,
        failpoint=OneShotCrash("after_authority_finalize_before_journal"),
    )
    plan = engine.plan(successor)
    authorization = adapter.reserve(plan)
    request_id = authorization["decision"]["requestId"]
    with pytest.raises(SimulatedCrash):
        engine.apply(plan["planId"], authorization)
    persisted = adapter.terminal_receipt(request_id)
    assert persisted is not None
    assert len(list(adapter.identity_dir.glob("*.json"))) == 2

    reopened, _adapter = adapter_engine(tmp_path, host)
    recovered = reopened.reconcile()
    assert recovered["accepted"]["releaseId"].endswith("0.2.0-rc.1")
    assert adapter.terminal_receipt(request_id) == persisted
    assert len(list(adapter.receipts_dir.glob("*.json"))) == 1
    assert len(list(adapter.claims_dir.glob("*.json"))) == 1
    assert len(list(adapter.identity_dir.glob("*.json"))) == 2
    links = list((tmp_path / UPDATER_ROOT / "authority-links").glob("*.json"))
    assert len(links) == 1
    assert validate_update_authority_link(json.loads(links[0].read_text())).digest


def test_apply_rollback_refuse_without_authorization_before_state_root(
    tmp_path: Path,
    capsysbinary: pytest.CaptureFixture[bytes],
) -> None:
    absent = tmp_path / "absent"
    for command in ("apply", "rollback"):
        assert (
            main(
                [
                    "--state-root",
                    str(absent),
                    command,
                    "--plan-id",
                    "update_plan_" + "a" * 32,
                ]
            )
            == 3
        )
        assert payload(capsysbinary) == {
            "schema": "stateport.updater-error/v1",
            "code": "installed_authority_adapter_required",
            "status": "not_executed",
        }
    assert not absent.exists()


@pytest.mark.parametrize(
    "argv",
    [
        ["check", "--release-index", "candidate.release-index.json"],
        ["plan", "--release-index", "candidate.release-index.json"],
        ["plan", "--rollback"],
        ["reconcile"],
    ],
)
def test_control_plane_commands_fail_closed_without_binding(
    tmp_path: Path,
    capsysbinary: pytest.CaptureFixture[bytes],
    argv: list[str],
) -> None:
    initialized_engine(tmp_path)
    inject(tmp_path)
    assert main(cli_args(tmp_path, *argv)) == 3
    assert payload(capsysbinary) == {
        "schema": "stateport.updater-error/v1",
        "code": "installed_authority_adapter_required",
        "status": "not_executed",
    }


def test_apply_with_authorization_still_requires_control_plane(
    tmp_path: Path,
    capsysbinary: pytest.CaptureFixture[bytes],
) -> None:
    _updater, host, _authority, successor, _document = initialized_engine(tmp_path)
    inject(tmp_path)
    engine, adapter = adapter_engine(tmp_path, host)
    plan = engine.plan(successor)
    bundle = tmp_path / "authorization.json"
    bundle.write_text(
        json.dumps({"schema": AUTHORIZATION_BUNDLE_SCHEMA, **adapter.reserve(plan)}),
        encoding="utf-8",
    )
    bundle.chmod(0o600)
    assert (
        main(
            cli_args(
                tmp_path,
                "apply",
                "--plan-id",
                plan["planId"],
                "--authorization",
                str(bundle),
            )
        )
        == 3
    )
    assert payload(capsysbinary) == {
        "schema": "stateport.updater-error/v1",
        "code": "installed_authority_adapter_required",
        "status": "not_executed",
    }


def test_cli_check_plan_authorize_apply_roundtrip(
    tmp_path: Path,
    capsysbinary: pytest.CaptureFixture[bytes],
) -> None:
    _updater, host, _authority, successor, document = initialized_engine(tmp_path)
    genesis = inject(tmp_path)
    state_root = tmp_path / UPDATER_ROOT
    index = tmp_path / "successor.release-index.json"
    index.write_text(json.dumps(document), encoding="utf-8")

    def snapshot() -> dict[Path, bytes]:
        return {
            path.relative_to(state_root): path.read_bytes()
            for path in sorted(state_root.rglob("*"))
            if path.is_file()
        }

    before = snapshot()
    assert (
        main(
            cli_args(tmp_path, "check", "--release-index", str(index)),
            control_plane=binding(host),
        )
        == 0
    )
    checked = payload(capsysbinary)
    assert checked["result"] == "update_available"
    assert checked["successor"]["releaseId"].endswith("0.2.0-rc.1")
    assert snapshot() == before

    assert (
        main(
            cli_args(tmp_path, "plan", "--release-index", str(index)),
            control_plane=binding(host),
        )
        == 0
    )
    plan = payload(capsysbinary)
    assert plan["operation"] == "update"
    assert plan["authority"]["runId"] == plan["planDigest"]

    bundle = tmp_path / "authorization.json"
    assert (
        main(
            cli_args(
                tmp_path,
                "authorize",
                "--plan-id",
                plan["planId"],
                "--output",
                str(bundle),
            )
        )
        == 0
    )
    assert payload(capsysbinary)["result"] == "authorization_reserved"
    written = json.loads(bundle.read_text())
    assert written["schema"] == AUTHORIZATION_BUNDLE_SCHEMA
    assert bundle.stat().st_mode & 0o777 == 0o600

    replay = tmp_path / "authorization-replay.json"
    assert (
        main(
            cli_args(
                tmp_path,
                "authorize",
                "--plan-id",
                plan["planId"],
                "--output",
                str(replay),
            )
        )
        == 0
    )
    payload(capsysbinary)
    assert json.loads(replay.read_text()) == written

    assert (
        main(
            cli_args(
                tmp_path,
                "apply",
                "--plan-id",
                plan["planId"],
                "--authorization",
                str(bundle),
            ),
            control_plane=binding(host),
        )
        == 0
    )
    assert payload(capsysbinary)["result"] == "accepted"

    assert main(cli_args(tmp_path, "status")) == 0
    status = payload(capsysbinary)
    assert status["current"]["releaseId"].endswith("0.2.0-rc.1")
    adapter = InstalledAuthorityAdapter(UpdateStore.open_existing(state_root))
    head = adapter._current_identity()
    assert head["releaseId"] == status["current"]["releaseId"]
    assert head["predecessorIdentityDigest"] == genesis["identityDigest"]

    assert main(cli_args(tmp_path, "plan", "--rollback"), control_plane=binding(host)) == 0
    assert payload(capsysbinary)["operation"] == "rollback"


def test_cli_policy_show_and_set_roundtrip(
    tmp_path: Path,
    capsysbinary: pytest.CaptureFixture[bytes],
) -> None:
    initialized_engine(tmp_path)
    inject(tmp_path)
    assert main(cli_args(tmp_path, "policy")) == 0
    assert payload(capsysbinary)["mode"] == "download-and-notify"

    assert (
        main(
            cli_args(
                tmp_path,
                "policy",
                "set",
                "--mode",
                "scheduled",
                "--schedule-days",
                "1,3,5",
                "--schedule-start-minute",
                "120",
            )
        )
        == 0
    )
    changed = payload(capsysbinary)
    assert changed["policy"]["mode"] == "scheduled"
    assert changed["policy"]["schedule"] == {
        "daysOfWeek": [1, 3, 5],
        "startMinuteUtc": 120,
    }
    assert main(cli_args(tmp_path, "policy")) == 0
    assert payload(capsysbinary)["mode"] == "scheduled"

    adapter = InstalledAuthorityAdapter(UpdateStore.open_existing(tmp_path / UPDATER_ROOT))
    receipts = [json.loads(path.read_text()) for path in adapter.receipts_dir.glob("*.json")]
    assert len(receipts) == 1
    _validate_receipt(receipts[0])
    assert receipts[0]["action"] == "modify_update_policy"
    assert receipts[0]["result"]["status"] == "succeeded"


def test_cli_policy_set_requires_schedule_for_scheduled_mode(
    tmp_path: Path,
    capsysbinary: pytest.CaptureFixture[bytes],
) -> None:
    initialized_engine(tmp_path)
    inject(tmp_path)
    assert main(cli_args(tmp_path, "policy", "set", "--mode", "scheduled")) == 2
    assert payload(capsysbinary) == {
        "schema": "stateport.updater-error/v1",
        "code": "policy_invalid",
        "status": "not_executed",
    }


def test_cli_policy_set_requires_installed_authority(
    tmp_path: Path,
    capsysbinary: pytest.CaptureFixture[bytes],
) -> None:
    initialized_engine(tmp_path)
    assert main(cli_args(tmp_path, "policy", "set", "--mode", "notify")) == 3
    assert payload(capsysbinary) == {
        "schema": "stateport.updater-error/v1",
        "code": "installed_authority_adapter_required",
        "status": "not_executed",
    }


def test_cli_reconcile_converges_installed_crash(
    tmp_path: Path,
    capsysbinary: pytest.CaptureFixture[bytes],
) -> None:
    _updater, host, _authority, successor, _document = initialized_engine(tmp_path)
    inject(tmp_path)
    engine, adapter = adapter_engine(
        tmp_path,
        host,
        failpoint=OneShotCrash("after_authority_claim_before_journal"),
    )
    plan = engine.plan(successor)
    authorization = adapter.reserve(plan)
    with pytest.raises(SimulatedCrash):
        engine.apply(plan["planId"], authorization)
    assert adapter.terminal_receipt(authorization["decision"]["requestId"]) is None

    assert main(cli_args(tmp_path, "reconcile"), control_plane=binding(host)) == 0
    recovered = payload(capsysbinary)
    assert recovered["accepted"]["releaseId"].endswith("0.2.0-rc.1")
    assert adapter.terminal_receipt(authorization["decision"]["requestId"]) is not None


def test_control_plane_environment_seam(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsysbinary: pytest.CaptureFixture[bytes],
) -> None:
    _updater, _host, _authority, _successor, document = initialized_engine(tmp_path)
    inject(tmp_path)
    module = tmp_path / "fixture_control_plane.py"
    module.write_text(
        "\n".join(
            [
                "from scripts.test_stateport_updater import (",
                "    NOW,",
                "    POLICY,",
                "    FixtureHost,",
                "    _EphemeralTestVerifier,",
                ")",
                "from stateport_updater.installed import ControlPlaneBinding",
                "",
                "",
                "def build_binding(state_root):",
                "    return ControlPlaneBinding(",
                "        host=FixtureHost(),",
                "        signature_verifier=_EphemeralTestVerifier(),",
                "        verification_policy=POLICY,",
                "        clock=lambda: NOW,",
                "    )",
                "",
            ]
        ),
        encoding="utf-8",
    )
    monkeypatch.syspath_prepend(str(tmp_path))
    monkeypatch.setenv(
        "STATEPORT_UPDATER_CONTROL_PLANE",
        "fixture_control_plane:build_binding",
    )
    index = tmp_path / "successor.release-index.json"
    index.write_text(json.dumps(document), encoding="utf-8")
    assert main(cli_args(tmp_path, "check", "--release-index", str(index))) == 0
    assert payload(capsysbinary)["result"] == "update_available"


def test_control_plane_environment_seam_rejects_malformed_spec(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsysbinary: pytest.CaptureFixture[bytes],
) -> None:
    initialized_engine(tmp_path)
    inject(tmp_path)
    monkeypatch.setenv("STATEPORT_UPDATER_CONTROL_PLANE", "not-a-module-spec")
    assert main(cli_args(tmp_path, "reconcile")) == 3
    assert payload(capsysbinary) == {
        "schema": "stateport.updater-error/v1",
        "code": "control_plane_binding_invalid",
        "status": "not_executed",
    }


def test_control_plane_binding_without_host_seam_is_refused(
    tmp_path: Path,
    capsysbinary: pytest.CaptureFixture[bytes],
) -> None:
    initialized_engine(tmp_path)
    inject(tmp_path)
    broken = ControlPlaneBinding(
        host=object(),
        signature_verifier=_EphemeralTestVerifier(),
        verification_policy=POLICY,
    )
    assert main(cli_args(tmp_path, "reconcile"), control_plane=broken) == 3
    assert payload(capsysbinary) == {
        "schema": "stateport.updater-error/v1",
        "code": "control_plane_binding_invalid",
        "status": "not_executed",
    }


# ---------------------------------------------------------------------------
# CLI content-addressed signature-bundle retention
# ---------------------------------------------------------------------------

SUCCESSOR_BUNDLE = (
    b'{"mediaType":"application/vnd.sigstore.bundle.v0.3+json","fixture":"successor"}\n'
)
FOREIGN_BUNDLE = b'{"mediaType":"application/vnd.sigstore.bundle.v0.3+json","fixture":"foreign"}\n'


class _RetainingTestVerifier(_EphemeralTestVerifier):
    """Ephemeral proofs, but real create-only content-addressed retention."""

    def __init__(self, bundle_root: Path) -> None:
        super().__init__()
        self._bundle_root = bundle_root

    def retain_bundle(self, source: Path, signature: Mapping[str, Any]) -> Path:
        return retain_bundle(self._bundle_root, source, signature)


def _retaining_binding(host: FixtureHost, bundle_root: Path) -> ControlPlaneBinding:
    return ControlPlaneBinding(
        host=host,
        signature_verifier=_RetainingTestVerifier(bundle_root),
        verification_policy=POLICY,
        clock=lambda: NOW,
    )


def _staged_successor(
    tmp_path: Path,
    document: dict[str, Any],
    *,
    bundle_bytes: bytes = SUCCESSOR_BUNDLE,
    record_bytes: bytes | None = None,
) -> tuple[Path, dict[str, Any]]:
    staged_document = deepcopy(document)
    recorded = staged_document["signatures"][0]["bundle"]
    bound = bundle_bytes if record_bytes is None else record_bytes
    recorded["digest"] = "sha256:" + hashlib.sha256(bound).hexdigest()
    recorded["size"] = len(bound)
    staging = tmp_path / "release-successor"
    staging.mkdir()
    (staging / signature_bundle_name(staged_document["signatures"][0])).write_bytes(bundle_bytes)
    index = staging / "release-index.json"
    index.write_text(json.dumps(staged_document), encoding="utf-8")
    return index, staged_document


def test_cli_check_retains_the_successor_bundle_in_the_durable_root(
    tmp_path: Path,
    capsysbinary: pytest.CaptureFixture[bytes],
) -> None:
    _updater, host, _authority, _successor, document = initialized_engine(tmp_path)
    inject(tmp_path)
    state_root = tmp_path / UPDATER_ROOT
    durable = state_root / "bundles"
    durable.mkdir()
    index, staged = _staged_successor(tmp_path, document)

    assert (
        main(
            cli_args(tmp_path, "check", "--release-index", str(index)),
            control_plane=_retaining_binding(host, durable),
        )
        == 0
    )
    assert payload(capsysbinary)["result"] == "update_available"
    slot = bundle_slot(durable, staged["signatures"][0])
    assert slot.is_file() and not slot.is_symlink()
    assert slot.read_bytes() == SUCCESSOR_BUNDLE
    assert slot.stat().st_mode & 0o777 == 0o600

    # Re-admission of the exact same release is idempotent.
    assert (
        main(
            cli_args(tmp_path, "check", "--release-index", str(index)),
            control_plane=_retaining_binding(host, durable),
        )
        == 0
    )
    payload(capsysbinary)
    assert slot.read_bytes() == SUCCESSOR_BUNDLE


def test_cli_check_refuses_a_successor_bundle_that_diverges_from_the_record(
    tmp_path: Path,
    capsysbinary: pytest.CaptureFixture[bytes],
) -> None:
    _updater, host, _authority, _successor, document = initialized_engine(tmp_path)
    inject(tmp_path)
    durable = tmp_path / UPDATER_ROOT / "bundles"
    durable.mkdir()
    index, _staged = _staged_successor(tmp_path, document, record_bytes=FOREIGN_BUNDLE)

    assert (
        main(
            cli_args(tmp_path, "check", "--release-index", str(index)),
            control_plane=_retaining_binding(host, durable),
        )
        == 3
    )
    assert payload(capsysbinary) == {
        "schema": "stateport.updater-error/v1",
        "code": "release_bundle_retention_refused",
        "status": "not_executed",
    }
    assert list(durable.iterdir()) == []


def test_cli_check_refuses_a_tampered_retained_bundle_slot(
    tmp_path: Path,
    capsysbinary: pytest.CaptureFixture[bytes],
) -> None:
    _updater, host, _authority, _successor, document = initialized_engine(tmp_path)
    inject(tmp_path)
    durable = tmp_path / UPDATER_ROOT / "bundles"
    durable.mkdir()
    index, staged = _staged_successor(tmp_path, document)
    slot = bundle_slot(durable, staged["signatures"][0])
    slot.parent.mkdir(parents=True)
    slot.write_bytes(b'{"tampered":true}\n')

    assert (
        main(
            cli_args(tmp_path, "check", "--release-index", str(index)),
            control_plane=_retaining_binding(host, durable),
        )
        == 3
    )
    assert payload(capsysbinary)["code"] == "release_bundle_retention_refused"
