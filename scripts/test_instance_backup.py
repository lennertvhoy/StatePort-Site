#!/usr/bin/env python3
"""Focused tests for deterministic and safe local instance backups."""

from __future__ import annotations

import io
import json
import os
from pathlib import Path
import stat
import sys
import tarfile
import tempfile
import zipfile
from unittest import mock

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "packages" / "instance-backup" / "src"))

import instance_backup
from instance_backup import (
    BACKUP_FORMAT,
    BackupConflictError,
    BackupError,
    BackupIntegrityError,
    UnsafePathError,
    create_backup,
    read_manifest,
    restore_backup,
    restore_staging_retained,
)


def _fixture(root: Path) -> Path:
    instance = root / "instance"
    (instance / ".statedd").mkdir(parents=True)
    (instance / "state").mkdir()
    (instance / "instance.yaml").write_text(
        "metadata:\n  id: backup-test\n  name: Synthetic Backup Test\n", encoding="utf-8"
    )
    lock = {
        "formatVersion": "statedd.lock/v1",
        "instanceId": "backup-test",
        "template": {
            "id": "synthetic-template",
            "source": {
                "formatVersion": "stateport.source/v1",
                "kind": "local",
                "sourceClass": "synthetic_fixture",
                "sourceDigest": "sha256:" + "1" * 64,
                "checkoutLocation": str(root / "not-in-identity"),
            },
        },
        "files": [
            {"path": "instance.yaml", "owner": "instance", "sensitivity": "private"},
            {"path": ".statedd/lock.yaml", "owner": "generated", "sensitivity": "internal"},
            {"path": "state/notes.md", "owner": "instance", "sensitivity": "private"},
        ],
    }
    (instance / ".statedd/lock.yaml").write_text(json.dumps(lock, sort_keys=True) + "\n", encoding="utf-8")
    (instance / "state/notes.md").write_text("synthetic state\n", encoding="utf-8")
    return instance


def test_deterministic_tar_and_zip_manifest_and_restrictive_permissions() -> None:
    with tempfile.TemporaryDirectory() as raw:
        root = Path(raw)
        instance = _fixture(root)
        tar_one = root / "one.tar"
        tar_two = root / "two.tar"
        zip_one = root / "one.zip"
        first = create_backup(instance, tar_one)
        second = create_backup(instance, tar_two)
        zipped = create_backup(instance, zip_one)

        assert tar_one.read_bytes() == tar_two.read_bytes()
        assert first.manifest == second.manifest
        assert first.manifest["formatVersion"] == BACKUP_FORMAT
        assert first.manifest["instanceId"] == "backup-test"
        assert first.manifest["sourceIdentity"]["sourceDigest"].startswith("sha256:")
        assert first.manifest["sourceIdentity"].get("checkoutLocation") is None
        assert [entry["path"] for entry in first.manifest["ownership"]] == sorted(
            entry["path"] for entry in first.manifest["ownership"]
        )
        assert {entry["owner"] for entry in first.manifest["files"]} == {"instance", "generated"}
        assert stat.S_IMODE(tar_one.stat().st_mode) == 0o600
        assert zipped.manifest["archiveDigest"] == first.manifest["archiveDigest"]
        assert read_manifest(zip_one)["archiveDigest"] == first.manifest["archiveDigest"]
        assert read_manifest(zip_one)["archive"]["format"] == "zip"


def test_backup_excludes_host_git_metadata() -> None:
    with tempfile.TemporaryDirectory() as raw:
        root = Path(raw)
        instance = _fixture(root)
        (instance / ".git/hooks").mkdir(parents=True)
        (instance / ".git/config").write_text("credential sentinel\n", encoding="utf-8")
        (instance / ".git/hooks/post-commit").write_text("hook sentinel\n", encoding="utf-8")
        archive = root / "without-git.tar"
        result = create_backup(instance, archive)
        assert not any(
            item["path"] == ".git" or item["path"].startswith(".git/")
            for item in result.manifest["files"]
        )
        restored = root / "restored-without-git"
        restore_backup(archive, restored, identity_policy="preserve")
        assert not (restored / ".git").exists()


def test_symlink_and_secret_source_boundaries_are_rejected() -> None:
    with tempfile.TemporaryDirectory() as raw:
        root = Path(raw)
        instance = _fixture(root)
        (instance / "state" / "escape").symlink_to(root / "outside.txt")
        try:
            create_backup(instance, root / "unsafe.tar")
        except UnsafePathError as exc:
            assert "symlink" in str(exc)
        else:
            raise AssertionError("symlinked instance content was accepted")

    with tempfile.TemporaryDirectory() as raw:
        root = Path(raw)
        instance = _fixture(root)
        (instance / ".env").write_text("not a real secret\n", encoding="utf-8")
        try:
            create_backup(instance, root / "secret.tar")
        except BackupError as exc:
            assert "secret" in str(exc)
        else:
            raise AssertionError("secret-looking content was accepted")


def test_dry_run_new_target_and_existing_unrelated_target_conflict() -> None:
    with tempfile.TemporaryDirectory() as raw:
        root = Path(raw)
        instance = _fixture(root)
        archive = root / "backup.tar"
        create_backup(instance, archive)
        target = root / "restored"
        result = restore_backup(archive, target, dry_run=True, identity_policy="preserve")
        assert result.dry_run is True
        assert result.instance_id == "backup-test"
        assert not target.exists()

        target.mkdir()
        (target / "unrelated.txt").write_text("keep me", encoding="utf-8")
        try:
            restore_backup(archive, target, identity_policy="preserve")
        except BackupConflictError as exc:
            assert "already exists" in str(exc)
        else:
            raise AssertionError("existing unrelated target was overwritten")


def test_restore_is_atomic_and_retains_staging_on_interruption() -> None:
    with tempfile.TemporaryDirectory() as raw:
        root = Path(raw)
        instance = _fixture(root)
        archive = root / "backup.zip"
        create_backup(instance, archive)
        target = root / "restored"

        with mock.patch.object(
            instance_backup,
            "_atomic_promote_new_directory",
            side_effect=OSError("simulated interruption"),
        ):
            try:
                restore_backup(archive, target, identity_policy="preserve")
            except OSError as exc:
                assert "simulated interruption" in str(exc)
            else:
                raise AssertionError("interrupted restore unexpectedly succeeded")
        assert not target.exists()
        retained = list(root.glob(".restored.restore-*"))
        assert len(retained) == 1
        assert (retained[0] / "state/notes.md").is_file()
        assert restore_staging_retained(target) is True


def test_restore_cleanup_preserves_replaced_staging_name() -> None:
    with tempfile.TemporaryDirectory() as raw:
        root = Path(raw)
        instance = _fixture(root)
        archive = root / "backup.tar"
        create_backup(instance, archive)
        target = root / "restored"
        original = root / ".restored.restore-original"

        def replace_then_interrupt(
            source: Path,
            _target: Path,
            *,
            expected_source_identity: tuple[int, int],
        ) -> None:
            assert expected_source_identity == (source.stat().st_dev, source.stat().st_ino)
            source.rename(original)
            source.mkdir(mode=0o700)
            (source / "foreign.txt").write_text("preserve\n", encoding="utf-8")
            raise OSError("staging replacement")

        with mock.patch.object(
            instance_backup,
            "_atomic_promote_new_directory",
            side_effect=replace_then_interrupt,
        ):
            with pytest.raises(OSError, match="staging replacement"):
                restore_backup(archive, target, identity_policy="preserve")
        replacements = list(root.glob(".restored.restore-*"))
        assert len(replacements) == 2
        foreign = next(path for path in replacements if path != original)
        assert (foreign / "foreign.txt").read_text(encoding="utf-8") == "preserve\n"
        assert (original / "state/notes.md").is_file()
        assert restore_staging_retained(target) is True


def test_restore_staging_inventory_fails_safe_on_dangling_parent_symlink(
    tmp_path: Path,
) -> None:
    dangling = tmp_path / "dangling"
    dangling.symlink_to(tmp_path / "missing", target_is_directory=True)
    assert restore_staging_retained(dangling / "restored") is True


def test_restore_no_replace_preserves_racing_target() -> None:
    with tempfile.TemporaryDirectory() as raw:
        root = Path(raw)
        instance = _fixture(root)
        archive = root / "backup.tar"
        create_backup(instance, archive)
        target = root / "restored"
        promote = instance_backup._atomic_promote_new_directory

        def race(
            source: Path,
            destination: Path,
            *,
            expected_source_identity: tuple[int, int],
        ) -> None:
            destination.mkdir(mode=0o700)
            (destination / "foreign.txt").write_text("preserve\n", encoding="utf-8")
            promote(source, destination, expected_source_identity=expected_source_identity)

        with mock.patch.object(instance_backup, "_atomic_promote_new_directory", side_effect=race):
            with pytest.raises(BackupConflictError, match="destination appeared"):
                restore_backup(archive, target, identity_policy="preserve")
        assert (target / "foreign.txt").read_text(encoding="utf-8") == "preserve\n"


def test_restore_rejects_tampering_and_supports_explicit_reidentification() -> None:
    with tempfile.TemporaryDirectory() as raw:
        root = Path(raw)
        instance = _fixture(root)
        archive = root / "backup.tar"
        create_backup(instance, archive)
        target = root / "new-instance"
        result = restore_backup(
            archive,
            target,
            identity_policy="reidentify",
            new_instance_id="backup-test-copy",
        )
        assert result.instance_id == "backup-test-copy"
        assert "id: \"backup-test-copy\"" in (target / "instance.yaml").read_text(encoding="utf-8")
        lock = json.loads((target / ".statedd/lock.yaml").read_text(encoding="utf-8"))
        assert lock["instanceId"] == "backup-test-copy"
        assert stat.S_IMODE((target / "state/notes.md").stat().st_mode) == 0o600
        assert stat.S_IMODE(target.stat().st_mode) == 0o700

        tampered = root / "tampered.tar"
        with tarfile.open(archive, "r") as source, tarfile.open(tampered, "w") as destination:
            for member in source.getmembers():
                data = source.extractfile(member).read() if member.isfile() else None
                if member.name == "files/state/notes.md":
                    data = b"tampered\n"
                    member.size = len(data)
                destination.addfile(member, io.BytesIO(data) if data is not None else None)
        try:
            read_manifest(tampered)
        except BackupIntegrityError:
            pass
        else:
            raise AssertionError("tampered archive was accepted")


def test_archive_traversal_and_zip_symlink_are_rejected() -> None:
    with tempfile.TemporaryDirectory() as raw:
        root = Path(raw)
        traversal = root / "traversal.zip"
        with zipfile.ZipFile(traversal, "w") as archive:
            archive.writestr("manifest.json", "{}")
            archive.writestr("files/../../escape", "bad")
        try:
            read_manifest(traversal)
        except (UnsafePathError, BackupIntegrityError):
            pass
        else:
            raise AssertionError("zip traversal was accepted")

        symlink = root / "symlink.zip"
        info = zipfile.ZipInfo("files/link")
        info.create_system = 3
        info.external_attr = (stat.S_IFLNK | 0o777) << 16
        with zipfile.ZipFile(symlink, "w") as archive:
            archive.writestr("manifest.json", "{}")
            archive.writestr(info, "../../escape")
        try:
            read_manifest(symlink)
        except (UnsafePathError, BackupIntegrityError):
            pass
        else:
            raise AssertionError("zip symlink was accepted")


def _write_resource_archive(path: Path, archive_format: str, payloads: list[tuple[str, bytes]]) -> None:
    if archive_format == "tar":
        with tarfile.open(path, "w") as archive:
            for name, data in payloads:
                info = tarfile.TarInfo(name)
                info.size = len(data)
                archive.addfile(info, io.BytesIO(data))
        return
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for name, data in payloads:
            archive.writestr(name, data)


def test_tar_and_compressed_zip_members_are_rejected_before_over_limit_materialization() -> None:
    with tempfile.TemporaryDirectory() as raw:
        root = Path(raw)
        oversized = b"\0" * 2048
        for archive_format in ("tar", "zip"):
            archive_path = root / f"oversized.{archive_format}"
            _write_resource_archive(
                archive_path,
                archive_format,
                [("manifest.json", b"{}"), ("files/state/large.bin", oversized)],
            )
            if archive_format == "zip":
                with zipfile.ZipFile(archive_path) as archive:
                    info = archive.getinfo("files/state/large.bin")
                    assert info.compress_size < info.file_size
            with mock.patch.object(instance_backup, "MAX_ARCHIVE_FILE_BYTES", 1024):
                try:
                    read_manifest(archive_path)
                except BackupIntegrityError as exc:
                    assert "bounded resource limit" in str(exc)
                else:
                    raise AssertionError(f"{archive_format} oversized member was materialized")


def test_archive_member_count_and_total_uncompressed_volume_are_bounded() -> None:
    with tempfile.TemporaryDirectory() as raw:
        root = Path(raw)
        count_archive = root / "count.zip"
        _write_resource_archive(
            count_archive,
            "zip",
            [
                ("manifest.json", b"{}"),
                ("files/state/one.bin", b"1"),
                ("files/state/two.bin", b"2"),
            ],
        )
        with mock.patch.object(instance_backup, "MAX_ARCHIVE_MEMBERS", 2):
            try:
                read_manifest(count_archive)
            except BackupIntegrityError as exc:
                assert "member count" in str(exc)
            else:
                raise AssertionError("archive member-count bomb was accepted")

        volume_archive = root / "volume.tar"
        _write_resource_archive(
            volume_archive,
            "tar",
            [
                ("manifest.json", b"{}"),
                ("files/state/one.bin", b"1" * 700),
                ("files/state/two.bin", b"2" * 700),
            ],
        )
        with (
            mock.patch.object(instance_backup, "MAX_ARCHIVE_FILE_BYTES", 1024),
            mock.patch.object(instance_backup, "MAX_ARCHIVE_MATERIALIZED_BYTES", 1200),
        ):
            try:
                read_manifest(volume_archive)
            except BackupIntegrityError as exc:
                assert "payload exceeds" in str(exc)
            else:
                raise AssertionError("archive total-uncompressed-volume bomb was accepted")


def test_backup_creation_refuses_an_over_limit_source_before_writing_an_archive() -> None:
    with tempfile.TemporaryDirectory() as raw:
        root = Path(raw)
        instance = _fixture(root)
        destination = root / "oversized.tar"
        with mock.patch.object(instance_backup, "MAX_ARCHIVE_FILE_BYTES", 8):
            try:
                create_backup(instance, destination)
            except BackupError as exc:
                assert "bounded backup limit" in str(exc)
            else:
                raise AssertionError("over-limit source file was archived")
        assert not destination.exists()


def test_backup_write_stays_bound_to_owned_descriptor_when_name_is_rebound() -> None:
    with tempfile.TemporaryDirectory() as raw:
        root = Path(raw)
        instance = _fixture(root)
        destination = root / "backup.tar"
        original = root / ".backup-original"
        victim = root / "victim.txt"
        victim.write_text("do not overwrite\n", encoding="utf-8")
        write_tar = instance_backup._write_tar

        def rebind_then_write(handle: object, *args: object, **kwargs: object) -> None:
            staging = next(root.glob(".backup.tar.*.tmp"))
            staging.rename(original)
            staging.symlink_to(victim)
            write_tar(handle, *args, **kwargs)

        with mock.patch.object(instance_backup, "_write_tar", side_effect=rebind_then_write):
            with pytest.raises(BackupConflictError, match="staging name changed"):
                create_backup(instance, destination)
        assert victim.read_text(encoding="utf-8") == "do not overwrite\n"
        assert original.is_file() and original.stat().st_size == 0
        assert not destination.exists()


def test_backup_no_replace_preserves_racing_destination() -> None:
    with tempfile.TemporaryDirectory() as raw:
        root = Path(raw)
        instance = _fixture(root)
        destination = root / "backup.tar"
        rename_noreplace = instance_backup._renameat2_noreplace_file

        def race(parent_fd: int, source_name: str, target_name: str) -> None:
            destination.write_text("foreign destination\n", encoding="utf-8")
            rename_noreplace(parent_fd, source_name, target_name)

        with mock.patch.object(instance_backup, "_renameat2_noreplace_file", side_effect=race):
            with pytest.raises(BackupConflictError, match="destination appeared"):
                create_backup(instance, destination)
        assert destination.read_text(encoding="utf-8") == "foreign destination\n"


def test_backup_refuses_existing_destination_without_mutation() -> None:
    with tempfile.TemporaryDirectory() as raw:
        root = Path(raw)
        instance = _fixture(root)
        destination = root / "backup.tar"
        destination.write_text("existing\n", encoding="utf-8")
        with pytest.raises(BackupConflictError, match="already exists"):
            create_backup(instance, destination)
        assert destination.read_text(encoding="utf-8") == "existing\n"


if __name__ == "__main__":
    for name, test in sorted(globals().items()):
        if name.startswith("test_"):
            test()
    print("instance backup tests passed")
