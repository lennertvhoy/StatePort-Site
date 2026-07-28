#!/usr/bin/env python3
"""Render the fail-closed Ko-fi support links into the static homepage."""

from __future__ import annotations

import argparse
from html import escape
import json
from pathlib import Path
import re
import sys
from urllib.parse import urlsplit


ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT / "config" / "support.json"
HOME_PATH = ROOT / "index.html"

SECTION_START = "<!-- support-section-link:start -->"
SECTION_END = "<!-- support-section-link:end -->"
FOOTER_START = "<!-- support-footer-link:start -->"
FOOTER_END = "<!-- support-footer-link:end -->"


def load_config() -> dict[str, object]:
    try:
        config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"{CONFIG_PATH.relative_to(ROOT)} is not valid JSON: {exc}") from exc

    expected = {"provider", "plan", "publicUrl", "settingsAttested"}
    if set(config) != expected:
        raise ValueError(
            f"{CONFIG_PATH.relative_to(ROOT)} must contain exactly: {', '.join(sorted(expected))}"
        )
    if config["provider"] != "ko-fi" or config["plan"] != "free":
        raise ValueError("Support provider and plan must remain ko-fi Free for BL-SUPPORT-001")
    if not isinstance(config["settingsAttested"], bool):
        raise ValueError("settingsAttested must be a boolean")
    if config["publicUrl"] is not None and not isinstance(config["publicUrl"], str):
        raise ValueError("publicUrl must be null or a string")
    return config


def validate_kofi_url(value: str) -> str:
    parsed = urlsplit(value)
    if (
        not re.fullmatch(r"https://(?:www\.)?ko-fi\.com/[A-Za-z0-9_-]+/?", value)
        or
        parsed.scheme != "https"
        or parsed.hostname not in {"ko-fi.com", "www.ko-fi.com"}
        or parsed.username
        or parsed.password
        or parsed.port is not None
        or parsed.query
        or parsed.fragment
    ):
        raise ValueError(
            "publicUrl must be a direct HTTPS Ko-fi page such as https://ko-fi.com/stateport "
            "with no credentials, port, query, or fragment"
        )
    return value


def support_enabled(config: dict[str, object]) -> bool:
    url = config["publicUrl"]
    if url is not None:
        validate_kofi_url(url)
    return bool(url and config["settingsAttested"] is True)


def replace_block(document: str, start: str, end: str, content: str) -> str:
    if document.count(start) != 1 or document.count(end) != 1:
        raise ValueError(f"Expected exactly one render block bounded by {start!r} and {end!r}")
    prefix, remainder = document.split(start, 1)
    _, suffix = remainder.split(end, 1)
    return f"{prefix}{start}\n{content}\n{end}{suffix}"


def rendered_home(document: str, config: dict[str, object]) -> str:
    if support_enabled(config):
        url = escape(str(config["publicUrl"]), quote=True)
        section = (
            '            <a class="button button--ink support-link" data-support-link '
            f'href="{url}" target="_blank" rel="external noopener noreferrer">'
            'Support StatePort <span aria-hidden="true">↗</span>'
            '<span class="sr-only"> (opens in a new tab)</span></a>'
        )
        footer = (
            f'          <a data-support-link href="{url}" target="_blank" '
            'rel="external noopener noreferrer">Support StatePort'
            '<span class="sr-only"> (opens in a new tab)</span></a>'
        )
    else:
        section = ""
        footer = ""

    rendered = replace_block(document, SECTION_START, SECTION_END, section)
    return replace_block(rendered, FOOTER_START, FOOTER_END, footer)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="fail if index.html does not match config/support.json",
    )
    args = parser.parse_args()

    try:
        config = load_config()
        current = HOME_PATH.read_text(encoding="utf-8")
        expected = rendered_home(current, config)
    except (OSError, ValueError) as exc:
        print(f"Support configuration error: {exc}", file=sys.stderr)
        return 1

    if args.check:
        if current != expected:
            print(
                "index.html does not match config/support.json; run python3 scripts/render_support.py",
                file=sys.stderr,
            )
            return 1
        print("Support link render: OK")
        return 0

    HOME_PATH.write_text(expected, encoding="utf-8")
    if support_enabled(config):
        print("Rendered the attested Ko-fi Free support link into index.html")
    else:
        print("Rendered the fail-closed support state; support remains hidden")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
