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

    def test_a_clause_boundary_cannot_separate_subject_from_predicate(self) -> None:
        """The recorded bypass, now a refusal.

        A subordinate clause introduces no new subject, so a comma must not be
        able to move the subject of a claim away from its predicate and leave
        each half holding only one of the two. The first string is the exact
        recorded finding; the rest are the same defect in other wordings, and
        are here to show the rule is structural rather than a pinned sentence.
        The controls in the next two tests are what stop this from being a
        rule that refuses everything containing a comma.
        """
        for claim in (
            # The recorded finding, uncaught until now.
            "The native installation, while the docs are unreviewed, is qualified.",
            # The two strings the KNOWN GAP sentinel used to assert as passing.
            "is qualified, the native installation",
            "For the native installation, the status is qualified.",
            # Same defect, other subordinating conjunctions and other orders.
            "Although the reviewer is unavailable, the native installation is fully qualified.",
            "Whereas no reviewer has signed off, the one-line command is qualified.",
            "Because the release history is thin, the native build is qualified.",
            "The native installation, insofar as anyone can tell, is qualified.",
        ):
            with self.subTest(claim=claim):
                self.assertIsNotNone(check_site_quality.qualification_claim_violation(claim))

    def test_a_finite_predicate_verb_is_not_treated_as_a_participial_fragment(self) -> None:
        """The recorded reduced-clause residual, now a refusal.

        The sentence pass is gated on the predicate sitting in a clause that has
        a finite verb, and that test reused the enumeration member list, which
        carries no present-tense qualification verb. A trailing clause holding
        only "qualifies" therefore had no subject for the clause pass and was
        switched off for the sentence pass, so the claim was seen by NEITHER
        pass. The first string is the exact wording that passed; the rest are
        the same defect in other wordings.
        """
        for claim in (
            "The native installation, reduced to a QEMU simulation, qualifies.",
            "The native installation, reduced, qualifies.",
            "The native installation, reduced to a simulation, qualifies for the journeys only.",
            "The one-line command, reduced to the developer's checkout, qualifies.",
        ):
            with self.subTest(claim=claim):
                self.assertIsNotNone(check_site_quality.qualification_claim_violation(claim))
        # The limit is the verb form, not the sentence: a participial or nominal
        # predicate in an aside still borrows no subject, and the live
        # enumeration sentence must stay accepted.
        for honest in (
            "The candidate has not received human acceptance, independent security "
            "review, or production qualification.",
            "The wider architecture this paper describes — catalogues of community "
            "applications, multiple qualified providers, team deployments — is a "
            "direction, not a description of what the alpha delivers",
        ):
            with self.subTest(honest=honest):
                self.assertIsNone(check_site_quality.qualification_claim_violation(honest))

    def test_a_reduced_relative_clause_does_not_hide_the_claim(self) -> None:
        """The five recorded false negatives, now refusals.

        Each of these was ACCEPTED: the comma split the sentence so that the
        clause holding the subject had no predicate and the clause holding the
        predicate had no subject, and the sentence pass was switched off because
        neither trailing clause has a finite verb. The claim was therefore seen
        by NEITHER pass. They are five wordings of one shape, and the shape is
        what the rule is about: a reduced relative clause between the subject
        and the predicate is an adjunct to the subject, not a new subject, so
        the predicate is still the installation's. Three of the five carry a
        bare participle or a nominal rather than a present-tense verb, which is
        why a verb-form rule alone does not reach them.
        """
        for claim in (
            "The native installation, reduced in scope, qualifies",
            "The native installation, reduced scope, qualified",
            "The native installation, reduced to one path, qualification complete",
            "The native installation, scope reduced, qualifies",
            "The native installation, reduced, qualifies",
        ):
            with self.subTest(claim=claim):
                self.assertIsNotNone(check_site_quality.qualification_claim_violation(claim))

    def test_a_reduced_clause_claim_is_still_judged_by_its_governance(self) -> None:
        """The same shape, with a negation, a pending label or a document subject.

        Reaching this shape is not a licence to refuse it. The rule decides
        WHERE a predicate belongs to a subject; _affirmative_claim_in_span still
        decides WHETHER the span is a claim, and a fix that returned a violation
        the moment the shape matched would refuse all of these while looking
        correct on the five above.
        """
        for honest in (
            # The negation sits in the same reduced-clause shape and governs it.
            "The native installation, reduced in scope, is not qualified",
            "The native installation, reduced in scope, is not yet qualified",
            "The native installation, reduced to one path, is not qualified",
            "The native installation, reduced to one path, remains unqualified",
            # Pending language outranks the shape.
            "The native installation, reduced in scope, is pending qualification",
            "The native installation, reduced in scope, is awaiting qualification",
            # The documentation-subject exemption outranks it too, and it needs
            # no comma here on purpose: a comma between the documentation noun
            # and the qualification deliberately does NOT exempt, which
            # test_a_documentation_noun_far_from_the_claim_does_not_excuse_it
            # pins, so a comma here would be testing a refusal, not an
            # exemption.
            "The installation instructions in reduced scope are qualified by the reviewer",
        ):
            with self.subTest(honest=honest):
                self.assertIsNone(check_site_quality.qualification_claim_violation(honest))

    def test_known_gap_vetting_prose_with_a_publication_assertion_is_over_refused(self) -> None:
        """KNOWN GAP, pinned deliberately. These are REFUSED, and that is wrong.

        0bc7bb5 widened the sentence pass to a predicate that carries this
        subject, which closed the reduced-clause bypass class. It also began
        refusing prose in which "qualified by" names who vetted something and
        the sentence asserts publication instead. Measured on 2026-09-27: 0 of
        the 58 real surfaces are refused, so nothing is blocked today, and the
        site contains no occurrence of "qualified by" at all.

        Two repairs were attempted and both were withdrawn, for the same reason:
        each decided the sentence by reading the text after the participle, and
        each moved the defect rather than removing it. Releasing the exemption
        when no known predicate word followed accepted every readiness claim
        that used no vocabulary word ("is ready", "is released"); releasing it
        on a list of publication words accepted every sentence that carried one
        of them alongside a readiness claim ("is public and ready", "is listed
        as production-ready"). The underlying cause is the CLOSED predicate
        vocabulary, which admits qualif* and the copula completion forms but not
        ready, released, endorsed or fit for production, so no logic layered on
        the attachment can be sound in both directions.

        Wake condition: a reviewed decision on that vocabulary. Until then the
        guard stays strict, which is the fail-closed direction, and this test
        keeps the cost visible instead of leaving it as an accident.
        """
        for over_refused in (
            "the product tour, qualified by the reviewer, is public",
            "the build, qualified by CI, is reproducible.",
            "the release notes, qualified by the reviewer, are public",
            "the installer, qualified by the reviewer, is public",
            "the release, qualified by the reviewer, is on the site",
            "the one-line command, qualified by the reviewer, is easy to follow",
        ):
            with self.subTest(over_refused=over_refused):
                self.assertIsNotNone(
                    check_site_quality.qualification_claim_violation(over_refused)
                )
        # The teeth of the same rule, so this test cannot be satisfied by a
        # guard that simply refuses everything with a participle in it.
        for claim in (
            "The native installation, reduced to a QEMU simulation, qualifies.",
            "The native installation is qualified by our own tests",
        ):
            with self.subTest(claim=claim):
                self.assertIsNotNone(check_site_quality.qualification_claim_violation(claim))

    def test_a_predicate_may_borrow_a_subject_only_where_nothing_else_claims_it(self) -> None:
        """The three ways this rule would over-refuse, each a real site shape.

        The reduced-clause shape is common in prose, so relaxing the finite-verb
        requirement without these three limits refuses truthful text: the
        predicate in each string below belongs to a noun that is not this
        sentence's subject. Dropping any one of the three limits leaves every
        other test in this file green while opening exactly one of these.
        """
        for honest in (
            # A dash aside, and the subject word sits BEFORE it: the predicate
            # is inside the aside, where a participial fragment lives. Same list
            # of community "qualified providers" the whitepaper names.
            "The product's wider architecture — catalogues of community applications, "
            "multiple qualified providers, team deployments — is a direction, not a "
            "description of what the alpha delivers",
            # A second subject word after the first comma, so the predicate
            # modifies the noun in its own clause. "The native installation"
            # also holds two subject words, and those are ONE subject: the
            # second-subject test therefore only applies past the first comma.
            "The native install page, next to the product tour, lists qualified providers",
            # The predicate comes FIRST and the only subject word follows it, so
            # this is a noun inside a list and not a subject-predicate pair.
            "The wider architecture this paper describes — catalogues of community "
            "applications, multiple qualified providers, team deployments — is a "
            "direction, not a description of what the alpha delivers",
        ):
            with self.subTest(honest=honest):
                self.assertIsNone(check_site_quality.qualification_claim_violation(honest))
        # A finite clause in the same aside position IS a claim, so the limits
        # are structural and not an exemption for this sentence.
        self.assertIsNotNone(
            check_site_quality.qualification_claim_violation(
                "The product's wider architecture — the native installation is "
                "qualified — is a direction, not a description of what the alpha "
                "delivers"
            )
        )

    def test_the_honest_enumeration_sentence_stays_accepted(self) -> None:
        """Regression pin for the live sentence the clause-splitting was for.

        download/0.1.0-alpha.3/known-limitations.md: the negation governs an
        enumeration, and "production qualification" is the predicate with a
        subject word of its own immediately in front of it. Any fix that reaches
        a predicate across commas must leave the "not" governing all of it.
        """
        honest = (
            "The candidate has not received human acceptance, independent "
            "security review, or production qualification."
        )
        self.assertIsNone(check_site_quality.qualification_claim_violation(honest))
        # The comma split itself must not be what saves it: the same sentence
        # with the enumeration's final member removed is a real claim.
        self.assertIsNotNone(
            check_site_quality.qualification_claim_violation(
                "The candidate has not received human acceptance, and the native "
                "installation has production qualification"
            )
        )

    def test_a_pendingly_subordinated_clause_does_not_excuse_the_claim(self) -> None:
        # The mirror of the bypass: a pending or negated predicate in the main
        # clause governs, and the subordinate clause does not turn it back into
        # a claim.
        for claim in (
            "The native installation, while the docs are unreviewed, is not yet qualified.",
            "The native installation, while the docs are unreviewed, is not qualified.",
            "The native installation, though the docs are unreviewed, remains pending.",
            "The native installation, because the review is outstanding, is still unqualified.",
        ):
            with self.subTest(claim=claim):
                self.assertIsNone(check_site_quality.qualification_claim_violation(claim))

    def test_a_participial_fragment_in_an_aside_is_not_a_predicate(self) -> None:
        # The over-refusal the sentence pass had to be limited to avoid. Taken
        # from papers/stateware-whitepaper-candidate-v1.2.md: "qualified" here
        # modifies "providers" inside a dash aside, the subject of the sentence
        # is "architecture", and the sentence's own predicate is negated. The
        # fragment has no finite verb, so the sentence pass must not hand it the
        # subject of an unrelated clause.
        honest = (
            "The wider\narchitecture this paper describes — catalogues of community applications,\n"
            "multiple qualified providers, team deployments — is a direction, not a\n"
            "description of what the alpha delivers"
        )
        self.assertIsNone(check_site_quality.qualification_claim_violation(honest))
        # A finite clause in the same position is a claim, so the gate is the
        # finite verb and not a special case for this sentence.
        self.assertIsNotNone(
            check_site_quality.qualification_claim_violation(
                "The wider architecture this paper describes — the native installation is "
                "qualified — is a direction, not a description of what the alpha delivers"
            )
        )

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

    def test_a_retraction_word_elsewhere_does_not_excuse_a_current_claim(self) -> None:
        # A retraction exemption that accepted any retraction word anywhere in
        # the sentence made the guard a rubber stamp: "The native installation is
        # qualified, retired." passed, undoing six shapes that every earlier
        # revision refused. Only a RETROSPECTIVE claim is history.
        for claim in (
            "The native installation is qualified, retired.",
            "The native installation is qualified; the Alpha.13 route was withdrawn.",
            "The native installation is qualified, and the old route is superseded.",
            "The native installation is qualified, as previously noted.",
            "The native installation is qualified; a retired route is unaffected.",
            "The native installation is qualified and replaced nothing.",
            "The native installation is qualified although CI is no longer red.",
        ):
            with self.subTest(claim=claim):
                self.assertIsNotNone(check_site_quality.qualification_claim_violation(claim))

    def test_nothing_qualified_is_honest(self) -> None:
        for honest in (
            "The Alpha.13 route was withdrawn; nothing is qualified today.",
            "Nothing is qualified on this route.",
        ):
            with self.subTest(honest=honest):
                self.assertIsNone(check_site_quality.qualification_claim_violation(honest))

    def test_the_offset_is_the_predicate_line_not_the_clause_line(self) -> None:
        # Pins the predicate offset, which the previous test could not: both the
        # clause start and the predicate sit on the same line there, so reverting
        # to the clause offset left every test green while the validator named
        # the wrong line. Here the clause opens on line 1 and the predicate is on
        # line 2, so the two offsets differ.
        text = "Native installation is\nqualified.\n"
        found = check_site_quality.qualification_claim_violation_span(text)
        self.assertIsNotNone(found)
        _, offset = found  # type: ignore[misc]
        self.assertEqual(text.count("\n", 0, offset) + 1, 2)

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
