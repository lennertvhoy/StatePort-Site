# NEXT_ACTIONS — active execution queue

**Updated At:** 2026-07-27
**Execution Mode:** operating
**Max Items:** 3

## P1 [BL-SITE-010] Complete the local alpha release alignment package

**Status:** in_progress

Branch `agent/site-alpha-release-alignment-001` (base `92d134b`, local only).
Scope: hero visual repair with a protected copy column; product-truth copy
corrections (provider honesty, both product planes, ownership seam,
human-on-the-loop); CTA and clearly-local alpha-status note; site licence
boundary (LICENSE, NOTICE, asset inventory); whitepaper v1.2 candidate beside
the untouched public v1.1; walkthrough narration/media rebuild from corrected
copy. No push, no Pages deploy, no release-ledger availability change, and no
whitepaper publication without explicit owner direction. The noob-friendly
copy sub-package on `agent/noob-friendly-copy-001` (BL-SITE-012, completed
below) builds on this branch and joins the same owner review.

**Exit:** package committed locally with repo validators, link/a11y checks,
and a browser pass at 1440/1280/1024/768/390/320 plus zoom 120/150% recorded
as evidence; owner review requested.

## P1 [BL-SITE-007] Obtain human acceptance of the public site package

**Status:** pending

The deployed harness-narrative package (and now the alpha-alignment package
behind it) still needs human review of copy, visual design, information
architecture, and media voice.

**Exit:** human review records acceptance or requested changes for the live
package.

## P1 [BL-SITE-003] Add release-specific content only with public source evidence

**Status:** pending_external

Replace release-preparation language only after a public implementation source,
license decision, versioned artifact, checksums, and verified install path exist.

**Exit:** all download and release claims bind to an exact published release.

## Completed since last update (2026-07-27)

- **BL-SITE-012** — Prepared the local noob-friendly copy package on
  `agent/noob-friendly-copy-001` (base `1e4f1dd`, local only): plain-language
  hero with an accurate technical trio (`e990b26`), beginner-level walkthrough
  narration with a locally rebuilt MP4/VTT (64.292 s, six verbatim cues) and a
  matching storyboard (`06ed537`), and "New here?" orientations on the two
  beginner entry docs (`fb4162d`). `validate_repo.py` and
  `check_site_quality.py` pass. No push, no deploy, papers untouched; owner
  review and human acceptance pending.

## Completed since last update (2026-07-26)

- **BL-SITE-011** — Reconciled stale deployment state. The harness-narrative
  package was in fact committed on `main` (`690b5f4`, `92d134b`) and deployed
  via Pages run `30043401841` (2026-07-23); earlier "uncommitted, unpushed,
  not deployed" state claims were corrected. Re-verified the live walkthrough
  media against the repository on 2026-07-26: MP4 SHA-256
  `057588edf3db94d9e022a1ca244edf5de9bddbb482f786e221bd0adf4d1875e1`, VTT
  SHA-256 `cab9d1ed26a31618874ef5c895a1d9cb1da6352a254118252dd67f74855a734d`;
  the previously recorded `f8ad9dad…` hash was the superseded pre-VTT-fix
  build. Removed the exact local filesystem path from `PROJECT_STATE.yaml`.

## Completed since last update (2026-07-23)

- **BL-SITE-008** — Regenerated the walkthrough MP4 spoken track from the
  reframed narration using the free public Edge TTS `en-US-AndrewNeural` voice
  at build time (no credentials); six VTT cues aligned to the audio. The
  reproducible build script is committed at `scripts/build_walkthrough.py`.
  (Final deployed build is the `92d134b` re-render with verbatim cues — see
  the 2026-07-26 reconciliation above.)
- **BL-SITE-009** — Added two site-themed mermaid diagrams (harness flow,
  template-to-instance flow) rendered to PNG and inserted into the foundations
  page and the homepage "How it works" section. Added `.diagram-figure` CSS
  card style.

## Completed since last update (2026-07-21)

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
