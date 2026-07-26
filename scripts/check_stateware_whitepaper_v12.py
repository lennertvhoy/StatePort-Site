#!/usr/bin/env python3
"""Validate the Stateware v1.2 source/render contract and claim boundary."""

from __future__ import annotations

from hashlib import sha256
from html import unescape
import re
import sys
from urllib.parse import parse_qsl, urlparse

from render_stateware_whitepaper_v12 import (
    EXPECTED_COMMITTED_SHELL_SHA256,
    ROOT,
    SOURCE,
    TARGET,
    _committed_shell,
    render,
)


V11_HASHES = {
    ROOT / "papers" / "stateware-whitepaper-public-v1.1.md":
        "fe0c3dbd7aeb5b30c479ce4ed7d65d5aea2a71a755f9b9e5c722f88ca1b32c36",
}

REQUIRED_CLAIMS = (
    "canonical state is the durable application boundary, not the totality",
    "stateport owns intent, authority, canonical state, evidence, and acceptance",
    "the harness owns execution behavior",
    "application plane",
    "execution plane",
    "supervised-direct",
    "human-on-the-loop",
    "behavioral equivalence",
    "security equivalence",
    "evidence equivalence",
    "remoteworkspacecanonical: false",
    "private review candidate",
    "not qualified as current supported execution paths",
    "a filesystem restore also cannot unsend a message",
)

FORBIDDEN_CLAIMS = (
    "replaceable processor",
    "replaceable processors",
    "swap the agent",
    "copy, not a migration",
    "switching engines is a configuration act",
    "a model that cannot execute cannot execute badly",
    "an application is its state",
    "same behavior across hosts",
)

PRIMARY_REFERENCE_HOSTS = {
    "airc.nist.gov",
    "developers.openai.com",
    "docs.github.com",
    "eur-lex.europa.eu",
    "git-scm.com",
    "opencode.ai",
    "specs.opencontainers.org",
    "www.inkandswitch.com",
    "www.sqlite.org",
    "www.w3.org",
}


def fail(message: str) -> None:
    raise AssertionError(message)


def _normalized_heading(value: str) -> str:
    return unescape(re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", value))).strip()


def main() -> int:
    try:
        for path, expected in V11_HASHES.items():
            actual = sha256(path.read_bytes()).hexdigest()
            if actual != expected:
                fail(f"immutable v1.1 changed: {path.relative_to(ROOT)} ({actual})")
        committed_shell_hash = sha256(_committed_shell().encode("utf-8")).hexdigest()
        if committed_shell_hash != EXPECTED_COMMITTED_SHELL_SHA256:
            fail("pinned v1.1 HTML shell differs from the renderer pin")

        markdown = SOURCE.read_text(encoding="utf-8")
        html = TARGET.read_text(encoding="utf-8")
        expected_html = render()
        if html != expected_html:
            fail("v1.2 HTML is not the deterministic render of v1.2 Markdown")

        lowered = re.sub(r"\s+", " ", re.sub(r"\s*>\s*", " ", markdown.lower()))
        for claim in REQUIRED_CLAIMS:
            if claim not in lowered:
                fail(f"required v1.2 claim boundary is absent: {claim!r}")
        for claim in FORBIDDEN_CLAIMS:
            if claim in lowered:
                fail(f"stale or false claim remains in v1.2: {claim!r}")

        article_match = re.search(
            r'<article class="prose paper-prose">(?P<body>.*?)</article>',
            html,
            re.DOTALL,
        )
        if article_match is None:
            fail("rendered HTML has no paper article")
        article = article_match.group("body")

        markdown_headings = [
            (len(match.group(1)), match.group(2).strip())
            for match in re.finditer(r"^(#+)\s+(.+)$", markdown, re.MULTILINE)
        ]
        html_headings = [
            (int(match.group(1)), _normalized_heading(match.group(2)))
            for match in re.finditer(
                r"<h([1-6])\b[^>]*>(.*?)</h\1>", article, re.DOTALL
            )
        ]
        expected_headings = [
            (level + 1, re.sub(r"[*_`]", "", text))
            for level, text in markdown_headings
        ]
        if html_headings != expected_headings:
            fail(
                "Markdown/HTML heading structure differs:\n"
                f"source={expected_headings!r}\nrender={html_headings!r}"
            )

        ids = re.findall(r'(?<![-\w:])id="([^"]+)"', article)
        duplicates = sorted({item for item in ids if ids.count(item) > 1})
        if duplicates:
            fail(f"duplicate article IDs: {', '.join(duplicates)}")

        markdown_images = re.findall(r"!\[[^\]]*\]\(([^)]+)\)", markdown)
        html_images = re.findall(r'<img\s+src="([^"]+)"', article)
        if markdown_images != html_images:
            fail(
                "Markdown/HTML image sequence differs: "
                f"source={markdown_images!r} render={html_images!r}"
            )
        for relative in markdown_images:
            if not (SOURCE.parent / relative).is_file():
                fail(f"paper image is missing: {relative}")

        source_mermaid = len(re.findall(r"^```mermaid$", markdown, re.MULTILINE))
        rendered_mermaid = len(re.findall(r'<figure class="diagram-figure">', article))
        if source_mermaid != rendered_mermaid:
            fail(
                f"Mermaid block count differs: source={source_mermaid} "
                f"render={rendered_mermaid}"
            )
        for index in range(1, source_mermaid + 1):
            svg_id = f"stateware-v12-diagram-{index}"
            if f'<svg id="{svg_id}" aria-labelledby="{svg_id}-title"' not in article:
                fail(f"accessible inline SVG is missing: {svg_id}")
        if '<pre class="mermaid"><code>' in article:
            fail("an unrendered Mermaid diagram remains in the HTML candidate")

        # Multiline footnotes make a direct regex fragile; inspect every HTTPS URL
        # in the source and require the deliberately small primary-source set.
        all_urls = sorted(set(re.findall(r"https://[^)\s]+", markdown)))
        if len(all_urls) < 10:
            fail(f"expected at least ten primary references, found {len(all_urls)}")
        for url in all_urls:
            parsed = urlparse(url)
            if parsed.hostname not in PRIMARY_REFERENCE_HOSTS:
                fail(f"unapproved reference host: {url}")
            if any(key.startswith("utm_") for key, _ in parse_qsl(parsed.query)):
                fail(f"tracking parameter in reference URL: {url}")

        if "Lennert Van Hoyweghen" not in html:
            fail("rendered candidate omits the author")
        if '<meta name="robots" content="noindex, nofollow">' not in html:
            fail("rendered private candidate lacks noindex/nofollow metadata")
        if "Section</p>\n<ol" in article:
            fail("paragraph text was accidentally parsed as an ordered list")
        if "public v1.1" not in html or "does not replace" not in html:
            fail("rendered candidate does not preserve the v1.1 publication boundary")

    except (AssertionError, OSError, RuntimeError) as error:
        print(f"Stateware v1.2 validation failed: {error}", file=sys.stderr)
        return 1

    print(
        "Stateware v1.2 source/render, v1.1 immutability, structure, claims, "
        "assets, and primary-reference boundary passed"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
