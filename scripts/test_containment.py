from __future__ import annotations

from copy import deepcopy
from html import escape
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
import install_transport
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
            "download/0.1.0-alpha.5": "eaa1ca6a67844259860917442a95c891d097939f",
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


class CurrentBootstrapTests(unittest.TestCase):
    def test_mutable_probe_bootstrap_is_bound_separately_from_immutable_alpha5(self) -> None:
        installer = ROOT / "download/install.sh"
        versioned = ROOT / "download/0.1.0-alpha.5/install.sh"
        self.assertNotEqual(installer.read_bytes(), versioned.read_bytes())
        self.assertEqual(
            hashlib.sha256(installer.read_bytes()).hexdigest(),
            install_transport.BOOTSTRAP_SHA256,
        )
        self.assertEqual(len(installer.read_bytes()), install_transport.BOOTSTRAP_SIZE)
        self.assertEqual(
            hashlib.sha256(versioned.read_bytes()).hexdigest(),
            install_transport.VERSIONED_BOOTSTRAP_SHA256,
        )
        self.assertEqual(len(versioned.read_bytes()), install_transport.VERSIONED_BOOTSTRAP_SIZE)
        for image_id, digest in install_transport.MANIFEST_DIGESTS.items():
            manifest = ROOT / "download/alpha5-manifests" / f"{image_id}.json"
            self.assertEqual(hashlib.sha256(manifest.read_bytes()).hexdigest(), digest)

    def test_program_has_valid_shell_syntax(self) -> None:
        installer = ROOT / "download/install.sh"
        syntax = subprocess.run(
            ["/bin/sh", "-n", str(installer)],
            check=False,
            capture_output=True,
            env={"LC_ALL": "C", "PATH": os.environ.get("PATH", "")},
        )
        self.assertEqual(syntax.returncode, 0, syntax.stderr.decode("utf-8"))

    def _run_transport(self, response: bytes, *, execute: bool) -> tuple[subprocess.CompletedProcess[str], Path]:
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        root = Path(temporary.name)
        response_path = root / "response"
        response_path.write_bytes(response)
        shell_log = root / "shell.log"

        curl = root / "curl"
        curl.write_text(
            "#!/bin/sh\n"
            "while [ \"$#\" -gt 0 ]; do\n"
            "  case \"$1\" in\n"
            "    --output) output=$2; shift 2 ;;\n"
            "    *) shift ;;\n"
            "  esac\n"
            "done\n"
            "cp \"$BOOTSTRAP_RESPONSE\" \"$output\"\n",
            encoding="utf-8",
        )
        curl.chmod(0o755)
        shell = root / "checked-sh"
        shell.write_text(
            "#!/bin/sh\n"
            "printf '%s\\n' \"$*\" >> \"$SHELL_LOG\"\n"
            "if [ \"${2-}\" = --materialization-preflight ]; then\n"
            f"  printf '%s\\n' '{install_transport.PREFLIGHT_SUCCESS}'\n"
            "  exit 0\n"
            "fi\n"
            "exec /bin/sh \"$@\"\n",
            encoding="utf-8",
        )
        shell.chmod(0o755)

        command = install_transport.render_install_command(execute=execute, shell=str(shell))
        completed = subprocess.run(
            ["/bin/sh", "-c", command],
            check=False,
            capture_output=True,
            text=True,
            env={
                "BOOTSTRAP_RESPONSE": str(response_path),
                "LC_ALL": "C",
                "PATH": f"{root}:{os.environ.get('PATH', '')}",
                "SHELL_LOG": str(shell_log),
            },
        )
        return completed, shell_log

    def test_replacement_binds_exact_bootstrap_without_pipe_to_shell(self) -> None:
        command = install_transport.render_install_command(execute=True)
        self.assertNotRegex(command, r"install\.sh[^\n]*\|\s*(?:/bin/)?sh\b")
        self.assertIn(install_transport.BOOTSTRAP_URL, command)
        self.assertIn(install_transport.BOOTSTRAP_SHA256, command)
        self.assertIn(str(install_transport.BOOTSTRAP_SIZE), command)
        self.assertLess(command.index("curl "), command.index("sha256sum"))
        self.assertLess(command.index("sha256sum"), command.index('/bin/sh -n "$tmp"'))
        self.assertLess(command.index('/bin/sh -n "$tmp"'), command.rindex('/bin/sh "$tmp"'))
        download = (ROOT / "download/index.html").read_text(encoding="utf-8")
        self.assertNotIn(escape(command), download)
        self.assertIn(
            "The alpha installer is temporarily unavailable while we fix a problem found during testing.",
            download,
        )

    def test_4096_byte_response_fails_before_shell_or_execution(self) -> None:
        bootstrap = (ROOT / "download/install.sh").read_bytes()
        completed, shell_log = self._run_transport(bootstrap[:4096], execute=True)
        self.assertNotEqual(completed.returncode, 0)
        self.assertFalse(shell_log.exists(), "truncated response reached the shell")

    def test_complete_exact_bytes_pass_dash_syntax_without_execution(self) -> None:
        bootstrap = (ROOT / "download/install.sh").read_bytes()
        self.assertEqual(len(bootstrap), install_transport.BOOTSTRAP_SIZE)
        self.assertEqual(hashlib.sha256(bootstrap).hexdigest(), install_transport.BOOTSTRAP_SHA256)
        completed, shell_log = self._run_transport(bootstrap, execute=False)
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertIn(install_transport.PREFLIGHT_SUCCESS, completed.stdout)
        calls = shell_log.read_text(encoding="utf-8").splitlines()
        self.assertEqual(len(calls), 2)
        self.assertTrue(calls[0].startswith("-n "), calls)
        self.assertTrue(calls[1].endswith(" --materialization-preflight"), calls)


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

        missing = dict(texts)
        technical = ROOT / "download/technical-release-files.html"
        missing[technical] = missing[technical].replace(
            "0.1.0-alpha.5/release-index.json", "missing-release-index.json"
        )
        with self.assertRaisesRegex(AssertionError, "technical release files page lacks"):
            validate_repo.validate_source_disclosures(missing)


if __name__ == "__main__":
    unittest.main()
