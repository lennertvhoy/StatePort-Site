from __future__ import annotations

from importlib.util import module_from_spec, spec_from_file_location
from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess
import sys

import pytest
import yaml


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
spec = spec_from_file_location(
    "collect_release_evidence", ROOT / "scripts/collect_release_evidence.py"
)
assert spec and spec.loader
module = module_from_spec(spec)
sys.modules[spec.name] = module
spec.loader.exec_module(module)


def test_installed_supply_chain_tools_match_pinned_versions_hashes_and_bottles() -> None:
    observed = module.verify_toolchain()
    assert set(observed) == {"syft", "grype", "cosign"}
    assert observed["syft"]["version"] == "1.50.0"
    assert observed["grype"]["version"] == "0.116.1"
    assert observed["cosign"]["version"] == "3.1.2"


def _ephemeral_cosign_key(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Generate an ephemeral, test-only Cosign key pair; never release evidence."""

    monkeypatch.setenv("COSIGN_PASSWORD", "test-ephemeral-non-release")
    cosign = "/home/linuxbrew/.linuxbrew/bin/cosign"
    subprocess.run(
        [cosign, "generate-key-pair", "--output-key-prefix", "test"],
        cwd=tmp_path,
        check=True,
        capture_output=True,
    )
    return tmp_path / "test.pub"


def test_private_cosign_command_requires_exact_der_spki_key_fingerprint(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    artifact = tmp_path / "artifact"
    artifact.write_bytes(b"artifact")
    bundle = tmp_path / "artifact.sigstore.json"
    bundle.write_text("{}")
    public_key = _ephemeral_cosign_key(tmp_path, monkeypatch)
    fingerprint = module.public_key_der_spki_fingerprint(public_key)
    assert fingerprint != module.sha256_file(public_key)
    command = module.signature_verification_command(
        artifact=artifact,
        bundle=bundle,
        public_key=public_key,
        expected_key_fingerprint=fingerprint,
        expected_key_id="stateport-alpha-private-2026-08",
        configured_key_id="stateport-alpha-private-2026-08",
    )
    assert command[0] == "/home/linuxbrew/.linuxbrew/bin/cosign"
    assert command[1] == "verify-blob"
    assert "--insecure-ignore-tlog" in command
    assert "--bundle" in command and "--key" in command
    with pytest.raises(module.EvidenceError, match="fingerprint"):
        module.signature_verification_command(
            artifact=artifact,
            bundle=bundle,
            public_key=public_key,
            expected_key_fingerprint=module.sha256_file(public_key),
            expected_key_id="stateport-alpha-private-2026-08",
            configured_key_id="stateport-alpha-private-2026-08",
        )
    with pytest.raises(module.EvidenceError, match="key ID"):
        module.signature_verification_command(
            artifact=artifact,
            bundle=bundle,
            public_key=public_key,
            expected_key_fingerprint=fingerprint,
            expected_key_id="stateport-alpha-private-2026-08",
            configured_key_id="wrong-key-id",
        )


def test_signature_policy_never_claims_a_private_release_trust_root() -> None:
    value = yaml.safe_load((ROOT / "config/release-tool-inputs.yaml").read_text())
    signature = value["policy"]["signature"]
    assert signature["status"] == "pending_owner_trust_root"
    assert signature["publicTransparencyLogUpload"] is False
    assert signature["testKeys"] == "ephemeral_non_release_only"


def _build_receipt(tmp_path: Path) -> Path:
    digest = "sha256:" + "a" * 64
    builds = []
    for ordinal in (1, 2):
        relative = f"digests/web-{ordinal}.digest"
        path = tmp_path / relative
        path.parent.mkdir(exist_ok=True, mode=0o700)
        path.write_text(digest + "\n", encoding="ascii")
        builds.append(
            {
                "ordinal": ordinal,
                "localTag": f"127.0.0.1:5000/stateport-alpha/stateport-web:test-{ordinal}",
                "localImageId": "local-image-id",
                "digestFile": relative,
                "digestFileDigest": module.sha256_file(path),
                "pushedDigest": digest,
                "digestReference": f"127.0.0.1:5000/stateport-alpha/stateport-web@{digest}",
                "pulledImageId": "local-image-id",
                "observedRemoteDigests": [digest],
                "startedAt": "2026-08-01T10:00:00Z",
                "finishedAt": "2026-08-01T10:01:00Z",
            }
        )
    receipt = {
        "formatVersion": "stateport.release-image-build-receipt/v1",
        "identity": {
            "commit": "b" * 40,
            "tree": "c" * 40,
            "version": "0.2.0-alpha.1",
            "created": "2026-08-01T10:00:00Z",
            "source_date_epoch": 1785578400,
        },
        "builder": {"version": "5.8.4"},
        "context": {"archiveDigest": "sha256:" + "d" * 64},
        "images": {
            "stateport-web": {
                "containerfile": "apps/web/Dockerfile",
                "containerfileDigest": "sha256:" + "e" * 64,
                "builds": builds,
                "reproducible": True,
                "acceptedReference": f"127.0.0.1:5000/stateport-alpha/stateport-web@{digest}",
            }
        },
    }
    path = tmp_path / "build-receipt.json"
    path.write_text(json.dumps(receipt), encoding="utf-8")
    return path


def test_double_build_digests_are_derived_from_receipt_and_live_image_identity(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    tmp_path.chmod(0o700)
    receipt_path = _build_receipt(tmp_path)
    monkeypatch.setattr(
        module,
        "_podman_observation",
        lambda _reference: {"imageId": "local-image-id", "observedDigests": ["sha256:" + "a" * 64]},
    )
    receipt, image, second, receipt_digest = module.derive_build_observations(
        image_id="stateport-web", build_receipt_path=receipt_path
    )
    assert receipt["identity"]["commit"] == "b" * 40
    assert image["builds"][0]["pushedDigest"] == image["builds"][1]["pushedDigest"]
    assert second["ordinal"] == 2
    assert receipt_digest == module.sha256_file(receipt_path)

    digest_path = tmp_path / "digests/web-2.digest"
    digest_path.chmod(0o600)
    digest_path.write_text("sha256:" + "f" * 64 + "\n", encoding="ascii")
    with pytest.raises(module.EvidenceError, match="no longer matches"):
        module.derive_build_observations(image_id="stateport-web", build_receipt_path=receipt_path)


def test_provenance_matches_canonical_schema_and_binds_dependencies_and_byproducts(
    tmp_path: Path,
) -> None:
    byproduct = tmp_path / "web.cdx.json"
    byproduct.write_text("{}\n", encoding="utf-8")
    receipt = {
        "identity": {
            "commit": "b" * 40,
            "tree": "c" * 40,
            "source_date_epoch": 1785578400,
        },
        "builder": {"version": "5.8.4"},
    }
    image = {
        "containerfile": "apps/web/Dockerfile",
        "builds": [
            {"startedAt": "2026-08-01T10:00:00Z"},
            {"finishedAt": "2026-08-01T10:01:00Z"},
        ],
    }
    dependency = {"uri": "oci:example", "digest": {"sha256": "d" * 64}}
    provenance = module.build_provenance(
        image_id="stateport-web",
        image_reference="registry.example/stateport-web@sha256:" + "a" * 64,
        image=image,
        receipt=receipt,
        receipt_digest="sha256:" + "f" * 64,
        source_repository="https://github.com/lennertvhoy/StatePort.git",
        public_snapshot_commit="1" * 40,
        public_snapshot_tree="2" * 40,
        dependencies=[dependency],
        byproduct_paths=[byproduct],
    )
    definition = provenance["predicate"]["buildDefinition"]
    assert definition["buildType"] == "https://stateport.invalid/buildtypes/oci/v1"
    assert definition["resolvedDependencies"] == [dependency]
    assert provenance["predicate"]["runDetails"]["byproducts"][0]["digest"] == module.sha256_file(
        byproduct
    )


def test_grype_freshness_and_unfixed_policy_fail_closed(monkeypatch: pytest.MonkeyPatch) -> None:
    now = datetime(2026, 8, 1, 12, tzinfo=timezone.utc)
    monkeypatch.setattr(
        module,
        "_run",
        lambda _arguments: json.dumps(
            {"schemaVersion": "v6", "built": "2026-08-01T11:30:00Z", "valid": True}
        ),
    )
    assert module.grype_database_status(now=now)["valid"] is True
    monkeypatch.setattr(
        module,
        "_run",
        lambda _arguments: json.dumps(
            {"schemaVersion": "v6", "built": "2026-07-30T11:30:00Z", "valid": True}
        ),
    )
    with pytest.raises(module.EvidenceError, match="not fresh"):
        module.grype_database_status(now=now)
    source = (ROOT / "scripts/collect_release_evidence.py").read_text(encoding="utf-8")
    assert "--only-fixed" not in source
    assert '"--first-digest"' not in source and '"--second-digest"' not in source
    assert '"--public-snapshot-commit"' not in source
    assert '"--public-snapshot-tree"' not in source


def test_evidence_collection_uses_one_syft_catalogue_and_scans_its_json() -> None:
    source = (ROOT / "scripts/collect_release_evidence.py").read_text(encoding="utf-8")
    assert 'f"syft-json={syft_json}"' in source
    assert 'f"cyclonedx-json={cdx}"' in source
    assert 'f"spdx-json={spdx}"' in source
    assert 'f"sbom:{syft_json}"' in source
    assert source.count('"-o",\n                f"') >= 3
    assert '[grype, local_source, "-o", "json"]' not in source
    assert 'f"oci-archive:{archive_path}"' in source


def test_candidate_identity_is_rederived_and_bound_to_build_source(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    candidate = {
        "candidateId": "stateport-public-candidate-test",
        "materialization": {
            "sourceRepository": "https://github.com/lennertvhoy/StatePort.git",
            "sourceCommit": "b" * 40,
            "sourceTree": "c" * 40,
        },
        "repository": {"commit": "d" * 40, "tree": "e" * 40},
        "artifacts": {"publicManifest": {"sha256": "f" * 64}},
    }
    contract = tmp_path / "candidate.yaml"
    contract.write_text(yaml.safe_dump(candidate), encoding="utf-8")
    bundle = tmp_path / "candidate.bundle"
    bundle.write_bytes(b"verified-test-bundle")
    monkeypatch.setattr(module, "validate_candidate_contract", lambda value, _schema: value)
    monkeypatch.setattr(module, "validate_repository_relationship", lambda _value, _root: None)
    monkeypatch.setattr(module, "verify_candidate_bundle", lambda _value, _bundle: None)
    receipt = {"identity": {"commit": "b" * 40, "tree": "c" * 40}}
    identity = module.validated_candidate_identity(
        candidate_provenance=contract,
        candidate_bundle=bundle,
        receipt=receipt,
    )
    assert identity["publicSnapshotCommit"] == "d" * 40
    assert identity["publicSnapshotTree"] == "e" * 40
    assert identity["candidateContractDigest"] == module.sha256_file(contract)
    assert identity["candidateBundleDigest"] == module.sha256_file(bundle)

    receipt["identity"]["commit"] = "0" * 40
    with pytest.raises(module.EvidenceError, match="does not match"):
        module.validated_candidate_identity(
            candidate_provenance=contract,
            candidate_bundle=bundle,
            receipt=receipt,
        )
