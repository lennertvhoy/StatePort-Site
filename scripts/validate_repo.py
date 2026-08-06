#!/usr/bin/env python3
"""Small, dependency-free integrity gate for the StatePort public site."""

from __future__ import annotations

from html.parser import HTMLParser
import hashlib
import json
from pathlib import Path
import re
import stat
from urllib.parse import urlsplit

from render_support import load_config, rendered_home, support_enabled


ROOT = Path(__file__).resolve().parents[1]


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


def validate_local_references() -> None:
    for page in sorted(ROOT.rglob("*.html")):
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
    if signed.get("source", {}).get("commit") != "fa4ea4b7f08e78669e194c204b59206ab109a02f":
        raise AssertionError("alpha.3 release index has the wrong source commit")
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
    quadlet_files = list((ROOT / release_root / "quadlet").rglob("materialization.template.json"))
    if len(quadlet_files) != 1:
        raise AssertionError("alpha.3 quadlet bundle must contain one materialization template")

    bootstraps = [require("download/install.sh"), require(f"{release_root}/install.sh")]
    contents = []
    for path in bootstraps:
        if stat.S_IMODE(path.stat().st_mode) & 0o111 == 0:
            raise AssertionError(f"Alpha.3 bootstrap must remain executable: {path}")
        text = path.read_text(encoding="utf-8")
        contents.append(text)
        for fragment in (
            "linux-amd64-rootless-podman-quadlet",
            "evaluate_linux_host",
            "RELEASE_INDEX_SHA256=\"d02709a250369b96c7bf5c39659d9080ff53d0cf0e20d391222fe5c1b0d4ae93\"",
            "TRUST_KEY_FINGERPRINT=\"sha256:3dca6219e41310c6a95a8189669aacad3198e6c84489946406b8f986e1f4211a\"",
        ):
            if fragment not in text:
                raise AssertionError(f"Expected {fragment!r} in {path}")
        if "all Linux" in text:
            raise AssertionError(f"Bootstrap must not claim all Linux support: {path}")
    if contents[0] != contents[1]:
        raise AssertionError("Convenience and versioned alpha.3 bootstraps must be identical")


def main() -> None:
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
        "download/install.sh",
        "download/0.1.0-alpha.2/install.sh",
        "download/0.1.0-alpha.3/install.sh",
        "assets/site.css",
        "assets/site.js",
        "assets/stateport-mascot-block-arch-dark.svg",
        "assets/stateport-mascot-block-arch-light.svg",
        "assets/favicon-block-arch.svg",
        "assets/media/stateport-local-prototype-walkthrough.mp4",
        "assets/media/stateport-local-prototype-walkthrough.vtt",
        "assets/media/stateport-demo-home.png",
        "assets/media/stateport-demo-conversation.png",
        "assets/media/stateport-demo-source.png",
        "assets/media/stateport-demo-mobile.png",
        "papers/stateware-whitepaper-public-v1.1.md",
        "papers/stateware-whitepaper-public-v1.1.html",
        "papers/assets/stateware-applications-home.png",
        "papers/assets/stateware-conversation.png",
        "papers/assets/stateware-approvals.png",
        ".github/workflows/deploy-pages.yml",
        ".github/workflows/validate-site-pr.yml",
        "scripts/check_site_quality.py",
        "scripts/render_paper_diagrams.py",
        "scripts/render_support.py",
        "scripts/test_render_support.py",
        "config/mermaid-theme.json",
    )
    for path in required:
        require(path)

    require_text("AGENTS.md", "statedd_mode: operating")
    require_text("STATUS.md", "**Execution Mode:** operating")
    require_text("PROJECT_STATE.yaml", "statedd_mode: operating")
    require_text("index.html", "StatePort")
    require_text("index.html", "See the application at work")
    require_text("docs/prototype-walkthrough.html", "Working fixture")
    require_text("docs/agent-kits.html", "Early direction")
    require_text("docs/platform-support.html", "Capability-based qualification")
    require_text("papers/stateware-whitepaper-public-v1.1.html", "Publication note")
    require_text("releases/index.html", "still being reviewed")
    require_text("download/index.html", "Do not install alpha.2.")
    require_text("docs/limitations.html", "Alpha.3 is published and clean-installed on Ubuntu 24.04 and Fedora 44")
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
    print("StatePort Site validation: OK")


if __name__ == "__main__":
    main()
