from __future__ import annotations

import unittest

from scripts.render_support import (
    FOOTER_END,
    FOOTER_START,
    SECTION_END,
    SECTION_START,
    rendered_home,
    support_enabled,
    validate_kofi_url,
)


SHELL = f"{SECTION_START}\nold section\n{SECTION_END}\n{FOOTER_START}\nold footer\n{FOOTER_END}\n"


class SupportRenderTests(unittest.TestCase):
    def test_disabled_configuration_exposes_no_link(self) -> None:
        config = {
            "provider": "ko-fi",
            "plan": "free",
            "publicUrl": None,
            "settingsAttested": False,
        }
        rendered = rendered_home(SHELL, config)
        self.assertIn("data-support-pending", rendered)
        self.assertNotIn("data-support-link", rendered)
        self.assertNotIn("ko-fi.com", rendered)

    def test_url_without_settings_attestation_remains_disabled(self) -> None:
        config = {
            "provider": "ko-fi",
            "plan": "free",
            "publicUrl": "https://ko-fi.com/stateport",
            "settingsAttested": False,
        }
        self.assertFalse(support_enabled(config))
        self.assertNotIn("data-support-link", rendered_home(SHELL, config))

    def test_attested_configuration_renders_two_accessible_external_links(self) -> None:
        config = {
            "provider": "ko-fi",
            "plan": "free",
            "publicUrl": "https://ko-fi.com/stateport",
            "settingsAttested": True,
        }
        rendered = rendered_home(SHELL, config)
        self.assertEqual(rendered.count("data-support-link"), 2)
        self.assertEqual(rendered.count('target="_blank"'), 2)
        self.assertEqual(rendered.count('rel="external noopener noreferrer"'), 2)
        self.assertEqual(rendered.count("opens in a new tab"), 2)

    def test_rejects_non_kofi_or_ambiguous_destinations(self) -> None:
        invalid = (
            "http://ko-fi.com/stateport",
            "https://ko-fi.com.evil.example/stateport",
            "https://ko-fi.com/",
            "https://ko-fi.com/stateport?ref=site",
            "https://ko-fi.com/stateport/shop",
            "https://user:password@ko-fi.com/stateport",
        )
        for value in invalid:
            with self.subTest(value=value), self.assertRaises(ValueError):
                validate_kofi_url(value)


if __name__ == "__main__":
    unittest.main()
