# NEXT_ACTIONS — active execution queue

**Updated At:** 2026-07-22
**Execution Mode:** operating
**Max Items:** 3

## P1 [BL-SITE-013] Make public screenshot evidence inspectable at full size

**Status:** locally_validated_deployment_pending_human_acceptance_pending

The homepage fixture screens were too small to communicate the working platform
well. The local revision gives each of the four 1920×1200 interface screens its
full inline column, removes the artificially narrow settings treatment, and
makes every screen a direct source-image link without JavaScript.

With JavaScript available, the same links open a single full-size screenshot
gallery with previous/next controls, left/right arrow navigation, Escape close,
outside-click close, focus transfer and restoration, live slide status, and
the screen's existing label and description. The dialog uses only local static
assets and respects reduced-motion preferences.

Static validation, JavaScript parsing, and desktop/390px browser checks passed.
The browser review exercised opening a screen, button and keyboard navigation,
Escape-to-close focus restoration, full-size settings visibility, and a clean
console. Deployment and public-runtime verification remain pending.

**Exit:** exact revision is statically validated, merged, Pages-deployed,
public-runtime verified at desktop and 390px widths, and human-accepted. The
screens remain public-safe fixture evidence, not a public software release.

## P1 [BL-SITE-012] Replace the screen slideshow with a working platform walkthrough

**Status:** deployed_public_runtime_verified_human_acceptance_pending

The product-owner review found that the clearer neural-voice revision still
began too abruptly and did not explain the product's theory before touring the
screens. The new local revision makes one story out of the working public-safe
fixture: what StatePort is; why chat belongs inside a lasting piece of work;
one complete checklist path; the approval, result, evidence, and settings a
person can inspect; a second workspace; and a plain-language takeaway.

The local MP4 is 103.968 seconds at 1920×1200 with SHA-256
`f57949d33bdfe9ee8bebde37dfe32446adb01c5c9136fdd6927724758aaa9467`.
It uses the male US `en-US-AndrewNeural` Edge neural voice, rendered as
continuous scene narration at 95% pace with a 750 ms pause after each of the
16 scenes. The WebVTT has 16 cues whose text exactly matches the 16 markup
scene groups, and the clean, uncropped screens hold for those same segments.
There are no baked-in text overlays. Only public narration text was sent once
at build time; visitors have no runtime voice-service dependency.

Local ffprobe metadata, exact caption text, and a 16-state contact sheet were
checked. PR #18 merged as `0d4875d15f3b5f613dca6a70e625ae459692cd52`; Pages
deployment run `29924837231` passed. The live MP4 and WebVTT SHA-256 values,
the 103.968-second video metadata, and the 1:44 walkthrough copy were verified
directly from the public URL.

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
