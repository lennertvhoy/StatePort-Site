from __future__ import annotations

from dataclasses import replace
from pathlib import Path
import re
import sys

import yaml


ROOT = Path(__file__).resolve().parents[1]
RELEASE_CONTRACTS_SRC = ROOT / "packages" / "release-contracts" / "src"
if str(RELEASE_CONTRACTS_SRC) not in sys.path:
    sys.path.insert(0, str(RELEASE_CONTRACTS_SRC))

from stateport_release import (  # noqa: E402
    LinuxHostObservation,
    PORTABLE_LINUX_TARGET_ID,
    evaluate_linux_host,
    parse_host_semantic_version,
)

DIGEST_REFERENCE = re.compile(r"^[^\s@]+@sha256:[0-9a-f]{64}$")


def test_base_image_manifest_is_exact_and_amd64_only() -> None:
    value = yaml.safe_load((ROOT / "config/container-base-images.yaml").read_text())
    assert value["formatVersion"] == "stateport.container-base-images/v1"
    assert value["resolvedOn"] == "2026-08-02"
    assert value["architecture"] == "linux/amd64"
    references = []
    for image in value["images"].values():
        assert DIGEST_REFERENCE.fullmatch(image["reference"])
        assert image["reference"].endswith("@" + image["indexDigest"])
        assert re.fullmatch(r"sha256:[0-9a-f]{64}", image["platformManifestDigest"])
        references.append(image["reference"])
    assert len(references) == len(set(references))
    assert value["qualification"]["supported"] == ["linux/amd64"]


def test_every_containerfile_from_is_in_the_pinned_base_manifest() -> None:
    value = yaml.safe_load((ROOT / "config/container-base-images.yaml").read_text())
    allowed = {item["reference"] for item in value["images"].values()}
    paths = {ROOT / path for item in value["images"].values() for path in item["usedBy"]}
    for path in sorted(paths):
        assert path.is_file(), path
        for line in path.read_text().splitlines():
            if line.startswith("FROM "):
                reference = line.split()[1]
                assert reference in allowed, (path, reference)


def _host(**overrides: object) -> LinuxHostObservation:
    value = LinuxHostObservation(
        kernel="Linux",
        architecture="amd64",
        os_id="ubuntu",
        version_id="24.04",
        cgroup_version="v2",
        podman_version="5.4.2",
        rootless=True,
        quadlet=True,
        systemd_user=True,
        subuid_configured=True,
        subgid_configured=True,
    )
    return replace(value, **overrides)


def test_linux_host_eligibility_is_capability_based() -> None:
    baseline = evaluate_linux_host(_host())
    assert baseline.eligible
    assert baseline.target_id == PORTABLE_LINUX_TARGET_ID
    assert baseline.support_tier == "validated_baseline"

    for os_id, version in (
        ("debian", "13"),
        ("fedora", "43"),
        ("arch", "rolling"),
        ("opensuse-tumbleweed", "20260801"),
    ):
        decision = evaluate_linux_host(_host(os_id=os_id, version_id=version))
        assert decision.eligible
        assert decision.support_tier == "compatible_unvalidated"
        assert decision.refusal_codes == ()
        assert decision.warnings


def test_linux_host_capabilities_fail_closed_individually() -> None:
    cases = {
        "kernel": ("Darwin", "linux_kernel_required"),
        "architecture": ("arm64", "linux_amd64_required"),
        "cgroup_version": ("v1", "cgroup_v2_required"),
        "podman_version": ("4.8.9", "podman_version_too_old"),
        "rootless": (False, "rootless_podman_required"),
        "quadlet": (False, "quadlet_required"),
        "systemd_user": (False, "systemd_user_required"),
        "subuid_configured": (False, "subuid_mapping_required"),
        "subgid_configured": (False, "subgid_mapping_required"),
    }
    for field, (value, code) in cases.items():
        decision = evaluate_linux_host(_host(**{field: value}))
        assert not decision.eligible
        assert decision.support_tier == "ineligible"
        assert code in decision.refusal_codes


def test_host_version_parser_accepts_vendor_suffixes() -> None:
    assert parse_host_semantic_version("5.4.2-1.fc43") == (5, 4, 2)
    assert parse_host_semantic_version(" 4.9.3 ") == (4, 9, 3)
    assert parse_host_semantic_version("not-a-version") is None
