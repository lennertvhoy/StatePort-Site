from __future__ import annotations

from datetime import datetime, timedelta, timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

import jsonschema
import pytest
import yaml


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "packages/release-contracts/src"))

from stateport_release import (  # noqa: E402
    CosignVerificationError,
    CosignVerifier,
    PinnedPublicKeyIdentity,
    ReleaseContractError,
    ReleaseVerificationPolicy,
    SignatureVerificationProof,
    canonical_json_bytes,
    load_release_index_file,
    public_key_der_spki_fingerprint,
    validate_release_index,
    verify_release_index,
)
import assemble_release_index as assembler  # noqa: E402
from release_safe_io import sha256_file  # noqa: E402


COSIGN = Path("/home/linuxbrew/.linuxbrew/bin/cosign")
pytestmark = pytest.mark.skipif(
    not COSIGN.is_file(), reason="pinned Cosign toolchain is unavailable"
)

COMMIT = "b" * 40
TREE = "c" * 40
PUBLIC_COMMIT = "d" * 40
PUBLIC_TREE = "e" * 40
IMAGES = ("stateport-web", "stateport-api", "stateport-worker", "stateport-execution-host")
HEALTH = {
    "stateport-web": (8080, "/health"),
    "stateport-api": (8790, "/readyz"),
    "stateport-worker": (8791, "/readyz"),
}
BUNDLE_MEDIA_TYPE = "application/vnd.dev.sigstore.bundle.v0.3+json"


@pytest.fixture(scope="module")
def trust_root(tmp_path_factory: pytest.TempPathFactory) -> dict[str, object]:
    """Ephemeral, test-only Cosign key pair; never release evidence."""

    root = tmp_path_factory.mktemp("trust-root")
    root.chmod(0o700)
    env = {**os.environ, "COSIGN_PASSWORD": "test-ephemeral-non-release"}
    subprocess.run(
        [str(COSIGN), "generate-key-pair", "--output-key-prefix", "test"],
        cwd=root,
        check=True,
        capture_output=True,
        env=env,
    )
    public = root / "test.pub"
    return {
        "private": root / "test.key",
        "public": public,
        "fingerprint": public_key_der_spki_fingerprint(public),
        "key_id": "stateport-alpha-test-2026-08",
    }


@pytest.fixture(autouse=True)
def _cosign_password(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("COSIGN_PASSWORD", "test-ephemeral-non-release")


def _timestamp(value: datetime) -> str:
    return value.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _service(
    service_id: str,
    volume_name: str,
    mount_path: str,
    control_contract: str = "none",
) -> dict[str, object]:
    port, path = HEALTH[service_id]
    return {
        "serviceId": service_id,
        "imageId": service_id,
        "trustDomain": "control",
        "quadletOwner": "stateport-control",
        "revisionScoped": True,
        "runAsUser": 65532,
        "readOnlyRoot": True,
        "health": {"kind": "http", "containerPort": port, "path": path},
        "ports": [
            {
                "name": "http",
                "containerPort": port,
                "hostScope": "loopback",
                "allocation": "full-revision-digest-derived-collision-probed",
            }
        ],
        "writableVolumes": [
            {
                "name": volume_name,
                "mountPath": mount_path,
                "purpose": "durable-state",
                "scope": "installation",
                "validation": {
                    "mode": "read-only-snapshot-copy",
                    "authority": "exact-backup-receipt-required",
                },
            }
        ],
        "resources": {"memoryMaxBytes": 1073741824, "cpuQuotaPercent": 200, "pidsMax": 512},
        "capabilities": {"podmanSocketAccess": "none", "controlContract": control_contract},
    }


def _execution_host_service() -> dict[str, object]:
    return {
        "serviceId": "stateport-execution-host",
        "imageId": "stateport-execution-host",
        "trustDomain": "execution",
        "quadletOwner": "stateport-exec",
        "revisionScoped": False,
        "lifecycle": "stable-out-of-revision",
        "runAsUser": 65532,
        "readOnlyRoot": True,
        "engineAccess": {
            "mode": "owned-execution-user-podman-socket",
            "owner": "stateport-exec",
            "hostPath": "%t/podman/podman.sock",
            "containerPath": "/run/stateport-engine/podman.sock",
            "access": "read-write",
        },
        "socket": {
            "transport": "confined-host-unix-socket",
            "hostDirectory": "/run/stateport/execution-control",
            "socketName": "control.sock",
            "directoryOwner": "stateport-exec",
            "directoryGroup": "stateport-execution-control",
            "allowedClientUser": "stateport-control",
            "directoryMode": "0750",
            "socketMode": "0660",
            "peerIdentity": "unix-peer-credentials-required",
        },
        "ports": [
            {
                "name": "metrics",
                "containerPort": 9911,
                "hostPort": 17001,
                "hostScope": "private-proxy",
                "allocation": "stable-operator-bound",
            }
        ],
        "writableVolumes": [
            {
                "name": "execution-state",
                "hostPath": "/var/lib/stateport-exec/stateport-execution-host/state",
                "mountPath": "/var/lib/stateport/execution-host",
                "purpose": "durable-state",
                "scope": "stable-host-service",
                "owner": "stateport-exec",
                "mode": "rw",
            }
        ],
        "resources": {"memoryMaxBytes": 536870912, "cpuQuotaPercent": 100, "pidsMax": 256},
        "logging": {"driver": "k8s-file", "maxSizeBytes": 10485760},
        "health": {"kind": "unix-socket", "value": "/run/stateport-execution/control.sock"},
        "updateCompatibility": {
            "contractVersion": 1,
            "minimumClientVersion": 1,
            "maximumClientVersion": 2,
            "replacementPolicy": "explicit-compatible-host-update-only",
        },
    }


def _execution_contract() -> dict[str, object]:
    return {
        "transport": "confined-host-unix-socket",
        "serviceId": "stateport-execution-host",
        "imageId": "stateport-execution-host",
        # The assembler binds the digest to the exact signed stable-host image.
        "imageDigest": None,
        "contractVersion": 1,
        "clientCompatibility": {"minimum": 1, "maximum": 2},
        "hostDirectory": "/run/stateport/execution-control",
        "containerDirectory": "/run/stateport-execution",
        "socketName": "control.sock",
        "bootstrap": "operator-provisioned-tmpfiles",
        "directoryOwner": "stateport-exec",
        "directoryGroup": "stateport-execution-control",
        "allowedClientUser": "stateport-control",
        "directoryMode": "0750",
        "socketMode": "0660",
        "peerIdentity": "unix-peer-credentials-required",
    }


def _runtime_derivation() -> dict[str, object]:
    return {
        "format": "stateport.revision-materialization/v2",
        "profiles": ["validation", "accepted"],
        "materialization": {
            "templateTokenVersion": "stateport.quadlet-template/v2",
            "stageRoot": "/var/lib/stateport/releases/staged",
            "liveQuadletRoots": {
                "stateport-control": "xdg-config-containers-systemd",
                "stateport-exec": "xdg-config-containers-systemd",
            },
            "regularSystemdRoot": "xdg-config-systemd-user",
            "candidateLocation": "outside-live-quadlet-search-roots",
            "acceptedLocation": "copied-after-acceptance-cas-only",
        },
        "portPolicy": {
            "algorithm": "sha256-full-revision-service-port-modulo-probe-v1",
            "rangeStart": 18000,
            "rangeEnd": 18999,
            "probeStep": 17,
            "maximumAttempts": 512,
            "collisionInputs": ["current", "predecessor", "candidate"],
            "observedHostCollision": "installer-refuses-before-start",
        },
        "stateMachine": {
            "stage": [
                "verify-images-by-digest-and-signature",
                "materialize-outside-live-quadlet-roots",
                "verify-materialization-manifest",
                "pre-pull-with-pull-never-runtime",
            ],
            "validate": [
                "create-exact-backup-or-snapshot-copy",
                "start-validation-profile-only",
                "run-health-api-browser-and-state-checks",
                "stop-validation-profile",
                "retain-validation-evidence",
            ],
            "promote": [
                "acquire-quiesced-maintenance-lease",
                "stop-and-discard-validation-generation",
                "fence-ingress-and-quiesce-predecessor-writers",
                "write-fresh-authoritative-backup-d0",
                "create-and-migrate-distinct-data-generation-d1",
                "fsync-data-generation-d1",
                "run-private-candidate-checks-on-d1",
                "write-durable-activation-decision-receipt-r1",
                "reconcile-owner-bundles-per-user",
                "atomically-materialize-and-fsync-regular-target-and-route-projections",
                "daemon-reload-control-user",
                "explicitly-start-observe-and-stop-candidate",
                "write-terminal-promotion-receipts",
                "switch-ingress-and-unfence",
                "retain-predecessor",
            ],
            "rollback": [
                "stop-failed-candidate",
                "evaluate-data-compatibility",
                "restore-or-reuse-data-only-if-authorized",
                "copy-predecessor-profile-to-live-quadlet-roots",
                "daemon-reload",
                "start-predecessor",
                "run-health-and-state-checks",
                "route-cas-to-predecessor",
                "enable-predecessor-activation-target",
                "retain-failure-evidence",
                "do-not-claim-external-side-effect-reversal",
            ],
            "rebootRecovery": [
                "load-accepted-pointer",
                "verify-acceptance-receipt",
                "materialize-only-accepted-live-units",
                "daemon-reload",
                "start-accepted-activation-target",
                "refuse-staged-or-stale-auto-start",
            ],
            "activationCas": "generation-and-acceptance-receipt-digest",
        },
    }


def _image_digest(image_id: str) -> str:
    return "sha256:" + hashlib.sha256(f"test-image-{image_id}".encode()).hexdigest()


def _build_inputs(tmp_path: Path) -> dict[str, object]:
    tmp_path.mkdir(mode=0o700, exist_ok=True)
    tmp_path.chmod(0o700)
    now = datetime.now(timezone.utc)
    built_at = _timestamp(now - timedelta(hours=2))
    observed_at = _timestamp(now - timedelta(hours=1))
    expires_at = _timestamp(now + timedelta(days=30))
    pinned = yaml.safe_load((ROOT / "config/release-tool-inputs.yaml").read_text())["tools"]
    tool_records = {
        name: {
            "version": str(tool["version"]),
            "executableDigest": str(tool["executableDigest"]),
            "bottleDigest": str(tool["bottleDigest"]),
            "provenance": str(tool["provenance"]),
        }
        for name, tool in pinned.items()
    }

    operator = tmp_path / "operator"
    operator.mkdir(mode=0o700)
    files: dict[str, Path] = {}
    for name, content in {
        "installer": b"test-installer\n",
        "updater": b"test-updater\n",
        "source-archive.tar.gz": b"test-source-archive\n",
        "release-notes.md": b"# test release notes\n",
        "known-limitations.md": b"# test known limitations\n",
        "public-export.json": b'{"formatVersion":"stateport.public-export-manifest/v1"}\n',
    }.items():
        path = operator / name
        path.write_bytes(content)
        files[name] = path
    public_manifest_sha = hashlib.sha256(files["public-export.json"].read_bytes()).hexdigest()
    source_archive_sha = hashlib.sha256(files["source-archive.tar.gz"].read_bytes()).hexdigest()

    candidate = tmp_path / "candidate.yaml"
    candidate.write_text(
        yaml.safe_dump(
            {
                "schema": "stateport.candidate-provenance/v1",
                "candidateId": "stateport-public-candidate-test",
                "materialization": {
                    "sourceRepository": "https://github.com/lennertvhoy/StatePort.git",
                    "sourceCommit": COMMIT,
                    "sourceTree": TREE,
                },
                "repository": {"commit": PUBLIC_COMMIT, "tree": PUBLIC_TREE},
                "artifacts": {
                    "publicManifest": {"sha256": public_manifest_sha},
                    "auditedSourceArchive": {"sha256": source_archive_sha},
                },
            }
        ),
        encoding="utf-8",
    )

    evidence = tmp_path / "evidence"
    evidence.mkdir(mode=0o700)
    bundles = tmp_path / "bundles"
    bundles.mkdir(mode=0o700)
    for image_id in IMAGES:
        digest = _image_digest(image_id)
        artifacts: dict[str, str] = {}
        for suffix in (
            "cdx.json",
            "spdx.json",
            "syft.json",
            "grype.json",
            "licenses.json",
            "double-build.json",
            "grype-db.json",
            "provenance.json",
            "healthcheck.json",
        ):
            path = evidence / f"{image_id}.{suffix}"
            if suffix == "healthcheck.json":
                path.write_text(
                    json.dumps(
                        {
                            "formatVersion": "stateport.release-image-healthcheck/v1",
                            "imageId": image_id,
                            "probeObservation": {"executed": True, "exitCode": 1},
                        }
                    )
                    + "\n",
                    encoding="utf-8",
                )
            else:
                path.write_text(
                    json.dumps({"testArtifact": suffix, "imageId": image_id}) + "\n",
                    encoding="utf-8",
                )
            if suffix != "healthcheck.json":
                artifacts[path.name] = sha256_file(path)
        manifest = {
            "formatVersion": "stateport.release-image-evidence/v1",
            "imageId": image_id,
            "imageReference": f"127.0.0.1:5000/stateport-alpha/{image_id}@{digest}",
            "buildReceiptDigest": "sha256:" + "0" * 64,
            "candidate": {
                "candidateId": "stateport-public-candidate-test",
                "sourceRepository": "https://github.com/lennertvhoy/StatePort.git",
                "sourceCommit": COMMIT,
                "sourceTree": TREE,
                "publicSnapshotCommit": PUBLIC_COMMIT,
                "publicSnapshotTree": PUBLIC_TREE,
                "publicExportManifestDigest": "sha256:" + public_manifest_sha,
            },
            "tools": tool_records,
            "grypeDatabase": {
                "builtAt": built_at,
                "observedAt": observed_at,
                "ageHours": 1.0,
                "maximumAgeHours": 24,
                "valid": True,
            },
            "scanPolicy": {
                "threshold": "high",
                "unfixedFindingsIncluded": True,
                "result": "passed",
                "exceptionsFile": "config/release-scan-exceptions.v1.yaml",
                "exceptionsDigest": "sha256:"
                + hashlib.sha256(
                    (ROOT / "config/release-scan-exceptions.v1.yaml").read_bytes()
                ).hexdigest(),
                "appliedExceptionIds": [],
                "unexplainedFindings": [],
            },
            "artifacts": artifacts,
            "signature": {
                "status": "pending_owner_trust_root",
                "publicTransparencyLogUpload": False,
                "privateVerification": "pinned-public-key-fingerprint-and-key-id",
            },
            "doubleBuild": {
                "formatVersion": "stateport.double-build-comparison/v1",
                "imageId": image_id,
                "first": {"digest": digest},
                "second": {"digest": digest},
                "reproducible": True,
            },
        }
        (evidence / f"{image_id}.evidence.json").write_text(
            json.dumps(manifest) + "\n", encoding="utf-8"
        )
        (bundles / f"{image_id}.sigstore.json").write_text(
            json.dumps(
                {
                    "mediaType": BUNDLE_MEDIA_TYPE,
                    "verificationMaterial": {"publicKey": {"hint": "dGVzdA=="}},
                    "messageSignature": {
                        "messageDigest": {"algorithm": "SHA2_256", "digest": "dGVzdA=="},
                        "signature": "dGVzdA==",
                    },
                }
            )
            + "\n",
            encoding="utf-8",
        )

    receipt = tmp_path / "build-receipt.json"
    receipt.write_text(
        json.dumps(
            {
                "formatVersion": "stateport.release-image-build-receipt/v1",
                "identity": {
                    "commit": COMMIT,
                    "tree": TREE,
                    "version": "0.2.0-alpha.1",
                    "created": observed_at,
                    "source_date_epoch": 1785578400,
                },
                "builder": {"version": "5.8.4"},
                "images": {
                    image_id: {
                        "acceptedReference": (
                            f"127.0.0.1:5000/stateport-alpha/{image_id}@{_image_digest(image_id)}"
                        ),
                        "releaseAuthority": {
                            "kind": "retained-oci-archive",
                            "sizeBytes": 1048576,
                            "manifestDigest": _image_digest(image_id),
                        },
                    }
                    for image_id in IMAGES
                },
            }
        )
        + "\n",
        encoding="utf-8",
    )

    topology = tmp_path / "topology.yaml"
    topology.write_text(
        yaml.safe_dump(
            {
                "targets": [
                    {
                        "targetId": "ubuntu-24.04-linux-amd64",
                        "executionHostMode": "stable-host-daemon-client",
                        "executionContract": _execution_contract(),
                        "hostServices": [_execution_host_service()],
                        "runtimeDerivation": _runtime_derivation(),
                        "services": [
                            _service(
                                "stateport-web",
                                "stateport-data",
                                "/var/lib/stateport",
                                control_contract="narrow-unix-client",
                            ),
                            _service(
                                "stateport-api",
                                "stateport-operations-api",
                                "/workspace/.stateport",
                            ),
                            _service(
                                "stateport-worker",
                                "stateport-operations-worker",
                                "/workspace/.stateport",
                            ),
                        ],
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    return {
        "receipt": receipt,
        "candidate": candidate,
        "evidence": evidence,
        "bundles": bundles,
        "topology": topology,
        "expires_at": expires_at,
        "installer": files["installer"],
        "updater": files["updater"],
        "source_archive": files["source-archive.tar.gz"],
        "release_notes": files["release-notes.md"],
        "known_limitations": files["known-limitations.md"],
        "public_export_manifest": files["public-export.json"],
    }


def _request(
    inputs: dict[str, object],
    trust_root: dict[str, object],
    output: Path,
    **changes: object,
) -> assembler.AssemblyRequest:
    values: dict[str, object] = {
        "build_receipt": inputs["receipt"],
        "evidence_dir": inputs["evidence"],
        "candidate_provenance": inputs["candidate"],
        "topology": inputs["topology"],
        "release_id": "stateport-alpha-0.2.0-rc.1",
        "version": "0.2.0-rc.1",
        "channel": "alpha",
        "qualification": "candidate",
        "image_repository": "ghcr.io/stateport/stateport-alpha",
        "public_snapshot_repository": "https://github.com/stateport/stateport-public.git",
        "updater_minimum_version": "0.1.0",
        "schema_migration_version": 1,
        "database_migration_version": 1,
        "predecessor_index": None,
        "rollback_supported": False,
        "rollback_minimum_version": None,
        "rollback_data_compatible": False,
        "rollback_reason": "Alpha predecessor remains retained and data compatible.",
        "installer": inputs["installer"],
        "updater": inputs["updater"],
        "source_archive": inputs["source_archive"],
        "release_notes": inputs["release_notes"],
        "known_limitations": inputs["known_limitations"],
        "public_export_manifest": inputs["public_export_manifest"],
        "expires_at": inputs["expires_at"],
        "trust_public_key": trust_root["public"],
        "trust_key_id": trust_root["key_id"],
        "trust_key_fingerprint": trust_root["fingerprint"],
        "image_bundle_dir": inputs["bundles"],
        "sign_images": False,
        "signing_key": None,
        "output_root": output,
    }
    values.update(changes)
    return assembler.AssemblyRequest(**values)  # type: ignore[arg-type]


def _proof(signature: object) -> SignatureVerificationProof:
    descriptor = dict(signature)  # type: ignore[arg-type]
    return SignatureVerificationProof(
        subject_digest=str(descriptor["subjectDigest"]),
        bundle_digest=str(descriptor["bundle"]["digest"]),
        trust_mode=str(descriptor["trustMode"]),
        identity_primary=str(descriptor["publicKeyFingerprint"]),
        identity_secondary=str(descriptor["publicKeyId"]),
        verified_at=datetime.now(timezone.utc),
        transparency_log_mode=str(descriptor["transparencyLog"]),
    )


class _RegistryDeferredVerifier:
    """Test seam: real Cosign for the payload blob; registry image signature
    verification requires a live registry and is exercised by the operator run,
    not by offline fixtures."""

    def __init__(self, delegate: CosignVerifier) -> None:
        self._delegate = delegate

    def verify_blob(self, payload: bytes, signature: object) -> SignatureVerificationProof:
        return self._delegate.verify_blob(payload, signature)  # type: ignore[arg-type]

    def retain_bundle(self, source: Path, signature: object) -> Path:
        return self._delegate.retain_bundle(source, signature)  # type: ignore[arg-type]

    def verify_image(self, reference: str, signature: object) -> SignatureVerificationProof:
        descriptor = dict(signature)  # type: ignore[arg-type]
        assert reference.endswith(str(descriptor["subjectDigest"]))
        return _proof(signature)


def _policy(identity: PinnedPublicKeyIdentity, **changes: object) -> ReleaseVerificationPolicy:
    values: dict[str, object] = {
        "expected_channel": "alpha",
        "expected_target": "ubuntu-24.04-linux-amd64",
        "updater_version": "0.1.0",
        "accepted_signers": frozenset(),
        "accepted_public_keys": frozenset({identity}),
        "expected_trust_mode": "pinned-public-key",
        # Inline Cosign proofs are created after the policy is built; allow
        # for their creation time without moving hour-scale freshness bounds.
        "now": datetime.now(timezone.utc) + timedelta(seconds=60),
        "allow_candidate": True,
    }
    values.update(changes)
    return ReleaseVerificationPolicy(**values)  # type: ignore[arg-type]


def _verifier(
    trust_root: dict[str, object], bundle_root: Path, identity: PinnedPublicKeyIdentity
) -> _RegistryDeferredVerifier:
    return _RegistryDeferredVerifier(
        CosignVerifier(
            cosign=COSIGN,
            public_key=trust_root["public"],  # type: ignore[arg-type]
            identity=identity,
            bundle_root=bundle_root,
        )
    )


def _identity(trust_root: dict[str, object]) -> PinnedPublicKeyIdentity:
    return PinnedPublicKeyIdentity(str(trust_root["fingerprint"]), str(trust_root["key_id"]))


def _assemble_and_sign(
    tmp_path: Path, trust_root: dict[str, object]
) -> tuple[dict[str, object], Path]:
    inputs = _build_inputs(tmp_path)
    output = tmp_path / "release"
    result = assembler.assemble(_request(inputs, trust_root, output))
    candidate = Path(str(result["candidate"]))
    signed = assembler.sign(
        candidate=candidate,
        signing_key=trust_root["private"],  # type: ignore[arg-type]
        trust_public_key=trust_root["public"],  # type: ignore[arg-type]
        trust_key_id=str(trust_root["key_id"]),
        trust_key_fingerprint=str(trust_root["fingerprint"]),
    )
    return inputs, Path(str(signed["releaseIndex"]))


def test_assembled_candidate_is_schema_valid(tmp_path: Path, trust_root: dict[str, object]) -> None:
    inputs = _build_inputs(tmp_path)
    result = assembler.assemble(_request(inputs, trust_root, tmp_path / "release"))
    candidate = Path(str(result["candidate"]))
    index = load_release_index_file(candidate, require_signatures=False)
    schema = json.loads((ROOT / "schemas/release-index.v1.schema.json").read_text())
    jsonschema.Draft202012Validator.check_schema(schema)
    jsonschema.Draft202012Validator(schema).validate(json.loads(candidate.read_text()))
    signed = index.document["signed"]
    assert signed["release"]["qualification"] == "candidate"
    assert not index.document["signatures"]
    for image in signed["images"]:
        assert "@sha256:" in str(image["reference"])
        assert image["signature"]["transparencyLog"] == "not-uploaded-private-candidate"
        assert image["signature"]["publicKeyFingerprint"] == trust_root["fingerprint"]
    target = signed["targets"][0]
    assert list(target["artifactIds"]) == sorted(signed["artifacts"])
    quadlet_dir = candidate.parent / "quadlet" / str(target["targetId"])
    assert quadlet_dir.is_dir() and any(quadlet_dir.iterdir())
    compose = (candidate.parent / "compose.release.yaml").read_text()
    assert ":latest" not in compose and compose.count("@sha256:") == 3


def test_sign_and_verify_roundtrip(tmp_path: Path, trust_root: dict[str, object]) -> None:
    inputs, index_path = _assemble_and_sign(tmp_path, trust_root)
    identity = _identity(trust_root)
    result = assembler.verify(
        index_path=index_path,
        request=_request(inputs, trust_root, tmp_path / "unused"),
        expected_channel="alpha",
        updater_version="0.1.0",
        expected_target=None,
        trust_public_key=trust_root["public"],  # type: ignore[arg-type]
        trust_key_id=str(trust_root["key_id"]),
        trust_key_fingerprint=str(trust_root["fingerprint"]),
        bundle_root=index_path.parent,
        verifier=_verifier(trust_root, index_path.parent, identity),
    )
    assert result["rederivation"] == "matched-recorded-inputs"
    assert len(result["verificationProofs"]) == len(IMAGES) + 1


def test_tampered_signed_field_refused(tmp_path: Path, trust_root: dict[str, object]) -> None:
    _, index_path = _assemble_and_sign(tmp_path, trust_root)
    document = json.loads(index_path.read_text())
    document["signed"]["release"]["version"] = "0.2.0-rc.2"
    with pytest.raises(ReleaseContractError, match="canonical signed payload"):
        validate_release_index(document)
    tampered_dir = tmp_path / "tampered"
    tampered_dir.mkdir(mode=0o700)
    tampered = tampered_dir / "release-index.json"
    tampered.write_text(json.dumps(document), encoding="utf-8")
    with pytest.raises(ReleaseContractError):
        load_release_index_file(tampered)


def test_wrong_key_refused(tmp_path: Path, trust_root: dict[str, object]) -> None:
    _, index_path = _assemble_and_sign(tmp_path, trust_root)
    subprocess.run(
        [str(COSIGN), "generate-key-pair", "--output-key-prefix", "other"],
        cwd=tmp_path,
        check=True,
        capture_output=True,
    )
    other_public = tmp_path / "other.pub"
    other_identity = PinnedPublicKeyIdentity(
        public_key_der_spki_fingerprint(other_public), "stateport-alpha-test-other"
    )
    index = load_release_index_file(index_path)
    with pytest.raises(ReleaseContractError, match="untrusted signer"):
        verify_release_index(
            index,
            policy=_policy(other_identity),
            verifier=_verifier(trust_root, index_path.parent, _identity(trust_root)),
        )
    wrong_key_verifier = CosignVerifier(
        cosign=COSIGN,
        public_key=other_public,
        identity=other_identity,
        bundle_root=index_path.parent,
    )
    with pytest.raises(CosignVerificationError):
        wrong_key_verifier.verify_blob(index.signed_bytes, index.document["signatures"][0])


def test_floating_tag_refused(tmp_path: Path, trust_root: dict[str, object]) -> None:
    inputs = _build_inputs(tmp_path)
    manifest_path = Path(str(inputs["evidence"])) / "stateport-web.evidence.json"
    manifest = json.loads(manifest_path.read_text())
    manifest["imageReference"] = "127.0.0.1:5000/stateport-alpha/stateport-web:0.2.0-alpha.1"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    with pytest.raises(assembler.AssemblyError, match="reference"):
        assembler.assemble(_request(inputs, trust_root, tmp_path / "release"))
    inputs = _build_inputs(tmp_path / "second")
    with pytest.raises(assembler.AssemblyError, match="digest-bound"):
        assembler.assemble(
            _request(
                inputs,
                trust_root,
                tmp_path / "second" / "release",
                image_repository="ghcr.io/stateport/stateport-alpha:latest",
            )
        )


def test_missing_evidence_refused(tmp_path: Path, trust_root: dict[str, object]) -> None:
    inputs = _build_inputs(tmp_path)
    (Path(str(inputs["evidence"])) / "stateport-worker.evidence.json").unlink()
    with pytest.raises(assembler.AssemblyError, match="evidence is missing"):
        assembler.assemble(_request(inputs, trust_root, tmp_path / "release"))

    inputs = _build_inputs(tmp_path / "second")
    (Path(str(inputs["evidence"])) / "stateport-api.healthcheck.json").unlink()
    with pytest.raises(assembler.AssemblyError, match="health probe evidence is missing"):
        assembler.assemble(_request(inputs, trust_root, tmp_path / "second" / "release"))

    inputs = _build_inputs(tmp_path / "third")
    drifted = Path(str(inputs["evidence"])) / "stateport-web.cdx.json"
    drifted.write_text('{"tampered": true}\n', encoding="utf-8")
    with pytest.raises(assembler.AssemblyError, match="drifted"):
        assembler.assemble(_request(inputs, trust_root, tmp_path / "third" / "release"))


def test_unexecuted_health_probe_refused(tmp_path: Path, trust_root: dict[str, object]) -> None:
    inputs = _build_inputs(tmp_path)
    probe_path = Path(str(inputs["evidence"])) / "stateport-api.healthcheck.json"
    probe_path.write_text(
        json.dumps(
            {
                "formatVersion": "stateport.release-image-healthcheck/v1",
                "imageId": "stateport-api",
                "probeObservation": {"executed": False, "exitCode": 127},
            }
        )
        + "\n",
        encoding="utf-8",
    )
    with pytest.raises(assembler.AssemblyError, match="did not verifiably execute"):
        assembler.assemble(_request(inputs, trust_root, tmp_path / "release"))


def test_der_spki_fingerprint_is_distinct_and_enforced(
    tmp_path: Path, trust_root: dict[str, object]
) -> None:
    public = Path(str(trust_root["public"]))
    der_fingerprint = public_key_der_spki_fingerprint(public)
    pem_fingerprint = sha256_file(public)
    assert der_fingerprint != pem_fingerprint
    inputs = _build_inputs(tmp_path)
    with pytest.raises(assembler.AssemblyError, match="DER SubjectPublicKeyInfo"):
        assembler.assemble(
            _request(
                inputs,
                trust_root,
                tmp_path / "release",
                trust_key_fingerprint=pem_fingerprint,
            )
        )
    result = assembler.assemble(
        _request(
            inputs,
            trust_root,
            tmp_path / "release-der",
            trust_key_fingerprint=der_fingerprint,
        )
    )
    assert result["signedPayloadDigest"].startswith("sha256:")


def test_canonical_bytes_are_stable_and_newline_free(
    tmp_path: Path, trust_root: dict[str, object]
) -> None:
    first_inputs = _build_inputs(tmp_path / "first")
    second_inputs = _build_inputs(tmp_path / "second")
    first = assembler.assemble(_request(first_inputs, trust_root, tmp_path / "first" / "release"))
    second = assembler.assemble(
        _request(second_inputs, trust_root, tmp_path / "second" / "release")
    )
    assert first["signedPayloadDigest"] == second["signedPayloadDigest"]
    index = load_release_index_file(Path(str(first["candidate"])), require_signatures=False)
    assert not index.signed_bytes.endswith(b"\n")
    assert index.signed_bytes == canonical_json_bytes(json.loads(index.signed_bytes))
    assert b": " not in index.signed_bytes


def test_source_mismatch_refused(tmp_path: Path, trust_root: dict[str, object]) -> None:
    inputs = _build_inputs(tmp_path)
    candidate = Path(str(inputs["candidate"]))
    provenance = yaml.safe_load(candidate.read_text())
    provenance["materialization"]["sourceCommit"] = "0" * 40
    candidate.write_text(yaml.safe_dump(provenance), encoding="utf-8")
    with pytest.raises(assembler.AssemblyError, match="candidate provenance"):
        assembler.assemble(_request(inputs, trust_root, tmp_path / "release"))


def test_published_qualification_refused(tmp_path: Path, trust_root: dict[str, object]) -> None:
    inputs = _build_inputs(tmp_path)
    with pytest.raises(assembler.AssemblyError, match="transparency-log"):
        assembler.assemble(
            _request(inputs, trust_root, tmp_path / "release", qualification="published")
        )


def test_image_signatures_without_registry_are_deferred_not_faked(
    tmp_path: Path, trust_root: dict[str, object]
) -> None:
    inputs = _build_inputs(tmp_path)
    with pytest.raises(assembler.AssemblyError, match="deferred-to-publication"):
        assembler.assemble(
            _request(inputs, trust_root, tmp_path / "release", image_bundle_dir=None)
        )
