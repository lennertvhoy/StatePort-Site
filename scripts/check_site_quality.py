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
from urllib.parse import unquote, urlsplit
import xml.etree.ElementTree as ET

from validate_repo import (
    ROOT,
    validate_documentation_button_accessibility,
    validate_local_references,
)

BASE_URL = "https://lennertvhoy.github.io/StatePort-Site/"
ENTRYPOINTS = {
    Path("index.html"): BASE_URL,
    Path("docs/index.html"): f"{BASE_URL}docs/",
    Path("tutorials/index.html"): f"{BASE_URL}tutorials/",
    Path("releases/index.html"): f"{BASE_URL}releases/",
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
    video_count: int = 0
    caption_track_count: int = 0

    @property
    def title(self) -> str:
        return "".join(self.title_parts).strip()


class QualityParser(HTMLParser):
    def __init__(self, path: Path) -> None:
        super().__init__(convert_charrefs=True)
        self.facts = DocumentFacts(path=path)
        self._in_title = False
        self._json_ld_parts: list[str] | None = None

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
            self.facts.video_count += 1
        elif tag == "track" and values.get("kind", "").lower() == "captions":
            self.facts.caption_track_count += 1

    def handle_endtag(self, tag: str) -> None:
        if tag == "title":
            self._in_title = False
        elif tag == "script" and self._json_ld_parts is not None:
            self.facts.json_ld.append("".join(self._json_ld_parts).strip())
            self._json_ld_parts = None

    def handle_data(self, data: str) -> None:
        if self._in_title:
            self.facts.title_parts.append(data)
        if self._json_ld_parts is not None:
            self._json_ld_parts.append(data)


def parse_documents() -> dict[Path, DocumentFacts]:
    documents: dict[Path, DocumentFacts] = {}
    for path in sorted(ROOT.rglob("*.html")):
        relative = path.relative_to(ROOT)
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

        if facts.video_count and facts.caption_track_count < facts.video_count:
            raise AssertionError(
                f"{path}: each video requires a captions track "
                f"({facts.video_count} videos, {facts.caption_track_count} caption tracks)"
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
    for image in home.images:
        source = image.get("src", "")
        if not source.startswith("assets/media/"):
            continue
        if not image.get("width") or not image.get("height"):
            raise AssertionError(f"index.html: media image requires intrinsic dimensions: {source}")
        if image.get("decoding") != "async":
            raise AssertionError(f"index.html: media image should decode asynchronously: {source}")
        if image.get("loading") != "lazy":
            raise AssertionError(f"index.html: below-the-fold media image should lazy-load: {source}")


def resolve_local_page(source_page: Path, href_path: str) -> Path:
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
        if path != Path("404.html")
    }
    missing = sorted(expected.difference(locations))
    extra = sorted(locations.difference(expected))
    if missing:
        raise AssertionError(f"sitemap.xml is missing: {', '.join(missing)}")
    if extra:
        raise AssertionError(f"sitemap.xml contains unknown pages: {', '.join(extra)}")


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
    if enhancements.stat().st_size > 30_000:
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


def main() -> None:
    require_file("assets/site-enhancements.css")
    documents = parse_documents()
    validate_local_references()
    validate_documentation_button_accessibility()
    validate_document_basics(documents)
    validate_entrypoint_metadata(documents)
    validate_home_media_hints(documents)
    validate_fragments(documents)
    validate_sitemap(documents)
    validate_manifest()
    validate_privacy_and_asset_discipline()
    print(
        "StatePort Site quality contract: "
        f"{len(documents)} pages; structure, accessibility, metadata, media, fragments, "
        "sitemap, privacy, and asset budgets: OK"
    )


if __name__ == "__main__":
    main()
