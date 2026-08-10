"""WCAG contrast contract for the frozen UX-mission brief.

The test reads design-token values from ``assets/site.css`` at run time — it
never hardcodes colors — so it keeps enforcing the contract across the visual
rewrite. Contract (frozen brief, "Contrast contract" section):

- normal text: target >= 7:1 (WCAG AAA; the site's stated goal)
- large text (>= 24px, or >= 19px bold): >= 4.5:1, only via the documented
  exception list below
- focus indicators and functional UI boundaries: >= 3:1 on every surface
  where they appear (paper AND night surfaces)

Token names follow the current ``:root`` block. If the visual worker renames a
token, this test fails closed with a "token not found" message and must be
updated in the same change that renames it.
"""

from __future__ import annotations

import re
import sys
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
ROOT = SCRIPTS.parent
sys.path.insert(0, str(SCRIPTS))

from validate_repo import contrast_ratio, css_variable_hex

CSS = (ROOT / "assets/site.css").read_text(encoding="utf-8")

NORMAL_TEXT = 7.0
LARGE_TEXT = 4.5
UI_BOUNDARY = 3.0

# Foreground/background token pairs used for text, per the frozen brief:
# "muted/ink/blue-deep on paper, paper-deep, night surfaces". Dark-surface
# pairs keep the site's best property (8.8-18.4:1) and must not regress.
TEXT_PAIRS: tuple[tuple[str, str, float], ...] = (
    ("--ink", "--paper", NORMAL_TEXT),
    ("--ink", "--paper-deep", NORMAL_TEXT),
    ("--muted", "--paper", NORMAL_TEXT),
    ("--muted", "--paper-deep", NORMAL_TEXT),
    ("--blue-deep", "--paper", NORMAL_TEXT),
    ("--blue-deep", "--paper-deep", NORMAL_TEXT),
    ("--white", "--night", NORMAL_TEXT),
    ("--white", "--night-soft", NORMAL_TEXT),
    ("--paper", "--night", NORMAL_TEXT),
    ("--paper", "--night-soft", NORMAL_TEXT),
)

# Documented exceptions: large text or link affordances may sit at >= 4.5:1
# instead of 7:1. Each entry must carry a reason; keep this list short.
# The brief allows links to stay >= 4.5:1 while small text is raised to >= 7.
EXCEPTIONS: dict[tuple[str, str], str] = {}

# Focus-indicator contract: the ring must reach >= 3:1 on both the paper and
# night families. The brief mandates a context-aware dual-tone treatment
# (cyan on dark surfaces, dark ink/blue on light surfaces), so individual
# colors are allowed to pass on only one family as long as each family is
# covered by at least one declared focus color.
LIGHT_SURFACES = ("--paper", "--paper-deep")
DARK_SURFACES = ("--night", "--night-soft")


def token_hex(token: str) -> tuple[int, int, int]:
    try:
        return css_variable_hex(CSS, token)
    except AssertionError as exc:
        raise AssertionError(
            f"design token {token} not found as a six-digit hex in assets/site.css; "
            "update the contrast contract in the same change that renames it"
        ) from exc


def collect_focus_colors(css: str) -> list[tuple[int, int, int]]:
    """Resolve every solid color declared in :focus-visible/:focus outlines."""
    tokens = dict(re.findall(r"(--[a-z0-9-]+)\s*:\s*(#[0-9a-fA-F]{6})\s*;", css))
    colors: list[tuple[int, int, int]] = []
    for rule in re.finditer(
        r"[^{}]*:focus(?:-visible)?[^{}]*\{(?P<body>[^}]*)\}", css
    ):
        body = rule.group("body")
        for outline in re.finditer(r"outline\s*:[^;]*;", body):
            declaration = outline.group(0)
            hex_match = re.search(r"#[0-9a-fA-F]{6}", declaration)
            var_match = re.search(r"var\((--[a-z0-9-]+)\)", declaration)
            if hex_match:
                value = hex_match.group(0).lstrip("#")
                colors.append(tuple(int(value[i : i + 2], 16) for i in range(0, 6, 2)))
            elif var_match and var_match.group(1) in tokens:
                value = tokens[var_match.group(1)].lstrip("#")
                colors.append(tuple(int(value[i : i + 2], 16) for i in range(0, 6, 2)))
    return colors


class ContrastContractTests(unittest.TestCase):
    def test_text_token_pairs_meet_wcag_targets(self) -> None:
        failures: list[str] = []
        for foreground, background, target in TEXT_PAIRS:
            ratio = contrast_ratio(token_hex(foreground), token_hex(background))
            exception = EXCEPTIONS.get((foreground, background))
            minimum = LARGE_TEXT if exception else target
            if ratio < minimum:
                failures.append(
                    f"{foreground} on {background}: {ratio:.2f}:1 "
                    f"(target {target}:1"
                    + (f", exception {exception!r} allows {LARGE_TEXT}:1)" if exception else ")")
                )
        self.assertEqual(
            failures,
            [],
            "text contrast below the frozen brief contract:\n" + "\n".join(failures),
        )

    def test_focus_indicator_covers_paper_and_night_surfaces(self) -> None:
        colors = collect_focus_colors(CSS)
        self.assertTrue(
            colors, "no solid outline color found in any :focus/:focus-visible rule"
        )
        for family_name, surfaces in (("paper", LIGHT_SURFACES), ("night", DARK_SURFACES)):
            for surface in surfaces:
                best = max(contrast_ratio(color, token_hex(surface)) for color in colors)
                self.assertGreaterEqual(
                    best,
                    UI_BOUNDARY,
                    f"no focus-indicator color reaches {UI_BOUNDARY}:1 on {surface} "
                    f"({family_name} surface; best {best:.2f}:1)",
                )

    def test_exceptions_stay_documented_and_minimal(self) -> None:
        for pair, reason in EXCEPTIONS.items():
            self.assertIn(pair, TEXT_PAIRS, f"exception for unknown pair {pair}")
            self.assertTrue(reason.strip(), f"exception {pair} lacks a reason")
            ratio = contrast_ratio(token_hex(pair[0]), token_hex(pair[1]))
            self.assertGreaterEqual(
                ratio,
                LARGE_TEXT,
                f"exception {pair} is below the large-text floor: {ratio:.2f}:1",
            )


if __name__ == "__main__":
    unittest.main()
