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


class QualificationClaimTests(unittest.TestCase):
    """Both directions, because a guard tested only on what it already refused
    pins instances rather than the rule.

    The affirmative side once held only the five strings that had been live on
    the site, so the rule could be rewritten to anything that still refused
    those five. The bypasses below were each measured passing against the
    previous single-literal pattern, and the last of them is a false negative:
    a negation about a different subject used to excuse a real claim.
    """

    def test_affirmative_qualification_claims_are_refused(self) -> None:
        for claim in (
            "the native public-route installation is qualified.",
            "Supported platform; installation qualified",
            "Available; native public-route installation qualified",
            "Early alpha · Native public-route installation qualified.",
            "its native public-route installation is qualified.",
        ):
            with self.subTest(claim=claim):
                self.assertIsNotNone(check_site_quality.qualification_claim_violation(claim))

    def test_word_order_and_adverb_variants_are_refused(self) -> None:
        # Each of these passed against the previous literal pattern.
        for claim in (
            "The native installation is fully qualified.",
            "Native qualification is complete.",
            "a qualified native installation",
            "The release is now qualified.",
            "Our product has been qualified.",
            # \bproduct\b cannot match "production", so this phrasing needed the
            # subject term added explicitly rather than arriving for free.
            "The native installation is production qualified.",
            "production ready: the installer is qualified",
        ):
            with self.subTest(claim=claim):
                self.assertIsNotNone(check_site_quality.qualification_claim_violation(claim))

    def test_negation_about_another_subject_does_not_excuse_a_claim(self) -> None:
        # False negative: "Not verified" is about something else entirely, and
        # the fixed-width lookback used to treat it as governing the claim.
        for claim in (
            "Not verified, the native installation is qualified",
            "No blockers, so the installation is qualified",
        ):
            with self.subTest(claim=claim):
                self.assertIsNotNone(check_site_quality.qualification_claim_violation(claim))

    def test_honest_phrasings_pass(self) -> None:
        for honest in (
            "the native public-route installation is not yet qualified.",
            "Supported platform; native qualification pending",
            "native qualification remains pending",
            "This qualified view of portability is still valuable.",
            "Alpha.16 is a superseded predecessor retained for history.",
            # Over-refusing honest prose would block the site, so the honest side
            # is exercised as deliberately as the failing side.
            "Qualification is still pending for the native installation.",
            "The qualified electrician inspected the panel.",
            "Installation instructions are qualified by the reviewer.",
            "This release candidate is pending review.",
            "The native build has not been qualified yet.",
        ):
            with self.subTest(honest=honest):
                self.assertIsNone(check_site_quality.qualification_claim_violation(honest))

    def test_violation_reports_the_offending_offset_not_the_first_match(self) -> None:
        text = (
            "the native public-route installation is not yet qualified.\n"
            "an honest sentence with no claim at all.\n"
            "Native qualification is complete.\n"
        )
        found = check_site_quality.qualification_claim_violation_span(text)
        self.assertIsNotNone(found)
        _, offset = found  # type: ignore[misc]
        self.assertEqual(text.count("\n", 0, offset) + 1, 3)
        # The reported span is the offending clause, not the first pattern hit.
        self.assertIn("Native qualification is complete", found[0])  # type: ignore[index]

    def test_release_version_vocabulary_is_not_a_sentence_boundary(self) -> None:
        # Alpha.N and 0.1.0-alpha.N are this site's own release vocabulary, and
        # a period inside one of those tokens is not the end of a sentence.
        for claim in (
            "Alpha.17 is fully qualified.",
            "Release 0.1.0-alpha.16 is fully qualified.",
            "stateport 0.1.0-alpha.19 is qualified",
        ):
            with self.subTest(claim=claim):
                self.assertIsNotNone(check_site_quality.qualification_claim_violation(claim))

    def test_a_list_member_with_its_own_verb_does_not_inherit_a_foreign_negation(self) -> None:
        # The dangerous shape: swapping a connective restores the false negative
        # the rule exists to catch. "No blockers" negates a different conjunct.
        for claim in (
            "No blockers, and the installation is qualified",
            "Not verified, or the native installation is qualified",
            "Nothing pending, and the native installation is fully qualified",
        ):
            with self.subTest(claim=claim):
                self.assertIsNotNone(check_site_quality.qualification_claim_violation(claim))

    def test_wrapping_does_not_sever_subject_from_predicate(self) -> None:
        # Markdown hard-wraps prose, and the site has thousands of such joins.
        for claim in (
            "The installation\nis qualified",
            "The native installation is\nnow\nqualified.",
            "The native installation\nis fully qualified.",
        ):
            with self.subTest(claim=claim):
                self.assertIsNotNone(check_site_quality.qualification_claim_violation(claim))

    def test_a_wrapped_continuation_line_does_not_inherit_a_pending_label(self) -> None:
        self.assertIsNotNone(
            check_site_quality.qualification_claim_violation(
                "Human acceptance is pending\nand the native installation is fully qualified."
            )
        )

    def test_un_prefixed_words_are_not_negations(self) -> None:
        # A general un\\w+ negation pattern matched "unique", "uninstall", "unit".
        for claim in (
            "The unique native installation is qualified",
            # Subject descriptors must not exempt a claim about that subject.
            "An unverified native installation is qualified",
        ):
            with self.subTest(claim=claim):
                self.assertIsNotNone(check_site_quality.qualification_claim_violation(claim))

    def test_completion_predicate_branch_is_load_bearing(self) -> None:
        # These match only the completion branch, not the qualif* vocabulary.
        # Deleting that branch used to leave every test green.
        for claim in (
            "The native installation is complete.",
            "The installation is done.",
            "The native installation is finished.",
            "Native qualification achieved.",
        ):
            with self.subTest(claim=claim):
                self.assertIsNotNone(check_site_quality.qualification_claim_violation(claim))

    def test_a_pending_label_governs_the_list_it_introduces(self) -> None:
        # The site writes pending lists in exactly this style.
        for honest in (
            "Pending: native qualification",
            "Pending items: native qualification, independent security review, human acceptance.",
            "Still pending: native qualification",
        ):
            with self.subTest(honest=honest):
                self.assertIsNone(check_site_quality.qualification_claim_violation(honest))

    def test_a_documentation_subject_is_exempt_in_either_word_order(self) -> None:
        for honest in (
            "The qualified installation guide covers WSL2.",
            "See the qualified installation checklist in the docs.",
        ):
            with self.subTest(honest=honest):
                self.assertIsNone(check_site_quality.qualification_claim_violation(honest))
        # Adjacency is what makes this safe: a documentation noun mentioned
        # later in the clause must not exempt a real claim.
        self.assertIsNotNone(
            check_site_quality.qualification_claim_violation(
                "The installation is qualified; see the guide for details."
            )
        )

    def test_an_aside_mentioning_a_negation_does_not_excuse_a_claim(self) -> None:
        # The bypass a lexical clause-wide scan cannot see: a parenthetical that
        # CONTRADICTS the claim still mentions a negation or pending word.
        for claim in (
            "The native installation is qualified (nothing pending)",
            "The native installation is qualified (no blockers remain)",
            "The native installation is qualified (not verified anywhere)",
            "The native installation is qualified (unqualified elsewhere)",
        ):
            with self.subTest(claim=claim):
                self.assertIsNotNone(check_site_quality.qualification_claim_violation(claim))

    def test_remains_qualified_is_a_claim_not_a_pending_marker(self) -> None:
        # "remains" is pending only before a pending word, so a synonym could
        # not defeat the guard that the enumeration fix introduced.
        for claim in (
            "No blockers, and the installation remains qualified",
            "No blockers, and the installation is qualified",
        ):
            with self.subTest(claim=claim):
                self.assertIsNotNone(check_site_quality.qualification_claim_violation(claim))

    def test_known_unfixed_bypass_a_comma_separates_subject_from_predicate(self) -> None:
        """KNOWN GAP, asserted so it stays visible rather than silently absent.

        Both strings below are affirmative claims that the guard does NOT
        refuse, because the comma splits the subject from the predicate and each
        half is then missing one of the two. Closing this needs the comma to stop
        being a clause boundary, which is where the over-refusals come from:
        every honest string of the form "native qualification pending" also
        depends on that split. It is recorded rather than fixed because the
        trade is a real judgement about the public readiness contract, not a
        local repair. If this test ever starts failing, the gap was closed and
        this expectation must be updated to assertIsNotNone.
        """
        for claim in (
            "is qualified, the native installation",
            "For the native installation, the status is qualified.",
        ):
            with self.subTest(claim=claim):
                self.assertIsNone(check_site_quality.qualification_claim_violation(claim))

    def test_a_documentation_noun_far_from_the_claim_does_not_excuse_it(self) -> None:
        # Pins the adjacency constraint. Widening the adjacency window left
        # every test green while opening this bypass.
        for claim in (
            "No blockers, and the native installation is qualified according to the guide for Windows",
            "The native installation is qualified, as explained in the installation checklist",
        ):
            with self.subTest(claim=claim):
                self.assertIsNotNone(check_site_quality.qualification_claim_violation(claim))

    def test_unqualified_is_honest(self) -> None:
        # Pins the unqualified entry in the pending list; removing it left
        # every test green.
        for honest in (
            "The installation is unqualified",
            "This release is unqualified and still early alpha",
        ):
            with self.subTest(honest=honest):
                self.assertIsNone(check_site_quality.qualification_claim_violation(honest))

    def test_release_history_may_state_that_a_route_was_qualified(self) -> None:
        # The site is release-history heavy and must be able to record this.
        for honest in (
            "Alpha.13 was qualified for its signed payload and later withdrawn.",
            "The Alpha.13 route was once qualified, then replaced after review.",
            "The Alpha.13 route was previously qualified.",
        ):
            with self.subTest(honest=honest):
                self.assertIsNone(check_site_quality.qualification_claim_violation(honest))

    def test_every_public_page_is_honest_today(self) -> None:
        documents = check_site_quality.parse_documents()
        for path, _ in documents.items():
            text = (check_site_quality.ROOT / path).read_text(encoding="utf-8")
            with self.subTest(page=str(path)):
                self.assertIsNone(check_site_quality.qualification_claim_violation(text))

    def test_every_surface_the_validator_scans_is_honest_today(self) -> None:
        # Covers exactly the set validate_qualification_claims reads, which is
        # wider than parse_documents(): subtitles and linked public markdown.
        # A test that covered only the documents passed while the validator
        # failed on download/0.1.0-alpha.17/release-notes.md.
        surfaces = check_site_quality.qualification_claim_surfaces(
            check_site_quality.parse_documents()
        )
        self.assertGreater(len(surfaces), len(check_site_quality.parse_documents()))
        for name, text in surfaces:
            with self.subTest(surface=name):
                self.assertIsNone(check_site_quality.qualification_claim_violation(text))

    def test_obligation_language_is_not_an_affirmative_claim(self) -> None:
        # Taken from a real page: "requires ... qualification" states that
        # qualification has not happened.
        for honest in (
            "This candidate requires agent-owned installed qualification before product acceptance",
            "The installation must be qualified before release.",
            "Qualification is required for acceptance.",
            # From download/0.1.0-alpha.3/known-limitations.md. The negation
            # governs an enumeration, so a comma split must not separate them
            # and turn honest prose into a refusal.
            "The candidate has not received human acceptance, independent security review, or production qualification.",
        ):
            with self.subTest(honest=honest):
                self.assertIsNone(check_site_quality.qualification_claim_violation(honest))

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
        self.assertIn("Review a change", homepage)
        self.assertIn("Inspect the receipt", homepage)
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
