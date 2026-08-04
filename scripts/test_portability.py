from __future__ import annotations

import hashlib
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
for relative in ("packages/portable-execution/src", "packages/persistent-app/src", "packages/statedd-core/src", "packages/template-validator/src", "packages/instance-catalog/src", "packages/instance-backup/src", "packages/execution-host/src", "packages/external-engine-runtime/src", "packages/codex-adapter/src", "packages/run-bundle/src"):
    sys.path.insert(0, str(ROOT / relative))

from stateport_portable_execution import PortabilityError, export_portable, import_portable, inspect_portable  # noqa: E402


def _instance(root: Path) -> Path:
    (root / ".statedd").mkdir(parents=True)
    (root / "state").mkdir()
    (root / ".statedd" / "lock.yaml").write_text("formatVersion: statedd.lock/v1\ninstanceId: demo\nsource:\n  repository: synthetic\n  commit: abc\n  tree: tree\nfiles:\n  - path: state/value.txt\n    owner: instance\n    sensitivity: private\n", encoding="utf-8")
    (root / "instance.yaml").write_text("formatVersion: statedd.instance/v1\nmetadata:\n  id: demo\n  name: Demo\n", encoding="utf-8")
    (root / "state" / "value.txt").write_text("durable\n", encoding="utf-8")
    return root


def test_portable_export_is_deterministic_and_excludes_engine_sessions(tmp_path: Path) -> None:
    root = _instance(tmp_path / "instance")
    first = export_portable(root, tmp_path / "one.zip")
    second = export_portable(root, tmp_path / "two.zip")
    assert first["archiveDigest"] == second["archiveDigest"]
    assert hashlib.sha256((tmp_path / "one.zip").read_bytes()).digest() == hashlib.sha256((tmp_path / "two.zip").read_bytes()).digest()
    assert inspect_portable(tmp_path / "one.zip")["engineSessions"]["included"] is False


def test_portable_import_supports_dry_run_and_atomic_move(tmp_path: Path) -> None:
    root = _instance(tmp_path / "instance")
    export_portable(root, tmp_path / "portable.zip")
    dry = import_portable(tmp_path / "portable.zip", tmp_path / "dry", dry_run=True)
    assert dry["dryRun"] is True
    assert not (tmp_path / "dry").exists()
    moved = import_portable(tmp_path / "portable.zip", tmp_path / "moved", new_instance_id="moved")
    assert moved["instanceId"] == "moved"
    assert (tmp_path / "moved" / "state" / "value.txt").read_text(encoding="utf-8") == "durable\n"


def test_portable_export_rejects_engine_session_files(tmp_path: Path) -> None:
    root = _instance(tmp_path / "instance")
    (root / "engine_sessions").mkdir()
    (root / "engine_sessions" / "session.json").write_text("not canonical\n", encoding="utf-8")
    try:
        export_portable(root, tmp_path / "unsafe.zip")
    except PortabilityError as exc:
        assert "transient" in str(exc)
    else:
        raise AssertionError("engine session state must not enter a portable package")
