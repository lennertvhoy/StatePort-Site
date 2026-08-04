#!/usr/bin/env python3
"""StatePort no-checkout, website-compatible installer (stdlib-only bootstrap).

Installs a signed StatePort release on a clean Ubuntu 24.04 amd64 host with
rootless Podman, without any source checkout, from downloaded release
artifacts.  The script is Python 3.12+ standard-library only; the release
contracts and updater engine are loaded from the digest-verified updater
wheel, never from a checkout.

Trust order (every step fails closed):

1. The operator pins the trust root out of band: the Cosign trust public key,
   its key ID, and its SHA-256 DER SubjectPublicKeyInfo fingerprint.  The
   fingerprint of the supplied PEM is recomputed in pure stdlib (PEM armor is
   base64 DER SPKI) and must match the pinned value exactly.
2. Bootstrap authentication: the pinned Cosign executable (``--cosign``,
   required; nothing is downloaded implicitly) verifies the release-index
   signature bundle over the canonical signed payload.  The payload bytes are
   re-derived here with the exact ``stateport.canonical-json/v1`` subset
   (sorted keys, tight separators, UTF-8, no floats) and must hash to the
   signature descriptor's ``subjectDigest`` before Cosign is even invoked.
3. Only now is the index content trusted for one purpose: pinning digests.
   The updater wheel is hashed and compared against ``artifacts.updater`` in
   the authenticated signed payload, then installed into an isolated venv
   with ``pip --no-index --no-deps`` (the single digest-pinned wheel is the
   hash-locked requirement; the wheel has no runtime dependencies).
4. ``stateport_release`` and ``stateport_updater`` are imported from that
   venv.  The index is then re-verified end to end with
   ``verify_release_index`` (schema, canonical digests, channel, target,
   expiry, scan freshness, image signatures) using the pinned-key verifier.
   Any divergence between the bootstrap parse and the contract parse refuses.

Genesis boundary (documented, fail-closed): a fresh install has no
predecessor, so the revision validation/promotion ceremony has no typed
producer in this codebase.  The installer therefore creates the exact empty
genesis data volumes and their snapshot copies, records a genuine
``stateport.revision-validation-backup-receipt/v1`` (``sourceDataGeneration``
null, quiesced because no writer exists at genesis), and calls
``materialize_verified_quadlet_bundle`` — never hand-rendered units.  Only
the accepted-profile artifacts are copied into the user's live Quadlet root;
their pending ``@@STATEPORT_ACCEPTED_DATA_VOLUME:*`` tokens are resolved with
the exact genesis named volumes (the same substitution the contract performs
in ``materialize_accepted_quadlet_bundle``, which itself requires promotion
receipts no producer can issue at genesis).  Validation-profile units stay
staged and are never installed or started.  Later updates go through the
installed updater's typed ceremony.

Updater genesis: the alpha release line is pinned-public-key, and the
installed updater's typed proof contract accepts pinned-key admissions.  The
installer creates the durable trust root exactly once (create-only
``updater/trust/<keyId>.pem`` plus the self-digested
``stateport.internal-update-trust-root/v1`` record), initializes the updater
engine against the pinned policy with the real Cosign verifier, records the
schema-valid ``installed-initialize`` admission (``trustMode:
pinned-public-key``), installs the bound installed-authority identity
(installation ID, release ID, index/installer digests, target, state root,
channel), and records the durable ``install-trust.json`` fact.  A
``updater/genesis-boundary.json`` deferral record from a pre-contract install
is a historic artifact, not an outcome of this installer.

Uninstall and purge (recorded authority only, converge on partial state):
``--uninstall`` loads the durable installation record (``install-trust.json``
plus the staged materialization manifest) and reverses exactly what install
did — it stops and disables the recorded systemd user units, removes the
recorded containers by exact name, deletes the exact live Quadlet files the
installer materialized, and reloads the user manager.  All genesis data
volumes, snapshot volumes, the state root with every durable record, and the
updater venv are preserved, and a durable
``stateport.internal-install-uninstall-receipt/v1`` records every removed and
preserved name so a later purge or reinstall can read what happened.
``--purge`` additionally removes the recorded genesis data and snapshot
volumes and deletes the state root contents; it refuses closed unless
``--confirm-purge`` names the exact installed identity ID from the durable
record, and its receipt is written to ``<state-root>.purge-receipt.json``
before any state root deletion.  Both modes are idempotent: missing units,
containers, files, or volumes are convergence, and every step touches only
names from the durable record — never a glob, never a foreign resource, and
no external side-effect reversal is ever claimed.

No ``curl | sh``, no mutable tags, no shell, no silent fallback.  Every
refusal is typed and durable; where the receipt schema has every required
fact, a failed run writes a schema-conformant receipt with ``result:
failed`` — earlier refusals write a typed refusal record instead of a
half-populated receipt.  Durable state uses write-ahead intent plus atomic
rename, so an interrupted install is safely re-runnable and converges.
"""

from __future__ import annotations

import argparse
import base64
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import secrets
import shlex
import shutil
import subprocess
import sys
import tempfile
import time
from typing import Any, Callable, Mapping, Protocol, Sequence
import unicodedata
import urllib.error
import urllib.request
import venv
import zipfile


INSTALLER_VERSION = "0.1.0"
INSTALLER_ORIGIN = "https://stateport.invalid/installer/no-checkout"
EXPECTED_TARGET = "ubuntu-24.04-linux-amd64"
PODMAN_MINIMUM = (4, 9, 3)
MAX_INDEX_BYTES = 4 * 1024 * 1024
MAX_ARTIFACT_BYTES = 512 * 1024 * 1024
# verify_release_index creates signature proofs inline during the call, so a
# policy clock captured beforehand reads every honest proof as coming from the
# future.  Sixty seconds covers proof creation without moving the hour-scale
# scan-freshness and expiry boundaries (same allowance as the assembler).
PROOF_CLOCK_ALLOWANCE = timedelta(seconds=60)
QUADLET_GENERATOR_CANDIDATES = (
    Path("/usr/libexec/podman/quadlet"),
    Path("/usr/lib/podman/quadlet"),
    Path("/usr/lib/systemd/user-generators/podman-user-generator"),
)
_DIGEST = re.compile(r"^sha256:[0-9a-f]{64}$")
_KEY_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{2,127}$")
_BUNDLE_NAME = re.compile(r"^[a-z0-9][a-z0-9._-]{0,118}\.sigstore\.json$")
_CHANNELS = ("alpha", "stable", "owner-dogfood")
_SUPPLEMENTARY_ARTIFACTS = ("compose", "sourceArchive", "releaseNotes", "knownLimitations")
UPDATE_TRUST_ROOT_SCHEMA = "stateport.internal-update-trust-root/v1"
INSTALL_TRUST_SCHEMA = "stateport.internal-install-trust/v1"
UNINSTALL_RECEIPT_SCHEMA = "stateport.internal-install-uninstall-receipt/v1"


class InstallerRefusal(RuntimeError):
    """A typed, fail-closed installer refusal."""

    def __init__(self, code: str, message: str) -> None:
        if re.fullmatch(r"[a-z][a-z0-9_]{0,127}", code) is None:
            raise ValueError(f"refusal code is malformed: {code!r}")
        super().__init__(message)
        self.code = code


@dataclass(frozen=True)
class Completed:
    returncode: int
    stdout: str
    stderr: str


class Runner(Protocol):
    """Single injected subprocess seam; never a shell."""

    def run(self, argv: Sequence[str], *, timeout: int) -> Completed: ...


class SubprocessRunner:
    def run(self, argv: Sequence[str], *, timeout: int) -> Completed:
        completed = subprocess.run(
            list(argv),
            check=False,
            capture_output=True,
            text=True,
            timeout=timeout,
            shell=False,
            stdin=subprocess.DEVNULL,
        )
        return Completed(completed.returncode, completed.stdout, completed.stderr)


@dataclass(frozen=True)
class FetchResult:
    status: int
    body: bytes


class Fetcher(Protocol):
    """Loopback health and bounded HTTPS download seam."""

    def fetch(self, url: str, *, timeout: float, max_bytes: int) -> FetchResult: ...


class UrllibFetcher:
    def fetch(self, url: str, *, timeout: float, max_bytes: int) -> FetchResult:
        if not url.startswith("https://") and not url.startswith("http://127.0.0.1"):
            raise InstallerRefusal("url_refused", f"only HTTPS or loopback HTTP is allowed: {url}")
        request = urllib.request.Request(url, headers={"User-Agent": "stateport-installer"})
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                body = response.read(max_bytes + 1)
                status = int(response.status)
        except urllib.error.HTTPError as exc:
            return FetchResult(int(exc.code), b"")
        except (urllib.error.URLError, OSError) as exc:
            raise InstallerRefusal("fetch_failed", f"{url}: {exc}") from exc
        if len(body) > max_bytes:
            raise InstallerRefusal("download_too_large", f"{url} exceeds {max_bytes} bytes")
        return FetchResult(status, body)


@dataclass(frozen=True)
class HostFacts:
    os_id: str
    version_id: str
    architecture: str
    cgroup_version: str
    podman_version: str
    rootless: bool
    quadlet: bool

    def as_receipt(self) -> dict[str, Any]:
        return {
            "osId": self.os_id,
            "versionId": self.version_id,
            "architecture": self.architecture,
            "cgroupVersion": self.cgroup_version,
            "podmanVersion": self.podman_version,
            "rootless": self.rootless,
            "quadlet": self.quadlet,
        }


class HostProbe(Protocol):
    def gather(self) -> HostFacts: ...

    def occupied_ports(self) -> list[int]: ...


class SystemHostProbe:
    def __init__(
        self,
        runner: Runner,
        *,
        os_release: Path = Path("/etc/os-release"),
        cgroup_controllers: Path = Path("/sys/fs/cgroup/cgroup.controllers"),
        proc_net_tcp: tuple[Path, ...] = (Path("/proc/net/tcp"), Path("/proc/net/tcp6")),
        quadlet_candidates: Sequence[Path] = QUADLET_GENERATOR_CANDIDATES,
    ) -> None:
        self._runner = runner
        self._os_release = os_release
        self._cgroup_controllers = cgroup_controllers
        self._proc_net_tcp = proc_net_tcp
        self._quadlet_candidates = tuple(quadlet_candidates)

    def gather(self) -> HostFacts:
        uname = self._runner.run(["uname", "-m"], timeout=30)
        if uname.returncode != 0:
            raise InstallerRefusal("host_probe_failed", "uname -m failed")
        architecture = {"x86_64": "amd64", "aarch64": "arm64"}.get(
            uname.stdout.strip(), uname.stdout.strip()
        )
        os_id, version_id = "", ""
        try:
            for line in self._os_release.read_text(encoding="utf-8").splitlines():
                key, separator, value = line.partition("=")
                if not separator:
                    continue
                if key == "ID":
                    os_id = value.strip().strip('"')
                elif key == "VERSION_ID":
                    version_id = value.strip().strip('"')
        except OSError as exc:
            raise InstallerRefusal("host_probe_failed", "os-release is unreadable") from exc
        version = self._runner.run(
            ["podman", "version", "--format", "{{.Client.Version}}"], timeout=60
        )
        if version.returncode != 0 or not version.stdout.strip():
            raise InstallerRefusal("podman_missing", "podman is not installed or not executable")
        info = self._runner.run(
            ["podman", "info", "--format", "{{.Host.Security.Rootless}}"], timeout=60
        )
        if info.returncode != 0:
            raise InstallerRefusal("podman_probe_failed", "podman info failed")
        systemd = self._runner.run(
            ["systemctl", "--user", "show", "--property=Version", "--value"], timeout=60
        )
        if systemd.returncode != 0:
            raise InstallerRefusal(
                "systemd_user_missing", "a systemd user session is required for Quadlets"
            )
        return HostFacts(
            os_id=os_id,
            version_id=version_id,
            architecture=architecture,
            cgroup_version="v2" if self._cgroup_controllers.is_file() else "v1",
            podman_version=version.stdout.strip(),
            rootless=info.stdout.strip() == "true",
            quadlet=any(candidate.is_file() for candidate in self._quadlet_candidates),
        )

    def occupied_ports(self) -> list[int]:
        ports: set[int] = set()
        for path in self._proc_net_tcp:
            try:
                lines = path.read_text(encoding="ascii").splitlines()[1:]
            except OSError:
                continue
            for line in lines:
                fields = line.split()
                if len(fields) < 4 or fields[3] != "0A":  # LISTEN only
                    continue
                _, separator, port_hex = fields[1].rpartition(":")
                if separator:
                    ports.add(int(port_hex, 16))
        return sorted(ports)


@dataclass(frozen=True)
class VerifiedModules:
    """Wheel-loaded contract and updater modules (verified code boundary)."""

    release: Any
    updater_engine: Any
    updater_installed: Any
    updater_models: Any
    updater_store: Any


def load_modules_from_venv(venv_dir: Path) -> VerifiedModules:
    """Import release contracts and the updater from the digest-verified venv."""

    candidates = sorted(venv_dir.glob("lib/python3.*/site-packages"))
    exact = [
        candidate
        for candidate in candidates
        if (candidate / "stateport_release" / "__init__.py").is_file()
        and (candidate / "stateport_updater" / "__init__.py").is_file()
    ]
    if len(exact) != 1:
        raise InstallerRefusal(
            "venv_layout_unexpected", "the updater venv does not contain exactly one module root"
        )
    sys.path.insert(0, str(exact[0]))
    import stateport_release
    import stateport_updater.engine
    import stateport_updater.installed
    import stateport_updater.models
    import stateport_updater.store

    return VerifiedModules(
        release=stateport_release,
        updater_engine=stateport_updater.engine,
        updater_installed=stateport_updater.installed,
        updater_models=stateport_updater.models,
        updater_store=stateport_updater.store,
    )


@dataclass(frozen=True)
class InstallConfig:
    """Exact installer inputs; each artifact value is a local path or https URL."""

    release_index: str
    bundle_root: Path
    trust_public_key: Path
    trust_key_id: str
    trust_key_fingerprint: str
    updater_wheel: str
    channel: str
    cosign: Path
    state_root: Path
    live_quadlet_root: Path
    actor_id: str
    release_index_sha256: str | None = None
    installer_path: Path | None = None
    compose: str | None = None
    source_archive: str | None = None
    release_notes: str | None = None
    known_limitations: str | None = None
    expected_target: str = EXPECTED_TARGET
    assume_yes: bool = False
    health_timeout_seconds: float = 300.0
    health_poll_seconds: float = 2.0


@dataclass(frozen=True)
class InstallOutcome:
    status: str
    code: str
    message: str
    local_url: str | None = None
    receipt_path: Path | None = None
    converged: bool = False


@dataclass(frozen=True)
class UninstallConfig:
    """Exact uninstall/purge inputs; both modes act on recorded resources only.

    ``purge`` is its own explicit flag — nothing about uninstall implies it —
    and it stays refused until ``confirm_purge`` names the exact installed
    identity ID from the durable ``install-trust.json`` record.
    """

    state_root: Path
    live_quadlet_root: Path
    actor_id: str
    purge: bool = False
    confirm_purge: str | None = None


# ---------------------------------------------------------------------------
# stdlib trust bootstrap helpers
# ---------------------------------------------------------------------------


def _canonical_subset_bytes(value: Any) -> bytes:
    """Serialize with the exact ``stateport.canonical-json/v1`` subset.

    The signed payload permits only integers (never floats), NFC strings, and
    unique object keys; this re-serialization is byte-identical to the
    contract's ``canonical_json_bytes`` for that subset and is cross-checked
    against the wheel-loaded contract before any trust decision relies on it.
    """

    def check(item: Any, path: str) -> None:
        if item is None or isinstance(item, bool) or isinstance(item, int):
            return
        if isinstance(item, float):
            raise InstallerRefusal("index_not_canonical", f"{path}: floats are not canonical")
        if isinstance(item, str):
            if unicodedata.normalize("NFC", item) != item:
                raise InstallerRefusal("index_not_canonical", f"{path}: strings must be NFC")
            if any(0xD800 <= ord(character) <= 0xDFFF for character in item):
                raise InstallerRefusal("index_not_canonical", f"{path}: surrogates are forbidden")
            return
        if isinstance(item, list):
            for position, entry in enumerate(item):
                check(entry, f"{path}[{position}]")
            return
        if isinstance(item, dict):
            for key, entry in item.items():
                if not isinstance(key, str):
                    raise InstallerRefusal("index_not_canonical", f"{path}: keys must be strings")
                check(key, f"{path}.<key>")
                check(entry, f"{path}.{key}")
            return
        raise InstallerRefusal("index_not_canonical", f"{path}: unsupported value type")

    check(value, "$")
    return json.dumps(
        value, ensure_ascii=False, allow_nan=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")


def _sha256_digest(content: bytes) -> str:
    return "sha256:" + hashlib.sha256(content).hexdigest()


def _read_bounded(path: Path, *, description: str, maximum: int) -> bytes:
    if path.is_symlink() or not path.is_file():
        raise InstallerRefusal("input_unsafe", f"{description} is not a regular file: {path}")
    size = path.stat().st_size
    if size < 1 or size > maximum:
        raise InstallerRefusal("input_unsafe", f"{description} has an unsafe size: {path}")
    return path.read_bytes()


def _timestamp(value: datetime) -> str:
    return value.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def der_spki_fingerprint(pem: bytes) -> str:
    """SHA-256 over the DER SubjectPublicKeyInfo of a PEM public key (stdlib)."""

    try:
        text = pem.decode("ascii").replace("\r\n", "\n")
    except UnicodeDecodeError as exc:
        raise InstallerRefusal("trust_key_invalid", "trust public key is not ASCII PEM") from exc
    match = re.search(
        r"-----BEGIN PUBLIC KEY-----\n([A-Za-z0-9+/=\n]+)\n?-----END PUBLIC KEY-----",
        text,
    )
    if match is None:
        raise InstallerRefusal(
            "trust_key_invalid", "trust public key is not a PEM SubjectPublicKeyInfo"
        )
    body = match.group(1).replace("\n", "")
    try:
        der = base64.b64decode(body, validate=True)
    except ValueError as exc:
        raise InstallerRefusal("trust_key_invalid", "trust public key PEM body is invalid") from exc
    if not der:
        raise InstallerRefusal("trust_key_invalid", "trust public key DER is empty")
    return _sha256_digest(der)


def _acquire_input(
    value: str | None,
    *,
    description: str,
    expected_sha256: str | None,
    require_published_digest: bool,
    fetcher: Fetcher,
    download_dir: Path,
    maximum: int = MAX_ARTIFACT_BYTES,
) -> Path:
    """Resolve one artifact input to a local path.

    Local paths are used directly.  ``https://`` inputs are downloaded with a
    bounded read; the published SHA-256 is verified before any later use when
    one is independently supplied (the release index), and the remaining
    artifacts are verified against the authenticated signed index afterwards.
    """

    if value is None:
        raise InstallerRefusal(
            "artifact_missing",
            f"the {description} input is required: the install receipt binds the exact "
            "verified artifact set and no unverified stand-in is ever recorded",
        )
    if not value.startswith("https://"):
        return Path(value)
    if require_published_digest and (
        expected_sha256 is None or re.fullmatch(r"[0-9a-f]{64}", expected_sha256) is None
    ):
        raise InstallerRefusal(
            "published_digest_missing",
            f"downloading the {description} requires its published SHA-256 up front",
        )
    result = fetcher.fetch(value, timeout=120.0, max_bytes=maximum)
    if result.status != 200 or not result.body:
        raise InstallerRefusal(
            "download_failed", f"{description} download failed with status {result.status}"
        )
    observed = hashlib.sha256(result.body).hexdigest()
    if expected_sha256 is not None and observed != expected_sha256:
        raise InstallerRefusal(
            "download_digest_mismatch",
            f"{description} downloaded digest {observed} != published {expected_sha256}",
        )
    destination = download_dir / f"{description.replace(' ', '-')}-{observed[:16]}"
    _atomic_write(destination, result.body)
    return destination


@dataclass(frozen=True)
class BootstrapIndex:
    document: Mapping[str, Any]
    signed: Mapping[str, Any]
    signed_bytes: bytes
    signed_digest: str
    index_digest: str


def _bootstrap_authenticate(
    config: InstallConfig, index_content: bytes, work_dir: Path, runner: Runner
) -> BootstrapIndex:
    """Authenticate the release index with the pinned Cosign CLI (trust step 2)."""

    if len(index_content) > MAX_INDEX_BYTES:
        raise InstallerRefusal("index_too_large", "release index exceeds the 4 MiB limit")
    try:
        document = json.loads(index_content)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise InstallerRefusal("index_malformed", "release index is not UTF-8 JSON") from exc
    if not isinstance(document, dict) or not isinstance(document.get("signed"), dict):
        raise InstallerRefusal("index_malformed", "release index has no signed payload object")
    signatures = document.get("signatures")
    if not isinstance(signatures, list) or len(signatures) != 1:
        raise InstallerRefusal("index_malformed", "release index must carry exactly one signature")
    signature = signatures[0]
    if not isinstance(signature, dict):
        raise InstallerRefusal("index_malformed", "release index signature is not an object")
    signed_bytes = _canonical_subset_bytes(document["signed"])
    signed_digest = _sha256_digest(signed_bytes)
    if signature.get("subjectDigest") != signed_digest:
        raise InstallerRefusal(
            "signature_payload_mismatch",
            "signature subject digest does not match the canonical signed payload",
        )
    if signature.get("scheme") != "cosign-v3-bundle":
        raise InstallerRefusal("signature_scheme_refused", "signature is not a Cosign v3 bundle")
    if signature.get("trustMode") != "pinned-public-key":
        raise InstallerRefusal(
            "signature_trust_refused", "signature is outside the pinned-public-key trust root"
        )
    if signature.get("transparencyLog") != "not-uploaded-private-candidate":
        raise InstallerRefusal(
            "signature_trust_refused",
            "signature claims transparency-log authority the private toolchain never uploads",
        )
    if signature.get("publicKeyFingerprintAlgorithm") != "sha256-canonical-der-spki":
        raise InstallerRefusal(
            "signature_trust_refused", "signature uses a non-canonical fingerprint algorithm"
        )
    if (
        signature.get("publicKeyFingerprint") != config.trust_key_fingerprint
        or signature.get("publicKeyId") != config.trust_key_id
    ):
        raise InstallerRefusal(
            "signature_untrusted", "signature is not bound to the pinned key identity"
        )
    bundle = signature.get("bundle")
    if not isinstance(bundle, dict) or _DIGEST.fullmatch(str(bundle.get("digest", ""))) is None:
        raise InstallerRefusal("signature_bundle_invalid", "signature has no digest-bound bundle")
    name = PurePosixPath(str(bundle.get("uri", ""))).name
    if _BUNDLE_NAME.fullmatch(name) is None:
        raise InstallerRefusal("signature_bundle_invalid", "bundle URI names no retained bundle")
    bundle_path = config.bundle_root / name
    bundle_bytes = _read_bounded(
        bundle_path, description="release index signature bundle", maximum=MAX_INDEX_BYTES
    )
    if _sha256_digest(bundle_bytes) != bundle["digest"] or len(bundle_bytes) != bundle.get("size"):
        raise InstallerRefusal(
            "signature_bundle_mismatch", "retained bundle bytes do not match the signed record"
        )
    payload_path = work_dir / "release-index.signed-payload.json"
    _atomic_write(payload_path, signed_bytes)
    completed = runner.run(
        [
            str(config.cosign),
            "verify-blob",
            "--insecure-ignore-tlog",
            "--bundle",
            str(bundle_path),
            "--key",
            str(config.trust_public_key),
            str(payload_path),
        ],
        timeout=300,
    )
    if completed.returncode != 0:
        raise InstallerRefusal(
            "signature_verification_failed",
            f"cosign verify-blob failed: {completed.stderr.strip()[:200]}",
        )
    return BootstrapIndex(
        document=document,
        signed=document["signed"],
        signed_bytes=signed_bytes,
        signed_digest=signed_digest,
        index_digest=_sha256_digest(_canonical_subset_bytes(document)),
    )


# ---------------------------------------------------------------------------
# durable state helpers (write-ahead intent + atomic rename)
# ---------------------------------------------------------------------------


def _ensure_private_directory(path: Path) -> Path:
    path.mkdir(mode=0o700, parents=True, exist_ok=True)
    if path.is_symlink():
        raise InstallerRefusal("state_root_unsafe", f"state path is a symlink: {path}")
    os.chmod(path, 0o700)
    return path


def _atomic_write(path: Path, content: bytes) -> None:
    """Write-temp-fsync-rename within one directory; never a torn file."""

    if path.is_symlink():
        raise InstallerRefusal("state_root_unsafe", f"refusing to write through symlink: {path}")
    descriptor, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
        directory_descriptor = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(directory_descriptor)
        finally:
            os.close(directory_descriptor)
    except BaseException:
        try:
            os.unlink(temporary)
        except OSError:
            pass
        raise


def _write_json(path: Path, value: Mapping[str, Any]) -> None:
    _atomic_write(
        path,
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
        + b"\n",
    )


def _load_json(path: Path, description: str) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise InstallerRefusal("state_unreadable", f"{description} is unreadable: {path}") from exc
    if not isinstance(value, dict):
        raise InstallerRefusal("state_unreadable", f"{description} is not an object: {path}")
    return value


def _write_refusal(state_root: Path, code: str, message: str, now: datetime) -> Path | None:
    """Best-effort durable typed refusal; never masks the refusal itself."""

    try:
        refusals = _ensure_private_directory(state_root / "refusals")
        path = refusals / f"{_timestamp(now).replace(':', '')}-{code}-{secrets.token_hex(4)}.json"
        _write_json(
            path,
            {
                "schema": "stateport.install-refusal/v1",
                "operation": "install",
                "code": code,
                "message": message[:500],
                "executed": False,
                "at": _timestamp(now),
            },
        )
    except (OSError, InstallerRefusal):
        return None
    return path


# ---------------------------------------------------------------------------
# install engine
# ---------------------------------------------------------------------------


def _verify_host(facts: HostFacts) -> None:
    if facts.architecture != "amd64":
        raise InstallerRefusal(
            "host_architecture_mismatch",
            f"only linux/amd64 is supported, not {facts.architecture}",
        )
    if facts.os_id != "ubuntu" or facts.version_id != "24.04":
        raise InstallerRefusal(
            "host_os_mismatch",
            f"only ubuntu 24.04 is supported, not {facts.os_id} {facts.version_id}",
        )
    if facts.cgroup_version != "v2":
        raise InstallerRefusal("cgroup_v2_missing", "cgroup v2 is required for rootless Quadlets")
    version_match = re.match(r"^(\d+)\.(\d+)\.(\d+)", facts.podman_version)
    if version_match is None:
        raise InstallerRefusal(
            "podman_version_unparseable", f"podman version is not semantic: {facts.podman_version}"
        )
    observed = tuple(int(part) for part in version_match.groups())
    if observed < PODMAN_MINIMUM:
        raise InstallerRefusal(
            "podman_version_floor",
            f"podman >= {'.'.join(str(part) for part in PODMAN_MINIMUM)} is required, "
            f"not {facts.podman_version}",
        )
    if not facts.rootless:
        raise InstallerRefusal("podman_not_rootless", "StatePort installs rootless only")
    if not facts.quadlet:
        raise InstallerRefusal("quadlet_missing", "the Podman Quadlet generator is not installed")


def _map_contract_refusal(exc: Exception) -> InstallerRefusal:
    message = str(exc)
    mapping = (
        ("release index is expired", "index_expired"),
        ("channel does not match", "channel_mismatch"),
        ("expected target", "target_missing"),
        ("not installable under this policy", "candidate_not_installable"),
        ("publication time is in the future", "index_not_yet_published"),
        ("untrusted signer", "signature_untrusted"),
        ("verification failed", "signature_verification_failed"),
        ("withdrawn", "release_withdrawn"),
        ("deprecated", "release_deprecated"),
        ("stale", "scan_evidence_stale"),
    )
    for needle, code in mapping:
        if needle in message:
            return InstallerRefusal(code, message[:500])
    return InstallerRefusal("release_verification_failed", message[:500])


def _verify_artifact_bytes(
    path: Path,
    artifact_id: str,
    expected_digest: str,
) -> dict[str, Any]:
    """Digest-verify one release artifact as exact bytes."""

    content = _read_bounded(path, description=f"{artifact_id} artifact", maximum=MAX_ARTIFACT_BYTES)
    observed = _sha256_digest(content)
    if observed != expected_digest:
        raise InstallerRefusal(
            "artifact_digest_mismatch",
            f"{artifact_id} artifact digest {observed} != signed {expected_digest}",
        )
    return {
        "artifactId": artifact_id,
        "expectedDigest": expected_digest,
        "observedDigest": observed,
        "status": "verified",
    }


def _volume_names(signed_hex: str, volume_key: str) -> tuple[str, str]:
    key_hash = hashlib.sha256(volume_key.encode("utf-8")).hexdigest()[:12]
    return (
        f"stateport-g{signed_hex[:12]}-{key_hash}",
        f"stateport-s{signed_hex[:12]}-{key_hash}",
    )


def _ensure_volume(runner: Runner, name: str) -> None:
    exists = runner.run(["podman", "volume", "exists", name], timeout=60)
    if exists.returncode == 0:
        return
    created = runner.run(["podman", "volume", "create", name], timeout=120)
    if created.returncode != 0:
        raise InstallerRefusal(
            "volume_create_failed", f"podman volume create {name}: {created.stderr.strip()[:200]}"
        )


def _create_venv(venv_dir: Path) -> None:
    venv.create(venv_dir, with_pip=True, clear=False)


def _wheel_canonical_name(wheel: Path) -> str:
    """Return the PEP 427 filename for the digest-verified wheel.

    pip parses the wheel filename (``name-version-pytag-abitag-platform``)
    before it looks at any content, so the staged name must be derived from
    the wheel's own ``.dist-info`` metadata, never invented.  The wheel bytes
    are already digest-verified against the authenticated release index before
    this point, so trusting their metadata for the *filename* adds no trust —
    but an unparseable wheel is still refused instead of handed to pip.
    """
    try:
        with zipfile.ZipFile(wheel) as archive:
            metadata_entries = [
                name
                for name in archive.namelist()
                if name.count("/") == 1 and name.endswith(".dist-info/METADATA")
            ]
            if len(metadata_entries) != 1:
                raise ValueError(
                    f"expected exactly one .dist-info/METADATA entry, found {len(metadata_entries)}"
                )
            dist_info = metadata_entries[0].split("/", 1)[0]
            base = dist_info[: -len(".dist-info")]
            tags = [
                line.split(":", 1)[1].strip()
                for line in archive.read(f"{dist_info}/WHEEL").decode("utf-8").splitlines()
                if line.startswith("Tag:")
            ]
            if not tags:
                raise ValueError("the WHEEL metadata declares no Tag")
    except (OSError, KeyError, UnicodeDecodeError, ValueError, zipfile.BadZipFile) as exc:
        raise InstallerRefusal(
            "wheel_layout_invalid",
            f"the digest-verified updater wheel is not a parseable wheel: {exc}",
        ) from exc
    return f"{base}-{tags[0]}.whl"


def _stage_wheel_for_pip(wheel: Path, venv_dir: Path) -> Path:
    """Return a pip-installable ``.whl`` path for the digest-verified wheel.

    The shipped release bundle uses extensionless artifact names
    (``artifacts/updater``), and pip refuses any path whose filename it cannot
    parse as a wheel.  The staged name is the wheel's own PEP 427 name (see
    ``_wheel_canonical_name``); a digest-derived decorative name is *not* used
    because pip rejects filenames that do not match the exact component
    grammar.  A hardlink keeps the staging free of copies on the same
    filesystem; a copy is the cross-filesystem fallback.  A stale staged file
    from an interrupted earlier run is reused only when its bytes are
    identical, and replaced otherwise.
    """
    if wheel.suffix == ".whl":
        return wheel
    staging_dir = venv_dir / ".wheel-staging"
    staging_dir.mkdir(parents=True, exist_ok=True)
    staged = staging_dir / _wheel_canonical_name(wheel)
    if staged.is_file():
        wheel_bytes = _read_bounded(wheel, description="updater wheel", maximum=MAX_ARTIFACT_BYTES)
        if _read_bounded(staged, description="staged wheel", maximum=MAX_ARTIFACT_BYTES) == (
            wheel_bytes
        ):
            return staged
        staged.unlink()
    try:
        os.link(wheel, staged)
    except OSError:
        shutil.copyfile(wheel, staged)
    return staged


def _install_venv(
    wheel: Path, venv_dir: Path, runner: Runner, venv_creator: Callable[[Path], None]
) -> None:
    if not (venv_dir / "pyvenv.cfg").is_file():
        venv_creator(venv_dir)
    pip = venv_dir / "bin" / "pip"
    if not pip.is_file():
        raise InstallerRefusal("venv_layout_unexpected", "the updater venv has no pip executable")
    marker = venv_dir / ".updater-wheel-digest"
    wheel_digest = _sha256_digest(
        _read_bounded(wheel, description="updater wheel", maximum=MAX_ARTIFACT_BYTES)
    )
    if marker.is_file() and marker.read_text(encoding="ascii").strip() == wheel_digest:
        already = runner.run(
            [str(venv_dir / "bin" / "python"), "-c", "import stateport_release, stateport_updater"],
            timeout=60,
        )
        if already.returncode == 0:
            return  # converged: the exact wheel is already installed
    completed = runner.run(
        [
            str(pip),
            "install",
            "--no-index",
            "--no-deps",
            "--disable-pip-version-check",
            str(_stage_wheel_for_pip(wheel, venv_dir)),
        ],
        timeout=600,
    )
    if completed.returncode != 0:
        raise InstallerRefusal(
            "venv_install_failed", f"pip install failed: {completed.stderr.strip()[:300]}"
        )
    _atomic_write(marker, (wheel_digest + "\n").encode("ascii"))


def _wait_for_health(
    services: Sequence[Mapping[str, Any]],
    ports: Mapping[str, int],
    container_names: Mapping[str, str],
    *,
    fetcher: Fetcher,
    runner: Runner,
    clock: Callable[[], datetime],
    timeout_seconds: float,
    poll_seconds: float,
) -> list[dict[str, Any]]:
    """Wait for every accepted service; capture service-reported identity evidence.

    Services with a signed host port are polled over loopback HTTP; services
    without one are observed through the container health status.  Evidence is
    the exact response digest — never an HTTP 200 alone.
    """

    deadline = clock() + timedelta(seconds=timeout_seconds)
    evidence: list[dict[str, Any]] = []
    for service in sorted(services, key=lambda item: item["serviceId"]):
        service_id = str(service["serviceId"])
        health = service["health"]
        health_port = next(
            (port for port in service["ports"] if port["containerPort"] == health["containerPort"]),
            service["ports"][0] if service["ports"] else None,
        )
        observed: dict[str, Any] | None = None
        while observed is None:
            if health_port is not None:
                port = ports[f"{service_id}:accepted:{health_port['name']}"]
                url = f"http://127.0.0.1:{port}{health['path']}"
                try:
                    result = fetcher.fetch(url, timeout=10.0, max_bytes=65536)
                except InstallerRefusal:
                    result = FetchResult(0, b"")
                if result.status == 200 and result.body:
                    observed = {
                        "serviceId": service_id,
                        "source": "http-health",
                        "url": url,
                        "responseDigest": _sha256_digest(result.body),
                    }
            else:
                completed = runner.run(
                    [
                        "podman",
                        "inspect",
                        "--format",
                        "{{.State.Healthcheck.Status}}",
                        container_names[service_id],
                    ],
                    timeout=60,
                )
                if completed.returncode == 0 and completed.stdout.strip() == "healthy":
                    observed = {
                        "serviceId": service_id,
                        "source": "podman-healthcheck",
                        "container": container_names[service_id],
                        "responseDigest": _sha256_digest(completed.stdout.strip().encode()),
                    }
            if observed is None:
                if clock() >= deadline:
                    raise InstallerRefusal(
                        "health_timeout", f"service {service_id} did not report healthy in time"
                    )
                time.sleep(min(poll_seconds, 0.5))
        evidence.append(observed)
    return evidence


def install(
    config: InstallConfig,
    *,
    runner: Runner,
    probe: HostProbe,
    fetcher: Fetcher,
    module_loader: Callable[[Path], VerifiedModules],
    verifier_factory: Callable[[VerifiedModules], Any],
    clock: Callable[[], datetime],
    confirmer: Callable[[Mapping[str, Any]], bool],
    venv_creator: Callable[[Path], None] = _create_venv,
) -> InstallOutcome:
    """Run the fail-closed install flow; every refusal is typed and durable."""

    try:
        return _install_inner(
            config,
            runner=runner,
            probe=probe,
            fetcher=fetcher,
            module_loader=module_loader,
            verifier_factory=verifier_factory,
            clock=clock,
            confirmer=confirmer,
            venv_creator=venv_creator,
            started=clock(),
        )
    except InstallerRefusal as refusal:
        refusal_path = _write_refusal(config.state_root, refusal.code, str(refusal), clock())
        return InstallOutcome(
            status="refused",
            code=refusal.code,
            message=str(refusal),
            receipt_path=refusal_path,
        )


def _install_inner(
    config: InstallConfig,
    *,
    runner: Runner,
    probe: HostProbe,
    fetcher: Fetcher,
    module_loader: Callable[[Path], VerifiedModules],
    verifier_factory: Callable[[VerifiedModules], Any],
    clock: Callable[[], datetime],
    confirmer: Callable[[Mapping[str, Any]], bool],
    venv_creator: Callable[[Path], None],
    started: datetime,
) -> InstallOutcome:
    if config.channel not in _CHANNELS:
        raise InstallerRefusal("channel_invalid", f"unknown channel: {config.channel}")
    if _KEY_ID.fullmatch(config.trust_key_id) is None:
        raise InstallerRefusal("trust_key_invalid", "trust key ID is malformed")
    if _DIGEST.fullmatch(config.trust_key_fingerprint) is None:
        raise InstallerRefusal("trust_key_invalid", "trust key fingerprint is malformed")
    if not config.state_root.is_absolute():
        raise InstallerRefusal("state_root_invalid", "the install state root must be absolute")
    if not config.cosign.is_file():
        raise InstallerRefusal(
            "cosign_missing",
            "the pinned Cosign executable is required (--cosign); nothing is downloaded "
            "implicitly and no pure-Python signature verification is attempted",
        )
    pem = _read_bounded(config.trust_public_key, description="trust public key", maximum=64 * 1024)
    if der_spki_fingerprint(pem) != config.trust_key_fingerprint:
        raise InstallerRefusal(
            "trust_key_invalid",
            "supplied trust public key does not match the pinned DER SPKI fingerprint",
        )
    if not config.bundle_root.is_dir() or config.bundle_root.is_symlink():
        raise InstallerRefusal("bundle_root_invalid", "bundle root is not an operator directory")

    state_root = _ensure_private_directory(config.state_root)
    work_dir = _ensure_private_directory(state_root / "work")
    download_dir = _ensure_private_directory(work_dir / "downloads")
    receipts_dir = _ensure_private_directory(state_root / "receipts")
    intent_dir = _ensure_private_directory(state_root / "intent")
    venv_dir = state_root / "updater-venv"

    # Inputs (local paths, or bounded HTTPS downloads with digest binding).
    index_path = _acquire_input(
        config.release_index,
        description="release index",
        expected_sha256=config.release_index_sha256,
        require_published_digest=True,
        fetcher=fetcher,
        download_dir=download_dir,
        maximum=MAX_INDEX_BYTES,
    )
    wheel_path = _acquire_input(
        config.updater_wheel,
        description="updater wheel",
        expected_sha256=None,
        require_published_digest=False,
        fetcher=fetcher,
        download_dir=download_dir,
    )

    # Trust step 2: bootstrap authentication with the pinned Cosign CLI.
    index_content = _read_bounded(index_path, description="release index", maximum=MAX_INDEX_BYTES)
    bootstrap = _bootstrap_authenticate(config, index_content, work_dir, runner)

    # Trust step 3: the authenticated index pins every artifact digest.
    signed = bootstrap.signed
    artifacts = signed.get("artifacts")
    if not isinstance(artifacts, dict):
        raise InstallerRefusal("index_malformed", "signed payload has no artifact inventory")
    updater_artifact = artifacts.get("updater")
    installer_artifact = artifacts.get("installer")
    if not isinstance(updater_artifact, dict) or not isinstance(installer_artifact, dict):
        raise InstallerRefusal(
            "index_malformed", "signed payload lacks installer/updater artifacts"
        )
    wheel_digest = _sha256_digest(
        _read_bounded(wheel_path, description="updater wheel", maximum=MAX_ARTIFACT_BYTES)
    )
    if wheel_digest != updater_artifact.get("digest"):
        raise InstallerRefusal(
            "wheel_digest_mismatch",
            f"updater wheel digest {wheel_digest} != signed {updater_artifact.get('digest')}",
        )
    _install_venv(wheel_path, venv_dir, runner, venv_creator)

    # Trust step 4: load verified modules, then full contract verification.
    modules = module_loader(venv_dir)
    release = modules.release
    if release.canonical_json_bytes(bootstrap.document["signed"]) != bootstrap.signed_bytes:
        raise InstallerRefusal(
            "canonical_divergence", "stdlib bootstrap serialization diverged from the contract"
        )
    try:
        index = release.load_release_index(index_content)
    except release.ReleaseContractError as exc:
        raise _map_contract_refusal(exc) from exc
    if (
        index.signed_digest != bootstrap.signed_digest
        or index.index_digest != bootstrap.index_digest
    ):
        raise InstallerRefusal(
            "canonical_divergence", "contract digests diverge from the bootstrap digests"
        )
    # Retain the genesis index bundle into the durable content-addressed root
    # before contract verification: the installed updater re-verifies stored
    # index envelopes from this root for the installation's whole life, and
    # the bootstrap already digest-checked these exact staging bytes.
    _ensure_private_directory(config.state_root / "updater")
    durable_bundle_root = _ensure_private_directory(config.state_root / "updater" / "bundles")
    for signature in index.document["signatures"]:
        try:
            bundle_name = modules.release.signature_bundle_name(signature)
            modules.release.retain_bundle(
                durable_bundle_root, config.bundle_root / bundle_name, signature
            )
        except modules.release.CosignVerificationError as exc:
            raise InstallerRefusal(
                "signature_bundle_retention_refused",
                f"genesis signature bundle cannot be retained: {exc}",
            ) from exc
    verifier = verifier_factory(modules)
    policy = release.ReleaseVerificationPolicy(
        expected_channel=config.channel,
        expected_target=config.expected_target,
        updater_version=str(modules.updater_engine.UPDATER_VERSION),
        accepted_signers=frozenset(),
        accepted_public_keys=frozenset(
            {release.PinnedPublicKeyIdentity(config.trust_key_fingerprint, config.trust_key_id)}
        ),
        expected_trust_mode="pinned-public-key",
        now=clock() + PROOF_CLOCK_ALLOWANCE,
        allow_candidate=True,
    )
    try:
        verified = release.verify_release_index(index, policy=policy, verifier=verifier)
    except release.ReleaseContractError as exc:
        raise _map_contract_refusal(exc) from exc
    target = verified.target
    images = index.document["signed"]["images"]

    # Host verification.
    facts = probe.gather()
    _verify_host(facts)
    host_identity = {
        "formatVersion": "stateport.install-host-identity/v1",
        **facts.as_receipt(),
        "expectedTarget": config.expected_target,
    }
    host_identity_digest = release.canonical_digest(host_identity)

    # Port collision inventory (contract port policy: probe/refuse, never guess).
    occupied: list[dict[str, Any]] = []
    for port in probe.occupied_ports():
        occupied.append(
            {
                "class": "observed-host",
                "port": port,
                "identityDigest": release.canonical_digest(
                    {"class": "observed-host", "port": port, "source": "proc-net-tcp-listen"}
                ),
            }
        )
    empty_inventory = release.canonical_digest([])
    collision_digests = {
        "current": empty_inventory,
        "predecessor": empty_inventory,
        "candidate": empty_inventory,
        "observedHost": release.canonical_digest(sorted(occupied, key=lambda item: item["port"])),
    }

    # Receipt identity pieces known right after verification.
    release_identity = release.release_identity_from_verified(verified)
    quadlet_artifact = artifacts.get("quadlet")
    if not isinstance(quadlet_artifact, dict):
        raise InstallerRefusal("index_malformed", "signed payload lacks the quadlet artifact")
    observed_services = [
        {
            "serviceId": str(service["serviceId"]),
            "imageId": str(service["imageId"]),
            "imageDigest": str(
                next(image["digest"] for image in images if image["imageId"] == service["imageId"])
            ),
            "healthy": False,
        }
        for service in sorted(target["services"], key=lambda item: item["serviceId"])
    ]
    observed_image_set = release.image_set_digest(images)
    observed_service_set = release.service_set_digest(observed_services)
    target_identity: dict[str, Any] = {
        "targetId": str(target["targetId"]),
        "topologyDigest": str(target["topologyDigest"]),
        "quadletArtifactDigest": str(quadlet_artifact["digest"]),
        "quadletBundleDigest": str(target["quadletBundleDigest"]),
        "imageSetDigest": observed_image_set,
        "serviceSetDigest": observed_service_set,
    }
    target_identity["targetDigest"] = release.canonical_digest(target_identity)
    image_by_digest = {str(image["digest"]): image for image in images}
    signer_entries: list[dict[str, Any]] = []
    for proof in release.signature_verification_proof_set(verified):
        if proof["subjectDigest"] == index.signed_digest:
            subject_kind, subject_id = "release-index", "release-index"
        elif proof["subjectDigest"] in image_by_digest:
            subject_kind = "image"
            subject_id = str(image_by_digest[proof["subjectDigest"]]["imageId"])
        else:
            raise InstallerRefusal(
                "receipt_assembly_failed", "verification proof binds an unknown subject"
            )
        signer_entries.append(
            {
                "subjectKind": subject_kind,
                "subjectId": subject_id,
                "subjectDigest": proof["subjectDigest"],
                "trustMode": proof["trustMode"],
                "publicKeyFingerprint": proof["identityPrimary"],
                "publicKeyFingerprintAlgorithm": "sha256-canonical-der-spki",
                "publicKeyId": proof["identitySecondary"],
                "bundleDigest": proof["bundleDigest"],
                "verifiedAt": proof["verifiedAt"],
                "transparencyLogStatus": "not-required-private-candidate",
                "status": "verified",
            }
        )
    signer_entries.sort(key=lambda item: (item["subjectKind"], item["subjectId"]))

    # Exact install plan.
    plan: dict[str, Any] = {
        "schema": "stateport.install-plan/v1",
        "installerVersion": INSTALLER_VERSION,
        "installerDigest": str(installer_artifact["digest"]),
        "release": release_identity,
        "releaseIndexDigest": index.index_digest,
        "target": {
            "targetId": str(target["targetId"]),
            "topologyDigest": str(target["topologyDigest"]),
            "quadletBundleDigest": str(target["quadletBundleDigest"]),
        },
        "images": [
            {
                "imageId": str(image["imageId"]),
                "reference": str(image["reference"]),
                "digest": str(image["digest"]),
            }
            for image in sorted(images, key=lambda item: item["imageId"])
        ],
        "updater": {
            "version": str(modules.updater_engine.UPDATER_VERSION),
            "digest": str(updater_artifact["digest"]),
        },
        "host": host_identity,
        "stateRoot": str(state_root),
        "liveQuadletRoot": str(config.live_quadlet_root),
        "createdAt": _timestamp(started),
    }
    # The plan digest binds the exact install identity, not the wall clock:
    # excluding createdAt makes an interrupted rerun converge on the same plan.
    plan_digest = release.canonical_digest(
        {key: value for key, value in plan.items() if key != "createdAt"}
    )

    # Convergence: an exact succeeded receipt for this plan ends the rerun.
    for receipt_path in sorted(receipts_dir.glob("install_receipt_*.json")):
        try:
            existing = _load_json(receipt_path, "install receipt")
        except InstallerRefusal:
            continue
        if (
            existing.get("result") == "succeeded"
            and existing.get("operation") == "install"
            and existing.get("installPlanDigest") == plan_digest
            and existing.get("releaseIndexDigest") == index.index_digest
        ):
            # A converged rerun still enforces the create-only entry point:
            # identical content is a no-op, foreign content refuses closed.
            _install_update_wrapper(config, state_root)
            url = str(existing.get("runtime", {}).get("localUrl", ""))
            return InstallOutcome(
                status="succeeded",
                code="already_installed",
                message="an exact succeeded receipt already binds this install plan",
                local_url=url or None,
                receipt_path=receipt_path,
                converged=True,
            )

    intent = {
        "schema": "stateport.install-intent/v1",
        "intentId": f"install_intent_{secrets.token_hex(16)}",
        "operation": "install",
        "planDigest": plan_digest,
        "releaseIndexDigest": index.index_digest,
        "startedAt": _timestamp(started),
        "phase": "planned",
    }
    intent_path = intent_dir / f"{intent['intentId']}.json"
    _write_json(intent_path, intent)

    # Interactive exact-plan confirmation (installer-directive authority).
    summary = {
        "releaseId": release_identity["releaseId"],
        "version": release_identity["version"],
        "channel": release_identity["channel"],
        "planDigest": plan_digest,
        "images": [item["reference"] for item in plan["images"]],
        "stateRoot": str(state_root),
    }
    if not (config.assume_yes or confirmer(summary)):
        raise InstallerRefusal(
            "confirmation_refused", "the exact install plan was not confirmed by the actor"
        )
    confirmed_at = _timestamp(clock())
    confirmation = {
        "schema": "stateport.install-confirmation/v1",
        "planDigest": plan_digest,
        "releaseIndexDigest": index.index_digest,
        "actorId": config.actor_id,
        "confirmation": "interactive-exact-plan-acknowledged",
        "confirmedAt": confirmed_at,
    }
    confirmation_digest = release.canonical_digest(confirmation)
    _write_json(intent_dir / f"confirmation-{intent['intentId']}.json", confirmation)
    directive: dict[str, Any] = {
        "kind": "installer-directive",
        "directiveId": f"installer_directive_{secrets.token_hex(16)}",
        "directiveKind": "interactive-exact-plan",
        "actorId": config.actor_id,
        "installerDigest": str(installer_artifact["digest"]),
        "releaseIndexDigest": index.index_digest,
        "planDigest": plan_digest,
        "confirmationReceiptDigest": confirmation_digest,
        "confirmedAt": confirmed_at,
    }
    directive["directiveDigest"] = release.installer_directive_digest(directive)
    intent["phase"] = "confirmed"
    _write_json(intent_path, intent)

    # From here the receipt schema has every required fact: failures write a
    # schema-conformant receipt with result "failed" before refusing.
    failure_context = _FailureContext(
        release=release,
        receipts_dir=receipts_dir,
        directive=directive,
        release_identity=release_identity,
        index_digest=index.index_digest,
        signed_digest=index.signed_digest,
        plan_digest=plan_digest,
        target_identity=target_identity,
        facts=facts,
        signer_entries=signer_entries,
        installer_artifact_digest=str(installer_artifact["digest"]),
        started=started,
        clock=clock,
    )
    try:
        return _execute_install(
            config,
            runner=runner,
            fetcher=fetcher,
            modules=modules,
            release=release,
            verified=verified,
            index=index,
            verifier=verifier,
            target=target,
            images=images,
            artifacts=artifacts,
            installer_artifact=installer_artifact,
            updater_artifact=updater_artifact,
            wheel_path=wheel_path,
            plan_digest=plan_digest,
            host_identity_digest=host_identity_digest,
            collision_digests=collision_digests,
            occupied=occupied,
            observed_services=observed_services,
            observed_image_set=observed_image_set,
            observed_service_set=observed_service_set,
            intent=intent,
            intent_path=intent_path,
            state_root=state_root,
            stage_parent=state_root / "releases" / "staged",
            update_policy=modules.updater_models.UpdatePolicy(
                mode="manual", channel=config.channel
            ),
            clock=clock,
            failure_context=failure_context,
        )
    except InstallerRefusal as refusal:
        failure_context.write(refusal)
        raise


@dataclass
class _FailureContext:
    """Everything a schema-conformant failure receipt needs after confirmation."""

    release: Any
    receipts_dir: Path
    directive: Mapping[str, Any]
    release_identity: Mapping[str, Any]
    index_digest: str
    signed_digest: str
    plan_digest: str
    target_identity: Mapping[str, Any]
    facts: HostFacts
    signer_entries: Sequence[Mapping[str, Any]]
    installer_artifact_digest: str
    started: datetime
    clock: Callable[[], datetime]
    artifact_entries: list[dict[str, Any]] | None = None
    image_entries: list[dict[str, Any]] | None = None
    runtime: Mapping[str, Any] | None = None
    data_disposition: str = "not_applicable"

    def write(self, refusal: InstallerRefusal) -> Path | None:
        if (
            self.artifact_entries is None
            or self.image_entries is None
            or self.runtime is None
            or len(self.artifact_entries) != 7
            or not self.image_entries
        ):
            return None  # the schema has no honest receipt for this stage
        receipt = {
            "schema": "stateport.install-receipt/v1",
            "receiptId": f"install_receipt_{secrets.token_hex(16)}",
            "operation": "install",
            "installer": {
                "version": INSTALLER_VERSION,
                "digest": self.installer_artifact_digest,
            },
            "release": {
                "releaseId": self.release_identity["releaseId"],
                "version": self.release_identity["version"],
                "channel": self.release_identity["channel"],
                "signedPayloadDigest": self.signed_digest,
                "sourceCommit": self.release_identity["sourceCommit"],
                "sourceTree": self.release_identity["sourceTree"],
            },
            "releaseIndexDigest": self.index_digest,
            "installPlanDigest": self.plan_digest,
            "target": self.target_identity,
            "host": self.facts.as_receipt(),
            "verification": {
                "signedIndex": {
                    "expectedDigest": self.index_digest,
                    "observedDigest": self.index_digest,
                    "status": "verified",
                },
                "signers": list(self.signer_entries),
                "artifacts": self.artifact_entries,
                "images": self.image_entries,
            },
            "runtime": self.runtime,
            "dataDisposition": self.data_disposition,
            "authority": self.directive,
            "startedAt": _timestamp(self.started),
            "finishedAt": _timestamp(self.clock()),
            "result": "failed",
        }
        try:
            validated = self.release.validate_install_receipt(receipt)
            path = self.receipts_dir / f"{receipt['receiptId']}.json"
            _write_json(path, validated.as_dict())
        except (InstallerRefusal, OSError, self.release.ReleaseContractError):
            return None
        return path


def _persist_update_trust_root(
    config: InstallConfig,
    *,
    release: Any,
    clock: Callable[[], datetime],
) -> dict[str, Any]:
    """Persist the create-only durable updater trust root inside the state root.

    The pinned key bytes and the trust-root record derive only from the
    operator's out-of-band pinning flags, never from a release artifact.  An
    exact reinstall is a no-op; different existing content refuses closed.
    """

    trust_dir = _ensure_private_directory(config.state_root / "updater" / "trust")
    pem = _read_bounded(config.trust_public_key, description="trust public key", maximum=64 * 1024)
    pem_path = trust_dir / f"{config.trust_key_id}.pem"
    if pem_path.exists() or pem_path.is_symlink():
        if (
            _read_bounded(pem_path, description="persisted trust public key", maximum=64 * 1024)
            != pem
        ):
            raise InstallerRefusal(
                "trust_root_conflict",
                "persisted trust key bytes differ from the pinned trust public key",
            )
    else:
        _atomic_write(pem_path, pem)
    body = {
        "schema": UPDATE_TRUST_ROOT_SCHEMA,
        "mode": "pinned-public-key",
        "keyId": config.trust_key_id,
        "publicKeyFingerprint": config.trust_key_fingerprint,
        "publicKeyFingerprintAlgorithm": "sha256-canonical-der-spki",
        "channel": config.channel,
        "targetId": config.expected_target,
        "publicKeyFileDigest": _sha256_digest(pem),
        "createdAt": _timestamp(clock()),
    }
    digest = release.canonical_digest(body)
    record = {
        "trustRootId": f"update_trust_root_{digest.removeprefix('sha256:')[:32]}",
        **body,
        "trustRootDigest": digest,
    }
    comparable = {
        key: value
        for key, value in record.items()
        if key not in {"trustRootId", "trustRootDigest", "createdAt"}
    }
    record_path = trust_dir / "trust-root.json"
    if record_path.exists() or record_path.is_symlink():
        existing = _load_json(record_path, "update trust root record")
        if (
            existing.get("schema") != UPDATE_TRUST_ROOT_SCHEMA
            or {
                key: value
                for key, value in existing.items()
                if key not in {"trustRootId", "trustRootDigest", "createdAt"}
            }
            != comparable
        ):
            raise InstallerRefusal(
                "trust_root_conflict",
                "persisted update trust root binds different trust material",
            )
        return dict(existing)
    _write_json(record_path, record)
    return record


def _install_update_wrapper(config: InstallConfig, state_root: Path) -> None:
    """Persist the create-only ``stateport-update`` entry point.

    The wrapper binds the installed control-plane seam and the operator-
    controlled tool locations, then execs the updater CLI from the
    digest-verified venv against the durable updater store.  An exact
    reinstall is a no-op; different existing content refuses closed.
    """

    wrapper_dir = _ensure_private_directory(state_root / "bin")
    wrapper_path = wrapper_dir / "stateport-update"
    wrapper_content = (
        "#!/bin/sh\n"
        "# Installed StatePort updater entry point; written once by the installer.\n"
        "export STATEPORT_UPDATER_CONTROL_PLANE=stateport_updater.control_plane:build\n"
        f"export STATEPORT_COSIGN={shlex.quote(str(config.cosign))}\n"
        f"export STATEPORT_QUADLET_ROOT={shlex.quote(str(config.live_quadlet_root))}\n"
        f"exec {shlex.quote(str(state_root / 'updater-venv' / 'bin' / 'python'))} "
        f'-m stateport_updater --state-root {shlex.quote(str(state_root / "updater"))} "$@"\n'
    ).encode("utf-8")
    if wrapper_path.exists() or wrapper_path.is_symlink():
        if wrapper_path.is_symlink() or wrapper_path.read_bytes() != wrapper_content:
            raise InstallerRefusal(
                "updater_wrapper_conflict",
                "existing stateport-update wrapper differs from the installer's",
            )
    else:
        _atomic_write(wrapper_path, wrapper_content)
    os.chmod(wrapper_path, 0o755)


def _execute_install(
    config: InstallConfig,
    *,
    runner: Runner,
    fetcher: Fetcher,
    modules: VerifiedModules,
    release: Any,
    verified: Any,
    index: Any,
    verifier: Any,
    target: Mapping[str, Any],
    images: Sequence[Mapping[str, Any]],
    artifacts: Mapping[str, Any],
    installer_artifact: Mapping[str, Any],
    updater_artifact: Mapping[str, Any],
    wheel_path: Path,
    plan_digest: str,
    host_identity_digest: str,
    collision_digests: Mapping[str, str],
    occupied: Sequence[Mapping[str, Any]],
    observed_services: list[dict[str, Any]],
    observed_image_set: str,
    observed_service_set: str,
    intent: dict[str, Any],
    intent_path: Path,
    state_root: Path,
    stage_parent: Path,
    update_policy: Any,
    clock: Callable[[], datetime],
    failure_context: _FailureContext,
) -> InstallOutcome:
    """Effectful phases; every refusal leaves a failure receipt where possible."""

    # Genuine artifact verification: installer self, updater wheel, and every
    # supplementary artifact as exact bytes.  The quadlet artifact is verified
    # by full re-derivation during materialization below.
    installer_path = config.installer_path or Path(__file__).resolve()
    artifact_entries = [
        _verify_artifact_bytes(installer_path, "installer", str(installer_artifact["digest"])),
        _verify_artifact_bytes(wheel_path, "updater", str(updater_artifact["digest"])),
    ]
    supplementary = {
        "compose": config.compose,
        "sourceArchive": config.source_archive,
        "releaseNotes": config.release_notes,
        "knownLimitations": config.known_limitations,
    }
    download_dir = state_root / "work" / "downloads"
    for artifact_id in _SUPPLEMENTARY_ARTIFACTS:
        artifact = artifacts.get(artifact_id)
        if not isinstance(artifact, dict):
            raise InstallerRefusal(
                "index_malformed", f"signed payload lacks artifact {artifact_id}"
            )
        path = _acquire_input(
            supplementary[artifact_id],
            description=f"{artifact_id} artifact",
            expected_sha256=None,
            require_published_digest=False,
            fetcher=fetcher,
            download_dir=download_dir,
        )
        artifact_entries.append(_verify_artifact_bytes(path, artifact_id, str(artifact["digest"])))

    # Pull the exact digest-pinned images; verify observed digests.
    image_entries: list[dict[str, Any]] = []
    for image in sorted(images, key=lambda item: item["imageId"]):
        reference = str(image["reference"])
        if "@sha256:" not in reference:
            raise InstallerRefusal(
                "image_reference_refused", f"image reference is not digest-pinned: {reference}"
            )
        pulled = runner.run(["podman", "pull", reference], timeout=3600)
        if pulled.returncode != 0:
            raise InstallerRefusal(
                "image_pull_failed", f"podman pull {reference}: {pulled.stderr.strip()[:200]}"
            )
        inspected = runner.run(
            ["podman", "image", "inspect", "--format", "{{.Digest}}", reference], timeout=120
        )
        if inspected.returncode != 0:
            raise InstallerRefusal(
                "image_inspect_failed", f"podman inspect {reference} failed after pull"
            )
        observed_digest = "sha256:" + inspected.stdout.strip().removeprefix("sha256:")
        if observed_digest != image["digest"]:
            raise InstallerRefusal(
                "image_digest_mismatch",
                f"observed {image['imageId']} digest {observed_digest} != signed {image['digest']}",
            )
        image_entries.append(
            {
                "imageId": str(image["imageId"]),
                "reference": reference,
                "expectedDigest": str(image["digest"]),
                "observedDigest": observed_digest,
                "sizeBytes": int(image["sizeBytes"]),
                "signatureBundleDigest": str(image["signature"]["bundle"]["digest"]),
                "cycloneDxDigest": str(image["sboms"]["cycloneDx"]["digest"]),
                "spdxDigest": str(image["sboms"]["spdx"]["digest"]),
                "scanDigest": str(image["scan"]["artifact"]["digest"]),
                "provenanceDigest": str(image["provenance"]["digest"]),
                "status": "verified",
            }
        )
    intent["phase"] = "images-verified"
    _write_json(intent_path, intent)

    # Genesis data volumes and the honest empty genesis validation backup.
    signed_hex = index.signed_digest.removeprefix("sha256:")
    installation_volumes: dict[str, str] = {}
    snapshot_bindings: list[dict[str, Any]] = []
    requires_snapshot = False
    for service in target["services"]:
        for volume in service["writableVolumes"]:
            volume_key = f"{service['serviceId']}:{volume['name']}"
            data_name, snapshot_name = _volume_names(signed_hex, volume_key)
            _ensure_volume(runner, data_name)
            failure_context.data_disposition = "created"
            if volume["scope"] == "installation":
                installation_volumes[volume_key] = data_name
            if volume["validation"]["mode"] == "read-only-snapshot-copy":
                requires_snapshot = True
                _ensure_volume(runner, snapshot_name)
                snapshot_bindings.append(
                    {
                        "volumeKey": volume_key,
                        "snapshotVolumeName": snapshot_name,
                        "sourceDataGeneration": None,
                        "readOnly": True,
                    }
                )
    validation_backup_receipt: dict[str, Any] | None = None
    if requires_snapshot:
        genesis_evidence = {
            "formatVersion": "stateport.genesis-backup-evidence/v1",
            "rationale": "genesis install: no predecessor data and no writer exists; "
            "empty data volumes and their empty snapshot copies were created exactly",
            "dataVolumes": dict(sorted(installation_volumes.items())),
            "snapshots": sorted(snapshot_bindings, key=lambda item: item["volumeKey"]),
            "observedAt": _timestamp(clock()),
        }
        validation_backup_receipt = {
            "schema": "stateport.revision-validation-backup-receipt/v1",
            "operationPlanDigest": plan_digest,
            "releaseId": str(verified.index.release_id),
            "signedPayloadDigest": index.signed_digest,
            "targetId": str(target["targetId"]),
            "topologyDigest": str(target["topologyDigest"]),
            "backupReceiptDigest": release.canonical_digest(genesis_evidence),
            "snapshotSetDigest": release.canonical_digest(
                sorted(snapshot_bindings, key=lambda item: item["volumeKey"])
            ),
            "volumeBindings": sorted(snapshot_bindings, key=lambda item: item["volumeKey"]),
            "createdAt": _timestamp(clock()),
            "consistencyMode": "quiesced",
            "consistencyEvidenceDigest": release.canonical_digest(
                {"quiescence": "genesis-no-writers", **genesis_evidence}
            ),
            "result": "succeeded",
        }
        validation_backup_receipt["receiptDigest"] = release.revision_contract_digest(
            validation_backup_receipt, digest_field="receiptDigest"
        )

    # Materialize the staged bundle from the verified release (never hand-rendered).
    try:
        staged = release.materialize_verified_quadlet_bundle(
            verified,
            operation_plan_digest=plan_digest,
            host_identity_digest=host_identity_digest,
            collision_inventory_digests=collision_digests,
            occupied_port_inputs=occupied,
            proposed_at=_timestamp(clock()),
            validation_backup_receipt=validation_backup_receipt,
        )
    except release.ReleaseContractError as exc:
        raise InstallerRefusal("materialization_failed", str(exc)[:500]) from exc
    # Quadlet artifact verification is full re-derivation digest equality.
    templates = release.render_quadlet_bundle(target, images)
    observed_quadlet = release.quadlet_bundle_digest(templates)
    if observed_quadlet != target[
        "quadletBundleDigest"
    ] or observed_quadlet != quadlet_artifact_digest(artifacts):
        raise InstallerRefusal(
            "quadlet_digest_mismatch", "re-derived quadlet bundle does not match the signed digest"
        )
    artifact_entries.append(
        {
            "artifactId": "quadlet",
            "expectedDigest": quadlet_artifact_digest(artifacts),
            "observedDigest": observed_quadlet,
            "status": "verified",
        }
    )
    artifact_entries.sort(key=lambda item: item["artifactId"])
    failure_context.artifact_entries = artifact_entries
    failure_context.image_entries = image_entries

    stage_root = _ensure_private_directory(stage_parent / signed_hex)
    staged_manifest: Mapping[str, Any] | None = None
    prefix = f"staged/{signed_hex}/"
    for relative, content in sorted(staged.items()):
        if not relative.startswith(prefix):
            raise InstallerRefusal("materialization_failed", f"unexpected staged path {relative}")
        local = stage_root / PurePosixPath(relative[len(prefix) :])
        _ensure_private_directory(local.parent)
        _atomic_write(local, content)
        if local.name == "materialization.json":
            staged_manifest = json.loads(content)
    if staged_manifest is None:
        raise InstallerRefusal("materialization_failed", "staged bundle has no manifest")
    ports = {key: int(value) for key, value in staged_manifest["ports"].items()}

    # From here a failure has every fact the runtime section needs: bind the
    # planned loopback URL with all services unhealthy until proven otherwise.
    web_port = ports.get("stateport-web:accepted:http")
    local_url = f"http://127.0.0.1:{web_port}/" if web_port is not None else "http://127.0.0.1/"
    planned_runtime: dict[str, Any] = {
        "releaseId": str(verified.index.release_id),
        "releaseIndexDigest": index.index_digest,
        "signedPayloadDigest": index.signed_digest,
        "targetDigest": target_identity_digest(failure_context),
        "topologyDigest": str(target["topologyDigest"]),
        "quadletArtifactDigest": quadlet_artifact_digest(artifacts),
        "quadletBundleDigest": str(target["quadletBundleDigest"]),
        "imageSetDigest": observed_image_set,
        "serviceSetDigest": observed_service_set,
        "services": [dict(service) for service in observed_services],
        "localUrl": local_url,
        "healthy": False,
    }
    planned_runtime["runtimeIdentityDigest"] = release.canonical_digest(planned_runtime)
    failure_context.runtime = planned_runtime

    # Install accepted-profile artifacts into the live Quadlet root; resolve
    # only the pending accepted-data tokens with the exact genesis volumes.
    live_root = _ensure_private_directory(config.live_quadlet_root)
    installed_units: list[str] = []
    for artifact in staged_manifest["artifacts"]:
        if artifact["profile"] != "accepted" or artifact["kind"] not in {"container", "network"}:
            continue
        source = stage_root / PurePosixPath(str(artifact["stagedPath"])[len(prefix) :])
        text = source.read_bytes().decode("utf-8")
        for volume_key, volume_name in sorted(installation_volumes.items()):
            text = text.replace(f"@@STATEPORT_ACCEPTED_DATA_VOLUME:{volume_key}@@", volume_name)
        if "@@STATEPORT_" in text:
            raise InstallerRefusal(
                "materialization_failed",
                f"accepted artifact has unresolved tokens: {artifact['stagedPath']}",
            )
        if "[Install]" in text or "WantedBy=" in text:
            raise InstallerRefusal(
                "boot_activation_refused", "accepted units must never be boot-enabled"
            )
        unit_name = PurePosixPath(str(artifact["liveRelativePath"])).name
        _atomic_write(live_root / unit_name, text.encode("utf-8"))
        if artifact["kind"] == "container":
            installed_units.append(unit_name.removesuffix(".container"))
    intent["phase"] = "units-installed"
    _write_json(intent_path, intent)

    # Start services via the systemd user manager.
    reloaded = runner.run(["systemctl", "--user", "daemon-reload"], timeout=120)
    if reloaded.returncode != 0:
        raise InstallerRefusal(
            "systemd_reload_failed", f"daemon-reload failed: {reloaded.stderr.strip()[:200]}"
        )
    for unit in sorted(installed_units):
        started_unit = runner.run(["systemctl", "--user", "start", unit], timeout=900)
        if started_unit.returncode != 0:
            raise InstallerRefusal(
                "service_start_failed",
                f"systemctl --user start {unit}: {started_unit.stderr.strip()[:200]}",
            )

    # Wait for health and capture service-reported runtime identity evidence.
    container_names = {
        str(service["serviceId"]): "stateport-"
        + release.canonical_digest({"serviceId": str(service["serviceId"])})[7:19]
        + "-accepted-"
        + str(staged_manifest["revisions"][f"{service['serviceId']}:accepted"])
        for service in target["services"]
    }
    evidence = _wait_for_health(
        target["services"],
        ports,
        container_names,
        fetcher=fetcher,
        runner=runner,
        clock=clock,
        timeout_seconds=config.health_timeout_seconds,
        poll_seconds=config.health_poll_seconds,
    )
    intent["phase"] = "healthy"
    _write_json(intent_path, intent)
    _write_json(
        state_root / "runtime-identity-evidence.json",
        {"schema": "stateport.runtime-identity-evidence/v1", "evidence": evidence},
    )

    for service in observed_services:
        service["healthy"] = any(item["serviceId"] == service["serviceId"] for item in evidence)
    runtime: dict[str, Any] = {
        "releaseId": str(verified.index.release_id),
        "releaseIndexDigest": index.index_digest,
        "signedPayloadDigest": index.signed_digest,
        "targetDigest": target_identity_digest(failure_context),
        "topologyDigest": str(target["topologyDigest"]),
        "quadletArtifactDigest": quadlet_artifact_digest(artifacts),
        "quadletBundleDigest": str(target["quadletBundleDigest"]),
        "imageSetDigest": observed_image_set,
        "serviceSetDigest": observed_service_set,
        "services": observed_services,
        "localUrl": local_url,
        "healthy": all(service["healthy"] for service in observed_services),
    }
    runtime["runtimeIdentityDigest"] = release.canonical_digest(runtime)
    failure_context.runtime = runtime

    # Updater genesis: persist the durable out-of-band trust root, admit the
    # exact genesis release through the typed pinned-key admission contract,
    # and inject the installed-authority identity.  A stale
    # updater/genesis-boundary.json from a pre-contract install is a historic
    # record and is deliberately left untouched.
    store = modules.updater_store.UpdateStore.create(state_root / "updater")
    envelope = release.to_updater_release_envelope(verified)
    trust_root = _persist_update_trust_root(config, release=release, clock=clock)
    engine = modules.updater_engine.UpdateEngine(
        store,
        object(),  # host: genesis initialization performs no host calls
        object(),  # authority: genesis initialization claims no authority
        verification_policy=release.ReleaseVerificationPolicy(
            expected_channel=config.channel,
            expected_target=config.expected_target,
            updater_version=str(modules.updater_engine.UPDATER_VERSION),
            accepted_signers=frozenset(),
            accepted_public_keys=frozenset(
                {release.PinnedPublicKeyIdentity(config.trust_key_fingerprint, config.trust_key_id)}
            ),
            expected_trust_mode="pinned-public-key",
            now=clock(),
            allow_candidate=True,
            require_transparency_log=False,
        ),
        signature_verifier=verifier,
        clock=clock,
    )
    try:
        engine.initialize(envelope, update_policy)
    except modules.updater_engine.UpdateError as exc:
        if exc.code != "already_initialized":
            raise InstallerRefusal("updater_genesis_failed", str(exc)[:300]) from exc
        existing_status = _load_json(store.status_path, "update status")
        current = existing_status.get("current", {})
        if (
            current.get("releaseId") != str(verified.index.release_id)
            or current.get("signedPayloadDigest") != index.signed_digest
        ):
            raise InstallerRefusal(
                "updater_genesis_conflict", "existing updater status binds a different release"
            ) from exc
    genesis_admissions = [
        item
        for item in (
            _load_json(path, "release admission")
            for path in sorted(store.admissions.glob("*.json"))
        )
        if item.get("kind") == "installed-initialize"
        and item.get("releaseId") == str(verified.index.release_id)
        and item.get("releaseIndexDigest") == index.index_digest
        and item.get("signedPayloadDigest") == index.signed_digest
    ]
    if len(genesis_admissions) != 1:
        raise InstallerRefusal(
            "updater_genesis_conflict",
            "updater admissions do not bind the exact genesis release",
        )
    admission = genesis_admissions[0]
    try:
        identity = modules.updater_installed.InstalledAuthorityAdapter.install(
            store,
            installer_digest=str(installer_artifact["digest"]),
            installer_origin=INSTALLER_ORIGIN,
            installer_version=INSTALLER_VERSION,
            actor_id=config.actor_id,
            clock=clock,
        )
    except modules.updater_installed.UpdateAuthorityError as exc:
        if exc.code != "installed_identity_exists":
            raise InstallerRefusal("updater_genesis_failed", str(exc)[:300]) from exc
        adapter = modules.updater_installed.InstalledAuthorityAdapter(store, clock=clock)
        identities = [
            _load_json(path, "installed identity record")
            for path in sorted(adapter.identity_dir.glob("*.json"))
        ]
        if (
            len(identities) != 1
            or identities[0].get("releaseId") != str(verified.index.release_id)
            or identities[0].get("releaseIndexDigest") != index.index_digest
            or identities[0].get("signedPayloadDigest") != index.signed_digest
            or identities[0].get("installerDigest") != str(installer_artifact["digest"])
        ):
            raise InstallerRefusal(
                "updater_genesis_conflict",
                "existing installed authority binds a different release",
            ) from exc
        identity = identities[0]
    # The install-receipt schema is strict, so the genesis trust binding lives
    # in its own durable record; it never names the PEM path, only digests.
    install_trust = {
        "schema": INSTALL_TRUST_SCHEMA,
        "trustRootId": trust_root["trustRootId"],
        "trustRootDigest": trust_root["trustRootDigest"],
        "mode": "pinned-public-key",
        "keyId": config.trust_key_id,
        "publicKeyFingerprint": config.trust_key_fingerprint,
        "channel": config.channel,
        "targetId": config.expected_target,
        "releaseId": str(verified.index.release_id),
        "releaseIndexDigest": index.index_digest,
        "signedPayloadDigest": index.signed_digest,
        "admissionId": str(admission["admissionId"]),
        "admissionDigest": str(admission["admissionDigest"]),
        "installedIdentityId": str(identity["identityId"]),
        "installedIdentityDigest": str(identity["identityDigest"]),
        "installerDigest": str(installer_artifact["digest"]),
        "createdAt": _timestamp(clock()),
    }
    install_trust_path = state_root / "updater" / "trust" / "install-trust.json"
    comparable = {key: value for key, value in install_trust.items() if key != "createdAt"}
    if install_trust_path.exists() or install_trust_path.is_symlink():
        existing_trust = _load_json(install_trust_path, "install trust record")
        if {
            key: value for key, value in existing_trust.items() if key != "createdAt"
        } != comparable:
            raise InstallerRefusal(
                "updater_genesis_conflict",
                "existing install trust record binds a different release",
            )
    else:
        _write_json(install_trust_path, install_trust)
    intent["phase"] = "updater-genesis"
    _write_json(intent_path, intent)

    _install_update_wrapper(config, state_root)

    receipt: dict[str, Any] = {
        "schema": "stateport.install-receipt/v1",
        "receiptId": f"install_receipt_{secrets.token_hex(16)}",
        "operation": "install",
        "installer": {"version": INSTALLER_VERSION, "digest": str(installer_artifact["digest"])},
        "release": {
            "releaseId": str(verified.index.release_id),
            "version": str(verified.index.version),
            "channel": str(verified.index.channel),
            "signedPayloadDigest": index.signed_digest,
            "sourceCommit": str(index.document["signed"]["source"]["commit"]),
            "sourceTree": str(index.document["signed"]["source"]["tree"]),
        },
        "releaseIndexDigest": index.index_digest,
        "installPlanDigest": plan_digest,
        "target": failure_context.target_identity,
        "host": failure_context.facts.as_receipt(),
        "verification": {
            "signedIndex": {
                "expectedDigest": index.index_digest,
                "observedDigest": index.index_digest,
                "status": "verified",
            },
            "signers": list(failure_context.signer_entries),
            "artifacts": artifact_entries,
            "images": image_entries,
        },
        "runtime": runtime,
        "dataDisposition": "created",
        "authority": failure_context.directive,
        "startedAt": _timestamp(failure_context.started),
        "finishedAt": _timestamp(clock()),
        "result": "succeeded",
    }
    try:
        validated = release.validate_install_receipt(receipt)
    except release.ReleaseContractError as exc:
        raise InstallerRefusal("receipt_assembly_failed", str(exc)[:500]) from exc
    receipt_dir = _ensure_private_directory(state_root / "receipts")
    receipt_path = receipt_dir / f"{receipt['receiptId']}.json"
    _write_json(receipt_path, validated.as_dict())
    intent["phase"] = "receipted"
    _write_json(intent_path, intent)
    return InstallOutcome(
        status="succeeded",
        code="installed",
        message="install completed and receipted",
        local_url=local_url,
        receipt_path=receipt_path,
    )


def quadlet_artifact_digest(artifacts: Mapping[str, Any]) -> str:
    quadlet = artifacts.get("quadlet")
    if not isinstance(quadlet, dict):
        raise InstallerRefusal("index_malformed", "signed payload lacks the quadlet artifact")
    return str(quadlet["digest"])


def target_identity_digest(failure_context: _FailureContext) -> str:
    return str(failure_context.target_identity["targetDigest"])


# ---------------------------------------------------------------------------
# uninstall/purge engine (recorded authority only, converge on partial state)
# ---------------------------------------------------------------------------

_CONTAINER_NAME = re.compile(r"^ContainerName=([0-9a-z][0-9a-z._-]{1,127})$", re.MULTILINE)
_ACCEPTED_VOLUME_TOKEN = re.compile(r"@@STATEPORT_ACCEPTED_DATA_VOLUME:([^@]+)@@")
# Refusals for which writing a durable record into the state root would itself
# be wrong: the directory is foreign, unsafe, or the root argument is invalid.
_UNINSTALL_UNRECORDABLE_REFUSALS = frozenset(
    {"no_installation_found", "state_root_not_stateport", "state_root_invalid", "state_root_unsafe"}
)


@dataclass(frozen=True)
class _RemovalPlan:
    """Every resource an uninstall may touch, derived from durable records only."""

    units: tuple[str, ...]
    containers: tuple[str, ...]
    quadlet_files: tuple[str, ...]
    data_volumes: tuple[str, ...]
    snapshot_volumes: tuple[str, ...]


def _run_effect(runner: Runner, argv: Sequence[str], *, timeout: int, code: str) -> Completed:
    """Run one effect; an executor-level OSError becomes the typed step refusal."""

    try:
        return runner.run(argv, timeout=timeout)
    except OSError as exc:
        raise InstallerRefusal(
            code, f"{' '.join(str(part) for part in argv[:3])} failed to execute: {exc}"
        ) from exc


def _load_installation_record(state_root: Path, *, missing_code: str) -> dict[str, Any]:
    """Load the durable install trust record; never guess an installation."""

    if state_root.is_symlink():
        raise InstallerRefusal("state_root_unsafe", f"state root is a symlink: {state_root}")
    trust_path = state_root / "updater" / "trust" / "install-trust.json"
    if trust_path.is_symlink() or not trust_path.is_file():
        raise InstallerRefusal(
            missing_code,
            f"no StatePort installation record exists at {trust_path}; "
            "uninstall never guesses which resources belong to an installation",
        )
    record = _load_json(trust_path, "install trust record")
    if record.get("schema") != INSTALL_TRUST_SCHEMA:
        raise InstallerRefusal(
            missing_code, f"{trust_path} is not a StatePort install trust record"
        )
    signed = record.get("signedPayloadDigest")
    index_digest = record.get("releaseIndexDigest")
    if (
        not isinstance(signed, str)
        or _DIGEST.fullmatch(signed) is None
        or not isinstance(index_digest, str)
        or _DIGEST.fullmatch(index_digest) is None
        or not isinstance(record.get("releaseId"), str)
        or not isinstance(record.get("installedIdentityId"), str)
        or not record["installedIdentityId"]
    ):
        raise InstallerRefusal(
            "installation_record_invalid",
            f"install trust record at {trust_path} lacks the exact installation identity",
        )
    return record


def _load_staged_manifest(state_root: Path, signed_hex: str) -> dict[str, Any]:
    path = state_root / "releases" / "staged" / signed_hex / "materialization.json"
    if path.is_symlink() or not path.is_file():
        raise InstallerRefusal(
            "installation_record_incomplete",
            f"the staged materialization manifest is missing at {path}; without it the "
            "exact installed unit set is unknowable and uninstall refuses closed",
        )
    manifest = _load_json(path, "staged materialization manifest")
    if (
        manifest.get("formatVersion") != "stateport.quadlet-materialization/v2"
        or manifest.get("signedPayloadDigest") != f"sha256:{signed_hex}"
        or not isinstance(manifest.get("artifacts"), list)
        or not isinstance(manifest.get("validationVolumeBindings"), dict)
    ):
        raise InstallerRefusal(
            "installation_record_incomplete",
            f"staged materialization manifest at {path} is not a complete v2 manifest",
        )
    return manifest


def _derive_removal_plan(
    state_root: Path, signed_hex: str, manifest: Mapping[str, Any]
) -> _RemovalPlan:
    """Derive the exact removal set from the installation's own durable records.

    Live unit file names come from the staged manifest's accepted artifacts;
    container names come from the ``ContainerName=`` line of the installation's
    own staged Quadlet definitions; genesis data volume names are re-derived
    from the recorded ``@@STATEPORT_ACCEPTED_DATA_VOLUME:*`` tokens with the
    same stdlib formula install used, and snapshot volume names come from the
    manifest's recorded validation volume bindings.
    """

    stage_root = state_root / "releases" / "staged" / signed_hex
    prefix = f"staged/{signed_hex}/"
    units: list[str] = []
    containers: list[str] = []
    quadlet_files: list[str] = []
    data_volume_keys: set[str] = set()
    for artifact in manifest["artifacts"]:
        if not isinstance(artifact, dict):
            raise InstallerRefusal(
                "installation_record_incomplete", "manifest artifact is not an object"
            )
        if artifact.get("profile") != "accepted" or artifact.get("kind") not in {
            "container",
            "network",
        }:
            continue
        live_relative = artifact.get("liveRelativePath")
        staged_path = artifact.get("stagedPath")
        if (
            not isinstance(live_relative, str)
            or not isinstance(staged_path, str)
            or not staged_path.startswith(prefix)
            or PurePosixPath(live_relative).name != live_relative
            or not live_relative.endswith(f".{artifact['kind']}")
        ):
            raise InstallerRefusal(
                "installation_record_incomplete",
                "manifest artifact does not name an exact live unit file",
            )
        raw = _read_bounded(
            stage_root / PurePosixPath(staged_path[len(prefix) :]),
            description="staged quadlet artifact",
            maximum=1024 * 1024,
        )
        try:
            text = raw.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise InstallerRefusal(
                "installation_record_incomplete",
                f"staged quadlet artifact is not UTF-8: {staged_path}",
            ) from exc
        if artifact["kind"] == "container":
            names = _CONTAINER_NAME.findall(text)
            if len(names) != 1:
                raise InstallerRefusal(
                    "installation_record_incomplete",
                    f"staged unit {staged_path} does not declare exactly one ContainerName",
                )
            containers.append(names[0])
            units.append(live_relative.removesuffix(".container"))
        data_volume_keys.update(_ACCEPTED_VOLUME_TOKEN.findall(text))
        quadlet_files.append(live_relative)
    snapshot_volumes: list[str] = []
    for key, name in sorted(manifest["validationVolumeBindings"].items()):
        if not isinstance(key, str) or not isinstance(name, str) or not name:
            raise InstallerRefusal(
                "installation_record_incomplete",
                "validation volume binding is not an exact name pair",
            )
        snapshot_volumes.append(name)
    return _RemovalPlan(
        units=tuple(sorted(units)),
        containers=tuple(sorted(containers)),
        quadlet_files=tuple(sorted(quadlet_files)),
        data_volumes=tuple(sorted(_volume_names(signed_hex, key)[0] for key in data_volume_keys)),
        snapshot_volumes=tuple(snapshot_volumes),
    )


def _stop_and_disable_units(runner: Runner, units: Sequence[str]) -> tuple[list[str], list[str]]:
    """Stop and disable exactly the recorded units; absent ones are convergence."""

    stopped: list[str] = []
    disabled: list[str] = []
    for unit in sorted(units):
        active = _run_effect(
            runner, ["systemctl", "--user", "is-active", unit], timeout=60, code="unit_stop_failed"
        )
        if active.returncode == 0:
            completed = _run_effect(
                runner, ["systemctl", "--user", "stop", unit], timeout=900, code="unit_stop_failed"
            )
            if completed.returncode != 0:
                raise InstallerRefusal(
                    "unit_stop_failed",
                    f"systemctl --user stop {unit}: {completed.stderr.strip()[:200]}",
                )
            stopped.append(unit)
        enabled = _run_effect(
            runner,
            ["systemctl", "--user", "is-enabled", unit],
            timeout=60,
            code="unit_disable_failed",
        )
        if enabled.returncode == 0:
            completed = _run_effect(
                runner,
                ["systemctl", "--user", "disable", unit],
                timeout=120,
                code="unit_disable_failed",
            )
            if completed.returncode != 0:
                raise InstallerRefusal(
                    "unit_disable_failed",
                    f"systemctl --user disable {unit}: {completed.stderr.strip()[:200]}",
                )
            disabled.append(unit)
    return stopped, disabled


def _remove_containers(runner: Runner, names: Sequence[str]) -> list[str]:
    """Remove exactly the recorded containers; absent ones are convergence."""

    removed: list[str] = []
    for name in sorted(names):
        exists = _run_effect(
            runner,
            ["podman", "container", "exists", name],
            timeout=60,
            code="container_remove_failed",
        )
        if exists.returncode != 0:
            continue
        completed = _run_effect(
            runner, ["podman", "rm", "-f", name], timeout=300, code="container_remove_failed"
        )
        if completed.returncode != 0:
            raise InstallerRefusal(
                "container_remove_failed",
                f"podman rm -f {name}: {completed.stderr.strip()[:200]}",
            )
        removed.append(name)
    return removed


def _remove_live_quadlet_files(live_root: Path, names: Sequence[str]) -> list[str]:
    """Delete exactly the recorded live unit files; absent ones are convergence."""

    removed: list[str] = []
    for name in sorted(names):
        path = live_root / name
        if path.is_symlink():
            raise InstallerRefusal("live_unit_unsafe", f"live quadlet path is a symlink: {path}")
        if not path.exists():
            continue
        if not path.is_file():
            raise InstallerRefusal(
                "live_unit_unsafe", f"live quadlet path is not a regular file: {path}"
            )
        path.unlink()
        removed.append(name)
    return removed


def _daemon_reload(runner: Runner) -> None:
    completed = _run_effect(
        runner, ["systemctl", "--user", "daemon-reload"], timeout=120, code="systemd_reload_failed"
    )
    if completed.returncode != 0:
        raise InstallerRefusal(
            "systemd_reload_failed", f"daemon-reload failed: {completed.stderr.strip()[:200]}"
        )


def _remove_volumes(runner: Runner, names: Sequence[str]) -> list[str]:
    """Remove exactly the recorded volumes; absent ones are convergence."""

    removed: list[str] = []
    for name in sorted(names):
        exists = _run_effect(
            runner, ["podman", "volume", "exists", name], timeout=60, code="volume_remove_failed"
        )
        if exists.returncode != 0:
            continue
        completed = _run_effect(
            runner, ["podman", "volume", "rm", name], timeout=120, code="volume_remove_failed"
        )
        if completed.returncode != 0:
            raise InstallerRefusal(
                "volume_remove_failed",
                f"podman volume rm {name}: {completed.stderr.strip()[:200]}",
            )
        removed.append(name)
    return removed


def _delete_state_root_contents(state_root: Path) -> list[str]:
    """Delete every child of the state root; never follow a symlink."""

    removed: list[str] = []
    for child in sorted(state_root.iterdir()):
        if child.is_symlink() or child.is_file():
            child.unlink()
        elif child.is_dir():
            shutil.rmtree(child)
        else:
            raise InstallerRefusal(
                "state_root_unsafe", f"refusing to remove non-regular state path: {child}"
            )
        removed.append(child.name)
    return removed


def _validate_uninstall_receipt(receipt: Mapping[str, Any]) -> None:
    """Inline stdlib field check for the self-describing uninstall receipt.

    The receipt is an internal durable record in the style of
    ``install-trust.json``: small, self-describing, and checked here rather
    than against a repository schema or the strict install-receipt schema.
    """

    def fail(message: str) -> None:
        raise InstallerRefusal("receipt_assembly_failed", f"uninstall receipt: {message}")

    if receipt.get("schema") != UNINSTALL_RECEIPT_SCHEMA:
        fail("schema is wrong")
    receipt_id = receipt.get("receiptId")
    if not isinstance(receipt_id, str) or not receipt_id.startswith("uninstall_receipt_"):
        fail("receiptId is malformed")
    if receipt.get("action") not in {"uninstall", "purge"}:
        fail("action is unknown")
    if not isinstance(receipt.get("actorId"), str) or not receipt["actorId"]:
        fail("actorId is missing")
    installation = receipt.get("installation")
    if not isinstance(installation, dict):
        fail("installation identity is missing")
    else:
        for field in ("releaseId", "installedIdentityId", "stateRoot", "liveQuadletRoot"):
            if not isinstance(installation.get(field), str) or not installation[field]:
                fail(f"installation.{field} is missing")
        for field in ("releaseIndexDigest", "signedPayloadDigest"):
            value = installation.get(field)
            if not isinstance(value, str) or _DIGEST.fullmatch(value) is None:
                fail(f"installation.{field} is not a sha256 digest")
    for section in ("removed", "preserved"):
        value = receipt.get(section)
        if not isinstance(value, dict):
            fail(f"{section} is missing")
            continue
        for key, entry in value.items():
            if not isinstance(entry, list) or any(not isinstance(item, str) for item in entry):
                fail(f"{section}.{key} is not a list of exact names")
    if receipt.get("result") not in {"succeeded", "already_uninstalled"}:
        fail("result is unknown")
    for field in ("startedAt", "finishedAt"):
        if not isinstance(receipt.get(field), str):
            fail(f"{field} is missing")


def uninstall(
    config: UninstallConfig,
    *,
    runner: Runner,
    clock: Callable[[], datetime],
) -> InstallOutcome:
    """Run the fail-closed uninstall/purge flow; every refusal is typed."""

    try:
        return _uninstall_inner(config, runner=runner, clock=clock, started=clock())
    except InstallerRefusal as refusal:
        refusal_path: Path | None = None
        if refusal.code not in _UNINSTALL_UNRECORDABLE_REFUSALS:
            refusal_path = _write_refusal(config.state_root, refusal.code, str(refusal), clock())
        return InstallOutcome(
            status="refused",
            code=refusal.code,
            message=str(refusal),
            receipt_path=refusal_path,
        )


def _uninstall_inner(
    config: UninstallConfig,
    *,
    runner: Runner,
    clock: Callable[[], datetime],
    started: datetime,
) -> InstallOutcome:
    if not config.state_root.is_absolute():
        raise InstallerRefusal("state_root_invalid", "the state root must be absolute")
    state_root = config.state_root
    missing_code = "state_root_not_stateport" if config.purge else "no_installation_found"
    record = _load_installation_record(state_root, missing_code=missing_code)
    if config.purge and config.confirm_purge != str(record["installedIdentityId"]):
        raise InstallerRefusal(
            "purge_confirmation_required",
            "--purge destroys all installation data and requires --confirm-purge naming the "
            "exact installed identity ID from updater/trust/install-trust.json",
        )
    signed_hex = str(record["signedPayloadDigest"]).removeprefix("sha256:")
    manifest = _load_staged_manifest(state_root, signed_hex)
    plan = _derive_removal_plan(state_root, signed_hex, manifest)

    stopped, disabled = _stop_and_disable_units(runner, plan.units)
    containers_removed = _remove_containers(runner, plan.containers)
    files_removed = _remove_live_quadlet_files(config.live_quadlet_root, plan.quadlet_files)
    _daemon_reload(runner)

    def build_receipt(
        *,
        action: str,
        result: str,
        volumes_removed: Sequence[str],
        state_contents: Sequence[str],
        preserved_volumes: Sequence[str],
        preserved_paths: Sequence[str],
    ) -> dict[str, Any]:
        return {
            "schema": UNINSTALL_RECEIPT_SCHEMA,
            "receiptId": f"uninstall_receipt_{secrets.token_hex(16)}",
            "action": action,
            "actorId": config.actor_id,
            "installation": {
                "releaseId": str(record["releaseId"]),
                "releaseIndexDigest": str(record["releaseIndexDigest"]),
                "signedPayloadDigest": str(record["signedPayloadDigest"]),
                "installedIdentityId": str(record["installedIdentityId"]),
                "stateRoot": str(state_root),
                "liveQuadletRoot": str(config.live_quadlet_root),
            },
            "removed": {
                "unitsStopped": list(stopped),
                "unitsDisabled": list(disabled),
                "containers": list(containers_removed),
                "quadletFiles": list(files_removed),
                "volumes": list(volumes_removed),
                "stateRootContents": list(state_contents),
            },
            "preserved": {
                "volumes": list(preserved_volumes),
                "paths": list(preserved_paths),
            },
            "startedAt": _timestamp(started),
            "finishedAt": _timestamp(clock()),
            "result": result,
        }

    if config.purge:
        volumes_removed = _remove_volumes(runner, (*plan.data_volumes, *plan.snapshot_volumes))
        receipt_path = state_root.parent / f"{state_root.name}.purge-receipt.json"
        state_contents = sorted(child.name for child in state_root.iterdir())
        receipt = build_receipt(
            action="purge",
            result="succeeded",
            volumes_removed=volumes_removed,
            state_contents=state_contents,
            preserved_volumes=[],
            preserved_paths=[str(receipt_path)],
        )
        _validate_uninstall_receipt(receipt)
        # The receipt is durable before any state root deletion begins.
        _write_json(receipt_path, receipt)
        _delete_state_root_contents(state_root)
        return InstallOutcome(
            status="succeeded",
            code="purged",
            message="runtime, genesis data volumes, and state root contents removed; the "
            "purge receipt survives beside the state root and no external side-effect "
            "reversal is claimed",
            receipt_path=receipt_path,
        )

    changed = bool(stopped or disabled or containers_removed or files_removed)
    result = "succeeded" if changed else "already_uninstalled"
    receipt = build_receipt(
        action="uninstall",
        result=result,
        volumes_removed=[],
        state_contents=[],
        preserved_volumes=(*plan.data_volumes, *plan.snapshot_volumes),
        preserved_paths=[str(state_root), str(state_root / "updater-venv")],
    )
    _validate_uninstall_receipt(receipt)
    receipts_dir = _ensure_private_directory(state_root / "receipts")
    receipt_path = receipts_dir / f"{receipt['receiptId']}.json"
    _write_json(receipt_path, receipt)
    return InstallOutcome(
        status="succeeded",
        code="uninstalled" if changed else "already_uninstalled",
        message=(
            "runtime removed; all data volumes, the state root, and the updater venv "
            "are preserved and receipted"
            if changed
            else "the installation was already uninstalled; observed convergence receipted"
        ),
        receipt_path=receipt_path,
        converged=not changed,
    )


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _default_state_root() -> Path:
    base = os.environ.get("XDG_STATE_HOME")
    return (Path(base) if base else Path.home() / ".local" / "state") / "stateport"


def _default_quadlet_root() -> Path:
    base = os.environ.get("XDG_CONFIG_HOME")
    return (Path(base) if base else Path.home() / ".config") / "containers" / "systemd"


def _tty_confirmer(summary: Mapping[str, Any]) -> bool:
    print("StatePort exact install plan:")
    print(json.dumps(summary, indent=2, sort_keys=True))
    if not sys.stdin.isatty():
        print("refusing without a TTY: pass --yes to confirm the exact plan", file=sys.stderr)
        return False
    answer = input("Install exactly this plan? [type 'install'] ")
    return answer.strip() == "install"


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="install_no_checkout.py",
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument(
        "--uninstall",
        action="store_true",
        help="remove exactly the recorded runtime resources (units, containers, live "
        "quadlet files) and preserve all data volumes and durable state",
    )
    mode.add_argument(
        "--purge",
        action="store_true",
        help="uninstall plus destroy the recorded genesis data volumes and the state "
        "root contents; requires --confirm-purge",
    )
    parser.add_argument(
        "--confirm-purge",
        default=None,
        metavar="INSTALLED-IDENTITY-ID",
        help="exact installed identity ID from updater/trust/install-trust.json; "
        "required together with --purge, refused in every other mode combination",
    )
    parser.add_argument(
        "--release-index",
        default=None,
        help="install mode only: signed release-index.json (local path or https URL; "
        "a URL requires --release-index-sha256 and no download is ever used before "
        "its digest verifies)",
    )
    parser.add_argument(
        "--release-index-sha256",
        default=None,
        help="published SHA-256 of the release index; mandatory for https downloads",
    )
    parser.add_argument(
        "--bundle-root",
        type=Path,
        default=None,
        help="install mode only: directory with the retained .sigstore.json bundles",
    )
    parser.add_argument("--trust-public-key", type=Path, default=None)
    parser.add_argument("--trust-key-id", default=None)
    parser.add_argument(
        "--trust-key-fingerprint",
        default=None,
        help="sha256:... DER SubjectPublicKeyInfo fingerprint of the trust key",
    )
    parser.add_argument("--updater-wheel", default=None, help="local path or https URL")
    parser.add_argument("--compose", default=None, help="local path or https URL")
    parser.add_argument("--source-archive", default=None, help="local path or https URL")
    parser.add_argument("--release-notes", default=None, help="local path or https URL")
    parser.add_argument("--known-limitations", default=None, help="local path or https URL")
    parser.add_argument("--channel", default=None, choices=_CHANNELS)
    parser.add_argument(
        "--cosign",
        type=Path,
        default=None,
        help="install mode only: pinned Cosign executable; required, never downloaded implicitly",
    )
    parser.add_argument("--state-root", type=Path, default=_default_state_root())
    parser.add_argument("--live-quadlet-root", type=Path, default=_default_quadlet_root())
    parser.add_argument("--actor-id", default=f"local-owner-{os.environ.get('USER', 'unknown')}")
    parser.add_argument(
        "--installer-path",
        type=Path,
        default=None,
        help="path of the exact installer artifact to self-verify (defaults to this script)",
    )
    parser.add_argument(
        "--yes", action="store_true", help="confirm the exact install plan non-interactively"
    )
    parser.add_argument("--health-timeout-seconds", type=float, default=300.0)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = _parser()
    args = parser.parse_args(argv)
    install_flags: dict[str, object] = {
        "--release-index": args.release_index,
        "--bundle-root": args.bundle_root,
        "--trust-public-key": args.trust_public_key,
        "--trust-key-id": args.trust_key_id,
        "--trust-key-fingerprint": args.trust_key_fingerprint,
        "--updater-wheel": args.updater_wheel,
        "--compose": args.compose,
        "--source-archive": args.source_archive,
        "--release-notes": args.release_notes,
        "--known-limitations": args.known_limitations,
        "--channel": args.channel,
        "--cosign": args.cosign,
    }
    runner = SubprocessRunner()
    if args.uninstall or args.purge:
        provided = [flag for flag, value in install_flags.items() if value is not None]
        if provided:
            parser.error(
                "--uninstall/--purge are mutually exclusive with install arguments: "
                + ", ".join(provided)
            )
        if args.confirm_purge is not None and not args.purge:
            parser.error("--confirm-purge is only meaningful together with --purge")
        outcome = uninstall(
            UninstallConfig(
                state_root=args.state_root,
                live_quadlet_root=args.live_quadlet_root,
                actor_id=args.actor_id,
                purge=bool(args.purge),
                confirm_purge=args.confirm_purge,
            ),
            runner=runner,
            clock=lambda: datetime.now(timezone.utc),
        )
        mode_name = "purge" if args.purge else "uninstall"
        if outcome.status == "succeeded":
            print(f"StatePort {mode_name} completed: {outcome.message}")
            if outcome.receipt_path is not None:
                print(f"receipt: {outcome.receipt_path}")
            return 0
        print(f"{mode_name} refused ({outcome.code}): {outcome.message}", file=sys.stderr)
        if outcome.receipt_path is not None:
            print(f"refusal record: {outcome.receipt_path}", file=sys.stderr)
        return 2
    missing = [flag for flag, value in install_flags.items() if value is None]
    if missing:
        parser.error("install mode requires: " + ", ".join(missing))
    config = InstallConfig(
        release_index=args.release_index,
        release_index_sha256=args.release_index_sha256,
        bundle_root=args.bundle_root,
        trust_public_key=args.trust_public_key,
        trust_key_id=args.trust_key_id,
        trust_key_fingerprint=args.trust_key_fingerprint,
        updater_wheel=args.updater_wheel,
        channel=args.channel,
        cosign=args.cosign,
        state_root=args.state_root,
        live_quadlet_root=args.live_quadlet_root,
        actor_id=args.actor_id,
        installer_path=args.installer_path,
        compose=args.compose,
        source_archive=args.source_archive,
        release_notes=args.release_notes,
        known_limitations=args.known_limitations,
        assume_yes=args.yes,
        health_timeout_seconds=args.health_timeout_seconds,
    )

    def cosign_factory(modules: VerifiedModules) -> Any:
        return modules.release.CosignVerifier(
            cosign=config.cosign,
            public_key=config.trust_public_key,
            identity=modules.release.PinnedPublicKeyIdentity(
                config.trust_key_fingerprint, config.trust_key_id
            ),
            bundle_root=config.state_root / "updater" / "bundles",
        )

    outcome = install(
        config,
        runner=runner,
        probe=SystemHostProbe(runner),
        fetcher=UrllibFetcher(),
        module_loader=load_modules_from_venv,
        verifier_factory=cosign_factory,
        clock=lambda: datetime.now(timezone.utc),
        confirmer=_tty_confirmer,
    )
    if outcome.status == "succeeded":
        print(f"StatePort is installed and healthy: {outcome.local_url}")
        print(f"install receipt: {outcome.receipt_path}")
        return 0
    print(f"install refused ({outcome.code}): {outcome.message}", file=sys.stderr)
    if outcome.receipt_path is not None:
        print(f"refusal record: {outcome.receipt_path}", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
