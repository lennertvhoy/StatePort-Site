#!/usr/bin/env python3
"""Collect canonical image supply-chain evidence from an exact build receipt."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import time
from typing import Any, Mapping, Sequence

import jsonschema
import yaml

from release_safe_io import (
    prepare_output_root,
    safe_path,
    sha256_file,
    write_bytes_create_only,
    write_json_create_only,
)


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "packages/release-contracts/src"))
from stateport_release import (  # noqa: E402
    public_key_der_spki_fingerprint,
    validate_release_provenance,
)
from validate_candidate_provenance import (  # noqa: E402
    CandidateProvenanceError,
    validate_contract as validate_candidate_contract,
    validate_repository_relationship,
    verify_bundle as verify_candidate_bundle,
)


TOOLS = ROOT / "config/release-tool-inputs.yaml"
BASE_IMAGES = ROOT / "config/container-base-images.yaml"
BUILD_INPUTS = ROOT / "config/container-build-inputs.yaml"
SCAN_EXCEPTIONS = ROOT / "config/release-scan-exceptions.v1.yaml"
SCAN_EXCEPTIONS_SCHEMA = ROOT / "schemas/release-scan-exceptions.v1.schema.json"
PODMAN = Path("/usr/bin/podman")
_DIGEST = re.compile(r"^sha256:[0-9a-f]{64}$")
_DIGEST_REFERENCE = re.compile(r"^[^\s@]+@sha256:[0-9a-f]{64}$")
_KEY_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{2,127}$")
_SEVERITY_ORDER = {"Negligible": 0, "Low": 1, "Medium": 2, "High": 3, "Critical": 4}
_THRESHOLD_ORDER = {"negligible": 0, "low": 1, "medium": 2, "high": 3, "critical": 4}


class EvidenceError(RuntimeError):
    pass


def _load_yaml(path: Path) -> Mapping[str, Any]:
    value = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(value, Mapping):
        raise EvidenceError(f"release input manifest is invalid: {path.name}")
    return value


def _load_json_file(path: Path, *, maximum_bytes: int = 4 * 1024 * 1024) -> Mapping[str, Any]:
    if path.is_symlink() or not path.is_file() or path.stat().st_size > maximum_bytes:
        raise EvidenceError(f"evidence input is unsafe: {path}")
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise EvidenceError(f"evidence input is not valid UTF-8 JSON: {path}") from exc
    if not isinstance(value, Mapping):
        raise EvidenceError(f"evidence input is not a JSON object: {path}")
    return value


def _run(arguments: Sequence[str], *, timeout: int = 3600) -> str:
    completed = subprocess.run(
        list(arguments),
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
        timeout=timeout,
        shell=False,
    )
    if completed.returncode != 0:
        raise EvidenceError(f"tool failed ({completed.returncode}): {' '.join(arguments)}")
    return completed.stdout


def _run_to_new_file(
    arguments: Sequence[str], path: Path, *, accepted_returncodes: set[int] = {0}
) -> int:
    if path.exists() or path.is_symlink():
        raise EvidenceError(f"evidence output already exists: {path}")
    with path.open("xb") as stream:
        completed = subprocess.run(
            list(arguments),
            cwd=ROOT,
            check=False,
            stdout=stream,
            stderr=subprocess.PIPE,
            timeout=3600,
            shell=False,
        )
    if completed.returncode not in accepted_returncodes:
        raise EvidenceError(f"tool failed ({completed.returncode}): {' '.join(arguments)}")
    return completed.returncode


def _progress(image_id: str, message: str) -> None:
    print(f"[release-evidence] {image_id}: {message}", file=sys.stderr, flush=True)


def _publish_tool_output(*, root: Path, source: Path, name: str) -> Path:
    if source.is_symlink() or not source.is_file():
        raise EvidenceError(f"tool did not produce a regular output file: {source}")
    content = source.read_bytes()
    if not content:
        raise EvidenceError(f"tool produced an empty output file: {source}")
    return write_bytes_create_only(root, name, content)


def _collect_sboms(
    *, image_id: str, local_source: str, syft: str, output: Path
) -> tuple[Path, Path, Path]:
    cdx_name = f"{image_id}.cdx.json"
    spdx_name = f"{image_id}.spdx.json"
    syft_name = f"{image_id}.syft.json"
    started = time.monotonic()
    _progress(image_id, "SBOM catalogue starting (CycloneDX, SPDX, Syft JSON)")
    with tempfile.TemporaryDirectory(prefix="syft-", dir=output) as temporary_root:
        temporary = Path(temporary_root)
        cdx = temporary / cdx_name
        spdx = temporary / spdx_name
        syft_json = temporary / syft_name
        _run(
            [
                syft,
                local_source,
                "-o",
                f"syft-json={syft_json}",
                "-o",
                f"cyclonedx-json={cdx}",
                "-o",
                f"spdx-json={spdx}",
            ]
        )
        published = (
            _publish_tool_output(root=output, source=cdx, name=cdx_name),
            _publish_tool_output(root=output, source=spdx, name=spdx_name),
            _publish_tool_output(root=output, source=syft_json, name=syft_name),
        )
    _progress(image_id, f"SBOM catalogue complete in {time.monotonic() - started:.1f}s")
    return published


def _collect_grype_scan(
    *, image_id: str, syft_json: Path, grype: str, output: Path
) -> Path:
    name = f"{image_id}.grype.json"
    started = time.monotonic()
    _progress(image_id, "vulnerability scan starting from Syft catalogue")
    with tempfile.TemporaryDirectory(prefix="grype-", dir=output) as temporary_root:
        temporary_scan = Path(temporary_root) / name
        _run_to_new_file([grype, f"sbom:{syft_json}", "-o", "json"], temporary_scan)
        published = _publish_tool_output(root=output, source=temporary_scan, name=name)
    _progress(image_id, f"vulnerability scan complete in {time.monotonic() - started:.1f}s")
    return published


def _catalogue_source(*, image: Mapping[str, Any], build_receipt_path: Path, local_tag: str) -> str:
    authority = image.get("releaseAuthority")
    if isinstance(authority, Mapping) and authority.get("kind") == "retained-oci-archive":
        archive_path = safe_path(build_receipt_path.parent, str(authority.get("path", "")))
        if archive_path.is_file() and not archive_path.is_symlink():
            return f"oci-archive:{archive_path}"
        raise EvidenceError(f"retained OCI archive is unavailable: {archive_path}")
    return f"podman:{local_tag}"


def verify_toolchain() -> dict[str, dict[str, str]]:
    manifest = _load_yaml(TOOLS)
    observed: dict[str, dict[str, str]] = {}
    for name, expected in manifest["tools"].items():
        expected_path = Path(str(expected["executablePath"]))
        discovered = shutil.which(name)
        if discovered is None or Path(discovered) != expected_path:
            raise EvidenceError(f"{name} is not available at its exact pinned executable path")
        resolved_executable = expected_path.resolve(strict=True)
        if str(resolved_executable) != str(expected["resolvedExecutablePath"]):
            raise EvidenceError(f"{name} resolves to an unexpected executable")
        digest = sha256_file(resolved_executable)
        if digest != expected["executableDigest"]:
            raise EvidenceError(f"{name} executable digest does not match the pinned tool manifest")
        version_text = _run([str(expected_path), "version"])
        if str(expected["version"]) not in version_text:
            raise EvidenceError(f"{name} version does not match the pinned tool manifest")
        observed[name] = {
            "version": str(expected["version"]),
            "executable": str(expected_path),
            "resolvedExecutable": str(resolved_executable),
            "executableDigest": digest,
            "bottleDigest": str(expected["bottleDigest"]),
            "provenance": str(expected["provenance"]),
        }
    return observed


def signature_verification_command(
    *,
    artifact: Path,
    bundle: Path,
    public_key: Path,
    expected_key_fingerprint: str,
    expected_key_id: str,
    configured_key_id: str,
) -> list[str]:
    fingerprint = public_key_der_spki_fingerprint(public_key)
    if fingerprint != expected_key_fingerprint:
        raise EvidenceError(
            "pinned public-key DER SPKI fingerprint does not match the supplied trust root"
        )
    if _KEY_ID.fullmatch(expected_key_id) is None or configured_key_id != expected_key_id:
        raise EvidenceError("pinned public-key ID does not match the configured trust root")
    if bundle.suffixes[-2:] != [".sigstore", ".json"]:
        raise EvidenceError("Cosign v3 bundle must use the .sigstore.json form")
    cosign = str(_load_yaml(TOOLS)["tools"]["cosign"]["executablePath"])
    return [
        cosign,
        "verify-blob",
        "--insecure-ignore-tlog",
        "--bundle",
        str(bundle),
        "--key",
        str(public_key),
        str(artifact),
    ]


def grype_database_status(*, now: datetime | None = None) -> dict[str, Any]:
    manifest = _load_yaml(TOOLS)
    policy = manifest["policy"]
    grype = str(manifest["tools"]["grype"]["executablePath"])
    value = json.loads(_run([grype, "db", "status", "-o", "json"]))
    if not isinstance(value, Mapping) or not isinstance(value.get("built"), str):
        raise EvidenceError("Grype database status is invalid")
    try:
        built = datetime.fromisoformat(str(value["built"]).replace("Z", "+00:00"))
    except ValueError as exc:
        raise EvidenceError("Grype database build timestamp is invalid") from exc
    observed_at = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    age_hours = (observed_at - built.astimezone(timezone.utc)).total_seconds() / 3600
    maximum = int(policy["maxDatabaseAgeHours"])
    if value.get("valid") is not True or age_hours < 0 or age_hours > maximum:
        raise EvidenceError(
            f"Grype database is not fresh and valid (age={age_hours:.2f}h, maximum={maximum}h)"
        )
    return {
        "schemaVersion": value.get("schemaVersion"),
        "builtAt": built.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "observedAt": observed_at.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "ageHours": round(age_hours, 4),
        "maximumAgeHours": maximum,
        "valid": True,
    }


def _health_observation(*, image_id: str, image_reference: str, local_tag: str) -> dict[str, Any]:
    inspect = json.loads(_run([str(PODMAN), "image", "inspect", local_tag]))
    declared = inspect[0].get("Config", {}).get("Healthcheck")
    probe_command = [
        str(PODMAN),
        "run",
        "--rm",
        local_tag,
        "/usr/local/bin/stateport-healthcheck",
        "--kind",
        "unix-socket",
        "--path",
        "/nonexistent/stateport-health.sock",
    ]
    completed = subprocess.run(
        probe_command,
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
        timeout=120,
        shell=False,
    )
    # The packaged probe exits 1 when the socket is absent; exit 2 would mean
    # argument parsing failed and 126/127 that the probe did not execute.
    probe_executed = completed.returncode == 1
    observation = {
        "formatVersion": "stateport.release-image-healthcheck/v1",
        "imageId": image_id,
        "imageReference": image_reference,
        "declaredHealthcheck": declared,
        "probeObservation": {
            "command": (
                "stateport-healthcheck --kind unix-socket --path /nonexistent/stateport-health.sock"
            ),
            "exitCode": completed.returncode,
            "executed": probe_executed,
            "interpretation": (
                "in-image probe execution observed; the absent socket fails the check exactly as designed"
                if probe_executed
                else "the packaged probe did not execute inside the image"
            ),
        },
        "serviceHealth": {
            "status": "deferred-to-stack-proof",
            "detail": (
                "runtime service health is proven at compose-stack and "
                "no-checkout-install level, not per standalone image"
            ),
        },
    }
    if not declared and not probe_executed:
        raise EvidenceError(f"no health observation is possible for {image_id}")
    return observation


def _podman_observation(reference: str) -> dict[str, Any]:
    values = json.loads(_run([str(PODMAN), "image", "inspect", reference]))
    if not isinstance(values, list) or len(values) != 1 or not isinstance(values[0], Mapping):
        raise EvidenceError(f"Podman returned an invalid image observation for {reference}")
    value = values[0]
    digests: set[str] = set()
    if isinstance(value.get("Digest"), str) and _DIGEST.fullmatch(value["Digest"]):
        digests.add(value["Digest"])
    for item in value.get("RepoDigests") or []:
        if isinstance(item, str) and "@" in item:
            digest = item.rsplit("@", 1)[-1]
            if _DIGEST.fullmatch(digest):
                digests.add(digest)
    return {"imageId": str(value.get("Id", "")), "observedDigests": sorted(digests)}


def derive_build_observations(
    *, image_id: str, build_receipt_path: Path
) -> tuple[Mapping[str, Any], Mapping[str, Any], Mapping[str, Any], str]:
    receipt = _load_json_file(build_receipt_path)
    if receipt.get("formatVersion") != "stateport.release-image-build-receipt/v1":
        raise EvidenceError("image evidence requires a canonical release build receipt")
    image = receipt.get("images", {}).get(image_id)
    if not isinstance(image, Mapping):
        raise EvidenceError(f"build receipt does not contain image {image_id}")
    builds = image.get("builds")
    if not isinstance(builds, list) or [item.get("ordinal") for item in builds] != [1, 2]:
        raise EvidenceError("build receipt does not contain exactly two ordered observations")
    first, second = builds
    first_digest = str(first.get("pushedDigest"))
    second_digest = str(second.get("pushedDigest"))
    if not _DIGEST.fullmatch(first_digest) or not _DIGEST.fullmatch(second_digest):
        raise EvidenceError("build receipt contains an invalid observed digest")
    if first_digest != second_digest or image.get("reproducible") is not True:
        raise EvidenceError("build receipt does not prove an exact OCI digest match")
    accepted_reference = str(image.get("acceptedReference"))
    if (
        not _DIGEST_REFERENCE.fullmatch(accepted_reference)
        or accepted_reference.rsplit("@", 1)[-1] != second_digest
    ):
        raise EvidenceError("accepted image reference is not bound to the second observed build")
    for observation in (first, second):
        local_tag = str(observation.get("localTag"))
        live = _podman_observation(local_tag)
        if live["imageId"] != observation.get("localImageId"):
            raise EvidenceError("local image identity drifted after the recorded double build")
        digest_path = safe_path(build_receipt_path.parent, str(observation["digestFile"]))
        if sha256_file(digest_path) != observation.get("digestFileDigest"):
            raise EvidenceError("Podman digest observation file no longer matches its receipt")
        if digest_path.read_text(encoding="ascii").strip() != observation["pushedDigest"]:
            raise EvidenceError("Podman digest observation bytes disagree with the receipt")
    return receipt, image, second, sha256_file(build_receipt_path)


def validated_candidate_identity(
    *,
    candidate_provenance: Path,
    candidate_bundle: Path,
    receipt: Mapping[str, Any],
) -> dict[str, str]:
    if (
        candidate_provenance.is_symlink()
        or not candidate_provenance.is_file()
        or candidate_provenance.stat().st_size > 1024 * 1024
    ):
        raise EvidenceError("candidate provenance input is unavailable or unsafe")
    try:
        value = yaml.safe_load(candidate_provenance.read_text(encoding="utf-8"))
        schema = json.loads(
            (ROOT / "schemas/candidate-provenance.v1.schema.json").read_text(encoding="utf-8")
        )
        validated = validate_candidate_contract(value, schema)
        validate_repository_relationship(validated, ROOT)
        verify_candidate_bundle(validated, candidate_bundle)
    except (CandidateProvenanceError, OSError, subprocess.CalledProcessError) as exc:
        raise EvidenceError(f"candidate provenance verification failed: {exc}") from exc
    source = validated["materialization"]
    candidate = validated["repository"]
    if (
        source["sourceCommit"] != receipt["identity"]["commit"]
        or source["sourceTree"] != receipt["identity"]["tree"]
    ):
        raise EvidenceError(
            "candidate materialization source does not match the image build receipt"
        )
    return {
        "candidateId": str(validated["candidateId"]),
        "sourceRepository": str(source["sourceRepository"]),
        "sourceCommit": str(source["sourceCommit"]),
        "sourceTree": str(source["sourceTree"]),
        "publicSnapshotCommit": str(candidate["commit"]),
        "publicSnapshotTree": str(candidate["tree"]),
        "publicExportManifestDigest": "sha256:"
        + str(validated["artifacts"]["publicManifest"]["sha256"]),
        "candidateContractDigest": sha256_file(candidate_provenance),
        "candidateBundleDigest": sha256_file(candidate_bundle),
    }


def _resolved_dependencies(
    *, image: Mapping[str, Any], receipt: Mapping[str, Any], receipt_digest: str
) -> list[dict[str, Any]]:
    build_inputs = _load_yaml(BUILD_INPUTS)
    base_manifest = _load_yaml(BASE_IMAGES)
    containerfile = ROOT / str(image["containerfile"])
    from_references = {
        line.split()[1]
        for line in containerfile.read_text(encoding="utf-8").splitlines()
        if line.startswith("FROM ")
    }
    dependencies = [
        {
            "uri": f"stateport-build-receipt:{receipt['identity']['commit']}",
            "digest": {"sha256": receipt_digest.removeprefix("sha256:")},
        },
        {
            "uri": f"git-archive:{receipt['identity']['commit']}",
            "digest": {"sha256": str(receipt["context"]["archiveDigest"]).removeprefix("sha256:")},
        },
        {
            "uri": f"file:{image['containerfile']}",
            "digest": {"sha256": str(image["containerfileDigest"]).removeprefix("sha256:")},
        },
    ]
    for base in base_manifest["images"].values():
        if base["reference"] in from_references:
            dependencies.append(
                {
                    "uri": f"oci:{base['reference']}",
                    "digest": {"sha256": str(base["indexDigest"]).removeprefix("sha256:")},
                }
            )
    for lock in build_inputs["locks"].values():
        dependencies.append(
            {
                "uri": f"file:{lock['path']}",
                "digest": {"sha256": str(lock["digest"]).removeprefix("sha256:")},
            }
        )
    return dependencies


def build_provenance(
    *,
    image_id: str,
    image_reference: str,
    image: Mapping[str, Any],
    receipt: Mapping[str, Any],
    receipt_digest: str,
    source_repository: str,
    public_snapshot_commit: str,
    public_snapshot_tree: str,
    dependencies: list[dict[str, Any]],
    byproduct_paths: Sequence[Path],
) -> dict[str, Any]:
    provenance = {
        "_type": "https://in-toto.io/Statement/v1",
        "subject": [
            {
                "name": image_id,
                "digest": {"sha256": image_reference.rsplit(":", 1)[-1]},
            }
        ],
        "predicateType": "https://slsa.dev/provenance/v1",
        "predicate": {
            "buildDefinition": {
                "buildType": "https://stateport.invalid/buildtypes/oci/v1",
                "externalParameters": {
                    "sourceRepository": source_repository,
                    "sourceCommit": receipt["identity"]["commit"],
                    "sourceTree": receipt["identity"]["tree"],
                    "publicSnapshotCommit": public_snapshot_commit,
                    "publicSnapshotTree": public_snapshot_tree,
                    "platform": "linux/amd64",
                    "dockerfile": image["containerfile"],
                },
                "internalParameters": {
                    "sourceDateEpoch": receipt["identity"]["source_date_epoch"],
                    "networkMode": "dependency-fetch-only",
                },
                "resolvedDependencies": dependencies,
            },
            "runDetails": {
                "builder": {
                    "id": "https://podman.io/rootless-build/v1",
                    "version": receipt["builder"]["version"],
                },
                "metadata": {
                    "invocationId": hashlib.sha256(
                        (receipt_digest + image_id).encode("utf-8")
                    ).hexdigest(),
                    "startedOn": image["builds"][0]["startedAt"],
                    "finishedOn": image["builds"][1]["finishedAt"],
                },
                "byproducts": [
                    {"name": path.name, "digest": sha256_file(path)} for path in byproduct_paths
                ],
            },
        },
    }
    validate_release_provenance(provenance)
    return provenance


def load_scan_exceptions() -> tuple[Mapping[str, Any], str]:
    """Load the typed scan-exception contract and bind its exact bytes."""
    config = _load_yaml(SCAN_EXCEPTIONS)
    schema = json.loads(SCAN_EXCEPTIONS_SCHEMA.read_text(encoding="utf-8"))
    try:
        jsonschema.Draft202012Validator.check_schema(schema)
        jsonschema.Draft202012Validator(schema).validate(config)
    except (jsonschema.SchemaError, jsonschema.ValidationError) as exc:
        raise EvidenceError(f"scan exception contract is invalid: {exc.message}") from exc
    digest = "sha256:" + hashlib.sha256(SCAN_EXCEPTIONS.read_bytes()).hexdigest()
    return config, digest


def _scan_threshold() -> str:
    policy = _load_yaml(TOOLS).get("policy", {})
    threshold = str(policy.get("vulnerabilityFailureThreshold", "high")).lower()
    if threshold not in _THRESHOLD_ORDER:
        raise EvidenceError(f"unknown vulnerability failure threshold: {threshold}")
    return threshold


def _matching_exception(
    exceptions: Sequence[Mapping[str, Any]],
    *,
    advisory: str,
    package: str,
    package_version: str,
    image_id: str,
    today: str,
) -> Mapping[str, Any] | None:
    for exception in exceptions:
        if (
            str(exception["advisory"]) == advisory
            and str(exception["package"]) == package
            and (
                exception.get("packageVersion") is None
                or str(exception["packageVersion"]) == package_version
            )
            and image_id in exception["images"]
            and str(exception["expiresOn"]) >= today
        ):
            return exception
    return None


def evaluate_scan(
    *,
    scan_path: Path,
    image_id: str,
    exceptions_config: Mapping[str, Any],
    today: str,
) -> dict[str, Any]:
    """Classify every threshold-severity finding as explained or unexplained.

    A finding passes the gate only through an exact typed exception that names
    the same advisory and package, applies to this image, and is unexpired on
    the evaluation date. Everything else fails the image.
    """
    scan = _load_json_file(scan_path, maximum_bytes=256 * 1024 * 1024)
    threshold = _THRESHOLD_ORDER[_scan_threshold()]
    counts: dict[str, int] = {}
    applied: list[dict[str, Any]] = []
    unexplained: list[dict[str, Any]] = []
    for match in scan.get("matches", []):
        vulnerability = match.get("vulnerability", {})
        artifact = match.get("artifact", {})
        severity = str(vulnerability.get("severity", ""))
        counts[severity] = counts.get(severity, 0) + 1
        if _SEVERITY_ORDER.get(severity, -1) < threshold:
            continue
        advisory = str(vulnerability.get("id", ""))
        package = str(artifact.get("name", ""))
        version = str(artifact.get("version", ""))
        fix = vulnerability.get("fix", {})
        finding = {
            "advisory": advisory,
            "package": package,
            "packageVersion": version,
            "severity": severity,
            "fixState": str(fix.get("state", "unknown")),
            "fixVersions": [str(item) for item in fix.get("versions", []) if item],
        }
        exception = _matching_exception(
            exceptions_config["exceptions"],
            advisory=advisory,
            package=package,
            package_version=version,
            image_id=image_id,
            today=today,
        )
        if exception is None:
            unexplained.append(finding)
        else:
            applied.append({**finding, "exceptionId": str(exception["id"])})
    return {
        "formatVersion": "stateport.release-scan-evaluation/v1",
        "imageId": image_id,
        "evaluatedOn": today,
        "findingsBySeverity": counts,
        "appliedExceptions": sorted(applied, key=lambda item: (item["advisory"], item["package"])),
        "unexplainedFindings": sorted(
            unexplained, key=lambda item: (item["advisory"], item["package"])
        ),
    }


def collect(
    *,
    image_id: str,
    build_receipt: Path,
    candidate_provenance: Path,
    candidate_bundle: Path,
    output_root: Path,
) -> dict[str, Any]:
    _progress(image_id, "identity validation starting")
    started = time.monotonic()
    receipt, image, second, receipt_digest = derive_build_observations(
        image_id=image_id, build_receipt_path=build_receipt
    )
    candidate = validated_candidate_identity(
        candidate_provenance=candidate_provenance,
        candidate_bundle=candidate_bundle,
        receipt=receipt,
    )
    _progress(image_id, f"identity validation complete in {time.monotonic() - started:.1f}s")
    image_reference = str(image["acceptedReference"])
    _progress(image_id, "toolchain validation starting")
    started = time.monotonic()
    tools = verify_toolchain()
    _progress(image_id, f"toolchain validation complete in {time.monotonic() - started:.1f}s")
    output = prepare_output_root(output_root, repository=ROOT)
    _progress(image_id, "Grype database validation starting")
    started = time.monotonic()
    database = grype_database_status()
    _progress(image_id, f"Grype database validation complete in {time.monotonic() - started:.1f}s")
    write_json_create_only(output, f"{image_id}.grype-db.json", database)
    local_source = _catalogue_source(
        image=image,
        build_receipt_path=build_receipt,
        local_tag=str(second["localTag"]),
    )
    _progress(image_id, f"catalogue source: {local_source}")
    syft = tools["syft"]["executable"]
    grype = tools["grype"]["executable"]
    cdx, spdx, syft_json = _collect_sboms(
        image_id=image_id,
        local_source=local_source,
        syft=syft,
        output=output,
    )
    scan = _collect_grype_scan(
        image_id=image_id,
        syft_json=syft_json,
        grype=grype,
        output=output,
    )
    _progress(image_id, "scan policy evaluation starting")
    exceptions_config, exceptions_digest = load_scan_exceptions()
    evaluation = evaluate_scan(
        scan_path=scan,
        image_id=image_id,
        exceptions_config=exceptions_config,
        today=datetime.now(timezone.utc).date().isoformat(),
    )
    evaluation_path = write_json_create_only(output, f"{image_id}.scan-evaluation.json", evaluation)
    _progress(image_id, "scan policy evaluation complete")
    packages = json.loads(syft_json.read_text(encoding="utf-8")).get("artifacts", [])
    licences = sorted(
        {
            str(license_item["value"])
            for package in packages
            for license_item in package.get("licenses", [])
            if isinstance(license_item, Mapping) and license_item.get("value")
        }
    )
    inventory = {
        "formatVersion": "stateport.license-inventory/v1",
        "imageId": image_id,
        "imageReference": image_reference,
        "licenses": licences,
    }
    license_path = write_json_create_only(output, f"{image_id}.licenses.json", inventory)
    comparison = {
        "formatVersion": "stateport.double-build-comparison/v1",
        "imageId": image_id,
        "first": {
            "digest": image["builds"][0]["pushedDigest"],
            "digestObservationDigest": image["builds"][0]["digestFileDigest"],
            "localImageId": image["builds"][0]["localImageId"],
        },
        "second": {
            "digest": image["builds"][1]["pushedDigest"],
            "digestObservationDigest": image["builds"][1]["digestFileDigest"],
            "localImageId": image["builds"][1]["localImageId"],
        },
        "reproducible": True,
        "interpretation": "exact independently observed OCI registry digest match",
    }
    comparison_path = write_json_create_only(output, f"{image_id}.double-build.json", comparison)
    health_path = write_json_create_only(
        output,
        f"{image_id}.healthcheck.json",
        _health_observation(
            image_id=image_id,
            image_reference=image_reference,
            local_tag=str(second["localTag"]),
        ),
    )
    _progress(image_id, "provenance and manifest assembly starting")
    byproduct_paths = [
        cdx,
        spdx,
        syft_json,
        scan,
        evaluation_path,
        license_path,
        comparison_path,
        health_path,
        output / f"{image_id}.grype-db.json",
    ]
    dependencies = _resolved_dependencies(
        image=image, receipt=receipt, receipt_digest=receipt_digest
    )
    provenance = build_provenance(
        image_id=image_id,
        image_reference=image_reference,
        image=image,
        receipt=receipt,
        receipt_digest=receipt_digest,
        source_repository=candidate["sourceRepository"],
        public_snapshot_commit=candidate["publicSnapshotCommit"],
        public_snapshot_tree=candidate["publicSnapshotTree"],
        dependencies=dependencies,
        byproduct_paths=byproduct_paths,
    )
    provenance_path = write_json_create_only(output, f"{image_id}.provenance.json", provenance)
    artifact_paths = [*byproduct_paths, provenance_path]
    manifest = {
        "formatVersion": "stateport.release-image-evidence/v1",
        "imageId": image_id,
        "imageReference": image_reference,
        "buildReceiptDigest": receipt_digest,
        "candidate": candidate,
        "tools": tools,
        "grypeDatabase": database,
        "scanPolicy": {
            "threshold": _scan_threshold(),
            "unfixedFindingsIncluded": True,
            "result": "passed" if not evaluation["unexplainedFindings"] else "failed",
            "exceptionsFile": "config/release-scan-exceptions.v1.yaml",
            "exceptionsDigest": exceptions_digest,
            "evaluationArtifact": evaluation_path.name,
            "appliedExceptionIds": sorted(
                {item["exceptionId"] for item in evaluation["appliedExceptions"]}
            ),
            "unexplainedFindings": evaluation["unexplainedFindings"],
        },
        "artifacts": {path.name: sha256_file(path) for path in artifact_paths},
        "signature": {
            "status": "pending_owner_trust_root",
            "publicTransparencyLogUpload": False,
            "privateVerification": "pinned-public-key-fingerprint-and-key-id",
        },
        "doubleBuild": comparison,
    }
    write_json_create_only(output, f"{image_id}.evidence.json", manifest)
    _progress(image_id, "evidence collection complete")
    if evaluation["unexplainedFindings"]:
        preview = ", ".join(
            f"{item['advisory']}:{item['package']}"
            for item in evaluation["unexplainedFindings"][:8]
        )
        raise EvidenceError(
            f"unexplained high-or-critical vulnerability findings refuse {image_id} "
            f"({len(evaluation['unexplainedFindings'])}): {preview}; evidence retained"
        )
    return manifest


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--image-id", required=True)
    parser.add_argument("--build-receipt", type=Path, required=True)
    parser.add_argument("--candidate-provenance", type=Path, required=True)
    parser.add_argument("--candidate-bundle", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    args = parser.parse_args(argv)
    print(
        json.dumps(
            collect(
                image_id=args.image_id,
                build_receipt=args.build_receipt,
                candidate_provenance=args.candidate_provenance,
                candidate_bundle=args.candidate_bundle,
                output_root=args.output_root,
            ),
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (EvidenceError, OSError, ValueError, yaml.YAMLError) as exc:
        print(f"release evidence refused: {exc}", file=sys.stderr)
        raise SystemExit(2) from exc
