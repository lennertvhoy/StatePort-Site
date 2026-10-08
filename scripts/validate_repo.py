#!/usr/bin/env python3
"""Small, dependency-free integrity gate for the StatePort public site."""

from __future__ import annotations

from html.parser import HTMLParser
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import subprocess
from urllib.parse import urlsplit

from install_transport import (
    MANIFEST_DIGESTS,
    MUTABLE_BOOTSTRAP_SHA256,
    MUTABLE_BOOTSTRAP_SIZE,
    MUTABLE_BOOTSTRAP_URL,
    RETAINED_ALPHA10_BOOTSTRAP_SHA256,
    RETAINED_ALPHA10_BOOTSTRAP_SIZE,
    RETAINED_ALPHA10_MANIFEST_DIGESTS,
    RETAINED_ALPHA11_BOOTSTRAP_SHA256,
    RETAINED_ALPHA11_BOOTSTRAP_SIZE,
    RETAINED_ALPHA11_INDEX_SHA256,
    RETAINED_ALPHA11_MANIFEST_DIGESTS,
    VERSIONED_BOOTSTRAP_SHA256,
    VERSIONED_BOOTSTRAP_SIZE,
    VERSIONED_BOOTSTRAP_URL,
)
from render_support import load_config, rendered_home, support_enabled
from projectstate_gate import validate as validate_projectstate


ROOT = Path(__file__).resolve().parents[1]

CURRENT_RELEASE_VERSION = "0.1.0-alpha.24"
CURRENT_RELEASE_LABEL = "Alpha.24"
CURRENT_RELEASE_ROOT = "download/0.1.0-alpha.24"
CURRENT_MANIFEST_ROOT = "download/alpha24-manifests"
CURRENT_RELEASE_INDEX_SHA256 = "2c6cd10929eb59923caa8d151464c05e844a6d909685644f1fa01495f1dc5f12"
CURRENT_RELEASE_INDEX_SIGSTORE_SHA256 = "28cb50d14dd078d68d7fd37fd079edfb80001e794f29355cf9d406d0d476a544"
CURRENT_SIGNED_PAYLOAD_SHA256 = "bbb3852e5e094f5d88b506a75b6bf1e6d1b4a8e5cb17814ba210b9dfdb650f90"
CURRENT_TRUST_PUBLIC_KEY_SHA256 = "798d6ea6e2703993758f0fb45618b1f05b40f6ef116e7d286fd5a6867859b8ad"
INSTALLER_STATUS = "StatePort 0.1.0-alpha.24 is the current signed release. It installs and passes in a clean test VM; real-Windows and reboot results pending (reboot: not measured). In a fresh Windows 11 test virtual machine (a KVM guest on a Linux workstation, not bare metal) with WSL2 and stock Ubuntu 24.04, reset to a clean snapshot, the Alpha.24 installer, run from a local copy of the signed files with the container images pulled from the registry, installed StatePort and exited 0. All services reported healthy, the web page and the API answered, a second run of the installer over the finished install reported that it was already installed and changed nothing, and the API port named in the install manifest (18097) was the port the started API answered on. That install test is all that has been measured on Alpha.24 so far. Three changes are in this release and are still being verified on the public bytes: the web service has its own outbound network while the API and worker stay isolated, the installer continues with a notice when the optional Windows keep-alive registration is slow, and restarting the StatePort target restarts its containers. Measured on the previous release, Alpha.23, through the public one-line command: it installed and exited 0 in about 9 minutes on a pristine machine (3 of 4 attempts on those bytes; the 4th crashed in the optional Windows keep-alive registration on a 120-second PowerShell timeout), the bundled study sample ran end to end (start an activity, review the exact proposed change, approve it, open the receipt, write a reflection, with the durable result read back through the product's own interface) and the saved data was still there after restarting the StatePort services and after a full WSL distribution restart (7 of 7 checks both times), the install plan named API port 18464 while the started API answered on 18447, and importing the StudyState template from GitHub inside StatePort failed because the product's containers could not resolve external host names. The public one-line command, the study sample, the restarts and the template import have not yet been measured on Alpha.24. The optional keep-alive task is registered to start at Windows start-up, at sign-in and every 10 minutes, but it had not run on the test machine. Reboot: not measured. Uninstall was not run on Windows. A browser click-through of the study sample was last measured on Alpha.21. On Alpha.21, coding-agent runs, chat replies, restore from the interface, the workbench terminal and files tools, per-application workspaces, and the standing-authority and updater pages did not work, and none of that has been measured on an installed Alpha.24."

# These publication anchors are intentionally duplicated here instead of being
# imported from build_immutable_manifest.py. The validator is an independent
# policy check over both the generator and its output.
VALIDATOR_PUBLICATION_ANCHORS = {
    "download/0.1.0-alpha.2": "4043534a9a1d56c51c3d47d0906e0520963af79c",
    "download/0.1.0-alpha.3": "52b42dd47a11510220f33690075f1b6773f6a889",
    "download/0.1.0-alpha.5": "eaa1ca6a67844259860917442a95c891d097939f",
    "download/0.1.0-alpha.10": "24428baa1dbee3eaac637e19c34c2aad00e7a38c",
    "download/0.1.0-alpha.11": "eff7302670e313c79b7fb79155fd5be607dcfdcf",
    "download/0.1.0-alpha.12": "15b11d7c30df5c95f6bce81fa61e4814c0697520",
}

ALPHA3_CANONICAL_SOURCE_IDENTITY = {
    "commit": "fa4ea4b7f08e78669e194c204b59206ab109a02f",
    "tree": "aec60303045e7a9c8255b941c761d904af85ec10",
}
ALPHA3_PUBLIC_SNAPSHOT_IDENTITY = {
    "commit": "43d6b4491b962c963a0ecafc060e0dfc7e334dc0",
    "tree": "3bbe46db14a7c929e6f0a17ca153ec686192aa51",
}
ALPHA3_CURATED_SOURCE_ARCHIVE = {
    "bytes": 20_305_920,
    "sha256": "17f5680c30841b1e831b37df02dca8f03c2c03d265a42633dd525f99bd613398",
}
CURRENT_CANONICAL_SOURCE_IDENTITY = {
    "commit": "b1641c540363912f9d3c3c1de04cf8fe8ca0a21f",
    "tree": "1ff2b631d049749c4eadb6058391f8c561ee0c39",
}
# Retained immutable Alpha.16 canonical identity (byte-anchored also by
# config/immutable-release-trees.json; per-field identity retained here).
RETAINED_ALPHA16_IDENTITY = {
    "commit": "0807b68edca8a1ae6fc1c1f16ddba9740783a951",
    "tree": "126587c310cf195e1ac06a59d76134ab6f8cc975",
}
CURRENT_PUBLIC_SNAPSHOT_IDENTITY = {
    "commit": "9bb0ea2505f35d4de428349214589dbcfc8fdc09",
    "tree": "53799c45a3e67f3bb9e0f622380e46634883a627",
}
RETAINED_ALPHA16_PUBLIC_SNAPSHOT_IDENTITY = {
    "commit": "05c2ace3b07233c1a84bd2a4b006c7ec6d2a918f",
    "tree": "cdc5769ff933599fba8c74d95842eb7cae0b0bd5",
}
CURRENT_CURATED_SOURCE_ARCHIVE = {
    "bytes": 28_375_040,
    "sha256": "edbf735451d543ce4c48521cd6e0d08866cb11ec330b35e2f166468e5fbd43d0",
}
CURRENT_PUBLIC_SOURCE_URL = "https://github.com/lennertvhoy/StatePort-Source.git"
CURRENT_TARGET_ID = "wsl2-ubuntu2404-linux-amd64-rootless-podman-quadlet"
RETAINED_ALPHA16_PREDECESSOR_VERSION = "0.1.0-alpha.23"
RETAINED_ALPHA11_IDENTITY = {
    "commit": "57dae10ff94c5b6aa37cc5d23509a89d91887cac",
    "tree": "c17f0ba7b44cfbf3f30ebe1938d92e640434a640",
}
RETAINED_ALPHA11_SOURCE_ARCHIVE = {
    "bytes": 24_432_640,
    "sha256": "bfbdffb380787d71bbbd558aa64cbd8eba3bedfdaabb121116c6df7ea2ac6d52",
}
RETAINED_ALPHA10_IDENTITY = {
    "commit": "930c2d9ad3dcc659da9e8a2b966972cfd78f0f0e",
    "tree": "726d1dcba907d83ed926ffbf977a3ef4fe1e4725",
}
RETAINED_ALPHA10_SOURCE_ARCHIVE = {
    "bytes": 24_258_560,
    "sha256": "7bd456b2ed3db1dcc881f78cc2f78ae88770af5ea9c75444d0eefa18be8ab795",
}
RETAINED_ALPHA10_INDEX_SHA256 = "2fc626fcab180f664f04f36d1fcceacaffa81ca96a658585f6684e3cf37abf89"
RETAINED_ALPHA10_INDEX_SIGSTORE_SHA256 = "db7814299a7603088e1a0cac3845a0c4be7a165465537bc7710957ecf5499b11"
RETAINED_ALPHA10_SIGNED_PAYLOAD = "sha256:2478e9c69aac1679813c448d25a7648e68d81f44daaa2d7bc3085aaf86b7b222"
RETAINED_ALPHA5_MANIFEST_DIGESTS = {
    "stateport-api": "a5c639880195ba6dc57fa9c13378fdf0cdb0361f08cbddea7b7e90f476906af8",
    "stateport-dev-workspace": "1a9eecc2a087620e7139570e09c08b4ce6c17a8369d2b428551809dff3fda886",
    "stateport-execution-host": "02d3ce6d6dfdacc164b947c1c88ebf6c64e0a103b05fbd420454083db589efb2",
    "stateport-playwright": "a5e8bc89bd193bd149dcad3de03366796bcc8f903f019e9e599f928dfaed9096",
    "stateport-runner": "45b5aaf0cd18699a66371ed800683ad5740b491d1442d9c1edd90d87089786ae",
    "stateport-web": "57f625f36c590c1440d70f07a3aa1bee6b31c2a9c942285c897c7934635fccf1",
    "stateport-worker": "ac835bf5449d1f7843734a8cbb9f4a332e9b01e6066f06599798a6964539e551",
}


# Local, untracked build source for the public overview media. It is not a
# visitor page, so page-level scans must exclude this source tree while
# remaining strict for every deployed HTML page.
LOCAL_BUILD_SOURCE_ROOTS = {
    Path("media-src/stateport-overview"),
    Path("output/ux-mission/source/stateport-overview"),
}
LOCAL_BUILD_SOURCE_MANIFEST = Path("media-src/stateport-overview/source-manifest.json")
BRAND_ASSET_SHA256 = {
    "assets/stateport-mascot-block-arch-light.svg": "32af9b36db5a7dafba0b85f3598806dc13b2d9a31e3fab5415ff65dd80462240",
    "assets/stateport-mascot-block-arch-dark.svg": "62d1a8ee6a68aa025e7246f689cd4ed7e885d7f3d97fb78fe84c0d5f75cdf013",
}
MASCOT_SIZE_CONTRACT = {"header": (184, 184), "footer": (85, 85)}
OVERVIEW_MP4_SHA256 = "bccf9121e2ecd43779599c48ffead2675fd0043b2bdf1d5b3fb0b6fca85c09b5"


def is_local_build_source(path: Path) -> bool:
    return any(path == root or root in path.parents for root in LOCAL_BUILD_SOURCE_ROOTS)


def validate_brand_asset_bytes() -> None:
    """Keep both canonical mascot files byte-bound, including inactive dark art."""

    for relative, expected in BRAND_ASSET_SHA256.items():
        path = ROOT / relative
        if not path.is_file():
            raise AssertionError(f"Missing canonical brand asset: {relative}")
        observed = hashlib.sha256(path.read_bytes()).hexdigest()
        if observed != expected:
            raise AssertionError(f"Canonical brand asset drifted: {relative}")


def validate_mascot_size_contract() -> None:
    """Keep rendered mascots at 75% of their previous size; preserve artwork."""

    css = require("assets/site.css").read_text(encoding="utf-8")
    if "--mascot-header-size: clamp(72px, 7.3828125vw, 138px)" not in css:
        raise AssertionError("header mascot token is stale")
    if "--mascot-footer-size: clamp(41.25px, 3.75vw, 63.75px)" not in css:
        raise AssertionError("footer mascot token is stale")
    favicon = require("assets/favicon-block-arch.svg").read_text(encoding="utf-8")
    if 'viewBox="24 21 464 464"' not in favicon:
        raise AssertionError("fixed mascot canvas artwork is not at the 175% contract")
    for path in ROOT.rglob("*.html"):
        if is_local_build_source(path):
            continue
        text = path.read_text(encoding="utf-8")
        for role, (width, height) in MASCOT_SIZE_CONTRACT.items():
            if role == "header" and 'class="brand"' in text and 'class="brand"' in text:
                if f'width="84" height="84"' in text:
                    raise AssertionError(f"header mascot intrinsic size is stale: {path}")
            if role == "footer" and 'class="footer-mark"' in text:
                if f'width="68" height="68"' in text:
                    raise AssertionError(f"footer mascot intrinsic size is stale: {path}")


def validate_local_media_source_manifest() -> None:
    """Validate local media provenance when the untracked source is present."""

    manifest_path = ROOT / LOCAL_BUILD_SOURCE_MANIFEST
    if not manifest_path.is_file():
        return
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    disposition = manifest.get("sourceDisposition", {})
    if disposition.get("trackedForPages") is not False:
        raise AssertionError("local media source must remain outside the Pages tree")
    if disposition.get("publishedExecutableSource") is not False:
        raise AssertionError("local HyperFrames source must not be published executable source")
    observed_mp4 = (ROOT / "assets/media/stateport-overview.mp4").is_file()
    if disposition.get("mp4Present") is not observed_mp4:
        raise AssertionError("source manifest MP4 disposition does not match the local candidate")
    if observed_mp4:
        observed_mp4_sha256 = hashlib.sha256(
            (ROOT / "assets/media/stateport-overview.mp4").read_bytes()
        ).hexdigest()
        if observed_mp4_sha256 != OVERVIEW_MP4_SHA256:
            raise AssertionError("local overview MP4 digest does not match the accepted candidate output")

    expected_mascots = {
        "assets/stateport-mascot-block-arch-light.svg": BRAND_ASSET_SHA256[
            "assets/stateport-mascot-block-arch-light.svg"
        ],
    }
    recorded_mascots = {
        details.get("asset"): details.get("sha256")
        for details in manifest.get("brandProvenance", {}).values()
    }
    if recorded_mascots != expected_mascots:
        raise AssertionError("local media source mascot provenance is stale")
    retained = manifest.get("retainedImmutableBrandAssets", {})
    dark_asset = "assets/stateport-mascot-block-arch-dark.svg"
    if retained.get(dark_asset, {}).get("sha256") != BRAND_ASSET_SHA256[dark_asset]:
        raise AssertionError("local media source must retain the inactive dark mascot hash")
    if retained.get(dark_asset, {}).get("activeUse") is not False:
        raise AssertionError("inactive dark mascot must not be marked as active use")

    for capture in manifest.get("finalCaptures", []):
        public_path = capture.get("publicPath")
        source_path = capture.get("sourcePath")
        public_file = ROOT / public_path if isinstance(public_path, str) else None
        source_file = manifest_path.parent / source_path if isinstance(source_path, str) else None
        if not public_file or not public_file.is_file() or not source_file or not source_file.is_file():
            raise AssertionError(f"local media source capture is missing: {public_path}")
        if capture.get("mascotAsset") != "assets/stateport-mascot-block-arch-light.svg":
            raise AssertionError(f"local media source capture is not light-mascot bound: {public_path}")
        if hashlib.sha256(public_file.read_bytes()).hexdigest() != capture.get("sha256"):
            raise AssertionError(f"local media source capture hash is stale: {public_path}")


class AssetReferenceParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.references: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        for name, value in attrs:
            if name in {"href", "src"} and value:
                self.references.append(value)


class FaviconReferenceParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.references: list[tuple[str, str]] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag != "link":
            return
        values = {name: value or "" for name, value in attrs}
        rel = {token.lower() for token in values.get("rel", "").split()}
        if rel.intersection({"icon", "manifest", "apple-touch-icon"}) and values.get("href"):
            self.references.append((" ".join(sorted(rel)), values["href"]))


ACTIVE_FAVICON_FILES = {
    "assets/favicon.svg": None,
    "assets/favicon-16.png": (16, 16),
    "assets/favicon-32.png": (32, 32),
    "assets/favicon-192.png": (192, 192),
    "assets/favicon-512.png": (512, 512),
    "assets/favicon.ico": None,
    "assets/apple-touch-icon.png": (180, 180),
}
FAVICON_VIEWBOX = 'viewBox="24 21 464 464"'


def _resolve_site_reference(page: Path, reference: str) -> Path | None:
    parsed = urlsplit(reference)
    if parsed.scheme or parsed.netloc or reference.startswith("#") or not parsed.path:
        return None
    if parsed.path.startswith("/StatePort-Site/"):
        target = (ROOT / parsed.path[len("/StatePort-Site/") :]).resolve()
    else:
        target = (page.parent / parsed.path).resolve()
    if ROOT not in target.parents and target != ROOT:
        return None
    return target


def _png_dimensions(path: Path) -> tuple[int, int]:
    data = path.read_bytes()
    if data[:8] != b"\x89PNG\r\n\x1a\n" or data[12:16] != b"IHDR":
        raise AssertionError(f"Not a PNG file: {path.relative_to(ROOT)}")
    return int.from_bytes(data[16:20], "big"), int.from_bytes(data[20:24], "big")


def validate_active_favicons() -> None:
    """Validate every served favicon link and the exact active artwork bounds."""

    source = require("assets/favicon-block-arch.svg").read_text(encoding="utf-8")
    active_svg = require("assets/favicon.svg").read_text(encoding="utf-8")
    if FAVICON_VIEWBOX not in source or FAVICON_VIEWBOX not in active_svg:
        raise AssertionError("active favicon SVG must use the 24 21 464 464 visual-bound contract")
    if active_svg != source:
        raise AssertionError("assets/favicon.svg must be byte-identical to favicon-block-arch.svg")

    referenced: set[Path] = set()
    for page in sorted(ROOT.rglob("*.html")):
        if is_local_build_source(page.relative_to(ROOT)):
            continue
        parser = FaviconReferenceParser()
        parser.feed(page.read_text(encoding="utf-8"))
        for rel, reference in parser.references:
            target = _resolve_site_reference(page, reference)
            if target is None:
                raise AssertionError(f"{page.relative_to(ROOT)}: favicon reference must be local: {reference}")
            if rel == "manifest":
                if target.name != "site.webmanifest":
                    raise AssertionError(f"{page.relative_to(ROOT)}: unexpected manifest reference: {reference}")
                try:
                    manifest = json.loads(target.read_text(encoding="utf-8"))
                except json.JSONDecodeError as exc:
                    raise AssertionError(f"Invalid manifest referenced by {page}: {exc}") from exc
                for icon in manifest.get("icons", []):
                    icon_target = _resolve_site_reference(target, icon.get("src", ""))
                    if icon_target is None:
                        raise AssertionError(f"{target.relative_to(ROOT)}: manifest icon must be local")
                    referenced.add(icon_target)
            else:
                referenced.add(target)

    missing = sorted(path.relative_to(ROOT) for path in referenced if not path.is_file())
    if missing:
        raise AssertionError(f"Active favicon reference is missing: {missing}")
    expected_paths = {Path(relative) for relative in ACTIVE_FAVICON_FILES}
    unexpected = sorted(str(path.relative_to(ROOT)) for path in referenced if path.relative_to(ROOT) not in expected_paths)
    if unexpected:
        raise AssertionError(f"Active favicon references contain unexpected files: {unexpected}")
    for relative, dimensions in ACTIVE_FAVICON_FILES.items():
        path = require(relative)
        if dimensions and path.suffix == ".png" and _png_dimensions(path) != dimensions:
            raise AssertionError(f"{relative} must retain fixed canvas dimensions {dimensions[0]}x{dimensions[1]}")


def require(path: str) -> Path:
    candidate = ROOT / path
    if not candidate.is_file():
        raise AssertionError(f"Missing required file: {path}")
    return candidate


def require_text(path: str, fragment: str) -> None:
    text = require(path).read_text(encoding="utf-8")
    if fragment not in text:
        raise AssertionError(f"Expected {fragment!r} in {path}")


def _git_environment() -> dict[str, str]:
    """Return an environment that cannot redirect or replace Git objects."""

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


def _anchored_files(tree: str, commit: str, *, root: Path = ROOT) -> dict[str, dict]:
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


def _current_files(tree: str, *, root: Path = ROOT) -> dict[str, dict]:
    tree_root = root / tree
    try:
        tree_mode = tree_root.lstat().st_mode
    except FileNotFoundError as exc:
        raise AssertionError(f"Missing immutable release tree: {tree}") from exc
    if not stat.S_ISDIR(tree_mode):
        raise AssertionError(f"Immutable release tree root is not a directory: {tree}")

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


def _validate_tree_records(
    tree: str,
    recorded: dict,
    anchored: dict[str, dict],
    observed: dict[str, dict],
) -> None:
    recorded_set, anchored_set, observed_set = set(recorded), set(anchored), set(observed)
    if missing := sorted(recorded_set - observed_set):
        raise AssertionError(f"Deleted from immutable tree {tree}: {missing}")
    if added := sorted(observed_set - recorded_set):
        raise AssertionError(f"Added to immutable tree {tree}: {added}")
    if only_anchor := sorted(anchored_set - recorded_set):
        raise AssertionError(f"Missing anchor paths from immutable manifest {tree}: {only_anchor}")
    if only_manifest := sorted(recorded_set - anchored_set):
        raise AssertionError(f"Unanchored paths in immutable manifest {tree}: {only_manifest}")

    expected_fields = {"bytes", "gitMode", "gitType", "lstatMode", "sha256"}
    for relative in sorted(recorded):
        entry = recorded[relative]
        if not isinstance(entry, dict) or set(entry) != expected_fields:
            raise AssertionError(
                f"Manifest record {tree}/{relative} must contain exactly "
                f"{sorted(expected_fields)}"
            )
        if isinstance(entry["bytes"], bool) or not isinstance(entry["bytes"], int):
            raise AssertionError(f"Manifest byte count is not an integer: {tree}/{relative}")
        if entry["bytes"] < 0:
            raise AssertionError(f"Manifest byte count is negative: {tree}/{relative}")
        if not isinstance(entry["sha256"], str) or not re.fullmatch(
            r"[0-9a-f]{64}", entry["sha256"]
        ):
            raise AssertionError(f"Manifest SHA-256 is invalid: {tree}/{relative}")
        if entry["gitMode"] not in {"100644", "100755"} or entry["gitType"] != "blob":
            raise AssertionError(f"Manifest Git node is not a regular blob: {tree}/{relative}")
        if not isinstance(entry["lstatMode"], str) or not re.fullmatch(
            r"100[0-7]{3}", entry["lstatMode"]
        ):
            raise AssertionError(f"Manifest lstat mode is not a regular file: {tree}/{relative}")

        current = observed[relative]
        if entry["sha256"] != current["sha256"]:
            raise AssertionError(f"Byte change in immutable tree {tree}: {relative}")
        if entry["bytes"] != current["bytes"]:
            raise AssertionError(f"Byte-count change in immutable tree {tree}: {relative}")
        # A fresh checkout applies the local umask, so only the executable bit is comparable;
        # content integrity is carried by the sha256, byte count and git mode checks.
        if (int(entry["lstatMode"], 8) & 0o111 != 0) != (int(current["lstatMode"], 8) & 0o111 != 0):
            raise AssertionError(f"executable-bit change in immutable tree {tree}: {relative}")

        publication = anchored[relative]
        for field in ("sha256", "bytes", "gitMode", "gitType"):
            if entry[field] != publication[field]:
                raise AssertionError(
                    f"Manifest {field} for {tree}/{relative} does not match publication anchor"
                )


def validate_local_references() -> None:
    for page in sorted(ROOT.rglob("*.html")):
        if is_local_build_source(page.relative_to(ROOT)):
            continue
        parser = AssetReferenceParser()
        parser.feed(page.read_text(encoding="utf-8"))
        for reference in parser.references:
            parsed = urlsplit(reference)
            if parsed.scheme or parsed.netloc or reference.startswith("#"):
                continue
            target_text = parsed.path
            if not target_text:
                continue
            if target_text.startswith("/StatePort-Site/"):
                target = (ROOT / target_text[len("/StatePort-Site/"):]).resolve()
            else:
                target = (page.parent / target_text).resolve()
            if ROOT not in target.parents and target != ROOT:
                raise AssertionError(f"Escaping local reference in {page.relative_to(ROOT)}: {reference}")
            if not target.exists():
                raise AssertionError(f"Broken local reference in {page.relative_to(ROOT)}: {reference}")


def css_variable_hex(css: str, variable: str) -> tuple[int, int, int]:
    match = re.search(rf"{re.escape(variable)}\s*:\s*(#[0-9a-fA-F]{{6}})\s*;", css)
    if not match:
        raise AssertionError(f"Expected a six-digit hex value for {variable}")
    value = match.group(1).lstrip("#")
    return tuple(int(value[index : index + 2], 16) for index in range(0, 6, 2))


def relative_luminance(rgb: tuple[int, int, int]) -> float:
    channels = []
    for channel in rgb:
        normalized = channel / 255
        channels.append(
            normalized / 12.92
            if normalized <= 0.04045
            else ((normalized + 0.055) / 1.055) ** 2.4
        )
    return 0.2126 * channels[0] + 0.7152 * channels[1] + 0.0722 * channels[2]


def contrast_ratio(foreground: tuple[int, int, int], background: tuple[int, int, int]) -> float:
    lighter, darker = sorted((relative_luminance(foreground), relative_luminance(background)), reverse=True)
    return (lighter + 0.05) / (darker + 0.05)


def validate_documentation_button_accessibility() -> None:
    css = require("assets/site.css").read_text(encoding="utf-8")
    required_overrides = (
        ".prose a.button {\n  font-weight: 760;\n  text-decoration: none;\n}",
        ".prose a.button--ink,\n.prose a.button--ink:hover {\n  color: var(--white);\n}",
        ".prose a.button--outlined {\n  color: var(--ink);\n}",
        ".prose a.button--outlined:hover {\n  color: var(--white);\n}",
    )
    for override in required_overrides:
        if override not in css:
            raise AssertionError(f"Missing documentation-button override: {override.splitlines()[0]}")
    if css.index(".prose a.button {") <= css.index(".prose a {"):
        raise AssertionError("Documentation-button overrides must follow the generic prose-link rule")
    if ".button--ink {\n  color: var(--white);\n  background: var(--ink);\n}" not in css:
        raise AssertionError("Dark button must declare white text on the ink background")

    focus_visible = re.search(r":focus-visible\s*\{(?P<body>[^}]*)\}", css, re.DOTALL)
    if not focus_visible or "outline:" not in focus_visible.group("body") or "outline-offset:" not in focus_visible.group("body"):
        raise AssertionError("Visible keyboard focus treatment is required")

    white = css_variable_hex(css, "--white")
    for background_variable in ("--ink", "--blue-deep"):
        ratio = contrast_ratio(white, css_variable_hex(css, background_variable))
        if ratio < 4.5:
            raise AssertionError(
                f"White text on {background_variable} fails WCAG AA contrast: {ratio:.2f}:1"
            )


def validate_action_pins() -> None:
    action_reference = re.compile(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+@[0-9a-f]{40}")
    for workflow in sorted((ROOT / ".github" / "workflows").glob("*.y*ml")):
        for line_number, line in enumerate(workflow.read_text(encoding="utf-8").splitlines(), start=1):
            match = re.match(r"\s*uses:\s*([^\s#]+)", line)
            if not match:
                continue
            reference = match.group(1)
            if reference.startswith("./"):
                continue
            if not action_reference.fullmatch(reference):
                raise AssertionError(
                    "Workflow action must use a full immutable commit SHA: "
                    f"{workflow.relative_to(ROOT)}:{line_number}: {reference}"
                )


def validate_pull_request_workflow() -> None:
    workflow_path = ".github/workflows/validate-site-pr.yml"
    workflow = require(workflow_path).read_text(encoding="utf-8")
    required_fragments = (
        "pull_request:",
        "contents: read",
        "runs-on: ubuntu-latest",
        "python3 scripts/validate_repo.py",
        "python3 scripts/check_site_quality.py",
        "PYTHONDONTWRITEBYTECODE=1 python3 -B -m unittest discover -s scripts -p 'test_*.py'",
    )
    for fragment in required_fragments:
        if fragment not in workflow:
            raise AssertionError(f"Expected {fragment!r} in {workflow_path}")
    forbidden_fragments = (
        "pull_request_target",
        "pages: write",
        "id-token: write",
        "deploy-pages",
        "upload-pages-artifact",
    )
    for fragment in forbidden_fragments:
        if fragment in workflow:
            raise AssertionError(f"Draft PR workflow must not contain {fragment!r}")


def validate_paper_diagrams() -> None:
    for page in sorted((ROOT / "papers").glob("stateware-whitepaper-*.html")):
        text = page.read_text(encoding="utf-8")
        if "<pre class=\"mermaid\">" in text:
            raise AssertionError(
                f"Unrendered Mermaid block in {page.relative_to(ROOT)}: "
                "run python3 scripts/render_paper_diagrams.py"
            )
        if "class=\"paper-diagram\"" not in text:
            raise AssertionError(
                f"Expected at least one rendered diagram in {page.relative_to(ROOT)}"
            )


def validate_support_configuration() -> None:
    config = load_config()
    homepage = require("index.html").read_text(encoding="utf-8")
    if homepage != rendered_home(homepage, config):
        raise AssertionError(
            "index.html support blocks are stale; run python3 scripts/render_support.py"
        )

    if support_enabled(config):
        if homepage.count("data-support-link") != 2:
            raise AssertionError("Enabled support requires exactly one homepage and one footer link")
        if homepage.count('target="_blank"') < 2:
            raise AssertionError("Support links must announce and safely open their external destination")
        if homepage.count('rel="external noopener noreferrer"') != 2:
            raise AssertionError("Support links require external, noopener, and noreferrer relations")
        if homepage.count("opens in a new tab") != 2:
            raise AssertionError("Support links must expose new-tab behavior to assistive technology")
    else:
        public_copy = "\n".join(
            page.read_text(encoding="utf-8") for page in ROOT.rglob("*.html")
        )
        if "data-support-link" in homepage or "ko-fi.com" in public_copy.lower():
            raise AssertionError("Unattested support configuration must expose no public Ko-fi link")
        if "data-support-pending" in homepage or "support link is being configured" in homepage.lower():
            raise AssertionError("Fail-closed support must remain hidden instead of exposing a dead end")


def validate_disabled_alpha2_bootstrap() -> None:
    path = "download/0.1.0-alpha.2/install.sh"
    candidate = require(path)
    mode = stat.S_IMODE(candidate.stat().st_mode)
    if mode & 0o111 == 0:
        raise AssertionError(f"Fail-closed bootstrap must remain executable: {path}")
    text = candidate.read_text(encoding="utf-8")
    for fragment in (
        "#!/bin/sh",
        "installation is disabled",
        "known packaged web-image defect",
        "exit 2",
    ):
        if fragment not in text:
            raise AssertionError(f"Expected {fragment!r} in {path}")
    for forbidden in ("curl ", "python3 ", "podman ", "sudo "):
        if forbidden in text:
            raise AssertionError(f"Disabled alpha.2 bootstrap must not execute {forbidden!r}: {path}")


def validate_alpha3_release() -> None:
    release_root = "download/0.1.0-alpha.3"
    expected_files = {
        "release-index.json": "d02709a250369b96c7bf5c39659d9080ff53d0cf0e20d391222fe5c1b0d4ae93",
        "release-index.sigstore.json": "e4fb2c0f274ed88e34a5904c2d85feb3dcc231a7a5d794072fff158a29178208",
        "release-notes.md": "588f0489cc91f09a31686b8949afc2b080fdd2024586c1987d9c504899696260",
        "known-limitations.md": "3fb1d7db8dcf486e1b742dc421791b05af0e8a365119af6910efa6e0dbe1351b",
        "compose.yaml": "27914d57e10c13e34aaddbaf2a66057a15a69d3afa3490faf62c9cb44f54f594",
        "stateport-installer": "33874d373c8949209f81895b4481747fb97f2ab570ddd26e76258c4a2c02e6ab",
        "stateport-updater": "00b1a75a40f37c10505fcec04271ea5231f7cfc8c21fa9c29567277b708f657b",
        "stateport-source.tar": "17f5680c30841b1e831b37df02dca8f03c2c03d265a42633dd525f99bd613398",
    }
    for name, expected in expected_files.items():
        path = require(f"{release_root}/{name}")
        observed = hashlib.sha256(path.read_bytes()).hexdigest()
        if observed != expected:
            raise AssertionError(f"{path.relative_to(ROOT)} digest {observed} != signed {expected}")

    index = json.loads(require(f"{release_root}/release-index.json").read_text(encoding="utf-8"))
    signed = index.get("signed", {})
    if signed.get("release", {}).get("version") != "0.1.0-alpha.3":
        raise AssertionError("alpha.3 release index has the wrong version")
    source = signed.get("source", {})
    for field, expected in ALPHA3_CANONICAL_SOURCE_IDENTITY.items():
        if source.get(field) != expected:
            raise AssertionError(f"alpha.3 release index has the wrong canonical source {field}")
    public_snapshot = source.get("publicSnapshot", {})
    for field, expected in ALPHA3_PUBLIC_SNAPSHOT_IDENTITY.items():
        if public_snapshot.get(field) != expected:
            raise AssertionError(f"alpha.3 release index has the wrong publicSnapshot {field}")
    source_archive = signed.get("artifacts", {}).get("sourceArchive", {})
    if source_archive.get("digest") != f"sha256:{ALPHA3_CURATED_SOURCE_ARCHIVE['sha256']}":
        raise AssertionError("alpha.3 release index has the wrong curated source archive digest")
    if source_archive.get("size") != ALPHA3_CURATED_SOURCE_ARCHIVE["bytes"]:
        raise AssertionError("alpha.3 release index has the wrong curated source archive byte count")
    targets = signed.get("targets", [])
    if not any(target.get("targetId") == "linux-amd64-rootless-podman-quadlet" for target in targets):
        raise AssertionError("alpha.3 release index lacks the portable capability target")
    if len(signed.get("images", [])) != 7:
        raise AssertionError("alpha.3 release index must contain seven images")

    signature_digests = {
        "stateport-api.sigstore.json": "4e4937cbfd4c54d67e5973d7dfbbfd255a0d664b0c85a772b20909aed2854360",
        "stateport-dev-workspace.sigstore.json": "18365379a0611f10b0dc13a136308c19acff5c5b4932673fd1f113429dddaf0c",
        "stateport-execution-host.sigstore.json": "5b24f342d8cfe44d714715dc0961df7bb6744a8039bd6fbdd174e6181c953e7e",
        "stateport-playwright.sigstore.json": "e6ce5bfd8f3d512562a25fb536946178125149494bb7cbb93eecbeb227c09dde",
        "stateport-runner.sigstore.json": "b7afe8b12cc72c0b650d5f73dd32fba0bb6a69dec0ac56621222ce41057baa63",
        "stateport-web.sigstore.json": "f8dd5a29a33d445e4f99552a3faf7529f42494e54145197cf6c7e3a968866966",
        "stateport-worker.sigstore.json": "df5277ebfaf90b34e9a55fc7345813c307231d33c460f1f13f954d7503786d21",
    }
    for name, expected in signature_digests.items():
        path = require(f"{release_root}/signatures/{name}")
        observed = hashlib.sha256(path.read_bytes()).hexdigest()
        if observed != expected:
            raise AssertionError(f"{path.relative_to(ROOT)} is not the indexed signature bundle")

    for name in (
        "public-export-manifest.json",
        "double-build-comparison.json",
        "syft.tool-provenance.json",
        "grype.tool-provenance.json",
        "cosign.tool-provenance.json",
    ):
        require(f"{release_root}/supply-chain/{name}")
    export_manifest = json.loads(
        require(f"{release_root}/supply-chain/public-export-manifest.json").read_text(
            encoding="utf-8"
        )
    )
    classified_files = export_manifest.get("files", [])
    if not any(entry.get("classification") == "public-source" for entry in classified_files):
        raise AssertionError("alpha.3 export manifest lacks AGPL-classified public source")
    if not any(
        entry.get("classification") == "public-documentation" for entry in classified_files
    ):
        raise AssertionError("alpha.3 export manifest lacks CC-BY-classified documentation")
    for entry in classified_files:
        expected_license = {
            "public-source": "AGPL-3.0-or-later",
            "public-documentation": "CC-BY-4.0",
        }.get(entry.get("classification"))
        if expected_license and entry.get("license") != expected_license:
            raise AssertionError(
                f"alpha.3 export license mismatch for {entry.get('path')}: "
                f"expected {expected_license}"
            )
    quadlet_files = list((ROOT / release_root / "quadlet").rglob("materialization.template.json"))
    if len(quadlet_files) != 1:
        raise AssertionError("alpha.3 quadlet bundle must contain one materialization template")

    # The immutable versioned bootstrap retains the original signed-install
    # logic (its bytes are release evidence and must never change).
    versioned = require(f"{release_root}/install.sh")
    if stat.S_IMODE(versioned.stat().st_mode) & 0o111 == 0:
        raise AssertionError(f"Alpha.3 versioned bootstrap must remain executable: {versioned}")
    versioned_text = versioned.read_text(encoding="utf-8")
    for fragment in (
        "linux-amd64-rootless-podman-quadlet",
        "evaluate_linux_host",
        "RELEASE_INDEX_SHA256=\"d02709a250369b96c7bf5c39659d9080ff53d0cf0e20d391222fe5c1b0d4ae93\"",
        "TRUST_KEY_FINGERPRINT=\"sha256:3dca6219e41310c6a95a8189669aacad3198e6c84489946406b8f986e1f4211a\"",
    ):
        if fragment not in versioned_text:
            raise AssertionError(f"Expected {fragment!r} in {versioned}")
    if "all Linux" in versioned_text:
        raise AssertionError(f"Bootstrap must not claim all Linux support: {versioned}")



def validate_current_release() -> None:
    """Bind the active Alpha.16 release to its signed index and exact bytes."""

    release_root = CURRENT_RELEASE_ROOT
    fixed_files = {
        "release-index.json": CURRENT_RELEASE_INDEX_SHA256,
        "release-index.sigstore.json": CURRENT_RELEASE_INDEX_SIGSTORE_SHA256,
        "release-index.signed-payload.json": CURRENT_SIGNED_PAYLOAD_SHA256,
        "stateport-alpha-2026-08-cosign.pub": CURRENT_TRUST_PUBLIC_KEY_SHA256,
        "bootstrap.sh": VERSIONED_BOOTSTRAP_SHA256,
    }
    for name, expected in fixed_files.items():
        path = require(f"{release_root}/{name}")
        observed = hashlib.sha256(path.read_bytes()).hexdigest()
        if observed != expected:
            raise AssertionError(f"{path.relative_to(ROOT)} digest {observed} != {expected}")

    index_path = require(f"{release_root}/release-index.json")
    index = json.loads(index_path.read_text(encoding="utf-8"))
    signed = index.get("signed", {})
    release = signed.get("release", {})
    if release.get("version") != CURRENT_RELEASE_VERSION or release.get("qualification") != "candidate":
        raise AssertionError("the current release must remain an explicitly unqualified candidate")

    signatures = index.get("signatures", [])
    if len(signatures) != 1:
        raise AssertionError("the current release index must carry exactly one index signature")
    signature = signatures[0]
    if signature.get("subjectDigest") != f"sha256:{CURRENT_SIGNED_PAYLOAD_SHA256}":
        raise AssertionError("current signed payload digest is stale")
    if signature.get("bundle", {}).get("digest") != f"sha256:{CURRENT_RELEASE_INDEX_SIGSTORE_SHA256}":
        raise AssertionError("current release-index signature descriptor is stale")
    if signature.get("publicKeyFingerprint") != "sha256:df24c1ccdcf1ecf72da6d8d81ae8b0ffaca8d399826091b107cc4d6905915ea5":
        raise AssertionError("current trust-key fingerprint is stale")

    source = signed.get("source", {})
    for field, expected in CURRENT_CANONICAL_SOURCE_IDENTITY.items():
        if source.get(field) != expected:
            raise AssertionError(f"current release index has the wrong canonical source {field}")
    public_snapshot = source.get("publicSnapshot", {})
    for field, expected in CURRENT_PUBLIC_SNAPSHOT_IDENTITY.items():
        if public_snapshot.get(field) != expected:
            raise AssertionError(f"current release index has the wrong public snapshot {field}")
    for field in ("authorityUrl", "repository"):
        if public_snapshot.get(field) != CURRENT_PUBLIC_SOURCE_URL:
            raise AssertionError(f"current public snapshot {field} is not remotely resolvable")

    targets = signed.get("targets", [])
    if len(targets) != 1 or targets[0].get("targetId") != CURRENT_TARGET_ID:
        raise AssertionError("the current release must name only the exact WSL2 Ubuntu 24.04 target")

    artifact_paths = {
        "compose": "compose.yaml",
        "executionHostProvisioner": "stateport-execution-host-provision",
        "installer": "stateport-installer",
        "knownLimitations": "known-limitations.md",
        "podmanPackageBundle": "stateport-podman-package-bundle.tar",
        "releaseNotes": "release-notes.md",
        "sourceArchive": "stateport-source.tar",
        "updater": "stateport-updater",
    }
    artifacts = signed.get("artifacts", {})
    for artifact_id, name in artifact_paths.items():
        descriptor = artifacts.get(artifact_id, {})
        path = require(f"{release_root}/{name}")
        observed = hashlib.sha256(path.read_bytes()).hexdigest()
        if descriptor.get("digest") != f"sha256:{observed}" or descriptor.get("size") != path.stat().st_size:
            raise AssertionError(f"current artifact descriptor mismatch: {artifact_id}")
    source_archive = artifacts.get("sourceArchive", {})
    if source_archive.get("digest") != f"sha256:{CURRENT_CURATED_SOURCE_ARCHIVE['sha256']}" or source_archive.get("size") != CURRENT_CURATED_SOURCE_ARCHIVE["bytes"]:
        raise AssertionError("current curated source archive identity is stale")

    expected_images = {image_id: f"sha256:{digest}" for image_id, digest in MANIFEST_DIGESTS.items()}
    images = signed.get("images", [])
    if {image.get("imageId"): image.get("digest") for image in images} != expected_images:
        raise AssertionError("Alpha.16 image set is not the signed seven-image set")
    for image in images:
        image_id = image["imageId"]
        digest = expected_images[image_id]
        if image.get("reference") != f"ghcr.io/lennertvhoy/{image_id}@{digest}":
            raise AssertionError(f"current image reference is not public and digest-pinned: {image_id}")
        bundle = image.get("signature", {}).get("bundle", {})
        bundle_path = require(f"{release_root}/signatures/{image_id}.sigstore.json")
        observed = hashlib.sha256(bundle_path.read_bytes()).hexdigest()
        if bundle.get("digest") != f"sha256:{observed}" or bundle.get("size") != bundle_path.stat().st_size:
            raise AssertionError(f"current image signature descriptor mismatch: {image_id}")

    supply_chain_paths = {
        "doubleBuildComparison": "double-build-comparison.json",
        "publicExportManifest": "public-export-manifest.json",
    }
    supply_chain = signed.get("supplyChain", {})
    for evidence_id, name in supply_chain_paths.items():
        descriptor = supply_chain.get(evidence_id, {})
        path = require(f"{release_root}/supply-chain/{name}")
        observed = hashlib.sha256(path.read_bytes()).hexdigest()
        if descriptor.get("digest") != f"sha256:{observed}" or descriptor.get("size") != path.stat().st_size:
            raise AssertionError(f"Alpha.16 supply-chain descriptor mismatch: {evidence_id}")

    predecessor_bundle = ROOT / release_root / "predecessor-bundle/release-index.sigstore.json"
    if not predecessor_bundle.is_file():
        raise AssertionError("Alpha.16 must retain the authenticated Alpha.15 predecessor bundle")
    successor = signed.get("successor", {})
    compatibility = signed.get("compatibility", {})
    predecessor = successor.get("predecessor", {})
    if predecessor.get("formatVersion") != "stateport.release-predecessor/v1":
        raise AssertionError("the current successor contract must identify its authenticated predecessor")
    if compatibility.get("predecessor", {}).get("version") != RETAINED_ALPHA16_PREDECESSOR_VERSION:
        raise AssertionError("current compatibility must identify its authenticated predecessor")
    if compatibility.get("predecessor", {}).get("signedPayloadDigest") != "sha256:3297441598ef7d90d38e2f25eee17654d6393fba7afa7d893940c48f6b07d895":
        raise AssertionError("current compatibility predecessor payload is stale")
    if compatibility.get("rollback", {}).get("supported") is not False:
        raise AssertionError("current rollback must remain explicitly unsupported")

    versioned = require(f"{release_root}/bootstrap.sh")
    mutable_root = "download/0.1.0-alpha.24"
    mutable_versioned = require(f"{mutable_root}/bootstrap.sh")
    mutable = require("download/install.sh")
    for path in (versioned, mutable):
        if stat.S_IMODE(path.stat().st_mode) != 0o755:
            raise AssertionError(f"bootstrap route mode must be exactly 0755: {path}")
    if versioned.stat().st_size != VERSIONED_BOOTSTRAP_SIZE:
        raise AssertionError("Immutable Alpha.16 bootstrap size changed")
    if VERSIONED_BOOTSTRAP_URL != f"https://lennertvhoy.github.io/StatePort-Site/{release_root}/bootstrap.sh":
        raise AssertionError("Immutable Alpha.16 bootstrap URL is stale")
    if mutable.stat().st_size != MUTABLE_BOOTSTRAP_SIZE or mutable.read_bytes() != mutable_versioned.read_bytes():
        raise AssertionError("Mutable bootstrap must equal the versioned Alpha.24 bytes")
    if hashlib.sha256(mutable.read_bytes()).hexdigest() != MUTABLE_BOOTSTRAP_SHA256:
        raise AssertionError("Mutable Alpha.24 bootstrap digest is stale")
    if MUTABLE_BOOTSTRAP_URL != f"https://lennertvhoy.github.io/StatePort-Site/{mutable_root}/bootstrap.sh":
        raise AssertionError("Mutable Alpha.24 bootstrap URL is stale")
    bootstrap = versioned.read_text(encoding="utf-8")
    for fragment in (
        CURRENT_TARGET_ID,
        "RELEASE_ROOT=\"https://lennertvhoy.github.io/StatePort-Site/download/0.1.0-alpha.24\"",
        "PROBE_ROOT=\"https://lennertvhoy.github.io/StatePort-Site/download/alpha24-manifests\"",
        "Windows 11 build 22000 or newer is required.",
        "Ubuntu 24.04 for WSL is required.",
        "WSL2 is required; WSL1 and native Linux are not this release target.",
        "Type install-packages to authorize",
        "Type install-exact to authorize",
    ):
        if fragment not in bootstrap:
            raise AssertionError(f"versioned bootstrap lacks required contract: {fragment}")
    mutable_bootstrap = mutable.read_text(encoding="utf-8")
    for fragment in (
        CURRENT_TARGET_ID,
        "RELEASE_ROOT=\"https://lennertvhoy.github.io/StatePort-Site/download/0.1.0-alpha.24\"",
        "PROBE_ROOT=\"https://lennertvhoy.github.io/StatePort-Site/download/alpha24-manifests\"",
        "Windows 11 build 22000 or newer is required.",
        "Ubuntu 24.04 for WSL is required.",
        "WSL2 is required; WSL1 and native Linux are not this release target.",
        "Type install-packages to authorize",
        "Type install-exact to authorize",
    ):
        if fragment not in mutable_bootstrap:
            raise AssertionError(f"Alpha.24 mutable bootstrap lacks required contract: {fragment}")
    alpha24_index = json.loads(require(f"{mutable_root}/release-index.json").read_text(encoding="utf-8"))
    alpha24_images = {
        image.get("imageId"): image.get("digest")
        for image in alpha24_index.get("signed", {}).get("images", [])
    }
    if not alpha24_images:
        raise AssertionError("Alpha.24 signed index must declare its seven images")
    for image_id, digest in alpha24_images.items():
        manifest = require(f"download/alpha24-manifests/{image_id}.json")
        if hashlib.sha256(manifest.read_bytes()).hexdigest() != str(digest).removeprefix("sha256:"):
            raise AssertionError(f"Alpha.24 manifest does not match the signed index: {image_id}")
    for image_id, expected in MANIFEST_DIGESTS.items():
        manifest = require(f"{CURRENT_MANIFEST_ROOT}/{image_id}.json")
        if hashlib.sha256(manifest.read_bytes()).hexdigest() != expected:
            raise AssertionError(f"current manifest is stale: {image_id}")


def validate_retained_alpha23() -> None:
    """Keep the superseded Alpha.23 tree byte-identical while Alpha.24 is current."""

    release_root = "download/0.1.0-alpha.23"
    fixed_files = {
        "release-index.json": "e6bc7a35d5f6b6c080a7b2e439c51572b07819e7e0c12279d839049c1bd7d696",
        "release-index.sigstore.json": "0975911176b75331383469106e48e68fb00625ec05b334fdc2ee1db88e3527c9",
        "release-index.signed-payload.json": "3297441598ef7d90d38e2f25eee17654d6393fba7afa7d893940c48f6b07d895",
        "bootstrap.sh": "f14c53e5ce596cd81b234f70b23d755aacc9eac9bd2adf3644a251807090d0c8",
        "stateport-alpha-2026-08-cosign.pub": CURRENT_TRUST_PUBLIC_KEY_SHA256,
    }
    for name, expected in fixed_files.items():
        path = require(f"{release_root}/{name}")
        observed = hashlib.sha256(path.read_bytes()).hexdigest()
        if observed != expected:
            raise AssertionError(f"{path.relative_to(ROOT)} digest {observed} != {expected}")

    index = json.loads(require(f"{release_root}/release-index.json").read_text(encoding="utf-8"))
    signed = index.get("signed", {})
    if signed.get("release", {}).get("version") != "0.1.0-alpha.23":
        raise AssertionError("Retained Alpha.23 index has the wrong version")
    source = signed.get("source", {})
    if source.get("commit") != "c549033fc482afc15e903d7df59eb6eb2be8e473":
        raise AssertionError("Retained Alpha.23 canonical source commit changed")
    if source.get("tree") != "64a82d857eb6d0f4fe64043a630d91e708153a21":
        raise AssertionError("Retained Alpha.23 canonical source tree changed")

    retained_manifests = {
        "stateport-api": "2d9a48b2ba80bacc1b73001a3670af4b7892aa8b99491c26c95ad02c8e936f23",
        "stateport-dev-workspace": "77fd9a31f7dcd66722dc5e1253f7bf026ad0c8931224071ae6c26d08fe202da1",
        "stateport-execution-host": "4c66766b8aea81930d98edecec3339724a1b8ec2df3450c7fb54aaeae54d4a92",
        "stateport-playwright": "a8f44acd6d204d14cc2e687847bfee38c29971c7ae5c839ba09db2f9f5c7070c",
        "stateport-runner": "9605809fb64d36bf788ada1441cdee58ddd8a358c54648d650e3cb102b651087",
        "stateport-web": "8d96843125a3d8159e8b90874152d9f357470e85aefceacc2ce7da0c273dec0c",
        "stateport-worker": "a499002d359c520ad7333c9c3b736d9d02988b2b4f2e33f1f35b4c8a873c2276",
    }
    for image_id, expected in retained_manifests.items():
        path = require(f"download/alpha23-manifests/{image_id}.json")
        if hashlib.sha256(path.read_bytes()).hexdigest() != expected:
            raise AssertionError(f"Retained Alpha.23 manifest is stale: {image_id}")


def validate_retained_alpha22() -> None:
    """Keep the superseded Alpha.22 tree byte-identical while a later release is current."""

    release_root = "download/0.1.0-alpha.22"
    fixed_files = {
        "release-index.json": "59872746b3fa7b4eafa17ed64cdebd808d387f7cf282903c3621b3e8f49d196d",
        "release-index.sigstore.json": "61470f8c81f8d0f54899b33b9d501ff3997c1899be8e892aee16ceec8ddd2e7d",
        "release-index.signed-payload.json": "88d965586222920ea697bdff164f861e9c75ff0d80500bb55dd6db09b7be2bb7",
        "bootstrap.sh": "60db0ca4dc590eeadd328c34bd20e1cfe202ac00f066289272fa12229d03db43",
        "stateport-alpha-2026-08-cosign.pub": CURRENT_TRUST_PUBLIC_KEY_SHA256,
    }
    for name, expected in fixed_files.items():
        path = require(f"{release_root}/{name}")
        observed = hashlib.sha256(path.read_bytes()).hexdigest()
        if observed != expected:
            raise AssertionError(f"{path.relative_to(ROOT)} digest {observed} != {expected}")

    index = json.loads(require(f"{release_root}/release-index.json").read_text(encoding="utf-8"))
    signed = index.get("signed", {})
    if signed.get("release", {}).get("version") != "0.1.0-alpha.22":
        raise AssertionError("Retained Alpha.22 index has the wrong version")
    source = signed.get("source", {})
    if source.get("commit") != "0e495cc9517330b3355ad4c8b18f502d1aaf3dfd":
        raise AssertionError("Retained Alpha.22 canonical source commit changed")
    if source.get("tree") != "b7ec1f046f4cfcf93d15be87e531a22f4633b633":
        raise AssertionError("Retained Alpha.22 canonical source tree changed")

    retained_manifests = {
        "stateport-api": "7ea5acf72e199d4b1fd45db20b498eb92806b81b7f44b8b59f20014bcd0bc98d",
        "stateport-dev-workspace": "c76a69d805cf4a6624159adb3368b0b9551e61451ce64d45bb249262bf94463e",
        "stateport-execution-host": "38e899cc4e356e7c71a1a9581ee7857fcb99e179e83a7b01271fd16d2f2987e3",
        "stateport-playwright": "02317c3dc0b1f5674ec5393a6c0a0bfb07e5ea507a5fd73230843fc34ba90e3f",
        "stateport-runner": "a1df6e3dc17518ec706f1bb7ec31521c709a900f01b7e0a8b6f81cc351095986",
        "stateport-web": "9c08fceeed5d18651591c823c96f3a4a28b16a4311dc2749c4dde385cc84270e",
        "stateport-worker": "2278f8507c52cb68d342148357df40ab73f249fd6c866d00429d76bfdbf0427a",
    }
    for image_id, expected in retained_manifests.items():
        path = require(f"download/alpha22-manifests/{image_id}.json")
        if hashlib.sha256(path.read_bytes()).hexdigest() != expected:
            raise AssertionError(f"Retained Alpha.22 manifest is stale: {image_id}")


def validate_retained_alpha21() -> None:
    """Keep the superseded Alpha.21 tree byte-identical while a later release is current."""

    release_root = "download/0.1.0-alpha.21"
    fixed_files = {
        "release-index.json": "78390eaca6da93eddb8ea0f93d90463a36f9d61aa83793d74d8abe59d7710c1f",
        "release-index.sigstore.json": "fd46f071e541d40d3d02dad62e9f287fdc5c02c94e00fa62b4dfd70dbcd16f1e",
        "release-index.signed-payload.json": "899715d27dd86e7c2abbca886e5e5587508200143c79ab4c3efb9306acf959d6",
        "bootstrap.sh": "5fc574f25072f1c801cd40a098126eb230934e8af4f18f8e5c1518955d0cc9e0",
        "stateport-alpha-2026-08-cosign.pub": CURRENT_TRUST_PUBLIC_KEY_SHA256,
    }
    for name, expected in fixed_files.items():
        path = require(f"{release_root}/{name}")
        observed = hashlib.sha256(path.read_bytes()).hexdigest()
        if observed != expected:
            raise AssertionError(f"{path.relative_to(ROOT)} digest {observed} != {expected}")

    index = json.loads(require(f"{release_root}/release-index.json").read_text(encoding="utf-8"))
    signed = index.get("signed", {})
    if signed.get("release", {}).get("version") != "0.1.0-alpha.21":
        raise AssertionError("Retained Alpha.21 index has the wrong version")
    source = signed.get("source", {})
    if source.get("commit") != "aafc79d45572c714ce10078bb57c38ab20e40aeb":
        raise AssertionError("Retained Alpha.21 canonical source commit changed")
    if source.get("tree") != "318a1c21d715473366e7dae6e5b80e571f7f25eb":
        raise AssertionError("Retained Alpha.21 canonical source tree changed")

    retained_manifests = {
        "stateport-api": "520b7d01402fae2dad43d80ff984d6daa2e389ac71d7519a81e617e9627e8779",
        "stateport-dev-workspace": "da91bc358a6a0408ec27be0f4f35b9d0fc22bf49f3346e22cff2bad8e91d3646",
        "stateport-execution-host": "a938b384de1e73574e4369decf9c0de46319329151f10e64f08d87b57e3a44f6",
        "stateport-playwright": "fa2bd392415752e9648f9e541b1d3ec8f5e3656c1107a8f678b49cc0845bcac7",
        "stateport-runner": "61eb0be882a99ec929cc40929a8ff9d5d414c6a7a3e13bf54d20ed3d5c0eaed4",
        "stateport-web": "7d535d2b03b523826e4411b507d56b6e3765284cdd33c6b9eec14e8e5d5ca9ee",
        "stateport-worker": "7407cca5a86b1b96a3ed06d9464c2e4dd18be9955c47fc3c1039e1bf5a04eaea",
    }
    for image_id, expected in retained_manifests.items():
        path = require(f"download/alpha21-manifests/{image_id}.json")
        if hashlib.sha256(path.read_bytes()).hexdigest() != expected:
            raise AssertionError(f"Retained Alpha.21 manifest is stale: {image_id}")


def validate_retained_alpha20() -> None:
    """Keep the superseded Alpha.20 tree byte-identical while a later release is current."""

    release_root = "download/0.1.0-alpha.20"
    fixed_files = {
        "release-index.json": "9401202ca4bb957b7c9549afefb1c8ef712b6bbb1179625b9369833f39d6e5be",
        "release-index.sigstore.json": "013abb5e1bb8ac3ac6d1a9f5230c1078d0fcfa8b609a2bd0aebaabb956cb1720",
        "release-index.signed-payload.json": "ccb324493ca528f060ea04eb0b2b808e6ed3fafeedacb8a483076c723ebc6189",
        "bootstrap.sh": "b83e8376776cd663b6a0aa8098ddde489f0125e033d70e8b1421fb04d1cb8916",
        "stateport-alpha-2026-08-cosign.pub": CURRENT_TRUST_PUBLIC_KEY_SHA256,
    }
    for name, expected in fixed_files.items():
        path = require(f"{release_root}/{name}")
        observed = hashlib.sha256(path.read_bytes()).hexdigest()
        if observed != expected:
            raise AssertionError(f"{path.relative_to(ROOT)} digest {observed} != {expected}")

    index = json.loads(require(f"{release_root}/release-index.json").read_text(encoding="utf-8"))
    signed = index.get("signed", {})
    if signed.get("release", {}).get("version") != "0.1.0-alpha.20":
        raise AssertionError("Retained Alpha.20 index has the wrong version")
    source = signed.get("source", {})
    if source.get("commit") != "65e42e8daf68ddbdc9696f7f56ae2365b4023b0e":
        raise AssertionError("Retained Alpha.20 canonical source commit changed")
    if source.get("tree") != "7fcc41327625a83fc12213907f84364b232332b7":
        raise AssertionError("Retained Alpha.20 canonical source tree changed")

    retained_manifests = {
        "stateport-api": "f183cea32499dd99090a79509f3c826a2058a347d276fa8807b3443808f17941",
        "stateport-dev-workspace": "6979920b4f759afe906300e0218f456f96ebd8bea96c7e087ce0b1c0650d6399",
        "stateport-execution-host": "116aeef45ffbd179223fbf7ede7d8c731e7b246d9cc937e999abacd928b3f5bb",
        "stateport-playwright": "8774d1a1123158514855470392b7037cde1813bb2f63882870602404371510e0",
        "stateport-runner": "b996778e66de235ccda1fb610776a8d2b2892711507502418e64e5a62f3466f2",
        "stateport-web": "84fcdc1928b4cb8892f1d4bb362d885f98153d1398eb5c1ef6ae08d07bc2088f",
        "stateport-worker": "55cc0665e801b5fefce2a5c315f63cfd2c900b16dfd869f43e246ab247a2fe7f",
    }
    for image_id, expected in retained_manifests.items():
        path = require(f"download/alpha20-manifests/{image_id}.json")
        if hashlib.sha256(path.read_bytes()).hexdigest() != expected:
            raise AssertionError(f"Retained Alpha.20 manifest is stale: {image_id}")


def validate_retained_alpha15() -> None:
    """Keep the superseded Alpha.15 tree byte-identical while Alpha.16 is current."""

    release_root = "download/0.1.0-alpha.15"
    fixed_files = {
        "release-index.json": "931cc726628c40cf749e99ee14478dba228478884980d63cd3ce0ce96d817097",
        "release-index.sigstore.json": "56d8761f1bcc23109cef0b20cdbd6adf3b9844cc7c2afb181bd48a16fa9802a7",
        "release-index.signed-payload.json": "66483f166570dea5135b732bd3c31a05d52691d48a3e8ddd94ae793d3654a47d",
        "bootstrap.sh": "a045d3d0c6478bae04b20923fe7e98025e46ea4c6b10f69667cc46852cf3a51f",
        "stateport-alpha-2026-08-cosign.pub": CURRENT_TRUST_PUBLIC_KEY_SHA256,
    }
    for name, expected in fixed_files.items():
        path = require(f"{release_root}/{name}")
        observed = hashlib.sha256(path.read_bytes()).hexdigest()
        if observed != expected:
            raise AssertionError(f"{path.relative_to(ROOT)} digest {observed} != {expected}")

    index = json.loads(require(f"{release_root}/release-index.json").read_text(encoding="utf-8"))
    signed = index.get("signed", {})
    if signed.get("release", {}).get("version") != "0.1.0-alpha.15":
        raise AssertionError("Retained Alpha.15 index has the wrong version")
    source = signed.get("source", {})
    if source.get("commit") != "6f6b6b7b1dd1ef5374883e2229cec351cc8b3cbc":
        raise AssertionError("Retained Alpha.15 canonical source commit changed")
    if source.get("tree") != "0be1aef3c5cfaa09d92588f6e4ac8b5e869c314a":
        raise AssertionError("Retained Alpha.15 canonical source tree changed")
    public_snapshot = source.get("publicSnapshot", {})
    if public_snapshot.get("commit") != "f4badb23696b74d0569668d5cca5ba16626fa4db":
        raise AssertionError("Retained Alpha.15 public source commit changed")
    if public_snapshot.get("tree") != "3e1104e1ea7c615d51b8c4742e1005810c72b8ae":
        raise AssertionError("Retained Alpha.15 public source tree changed")

    retained_manifests = {
        "stateport-api": "507691145e9900022e7be30222a12a34389f12b1855fddc1e6e65f6989314c52",
        "stateport-dev-workspace": "13b4b2c52f26f30c3a42f264ba80fb0bdc476da4b946c4d93878b55b1d3a6a64",
        "stateport-execution-host": "7766a32d32471c48b153bf7ec96401728757460e20fe79c639ac93ec2c4c0d3a",
        "stateport-playwright": "c4b31ba99602d23202f4c8f8ce4995ac025aa4d96143381277a3b28a93deed45",
        "stateport-runner": "1cf5bea27ffed6b909d3384c45d32fb1e728c7dc9000ffdddf8090085b781a81",
        "stateport-web": "fadb99f743acd10971c576e212d74c85a4ae879eba5f4ac3a980cf9156222a5e",
        "stateport-worker": "8930a946988627fa9cebd900b86043460a9e34e5252c7ad2f5601629621694ed",
    }
    for image_id, expected in retained_manifests.items():
        path = require(f"download/alpha15-manifests/{image_id}.json")
        if hashlib.sha256(path.read_bytes()).hexdigest() != expected:
            raise AssertionError(f"Retained Alpha.15 manifest is stale: {image_id}")


def validate_retained_alpha11() -> None:
    """Keep superseded Alpha.11 immutable as the retained predecessor record."""

    release_root = "download/0.1.0-alpha.11"
    fixed_files = {
        "release-index.json": RETAINED_ALPHA11_INDEX_SHA256,
        "install.sh": RETAINED_ALPHA11_BOOTSTRAP_SHA256,
    }
    for name, expected in fixed_files.items():
        path = require(f"{release_root}/{name}")
        observed = hashlib.sha256(path.read_bytes()).hexdigest()
        if observed != expected:
            raise AssertionError(f"{path.relative_to(ROOT)} digest {observed} != {expected}")

    index = json.loads(require(f"{release_root}/release-index.json").read_text(encoding="utf-8"))
    signed = index.get("signed", {})
    if signed.get("release", {}).get("version") != "0.1.0-alpha.11":
        raise AssertionError("Retained Alpha.11 index has the wrong version")
    source = signed.get("source", {})
    for field, expected in RETAINED_ALPHA11_IDENTITY.items():
        if source.get(field) != expected:
            raise AssertionError(f"Retained Alpha.11 index has the wrong canonical source {field}")
    source_archive = signed.get("artifacts", {}).get("sourceArchive", {})
    if source_archive.get("digest") != f"sha256:{RETAINED_ALPHA11_SOURCE_ARCHIVE['sha256']}":
        raise AssertionError("Retained Alpha.11 source archive identity is stale")
    for image_id, expected in RETAINED_ALPHA11_MANIFEST_DIGESTS.items():
        manifest = require(f"download/alpha11-manifests/{image_id}.json")
        if hashlib.sha256(manifest.read_bytes()).hexdigest() != expected:
            raise AssertionError(f"Retained Alpha.11 manifest is stale: {image_id}")

    if (ROOT / release_root / "predecessor-bundle").exists():
        raise AssertionError("Alpha.11 must not invent an unauthenticated predecessor bundle")
    compatibility = signed.get("compatibility", {})
    if compatibility.get("predecessor") is not None or compatibility.get("rollback", {}).get("supported") is not False:
        raise AssertionError("Retained Alpha.11 rollback must remain explicitly unsupported")

    versioned = require(f"{release_root}/install.sh")
    if stat.S_IMODE(versioned.stat().st_mode) != 0o755:
        raise AssertionError(f"Retained Alpha.11 bootstrap must remain executable: {versioned}")
    if versioned.stat().st_size != RETAINED_ALPHA11_BOOTSTRAP_SIZE:
        raise AssertionError("Retained Alpha.11 bootstrap size changed")
    if RETAINED_ALPHA11_BOOTSTRAP_SHA256 != RETAINED_ALPHA11_BOOTSTRAP_SHA256:
        raise AssertionError("Retained Alpha.11 bootstrap digest changed")


def validate_retained_alpha10() -> None:
    """Keep rejected Alpha.10 immutable as the retained predecessor record."""

    release_root = "download/0.1.0-alpha.10"
    fixed_files = {
        "release-index.json": RETAINED_ALPHA10_INDEX_SHA256,
        "release-index.sigstore.json": RETAINED_ALPHA10_INDEX_SIGSTORE_SHA256,
        "install.sh": RETAINED_ALPHA10_BOOTSTRAP_SHA256,
    }
    for name, expected in fixed_files.items():
        path = require(f"{release_root}/{name}")
        observed = hashlib.sha256(path.read_bytes()).hexdigest()
        if observed != expected:
            raise AssertionError(f"{path.relative_to(ROOT)} digest {observed} != {expected}")

    index = json.loads(require(f"{release_root}/release-index.json").read_text(encoding="utf-8"))
    signed = index.get("signed", {})
    if signed.get("release", {}).get("version") != "0.1.0-alpha.10":
        raise AssertionError("Retained Alpha.10 index has the wrong version")
    source = signed.get("source", {})
    for field, expected in RETAINED_ALPHA10_IDENTITY.items():
        if source.get(field) != expected:
            raise AssertionError(f"Retained Alpha.10 index has the wrong canonical source {field}")
    source_archive = signed.get("artifacts", {}).get("sourceArchive", {})
    if source_archive.get("digest") != f"sha256:{RETAINED_ALPHA10_SOURCE_ARCHIVE['sha256']}":
        raise AssertionError("Retained Alpha.10 source archive identity is stale")
    for image_id, expected in RETAINED_ALPHA10_MANIFEST_DIGESTS.items():
        manifest = require(f"download/alpha10-manifests/{image_id}.json")
        if hashlib.sha256(manifest.read_bytes()).hexdigest() != expected:
            raise AssertionError(f"Retained Alpha.10 manifest is stale: {image_id}")
    for image_id, expected in RETAINED_ALPHA5_MANIFEST_DIGESTS.items():
        manifest = require(f"download/alpha5-manifests/{image_id}.json")
        if hashlib.sha256(manifest.read_bytes()).hexdigest() != expected:
            raise AssertionError(f"Retained Alpha.5 manifest is stale: {image_id}")

    if (ROOT / release_root / "predecessor-bundle").exists():
        raise AssertionError("Alpha.10 must not invent an unauthenticated predecessor bundle")
    compatibility = signed.get("compatibility", {})
    if compatibility.get("predecessor") is not None or compatibility.get("rollback", {}).get("supported") is not False:
        raise AssertionError("Retained Alpha.10 rollback must remain explicitly unsupported")

    versioned = require(f"{release_root}/install.sh")
    if stat.S_IMODE(versioned.stat().st_mode) != 0o755:
        raise AssertionError(f"Retained Alpha.10 bootstrap must remain executable: {versioned}")
    if versioned.stat().st_size != RETAINED_ALPHA10_BOOTSTRAP_SIZE:
        raise AssertionError("Retained Alpha.10 bootstrap size changed")
    if RETAINED_ALPHA10_BOOTSTRAP_SHA256 != RETAINED_ALPHA10_BOOTSTRAP_SHA256:
        raise AssertionError("Retained Alpha.10 bootstrap digest changed")



def validate_immutable_release_trees() -> None:
    """Reject node, mode, byte-count, and content drift in signed trees.

    Two independent bindings must both hold: current working-tree bytes match
    the manifest, and the manifest matches the recorded publication-commit
    anchor for each tree. A manifest regenerated from modified bytes fails
    the anchor check even if it matches the modified working tree.
    """
    manifest_path = "config/immutable-release-trees.json"
    manifest = json.loads(require(manifest_path).read_text(encoding="utf-8"))
    if manifest.get("schema") != "stateport-site.immutable-release-trees/v2":
        raise AssertionError(f"{manifest_path} has an unknown schema")
    trees = manifest.get("trees", {})
    expected_roots = set(VALIDATOR_PUBLICATION_ANCHORS)
    if set(trees) != expected_roots:
        raise AssertionError(f"{manifest_path} must cover exactly {sorted(expected_roots)}")
    for tree, payload in trees.items():
        anchor = payload.get("anchor", {}).get("commit")
        if not isinstance(anchor, str) or not re.fullmatch(r"[0-9a-f]{40}", anchor):
            raise AssertionError(f"{manifest_path} tree {tree} lacks an exact anchor commit")
        if anchor != VALIDATOR_PUBLICATION_ANCHORS[tree]:
            raise AssertionError(
                f"{manifest_path} tree {tree} anchor {anchor} is not the verified "
                f"publication commit {VALIDATOR_PUBLICATION_ANCHORS[tree]}"
            )
        recorded = payload.get("files", {})
        if not isinstance(recorded, dict):
            raise AssertionError(f"{manifest_path} tree {tree} files must be an object")
        for relative in recorded:
            if (
                not isinstance(relative, str)
                or not relative
                or relative.startswith("/")
                or ".." in Path(relative).parts
            ):
                raise AssertionError(f"{manifest_path} records an escaping path: {relative}")
        anchored = _anchored_files(tree, anchor)
        observed = _current_files(tree)
        _validate_tree_records(tree, recorded, anchored, observed)


def release_state_block() -> str:
    """ProjectState v6 keeps the active release outcome in one compact state file."""

    text = require("STATE.yaml").read_text(encoding="utf-8")
    if CURRENT_RELEASE_VERSION not in text or "download/install.sh" not in text:
        raise AssertionError(f"STATE.yaml does not bind the active {CURRENT_RELEASE_LABEL} public route")
    return f"  public_route_available: true\n  version: {CURRENT_RELEASE_VERSION}\n"


def mutable_public_pages() -> list[Path]:
    immutable_parts = {Path(root) for root in VALIDATOR_PUBLICATION_ANCHORS}
    pages = []
    for page in sorted(ROOT.rglob("*.html")):
        relative = page.relative_to(ROOT)
        if any(relative == root or root in relative.parents for root in immutable_parts):
            continue
        if is_local_build_source(relative):
            continue
        pages.append(page)
    return pages


def linked_public_markdown_pages() -> set[Path]:
    """Return visitor-linked Markdown files, not private build-source prose."""

    linked: set[Path] = set()
    for page in mutable_public_pages():
        parser = AssetReferenceParser()
        parser.feed(page.read_text(encoding="utf-8"))
        for reference in parser.references:
            parsed = urlsplit(reference)
            if parsed.scheme or parsed.netloc or not parsed.path.endswith(".md"):
                continue
            if parsed.path.startswith("/StatePort-Site/"):
                target = (ROOT / parsed.path[len("/StatePort-Site/"):]).resolve()
            else:
                target = (page.parent / parsed.path).resolve()
            if ROOT in target.parents and target.is_file():
                linked.add(target)
    return linked


def _release_identity_tokens(release_root: str) -> set[str]:
    """Digest and commit tokens that uniquely identify a signed release."""
    index_path = require(f"{release_root}/release-index.json")
    index_bytes = index_path.read_bytes()
    index = json.loads(index_bytes)
    tokens = {hashlib.sha256(index_bytes).hexdigest()}
    signed = index.get("signed", {})
    source = signed.get("source", {})
    for key in ("commit", "tree"):
        if source.get(key):
            tokens.add(source[key])
    tokens.update(re.findall(r"sha256:[0-9a-f]{64}", json.dumps(index)))
    return tokens


def validate_source_disclosures(texts: dict[Path, str]) -> None:
    """Keep technical source files available without crowding primary pages."""

    technical_path = ROOT / "download/technical-release-files.html"
    technical = texts.get(technical_path)
    if technical is None:
        raise AssertionError("Missing technical release files page")
    required_links = (
        "0.1.0-alpha.16/release-index.json",
        "0.1.0-alpha.16/release-index.sigstore.json",
        "0.1.0-alpha.16/stateport-alpha-2026-08-cosign.pub",
        "0.1.0-alpha.16/stateport-source.tar",
        "0.1.0-alpha.16/stateport-podman-package-bundle.tar",
        "0.1.0-alpha.16/supply-chain/public-export-manifest.json",
        "0.1.0-alpha.16/release-notes.md",
        "0.1.0-alpha.16/known-limitations.md",
        "https://github.com/lennertvhoy/StatePort-Source",
    )
    for link in required_links:
        if link not in technical:
            raise AssertionError(f"technical release files page lacks {link!r}")
    for term in ("AGPL-3.0-or-later", "CC-BY-4.0"):
        if term not in technical:
            raise AssertionError(f"technical release files page lacks {term!r}")

    download = texts[ROOT / "download/index.html"]
    if 'href="technical-release-files.html"' not in download:
        raise AssertionError("download/index.html must link to technical release files")

    erratum = texts[ROOT / "download/erratum-alpha3.html"]
    for link in (
        "0.1.0-alpha.3/release-index.json",
        "0.1.0-alpha.3/release-index.sigstore.json",
        "0.1.0-alpha.3/stateport-source.tar",
    ):
        if link not in erratum:
            raise AssertionError(f"Alpha.3 technical page lacks {link!r}")

    stale_source_claims = (
        re.compile(r">\s*not public\s*<", re.IGNORECASE),
        re.compile(r"implementation source(?: itself)? is not public", re.IGNORECASE),
        re.compile(
            r"\b(?:source code|source archive|artifacts?)\s+"
            r"(?:itself\s+)?(?:is|are|remain|remains)\s+"
            r"(?:not public|absent|unavailable)\b",
            re.IGNORECASE,
        ),
        re.compile(r"\bno public (?:source|source archive|artifacts?)\b", re.IGNORECASE),
        re.compile(r"product license (?:is )?not decided", re.IGNORECASE),
        re.compile(
            r"\blicens(?:e|ing)\s+(?:is\s+)?(?:not decided|undecided)\b",
            re.IGNORECASE,
        ),
        re.compile(r"public source release,\s*licensing decision,\s*artifacts", re.IGNORECASE),
        re.compile(
            r"\b(?:source|artifacts?|licens(?:e|ing))\s+"
            r"(?:remain|remains|are|is)\s+(?:absent|unavailable|undecided)\b",
            re.IGNORECASE,
        ),
    )
    for path, text in texts.items():
        for pattern in stale_source_claims:
            if pattern.search(text):
                raise AssertionError(
                    f"Stale pre-publication source or license copy in {path.relative_to(ROOT)}: "
                    f"{pattern.pattern}"
                )


def validate_release_semantics() -> None:
    """Reject mutable-surface claims that contradict canonical release truth."""
    release_block = release_state_block()
    route_available = re.search(r"^  public_route_available: true\s*$", release_block, re.MULTILINE)
    if not route_available:
        raise AssertionError(
            f"STATE.yaml must bind the published {CURRENT_RELEASE_LABEL} route"
        )

    pages = mutable_public_pages()
    texts = {page: page.read_text(encoding="utf-8") for page in pages}
    current_surfaces = (
        "index.html",
        "download/index.html",
        "docs/index.html",
        "docs/getting-started.html",
        "docs/templates.html",
        "docs/study-state.html",
        "docs/platform-support.html",
        "docs/limitations.html",
        "docs/updates.html",
        "docs/evidence-and-roadmap.html",
        "download/technical-release-files.html",
        "releases/index.html",
    )
    current_release_claim = re.compile(
        r"\b(?:current|active|available|install(?:able|ation)?|supported|candidate)\b",
        re.IGNORECASE,
    )
    historical_marker = re.compile(
        r"\b(?:historical|superseded|rejected|defective|inspection|out of date|"
        r"not the current|earlier|old|known bugs)\b",
        re.IGNORECASE,
    )
    for surface in current_surfaces:
        surface_text = require(surface).read_text(encoding="utf-8")
        if CURRENT_RELEASE_LABEL.lower() not in surface_text.lower() and CURRENT_RELEASE_VERSION not in surface_text:
            raise AssertionError(f"{surface} must identify {CURRENT_RELEASE_LABEL} as the current release")
        for line in surface_text.splitlines():
            if not current_release_claim.search(line):
                continue
            if not re.search(r"\balpha[ .-]?(?:12|13|14)\b", line, re.IGNORECASE):
                continue
            if historical_marker.search(line):
                continue
            raise AssertionError(
                f"{surface} presents a superseded Alpha.12/13/14 release as current: {line.strip()}"
            )
    pipe_to_shell = re.compile(r"(?:curl|wget)\s[^<\n]*\|\s*(?:/bin/)?sh\b")
    for page, text in texts.items():
        relative = page.relative_to(ROOT)
        if pipe_to_shell.search(text):
            raise AssertionError(f"pipe-to-shell promotion is forbidden on {relative}")

    download = texts[ROOT / "download/index.html"]
    if INSTALLER_STATUS not in download:
        raise AssertionError(f"download/index.html lacks {CURRENT_RELEASE_LABEL} installer status {INSTALLER_STATUS!r}")
    if "download/install.sh" not in download:
        raise AssertionError("download/index.html must show the install command with download/install.sh")

    launcher = require("download/install.sh")
    launcher_sha256 = hashlib.sha256(launcher.read_bytes()).hexdigest()
    if launcher_sha256 not in download:
        raise AssertionError(
            "download/index.html must display the SHA-256 of download/install.sh "
            f"({launcher_sha256})"
        )
    for page in ("launch/README.md", "launch/first-comment.md"):
        launch_text = require(page).read_text(encoding="utf-8")
        if launcher_sha256 not in launch_text:
            raise AssertionError(f"{page} must quote the SHA-256 of download/install.sh ({launcher_sha256})")
    if stat.S_IMODE(launcher.stat().st_mode) != 0o755:
        raise AssertionError(f"{CURRENT_RELEASE_LABEL} mutable bootstrap route must remain executable")
    syntax = subprocess.run(
        ["/bin/sh", "-n", str(launcher)],
        check=False,
        capture_output=True,
        env={"LC_ALL": "C", "PATH": os.environ.get("PATH", "")},
        timeout=5,
    )
    if syntax.returncode != 0:
        raise AssertionError(f"{CURRENT_RELEASE_LABEL} mutable bootstrap must pass shell syntax check")

    for surface in ("index.html", "download/index.html", "releases/index.html", "docs/limitations.html"):
        text = texts[ROOT / surface].lower()
        for marker in (CURRENT_RELEASE_LABEL.lower(), "early alpha"):
            if marker not in text:
                raise AssertionError(f"{surface} must disclose current {CURRENT_RELEASE_LABEL} boundary {marker!r}")
    if "erratum-alpha3.html" not in texts[ROOT / "download/index.html"]:
        raise AssertionError("download/index.html must retain the historical alpha.3 erratum")

    validate_source_disclosures(texts)

    state_files = ["PROJECT.md", "STATE.yaml"]
    stale_pages_claims = (
        re.compile(r"github actions deploys? (?:the|this|our)?\s*site", re.IGNORECASE),
        re.compile(r"deploy(?:s|ed|ment)? (?:automatically )?on every push", re.IGNORECASE),
        re.compile(r"every push (?:to main )?(?:triggers|deploys|publishes)", re.IGNORECASE),
    )
    for name in state_files:
        text = require(name).read_text(encoding="utf-8")
        for pattern in stale_pages_claims:
            if pattern.search(text):
                raise AssertionError(f"Stale Pages provider claim in {name}: {pattern.pattern}")
    for page, text in texts.items():
        for pattern in stale_pages_claims:
            if pattern.search(text):
                raise AssertionError(
                    f"Stale Pages provider claim in {page.relative_to(ROOT)}: {pattern.pattern}"
                )
    alpha2_tokens = _release_identity_tokens("download/0.1.0-alpha.2")
    alpha3_tokens = _release_identity_tokens("download/0.1.0-alpha.3")
    alpha5_tokens = _release_identity_tokens("download/0.1.0-alpha.5")
    alpha6_tokens = _release_identity_tokens("download/0.1.0-alpha.6")
    alpha7_tokens = _release_identity_tokens("download/0.1.0-alpha.7")
    alpha10_tokens = _release_identity_tokens("download/0.1.0-alpha.10")
    alpha11_tokens = _release_identity_tokens("download/0.1.0-alpha.11")
    alpha12_tokens = _release_identity_tokens("download/0.1.0-alpha.12")
    alpha15_tokens = _release_identity_tokens("download/0.1.0-alpha.15")
    alpha16_tokens = _release_identity_tokens(CURRENT_RELEASE_ROOT)
    release_tokens = {"2": alpha2_tokens, "3": alpha3_tokens, "5": alpha5_tokens, "6": alpha6_tokens, "7": alpha7_tokens, "10": alpha10_tokens, "11": alpha11_tokens, "12": alpha12_tokens, "15": alpha15_tokens, "16": alpha16_tokens}
    unique_tokens = {
        version: tokens - set().union(*(other for key, other in release_tokens.items() if key != version))
        for version, tokens in release_tokens.items()
    }
    labels = {
        version: re.compile(rf"\balpha[ .-]?{version}\b|\b0\.1\.0-alpha\.{version}\b", re.IGNORECASE)
        for version in release_tokens
    }
    for page, text in texts.items():
        relative = page.relative_to(ROOT)
        for line in text.splitlines():
            for version, tokens in unique_tokens.items():
                if not any(token in line for token in tokens):
                    continue
                for other_version, label in labels.items():
                    if other_version != version and label.search(line):
                        raise AssertionError(
                            f"alpha.{version} identity attributed to alpha.{other_version} "
                            f"in {relative}: {line.strip()[:120]}"
                        )


def validate_asset_cache_keys() -> None:
    """Shared cache-busted assets carry one identical ?v= key on every page.

    The frozen brief requires site.css, site-enhancements.css, and the site.js
    script tag to move in lockstep under a single cache version, so a deploy
    can never serve a mixed-generation page.
    """
    assets = ("site.css", "site-enhancements.css", "site.js")
    keys_by_asset: dict[str, set[str]] = {asset: set() for asset in assets}
    for page in mutable_public_pages():
        text = page.read_text(encoding="utf-8")
        for asset in assets:
            keys_by_asset[asset].update(
                re.findall(rf"{re.escape(asset)}\?v=([0-9A-Za-z-]+)", text)
            )
    shared: set[str] = set()
    for asset, keys in keys_by_asset.items():
        if len(keys) > 1:
            raise AssertionError(f"{asset} cache keys diverge across pages: {sorted(keys)}")
        shared |= keys
    if len(shared) != 1:
        raise AssertionError(
            "site.css, site-enhancements.css, and site.js must share one cache key: "
            f"{sorted(shared)}"
        )
    shared_key = next(iter(shared))
    for page in mutable_public_pages():
        text = page.read_text(encoding="utf-8")
        for asset in assets:
            references = re.findall(
                rf'(?:href|src)="([^"]*{re.escape(asset)}\?v=([0-9A-Za-z-]+))"',
                text,
            )
            if len(references) != 1:
                raise AssertionError(
                    f"{page.relative_to(ROOT)}: expected exactly one keyed {asset} reference"
                )
            if references[0][1] != shared_key:
                raise AssertionError(
                    f"{page.relative_to(ROOT)}: {asset} does not use the shared cache key"
                )


def validate_pages_provider_truth() -> None:
    """Legacy Pages build is the provider; the custom workflow is manual-only."""
    readme = require("README.md").read_text(encoding="utf-8")
    stale_readme_claims = (
        re.compile(r"pushes?\s+to\s+[`'\"]?main[`'\"]?\s+invoke", re.IGNORECASE),
        re.compile(r"invoke[^.\n]*deploy-pages\.yml", re.IGNORECASE),
        re.compile(r"deploy-pages\.yml[^.\n]*(?:on every push|on push|automatically)", re.IGNORECASE),
    )
    for pattern in stale_readme_claims:
        if pattern.search(readme):
            raise AssertionError(
                "README.md must not claim pushes invoke the custom Pages workflow: "
                f"{pattern.pattern}"
            )
    for truth in ("legacy", "manual-only"):
        if not re.search(rf"\b{re.escape(truth)}\b", readme, re.IGNORECASE):
            raise AssertionError(
                f"README.md must record the Pages provider truth containing {truth!r}"
            )

    workflow_path = ".github/workflows/deploy-pages.yml"
    workflow = require(workflow_path).read_text(encoding="utf-8")
    if "workflow_dispatch" not in workflow:
        raise AssertionError(f"{workflow_path} must remain manually dispatched")
    uncommented = "\n".join(line.split("#", 1)[0] for line in workflow.splitlines())
    if re.search(r"(?m)^\s*push\s*:", uncommented) or re.search(
        r"(?m)^on:\s*\[[^\]]*\bpush\b", uncommented
    ):
        raise AssertionError(f"{workflow_path} must not run on push; it is manual-only")


def validate_projectstate_v6() -> None:
    """Run the v6 gate without turning a pending native journey into a false pass."""

    errors, blockers, warnings = validate_projectstate(ROOT)
    if errors:
        detail = "; ".join(errors)
        raise AssertionError(f"ProjectState v6 gate failed: {detail}")
    for warning in warnings:
        print(f"ProjectState v6 warning: {warning}")
    for blocker in blockers:
        print(f"ProjectState v6 outcome pending: {blocker}")


def main() -> None:
    validate_projectstate_v6()
    validate_brand_asset_bytes()
    validate_mascot_size_contract()
    required = (
        "AGENTS.md",
        "PROJECT.md",
        "STATE.yaml",
        "evidence/alpha16-public-install-001/summary.md",
        "scripts/projectstate_gate.py",
        "SUPPORT_SETUP.md",
        "config/support.json",
        "index.html",
        "404.html",
        "docs/index.html",
        "docs/getting-started.html",
        "docs/foundations.html",
        "docs/model.html",
        "docs/lifecycle.html",
        "docs/governance.html",
        "docs/security-and-privacy.html",
        "docs/hosts-and-portability.html",
        "docs/platform-support.html",
        "docs/evidence-and-roadmap.html",
        "docs/reference.html",
        "docs/prototype-walkthrough.html",
        "docs/agent-kits.html",
        "docs/limitations.html",
        "tutorials/index.html",
        "tutorials/first-application.html",
        "tutorials/reading-a-receipt.html",
        "releases/index.html",
        "download/index.html",
        "download/technical-release-files.html",
        "download/erratum-alpha3.html",
        "download/install.sh",
        "download/0.1.0-alpha.16/bootstrap.sh",
        "download/alpha16-manifests/stateport-api.json",
        "download/0.1.0-alpha.2/install.sh",
        "download/0.1.0-alpha.3/install.sh",
        "download/0.1.0-alpha.5/install.sh",
        "download/0.1.0-alpha.7/install.sh",
        "download/0.1.0-alpha.10/install.sh",
        "download/0.1.0-alpha.11/install.sh",
        "download/0.1.0-alpha.12/install.sh",
        "assets/site.css",
        "assets/site.js",
        "assets/stateport-mascot-block-arch-dark.svg",
        "assets/stateport-mascot-block-arch-light.svg",
        "assets/favicon-block-arch.svg",
        "assets/media/stateport-overview.mp4",
        "assets/media/stateport-overview.vtt",
        "assets/media/stateport-overview-poster.png",
        "assets/media/stateport-social-card.png",
        "assets/media/stateport-hero-preview.png",
        "assets/media/frame-conversation.png",
        "assets/media/frame-result.png",
        "assets/media/frame-mobile.png",
        "papers/stateware-whitepaper-public-v1.1.md",
        "papers/stateware-whitepaper-public-v1.1.html",
        "papers/assets/stateware-applications-home.png",
        "papers/assets/stateware-conversation.png",
        "papers/assets/stateware-approvals.png",
        ".github/workflows/deploy-pages.yml",
        ".github/workflows/validate-site-pr.yml",
        "scripts/check_site_quality.py",
        "scripts/install_transport.py",
        "scripts/build_immutable_manifest.py",
        "scripts/render_paper_diagrams.py",
        "scripts/render_support.py",
        "scripts/test_render_support.py",
        "scripts/test_containment.py",
        "config/mermaid-theme.json",
        "config/immutable-release-trees.json",
    )
    for path in required:
        require(path)

    require_text("AGENTS.md", "projectstate-template-v6")
    require_text("PROJECT.md", "Alpha.16")
    require_text("STATE.yaml", "0.1.0-alpha.16")
    require_text("evidence/alpha16-public-install-001/summary.md", "## Primary journey")
    require_text("index.html", "StatePort")
    require_text("index.html", "See StatePort in 19 seconds")
    require_text("docs/prototype-walkthrough.html", "Development preview")
    require_text("docs/agent-kits.html", "Early direction")
    require_text("docs/platform-support.html", "Alpha.16 requirements")
    require_text("papers/stateware-whitepaper-public-v1.1.html", "Publication note")
    require_text("releases/index.html", INSTALLER_STATUS)
    require_text("releases/index.html", "Do not install Alpha 2 or Alpha 3")
    require_text("docs/limitations.html", INSTALLER_STATUS)
    require_text(".github/workflows/deploy-pages.yml", "actions/deploy-pages@d6db90164ac5ed86f2b6aed7e0febac5b3c0c03e")

    public_copy = "\n".join(
        page.read_text(encoding="utf-8") for page in ROOT.rglob("*.html")
    )
    if re.search(r"github\.com/lennertvhoy/StatePort(?:\.git)?(?:[/?#\"'<]|$)", public_copy):
        raise AssertionError(
            "Public pages must not link to the private implementation repository "
            "(lennertvhoy/StatePort); the public site repository (StatePort-Site) is allowed"
        )

    validate_local_references()
    validate_active_favicons()
    validate_documentation_button_accessibility()
    validate_paper_diagrams()
    validate_action_pins()
    validate_pull_request_workflow()
    validate_support_configuration()
    validate_disabled_alpha2_bootstrap()
    validate_alpha3_release()
    validate_retained_alpha10()
    validate_retained_alpha11()
    validate_retained_alpha15()
    validate_retained_alpha20()
    validate_retained_alpha21()
    validate_retained_alpha22()
    validate_retained_alpha23()
    validate_current_release()
    validate_immutable_release_trees()
    validate_release_semantics()
    validate_asset_cache_keys()
    validate_pages_provider_truth()
    validate_local_media_source_manifest()
    print("StatePort Site validation: OK")


if __name__ == "__main__":
    main()
