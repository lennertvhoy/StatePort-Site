#!/usr/bin/env python3
"""Deterministic quality contract for the StatePort public site.

The checks intentionally stay dependency-free so pull requests can validate the
site's information architecture, accessibility basics, metadata, privacy, and
asset discipline without a JavaScript toolchain or network access.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from html.parser import HTMLParser
import json
from pathlib import Path
import re
import subprocess
from urllib.parse import unquote, urlsplit
import xml.etree.ElementTree as ET

from validate_repo import (
    INSTALLER_STATUS,
    ROOT,
    is_local_build_source,
    linked_public_markdown_pages,
    mutable_public_pages,
    release_state_block,
    validate_documentation_button_accessibility,
    validate_local_references,
    validate_source_disclosures,
)

BASE_URL = "https://lennertvhoy.github.io/StatePort-Site/"
SOCIAL_CARD_URL = f"{BASE_URL}assets/media/stateport-social-card.png"
SOCIAL_CARD_FILE = Path("assets/media/stateport-social-card.png")
MEDIA_ROOT = Path("assets/media")
ENTRYPOINTS = {
    Path("index.html"): BASE_URL,
    Path("docs/index.html"): f"{BASE_URL}docs/",
    Path("tutorials/index.html"): f"{BASE_URL}tutorials/",
    Path("releases/index.html"): f"{BASE_URL}releases/",
}
PRIMARY_PUBLIC_COPY_PAGES = {
    Path("index.html"),
    Path("download/index.html"),
    Path("download/erratum-alpha3.html"),
    Path("docs/templates.html"),
    Path("releases/index.html"),
    Path("tutorials/index.html"),
    Path("tutorials/first-application.html"),
    Path("tutorials/reading-a-receipt.html"),
    *{Path(f"docs/{name}.html") for name in (
        "index",
        "agent-kits",
        "deployments",
        "evidence-and-roadmap",
        "foundations",
        "getting-started",
        "governance",
        "hosts-and-portability",
        "lifecycle",
        "limitations",
        "model",
        "platform-support",
        "prototype-walkthrough",
        "reference",
        "security-and-privacy",
        "study-state",
        "updates",
    )},
}
PUBLIC_COPY_REJECTIONS = {
    "owner-reported": re.compile(r"owner[- ]reported", re.IGNORECASE),
    "compatible_unvalidated": re.compile(r"compatible_unvalidated", re.IGNORECASE),
    "exact-target": re.compile(r"exact[- ]target", re.IGNORECASE),
    "clean-install receipt or proof": re.compile(
        r"clean[- ]install\s+(?:receipt|proof)", re.IGNORECASE
    ),
    "remotely byte-verified": re.compile(r"remotely\s+byte[- ]verified", re.IGNORECASE),
    "immutable bytes": re.compile(r"immutable\s+bytes", re.IGNORECASE),
    "signed payload identity": re.compile(r"signed\s+payload\s+identity", re.IGNORECASE),
    "internal target identifier": re.compile(
        r"wsl2-ubuntu2404-linux-amd64-rootless-podman-quadlet", re.IGNORECASE
    ),
    "private source bookkeeping": re.compile(
        r"canonical\s+development\s+git|publicsnapshot|curated\s+alpha\.5\s+source\s+archive",
        re.IGNORECASE,
    ),
    "claim stack": re.compile(
        r"honest\s+disclaimer|not\s+clean-installed|owner-accepted|"
        r"independently\s+security-(?:reviewed|audited)|production-ready|"
        r"human\s+acceptance|production\s+qualification",
        re.IGNORECASE,
    ),
    "incident byte chronology": re.compile(r"\b(?:4,096|8,971|17,561)\s+bytes\b"),
    "internal availability prose": re.compile(
        r"availability\s+boundary|release\s+ledger", re.IGNORECASE
    ),
    "stale installer availability": re.compile(
        r"installer\s+is\s+available\s+for\s+(?:a\s+first|an\s+owner)\s+test",
        re.IGNORECASE,
    ),
    "raw SHA-256 inventory": re.compile(r"sha256:[0-9a-f]{64}", re.IGNORECASE),
    "raw Git identity": re.compile(r"(?<![0-9a-f])[0-9a-f]{40}(?![0-9a-f])", re.IGNORECASE),
}
# Pages that exist in the repository but are self-marked as not yet published.
# They stay out of sitemap.xml so crawlers are not sent to unfinished work.
UNPUBLISHED_PAGES = {
    Path("papers/stateware-whitepaper-candidate-v1.2.html"),
}
TRACKING_PATTERNS = (
    "googletagmanager.com",
    "google-analytics.com",
    "gtag(",
    "plausible.io/js/",
    "posthog.com",
    "cdn.segment.com",
    "api.segment.io",
    "mixpanel.com",
    "clarity.ms",
    "connect.facebook.net",
)


@dataclass
class DocumentFacts:
    path: Path
    language: str | None = None
    title_parts: list[str] = field(default_factory=list)
    description: str | None = None
    viewport: str | None = None
    canonical: str | None = None
    manifest: str | None = None
    social: dict[str, str] = field(default_factory=dict)
    json_ld: list[str] = field(default_factory=list)
    ids: set[str] = field(default_factory=set)
    duplicate_ids: set[str] = field(default_factory=set)
    headings: list[int] = field(default_factory=list)
    h1_count: int = 0
    main_count: int = 0
    links: list[dict[str, str]] = field(default_factory=list)
    images: list[dict[str, str]] = field(default_factory=list)
    script_sources: list[str] = field(default_factory=list)
    nav_toggles: list[dict[str, str]] = field(default_factory=list)
    skip_links: list[str] = field(default_factory=list)
    labels_for: set[str] = field(default_factory=set)
    controls: list[dict[str, str]] = field(default_factory=list)
    videos: list[dict[str, str]] = field(default_factory=list)
    tracks: list[dict[str, str]] = field(default_factory=list)
    sources: list[dict[str, str]] = field(default_factory=list)
    id_text: dict[str, int] = field(default_factory=dict)

    @property
    def title(self) -> str:
        return "".join(self.title_parts).strip()


VOID_TAGS = {
    "area", "base", "br", "col", "embed", "hr", "img", "input", "link",
    "meta", "param", "source", "track", "wbr",
}


class QualityParser(HTMLParser):
    def __init__(self, path: Path) -> None:
        super().__init__(convert_charrefs=True)
        self.facts = DocumentFacts(path=path)
        self._in_title = False
        self._json_ld_parts: list[str] | None = None
        self._id_stack: list[str] = []

    @staticmethod
    def attrs_dict(attrs: list[tuple[str, str | None]]) -> dict[str, str]:
        return {name: value or "" for name, value in attrs}

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = self.attrs_dict(attrs)
        element_id = values.get("id")
        if element_id:
            if element_id in self.facts.ids:
                self.facts.duplicate_ids.add(element_id)
            self.facts.ids.add(element_id)

        if tag == "html":
            self.facts.language = values.get("lang")
        elif tag == "title":
            self._in_title = True
        elif tag == "meta":
            name = values.get("name")
            property_name = values.get("property")
            content = values.get("content", "").strip()
            if name == "description":
                self.facts.description = content
            elif name == "viewport":
                self.facts.viewport = content
            if property_name:
                self.facts.social[property_name] = content
            if name and name.startswith("twitter:"):
                self.facts.social[name] = content
        elif tag == "link":
            rel = {token.lower() for token in values.get("rel", "").split()}
            if "canonical" in rel:
                self.facts.canonical = values.get("href")
            if "manifest" in rel:
                self.facts.manifest = values.get("href")
        elif tag == "main":
            self.facts.main_count += 1
        elif tag in {"h1", "h2", "h3", "h4", "h5", "h6"}:
            level = int(tag[1])
            self.facts.headings.append(level)
            if level == 1:
                self.facts.h1_count += 1
        elif tag == "a":
            self.facts.links.append(values)
            classes = set(values.get("class", "").split())
            if "skip-link" in classes:
                self.facts.skip_links.append(values.get("href", ""))
        elif tag == "img":
            self.facts.images.append(values)
        elif tag == "script":
            source = values.get("src")
            if source:
                self.facts.script_sources.append(source)
            if values.get("type", "").lower() == "application/ld+json":
                self._json_ld_parts = []
        elif tag == "button":
            if "nav-toggle" in set(values.get("class", "").split()):
                self.facts.nav_toggles.append(values)
        elif tag == "label":
            if values.get("for"):
                self.facts.labels_for.add(values["for"])
        elif tag in {"input", "select", "textarea"}:
            if values.get("type", "").lower() != "hidden":
                self.facts.controls.append(values)
        elif tag == "video":
            self.facts.videos.append(values)
        elif tag == "track":
            self.facts.tracks.append(values)
        elif tag == "source":
            self.facts.sources.append(values)

        if tag not in VOID_TAGS:
            self._id_stack.append(element_id or "")

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.handle_starttag(tag, attrs)
        if self._id_stack:
            self._id_stack.pop()

    def handle_endtag(self, tag: str) -> None:
        if tag == "title":
            self._in_title = False
        elif tag == "script" and self._json_ld_parts is not None:
            self.facts.json_ld.append("".join(self._json_ld_parts).strip())
            self._json_ld_parts = None
        if tag not in VOID_TAGS and self._id_stack:
            self._id_stack.pop()

    def handle_data(self, data: str) -> None:
        if self._in_title:
            self.facts.title_parts.append(data)
        if self._json_ld_parts is not None:
            self._json_ld_parts.append(data)
        for element_id in self._id_stack:
            if element_id:
                self.facts.id_text[element_id] = self.facts.id_text.get(element_id, 0) + len(data.strip())


def parse_documents() -> dict[Path, DocumentFacts]:
    documents: dict[Path, DocumentFacts] = {}
    for path in sorted(ROOT.rglob("*.html")):
        relative = path.relative_to(ROOT)
        if is_local_build_source(relative):
            # Checked-in media build source, not a visitor-facing HTML page.
            continue
        parser = QualityParser(relative)
        parser.feed(path.read_text(encoding="utf-8"))
        parser.close()
        documents[relative] = parser.facts
    return documents


def require_file(path: str) -> Path:
    candidate = ROOT / path
    if not candidate.is_file():
        raise AssertionError(f"Missing quality-contract file: {path}")
    return candidate


def validate_document_basics(documents: dict[Path, DocumentFacts]) -> None:
    titles: dict[str, Path] = {}
    for path, facts in documents.items():
        if facts.language != "en":
            raise AssertionError(f"{path}: expected <html lang=\"en\">")
        if not facts.title:
            raise AssertionError(f"{path}: missing document title")
        if facts.title in titles:
            raise AssertionError(f"Duplicate document title in {titles[facts.title]} and {path}: {facts.title!r}")
        titles[facts.title] = path
        if not facts.description:
            raise AssertionError(f"{path}: missing meta description")
        if not facts.viewport or "width=device-width" not in facts.viewport:
            raise AssertionError(f"{path}: missing responsive viewport metadata")
        if facts.main_count != 1:
            raise AssertionError(f"{path}: expected exactly one <main>, found {facts.main_count}")
        if facts.h1_count != 1:
            raise AssertionError(f"{path}: expected exactly one <h1>, found {facts.h1_count}")
        if facts.duplicate_ids:
            duplicates = ", ".join(sorted(facts.duplicate_ids))
            raise AssertionError(f"{path}: duplicate id values: {duplicates}")
        if "#main" not in facts.skip_links or "main" not in facts.ids:
            raise AssertionError(f"{path}: skip link must target #main")

        for image in facts.images:
            if "alt" not in image:
                raise AssertionError(f"{path}: every image requires an alt attribute: {image.get('src', '<unknown>')}")

        for link in facts.links:
            if link.get("target") == "_blank":
                rel = set(link.get("rel", "").split())
                if "noopener" not in rel:
                    raise AssertionError(f"{path}: target=_blank link requires rel=noopener: {link.get('href')}")

        for toggle in facts.nav_toggles:
            if "aria-expanded" not in toggle or not toggle.get("aria-controls"):
                raise AssertionError(f"{path}: navigation toggle requires aria-expanded and aria-controls")
            if toggle["aria-controls"] not in facts.ids:
                raise AssertionError(
                    f"{path}: navigation toggle controls missing id #{toggle['aria-controls']}"
                )

        for control in facts.controls:
            control_id = control.get("id")
            if not control_id or control_id not in facts.labels_for:
                raise AssertionError(f"{path}: form control requires a matching <label for>: {control}")

        caption_tracks = [
            track for track in facts.tracks if track.get("kind", "").lower() == "captions"
        ]
        if facts.videos and len(caption_tracks) < len(facts.videos):
            raise AssertionError(
                f"{path}: each video requires a captions track "
                f"({len(facts.videos)} videos, {len(caption_tracks)} caption tracks)"
            )

        for source in facts.script_sources:
            parsed = urlsplit(source)
            if parsed.scheme or parsed.netloc:
                raise AssertionError(f"{path}: third-party or remote script is not allowed: {source}")


def validate_entrypoint_metadata(documents: dict[Path, DocumentFacts]) -> None:
    required_social = {"og:title", "og:description", "og:url", "og:image", "twitter:card"}
    for path, expected_canonical in ENTRYPOINTS.items():
        facts = documents.get(path)
        if not facts:
            raise AssertionError(f"Missing entrypoint page: {path}")
        description_length = len(facts.description or "")
        if not 80 <= description_length <= 170:
            raise AssertionError(
                f"{path}: meta description should be 80–170 characters, found {description_length}"
            )
        if facts.canonical != expected_canonical:
            raise AssertionError(
                f"{path}: canonical URL must be {expected_canonical!r}, found {facts.canonical!r}"
            )
        missing_social = sorted(required_social.difference(facts.social))
        if missing_social:
            raise AssertionError(f"{path}: missing social metadata: {', '.join(missing_social)}")
        if not facts.manifest:
            raise AssertionError(f"{path}: missing web app manifest link")
        if not facts.json_ld:
            raise AssertionError(f"{path}: missing JSON-LD metadata")
        for payload in facts.json_ld:
            try:
                parsed = json.loads(payload)
            except json.JSONDecodeError as exc:
                raise AssertionError(f"{path}: invalid JSON-LD: {exc}") from exc
            if parsed.get("@context") != "https://schema.org" or not parsed.get("@type"):
                raise AssertionError(f"{path}: JSON-LD requires schema.org context and @type")

        levels = facts.headings
        for previous, current in zip(levels, levels[1:]):
            if current > previous + 1:
                raise AssertionError(f"{path}: heading level jumps from h{previous} to h{current}")

        html = (ROOT / path).read_text(encoding="utf-8")
        if "site-enhancements.css" not in html:
            raise AssertionError(f"{path}: entrypoint must load the enhancement stylesheet without JavaScript")


def validate_home_media_hints(documents: dict[Path, DocumentFacts]) -> None:
    home = documents[Path("index.html")]
    eager: list[str] = []
    for image in home.images:
        source = image.get("src", "")
        if not source.startswith("assets/media/"):
            continue
        if not image.get("width") or not image.get("height"):
            raise AssertionError(f"index.html: media image requires intrinsic dimensions: {source}")
        if image.get("decoding") != "async":
            raise AssertionError(f"index.html: media image should decode asynchronously: {source}")
        loading = image.get("loading")
        if loading == "eager":
            # Exactly one above-the-fold hero proof visual may load eagerly.
            eager.append(source)
        elif loading != "lazy":
            raise AssertionError(
                f"index.html: below-the-fold media image should lazy-load: {source}"
            )
    if len(eager) > 1:
        raise AssertionError(
            f"index.html: at most one hero media image may load eagerly: {eager}"
        )


def validate_mascot_surface_references(documents: dict[Path, DocumentFacts]) -> None:
    """Require the light mascot on every active public surface."""

    for path in documents:
        html = (ROOT / path).read_text(encoding="utf-8")
        dark_asset = "stateport-mascot-block-arch-dark.svg"
        light_asset = "stateport-mascot-block-arch-light.svg"
        if dark_asset in html:
            raise AssertionError(f"{path}: active public HTML must not reference {dark_asset}")

        for surface in ("site-header--on-dark", "site-header--light"):
            headers = re.findall(
                rf'<header\b[^>]*class="[^"]*\b{re.escape(surface)}\b[^"]*"[^>]*>.*?</header>',
                html,
                re.DOTALL,
            )
            for header in headers:
                if light_asset not in header:
                    raise AssertionError(f"{path}: {surface} must use {light_asset}")

        footers = re.findall(r"<footer\b[^>]*class=\"[^\"]*\bsite-footer\b[^\"]*\"[^>]*>.*?</footer>", html, re.DOTALL)
        for footer in footers:
            if light_asset not in footer:
                raise AssertionError(f"{path}: site footer must use {light_asset}")


def resolve_local_page(source_page: Path, href_path: str) -> Path:
    if href_path.startswith("/StatePort-Site/"):
        # Site-root-absolute link (see 404.html, served at arbitrary depth).
        target = (ROOT / href_path[len("/StatePort-Site/"):]).resolve()
    else:
        target = (ROOT / source_page.parent / unquote(href_path)).resolve()
    try:
        relative = target.relative_to(ROOT)
    except ValueError as exc:
        raise AssertionError(f"{source_page}: local link escapes repository: {href_path}") from exc
    if target.is_dir() or href_path.endswith("/"):
        relative = relative / "index.html"
    return relative


def validate_fragments(documents: dict[Path, DocumentFacts]) -> None:
    for source_path, facts in documents.items():
        for link in facts.links:
            href = link.get("href", "")
            if not href:
                continue
            parsed = urlsplit(href)
            if parsed.scheme or parsed.netloc or not parsed.fragment:
                continue
            target_page = source_path if not parsed.path else resolve_local_page(source_path, parsed.path)
            target_facts = documents.get(target_page)
            if not target_facts:
                continue
            fragment = unquote(parsed.fragment)
            if fragment not in target_facts.ids:
                raise AssertionError(
                    f"{source_path}: fragment #{fragment} does not exist in {target_page}"
                )


def public_url(path: Path) -> str:
    if path.name == "index.html":
        parent = path.parent.as_posix()
        return BASE_URL if parent == "." else f"{BASE_URL}{parent}/"
    return f"{BASE_URL}{path.as_posix()}"


def validate_sitemap(documents: dict[Path, DocumentFacts]) -> None:
    sitemap_path = require_file("sitemap.xml")
    try:
        root = ET.parse(sitemap_path).getroot()
    except ET.ParseError as exc:
        raise AssertionError(f"Invalid sitemap.xml: {exc}") from exc
    namespace = {"s": "http://www.sitemaps.org/schemas/sitemap/0.9"}
    locations = {
        element.text.strip()
        for element in root.findall("s:url/s:loc", namespace)
        if element.text and element.text.strip()
    }
    expected = {
        public_url(path)
        for path in documents
        if path != Path("404.html") and path not in UNPUBLISHED_PAGES
    }
    missing = sorted(expected.difference(locations))
    extra = sorted(locations.difference(expected))
    if missing:
        raise AssertionError(f"sitemap.xml is missing: {', '.join(missing)}")
    if extra:
        raise AssertionError(f"sitemap.xml contains unknown pages: {', '.join(extra)}")
    advertised_unpublished = sorted(locations.intersection({public_url(path) for path in UNPUBLISHED_PAGES}))
    if advertised_unpublished:
        raise AssertionError(
            f"sitemap.xml advertises pages that are not yet published: {', '.join(advertised_unpublished)}"
        )


def validate_manifest() -> None:
    manifest_path = require_file("site.webmanifest")
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise AssertionError(f"Invalid site.webmanifest: {exc}") from exc
    required = {"name", "short_name", "description", "start_url", "scope", "display", "theme_color", "icons"}
    missing = sorted(required.difference(manifest))
    if missing:
        raise AssertionError(f"site.webmanifest is missing keys: {', '.join(missing)}")
    if not isinstance(manifest["icons"], list) or not manifest["icons"]:
        raise AssertionError("site.webmanifest requires at least one icon")
    for icon in manifest["icons"]:
        source = icon.get("src", "")
        if urlsplit(source).scheme or not (ROOT / source).is_file():
            raise AssertionError(f"site.webmanifest icon must be an existing local file: {source}")
    if manifest["start_url"] != manifest["scope"]:
        raise AssertionError("site.webmanifest start_url and scope must stay consistent")


def validate_privacy_and_asset_discipline() -> None:
    searchable = [*ROOT.rglob("*.html"), *ROOT.rglob("*.js")]
    for path in searchable:
        text = path.read_text(encoding="utf-8").lower()
        for pattern in TRACKING_PATTERNS:
            if pattern in text:
                raise AssertionError(f"Tracking or remote analytics pattern in {path.relative_to(ROOT)}: {pattern}")

    site_js = require_file("assets/site.js")
    enhancements = require_file("assets/site-enhancements.css")
    if site_js.stat().st_size > 24_000:
        raise AssertionError(f"assets/site.js exceeds the 24 KB progressive-enhancement budget: {site_js.stat().st_size}")
    if enhancements.stat().st_size > 30_720:
        raise AssertionError(
            "assets/site-enhancements.css exceeds the 30 KB additive-style budget: "
            f"{enhancements.stat().st_size}"
        )
    total_css = sum(path.stat().st_size for path in (ROOT / "assets").glob("*.css"))
    if total_css > 120_000:
        raise AssertionError(f"Total CSS exceeds the 120 KB static-site budget: {total_css}")

    javascript = site_js.read_text(encoding="utf-8")
    if ".innerHTML" in javascript or "insertAdjacentHTML" in javascript:
        raise AssertionError("Progressive enhancement JavaScript must not inject untrusted HTML strings")
    if "data-site-enhancements" in javascript or "createElement(\"link\")" in javascript:
        raise AssertionError(
            "Shared enhancement styles must be statically linked, not injected by JavaScript"
        )


def validate_public_media_boundaries(documents: dict[Path, DocumentFacts]) -> None:
    """Visitor pages must not publish build source or retired media names."""

    retired = (
        "media-src/",
        "stateport-local-prototype-walkthrough",
        "stateport-demo-",
        "build_walkthrough",
    )
    for page in documents:
        text = (ROOT / page).read_text(encoding="utf-8")
        for marker in retired:
            if marker in text:
                raise AssertionError(f"{page}: retired or private media reference: {marker}")


def validate_linked_markdown_language() -> None:
    """Visitor-linked Markdown must carry the same current release boundary."""

    stale = (
        re.compile(r"\bv0\.1\.0-alpha\.1\b", re.IGNORECASE),
        re.compile(r"\bprivate product-owner candidate\b", re.IGNORECASE),
        re.compile(r"\bno public download\b", re.IGNORECASE),
    )
    for path in sorted(linked_public_markdown_pages()):
        text = path.read_text(encoding="utf-8")
        for pattern in stale:
            if pattern.search(text):
                raise AssertionError(
                    f"{path.relative_to(ROOT)}: stale linked Markdown language: {pattern.pattern}"
                )


def validate_release_surface_quality(documents: dict[Path, DocumentFacts]) -> None:
    """Keep the enabled Alpha.16 release metadata explicit and free of pipe-to-shell."""
    release_block = release_state_block()
    install_enabled = re.search(r"^  installation_enabled: true\s*$", release_block, re.MULTILINE)
    if not install_enabled:
        raise AssertionError("Release surface quality checks require enabled Alpha.16 state")

    command_pattern = re.compile(r"(?:curl|wget)\s[^<\n]*install\.sh")
    for page in mutable_public_pages():
        facts = documents.get(page.relative_to(ROOT))
        if facts is None:
            continue
        metadata = " ".join(
            [facts.title, facts.description or "", *facts.social.values(), *facts.json_ld]
        )
        if command_pattern.search(metadata):
            raise AssertionError(
                f"{facts.path}: metadata must not contain an executable install command"
            )

    release_description = (documents[Path("releases/index.html")].description or "").lower()
    if (
        "installer" not in release_description
        or "available" not in release_description
        or "temporarily unavailable" in release_description
    ):
        raise AssertionError(
            "releases/index.html: meta description must plainly state installer availability"
        )


def validate_primary_public_copy() -> None:
    """Keep internal release and evidence vocabulary out of the visitor journey."""

    for relative in sorted(PRIMARY_PUBLIC_COPY_PAGES):
        path = ROOT / relative
        if not path.is_file():
            raise AssertionError(f"Missing primary public copy page: {relative}")
        text = path.read_text(encoding="utf-8")
        for label, pattern in PUBLIC_COPY_REJECTIONS.items():
            if match := pattern.search(text):
                raise AssertionError(
                    f"{relative}: rejected public copy ({label}): {match.group(0)!r}"
                )

    for relative in (
        Path("index.html"),
        Path("download/index.html"),
        Path("releases/index.html"),
        Path("docs/limitations.html"),
    ):
        text = (ROOT / relative).read_text(encoding="utf-8")
        if "StatePort is in early alpha. Do not use it for important data." not in text:
            raise AssertionError(f"{relative}: missing concise early-alpha warning")

    for relative in (Path("index.html"), Path("download/index.html"), Path("releases/index.html")):
        if INSTALLER_STATUS not in (ROOT / relative).read_text(encoding="utf-8"):
            raise AssertionError(f"{relative}: missing concise installer status")


def validate_source_disclosure_quality(documents: dict[Path, DocumentFacts]) -> None:
    """Reuse the repository's exact identity and source/license boundary."""

    texts = {ROOT / path: (ROOT / path).read_text(encoding="utf-8") for path in documents}
    validate_source_disclosures(texts)


def validate_social_card_metadata(documents: dict[Path, DocumentFacts]) -> None:
    """Every page carries OG + Twitter image tags for the frozen social card."""
    for path, facts in documents.items():
        for key in ("og:image", "twitter:image"):
            if facts.social.get(key) != SOCIAL_CARD_URL:
                raise AssertionError(
                    f"{path}: {key} must be the frozen social card {SOCIAL_CARD_URL}, "
                    f"found {facts.social.get(key)!r}"
                )
        if facts.social.get("og:image:width") != "1200" or facts.social.get("og:image:height") != "630":
            raise AssertionError(f"{path}: og:image dimensions must be 1200x630")
        if not facts.social.get("og:image:alt"):
            raise AssertionError(f"{path}: og:image requires an alt description")
    card = ROOT / SOCIAL_CARD_FILE
    if not card.is_file():
        raise AssertionError(
            f"Missing frozen social card asset: {SOCIAL_CARD_FILE} "
            "(produced by the media worker)"
        )
    if _png_dimensions(card) != (1200, 630):
        raise AssertionError(f"{SOCIAL_CARD_FILE} must be exactly 1200x630")


STALE_RELEASE_PATTERNS = (
    re.compile(r"\bprivate alpha\b", re.IGNORECASE),
    re.compile(r"\bcan(?:'|’)t be downloaded\b", re.IGNORECASE),
    re.compile(r"\bcannot be downloaded\b", re.IGNORECASE),
    re.compile(
        r"(?:\bcoming soon\b[^.\n]{0,60}\b(?:install|download|available)\b"
        r"|\b(?:install|download|available)\b[^.\n]{0,60}\bcoming soon\b)",
        re.IGNORECASE,
    ),
)


def validate_stale_release_language(documents: dict[Path, DocumentFacts]) -> None:
    """Reject pre-publication framing on every mutable page and caption file."""
    surfaces: list[tuple[str, str]] = [
        (str(path), (ROOT / path).read_text(encoding="utf-8")) for path in documents
    ]
    surfaces.extend(
        (str(vtt.relative_to(ROOT)), vtt.read_text(encoding="utf-8"))
        for vtt in sorted((ROOT / MEDIA_ROOT).glob("*.vtt"))
    )
    surfaces.extend(
        (str(path.relative_to(ROOT)), path.read_text(encoding="utf-8"))
        for path in sorted(linked_public_markdown_pages())
    )
    markdown_stale_patterns = (
        re.compile(r"\bv0\.1\.0-alpha\.1\b", re.IGNORECASE),
        re.compile(r"\bprivate product-owner candidate\b", re.IGNORECASE),
        re.compile(r"\bno public download\b", re.IGNORECASE),
    )
    for name, text in surfaces:
        patterns = STALE_RELEASE_PATTERNS + (markdown_stale_patterns if name.endswith(".md") else ())
        for pattern in patterns:
            if pattern.search(text):
                raise AssertionError(
                    f"Stale release language in {name}: {pattern.pattern}"
                )


def validate_video_embeds(documents: dict[Path, DocumentFacts]) -> None:
    """Frozen embed contract: controllable, lazy, captioned, transcribed video."""
    for path, facts in documents.items():
        if not facts.videos:
            continue
        for video in facts.videos:
            if "controls" not in video:
                raise AssertionError(f"{path}: video must expose controls")
            if video.get("preload") != "metadata":
                raise AssertionError(
                    f"{path}: video must declare preload=\"metadata\" (no eager loading)"
                )
            if "playsinline" not in video:
                raise AssertionError(f"{path}: video must play inline")
            if "autoplay" in video:
                raise AssertionError(f"{path}: video must never autoplay")
            if not video.get("width") or not video.get("height"):
                raise AssertionError(f"{path}: video requires intrinsic width/height")
            if not video.get("poster"):
                raise AssertionError(f"{path}: video requires a poster frame")
            describedby = video.get("aria-describedby", "")
            if not describedby or describedby not in facts.ids:
                raise AssertionError(
                    f"{path}: video aria-describedby must reference an on-page caption"
                )
        caption_tracks = [
            track
            for track in facts.tracks
            if track.get("kind", "").lower() == "captions"
            and urlsplit(track.get("src", "")).path.endswith(".vtt")
        ]
        if len(caption_tracks) != len(facts.videos):
            raise AssertionError(f"{path}: each video must have exactly one .vtt captions track")
        if len(caption_tracks) != 1 or "default" not in caption_tracks[0]:
            raise AssertionError(f"{path}: one captions track must be the default")
        html = (ROOT / path).read_text(encoding="utf-8")
        for marker in ('data-composition-id="captions"', 'class="caption-layer"', 'class="caption-stage"'):
            if marker in html:
                raise AssertionError(f"{path}: burned/open caption layer duplicates the VTT track")
        transcripts = [
            element_id for element_id in facts.ids if "transcript" in element_id.lower()
        ]
        if not transcripts:
            raise AssertionError(
                f"{path}: embedded video requires a visible transcript "
                "(an element whose id contains \"transcript\")"
            )
        if max(facts.id_text.get(element_id, 0) for element_id in transcripts) < 200:
            raise AssertionError(
                f"{path}: transcript must contain the real narration text, not a summary"
            )


def _vtt_timestamp(value: str) -> float:
    match = re.fullmatch(r"(?:(\d+):)?(\d{1,2}):(\d{2})\.(\d{3})", value.strip())
    if not match:
        raise AssertionError(f"Malformed WebVTT timestamp: {value!r}")
    hours = int(match.group(1) or 0)
    return hours * 3600 + int(match.group(2)) * 60 + int(match.group(3)) + int(match.group(4)) / 1000


def parse_vtt_cues(text: str) -> list[tuple[float, float, str]]:
    cues: list[tuple[float, float, str]] = []
    blocks = re.split(r"\n\s*\n", text.replace("\r\n", "\n"))
    for block in blocks:
        lines = [line for line in block.strip().splitlines() if line.strip()]
        timing_index = next((i for i, line in enumerate(lines) if "-->" in line), None)
        if timing_index is None:
            continue
        start_raw, _, end_raw = lines[timing_index].partition("-->")
        end_raw = end_raw.strip().split()[0]
        cues.append(
            (
                _vtt_timestamp(start_raw),
                _vtt_timestamp(end_raw),
                " ".join(" ".join(lines[timing_index + 1 :]).split()),
            )
        )
    return cues


def validate_caption_files(documents: dict[Path, DocumentFacts]) -> None:
    """Caption cues stay readable: <= 7s each, no truncation-duplication."""
    referenced: set[Path] = set()
    for path, facts in documents.items():
        for track in facts.tracks:
            source = track.get("src", "")
            if source.endswith(".vtt"):
                referenced.add(resolve_local_page(path, urlsplit(source).path))
    candidates = {vtt.relative_to(ROOT) for vtt in (ROOT / MEDIA_ROOT).glob("*.vtt")}
    for relative in sorted(referenced | candidates):
        vtt = ROOT / relative
        if not vtt.is_file():
            raise AssertionError(f"Captions track references a missing file: {relative}")
        cues = parse_vtt_cues(vtt.read_text(encoding="utf-8"))
        if not cues:
            raise AssertionError(f"{relative}: caption file has no cues")
        previous_end = -1.0
        for index, (start, end, text) in enumerate(cues):
            if end <= start:
                raise AssertionError(
                    f"{relative}: cue {index + 1} must end after it starts"
                )
            if start < previous_end:
                raise AssertionError(
                    f"{relative}: cue {index + 1} is out of chronological order"
                )
            if end - start > 7.0:
                raise AssertionError(
                    f"{relative}: cue {index + 1} runs {end - start:.2f}s, over the 7s maximum"
                )
            previous_end = end
            if index + 1 < len(cues):
                following = cues[index + 1][2]
                if text and following.startswith(text):
                    raise AssertionError(
                        f"{relative}: cue {index + 1} text is duplicated or truncated in cue {index + 2}"
                    )


def validate_video_caption_duration_consistency(documents: dict[Path, DocumentFacts]) -> None:
    """Reject a caption candidate whose end time does not match the served MP4."""

    referenced_videos = {
        resolve_local_page(page, urlsplit(source.get("src", "")).path)
        for page, facts in documents.items()
        for source in facts.sources
        if urlsplit(source.get("src", "")).path.endswith(".mp4")
    }
    for video in sorted(referenced_videos):
        media_path = ROOT / video
        if not media_path.is_file():
            continue
        caption_path = video.with_suffix(".vtt")
        if not (ROOT / caption_path).is_file():
            continue
        result = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", str(media_path)],
            check=False,
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            raise AssertionError(f"{video}: unable to inspect MP4 duration: {result.stderr.strip()}")
        media_duration = float(result.stdout.strip())
        cues = parse_vtt_cues((ROOT / caption_path).read_text(encoding="utf-8"))
        caption_duration = cues[-1][1] if cues else 0.0
        if abs(media_duration - caption_duration) > 0.25:
            raise AssertionError(
                f"{video}: served MP4 duration {media_duration:.3f}s does not match "
                f"VTT end {caption_duration:.3f}s; render matching media before release"
            )


def _media_references(documents: dict[Path, DocumentFacts]) -> dict[Path, list[tuple[Path, dict[str, str]]]]:
    """Map assets/media files to the pages and tags referencing them."""
    references: dict[Path, list[tuple[Path, dict[str, str]]]] = {}

    def record(page: Path, tag: dict[str, str], raw: str) -> None:
        parsed = urlsplit(raw.strip())
        if parsed.scheme or parsed.netloc:
            absolute = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
            if not absolute.startswith(BASE_URL):
                return
            target = Path(unquote(parsed.path[len(urlsplit(BASE_URL).path):]))
        else:
            if not parsed.path:
                return
            target = resolve_local_page(page, unquote(parsed.path))
        if MEDIA_ROOT == target or MEDIA_ROOT in target.parents:
            references.setdefault(target, []).append((page, tag))

    for path, facts in documents.items():
        for image in facts.images:
            record(path, image, image.get("src", ""))
        for video in facts.videos:
            record(path, video, video.get("poster", ""))
        for track in facts.tracks:
            record(path, track, track.get("src", ""))
        for source in facts.sources:
            record(path, source, source.get("src", ""))
        for key in ("og:image", "twitter:image"):
            if facts.social.get(key):
                record(path, {"property": key}, facts.social[key])
    return references


def _png_dimensions(path: Path) -> tuple[int, int]:
    data = path.read_bytes()
    if data[:8] != b"\x89PNG\r\n\x1a\n" or data[12:16] != b"IHDR":
        raise AssertionError(f"Not a PNG file: {path.relative_to(ROOT)}")
    width = int.from_bytes(data[16:20], "big")
    height = int.from_bytes(data[20:24], "big")
    return width, height


def validate_media_asset_integrity(documents: dict[Path, DocumentFacts]) -> None:
    """Referenced media exist with true dimensions; nothing in media/ is orphaned."""
    references = _media_references(documents)
    for target, tags in sorted(references.items()):
        file_path = ROOT / target
        if not file_path.is_file():
            raise AssertionError(f"Referenced media file does not exist: {target}")
        if target.suffix != ".png":
            continue
        real_width, real_height = _png_dimensions(file_path)
        for page, tag in tags:
            if "property" in tag:
                continue  # social meta dims are covered by validate_social_card_metadata
            width, height = tag.get("width"), tag.get("height")
            if not width or not height:
                raise AssertionError(
                    f"{page}: media reference requires width/height attributes: {target}"
                )
            if (int(width), int(height)) != (real_width, real_height):
                raise AssertionError(
                    f"{page}: width/height {width}x{height} do not match "
                    f"{target} ({real_width}x{real_height})"
                )

    on_disk = {
        path.relative_to(ROOT)
        for path in (ROOT / MEDIA_ROOT).rglob("*")
        if path.is_file()
    }
    unreferenced = sorted(on_disk - set(references))
    if unreferenced:
        raise AssertionError(
            "Unreferenced files in assets/media/ (retire or reference them): "
            + ", ".join(str(path) for path in unreferenced)
        )


def validate_homepage_sequence(documents: dict[Path, DocumentFacts]) -> None:
    """Frozen homepage: seven sections in order, hero CTAs in the first viewport."""
    home = documents.get(Path("index.html"))
    if home is None:
        raise AssertionError("Missing homepage")
    html = (ROOT / "index.html").read_text(encoding="utf-8")
    sections = ("overview", "journey", "benefits", "how-it-works", "status", "routes")
    positions: list[int] = []
    for section in sections:
        marker = f'id="{section}"'
        position = html.find(marker)
        if position < 0:
            raise AssertionError(f"index.html: missing homepage section #{section}")
        positions.append(position)
    if positions != sorted(positions):
        raise AssertionError(
            f"index.html: homepage sections out of order: {sections}"
        )
    if not re.search(r'<a[^>]*href="#overview"[^>]*>\s*See StatePort in 33 seconds', html):
        raise AssertionError(
            "index.html: primary CTA \"See StatePort in 33 seconds\" must link #overview"
        )
    if not re.search(
        r'<a[^>]*href="docs/study-state\.html"[^>]*>\s*Explore StudyState', html
    ):
        raise AssertionError(
            "index.html: secondary CTA \"Explore StudyState\" must link docs/study-state.html"
        )


def validate_shared_structure(documents: dict[Path, DocumentFacts]) -> None:
    """Walkthrough page joins the shared enhancement-stylesheet structure."""
    path = Path("docs/prototype-walkthrough.html")
    if path not in documents:
        raise AssertionError("Missing docs/prototype-walkthrough.html")
    html = (ROOT / path).read_text(encoding="utf-8")
    if not re.search(r"\.\./assets/site-enhancements\.css\?v=[0-9A-Za-z-]+", html):
        raise AssertionError(
            f"{path}: must load assets/site-enhancements.css with the shared ?v= cache key"
        )


def main() -> None:
    require_file("assets/site-enhancements.css")
    documents = parse_documents()
    validate_local_references()
    validate_documentation_button_accessibility()
    validate_document_basics(documents)
    validate_entrypoint_metadata(documents)
    validate_home_media_hints(documents)
    validate_mascot_surface_references(documents)
    validate_homepage_sequence(documents)
    validate_shared_structure(documents)
    validate_social_card_metadata(documents)
    validate_video_embeds(documents)
    validate_caption_files(documents)
    validate_video_caption_duration_consistency(documents)
    validate_media_asset_integrity(documents)
    validate_stale_release_language(documents)
    validate_fragments(documents)
    validate_sitemap(documents)
    validate_manifest()
    validate_privacy_and_asset_discipline()
    validate_public_media_boundaries(documents)
    validate_linked_markdown_language()
    validate_primary_public_copy()
    validate_release_surface_quality(documents)
    validate_source_disclosure_quality(documents)
    print(
        "StatePort Site quality contract: "
        f"{len(documents)} pages; structure, accessibility, metadata, media, fragments, "
        "sitemap, privacy, and asset budgets: OK"
    )


if __name__ == "__main__":
    main()
