from __future__ import annotations

from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
for relative in (
    "packages/persistent-app/src",
    "packages/statedd-core/src",
    "packages/template-validator/src",
    "packages/instance-backup/src",
    "packages/instance-catalog/src",
    "packages/diagnostics/src",
):
    sys.path.insert(0, str(ROOT / relative))

from stateport_persistent_app import LocalLayout, PersistentApp  # noqa: E402
from stateport_persistent_app.activity_receipts import ActivityReceiptStore  # noqa: E402


def _git(root: Path, *args: str) -> str:
    result = subprocess.run(["git", *args], cwd=root, check=True, text=True, stdout=subprocess.PIPE)
    return result.stdout.strip()


def _repo(root: Path) -> Path:
    root.mkdir(parents=True)
    _git(root, "init", "-q")
    _git(root, "config", "user.email", "fixture@example.invalid")
    _git(root, "config", "user.name", "Registration fixture")
    (root / "flake.nix").write_text("{ }\n", encoding="utf-8")
    _git(root, "add", "flake.nix")
    _git(root, "commit", "-q", "-m", "fixture")
    return root


def test_external_registration_persists_without_copying_or_mutating_source(tmp_path: Path) -> None:
    source = _repo(tmp_path / "nixos-homelab")
    original = (source / "flake.nix").read_bytes()
    layout = LocalLayout(tmp_path / "config", tmp_path / "data", tmp_path / "state")
    layout.initialize()

    first = PersistentApp(layout).register_external_repository(
        source,
        instance_id="nixos-infrastructure",
        name="NixOS Infrastructure",
        application_id="nixos-infrastructure",
        source={"sourceKind": "local", "headCommit": _git(source, "rev-parse", "HEAD")},
    )
    assert first["path"] == source.resolve().as_posix()
    assert first["adoption"] == {"mode": "registered", "readOnly": True}
    assert (source / "flake.nix").read_bytes() == original
    assert not (layout.instances_root / "nixos-infrastructure").exists()

    reopened = PersistentApp(layout).catalog.get("nixos-infrastructure")
    assert reopened["pathState"] == "present"
    assert reopened["applicationId"] == "nixos-infrastructure"
    assert reopened["observedSource"]["headCommit"] == first["observedSource"]["headCommit"]


def test_external_registration_rejects_duplicate_and_detects_identity_drift(tmp_path: Path) -> None:
    source = _repo(tmp_path / "nixos-homelab")
    layout = LocalLayout(tmp_path / "config", tmp_path / "data", tmp_path / "state")
    layout.initialize()
    app = PersistentApp(layout)
    app.register_external_repository(source, instance_id="nixos-infrastructure", name="NixOS", application_id="nixos-infrastructure", source={"sourceKind": "local"})
    try:
        app.register_external_repository(source, instance_id="nixos-infrastructure-2", name="NixOS", application_id="nixos-infrastructure", source={"sourceKind": "local"})
    except ValueError as exc:
        assert "already registered" in str(exc)
    else:
        raise AssertionError("duplicate external path was accepted")

    moved = tmp_path / "moved"
    source.rename(moved)
    assert PersistentApp(layout).catalog.get("nixos-infrastructure")["pathState"] == "missing"


def test_import_receipt_is_durable_and_bounded(tmp_path: Path) -> None:
    store = ActivityReceiptStore(tmp_path / "activity.sqlite3")
    receipt = {
        "formatVersion": "stateport.repository-import-receipt/v1",
        "receiptId": "repository-import-1234567890abcdef12345678",
        "receiptType": "stateport.repository-import-receipt/v1",
        "action": "repository.import",
        "status": "completed",
        "sourceKind": "repository_import",
        "createdAt": "2026-07-16T00:00:00Z",
        "sourceIdentity": {"headCommit": "a" * 40},
    }
    store.record_receipt(instance_id="nixos-infrastructure", receipt=receipt)
    assert store.receipt_index("nixos-infrastructure")["receipts"][0]["receiptId"] == receipt["receiptId"]
    detail = store.receipt_detail("nixos-infrastructure", receipt["receiptId"])
    assert detail["receipt"]["payload"]["sourceIdentity"]["headCommit"] == "a" * 40
