#!/usr/bin/env python3
"""Regenerate config/immutable-release-trees.json, anchored to publication.

The manifest records every retained file's path, bytes, SHA-256, publication
Git mode/type, and current lstat mode. The trees themselves are immutable:
this script only observes them. validate_repo.py rejects any path, node-type,
mode, byte-count, or content change against the manifest.

Anti-regeneration anchor: each tree is bound to the exact site commit that
published its current bytes. This script recomputes the SHA-256 of every
file's content at that anchor commit and refuses to write a manifest whose
current files do not match the anchor exactly. Git reads are fixed to this
repository, ignore replacement objects, and ignore inherited Git configuration.
validate_repo.py independently implements and checks the same policy.
"""

from __future__ import annotations

import hashlib
import json
import os
import stat
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "config/immutable-release-trees.json"

# These exact publication anchors are intentionally duplicated, not imported,
# in validate_repo.py. A mutable shared definition would not be an independent
# policy check.
PUBLICATION_ANCHORS = {
    "download/0.1.0-alpha.2": "4043534a9a1d56c51c3d47d0906e0520963af79c",
    "download/0.1.0-alpha.3": "52b42dd47a11510220f33690075f1b6773f6a889",
    "download/0.1.0-alpha.5": "eaa1ca6a67844259860917442a95c891d097939f",
}


def _git_environment() -> dict[str, str]:
    """Return an environment with no inherited Git repository/config hooks."""

    environment = {
        key: value for key, value in os.environ.items() if not key.startswith("GIT_")
    }
    environment.update(
        {
            "GIT_CONFIG_GLOBAL": os.devnull,
            "GIT_CONFIG_NOSYSTEM": "1",
            "GIT_CONFIG_SYSTEM": os.devnull,
            "GIT_NO_REPLACE_OBJECTS": "1",
            "GIT_TERMINAL_PROMPT": "0",
            "LC_ALL": "C",
        }
    )
    return environment


def _git(*args: str, root: Path = ROOT) -> bytes:
    repository = root.resolve(strict=True)
    git_dir = repository / ".git"
    if git_dir.is_symlink() or not git_dir.is_dir():
        raise AssertionError(f"Expected a fixed Git directory at {git_dir}")
    completed = subprocess.run(
        [
            "git",
            "--no-replace-objects",
            f"--git-dir={git_dir}",
            f"--work-tree={repository}",
            *args,
        ],
        check=False,
        capture_output=True,
        env=_git_environment(),
        timeout=60,
    )
    if completed.returncode:
        detail = completed.stderr.decode("utf-8", errors="replace").strip()
        raise AssertionError(f"sanitized git {' '.join(args)} failed: {detail}")
    return completed.stdout


def anchored_files(tree: str, commit: str, *, root: Path = ROOT) -> dict[str, dict]:
    """Return exact blob metadata at an independently verified anchor."""

    listing = _git("ls-tree", "-rz", "--full-tree", commit, "--", tree, root=root)
    records = [record for record in listing.split(b"\0") if record]
    if not records:
        raise AssertionError(f"Anchor commit {commit} has no files under {tree}")
    files: dict[str, dict] = {}
    for record in records:
        metadata, separator, raw_path = record.partition(b"\t")
        fields = metadata.split()
        if not separator or len(fields) != 3:
            raise AssertionError(f"Malformed git ls-tree record at {commit}: {record!r}")
        git_mode, git_type, object_id = (
            field.decode("ascii", errors="strict") for field in fields
        )
        repo_path = raw_path.decode("utf-8", errors="strict")
        relative = Path(repo_path).relative_to(Path(tree)).as_posix()
        if git_type != "blob" or git_mode not in {"100644", "100755"}:
            raise AssertionError(
                f"Unsupported Git node at {commit}:{repo_path}: {git_mode} {git_type}"
            )
        blob = _git("cat-file", "blob", object_id, root=root)
        files[relative] = {
            "bytes": len(blob),
            "gitMode": git_mode,
            "gitType": git_type,
            "sha256": hashlib.sha256(blob).hexdigest(),
        }
    return files


def current_files(tree: str, *, root: Path = ROOT) -> dict[str, dict]:
    tree_root = root / tree
    try:
        tree_mode = tree_root.lstat().st_mode
    except FileNotFoundError as exc:
        raise AssertionError(f"Missing immutable release tree: {tree}") from exc
    if not stat.S_ISDIR(tree_mode):
        raise AssertionError(f"Missing immutable release tree: {tree}")

    files: dict[str, dict] = {}

    def visit(directory: Path) -> None:
        with os.scandir(directory) as iterator:
            entries = sorted(iterator, key=lambda entry: entry.name)
        for entry in entries:
            path = Path(entry.path)
            metadata = entry.stat(follow_symlinks=False)
            relative = path.relative_to(tree_root).as_posix()
            if stat.S_ISDIR(metadata.st_mode):
                visit(path)
                continue
            if not stat.S_ISREG(metadata.st_mode):
                raise AssertionError(
                    f"Immutable release tree {tree} contains a symlink or special file: "
                    f"{relative} ({metadata.st_mode:06o})"
                )
            data = path.read_bytes()
            files[relative] = {
                "bytes": len(data),
                "lstatMode": f"{metadata.st_mode:06o}",
                "sha256": hashlib.sha256(data).hexdigest(),
            }

    visit(tree_root)
    if not files:
        raise AssertionError(f"Immutable release tree is empty: {tree}")
    return files


def build_manifest() -> dict:
    trees: dict[str, dict] = {}
    for tree, anchor in PUBLICATION_ANCHORS.items():
        anchored = anchored_files(tree, anchor)
        current = current_files(tree)
        anchored_set, current_set = set(anchored), set(current)
        if anchored_set != current_set:
            raise AssertionError(
                f"{tree} path set differs from anchor {anchor}: "
                f"only-anchor={sorted(anchored_set - current_set)} "
                f"only-current={sorted(current_set - anchored_set)}"
            )
        changed = sorted(
            relative
            for relative, observed in current.items()
            if observed["sha256"] != anchored[relative]["sha256"]
            or observed["bytes"] != anchored[relative]["bytes"]
        )
        if changed:
            raise AssertionError(
                f"{tree} bytes or byte counts differ from anchor {anchor}: {changed}. "
                "Refusing to regenerate a manifest from modified bytes."
            )
        trees[tree] = {
            "anchor": {"commit": anchor},
            "files": {
                relative: {**anchored[relative], "lstatMode": observed["lstatMode"]}
                for relative, observed in current.items()
            },
        }
    return {
        "schema": "stateport-site.immutable-release-trees/v2",
        "description": (
            "Exact path, SHA-256, byte-count, publication Git mode/type, and "
            "current lstat-mode manifest for the retained signed release trees, "
            "anchored to verified publication commits. Regenerate only with "
            "python3 scripts/build_immutable_manifest.py; the release trees are "
            "immutable and must never change nodes, modes, or bytes."
        ),
        "trees": trees,
    }


def main() -> None:
    manifest = build_manifest()
    OUTPUT.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    counts = {tree: len(payload["files"]) for tree, payload in manifest["trees"].items()}
    summary = ", ".join(f"{tree}: {count} files" for tree, count in counts.items())
    print(f"Wrote {OUTPUT.relative_to(ROOT)} ({summary})")


if __name__ == "__main__":
    main()
