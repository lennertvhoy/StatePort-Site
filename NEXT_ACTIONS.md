# NEXT_ACTIONS — active execution queue

**Updated At:** 2026-07-22
**Execution Mode:** operating
**Max Items:** 3

## P1 [BL-SITE-012] Replace the screen slideshow with a working platform walkthrough

**Status:** deployed_public_runtime_verified_human_acceptance_pending

The product-owner review correctly identified that the 52-second clean-screen
revision still behaved like a slideshow. The replacement walkthrough is
captured from the working public-safe fixture at 1920×1200 and follows real
states: catalog, project view, conversation answer, exact-run review,
approval, governed result, evidence, settings, and a second application’s
capability boundary. The spoken track and WebVTT are generated from the same
ten scene segments, with no baked-in text overlay.

The local MP4 is 105.746 seconds with SHA-256
`b69e18dfcac398e2839f2b6f6733b7cb440631903ea6fc9cf1bec603d7f76293`.
The site validators passed, the local site reports 1920×1200 video metadata,
and the public-safe platform runtime was exercised before capture. PR #11
merged as `9567f1c223f3c536bebe51ae8f4580709a748b76`; Pages deployment run
`29919971077` passed; and the live public runtime serves the expected video
metadata and captions.

**Exit:** exact revision is validated, reviewed at desktop and 390px widths,
merged, Pages-deployed, public-runtime verified, and human-accepted. The
working fixture evidence must remain separate from software-release claims.

## P1 [BL-SITE-011] Replace the jargon-heavy prototype walkthrough

**Status:** completed

The next video revision removes the baked-in blue text cards and replaces the
84-second screen recording with a 52-second walkthrough built from clean local
prototype screens. The narration and captions use ordinary language: project,
conversation, files, decisions, what is ready, and what is still being checked.

Validated the MP4, captions, public wording, and video playback. PR #7 merged
as `b9a22283278b548628d3f4f591c159e55afa98d6`; Pages deployment run
`29916907351` passed; the public MP4 hash and 52-second duration match the
exact asset. PR #9 then synchronized the spoken sections to the visible screens
and merged as `b9d0b757536608b05433781dd32dda157893ad06`; Pages deployment run
`29917446210` passed. The public MP4 hash is now
`b1be27a1cc2a1001050839dbfd3b0476a2e78cfa89478a03e15f0554ed51cadc`.

**Exit:** exact revision is statically validated, merged, Pages-deployed, and
public-runtime verified. Human comprehension acceptance remains separate.

## P1 [BL-SITE-009] Obtain human acceptance of the deployed product and UX overhaul

**Status:** pending

PR [`#5`](https://github.com/lennertvhoy/StatePort-Site/pull/5) merged as
`905849ebc874391eb0449d619159fd5e78f02be2` and Pages deployment run
`29915789073` passed. The exact final head
`4d890658a8723bd5c44959ea6d5a455918f1e36e` also passed the repository and
expanded quality contracts, desktop/390px browser review, keyboard smoke,
caption/media checks, and public browser-console verification.

Complete human review of the live site at desktop and 390px widths. Use five
tasks: explain StatePort after the first screen; distinguish the prototype from
downloadable software; find security limits; find platform support; explain
proposal versus validation versus human acceptance.

**Exit:** human review records accepted changes or concrete revisions against
the deployed merge commit. Static or agent browser validation alone does not
close this item.

## P1 [BL-SITE-010] Merge, deploy, and verify an accepted exact revision

**Status:** completed

PR #5 exact head `4d890658a8723bd5c44959ea6d5a455918f1e36e` merged as
`905849ebc874391eb0449d619159fd5e78f02be2`. Pages run `29915789073` passed;
the homepage, documentation, release ledger, 404 route, captions, media,
mobile navigation, and browser console were verified publicly.

**Exit:** merged, deployed, and public-runtime verified are recorded
separately. Human acceptance remains BL-SITE-009.

## P1 [BL-SITE-003] Add release-specific content only with public source evidence

**Status:** pending_external

Replace release-preparation language only after a public implementation source,
license decision, versioned artifact, checksums, and verified install path exist.

**Exit:** all download and release claims bind to an exact published release.

## Completed since last update (2026-07-22)

- **BL-SITE-008** — Merged and deployed the plain-language revision. PR #2
  validation run `29912161044` and Pages run `29912179462` passed; the public
  runtime was verified. Human acceptance remained separate.
- Prepared the critical audit and product/UX overhaul on a clean branch based on
  current canonical `main`; opened draft PR #5 and closed superseded draft PR #4.
- Expanded the deterministic quality contract and corrected the 404-page defect
  it exposed. Behavior-bearing head validation passed in run `29914436990`.
- Reviewed and deployed PR #5's exact final head; recorded merge, Pages, and
  public-runtime evidence separately. Human acceptance remains open.
- Prepared, merged, and deployed a clean-screen, plain-narration video revision
  in response to direct product-owner feedback that the baked-in labels and
  spoken explanation were still too jargon-heavy.
- Corrected the narration/caption timing after review found that the first
  revision changed screens at fixed times while the audio followed a separate
  timeline. Captions are now sentence-level and timed to regenerated audio.
