from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

from instance_backup import BackupError, create_backup, read_manifest, restore_backup


class PortabilityError(ValueError):
    """A portable instance package is invalid or unsafe."""


_TRANSIENT_PREFIXES = (".stateport/", ".statedd/runtime/", "engine_sessions/")


def _archive_file_digest(path: Path) -> str:
    """Return an exact archive-byte digest without loading an archive into memory."""

    if path.is_symlink() or not path.is_file():
        raise PortabilityError("portable archive must be a regular file")
    digest = hashlib.sha256()
    try:
        with path.open("rb") as handle:
            for block in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(block)
    except OSError as exc:
        raise PortabilityError("portable archive could not be read") from exc
    return "sha256:" + digest.hexdigest()


def _portable_manifest(manifest: dict[str, Any]) -> dict[str, Any]:
    files = manifest.get("files", [])
    if not isinstance(files, list):
        raise PortabilityError("portable package manifest files must be a list")
    for item in files:
        path = item.get("path") if isinstance(item, dict) else None
        if not isinstance(path, str) or path.startswith("/") or "\\" in path or ".." in path.split("/"):
            raise PortabilityError("portable package contains an unsafe path")
        if any(path == prefix[:-1] or path.startswith(prefix) for prefix in _TRANSIENT_PREFIXES):
            raise PortabilityError(f"portable package contains transient engine/runtime state: {path}")
    return {
        "formatVersion": "stateport.instance-portable/v1",
        "backupFormat": manifest.get("formatVersion"),
        "instanceId": manifest.get("instanceId"),
        "sourceIdentity": manifest.get("sourceIdentity"),
        "archiveDigest": manifest.get("archiveDigest"),
        "fileCount": len(files),
        "engineSessions": {"included": False, "reason": "portable packages contain canonical instance files only"},
        "machinePaths": {"included": False, "reason": "manifest paths are repository-relative"},
    }


def export_portable(instance_root: str | Path, archive_path: str | Path) -> dict[str, Any]:
    archive = Path(archive_path)
    temporary = archive.with_name(f".{archive.name}.stateport-exporting")
    try:
        result = create_backup(instance_root, temporary, archive_format="zip")
        portable = _portable_manifest(result.manifest)
    except (BackupError, OSError, TypeError) as exc:
        temporary.unlink(missing_ok=True)
        raise PortabilityError(str(exc)) from exc
    temporary.replace(archive)
    return {"formatVersion": "stateport.instance-portable/v1", "archive": archive.as_posix(), "archiveDigest": result.archive_digest, "archiveFileDigest": result.archive_file_digest, "manifest": portable}


def inspect_portable(archive_path: str | Path) -> dict[str, Any]:
    archive = Path(archive_path)
    try:
        manifest = read_manifest(archive)
        portable = _portable_manifest(manifest)
        portable["archiveFileDigest"] = _archive_file_digest(archive)
        return portable
    except (BackupError, OSError, TypeError) as exc:
        raise PortabilityError(str(exc)) from exc


def import_portable(archive_path: str | Path, destination: str | Path, *, dry_run: bool = False, new_instance_id: str | None = None) -> dict[str, Any]:
    portable = inspect_portable(archive_path)
    try:
        result = restore_backup(archive_path, destination, dry_run=dry_run, identity_policy="reidentify" if new_instance_id else "preserve", new_instance_id=new_instance_id)
    except (BackupError, OSError, TypeError) as exc:
        raise PortabilityError(str(exc)) from exc
    return {"formatVersion": "stateport.instance-portable-import/v1", "archiveDigest": result.archive_digest, "destination": result.target_path.as_posix(), "instanceId": result.instance_id, "fileCount": result.file_count, "dryRun": result.dry_run, "manifest": portable}
