#!/usr/bin/env python3
"""Build Stateware diagrams for static, JavaScript-free reading.

The current public paper is rebuilt from Markdown using Pandoc and Mermaid CLI.
Diagrams become isolated SVG image files with accessible descriptions and links
back to their Mermaid sources. SVG-local styles and IDs do not enter the page.

  python3 scripts/render_paper_diagrams.py --paper stateware-whitepaper-public-v1.1

Requires pandoc, mmdc, and a Chrome/Chromium executable (or MMDC_CHROME_BIN).
Without --paper, both papers render; the historical candidate retains its legacy
inline-SVG rendering path. Its content is not rebuilt from Markdown.
"""
from __future__ import annotations

import html
import argparse
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


def render_svg(source: str, out_svg: Path, work: Path, theme_config: Path = THEME_CONFIG) -> None:
    mmd = work / "diagram.mmd"
    mmd.write_text(source, encoding="utf-8")
    cmd: list[str] = [
        "mmdc",
        "-i", str(mmd),
        "-o", str(out_svg),
        "-c", str(theme_config),
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
    if stem == "stateware-whitepaper-public-v1.1":
        render_public_paper(stem, work)
        return
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


def render_public_paper(stem: str, work: Path) -> None:
    """Build the current paper from Markdown, with isolated SVG image assets.

    SVG image documents keep Mermaid's style and marker IDs local to each image.
    This avoids both the page CSP rejecting inline styles and IDs colliding when
    several Mermaid diagrams share a page. No visitor JavaScript is required.
    """
    md_path = PAPERS / f"{stem}.md"
    html_path = PAPERS / f"{stem}.html"
    markdown = md_path.read_text(encoding="utf-8")
    body = subprocess.run(
        ["pandoc", "--from=markdown", "--to=html5", "--shift-heading-level-by=1"],
        input=markdown, text=True, capture_output=True, check=True,
    ).stdout
    asset_dir = ROOT / "assets/diagrams/paper"
    asset_dir.mkdir(parents=True, exist_ok=True)
    MMD_SRC_DIR.mkdir(parents=True, exist_ok=True)
    figures = []
    for index, source in enumerate(extract_mermaid_blocks(markdown), start=1):
        diagram_id = f"{slugify(stem)}-{index:02d}"
        title = re.search(r"^\s*accTitle:\s*(.+)$", source, re.MULTILINE)
        description = re.search(r"^\s*accDescr:\s*(.+)$", source, re.MULTILINE)
        if not title or not description:
            raise AssertionError(f"{diagram_id}: provide an accessible title and description")
        (MMD_SRC_DIR / f"{diagram_id}.mmd").write_text(source, encoding="utf-8")
        target = asset_dir / f"{diagram_id}.svg"
        render_svg(source, target, work, ROOT / "config/mermaid-paper-theme.json")
        svg = target.read_text(encoding="utf-8")
        bounds = re.search(r'viewBox="([\d. -]+)"', svg)
        if not bounds:
            raise AssertionError(f"{diagram_id}: missing SVG dimensions")
        _, _, width, height = map(float, bounds[1].split())
        target.write_text(svg.replace('width="100%"', f'width="{width}"', 1), encoding="utf-8")
        image_url = f"../assets/diagrams/paper/{diagram_id}.svg"
        source_url = f"../assets/diagrams/src/paper/{diagram_id}.mmd"
        label = html.escape(title[1], quote=True)
        alt = html.escape(description[1], quote=True)
        figures.append(
            f'<figure class="paper-diagram" id="figure-{index}" data-mermaid-id="{diagram_id}">\n'
            f'  <div class="paper-diagram-scroll" tabindex="0" role="region" aria-label="Figure {index}: {label}">\n'
            f'    <img src="{image_url}" alt="{alt}" width="{round(width)}" height="{round(height)}" loading="lazy">\n'
            f'  </div>\n'
            f'  <figcaption><strong>Figure {index}. {label}</strong>'
            f'<span class="paper-diagram-links"><a href="{image_url}">Open full diagram</a> · '
            f'<a href="{source_url}">Mermaid source</a></span></figcaption>\n'
            f'</figure>'
        )
        print(f"  rendered {diagram_id}: {width:.0f} × {height:.0f}")
    slots = list(DIAGRAM_SLOT.finditer(body))
    if len(slots) != len(figures):
        raise AssertionError("Markdown render lost diagram slots")
    replacements = iter(figures)
    body = DIAGRAM_SLOT.sub(lambda _: next(replacements), body)
    # Preserve section URLs from the previous public revision.
    body = body.replace('id="projectstate-developing-and-operating-projects"',
                        'id="projectstate-coordinating-development-without-coupling-the-runtime"')
    body = body.replace('id="development-and-operating-use"', 'id="the-two-uses-of-projectstate"')
    page = html_path.read_text(encoding="utf-8")
    start = page.index('<article class="prose paper-prose">')
    start = page.index('<h2 ', start)
    finish = page.index('</article>', start)
    html_path.write_text(page[:start] + body + page[finish:], encoding="utf-8")
    print(f"  rebuilt public paper with {len(figures)} static diagrams")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--paper", choices=PAPERS_TO_RENDER, action="append",
                        help="Render only the named paper; repeat to select more than one")
    args = parser.parse_args()
    if not shutil.which("mmdc"):
        sys.exit("missing required tool: mmdc (npm i -g @mermaid-js/mermaid-cli)")
    if not THEME_CONFIG.is_file():
        sys.exit(f"missing theme config: {THEME_CONFIG.relative_to(ROOT)}")
    work = Path(tempfile.mkdtemp(prefix="paper-diagrams-"))
    try:
        for stem in args.paper or PAPERS_TO_RENDER:
            print(f"rendering {stem}")
            render_paper(stem, work)
    finally:
        shutil.rmtree(work, ignore_errors=True)
    print("Paper diagram render: OK")


if __name__ == "__main__":
    main()
