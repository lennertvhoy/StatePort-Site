#!/usr/bin/env python3
"""Render the Stateware v1.2 review candidate deterministically.

The public v1.1 Markdown and HTML are immutable inputs.  The existing HTML is
used only as the established site shell; all v1.2 article content comes from the
v1.2 Markdown source.  ``--check`` renders in memory and fails on drift.
"""

from __future__ import annotations

import argparse
from hashlib import sha256
from html import escape, unescape
import os
from pathlib import Path
import re
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "papers" / "stateware-whitepaper-public-v1.2.md"
TARGET = ROOT / "papers" / "stateware-whitepaper-public-v1.2.html"
EXPECTED_PANDOC = "pandoc 3.7.0.2"
EXPECTED_MMDC = "11.12.0"
CHROMIUM = Path("/usr/bin/chromium-browser")
EXPECTED_CHROMIUM = "Chromium 150.0.7871.181 Built from source for Fedora release 44 (Forty Four)"
PINNED_SHELL_COMMIT = "92d134bde6e13752cc05e26b6685b694b7670d9c"
EXPECTED_COMMITTED_SHELL_SHA256 = (
    "239bc94c7925a57f4c02424978c3863c766776290b29f87226b5e041613ee51a"
)
DIAGRAM_LABELS = (
    "An identified application definition is installed as an owned instance. "
    "A runtime receives a versioned projection and returns a candidate and "
    "evidence without promoting or accepting itself.",
    "The application plane supplies purpose and continuity. StatePort owns the "
    "seam to an execution plane made of an adapter, opinionated harness, and "
    "operating environment.",
)


class RenderError(RuntimeError):
    """Raised when the candidate cannot be rendered without ambiguity."""


def _metadata(markdown: str) -> dict[str, str]:
    match = re.match(r"\A---\n(?P<body>.*?)\n---\n", markdown, re.DOTALL)
    if match is None:
        raise RenderError("v1.2 Markdown must start with YAML front matter")

    values: dict[str, str] = {}
    for line in match.group("body").splitlines():
        key, separator, raw = line.partition(":")
        if not separator:
            raise RenderError(f"unsupported front-matter line: {line!r}")
        value = raw.strip()
        if len(value) >= 2 and value[0] == value[-1] == '"':
            value = value[1:-1].replace(r'\"', '"')
        values[key.strip()] = value

    required = {"title", "subtitle", "version", "date", "author", "status"}
    missing = sorted(required - values.keys())
    if missing:
        raise RenderError(f"missing front-matter keys: {', '.join(missing)}")
    if values["version"] != "1.2 candidate":
        raise RenderError("version must remain '1.2 candidate' before publication")
    if values["status"] != "Private review candidate — not published":
        raise RenderError("candidate status was weakened or changed")
    return values


def _replace_once(text: str, pattern: str, replacement: str) -> str:
    result, count = re.subn(pattern, replacement, text, count=1, flags=re.DOTALL)
    if count != 1:
        raise RenderError(f"site-shell pattern matched {count} times: {pattern}")
    return result


def _pandoc_fragment(markdown: str) -> str:
    version = subprocess.run(
        ["pandoc", "--version"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.splitlines()[0]
    if version != EXPECTED_PANDOC:
        raise RenderError(
            f"expected {EXPECTED_PANDOC!r}, found {version!r}; "
            "use the pinned renderer or review and update the pin explicitly"
        )

    completed = subprocess.run(
        [
            "pandoc",
            "--from=markdown+smart",
            "--to=html5",
            "--shift-heading-level-by=1",
            "--wrap=none",
            "--eol=lf",
        ],
        input=markdown,
        check=True,
        capture_output=True,
        text=True,
    )
    fragment = completed.stdout.strip()
    if not fragment.startswith('<h2 id="abstract-thesis-and-standing">'):
        raise RenderError("unexpected first rendered heading")
    if '<h2 id="a-note-on-authorship">' not in fragment:
        raise RenderError("rendered article is missing the authorship section")
    return _render_diagrams(fragment)


def _namespace_svg_ids(svg: str, namespace: str) -> str:
    """Make Mermaid's internal SVG IDs unique in the combined HTML document."""

    ids = re.findall(r'(?<![-\w:])id="([^"]+)"', svg)
    if not ids or ids[0] != namespace:
        raise RenderError(f"diagram root ID differs from {namespace!r}")
    internal_ids = ids[1:]
    duplicates = sorted(
        {item for item in internal_ids if internal_ids.count(item) > 1}
    )
    if duplicates:
        raise RenderError(
            f"Mermaid produced duplicate IDs inside {namespace}: "
            f"{', '.join(duplicates)}"
        )

    for old in sorted(internal_ids, key=len, reverse=True):
        new = f"{namespace}-{old}"
        svg, replacements = re.subn(
            rf'(?<![-\w:])id="{re.escape(old)}"',
            f'id="{new}"',
            svg,
        )
        if replacements != 1:
            raise RenderError(
                f"expected one ID declaration for {old!r}, found {replacements}"
            )
        svg = re.sub(
            rf'#{re.escape(old)}(?![A-Za-z0-9_.:-])',
            f"#{new}",
            svg,
        )
    return svg


def _render_diagrams(fragment: str) -> str:
    version = subprocess.run(
        ["mmdc", "--version"], check=True, capture_output=True, text=True
    ).stdout.strip()
    if version != EXPECTED_MMDC:
        raise RenderError(
            f"expected Mermaid CLI {EXPECTED_MMDC!r}, found {version!r}"
        )
    if not CHROMIUM.is_file():
        raise RenderError(f"pinned Chromium is absent: {CHROMIUM}")
    chromium_version = subprocess.run(
        [str(CHROMIUM), "--version"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    if chromium_version != EXPECTED_CHROMIUM:
        raise RenderError(
            f"expected {EXPECTED_CHROMIUM!r}, found {chromium_version!r}"
        )

    matches = list(
        re.finditer(r'<pre class="mermaid"><code>(.*?)</code></pre>', fragment, re.DOTALL)
    )
    if len(matches) != len(DIAGRAM_LABELS):
        raise RenderError(
            f"expected {len(DIAGRAM_LABELS)} Mermaid diagrams, found {len(matches)}"
        )

    environment = os.environ.copy()
    environment["PUPPETEER_EXECUTABLE_PATH"] = str(CHROMIUM)
    replacements: list[str] = []
    for index, (match, label) in enumerate(zip(matches, DIAGRAM_LABELS), start=1):
        source = unescape(match.group(1)).strip() + "\n"
        svg_id = f"stateware-v12-diagram-{index}"
        title_id = f"{svg_id}-title"
        completed = subprocess.run(
            [
                "mmdc",
                "--quiet",
                "--input",
                "-",
                "--output",
                "-",
                "--outputFormat",
                "svg",
                "--theme",
                "neutral",
                "--backgroundColor",
                "transparent",
                "--svgId",
                svg_id,
            ],
            input=source,
            check=True,
            capture_output=True,
            text=True,
            env=environment,
        )
        svg = completed.stdout.strip()
        if not svg.startswith(f'<svg id="{svg_id}"'):
            raise RenderError(f"unexpected SVG root for diagram {index}")
        svg = _namespace_svg_ids(svg, svg_id)
        svg = svg.replace(
            f'<svg id="{svg_id}"',
            f'<svg id="{svg_id}" aria-labelledby="{title_id}"',
            1,
        )
        opening_end = svg.find(">")
        if opening_end < 0:
            raise RenderError(f"diagram {index} has no SVG opening tag")
        svg = (
            svg[: opening_end + 1]
            + f'<title id="{title_id}">{escape(label)}</title>'
            + svg[opening_end + 1 :]
        )
        replacements.append(
            '<figure class="diagram-figure">\n'
            f"{svg}\n"
            f"<figcaption>{escape(label)}</figcaption>\n"
            "<details><summary>Diagram source</summary>"
            f"<pre><code>{escape(source.rstrip())}</code></pre></details>\n"
            "</figure>"
        )

    pieces: list[str] = []
    cursor = 0
    for match, replacement in zip(matches, replacements):
        pieces.append(fragment[cursor : match.start()])
        pieces.append(replacement)
        cursor = match.end()
    pieces.append(fragment[cursor:])
    return "".join(pieces)


def _committed_shell() -> str:
    """Read the pinned clean shell from Git, never a current v1.1 reader."""

    completed = subprocess.run(
        [
            "git",
            "show",
            f"{PINNED_SHELL_COMMIT}:papers/stateware-whitepaper-public-v1.1.html",
        ],
        cwd=ROOT,
        check=True,
        capture_output=True,
    )
    actual = sha256(completed.stdout).hexdigest()
    if actual != EXPECTED_COMMITTED_SHELL_SHA256:
        raise RenderError(
            "pinned v1.1 shell identity changed; review the shell and update "
            "the renderer pin explicitly"
        )
    return completed.stdout.decode("utf-8")


def render() -> str:
    markdown = SOURCE.read_text(encoding="utf-8")
    metadata = _metadata(markdown)
    fragment = _pandoc_fragment(markdown)
    document = _committed_shell()

    document = document.replace(
        "stateware-whitepaper-public-v1.1", "stateware-whitepaper-public-v1.2"
    )
    document = _replace_once(
        document,
        r'(<meta name="viewport" content="width=device-width, initial-scale=1">)',
        r'\1\n    <meta name="robots" content="noindex, nofollow">',
    )
    document = _replace_once(
        document,
        r'<meta name="description" content=".*?">',
        '<meta name="description" content="Stateware v1.2 private review candidate: canonical state as the durable application boundary, with explicit execution-provider limits.">',
    )
    document = _replace_once(
        document,
        r"<title>.*?</title>",
        f"<title>{escape(metadata['title'])} — StatePort</title>",
    )
    document = _replace_once(
        document,
        r'<p class="document-kicker">.*?</p>',
        '<p class="document-kicker">Private review candidate / 1.2</p>',
    )
    document = _replace_once(
        document,
        r'<h1 id="paper-title">.*?</h1>',
        f'<h1 id="paper-title">{escape(metadata["title"])}</h1>',
    )
    document = _replace_once(
        document,
        r'(<h1 id="paper-title">.*?</h1>\s*)<p>.*?</p>',
        rf"\1<p>{escape(metadata['subtitle'])}</p>",
    )
    document = document.replace(">Read online<", ">Read candidate<", 1)

    notice = (
        '<p class="notice notice--quiet"><strong>Candidate note</strong> '
        f'Private Stateware review candidate, version 1.2 ({escape(metadata["date"])}), '
        f'by {escape(metadata["author"])}. It does not replace '
        '<a href="./stateware-whitepaper-public-v1.1.html">public v1.1</a> or '
        'establish software availability; <a href="../releases/">availability '
        "lives in the release ledger</a>.</p>"
    )
    generated = (
        "        <article class=\"prose paper-prose\">\n"
        "          <!-- Generated by scripts/render_stateware_whitepaper_v12.py "
        f"with {EXPECTED_PANDOC}; edit the Markdown source, not this fragment. -->\n"
        f"          {notice}\n"
        f"{fragment}\n"
        "        </article>"
    )
    document = _replace_once(
        document,
        r'\s*<article class="prose paper-prose">.*?</article>',
        "\n" + generated,
    )

    if "replaceable processor" in document.lower():
        raise RenderError("stale replaceable-processor claim survived rendering")
    if "Private review candidate / 1.2" not in document:
        raise RenderError("candidate label is absent from the rendered page")
    if '<meta name="robots" content="noindex, nofollow">' not in document:
        raise RenderError("private candidate is missing its noindex boundary")
    return document.rstrip() + "\n"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--check",
        action="store_true",
        help="fail if the checked-in HTML differs from a fresh in-memory render",
    )
    args = parser.parse_args()

    try:
        rendered = render()
    except (OSError, subprocess.CalledProcessError, RenderError) as error:
        print(f"paper render failed: {error}", file=sys.stderr)
        return 1

    if args.check:
        if not TARGET.exists():
            print(f"paper render drift: missing {TARGET.relative_to(ROOT)}", file=sys.stderr)
            return 1
        current = TARGET.read_text(encoding="utf-8")
        if current != rendered:
            print(
                f"paper render drift: run {Path(__file__).relative_to(ROOT)}",
                file=sys.stderr,
            )
            return 1
        print("Stateware v1.2 render is deterministic and current")
        return 0

    TARGET.write_text(rendered, encoding="utf-8", newline="\n")
    print(f"rendered {TARGET.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
