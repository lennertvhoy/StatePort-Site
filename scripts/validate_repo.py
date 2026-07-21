#!/usr/bin/env python3
"""Small, dependency-free integrity gate for the StatePort public site."""

from __future__ import annotations

from html.parser import HTMLParser
from pathlib import Path
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
    require_text("papers/stateware-whitepaper-public-v1.1.html", "Publication note")
    require_text("releases/index.html", "The release is still in preparation")
    require_text(".github/workflows/deploy-pages.yml", "actions/deploy-pages@v4")

    public_copy = "\n".join(
        page.read_text(encoding="utf-8") for page in ROOT.rglob("*.html")
    )
    if "github.com/lennertvhoy/StatePort" in public_copy:
        raise AssertionError("Public pages must not link to the private implementation repository")

    validate_local_references()
    print("StatePort Site validation: OK")


if __name__ == "__main__":
    main()
