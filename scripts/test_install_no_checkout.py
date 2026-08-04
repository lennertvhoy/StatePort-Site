from __future__ import annotations

from datetime import datetime, timedelta, timezone
from dataclasses import dataclass
import hashlib
import io
import json
from pathlib import Path
import shutil
import stat
import sys
from typing import Any, Mapping, Sequence
import zipfile

import pytest
import yaml


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "packages/release-contracts/src"))
sys.path.insert(0, str(ROOT / "packages/updater/src"))

from stateport_release import (  # noqa: E402
    ReleaseContractError,
    SignatureVerificationProof,
    canonical_digest,
    load_release_index_file,
    validate_install_receipt,
)
import stateport_updater.engine as updater_engine  # noqa: E402
import stateport_updater.installed as updater_installed  # noqa: E402
import stateport_updater.models as updater_models  # noqa: E402
import stateport_updater.store as updater_store  # noqa: E402
import stateport_updater.control_plane as updater_control_plane  # noqa: E402
import stateport_release  # noqa: E402
import assemble_release_index as assembler  # noqa: E402
import install_no_checkout as installer  # noqa: E402
from release_safe_io import sha256_file  # noqa: E402


pytestmark = pytest.mark.skipif(
    shutil.which("openssl") is None, reason="openssl is required to fingerprint the fixture key"
)

# Throwaway, test-only P-256 public key (the private half was deleted).  It is
# never release evidence and never signs anything: signature verification is
# exercised through the injected runner and verifier seams.
TEST_PUBLIC_KEY_PEM = (
    "-----BEGIN PUBLIC KEY-----\n"
    "MFkwEwYHKoZIzj0CAQYIKoZIzj0DAQcDQgAEnmFuNZUaTmFwa1oQGPi1vYD0u+yq\n"
    "aL3blYr9sdh1Rmfghm65WBwZ/sEXjt8TOqUlUotpoY7XWxaoYiQ1WnkgWA==\n"
    "-----END PUBLIC KEY-----\n"
)
KEY_ID = "stateport-alpha-test-2026-08"
COMMIT = "b" * 40
TREE = "c" * 40
PUBLIC_COMMIT = "d" * 40
PUBLIC_TREE = "e" * 40
IMAGES = ("stateport-web", "stateport-api", "stateport-worker", "stateport-execution-host")
# The execution host is a stable out-of-revision service: it is signed and pulled
# with the release but never installed as a revision Quadlet unit.
REVISION_SERVICES = ("stateport-web", "stateport-api", "stateport-worker")
HEALTH = {
    "stateport-web": (8080, "/health"),
    "stateport-api": (8790, "/readyz"),
    "stateport-worker": (8791, "/readyz"),
}
BUNDLE_MEDIA_TYPE = "application/vnd.dev.sigstore.bundle.v0.3+json"


def _timestamp(value: datetime) -> str:
    return value.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _service(
    service_id: str,
    volume_name: str,
    mount_path: str,
    control_contract: str = "none",
) -> dict[str, object]:
    port, path = HEALTH[service_id]
    # The signed contract requires every health port to be declared in ports;
    # loopback-only publishing keeps api and worker off the network while the
    # installer still observes them over 127.0.0.1.
    ports = [
        {
            "name": "http",
            "containerPort": port,
            "hostScope": "loopback",
            "allocation": "full-revision-digest-derived-collision-probed",
        }
    ]
    return {
        "serviceId": service_id,
        "imageId": service_id,
        "trustDomain": "control",
        "quadletOwner": "stateport-control",
        "revisionScoped": True,
        "runAsUser": 65532,
        "readOnlyRoot": True,
        "health": {"kind": "http", "containerPort": port, "path": path},
        "ports": ports,
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


def _minimal_wheel_bytes() -> bytes:
    """A real, minimal wheel zip with pip-parseable .dist-info metadata.

    The installer derives the staged pip filename from the wheel's own
    metadata (regression for the VM refusal ``venv_install_failed-17a40047``:
    a digest-decorated name is not a valid wheel filename), so fixtures that
    flow through ``_stage_wheel_for_pip`` must be genuine zips.
    """
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr(
            "stateport_updater-0.1.0.dist-info/METADATA",
            "Metadata-Version: 2.1\nName: stateport-updater\nVersion: 0.1.0\n",
        )
        archive.writestr(
            "stateport_updater-0.1.0.dist-info/WHEEL",
            "Wheel-Version: 1.0\nGenerator: test\nRoot-Is-Purelib: true\nTag: py3-none-any\n",
        )
    return buffer.getvalue()


def _build_inputs(tmp_path: Path, *, expires_at: str | None = None) -> dict[str, object]:
    """Fixture assembly inputs, in the style of scripts/test_assemble_release_index.py."""

    tmp_path.mkdir(mode=0o700, exist_ok=True)
    now = datetime.now(timezone.utc)
    built_at = _timestamp(now - timedelta(hours=2))
    observed_at = _timestamp(now - timedelta(hours=1))
    if expires_at is None:
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
        "installer": b"test-installer-no-checkout\n",
        "updater": _minimal_wheel_bytes(),
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
                            "probeObservation": {"executed": True, "exitCode": 0},
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
                                "stateport-product-data",
                                "/var/lib/stateport",
                                control_contract="narrow-unix-client",
                            ),
                            _service(
                                "stateport-api", "stateport-operations", "/workspace/.stateport"
                            ),
                            _service(
                                "stateport-worker", "stateport-operations", "/workspace/.stateport"
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
    trust: dict[str, object],
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
        "trust_public_key": trust["public"],
        "trust_key_id": KEY_ID,
        "trust_key_fingerprint": trust["fingerprint"],
        "image_bundle_dir": inputs["bundles"],
        "sign_images": False,
        "signing_key": None,
        "output_root": output,
    }
    values.update(changes)
    return assembler.AssemblyRequest(**values)  # type: ignore[arg-type]


class FakeRunner:
    """Single subprocess seam: exact argv rules, no podman/systemctl/cosign needed."""

    def __init__(
        self,
        *,
        cosign_returncode: int = 0,
        podman_version: str = "4.9.3",
        rootless: bool = True,
    ) -> None:
        self.cosign_returncode = cosign_returncode
        self.podman_version = podman_version
        self.rootless = rootless
        self.calls: list[tuple[str, ...]] = []
        self.volumes: set[str] = set()
        self.active_units: set[str] = set()
        self.enabled_units: set[str] = set()
        self.containers: set[str] = set()
        # Consumed one per `systemctl --user stop`: an int returncode or an
        # OSError instance models one mid-uninstall interruption.
        self.stop_failures: list[object] = []

    def run(self, argv: Sequence[str], *, timeout: int) -> installer.Completed:
        call = tuple(str(item) for item in argv)
        self.calls.append(call)
        if call == ("uname", "-m"):
            return installer.Completed(0, "x86_64\n", "")
        if call[0].endswith("cosign") or "cosign" in call[0]:
            return installer.Completed(self.cosign_returncode, "", "verification failed")
        if call[:2] == ("podman", "version"):
            return installer.Completed(0, self.podman_version + "\n", "")
        if call[:2] == ("podman", "info"):
            return installer.Completed(0, ("true" if self.rootless else "false") + "\n", "")
        if call[:3] == ("systemctl", "--user", "show"):
            return installer.Completed(0, "254\n", "")
        if call[:2] == ("podman", "pull"):
            if "@sha256:" not in call[-1]:
                return installer.Completed(1, "", "tag references are refused")
            return installer.Completed(0, "", "")
        if call[:3] == ("podman", "image", "inspect"):
            reference = call[-1]
            if "@sha256:" not in reference:
                return installer.Completed(1, "", "no such image")
            return installer.Completed(0, reference.rsplit("@", 1)[-1] + "\n", "")
        if call[:3] == ("podman", "volume", "exists"):
            return installer.Completed(0 if call[-1] in self.volumes else 1, "", "")
        if call[:3] == ("podman", "volume", "create"):
            self.volumes.add(call[-1])
            return installer.Completed(0, call[-1] + "\n", "")
        if call[:3] == ("podman", "volume", "rm"):
            if call[-1] in self.volumes:
                self.volumes.discard(call[-1])
                return installer.Completed(0, call[-1] + "\n", "")
            return installer.Completed(1, "", "no such volume")
        if call[:3] == ("podman", "container", "exists"):
            return installer.Completed(0 if call[-1] in self.containers else 1, "", "")
        if call[:3] == ("podman", "rm", "-f"):
            if call[-1] in self.containers:
                self.containers.discard(call[-1])
                return installer.Completed(0, call[-1] + "\n", "")
            return installer.Completed(1, "", "no such container")
        if call[:2] == ("podman", "inspect"):
            return installer.Completed(0, "healthy\n", "")
        if call[:3] == ("systemctl", "--user", "daemon-reload"):
            return installer.Completed(0, "", "")
        if call[:3] == ("systemctl", "--user", "start"):
            self.active_units.add(call[-1])
            return installer.Completed(0, "", "")
        if call[:3] == ("systemctl", "--user", "stop"):
            if self.stop_failures:
                failure = self.stop_failures.pop(0)
                if isinstance(failure, BaseException):
                    raise failure
                return installer.Completed(int(failure), "", "simulated stop failure")  # type: ignore[arg-type]
            self.active_units.discard(call[-1])
            return installer.Completed(0, "", "")
        if call[:3] == ("systemctl", "--user", "is-active"):
            if call[-1] in self.active_units:
                return installer.Completed(0, "active\n", "")
            return installer.Completed(3, "inactive\n", "")
        if call[:3] == ("systemctl", "--user", "is-enabled"):
            if call[-1] in self.enabled_units:
                return installer.Completed(0, "enabled\n", "")
            return installer.Completed(1, "disabled\n", "")
        if call[:3] == ("systemctl", "--user", "disable"):
            self.enabled_units.discard(call[-1])
            return installer.Completed(0, "", "")
        if call[0].endswith("/pip"):
            return installer.Completed(0, "Successfully installed stateport-updater\n", "")
        if call[0].endswith("/python"):
            return installer.Completed(0, "", "")
        raise AssertionError(f"unexpected subprocess call: {call}")


class FakeProbe:
    def __init__(self, facts: installer.HostFacts, occupied: list[int] | None = None) -> None:
        self._facts = facts
        self._occupied = occupied or []

    def gather(self) -> installer.HostFacts:
        return self._facts

    def occupied_ports(self) -> list[int]:
        return list(self._occupied)


def _facts(**changes: object) -> installer.HostFacts:
    values: dict[str, object] = {
        "os_id": "ubuntu",
        "version_id": "24.04",
        "architecture": "amd64",
        "cgroup_version": "v2",
        "podman_version": "4.9.3",
        "rootless": True,
        "quadlet": True,
    }
    values.update(changes)
    return installer.HostFacts(**values)  # type: ignore[arg-type]


class FakeFetcher:
    def __init__(self, healthy: bool = True, downloads: Mapping[str, bytes] | None = None) -> None:
        self.healthy = healthy
        self.downloads = dict(downloads or {})
        self.requests: list[str] = []

    def fetch(self, url: str, *, timeout: float, max_bytes: int) -> installer.FetchResult:
        self.requests.append(url)
        if url in self.downloads:
            return installer.FetchResult(200, self.downloads[url])
        if url.startswith("http://127.0.0.1:"):
            if not self.healthy:
                return installer.FetchResult(0, b"")
            body = json.dumps(
                {
                    "service": "stateport-web",
                    "signedPayloadDigest": "sha256:" + "0" * 64,
                    "status": "ok",
                }
            ).encode()
            return installer.FetchResult(200, body)
        raise AssertionError(f"unexpected fetch: {url}")


class FakeVerifier:
    """Mirrors the CosignVerifier proof contract without a registry or cosign."""

    def __init__(self, clock) -> None:
        self._clock = clock

    def _proof(self, signature: Mapping[str, Any]) -> SignatureVerificationProof:
        # The contract refuses proofs newer than policy.now, and the updater
        # engine truncates its policy time to whole seconds; mirror that
        # truncation so real-clock tests are not racy at second boundaries.
        verified_at = self._clock().astimezone(timezone.utc).replace(microsecond=0)
        return SignatureVerificationProof(
            subject_digest=str(signature["subjectDigest"]),
            bundle_digest=str(signature["bundle"]["digest"]),
            trust_mode=str(signature["trustMode"]),
            identity_primary=str(signature["publicKeyFingerprint"]),
            identity_secondary=str(signature["publicKeyId"]),
            verified_at=verified_at,
            transparency_log_mode=str(signature["transparencyLog"]),
        )

    def verify_blob(
        self, payload: bytes, signature: Mapping[str, Any]
    ) -> SignatureVerificationProof:
        observed = "sha256:" + hashlib.sha256(payload).hexdigest()
        if observed != signature["subjectDigest"]:
            raise ReleaseContractError("blob payload does not match the signed subject digest")
        return self._proof(signature)

    def verify_image(
        self, reference: str, signature: Mapping[str, Any]
    ) -> SignatureVerificationProof:
        if not reference.endswith(str(signature["subjectDigest"])):
            raise ReleaseContractError("image reference is not bound to the signed digest")
        return self._proof(signature)


def _modules(venv_dir: Path) -> installer.VerifiedModules:
    return installer.VerifiedModules(
        release=stateport_release,
        updater_engine=updater_engine,
        updater_installed=updater_installed,
        updater_models=updater_models,
        updater_store=updater_store,
    )


def _fake_venv_creator(venv_dir: Path) -> None:
    bin_dir = venv_dir / "bin"
    bin_dir.mkdir(parents=True, exist_ok=True)
    (bin_dir / "pip").touch()
    (bin_dir / "python").touch()
    (venv_dir / "pyvenv.cfg").write_text("home = /fake\n", encoding="utf-8")


@pytest.fixture
def trust(tmp_path: Path) -> dict[str, object]:
    public = tmp_path / "trust.pub"
    public.write_text(TEST_PUBLIC_KEY_PEM, encoding="utf-8")
    return {
        "public": public,
        "fingerprint": installer.der_spki_fingerprint(TEST_PUBLIC_KEY_PEM.encode("ascii")),
        "key_id": KEY_ID,
    }


@dataclass(frozen=True)
class Fixture:
    inputs: dict[str, object]
    index_path: Path
    bundle_root: Path
    artifact_paths: dict[str, Path]
    trust: dict[str, object]


def _signed_index(
    tmp_path: Path, trust: dict[str, object], *, expires_at: str | None = None
) -> Fixture:
    """Assemble a fixture index and bind a synthetic pinned-key signature.

    The signature descriptor is real in structure but its bundle is a fixture
    placeholder: cryptographic verification is exercised through the runner
    (bootstrap cosign) and FakeVerifier (contract) seams, never claimed here.
    """

    inputs = _build_inputs(tmp_path, expires_at=expires_at)
    output = tmp_path / "release"
    result = assembler.assemble(_request(inputs, trust, output))
    candidate = Path(str(result["candidate"]))
    unsigned = load_release_index_file(candidate, require_signatures=False)
    bundle_root = Path(str(inputs["bundles"]))
    index_bundle = bundle_root / "release-index.sigstore.json"
    index_bundle.write_text(
        json.dumps(
            {
                "mediaType": BUNDLE_MEDIA_TYPE,
                "verificationMaterial": {"publicKey": {"hint": "aW5kZXg="}},
                "messageSignature": {
                    "messageDigest": {"algorithm": "SHA2_256", "digest": "aW5kZXg="},
                    "signature": "aW5kZXg=",
                },
            }
        )
        + "\n",
        encoding="utf-8",
    )
    document = json.loads(candidate.read_text(encoding="utf-8"))
    document["signatures"] = [
        {
            "scheme": "cosign-v3-bundle",
            "subjectDigest": unsigned.signed_digest,
            "bundle": {
                "uri": "operator://release/release-index.sigstore.json",
                "digest": sha256_file(index_bundle),
                "size": index_bundle.stat().st_size,
                "mediaType": "application/vnd.sigstore.bundle.v0.3+json",
            },
            "trustMode": "pinned-public-key",
            "publicKeyFingerprint": str(trust["fingerprint"]),
            "publicKeyFingerprintAlgorithm": "sha256-canonical-der-spki",
            "publicKeyId": KEY_ID,
            "transparencyLog": "not-uploaded-private-candidate",
        }
    ]
    index_path = tmp_path / "release-index.json"
    index_path.write_text(json.dumps(document) + "\n", encoding="utf-8")
    artifact_paths = {
        "installer": Path(str(inputs["installer"])),
        "updater": Path(str(inputs["updater"])),
        "sourceArchive": Path(str(inputs["source_archive"])),
        "releaseNotes": Path(str(inputs["release_notes"])),
        "knownLimitations": Path(str(inputs["known_limitations"])),
        "compose": output / "compose.release.yaml",
    }
    return Fixture(inputs, index_path, bundle_root, artifact_paths, trust)


def _config(fixture: Fixture, tmp_path: Path, **changes: object) -> installer.InstallConfig:
    values: dict[str, object] = {
        "release_index": str(fixture.index_path),
        "bundle_root": fixture.bundle_root,
        "trust_public_key": fixture.trust["public"],
        "trust_key_id": KEY_ID,
        "trust_key_fingerprint": fixture.trust["fingerprint"],
        "updater_wheel": str(fixture.artifact_paths["updater"]),
        "channel": "alpha",
        "cosign": Path("/usr/bin/cosign-fixture"),
        "state_root": tmp_path / "state",
        "live_quadlet_root": tmp_path / "quadlets",
        "actor_id": "local-owner-test",
        "installer_path": fixture.artifact_paths["installer"],
        "compose": str(fixture.artifact_paths["compose"]),
        "source_archive": str(fixture.artifact_paths["sourceArchive"]),
        "release_notes": str(fixture.artifact_paths["releaseNotes"]),
        "known_limitations": str(fixture.artifact_paths["knownLimitations"]),
        "assume_yes": True,
        "health_timeout_seconds": 30.0,
        "health_poll_seconds": 0.01,
    }
    values.update(changes)
    return installer.InstallConfig(**values)  # type: ignore[arg-type]


@pytest.fixture
def cosign_executable(tmp_path: Path) -> Path:
    path = tmp_path / "cosign"
    path.write_bytes(b"#!/bin/false\n")
    return path


def _run_install(
    config: installer.InstallConfig,
    *,
    runner: FakeRunner,
    probe: FakeProbe,
    fetcher: FakeFetcher,
    confirmer=lambda summary: True,
) -> installer.InstallOutcome:
    clock = lambda: datetime.now(timezone.utc)  # noqa: E731
    return installer.install(
        config,
        runner=runner,
        probe=probe,
        fetcher=fetcher,
        module_loader=_modules,
        verifier_factory=lambda modules: FakeVerifier(clock),
        clock=clock,
        confirmer=confirmer,
        venv_creator=_fake_venv_creator,
    )


def _happy(
    tmp_path: Path, trust: dict[str, object], cosign_executable: Path, **probe_changes: object
) -> tuple[installer.InstallOutcome, FakeRunner, Fixture, installer.InstallConfig]:
    fixture = _signed_index(tmp_path / "fixture", trust)
    runner = FakeRunner()
    probe = FakeProbe(_facts(**probe_changes), occupied=[])
    fetcher = FakeFetcher()
    config = _config(fixture, tmp_path, cosign=cosign_executable)
    outcome = _run_install(config, runner=runner, probe=probe, fetcher=fetcher)
    return outcome, runner, fixture, config


def test_happy_path_installs_and_receipts(
    tmp_path: Path, trust: dict[str, object], cosign_executable: Path
) -> None:
    outcome, runner, fixture, config = _happy(tmp_path, trust, cosign_executable)
    assert outcome.status == "succeeded", outcome.message
    assert outcome.local_url is not None and outcome.local_url.startswith("http://127.0.0.1:")
    assert outcome.receipt_path is not None and outcome.receipt_path.is_file()

    receipt = json.loads(outcome.receipt_path.read_text(encoding="utf-8"))
    validated = validate_install_receipt(receipt)
    assert validated.document["result"] == "succeeded"
    assert validated.document["operation"] == "install"
    assert validated.document["runtime"]["healthy"] is True
    assert validated.document["host"]["architecture"] == "amd64"
    assert validated.document["host"]["podmanVersion"] == "4.9.3"

    index = load_release_index_file(fixture.index_path)
    signed = index.document["signed"]
    assert validated.document["releaseIndexDigest"] == index.index_digest
    assert validated.document["runtime"]["signedPayloadDigest"] == index.signed_digest
    assert validated.document["installer"]["digest"] == signed["artifacts"]["installer"]["digest"]
    assert (
        validated.document["target"]["targetDigest"]
        == validated.document["runtime"]["targetDigest"]
    )
    assert len(validated.document["verification"]["artifacts"]) == 7
    assert len(validated.document["verification"]["signers"]) == len(IMAGES) + 1
    assert validated.document["authority"]["kind"] == "installer-directive"
    assert validated.document["dataDisposition"] == "created"

    # Loopback-only publishing; accepted units are token-free and not boot-enabled.
    live_units = sorted(config.live_quadlet_root.iterdir())
    assert live_units, "no accepted units were installed"
    container_units = [path for path in live_units if path.suffix == ".container"]
    assert len(container_units) == len(REVISION_SERVICES)
    for path in live_units:
        text = path.read_text(encoding="utf-8")
        assert "@@STATEPORT_" not in text
        assert "[Install]" not in text and "WantedBy=" not in text
        if "PublishPort=" in text:
            assert "PublishPort=127.0.0.1:" in text

    # Genesis volumes were created exactly once per volume key.
    assert len(runner.volumes) == 2 * 3  # 3 data volumes + 3 snapshot copies

    # Exact digest-pinned pulls and a hash-locked, index-less wheel install.
    pulls = [call for call in runner.calls if call[:2] == ("podman", "pull")]
    assert len(pulls) == len(IMAGES)
    for call in pulls:
        assert "@sha256:" in call[-1]
    pip_calls = [call for call in runner.calls if call[0].endswith("/pip")]
    assert pip_calls and "--no-index" in pip_calls[0] and "--no-deps" in pip_calls[0]
    cosign_calls = [call for call in runner.calls if "verify-blob" in call]
    assert cosign_calls and "--insecure-ignore-tlog" in cosign_calls[0]

    # Updater genesis: durable trust root, status, admission, and authority.
    status = json.loads((config.state_root / "updater" / "status.json").read_text())
    assert status["phase"] == "idle" and status["sequence"] == 0
    assert status["current"]["releaseId"] == signed["release"]["releaseId"]
    assert status["current"]["signedPayloadDigest"] == index.signed_digest
    releases = list((config.state_root / "updater" / "releases").glob("*.release-index.json"))
    assert len(releases) == 1

    trust_dir = config.state_root / "updater" / "trust"
    pem_path = trust_dir / f"{KEY_ID}.pem"
    assert pem_path.read_bytes() == (config.trust_public_key).read_bytes()
    trust_root = json.loads((trust_dir / "trust-root.json").read_text())
    assert trust_root["schema"] == "stateport.internal-update-trust-root/v1"
    assert trust_root["mode"] == "pinned-public-key"
    assert trust_root["keyId"] == KEY_ID
    assert trust_root["publicKeyFingerprint"] == config.trust_key_fingerprint
    assert trust_root["publicKeyFingerprintAlgorithm"] == "sha256-canonical-der-spki"
    assert trust_root["channel"] == "alpha"
    assert trust_root["targetId"] == installer.EXPECTED_TARGET
    assert trust_root["publicKeyFileDigest"] == installer._sha256_digest(pem_path.read_bytes())
    trust_body = {
        key: value
        for key, value in trust_root.items()
        if key not in {"trustRootId", "trustRootDigest"}
    }
    assert canonical_digest(trust_body) == trust_root["trustRootDigest"]
    assert trust_root["trustRootId"] == (
        f"update_trust_root_{trust_root['trustRootDigest'].removeprefix('sha256:')[:32]}"
    )

    # Real typed pinned-key admission and installed-authority identity; the
    # deferred genesis boundary record must not be written anymore.
    admissions = list((config.state_root / "updater" / "release-admissions").glob("*.json"))
    assert len(admissions) == 1
    admission = json.loads(admissions[0].read_text())
    assert admission["kind"] == "installed-initialize"
    assert admission["trustMode"] == "pinned-public-key"
    assert admission["releaseIndexDigest"] == index.index_digest
    assert admission["verifiedSigners"] == [
        {
            "mode": "pinned-public-key",
            "keyId": KEY_ID,
            "publicKeyDigest": config.trust_key_fingerprint,
        }
    ]
    identities = list(
        (config.state_root / "updater" / "installed-authority" / "identity").glob("*.json")
    )
    assert len(identities) == 1
    identity = json.loads(identities[0].read_text())
    assert identity["releaseId"] == signed["release"]["releaseId"]
    assert identity["releaseIndexDigest"] == index.index_digest
    assert identity["installerDigest"] == signed["artifacts"]["installer"]["digest"]
    assert identity["installerOrigin"] == installer.INSTALLER_ORIGIN
    assert identity["installerVersion"] == installer.INSTALLER_VERSION
    assert identity["actorId"] == "local-owner-test"
    assert not (config.state_root / "updater" / "genesis-boundary.json").exists()

    install_trust = json.loads((trust_dir / "install-trust.json").read_text())
    assert install_trust["schema"] == "stateport.internal-install-trust/v1"
    assert install_trust["trustRootDigest"] == trust_root["trustRootDigest"]
    assert install_trust["keyId"] == KEY_ID
    assert install_trust["publicKeyFingerprint"] == config.trust_key_fingerprint
    assert install_trust["admissionDigest"] == admission["admissionDigest"]
    assert install_trust["installedIdentityDigest"] == identity["identityDigest"]

    # The installed updater entry point binds the control-plane seam exactly.
    wrapper_path = config.state_root / "bin" / "stateport-update"
    assert wrapper_path.is_file() and not wrapper_path.is_symlink()
    assert stat.S_IMODE(wrapper_path.stat().st_mode) & 0o777 == 0o755
    wrapper_text = wrapper_path.read_text(encoding="utf-8")
    assert wrapper_text.startswith("#!/bin/sh\n")
    assert (
        "export STATEPORT_UPDATER_CONTROL_PLANE=stateport_updater.control_plane:build\n"
        in wrapper_text
    )
    assert f"export STATEPORT_COSIGN={config.cosign}\n" in wrapper_text
    assert "STATEPORT_UPDATER_BUNDLE_ROOT" not in wrapper_text
    assert f"export STATEPORT_QUADLET_ROOT={config.live_quadlet_root}\n" in wrapper_text
    assert wrapper_text.endswith(
        f"exec {config.state_root}/updater-venv/bin/python -m stateport_updater "
        f'--state-root {config.state_root}/updater "$@"\n'
    )

    # Runtime identity evidence is captured from the services, not claimed.
    evidence = json.loads((config.state_root / "runtime-identity-evidence.json").read_text())
    assert {item["serviceId"] for item in evidence["evidence"]} == set(REVISION_SERVICES)
    for item in evidence["evidence"]:
        assert item["source"] == "http-health"
        assert item["url"].startswith("http://127.0.0.1:")


def test_wrapper_survives_an_exact_reinstall(
    tmp_path: Path, trust: dict[str, object], cosign_executable: Path
) -> None:
    outcome, _runner, fixture, config = _happy(tmp_path, trust, cosign_executable)
    assert outcome.status == "succeeded", outcome.message
    wrapper_path = config.state_root / "bin" / "stateport-update"
    before = wrapper_path.read_bytes()

    rerun = _run_install(
        config,
        runner=FakeRunner(),
        probe=FakeProbe(_facts(), occupied=[]),
        fetcher=FakeFetcher(),
    )
    assert rerun.status == "succeeded", rerun.message
    assert wrapper_path.read_bytes() == before


def test_wrapper_conflict_refuses_closed(
    tmp_path: Path, trust: dict[str, object], cosign_executable: Path
) -> None:
    outcome, _runner, fixture, config = _happy(tmp_path, trust, cosign_executable)
    assert outcome.status == "succeeded", outcome.message
    wrapper_path = config.state_root / "bin" / "stateport-update"
    wrapper_path.write_text("#!/bin/sh\n# foreign content\n", encoding="utf-8")

    rerun = _run_install(
        config,
        runner=FakeRunner(),
        probe=FakeProbe(_facts(), occupied=[]),
        fetcher=FakeFetcher(),
    )
    assert rerun.status == "refused"
    assert rerun.code == "updater_wrapper_conflict"


def test_installed_control_plane_builds_from_the_installer_trust_root(
    tmp_path: Path,
    trust: dict[str, object],
    cosign_executable: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    outcome, _runner, fixture, config = _happy(tmp_path, trust, cosign_executable)
    assert outcome.status == "succeeded", outcome.message
    monkeypatch.setenv("STATEPORT_COSIGN", str(config.cosign))
    monkeypatch.delenv("STATEPORT_UPDATER_BUNDLE_ROOT", raising=False)
    monkeypatch.setenv("STATEPORT_QUADLET_ROOT", str(config.live_quadlet_root))

    # The installer retains the genesis index bundle in the durable
    # content-addressed root, so the installed control plane needs no
    # staging-directory environment override.
    bundle_bytes = (fixture.bundle_root / "release-index.sigstore.json").read_bytes()
    retained = (
        config.state_root
        / "updater"
        / "bundles"
        / hashlib.sha256(bundle_bytes).hexdigest()
        / "release-index.sigstore.json"
    )
    assert retained.is_file() and not retained.is_symlink()
    assert retained.read_bytes() == bundle_bytes
    assert retained.stat().st_mode & 0o777 == 0o600

    binding = updater_control_plane.build(config.state_root / "updater")

    policy = binding.verification_policy
    assert policy.expected_channel == "alpha"
    assert policy.expected_target == installer.EXPECTED_TARGET
    assert policy.expected_trust_mode == "pinned-public-key"
    assert {identity.key_id for identity in policy.accepted_public_keys} == {KEY_ID}
    assert {identity.public_key_fingerprint for identity in policy.accepted_public_keys} == {
        config.trust_key_fingerprint
    }
    assert binding.host.quadlet_root == config.live_quadlet_root


def test_signature_tamper_refused_before_cosign(
    tmp_path: Path, trust: dict[str, object], cosign_executable: Path
) -> None:
    fixture = _signed_index(tmp_path / "fixture", trust)
    document = json.loads(fixture.index_path.read_text(encoding="utf-8"))
    document["signed"]["release"]["version"] = "0.2.0-rc.2"
    tampered = tmp_path / "tampered-index.json"
    tampered.write_text(json.dumps(document) + "\n", encoding="utf-8")
    runner = FakeRunner()
    outcome = _run_install(
        _config(fixture, tmp_path, release_index=str(tampered), cosign=cosign_executable),
        runner=runner,
        probe=FakeProbe(_facts()),
        fetcher=FakeFetcher(),
    )
    assert outcome.status == "refused"
    assert outcome.code == "signature_payload_mismatch"
    # The tamper is caught by the stdlib digest binding before any trust decision.
    assert not [call for call in runner.calls if call[0].endswith("/pip")]


def test_cosign_verification_failure_refused(
    tmp_path: Path, trust: dict[str, object], cosign_executable: Path
) -> None:
    fixture = _signed_index(tmp_path / "fixture", trust)
    runner = FakeRunner(cosign_returncode=1)
    outcome = _run_install(
        _config(fixture, tmp_path, cosign=cosign_executable),
        runner=runner,
        probe=FakeProbe(_facts()),
        fetcher=FakeFetcher(),
    )
    assert outcome.status == "refused"
    assert outcome.code == "signature_verification_failed"
    assert not [call for call in runner.calls if call[0].endswith("/pip")]


def test_missing_cosign_refused(tmp_path: Path, trust: dict[str, object]) -> None:
    fixture = _signed_index(tmp_path / "fixture", trust)
    outcome = _run_install(
        _config(fixture, tmp_path, cosign=tmp_path / "no-such-cosign"),
        runner=FakeRunner(),
        probe=FakeProbe(_facts()),
        fetcher=FakeFetcher(),
    )
    assert outcome.status == "refused"
    assert outcome.code == "cosign_missing"


def test_wrong_architecture_refused(
    tmp_path: Path, trust: dict[str, object], cosign_executable: Path
) -> None:
    outcome, _, _, _ = _happy(tmp_path, trust, cosign_executable, architecture="arm64")
    assert outcome.status == "refused"
    assert outcome.code == "host_architecture_mismatch"


def test_wrong_os_baseline_refused(
    tmp_path: Path, trust: dict[str, object], cosign_executable: Path
) -> None:
    outcome, _, _, _ = _happy(tmp_path, trust, cosign_executable, os_id="debian", version_id="12")
    assert outcome.status == "refused"
    assert outcome.code == "host_os_mismatch"


def test_expired_index_refused(
    tmp_path: Path, trust: dict[str, object], cosign_executable: Path
) -> None:
    expired = _timestamp(datetime.now(timezone.utc) - timedelta(days=1))
    fixture = _signed_index(tmp_path / "fixture", trust, expires_at=expired)
    outcome = _run_install(
        _config(fixture, tmp_path, cosign=cosign_executable),
        runner=FakeRunner(),
        probe=FakeProbe(_facts()),
        fetcher=FakeFetcher(),
    )
    assert outcome.status == "refused"
    assert outcome.code == "index_expired"


def test_channel_mismatch_refused(
    tmp_path: Path, trust: dict[str, object], cosign_executable: Path
) -> None:
    fixture = _signed_index(tmp_path / "fixture", trust)
    outcome = _run_install(
        _config(fixture, tmp_path, channel="stable", cosign=cosign_executable),
        runner=FakeRunner(),
        probe=FakeProbe(_facts()),
        fetcher=FakeFetcher(),
    )
    assert outcome.status == "refused"
    assert outcome.code == "channel_mismatch"


def test_tag_reference_refused(
    tmp_path: Path, trust: dict[str, object], cosign_executable: Path
) -> None:
    fixture = _signed_index(tmp_path / "fixture", trust)
    document = json.loads(fixture.index_path.read_text(encoding="utf-8"))
    document["signed"]["images"][0]["reference"] = (
        "ghcr.io/stateport/stateport-alpha/stateport-web:latest"
    )
    # Rebind the payload digest so only the mutable-tag reference is dishonest.
    signed_bytes = json.dumps(
        document["signed"], ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode()
    document["signatures"][0]["subjectDigest"] = (
        "sha256:" + hashlib.sha256(signed_bytes).hexdigest()
    )
    tagged = tmp_path / "tagged-index.json"
    tagged.write_text(json.dumps(document) + "\n", encoding="utf-8")
    outcome = _run_install(
        _config(fixture, tmp_path, release_index=str(tagged), cosign=cosign_executable),
        runner=FakeRunner(),
        probe=FakeProbe(_facts()),
        fetcher=FakeFetcher(),
    )
    assert outcome.status == "refused"
    assert outcome.code in {
        "signature_verification_failed",
        "release_verification_failed",
        "image_reference_refused",
        "index_verification_failed",
    }


def test_wheel_digest_mismatch_refused_before_pip(
    tmp_path: Path, trust: dict[str, object], cosign_executable: Path
) -> None:
    fixture = _signed_index(tmp_path / "fixture", trust)
    fixture.artifact_paths["updater"].write_bytes(b"tampered-wheel-bytes\n")
    runner = FakeRunner()
    outcome = _run_install(
        _config(fixture, tmp_path, cosign=cosign_executable),
        runner=runner,
        probe=FakeProbe(_facts()),
        fetcher=FakeFetcher(),
    )
    assert outcome.status == "refused"
    assert outcome.code == "wheel_digest_mismatch"
    assert not [call for call in runner.calls if call[0].endswith("/pip")]


def test_extensionless_bundle_wheel_is_staged_with_whl_suffix_for_pip(
    tmp_path: Path, trust: dict[str, object], cosign_executable: Path
) -> None:
    # Regression for the VM refusals venv_install_failed-56add791 and
    # venv_install_failed-17a40047: the shipped bundle names the wheel
    # artifact extensionless (artifacts/updater), and pip refuses both a
    # non-.whl path and a decorated name that is not a valid wheel filename
    # (the digest contains a colon and the name lacks the tag components).
    outcome, runner, fixture, config = _happy(tmp_path, trust, cosign_executable)
    assert outcome.status == "succeeded", outcome.message
    wheel = fixture.artifact_paths["updater"]
    assert wheel.suffix != ".whl"  # the fixture mirrors the real bundle layout
    pip_calls = [call for call in runner.calls if call[0].endswith("/pip")]
    assert pip_calls, "the updater wheel must be installed through pip"
    for call in pip_calls:
        target = Path(call[-1])
        # The exact PEP 427 name pip parses without error: no colon, the
        # wheel's own dist-info base, and the py-abi-platform tag triplet.
        assert target.name == "stateport_updater-0.1.0-py3-none-any.whl"
        assert target.is_file()
        assert target.read_bytes() == wheel.read_bytes()


def test_stage_wheel_for_pip_passes_whl_path_through(tmp_path: Path) -> None:
    wheel = tmp_path / "stateport_updater-0.1.0-py3-none-any.whl"
    wheel.write_bytes(_minimal_wheel_bytes())
    staged = installer._stage_wheel_for_pip(wheel, tmp_path / "venv")
    assert staged == wheel


def test_stage_wheel_for_pip_derives_pep427_name_from_wheel_metadata(
    tmp_path: Path,
) -> None:
    wheel = tmp_path / "updater"  # extensionless, like the shipped bundle
    wheel.write_bytes(_minimal_wheel_bytes())
    staged = installer._stage_wheel_for_pip(wheel, tmp_path / "venv")
    assert staged.name == "stateport_updater-0.1.0-py3-none-any.whl"
    assert staged.read_bytes() == wheel.read_bytes()


def test_stage_wheel_for_pip_replaces_stale_staged_copy(tmp_path: Path) -> None:
    wheel = tmp_path / "updater"
    wheel.write_bytes(_minimal_wheel_bytes())
    venv_dir = tmp_path / "venv"
    staged = installer._stage_wheel_for_pip(wheel, venv_dir)
    staged.unlink()  # the staged file hardlinks the wheel; replace, not overwrite
    staged.write_bytes(b"stale-bytes-from-an-interrupted-run\n")
    restaged = installer._stage_wheel_for_pip(wheel, venv_dir)
    assert restaged == staged
    assert restaged.read_bytes() == wheel.read_bytes()


def test_stage_wheel_for_pip_refuses_unparseable_wheel(tmp_path: Path) -> None:
    wheel = tmp_path / "updater"
    wheel.write_bytes(b"not-a-zip-archive\n")
    with pytest.raises(installer.InstallerRefusal) as refusal:
        installer._stage_wheel_for_pip(wheel, tmp_path / "venv")
    assert refusal.value.code == "wheel_layout_invalid"


def test_stage_wheel_for_pip_hardlink_fallback_copy(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    wheel = tmp_path / "updater"
    wheel.write_bytes(_minimal_wheel_bytes())

    def _no_link(source: Path, target: Path) -> None:
        raise OSError("cross-device link")

    monkeypatch.setattr(installer.os, "link", _no_link)
    staged = installer._stage_wheel_for_pip(wheel, tmp_path / "venv")
    assert staged.suffix == ".whl"
    assert staged.read_bytes() == wheel.read_bytes()


def test_podman_version_floor_refused(
    tmp_path: Path, trust: dict[str, object], cosign_executable: Path
) -> None:
    fixture = _signed_index(tmp_path / "fixture", trust)
    outcome = _run_install(
        _config(fixture, tmp_path, cosign=cosign_executable),
        runner=FakeRunner(podman_version="4.0.0"),
        probe=FakeProbe(_facts(podman_version="4.0.0")),
        fetcher=FakeFetcher(),
    )
    assert outcome.status == "refused"
    assert outcome.code == "podman_version_floor"


def test_cgroup_v1_refused(
    tmp_path: Path, trust: dict[str, object], cosign_executable: Path
) -> None:
    outcome, _, _, _ = _happy(tmp_path, trust, cosign_executable, cgroup_version="v1")
    assert outcome.status == "refused"
    assert outcome.code == "cgroup_v2_missing"


def test_rootful_podman_refused(
    tmp_path: Path, trust: dict[str, object], cosign_executable: Path
) -> None:
    outcome, _, _, _ = _happy(tmp_path, trust, cosign_executable, rootless=False)
    assert outcome.status == "refused"
    assert outcome.code == "podman_not_rootless"


def _materialized_web_port(fixture: Fixture, occupied: list[dict[str, object]]) -> tuple[int, int]:
    """Contract-computed accepted web port for a given occupied inventory."""

    clock = datetime.now(timezone.utc)
    index = load_release_index_file(fixture.index_path)
    release = stateport_release
    policy = release.ReleaseVerificationPolicy(
        expected_channel="alpha",
        expected_target="ubuntu-24.04-linux-amd64",
        updater_version="0.1.0",
        accepted_signers=frozenset(),
        accepted_public_keys=frozenset(
            {release.PinnedPublicKeyIdentity(str(fixture.trust["fingerprint"]), KEY_ID)}
        ),
        expected_trust_mode="pinned-public-key",
        now=clock + timedelta(seconds=60),
        allow_candidate=True,
    )
    verified = release.verify_release_index(
        index, policy=policy, verifier=FakeVerifier(lambda: clock)
    )
    target = verified.target
    plan_digest = release.canonical_digest({"test": "port-probe"})
    backup = {
        "schema": "stateport.revision-validation-backup-receipt/v1",
        "operationPlanDigest": plan_digest,
        "releaseId": str(verified.index.release_id),
        "signedPayloadDigest": index.signed_digest,
        "targetId": str(target["targetId"]),
        "topologyDigest": str(target["topologyDigest"]),
        "backupReceiptDigest": release.canonical_digest({"test": "backup"}),
        "snapshotSetDigest": release.canonical_digest({"test": "snapshots"}),
        "volumeBindings": [
            {
                "volumeKey": f"{service['serviceId']}:{volume['name']}",
                "snapshotVolumeName": f"stateport-s{'ab' * 6}-{service['serviceId'][10:]}",
                "sourceDataGeneration": None,
                "readOnly": True,
            }
            for service in target["services"]
            for volume in service["writableVolumes"]
        ],
        "createdAt": _timestamp(clock),
        "consistencyMode": "quiesced",
        "consistencyEvidenceDigest": release.canonical_digest({"test": "evidence"}),
        "result": "succeeded",
    }
    backup["receiptDigest"] = release.revision_contract_digest(backup, digest_field="receiptDigest")
    empty = release.canonical_digest([])
    staged = release.materialize_verified_quadlet_bundle(
        verified,
        operation_plan_digest=plan_digest,
        host_identity_digest=release.canonical_digest({"test": "host"}),
        collision_inventory_digests={
            "current": empty,
            "predecessor": empty,
            "candidate": empty,
            "observedHost": release.canonical_digest(
                sorted(occupied, key=lambda item: item["port"])
            ),
        },
        occupied_port_inputs=occupied,
        proposed_at=_timestamp(clock),
        validation_backup_receipt=backup,
    )
    manifest = json.loads(
        staged[f"staged/{index.signed_digest.removeprefix('sha256:')}/materialization.json"]
    )
    proposal = json.loads(
        staged[
            f"staged/{index.signed_digest.removeprefix('sha256:')}/port-allocation.proposal.json"
        ]
    )
    port = int(manifest["ports"]["stateport-web:accepted:http"])
    attempts = {
        item["portName"]: item["probeAttempt"]
        for item in proposal["allocations"]
        if item["serviceId"] == "stateport-web" and item["profile"] == "accepted"
    }
    return port, int(attempts["http"])


def test_occupied_port_collision_probed_not_guessed(
    tmp_path: Path, trust: dict[str, object], cosign_executable: Path
) -> None:
    fixture = _signed_index(tmp_path / "fixture", trust)
    default_port, default_attempts = _materialized_web_port(fixture, [])
    assert default_attempts == 0
    occupied = [
        {
            "class": "observed-host",
            "port": default_port,
            "identityDigest": canonical_digest({"test": "foreign-listener"}),
        }
    ]
    probed_port, probed_attempts = _materialized_web_port(fixture, occupied)
    assert probed_port != default_port and probed_attempts > 0

    config = _config(fixture, tmp_path, cosign=cosign_executable)
    probe = FakeProbe(_facts(), occupied=[default_port])
    outcome = _run_install(config, runner=FakeRunner(), probe=probe, fetcher=FakeFetcher())
    assert outcome.status == "succeeded", outcome.message
    assert outcome.local_url == f"http://127.0.0.1:{probed_port}/"
    published_units = [
        path
        for path in config.live_quadlet_root.iterdir()
        if path.suffix == ".container" and "PublishPort" in path.read_text(encoding="utf-8")
    ]
    # All three services publish on loopback; the web unit must use the probed
    # port, never the colliding contract default.
    assert len(published_units) == 3
    web_unit = next(path for path in published_units if ":8080" in path.read_text(encoding="utf-8"))
    assert f"PublishPort=127.0.0.1:{probed_port}:8080" in web_unit.read_text(encoding="utf-8")
    assert f":{default_port}:" not in web_unit.read_text(encoding="utf-8")


def test_interrupted_install_rerun_converges(
    tmp_path: Path, trust: dict[str, object], cosign_executable: Path
) -> None:
    fixture = _signed_index(tmp_path / "fixture", trust)
    config = _config(fixture, tmp_path, cosign=cosign_executable, health_timeout_seconds=0.2)
    runner = FakeRunner()
    first = _run_install(
        config, runner=runner, probe=FakeProbe(_facts()), fetcher=FakeFetcher(healthy=False)
    )
    assert first.status == "refused"
    assert first.code == "health_timeout"
    # The interruption left a schema-conformant failure receipt, not torn state.
    receipts = sorted((config.state_root / "receipts").glob("install_receipt_*.json"))
    assert len(receipts) == 1
    failure = validate_install_receipt(json.loads(receipts[0].read_text(encoding="utf-8")))
    assert failure.document["result"] == "failed"
    assert failure.document["runtime"]["healthy"] is False

    second = _run_install(
        config, runner=runner, probe=FakeProbe(_facts()), fetcher=FakeFetcher(healthy=True)
    )
    assert second.status == "succeeded", second.message
    assert second.receipt_path is not None
    success = validate_install_receipt(json.loads(second.receipt_path.read_text(encoding="utf-8")))
    assert success.document["result"] == "succeeded"
    status = json.loads((config.state_root / "updater" / "status.json").read_text())
    assert status["sequence"] == 0 and status["phase"] == "idle"
    # One durable trust root, admission, and installed identity across the rerun.
    assert len(list((config.state_root / "updater" / "trust").glob("*.json"))) == 2
    assert len(list((config.state_root / "updater" / "release-admissions").glob("*.json"))) == 1
    assert (
        len(
            list(
                (config.state_root / "updater" / "installed-authority" / "identity").glob("*.json")
            )
        )
        == 1
    )
    assert not (config.state_root / "updater" / "genesis-boundary.json").exists()


def _remove_receipts(state_root: Path) -> None:
    for path in (state_root / "receipts").glob("install_receipt_*.json"):
        path.unlink()


def test_genesis_rerun_without_receipt_is_idempotent(
    tmp_path: Path, trust: dict[str, object], cosign_executable: Path
) -> None:
    outcome, runner, _fixture, config = _happy(tmp_path, trust, cosign_executable)
    assert outcome.status == "succeeded", outcome.message

    def durable_genesis_bytes() -> dict[str, bytes]:
        return {
            path.relative_to(config.state_root).as_posix(): path.read_bytes()
            for path in sorted((config.state_root / "updater").rglob("*"))
            if path.is_file()
        }

    before = durable_genesis_bytes()
    _remove_receipts(config.state_root)
    second = _run_install(config, runner=runner, probe=FakeProbe(_facts()), fetcher=FakeFetcher())
    assert second.status == "succeeded", second.message

    assert durable_genesis_bytes() == before
    assert len(list((config.state_root / "updater" / "release-admissions").glob("*.json"))) == 1
    assert (
        len(
            list(
                (config.state_root / "updater" / "installed-authority" / "identity").glob("*.json")
            )
        )
        == 1
    )


def test_conflicting_trust_key_bytes_refuse_rerun(
    tmp_path: Path, trust: dict[str, object], cosign_executable: Path
) -> None:
    outcome, runner, _fixture, config = _happy(tmp_path, trust, cosign_executable)
    assert outcome.status == "succeeded", outcome.message
    pem_path = config.state_root / "updater" / "trust" / f"{KEY_ID}.pem"
    pem_path.write_bytes(b"-----BEGIN PUBLIC KEY-----\ntampered\n-----END PUBLIC KEY-----\n")
    _remove_receipts(config.state_root)
    outcome = _run_install(config, runner=runner, probe=FakeProbe(_facts()), fetcher=FakeFetcher())
    assert outcome.status == "refused"
    assert outcome.code == "trust_root_conflict"


def test_conflicting_trust_root_record_refuses_rerun(
    tmp_path: Path, trust: dict[str, object], cosign_executable: Path
) -> None:
    outcome, runner, _fixture, config = _happy(tmp_path, trust, cosign_executable)
    assert outcome.status == "succeeded", outcome.message
    record_path = config.state_root / "updater" / "trust" / "trust-root.json"
    record = json.loads(record_path.read_text(encoding="utf-8"))
    record["channel"] = "stable"
    record_path.write_text(json.dumps(record) + "\n", encoding="utf-8")
    _remove_receipts(config.state_root)
    outcome = _run_install(config, runner=runner, probe=FakeProbe(_facts()), fetcher=FakeFetcher())
    assert outcome.status == "refused"
    assert outcome.code == "trust_root_conflict"


def test_stale_status_binding_other_release_refuses_genesis_conflict(
    tmp_path: Path, trust: dict[str, object], cosign_executable: Path
) -> None:
    outcome, runner, _fixture, config = _happy(tmp_path, trust, cosign_executable)
    assert outcome.status == "succeeded", outcome.message
    status_path = config.state_root / "updater" / "status.json"
    status = json.loads(status_path.read_text(encoding="utf-8"))
    status["current"] = {
        **status["current"],
        "releaseId": "stateport-alpha-9.9.9-rc.1",
        "version": "9.9.9-rc.1",
    }
    status["accepted"] = status["current"]
    status_path.write_text(json.dumps(status) + "\n", encoding="utf-8")
    _remove_receipts(config.state_root)
    outcome = _run_install(config, runner=runner, probe=FakeProbe(_facts()), fetcher=FakeFetcher())
    assert outcome.status == "refused"
    assert outcome.code == "updater_genesis_conflict"


def test_stale_genesis_boundary_record_is_left_untouched(
    tmp_path: Path, trust: dict[str, object], cosign_executable: Path
) -> None:
    outcome, runner, _fixture, config = _happy(tmp_path, trust, cosign_executable)
    assert outcome.status == "succeeded", outcome.message
    boundary_path = config.state_root / "updater" / "genesis-boundary.json"
    historic = {
        "schema": "stateport.install-genesis-boundary/v1",
        "code": "pinned_key_admission_contract_unsupported",
        "createdAt": "2026-08-01T00:00:00Z",
    }
    boundary_path.write_text(json.dumps(historic) + "\n", encoding="utf-8")
    boundary_path.chmod(0o600)
    _remove_receipts(config.state_root)
    second = _run_install(config, runner=runner, probe=FakeProbe(_facts()), fetcher=FakeFetcher())
    assert second.status == "succeeded", second.message
    assert json.loads(boundary_path.read_text(encoding="utf-8")) == historic


def test_completed_install_rerun_converges_without_duplicate_receipt(
    tmp_path: Path, trust: dict[str, object], cosign_executable: Path
) -> None:
    fixture = _signed_index(tmp_path / "fixture", trust)
    config = _config(fixture, tmp_path, cosign=cosign_executable)
    runner = FakeRunner()
    first = _run_install(config, runner=runner, probe=FakeProbe(_facts()), fetcher=FakeFetcher())
    assert first.status == "succeeded", first.message
    second = _run_install(config, runner=runner, probe=FakeProbe(_facts()), fetcher=FakeFetcher())
    assert second.status == "succeeded"
    assert second.converged is True
    assert second.code == "already_installed"
    assert second.local_url == first.local_url
    receipts = sorted((config.state_root / "receipts").glob("install_receipt_*.json"))
    assert len(receipts) == 1


def test_receipt_validates_against_schema(
    tmp_path: Path, trust: dict[str, object], cosign_executable: Path
) -> None:
    outcome, _, fixture, _ = _happy(tmp_path, trust, cosign_executable)
    assert outcome.status == "succeeded", outcome.message
    assert outcome.receipt_path is not None
    receipt = json.loads(outcome.receipt_path.read_text(encoding="utf-8"))
    validated = validate_install_receipt(receipt)
    assert validated.digest == receipt["receiptId"] or validated.document is not None
    index = load_release_index_file(fixture.index_path)
    assert receipt["releaseIndexDigest"] == index.index_digest
    assert receipt["installPlanDigest"].startswith("sha256:")
    assert (
        receipt["target"]["topologyDigest"]
        == index.document["signed"]["targets"][0]["topologyDigest"]
    )
    assert receipt["verification"]["signedIndex"]["status"] == "verified"
    assert all(entry["status"] == "verified" for entry in receipt["verification"]["images"])


def test_confirmation_refused_writes_durable_refusal(
    tmp_path: Path, trust: dict[str, object], cosign_executable: Path
) -> None:
    fixture = _signed_index(tmp_path / "fixture", trust)
    config = _config(fixture, tmp_path, cosign=cosign_executable, assume_yes=False)
    outcome = _run_install(
        config,
        runner=FakeRunner(),
        probe=FakeProbe(_facts()),
        fetcher=FakeFetcher(),
        confirmer=lambda summary: False,
    )
    assert outcome.status == "refused"
    assert outcome.code == "confirmation_refused"
    refusals = sorted((config.state_root / "refusals").glob("*.json"))
    assert len(refusals) == 1
    record = json.loads(refusals[0].read_text(encoding="utf-8"))
    assert record["code"] == "confirmation_refused"
    assert record["executed"] is False
    # Nothing was pulled or installed without confirmation.
    assert not config.live_quadlet_root.exists() or not any(config.live_quadlet_root.iterdir())


def test_https_index_requires_published_digest(
    tmp_path: Path, trust: dict[str, object], cosign_executable: Path
) -> None:
    fixture = _signed_index(tmp_path / "fixture", trust)
    url = "https://releases.stateport.invalid/alpha/release-index.json"
    outcome = _run_install(
        _config(fixture, tmp_path, release_index=url, cosign=cosign_executable),
        runner=FakeRunner(),
        probe=FakeProbe(_facts()),
        fetcher=FakeFetcher(),
    )
    assert outcome.status == "refused"
    assert outcome.code == "published_digest_missing"


def test_https_index_download_digest_mismatch_refused(
    tmp_path: Path, trust: dict[str, object], cosign_executable: Path
) -> None:
    fixture = _signed_index(tmp_path / "fixture", trust)
    url = "https://releases.stateport.invalid/alpha/release-index.json"
    body = fixture.index_path.read_bytes()
    outcome = _run_install(
        _config(
            fixture,
            tmp_path,
            release_index=url,
            release_index_sha256="0" * 64,
            cosign=cosign_executable,
        ),
        runner=FakeRunner(),
        probe=FakeProbe(_facts()),
        fetcher=FakeFetcher(downloads={url: body}),
    )
    assert outcome.status == "refused"
    assert outcome.code == "download_digest_mismatch"


def test_https_index_download_with_published_digest(
    tmp_path: Path, trust: dict[str, object], cosign_executable: Path
) -> None:
    fixture = _signed_index(tmp_path / "fixture", trust)
    url = "https://releases.stateport.invalid/alpha/release-index.json"
    body = fixture.index_path.read_bytes()
    outcome = _run_install(
        _config(
            fixture,
            tmp_path,
            release_index=url,
            release_index_sha256=hashlib.sha256(body).hexdigest(),
            cosign=cosign_executable,
        ),
        runner=FakeRunner(),
        probe=FakeProbe(_facts()),
        fetcher=FakeFetcher(downloads={url: body}),
    )
    assert outcome.status == "succeeded", outcome.message


def test_der_spki_fingerprint_matches_openssl_semantics() -> None:
    fingerprint = installer.der_spki_fingerprint(TEST_PUBLIC_KEY_PEM.encode("ascii"))
    from stateport_release import public_key_der_spki_fingerprint
    import tempfile

    with tempfile.NamedTemporaryFile("w", suffix=".pub", delete=False) as handle:
        handle.write(TEST_PUBLIC_KEY_PEM)
        path = Path(handle.name)
    assert fingerprint == public_key_der_spki_fingerprint(path)
    assert fingerprint.startswith("sha256:")


# ---------------------------------------------------------------------------
# uninstall / purge modes (recorded authority only, converge on partial state)
# ---------------------------------------------------------------------------


def _live_unit_names(config: installer.InstallConfig) -> list[str]:
    return sorted(
        path.name.removesuffix(".container")
        for path in config.live_quadlet_root.glob("*.container")
    )


def _live_container_names(config: installer.InstallConfig) -> list[str]:
    names: list[str] = []
    for path in sorted(config.live_quadlet_root.glob("*.container")):
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.startswith("ContainerName="):
                names.append(line.split("=", 1)[1])
    return sorted(names)


def _live_quadlet_files(config: installer.InstallConfig) -> list[str]:
    return sorted(path.name for path in config.live_quadlet_root.iterdir())


def _state_bytes(state_root: Path) -> dict[str, bytes]:
    return {
        path.relative_to(state_root).as_posix(): path.read_bytes()
        for path in sorted(state_root.rglob("*"))
        if path.is_file()
    }


def _install_trust(config: installer.InstallConfig) -> dict[str, object]:
    return json.loads(
        (config.state_root / "updater" / "trust" / "install-trust.json").read_text(encoding="utf-8")
    )


def _uninstall_config(
    config: installer.InstallConfig, **changes: object
) -> installer.UninstallConfig:
    values: dict[str, object] = {
        "state_root": config.state_root,
        "live_quadlet_root": config.live_quadlet_root,
        "actor_id": "local-owner-test",
        "purge": False,
        "confirm_purge": None,
    }
    values.update(changes)
    return installer.UninstallConfig(**values)  # type: ignore[arg-type]


def _run_uninstall(
    config: installer.UninstallConfig, *, runner: FakeRunner
) -> installer.InstallOutcome:
    clock = lambda: datetime.now(timezone.utc)  # noqa: E731
    return installer.uninstall(config, runner=runner, clock=clock)


def _uninstall_receipts(state_root: Path) -> list[Path]:
    return sorted((state_root / "receipts").glob("uninstall_receipt_*.json"))


def test_uninstall_happy_path_preserves_data(
    tmp_path: Path, trust: dict[str, object], cosign_executable: Path
) -> None:
    outcome, runner, _fixture, config = _happy(tmp_path, trust, cosign_executable)
    assert outcome.status == "succeeded", outcome.message
    units = _live_unit_names(config)
    containers = _live_container_names(config)
    quadlet_files = _live_quadlet_files(config)
    assert len(units) == len(REVISION_SERVICES) == len(containers)
    runner.containers.update(containers)
    preserved_volumes = set(runner.volumes)
    assert len(preserved_volumes) == 2 * len(REVISION_SERVICES)
    state_before = _state_bytes(config.state_root)
    runner.calls.clear()

    result = _run_uninstall(_uninstall_config(config), runner=runner)

    assert result.status == "succeeded", result.message
    assert result.code == "uninstalled"
    stops = [call for call in runner.calls if call[:3] == ("systemctl", "--user", "stop")]
    assert sorted(call[-1] for call in stops) == units
    reloads = [
        call for call in runner.calls if call[:3] == ("systemctl", "--user", "daemon-reload")
    ]
    assert len(reloads) == 1
    removals = [call for call in runner.calls if call[:3] == ("podman", "rm", "-f")]
    assert sorted(call[-1] for call in removals) == containers
    # Data preservation: not a single volume removal, state root untouched.
    assert not [call for call in runner.calls if call[:3] == ("podman", "volume", "rm")]
    assert runner.volumes == preserved_volumes
    assert not any(config.live_quadlet_root.iterdir())
    state_after = _state_bytes(config.state_root)
    added = set(state_after) - set(state_before)
    assert added and all(name.startswith("receipts/uninstall_receipt_") for name in added), added
    assert not (set(state_before) - set(state_after))
    assert not {
        name
        for name in state_before
        if name in state_after and state_after[name] != state_before[name]
    }

    assert result.receipt_path is not None
    receipt = json.loads(result.receipt_path.read_text(encoding="utf-8"))
    assert receipt["schema"] == "stateport.internal-install-uninstall-receipt/v1"
    assert receipt["action"] == "uninstall"
    assert receipt["actorId"] == "local-owner-test"
    assert receipt["result"] == "succeeded"
    assert (
        receipt["installation"]["signedPayloadDigest"]
        == _install_trust(config)["signedPayloadDigest"]
    )
    assert receipt["removed"]["unitsStopped"] == units
    assert receipt["removed"]["containers"] == containers
    assert receipt["removed"]["quadletFiles"] == quadlet_files
    assert receipt["removed"]["volumes"] == []
    assert receipt["removed"]["stateRootContents"] == []
    assert sorted(receipt["preserved"]["volumes"]) == sorted(preserved_volumes)
    assert str(config.state_root) in receipt["preserved"]["paths"]
    assert str(config.state_root / "updater-venv") in receipt["preserved"]["paths"]


def test_uninstall_without_installation_refused(tmp_path: Path) -> None:
    config = installer.UninstallConfig(
        state_root=tmp_path / "state",
        live_quadlet_root=tmp_path / "quadlets",
        actor_id="local-owner-test",
    )
    runner = FakeRunner()
    outcome = _run_uninstall(config, runner=runner)
    assert outcome.status == "refused"
    assert outcome.code == "no_installation_found"
    # Zero runner mutations and zero new state in a foreign directory.
    assert runner.calls == []
    assert not (tmp_path / "state").exists()


def test_uninstall_rerun_converges(
    tmp_path: Path, trust: dict[str, object], cosign_executable: Path
) -> None:
    outcome, runner, _fixture, config = _happy(tmp_path, trust, cosign_executable)
    assert outcome.status == "succeeded", outcome.message
    runner.containers.update(_live_container_names(config))
    first = _run_uninstall(_uninstall_config(config), runner=runner)
    assert first.status == "succeeded", first.message
    assert first.code == "uninstalled"
    receipts_before = _uninstall_receipts(config.state_root)
    runner.calls.clear()

    second = _run_uninstall(_uninstall_config(config), runner=runner)

    assert second.status == "succeeded", second.message
    assert second.code == "already_uninstalled"
    assert second.converged is True
    assert not [call for call in runner.calls if call[:3] == ("systemctl", "--user", "stop")]
    assert not [call for call in runner.calls if call[:3] == ("podman", "rm", "-f")]
    assert not [call for call in runner.calls if call[:3] == ("podman", "volume", "rm")]
    # The rerun still receipts the observed result.
    assert second.receipt_path is not None
    receipt = json.loads(second.receipt_path.read_text(encoding="utf-8"))
    assert receipt["result"] == "already_uninstalled"
    assert receipt["removed"]["unitsStopped"] == []
    assert receipt["removed"]["containers"] == []
    assert receipt["removed"]["quadletFiles"] == []
    assert len(_uninstall_receipts(config.state_root)) == len(receipts_before) + 1


def test_uninstall_never_touches_foreign_resources(
    tmp_path: Path, trust: dict[str, object], cosign_executable: Path
) -> None:
    outcome, runner, _fixture, config = _happy(tmp_path, trust, cosign_executable)
    assert outcome.status == "succeeded", outcome.message
    runner.containers.update(_live_container_names(config))
    foreign_unit = config.live_quadlet_root / "foreign-app.container"
    foreign_unit.write_text(
        "[Container]\nContainerName=foreign-app\nImage=docker.io/library/alpine:latest\n",
        encoding="utf-8",
    )
    runner.active_units.add("foreign-app")
    runner.containers.add("foreign-app")
    runner.volumes.add("foreign-volume")

    result = _run_uninstall(_uninstall_config(config), runner=runner)

    assert result.status == "succeeded", result.message
    assert foreign_unit.is_file()
    assert "foreign-app" in runner.active_units
    assert "foreign-app" in runner.containers
    assert "foreign-volume" in runner.volumes
    assert not [call for call in runner.calls if any("foreign" in part for part in call)]


def test_purge_without_confirmation_refused(
    tmp_path: Path, trust: dict[str, object], cosign_executable: Path
) -> None:
    outcome, runner, _fixture, config = _happy(tmp_path, trust, cosign_executable)
    assert outcome.status == "succeeded", outcome.message
    runner.containers.update(_live_container_names(config))
    volumes_before = set(runner.volumes)
    quadlets_before = _live_quadlet_files(config)
    runner.calls.clear()

    result = _run_uninstall(_uninstall_config(config, purge=True), runner=runner)

    assert result.status == "refused"
    assert result.code == "purge_confirmation_required"
    assert runner.calls == []
    assert runner.volumes == volumes_before
    assert _live_quadlet_files(config) == quadlets_before


def test_purge_with_wrong_installation_id_refused(
    tmp_path: Path, trust: dict[str, object], cosign_executable: Path
) -> None:
    outcome, runner, _fixture, config = _happy(tmp_path, trust, cosign_executable)
    assert outcome.status == "succeeded", outcome.message
    runner.containers.update(_live_container_names(config))
    volumes_before = set(runner.volumes)
    runner.calls.clear()

    result = _run_uninstall(
        _uninstall_config(config, purge=True, confirm_purge="installed_identity_" + "0" * 32),
        runner=runner,
    )

    assert result.status == "refused"
    assert result.code == "purge_confirmation_required"
    assert runner.calls == []
    assert runner.volumes == volumes_before
    assert any(config.live_quadlet_root.iterdir())


def test_purge_removes_volumes_and_state_root(
    tmp_path: Path, trust: dict[str, object], cosign_executable: Path
) -> None:
    outcome, runner, _fixture, config = _happy(tmp_path, trust, cosign_executable)
    assert outcome.status == "succeeded", outcome.message
    containers = _live_container_names(config)
    runner.containers.update(containers)
    identity_id = str(_install_trust(config)["installedIdentityId"])
    volumes = set(runner.volumes)
    assert len(volumes) == 2 * len(REVISION_SERVICES)
    receipt_path = config.state_root.parent / f"{config.state_root.name}.purge-receipt.json"

    result = _run_uninstall(
        _uninstall_config(config, purge=True, confirm_purge=identity_id), runner=runner
    )

    assert result.status == "succeeded", result.message
    assert result.code == "purged"
    volume_removals = [call for call in runner.calls if call[:3] == ("podman", "volume", "rm")]
    assert sorted(call[-1] for call in volume_removals) == sorted(volumes)
    assert runner.volumes == set()
    assert not any(config.state_root.iterdir())  # contents deleted
    # The receipt was written to the surviving sibling path before deletion.
    assert result.receipt_path == receipt_path
    assert receipt_path.is_file()
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    assert receipt["schema"] == "stateport.internal-install-uninstall-receipt/v1"
    assert receipt["action"] == "purge"
    assert receipt["result"] == "succeeded"
    assert sorted(receipt["removed"]["volumes"]) == sorted(volumes)
    assert receipt["removed"]["containers"] == containers
    assert receipt["removed"]["stateRootContents"]
    assert str(receipt_path) in receipt["preserved"]["paths"]
    assert receipt["preserved"]["volumes"] == []


def test_purge_on_non_stateport_directory_refused(tmp_path: Path) -> None:
    foreign = tmp_path / "random-dir"
    foreign.mkdir()
    (foreign / "keep.txt").write_text("precious\n", encoding="utf-8")
    config = installer.UninstallConfig(
        state_root=foreign,
        live_quadlet_root=tmp_path / "quadlets",
        actor_id="local-owner-test",
        purge=True,
        confirm_purge="installed_identity_" + "0" * 32,
    )
    runner = FakeRunner()

    outcome = _run_uninstall(config, runner=runner)

    assert outcome.status == "refused"
    assert outcome.code == "state_root_not_stateport"
    assert runner.calls == []
    assert (foreign / "keep.txt").read_text(encoding="utf-8") == "precious\n"


@pytest.mark.parametrize("failure", [1, OSError("simulated systemctl exec failure")])
def test_interrupted_uninstall_rerun_converges(
    tmp_path: Path,
    trust: dict[str, object],
    cosign_executable: Path,
    failure: object,
) -> None:
    outcome, runner, _fixture, config = _happy(tmp_path, trust, cosign_executable)
    assert outcome.status == "succeeded", outcome.message
    runner.containers.update(_live_container_names(config))
    runner.stop_failures.append(failure)

    first = _run_uninstall(_uninstall_config(config), runner=runner)

    assert first.status == "refused"
    assert first.code == "unit_stop_failed"
    refusals = sorted((config.state_root / "refusals").glob("*.json"))
    assert any(
        json.loads(path.read_text(encoding="utf-8"))["code"] == "unit_stop_failed"
        for path in refusals
    )

    second = _run_uninstall(_uninstall_config(config), runner=runner)

    assert second.status == "succeeded", second.message
    assert second.code == "uninstalled"
    assert not any(config.live_quadlet_root.iterdir())
    assert runner.containers == set()
    assert runner.active_units == set()


def test_cli_mode_flags_do_not_require_install_arguments() -> None:
    args = installer._parser().parse_args(["--uninstall", "--state-root", "/tmp/state"])
    assert args.uninstall is True
    assert args.purge is False
    args = installer._parser().parse_args(
        ["--purge", "--confirm-purge", "installed_identity_" + "0" * 32]
    )
    assert args.purge is True
    assert args.confirm_purge == "installed_identity_" + "0" * 32


def test_cli_uninstall_and_purge_are_mutually_exclusive() -> None:
    with pytest.raises(SystemExit):
        installer._parser().parse_args(["--uninstall", "--purge"])
