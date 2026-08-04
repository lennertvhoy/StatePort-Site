from __future__ import annotations

import hashlib
from pathlib import Path
import re

import yaml


ROOT = Path(__file__).resolve().parents[1]


def _digest(path: Path) -> str:
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


def test_locked_build_inputs_match_exact_repository_bytes() -> None:
    value = yaml.safe_load((ROOT / "config/container-build-inputs.yaml").read_text())
    assert value["resolvedOn"] == "2026-08-03"
    for lock in value["locks"].values():
        assert _digest(ROOT / lock["path"]) == lock["digest"]
    for path, expected in value["definitions"].items():
        assert _digest(ROOT / path) == expected


def test_ubuntu_packages_are_exact_and_snapshot_bound() -> None:
    value = yaml.safe_load((ROOT / "config/container-build-inputs.yaml").read_text())
    containerfile = (ROOT / "images/stateport-dev-workspace/Containerfile").read_text()
    assert value["ubuntuSnapshot"]["timestamp"] == "20260801T000000Z"
    for package, version in value["ubuntuSnapshot"]["packages"].items():
        assert f"{package}={version}" in containerfile
    assert "apt-get install --no-install-recommends" in containerfile
    assert "|| true" not in containerfile


def test_upstream_tools_are_pinned_in_containerfile() -> None:
    value = yaml.safe_load((ROOT / "config/container-build-inputs.yaml").read_text())
    containerfile = (ROOT / "images/stateport-dev-workspace/Containerfile").read_text()
    tools = value["upstreamTools"]
    assert tools, "upstreamTools must not be empty"
    for name, tool in tools.items():
        digest = tool["digest"]
        assert digest.startswith("sha256:")
        assert digest.removeprefix("sha256:") in containerfile
        assert tool["uri"] in containerfile
        install_path = tool["installPath"]
        assert install_path.startswith("/usr/local")
        if install_path != "/usr/local":
            # Single-binary tools install to a path named after the tool;
            # prefix installs (e.g. Node.js) target /usr/local itself.
            assert install_path.rsplit("/", 1)[-1] == name
    assert "|| true" not in containerfile


def test_alpine_packages_are_exact_and_repository_bound() -> None:
    value = yaml.safe_load((ROOT / "config/container-build-inputs.yaml").read_text())
    dockerfile = (ROOT / "apps/web/Dockerfile").read_text()
    snapshot = value["alpinePackages"]
    assert snapshot["release"] == "3.23"
    assert snapshot["repository"].endswith("/alpine/v3.23/main")
    for package, version in snapshot["packages"].items():
        assert f"{package}={version}" in dockerfile
    assert "apk add --no-cache" in dockerfile
    assert "|| true" not in dockerfile


def test_execution_host_alpine_packages_are_exact_and_fully_pinned() -> None:
    value = yaml.safe_load((ROOT / "config/container-build-inputs.yaml").read_text())
    containerfile = (ROOT / "images/stateport-execution-host/Containerfile").read_text()
    snapshot = value["executionHostAlpine"]
    assert snapshot["repositories"] == [
        "https://dl-cdn.alpinelinux.org/alpine/edge/main",
        "https://dl-cdn.alpinelinux.org/alpine/edge/community",
    ]
    for repository in snapshot["repositories"]:
        assert f"--repository {repository}" in containerfile
    for package, version in snapshot["packages"].items():
        assert f"{package}={version}" in containerfile
    assert "apk add --no-cache" in containerfile
    assert "podman-remote" in containerfile
    assert "|| true" not in containerfile


def test_web_image_contains_runtime_packages_imported_by_appserver() -> None:
    dockerfile = (ROOT / "apps/web/Dockerfile").read_text()
    manifest = yaml.safe_load((ROOT / "images/packaged-content.v1.yaml").read_text())
    packaged_sources = manifest["profiles"]["stateport-web"]["finalImageSources"]
    required = {
        "packages/preview-gateway/src": (
            ROOT / "packages/persistent-app/src/stateport_persistent_app/service_process.py",
            "stateport_preview_gateway",
        ),
        "packages/updater/src": (
            ROOT / "packages/persistent-app/src/stateport_persistent_app/platform_surface.py",
            "stateport_updater",
        ),
    }
    for source, (consumer_path, imported_module) in required.items():
        consumer = consumer_path.read_text()
        assert re.search(
            rf"\b(?:from|import)\s+{re.escape(imported_module)}(?:\.|\b)",
            consumer,
        ), imported_module
        assert f"COPY {source} /workspace/{source}" in dockerfile, source
        assert source in packaged_sources, source


def test_control_plane_runtime_lock_has_no_provider_sdk_or_best_effort_install() -> None:
    runtime = (ROOT / "requirements/runtime-linux-amd64.txt").read_text()
    assert "--hash=sha256:" in runtime
    assert not re.search(r"openai|anthropic|google-generative|provider", runtime, re.I)
    for path in (ROOT / "apps/api/Dockerfile", ROOT / "apps/worker/Dockerfile"):
        text = path.read_text()
        assert "--require-hashes" in text
        assert "|| true" not in text
        assert "podman" not in text.lower()
        assert "/var/run/docker.sock" not in text.lower()
        assert not re.search(r"(?:apk|apt-get)\s+[^\n]*(?:podman|docker|git)", text, re.I)
