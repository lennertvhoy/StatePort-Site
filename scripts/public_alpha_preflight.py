#!/usr/bin/env python3
"""Verify StatePort public-alpha runtime or source-release boundaries.

Runtime mode remains a read-only, standard-library-only check of the local
application catalog. Source mode is the mandatory cheap gate before any OCI
release build: it requires one clean canonical ``main`` checkout, verifies the
web image's actual Python import closure and locked bytes, validates Dockerfile
COPY sources, and executes the exact public export into an ephemeral external
directory. No image is built, pulled, pushed, signed, or published.
"""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
from http.cookiejar import CookieJar
from pathlib import Path
import subprocess
import sys
import tempfile
from typing import Any, Mapping, Sequence
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import HTTPCookieProcessor, build_opener


APPLICATION_ID = "studystate.sample"
DISPLAY_NAME = "StudyState Sample"
EXPECTED_CAPABILITIES = {
    "conversation",
    "goal_execution",
    "proactive_notifications",
    "progress_dashboard",
}
REQUIRED_WEB_RUNTIME_SOURCES = {
    "stateport_preview_gateway": "packages/preview-gateway/src",
    "stateport_updater": "packages/updater/src",
}


class PreflightError(ValueError):
    """The runtime or source checkout does not satisfy the public-alpha gate."""


def validate_catalog(payload: Mapping[str, Any]) -> Mapping[str, Any]:
    """Return the exact sample entry or fail with an actionable explanation."""

    result = payload.get("result")
    applications = result.get("applications") if isinstance(result, Mapping) else None
    if not isinstance(applications, list):
        raise PreflightError("application catalog response has no result.applications list")
    matches = [
        item
        for item in applications
        if isinstance(item, Mapping) and item.get("applicationId") == APPLICATION_ID
    ]
    if len(matches) != 1:
        raise PreflightError(
            f"application catalog must contain exactly one {APPLICATION_ID!r} entry; found {len(matches)}"
        )
    entry = matches[0]
    if entry.get("displayName") != DISPLAY_NAME:
        raise PreflightError(
            f"{APPLICATION_ID} display name is not the expected fictional sample {DISPLAY_NAME!r}"
        )
    install = entry.get("install")
    if not isinstance(install, Mapping):
        raise PreflightError(f"{APPLICATION_ID} has no install contract")
    if install.get("status") != "available":
        reasons = install.get("reasons", [])
        raise PreflightError(f"{DISPLAY_NAME} is not installable: {reasons}")
    if install.get("sourceKind") != "bundled_public_fixture":
        raise PreflightError(f"{DISPLAY_NAME} is not identified as a bundled public fixture")
    if install.get("networkPolicy") != "disabled":
        raise PreflightError(f"{DISPLAY_NAME} does not declare networkPolicy=disabled")
    capabilities = install.get("requestedCapabilities")
    if not isinstance(capabilities, list) or set(capabilities) != EXPECTED_CAPABILITIES:
        raise PreflightError(f"{DISPLAY_NAME} requested capabilities do not match the public-alpha contract")
    if install.get("confirmationRequired") is not True:
        raise PreflightError(f"{DISPLAY_NAME} does not require explicit installation confirmation")
    return entry


def check_service(base_url: str, timeout: float = 10.0) -> Mapping[str, Any]:
    """Open a local session and validate its application catalog."""

    parsed = urlsplit(base_url)
    try:
        port = parsed.port
    except ValueError as exc:
        raise PreflightError("base URL has an invalid port") from exc
    if (
        parsed.scheme != "http"
        or parsed.hostname not in {"127.0.0.1", "localhost"}
        or port is None
        or parsed.username is not None
        or parsed.password is not None
        or parsed.path.rstrip("/")
        or parsed.query
        or parsed.fragment
    ):
        raise PreflightError("base URL must be an origin-only loopback HTTP URL with an explicit port")
    base = f"http://{parsed.hostname}:{port}"
    opener = build_opener(HTTPCookieProcessor(CookieJar()))
    with opener.open(f"{base}/session", timeout=timeout) as response:
        session = json.load(response)
    if not isinstance(session, Mapping) or session.get("ok") is not True:
        raise PreflightError("StatePort session endpoint is not ready")
    with opener.open(f"{base}/v1/applications", timeout=timeout) as response:
        catalog = json.load(response)
    if not isinstance(catalog, Mapping):
        raise PreflightError("application catalog response is not an object")
    return validate_catalog(catalog)


def _git(root: Path, arguments: Sequence[str]) -> str:
    completed = subprocess.run(
        ["git", "-C", str(root), *arguments],
        check=False,
        capture_output=True,
        text=True,
        timeout=60,
        shell=False,
    )
    if completed.returncode != 0:
        detail = (completed.stderr or completed.stdout).strip()[:500]
        raise PreflightError(f"Git command failed: {' '.join(arguments)}: {detail}")
    return completed.stdout.strip()


def validate_canonical_checkout(root: Path) -> dict[str, str]:
    """Require one clean local ``main`` exactly synchronized with ``origin/main``."""

    try:
        root = root.resolve(strict=True)
    except OSError as exc:
        raise PreflightError("source root is unavailable") from exc
    if not root.is_dir():
        raise PreflightError("source root is not a directory")
    observed_root = Path(_git(root, ["rev-parse", "--show-toplevel"]))
    try:
        observed_root = observed_root.resolve(strict=True)
    except OSError as exc:
        raise PreflightError("Git source root is unavailable") from exc
    if observed_root != root:
        raise PreflightError("source root is not the canonical Git toplevel")
    if _git(root, ["branch", "--show-current"]) != "main":
        raise PreflightError("release preflight requires the canonical main branch")
    dirty = _git(root, ["status", "--porcelain=v1", "--untracked-files=all"])
    if dirty:
        raise PreflightError("release preflight requires a clean tree, including untracked files")

    commit = _git(root, ["rev-parse", "--verify", "HEAD"])
    tree = _git(root, ["rev-parse", "--verify", "HEAD^{tree}"])
    origin_main = _git(root, ["rev-parse", "--verify", "refs/remotes/origin/main"])
    if commit != origin_main:
        raise PreflightError("local main is not exactly synchronized with origin/main")

    local_branches = [
        item
        for item in _git(root, ["for-each-ref", "--format=%(refname:short)", "refs/heads"])
        .splitlines()
        if item
    ]
    if local_branches != ["main"]:
        raise PreflightError(
            f"release preflight requires main as the only local branch; found {local_branches}"
        )

    records = [
        record
        for record in _git(root, ["worktree", "list", "--porcelain"]).split("\n\n")
        if record.strip()
    ]
    if len(records) != 1:
        raise PreflightError(
            f"release preflight requires one registered worktree; found {len(records)}"
        )
    first_line = records[0].splitlines()[0] if records[0].splitlines() else ""
    if not first_line.startswith("worktree "):
        raise PreflightError("Git worktree inventory is malformed")
    try:
        worktree_root = Path(first_line.removeprefix("worktree ")).resolve(strict=True)
    except OSError as exc:
        raise PreflightError("registered worktree is unavailable") from exc
    if worktree_root != root:
        raise PreflightError("the only registered worktree is not the canonical checkout")
    return {"commit": commit, "tree": tree}


def _imported_roots(path: Path) -> set[str]:
    try:
        module = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    except (OSError, UnicodeError, SyntaxError) as exc:
        raise PreflightError(f"runtime import source is invalid: {path}") from exc
    imported: set[str] = set()
    for node in ast.walk(module):
        if isinstance(node, ast.Import):
            imported.update(alias.name.split(".", 1)[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module.split(".", 1)[0])
    return imported


def validate_packaged_web_sources(root: Path) -> dict[str, str]:
    """Bind the web image allowlist to the AppServer's actual import closure."""

    try:
        import yaml
    except ImportError as exc:
        raise PreflightError("source preflight requires PyYAML") from exc

    dockerfile_path = root / "apps/web/Dockerfile"
    manifest_path = root / "images/packaged-content.v1.yaml"
    service_process = root / "packages/persistent-app/src/stateport_persistent_app/service_process.py"
    platform_surface = root / "packages/persistent-app/src/stateport_persistent_app/platform_surface.py"
    build_inputs_path = root / "config/container-build-inputs.yaml"
    for path in (
        dockerfile_path,
        manifest_path,
        service_process,
        platform_surface,
        build_inputs_path,
    ):
        if not path.is_file() or path.is_symlink():
            raise PreflightError(f"required source is missing or unsafe: {path.relative_to(root)}")

    imported = _imported_roots(service_process) | _imported_roots(platform_surface)
    dockerfile = dockerfile_path.read_text(encoding="utf-8")
    manifest = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
    try:
        packaged_sources = manifest["profiles"]["stateport-web"]["finalImageSources"]
    except (KeyError, TypeError) as exc:
        raise PreflightError("stateport-web packaged-content profile is malformed") from exc
    if not isinstance(packaged_sources, list):
        raise PreflightError("stateport-web finalImageSources must be an array")

    observations: dict[str, str] = {}
    for module, source in REQUIRED_WEB_RUNTIME_SOURCES.items():
        if module not in imported:
            raise PreflightError(f"expected AppServer runtime import is absent: {module}")
        copy = f"COPY {source} /workspace/{source}"
        if copy not in dockerfile:
            raise PreflightError(f"web image omits runtime source required by AppServer: {source}")
        if source not in packaged_sources:
            raise PreflightError(f"packaged-content manifest omits runtime source: {source}")
        observations[module] = source

    build_inputs = yaml.safe_load(build_inputs_path.read_text(encoding="utf-8"))
    definitions = build_inputs.get("definitions") if isinstance(build_inputs, Mapping) else None
    if not isinstance(definitions, Mapping) or not definitions:
        raise PreflightError("container build-input definitions are missing")
    for relative, expected in definitions.items():
        if not isinstance(relative, str) or not isinstance(expected, str):
            raise PreflightError("container build-input definition is malformed")
        path = root / relative
        if not path.is_file() or path.is_symlink():
            raise PreflightError(f"locked container definition is missing: {relative}")
        observed = "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()
        if observed != expected:
            raise PreflightError(f"locked container definition digest drifted: {relative}")
    return observations


def validate_public_export(root: Path, commit: str) -> dict[str, Any]:
    """Execute the exact public export in a temporary directory before building."""

    scripts = Path(__file__).resolve().parent
    if str(scripts) not in sys.path:
        sys.path.insert(0, str(scripts))
    try:
        from export_public_candidate import export_candidate, extract_private_detectors
    except (ImportError, OSError) as exc:
        raise PreflightError("public-export tooling is unavailable") from exc

    with tempfile.TemporaryDirectory(prefix="stateport-release-preflight-") as temporary:
        temporary_root = Path(temporary)
        detectors = temporary_root / "private-detectors.json"
        output = temporary_root / "public-source"
        public_manifest = temporary_root / "public-manifest.json"
        private_inventory = temporary_root / "private-inventory.json"
        try:
            extract_private_detectors(
                root,
                commit,
                "config/public-release-policy.yaml",
                detectors,
            )
            exported = export_candidate(
                root,
                commit,
                "config/public-export-allowlist.v1.yaml",
                detectors,
                output,
                public_manifest,
                private_inventory,
            )
        except (OSError, ValueError) as exc:
            raise PreflightError(f"public export preflight failed: {exc}") from exc
        if not exported:
            try:
                manifest = json.loads(public_manifest.read_text(encoding="utf-8"))
                issues = manifest.get("blockingIssueCounts", [])
            except (OSError, UnicodeError, json.JSONDecodeError):
                issues = []
            raise PreflightError(f"public export is blocked: {issues}")
        manifest = json.loads(public_manifest.read_text(encoding="utf-8"))
        files = manifest.get("files")
        if manifest.get("status") != "exported" or not isinstance(files, list) or not files:
            raise PreflightError("public export produced no authoritative file inventory")
        return {
            "publicFileCount": len(files),
            "manifestDigest": "sha256:"
            + hashlib.sha256(public_manifest.read_bytes()).hexdigest(),
        }


def check_source(root: Path) -> dict[str, Any]:
    """Run every cheap release gate before the first OCI build begins."""

    root = root.resolve()
    identity = validate_canonical_checkout(root)
    packaged = validate_packaged_web_sources(root)
    copy_validator = root / "scripts/validate_dockerfile_copy_sources.py"
    completed = subprocess.run(
        [sys.executable, str(copy_validator)],
        cwd=root,
        check=False,
        capture_output=True,
        text=True,
        timeout=120,
        shell=False,
    )
    if completed.returncode != 0:
        detail = (completed.stderr or completed.stdout).strip()[:1000]
        raise PreflightError(f"Dockerfile COPY-source validation failed: {detail}")
    public_export = validate_public_export(root, identity["commit"])
    return {
        "formatVersion": "stateport.release-source-preflight/v1",
        "status": "passed",
        "commit": identity["commit"],
        "tree": identity["tree"],
        "packagedRuntimeSources": packaged,
        **public_export,
        "heavyOperationsStarted": False,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--base-url")
    mode.add_argument("--source-root", type=Path)
    parser.add_argument("--timeout", type=float, default=10.0)
    args = parser.parse_args(argv)
    try:
        if args.source_root is not None:
            print(json.dumps(check_source(args.source_root), indent=2, sort_keys=True))
            return 0
        assert args.base_url is not None
        check_service(args.base_url, args.timeout)
    except (
        PreflightError,
        HTTPError,
        URLError,
        json.JSONDecodeError,
        TimeoutError,
        OSError,
    ) as exc:
        parser.exit(1, f"public-alpha preflight: error: {exc}\n")
    print(
        "public-alpha preflight: StudyState Sample is available as a "
        "provider-free bundled fixture; explicit browser confirmation remains required."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
