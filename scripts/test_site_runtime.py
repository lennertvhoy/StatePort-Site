from __future__ import annotations

import re
from pathlib import Path
import sys
import unittest

SCRIPTS = Path(__file__).resolve().parent
ROOT = SCRIPTS.parent
sys.path.insert(0, str(SCRIPTS))

import check_site_quality
import validate_repo


class SiteRuntimeContractTests(unittest.TestCase):
    def test_every_public_page_has_the_three_keyed_shared_assets(self) -> None:
        validate_repo.validate_asset_cache_keys()

    def test_enhancements_are_static_and_reveals_are_ready_gated(self) -> None:
        javascript = (ROOT / "assets/site.js").read_text(encoding="utf-8")
        css = (ROOT / "assets/site.css").read_text(encoding="utf-8")
        enhancements = (ROOT / "assets/site-enhancements.css").read_text(encoding="utf-8")
        self.assertNotIn('createElement("link")', javascript)
        self.assertNotIn("ensureEnhancementStyles", javascript)
        self.assertIn('root.classList.add("reveal-ready")', javascript)
        self.assertIn(".reveal-ready .reveal", css)
        self.assertNotIn("650ms", css)
        durations = [int(value) for value in re.findall(r"transition:[^;{}]*?(\d+)ms", css)]
        self.assertTrue(durations)
        self.assertLessEqual(max(durations), 280)
        self.assertIn(".js:not(.reveal-ready) .reveal", enhancements)

    def test_no_js_navigation_wraps_and_cannot_extend_the_viewport(self) -> None:
        enhancements = (ROOT / "assets/site-enhancements.css").read_text(encoding="utf-8")
        self.assertIn("overflow-x: clip", enhancements)
        no_js = enhancements[enhancements.index("html:not(.js) .site-nav"):]
        self.assertIn("flex-wrap: wrap", no_js)
        self.assertIn("white-space: normal", no_js)

    def test_actual_walkthrough_text_contrasts_on_the_dark_media_surface(self) -> None:
        css = (ROOT / "assets/site.css").read_text(encoding="utf-8")
        enhancements = (ROOT / "assets/site-enhancements.css").read_text(encoding="utf-8")
        self.assertIn(".media-player {", css)
        self.assertIn("background: var(--night);", css)
        self.assertIn(".media-player > p,\n.media-player .video-transcript summary", enhancements)
        self.assertIn("color: var(--white);", enhancements)
        self.assertGreaterEqual(
            validate_repo.contrast_ratio(
                validate_repo.css_variable_hex(css, "--white"),
                validate_repo.css_variable_hex(css, "--night"),
            ),
            7.0,
        )
        self.assertGreaterEqual(
            validate_repo.contrast_ratio((220, 229, 246), validate_repo.css_variable_hex(css, "--night")),
            7.0,
        )

    def test_plain_preview_copy_retires_unsupported_phrasing(self) -> None:
        homepage = (ROOT / "index.html").read_text(encoding="utf-8")
        walkthrough = (ROOT / "docs/prototype-walkthrough.html").read_text(encoding="utf-8")
        self.assertIn("Product walkthrough", homepage)
        self.assertIn("Development preview", walkthrough)
        self.assertIn("Ask a question", homepage)
        self.assertIn("Use the same clear view", homepage)
        self.assertIn("See an application remember", homepage)
        for text in (homepage, walkthrough):
            for retired in (
                "Product proof",
                "Ask a real question",
                "Pick up anywhere",
                "not a staged mockup",
                "compatible_unvalidated",
                "clean-install receipt",
            ):
                self.assertNotIn(retired, text)

    def test_public_media_and_caption_contracts_exclude_source_and_retired_references(self) -> None:
        documents = check_site_quality.parse_documents()
        check_site_quality.validate_public_media_boundaries(documents)
        check_site_quality.validate_video_embeds(documents)
        check_site_quality.validate_caption_files(documents)

    def test_current_media_caption_duration_is_consistent(self) -> None:
        documents = check_site_quality.parse_documents()
        check_site_quality.validate_video_caption_duration_consistency(documents)

    def test_home_gallery_has_four_items_with_the_hero_first(self) -> None:
        homepage = (ROOT / "index.html").read_text(encoding="utf-8")
        self.assertEqual(homepage.count('data-prototype-gallery-item'), 4)
        self.assertIn('data-gallery-label="StatePort application overview"', homepage)
        self.assertIn('data-prototype-gallery-counter>01 / 04', homepage)
        self.assertIn('if (!gallery || items.length !== 4', (ROOT / "assets/site.js").read_text(encoding="utf-8"))

    def test_active_surfaces_use_light_mascot_and_local_source_manifest_is_bound(self) -> None:
        documents = check_site_quality.parse_documents()
        check_site_quality.validate_mascot_surface_references(documents)
        validate_repo.validate_brand_asset_bytes()
        validate_repo.validate_mascot_size_contract()
        validate_repo.validate_active_favicons()
        validate_repo.validate_local_media_source_manifest()

    def test_linked_whitepaper_markdown_matches_current_release_boundary(self) -> None:
        check_site_quality.validate_linked_markdown_language()
        linked = validate_repo.linked_public_markdown_pages()
        self.assertIn(ROOT / "papers/stateware-whitepaper-candidate-v1.2.md", linked)


if __name__ == "__main__":
    unittest.main()
