#!/usr/bin/env python3
"""Small, dependency-free integrity gate for the StatePort public site."""

from __future__ import annotations

from html.parser import HTMLParser
from pathlib import Path
import re
from urllib.parse import urlsplit


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
    """Require immutable action refs in every repository workflow."""
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
    """Keep draft-PR validation on GitHub-hosted, non-deploying authority."""
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


def main() -> None:
    required = (
        "AGENTS.md",
        "STATUS.md",
        "PROJECT_STATE.yaml",
        "PROJECT_DNA.yaml",
        "NEXT_ACTIONS.md",
        "BACKLOG.md",
        "WORKLOG.md",
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
        "tutorials/index.html",
        "tutorials/first-application.html",
        "tutorials/reading-a-receipt.html",
        "releases/index.html",
        "assets/site.css",
        "assets/site.js",
        "assets/stateport-mascot-shell.svg",
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
    )
    for path in required:
        require(path)

    require_text("AGENTS.md", "statedd_mode: operating")
    require_text("STATUS.md", "**Execution Mode:** operating")
    require_text("PROJECT_STATE.yaml", "statedd_mode: operating")
    require_text("index.html", "StatePort")
    require_text("index.html", "Watch the local prototype")
    require_text("docs/prototype-walkthrough.html", "Local preview")
    require_text("docs/agent-kits.html", "Early direction")
    require_text("docs/platform-support.html", "Capability-based qualification")
    require_text("papers/stateware-whitepaper-public-v1.1.html", "Publication note")
    require_text("releases/index.html", "The release is still in preparation")
    require_text(".github/workflows/deploy-pages.yml", "actions/deploy-pages@d6db90164ac5ed86f2b6aed7e0febac5b3c0c03e")

    public_copy = "\n".join(
        page.read_text(encoding="utf-8") for page in ROOT.rglob("*.html")
    )
    if "github.com/lennertvhoy/StatePort" in public_copy:
        raise AssertionError("Public pages must not link to the private implementation repository")

    validate_local_references()
    validate_documentation_button_accessibility()
    validate_action_pins()
    validate_pull_request_workflow()
    print("StatePort Site validation: OK")


if __name__ == "__main__":
    main()
