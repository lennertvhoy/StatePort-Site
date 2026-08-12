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

from render_support import load_config, rendered_home, support_enabled


ROOT = Path(__file__).resolve().parents[1]

# These publication anchors are intentionally duplicated here instead of being
# imported from build_immutable_manifest.py. The validator is an independent
# policy check over both the generator and its output.
VALIDATOR_PUBLICATION_ANCHORS = {
    "download/0.1.0-alpha.2": "4043534a9a1d56c51c3d47d0906e0520963af79c",
    "download/0.1.0-alpha.3": "52b42dd47a11510220f33690075f1b6773f6a889",
}

CANONICAL_SOURCE_IDENTITY = {
    "commit": "fa4ea4b7f08e78669e194c204b59206ab109a02f",
    "tree": "aec60303045e7a9c8255b941c761d904af85ec10",
}
PUBLIC_SNAPSHOT_IDENTITY = {
    "commit": "43d6b4491b962c963a0ecafc060e0dfc7e334dc0",
    "tree": "3bbe46db14a7c929e6f0a17ca153ec686192aa51",
}
CURATED_SOURCE_ARCHIVE = {
    "bytes": 20_305_920,
    "sha256": "17f5680c30841b1e831b37df02dca8f03c2c03d265a42633dd525f99bd613398",
}

MUTABLE_DISABLED_BOOTSTRAP = """#!/bin/sh
printf '%s\\n' \\
  'StatePort v0.1.0-alpha.3 installation is disabled.' \\
  '' \\
  'The signed candidate is byte-intact, but its freshness evidence has expired' \\
  'and known installer and runtime defects require a successor release.' \\
  'No installation command is executed by this disabled bootstrap.' \\
  '' \\
  'Wait for a corrected, rebuilt, and re-signed successor candidate.' \\
  'Erratum: https://lennertvhoy.github.io/StatePort-Site/download/erratum-alpha3.html' >&2
exit 2
"""
MUTABLE_DISABLED_BOOTSTRAP_STRUCTURE = re.compile(
    r"\A#!/bin/sh\n"
    r"printf '%s\\n' \\\n"
    r"(?:  '[^'\r\n]*' \\\n)*"
    r"  '[^'\r\n]*' >&2\n"
    r"exit 2\n\Z"
)

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
MASCOT_SIZE_CONTRACT = {"header": (105, 105), "footer": (85, 85)}
OVERVIEW_MP4_SHA256 = "81e16caf22fa6a7d59b7443939dd0bd6f5c66be583567a939c413131440acfe2"


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
    """Keep active header/footer mascot artwork at the 125% visual contract."""

    css = require("assets/site.css").read_text(encoding="utf-8")
    if "--mascot-header-size: clamp(55px, 5.625vw, 105px)" not in css:
        raise AssertionError("header mascot token is stale")
    if "--mascot-footer-size: clamp(55px, 5vw, 85px)" not in css:
        raise AssertionError("footer mascot token is stale")
    favicon = require("assets/favicon-block-arch.svg").read_text(encoding="utf-8")
    if 'viewBox="24 21 464 464"' not in favicon:
        raise AssertionError("fixed mascot canvas artwork is not at the 125% contract")
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
        if entry["lstatMode"] != current["lstatMode"]:
            raise AssertionError(f"lstat mode change in immutable tree {tree}: {relative}")

        publication = anchored[relative]
        for field in ("sha256", "bytes", "gitMode", "gitType"):
            if entry[field] != publication[field]:
                raise AssertionError(
                    f"Manifest {field} for {tree}/{relative} does not match publication anchor"
                )


def validate_disabled_bootstrap_program(data: bytes) -> None:
    expected = MUTABLE_DISABLED_BOOTSTRAP.encode("utf-8")
    try:
        text = data.decode("utf-8", errors="strict")
    except UnicodeDecodeError as exc:
        raise AssertionError("Disabled bootstrap must be exact UTF-8 text") from exc
    if not MUTABLE_DISABLED_BOOTSTRAP_STRUCTURE.fullmatch(text):
        raise AssertionError(
            "Disabled bootstrap may contain only one builtin printf followed by builtin exit 2"
        )
    if data != expected:
        raise AssertionError("Disabled bootstrap differs from the exact pinned fail-closed program")


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
    for page in sorted((ROOT / "papers").glob("*.html")):
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
    for field, expected in CANONICAL_SOURCE_IDENTITY.items():
        if source.get(field) != expected:
            raise AssertionError(f"alpha.3 release index has the wrong canonical source {field}")
    public_snapshot = source.get("publicSnapshot", {})
    for field, expected in PUBLIC_SNAPSHOT_IDENTITY.items():
        if public_snapshot.get(field) != expected:
            raise AssertionError(f"alpha.3 release index has the wrong publicSnapshot {field}")
    source_archive = signed.get("artifacts", {}).get("sourceArchive", {})
    if source_archive.get("digest") != f"sha256:{CURATED_SOURCE_ARCHIVE['sha256']}":
        raise AssertionError("alpha.3 release index has the wrong curated source archive digest")
    if source_archive.get("size") != CURATED_SOURCE_ARCHIVE["bytes"]:
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

    # The mutable convenience entry point is an exact fail-closed program. Its
    # only commands are shell builtins: one printf to stderr and exit 2.
    mutable_path = "download/install.sh"
    mutable = require(mutable_path)
    mutable_mode = mutable.lstat().st_mode
    if not stat.S_ISREG(mutable_mode):
        raise AssertionError(f"Fail-closed bootstrap must be a regular file: {mutable_path}")
    if stat.S_IMODE(mutable_mode) != 0o755:
        raise AssertionError(f"Fail-closed bootstrap mode must remain exactly 0755: {mutable_path}")
    validate_disabled_bootstrap_program(mutable.read_bytes())


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
    text = require("PROJECT_STATE.yaml").read_text(encoding="utf-8")
    match = re.search(r"^release:\n(?P<body>(?: {2,}.*\n?)*)", text, re.MULTILINE)
    if not match:
        raise AssertionError("PROJECT_STATE.yaml lacks a release: block")
    return match.group("body")


def mutable_public_pages() -> list[Path]:
    immutable_parts = {Path("download/0.1.0-alpha.2"), Path("download/0.1.0-alpha.3")}
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
    """Keep private Git, publicSnapshot, and archive identities distinct."""

    disclosure_surfaces = (
        "index.html",
        "download/index.html",
        "download/erratum-alpha3.html",
        "releases/index.html",
        "docs/evidence-and-roadmap.html",
        "docs/limitations.html",
    )
    common_terms = (
        "canonical development git",
        "private",
        "publicsnapshot",
        "not remotely resolvable",
        "curated alpha.3 source archive",
        "agpl-3.0-or-later",
        "cc-by-4.0",
    )
    for surface in disclosure_surfaces:
        text = texts[ROOT / surface].lower()
        for term in common_terms:
            if term not in text:
                raise AssertionError(f"{surface} must distinguish source status with {term!r}")
        semantic_patterns = (
            r"curated alpha\.3 source archive.{0,120}\bpublic\b",
            r"canonical development git.{0,240}\bprivate\b",
            r"publicsnapshot.{0,800}not remotely resolvable",
            r"code and statespec artifacts.{0,160}agpl-3\.0-or-later",
            r"documentation.{0,120}cc-by-4\.0",
        )
        for pattern in semantic_patterns:
            if not re.search(pattern, text, re.DOTALL):
                raise AssertionError(
                    f"{surface} conflates or omits a source/license relationship: {pattern}"
                )

    identity_tokens = (
        *CANONICAL_SOURCE_IDENTITY.values(),
        *PUBLIC_SNAPSHOT_IDENTITY.values(),
        CURATED_SOURCE_ARCHIVE["sha256"],
    )
    for surface in ("download/index.html", "download/erratum-alpha3.html"):
        text = texts[ROOT / surface]
        for token in identity_tokens:
            if token not in text:
                raise AssertionError(f"{surface} must bind the exact source identity {token!r}")

    download_text = texts[ROOT / "download/index.html"]
    download_labels = {
        "<dt>Canonical development Git</dt>": tuple(CANONICAL_SOURCE_IDENTITY.values()),
        "<dt>Signed <code>publicSnapshot</code> Git identity</dt>": tuple(
            PUBLIC_SNAPSHOT_IDENTITY.values()
        ),
        "<dt>Public curated source archive</dt>": (CURATED_SOURCE_ARCHIVE["sha256"],),
    }
    all_identity_tokens = set(identity_tokens)
    for label, expected_tokens in download_labels.items():
        match = re.search(
            rf"{re.escape(label)}\s*<dd>(?P<body>.*?)</dd>",
            download_text,
            re.DOTALL,
        )
        if not match:
            raise AssertionError(f"download/index.html must keep a separate {label}")
        block = match.group("body")
        for token in expected_tokens:
            if token not in block:
                raise AssertionError(f"{label} is not bound to {token}")
        forbidden_tokens = all_identity_tokens - set(expected_tokens)
        if conflated := sorted(token for token in forbidden_tokens if token in block):
            raise AssertionError(f"{label} conflates separate source identities: {conflated}")

    erratum_text = texts[ROOT / "download/erratum-alpha3.html"]
    erratum_blocks = (
        (
            r"<li>The <strong>canonical development Git repository is private</strong>.*?</li>",
            tuple(CANONICAL_SOURCE_IDENTITY.values()),
        ),
        (
            r"<li>The release index separately records a <strong>signed "
            r"<code>publicSnapshot</code> Git identity</strong>.*?</li>",
            tuple(PUBLIC_SNAPSHOT_IDENTITY.values()),
        ),
        (
            r"<li>What <em>is</em> publicly distributed: the curated alpha\.3 "
            r"source archive.*?</li>",
            (CURATED_SOURCE_ARCHIVE["sha256"],),
        ),
    )
    for pattern, expected_tokens in erratum_blocks:
        match = re.search(pattern, erratum_text, re.DOTALL)
        if not match:
            raise AssertionError("erratum-alpha3.html must keep three separate source disclosures")
        block = match.group(0)
        for token in expected_tokens:
            if token not in block:
                raise AssertionError(f"erratum source disclosure is not bound to {token}")
        forbidden_tokens = all_identity_tokens - set(expected_tokens)
        if conflated := sorted(token for token in forbidden_tokens if token in block):
            raise AssertionError(
                f"erratum source disclosure conflates separate identities: {conflated}"
            )

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
    for surface in disclosure_surfaces:
        text = texts[ROOT / surface]
        for pattern in stale_source_claims:
            if pattern.search(text):
                raise AssertionError(
                    f"Stale pre-publication source or license copy in {surface}: "
                    f"{pattern.pattern}"
                )


def validate_release_semantics() -> None:
    """Reject mutable-surface claims that contradict canonical release truth."""
    release_block = release_state_block()
    install_disabled = re.search(r"^  installation_enabled: false\s*$", release_block, re.MULTILINE)
    known_defective = re.search(r"^  known_defective: true\s*$", release_block, re.MULTILINE)
    if not install_disabled or not known_defective:
        raise AssertionError(
            "PROJECT_STATE.yaml release block must record installation_enabled: false "
            "and known_defective: true for the current candidate"
        )

    pages = mutable_public_pages()
    texts = {page: page.read_text(encoding="utf-8") for page in pages}
    command_pattern = re.compile(r"curl\s[^<\n]*install\.sh")
    installable_claim = re.compile(r"you can (?:download and )?install", re.IGNORECASE)
    for page, text in texts.items():
        relative = page.relative_to(ROOT)
        if command_pattern.search(text):
            raise AssertionError(
                f"install-disabled release still promoted with a curl install command in {relative}"
            )
        if installable_claim.search(text):
            raise AssertionError(
                f"known-defective release described as currently installable in {relative}"
            )
        for promotion in (
            'data-label="One-line install"',
            "Install StatePort on Linux",
            "with one command",
        ):
            if promotion in text:
                raise AssertionError(
                    f"retired one-line install framing still promoted in {relative}: {promotion!r}"
                )

    disabled_marker = "installation is currently disabled"
    for surface in ("index.html", "download/index.html", "releases/index.html", "docs/limitations.html"):
        if disabled_marker not in texts[ROOT / surface].lower():
            raise AssertionError(f"{surface} must plainly state {disabled_marker!r}")
    erratum = ROOT / "download/erratum-alpha3.html"
    if "download/erratum-alpha3.html" not in texts[ROOT / "index.html"]:
        raise AssertionError("index.html must link the alpha.3 erratum")
    if "erratum-alpha3.html" not in texts[ROOT / "download/index.html"]:
        raise AssertionError("download/index.html must link the alpha.3 erratum")

    validate_source_disclosures(texts)

    state_files = ["STATUS.md", "PROJECT_STATE.yaml", "NEXT_ACTIONS.md"]
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
    state_text = require("PROJECT_STATE.yaml").read_text(encoding="utf-8")
    if "build_type: legacy" not in state_text:
        raise AssertionError("PROJECT_STATE.yaml must record the legacy Pages build_type")

    alpha2_tokens = _release_identity_tokens("download/0.1.0-alpha.2")
    alpha3_tokens = _release_identity_tokens("download/0.1.0-alpha.3")
    alpha2_only = alpha2_tokens - alpha3_tokens
    alpha3_only = alpha3_tokens - alpha2_tokens
    alpha2_label = re.compile(r"\balpha[ .-]?2\b|\b0\.1\.0-alpha\.2\b", re.IGNORECASE)
    alpha3_label = re.compile(r"\balpha[ .-]?3\b|\b0\.1\.0-alpha\.3\b", re.IGNORECASE)
    for page, text in texts.items():
        relative = page.relative_to(ROOT)
        for line in text.splitlines():
            has_alpha2_token = any(token in line for token in alpha2_only)
            has_alpha3_token = any(token in line for token in alpha3_only)
            if has_alpha2_token and (has_alpha3_token or alpha3_label.search(line)):
                raise AssertionError(f"alpha.2 identity attributed to alpha.3 in {relative}: {line.strip()[:120]}")
            if has_alpha3_token and (has_alpha2_token or alpha2_label.search(line)):
                raise AssertionError(f"alpha.3 identity attributed to alpha.2 in {relative}: {line.strip()[:120]}")


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


def main() -> None:
    validate_brand_asset_bytes()
    validate_mascot_size_contract()
    required = (
        "AGENTS.md",
        "STATUS.md",
        "PROJECT_STATE.yaml",
        "PROJECT_DNA.yaml",
        "NEXT_ACTIONS.md",
        "BACKLOG.md",
        "WORKLOG.md",
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
        "download/erratum-alpha3.html",
        "download/install.sh",
        "download/0.1.0-alpha.2/install.sh",
        "download/0.1.0-alpha.3/install.sh",
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

    require_text("AGENTS.md", "statedd_mode: operating")
    require_text("STATUS.md", "**Execution Mode:** operating")
    require_text("PROJECT_STATE.yaml", "statedd_mode: operating")
    require_text("index.html", "StatePort")
    require_text("index.html", "See StatePort in 60 seconds")
    require_text("docs/prototype-walkthrough.html", "Working preview")
    require_text("docs/agent-kits.html", "Early direction")
    require_text("docs/platform-support.html", "Capability-based qualification")
    require_text("papers/stateware-whitepaper-public-v1.1.html", "Publication note")
    require_text("releases/index.html", "still being reviewed")
    require_text("download/index.html", "Do not install alpha.2.")
    require_text("docs/limitations.html", "Earlier local clean-install receipts for Ubuntu 24.04 and Fedora 44 are historical")
    require_text(".github/workflows/deploy-pages.yml", "actions/deploy-pages@d6db90164ac5ed86f2b6aed7e0febac5b3c0c03e")

    public_copy = "\n".join(
        page.read_text(encoding="utf-8") for page in ROOT.rglob("*.html")
    )
    if re.search(r"github\.com/lennertvhoy/StatePort(?!-Site)", public_copy):
        raise AssertionError(
            "Public pages must not link to the private implementation repository "
            "(lennertvhoy/StatePort); the public site repository (StatePort-Site) is allowed"
        )

    validate_local_references()
    validate_documentation_button_accessibility()
    validate_paper_diagrams()
    validate_action_pins()
    validate_pull_request_workflow()
    validate_support_configuration()
    validate_disabled_alpha2_bootstrap()
    validate_alpha3_release()
    validate_immutable_release_trees()
    validate_release_semantics()
    validate_asset_cache_keys()
    validate_pages_provider_truth()
    print("StatePort Site validation: OK")


if __name__ == "__main__":
    main()
