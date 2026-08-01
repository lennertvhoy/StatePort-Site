#!/usr/bin/env python3
"""Render the Stateware whitepaper Mermaid blocks to inline SVG.

Reproducible build-time step (no visitor-runtime dependency):

  papers/*.md  ```mermaid blocks   --mmdc-->  scoped inline <svg>
                                          -> assets/diagrams/src/paper/*.mmd

The Markdown stays the source of truth (and renders natively on GitHub).
This script renders each block to a static SVG with the project theme,
scopes every internal id so multiple inline diagrams never collide, and
inlines the result into the corresponding paper HTML. The public site
therefore displays the diagrams with zero client-side JavaScript and no
third-party runtime, consistent with the site's static-first policy.

Re-run from the repo root:

  python3 scripts/render_paper_diagrams.py

Requires the `mmdc` (mermaid-cli) executable and a Chrome/Chromium binary
discovered automatically or via the MMDC_CHROME_BIN environment variable.
"""
from __future__ import annotations

import html
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PAPERS = ROOT / "papers"
MMD_SRC_DIR = ROOT / "assets" / "diagrams" / "src" / "paper"
THEME_CONFIG = ROOT / "config" / "mermaid-theme.json"

PAPERS_TO_RENDER = (
    "stateware-whitepaper-public-v1.1",
    "stateware-whitepaper-candidate-v1.2",
)

MERMAID_FENCE = re.compile(r"```mermaid\n(.*?)```", re.DOTALL)
# Matches either an unrendered mermaid pre block or an already-rendered
# figure (so re-runs regenerate diagrams in place).
DIAGRAM_SLOT = re.compile(
    r"<pre class=\"mermaid\"><code>.*?</code></pre>"
    r"|<figure class=\"paper-diagram\"[^>]*>.*?</figure>",
    re.DOTALL,
)
SVG_ID_ATTR = re.compile(r"\sid=\"([^\"]+)\"")


def extract_mermaid_blocks(markdown: str) -> list[str]:
    blocks = MERMAID_FENCE.findall(markdown)
    if not blocks:
        raise AssertionError("no ```mermaid blocks found in markdown source")
    return [b.strip() + "\n" for b in blocks]


def detect_chrome() -> str | None:
    env = os.environ.get("MMDC_CHROME_BIN")
    if env and Path(env).exists():
        return env
    for candidate in (
        "/usr/bin/google-chrome-stable",
        "/usr/bin/google-chrome",
        "/opt/google/chrome/chrome",
        "/usr/bin/chromium-browser",
        "/usr/bin/chromium",
    ):
        if Path(candidate).exists():
            return candidate
    return None


def render_svg(source: str, out_svg: Path, work: Path) -> None:
    mmd = work / "diagram.mmd"
    mmd.write_text(source, encoding="utf-8")
    cmd: list[str] = [
        "mmdc",
        "-i", str(mmd),
        "-o", str(out_svg),
        "-c", str(THEME_CONFIG),
        "--backgroundColor", "transparent",
        "-q",
    ]
    chrome = detect_chrome()
    if chrome:
        pptr = work / "puppeteer.json"
        pptr.write_text(
            '{"executablePath": "' + chrome + '", "args": ["--no-sandbox"]}\n',
            encoding="utf-8",
        )
        cmd += ["--puppeteerConfigFile", str(pptr)]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0 or not out_svg.is_file():
        raise AssertionError(
            "mmdc failed:\n" + result.stderr.strip()
        )


def scope_svg_ids(svg: str, prefix: str) -> str:
    """Prefix every internal id and reference so inline diagrams never clash."""
    # The root element and its CSS self-references (e.g. "#my-svg .node")
    # must rename together, or the theme styles orphan.
    svg = svg.replace('id="my-svg"', 'id="' + prefix + 'svg"')
    svg = svg.replace("#my-svg", "#" + prefix + "svg")
    ids = SVG_ID_ATTR.findall(svg)
    for value in sorted(set(ids), key=len, reverse=True):
        if value.startswith(prefix):
            continue
        svg = svg.replace('"' + value + '"', '"' + prefix + value + '"')
    svg = svg.replace("url(#", "url(#" + prefix)
    svg = svg.replace("href=\"#", "href=\"#" + prefix)
    return svg


def finalize_svg(svg: str, prefix: str) -> str:
    svg = scope_svg_ids(svg, prefix)
    # Preserve the diagram's natural pixel size (keeps label text legible)
    # instead of forcing width:100%, which would shrink wide diagrams.
    width_match = re.search(r"max-width:\s*([\d.]+)px", svg)
    if width_match:
        svg = svg.replace('width="100%"', 'width="' + width_match.group(1) + '"', 1)
    svg = svg.replace(
        "<svg ",
        '<svg role="img" aria-hidden="true" focusable="false" ',
        1,
    )
    svg = svg.replace('class="flowchart"', 'class="flowchart paper-diagram__svg"', 1)
    return svg


def guess_label(source: str) -> str:
    """Best-effort short accessible label from the first labelled node."""
    for line in source.splitlines():
        text = line.strip()
        if not text or text.startswith(("flowchart", "graph", "%%")):
            continue
        quoted = re.search(r'"([^"]+)"', text)
        if quoted:
            label = quoted.group(1)
            break
        bracket = re.search(r"\[([^\[\]]+)\]", text)
        if bracket:
            label = bracket.group(1)
            break
    else:
        label = "Diagram"
    # Strip mermaid line breaks and any residual markup for screen readers.
    label = re.sub(r"<br\s*/?>", " ", label, flags=re.IGNORECASE)
    label = re.sub(r"<[^>]+>", "", label)
    label = html.unescape(label)
    return re.sub(r"\s+", " ", label).strip()


def build_figure(svg: str, mermaid_id: str, label: str) -> str:
    return (
        '<figure class="paper-diagram" role="img" aria-label="'
        + html.escape(label)
        + '" data-mermaid-id="'
        + mermaid_id
        + '">\n'
        + svg.strip()
        + "\n</figure>"
    )


def slugify(stem: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", stem.lower()).strip("-")


def render_paper(stem: str, work: Path) -> None:
    md_path = PAPERS / (stem + ".md")
    html_path = PAPERS / (stem + ".html")
    if not md_path.is_file() or not html_path.is_file():
        raise AssertionError(f"missing paper pair for {stem}")

    slug = slugify(stem)
    MMD_SRC_DIR.mkdir(parents=True, exist_ok=True)

    blocks = extract_mermaid_blocks(md_path.read_text(encoding="utf-8"))
    figures: list[str] = []

    for index, source in enumerate(blocks, start=1):
        mermaid_id = f"{slug}-{index:02d}"
        mmd_src = MMD_SRC_DIR / (mermaid_id + ".mmd")
        mmd_src.write_text(source, encoding="utf-8")

        svg_path = work / (mermaid_id + ".svg")
        render_svg(source, svg_path, work)
        svg = finalize_svg(svg_path.read_text(encoding="utf-8"), mermaid_id.replace("-", "_") + "_")
        figures.append(build_figure(svg, mermaid_id, guess_label(source)))
        print(f"  rendered {mermaid_id}")

    page = html_path.read_text(encoding="utf-8")
    slots = list(DIAGRAM_SLOT.finditer(page))
    if len(slots) != len(figures):
        raise AssertionError(
            f"{stem}: found {len(slots)} diagram slots but {len(figures)} mermaid blocks"
        )

    cursor = 0
    out_parts: list[str] = []
    for match, figure in zip(DIAGRAM_SLOT.finditer(page), figures):
        out_parts.append(page[cursor:match.start()])
        out_parts.append(figure)
        cursor = match.end()
    out_parts.append(page[cursor:])
    html_path.write_text("".join(out_parts), encoding="utf-8")
    print(f"  inlined {len(figures)} diagrams into {html_path.relative_to(ROOT)}")


def main() -> None:
    if not shutil.which("mmdc"):
        sys.exit("missing required tool: mmdc (npm i -g @mermaid-js/mermaid-cli)")
    if not THEME_CONFIG.is_file():
        sys.exit(f"missing theme config: {THEME_CONFIG.relative_to(ROOT)}")
    work = Path(tempfile.mkdtemp(prefix="paper-diagrams-"))
    try:
        for stem in PAPERS_TO_RENDER:
            print(f"rendering {stem}")
            render_paper(stem, work)
    finally:
        shutil.rmtree(work, ignore_errors=True)
    print("Paper diagram render: OK")


if __name__ == "__main__":
    main()
