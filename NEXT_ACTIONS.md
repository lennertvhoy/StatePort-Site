# NEXT_ACTIONS — active execution queue

**Updated At:** 2026-07-26
**Execution Mode:** operating
**Max Items:** 3

## P1 [BL-SITE-011] Review the reconciled local Site candidate against the final StatePort artifact

**Status:** pending

The local candidate reconciles both active Site lines and preserved WIP. Keep
it unbound to an implementation release until the final StatePort source,
replacement bundle, lifecycle evidence, and exact-head CI exist. Then review
the copy, visual design, information architecture, rights boundary, and media
against that exact artifact.

**Exit:** owner records acceptance or requested changes for a Site candidate
bound to the exact accepted private-alpha artifact. Deployment remains a
separate explicit action.

## P1 [BL-SITE-003] Add release-specific content only with public source evidence

**Status:** pending_external

Replace release-preparation language only after a public implementation source,
license decision, versioned artifact, checksums, and verified install path exist.

**Exit:** all download and release claims bind to an exact published release.

## Completed since last update (2026-07-23)

- **BL-SITE-010** — Reconciled the Sol Ultra candidate, alpha-alignment
  candidate, and preserved unreachable `f3d3512…` WIP on the local-only
  `agent/site-final-alpha-reconciliation-001` branch. The complete
  item-level disposition and rights record are in
  `SITE_PARALLEL_RECONCILIATION.yaml` and `SITE_ASSET_RIGHTS.yaml`. No branch
  was deleted, pushed, or deployed; no final StatePort identity was claimed.

- **BL-SITE-008** — Regenerated the walkthrough MP4 spoken track from the
  reframed narration using the free public Edge TTS `en-US-AndrewNeural` voice
  at build time (no credentials). The 95.17s 1280x720 H.264/AAC MP4
  (SHA-256 `f8ad9dad463d14e364284488272e261bfc45b85c8fe4e22f51e9b5bf8ea31d43`)
  has six VTT cues aligned to the audio. Frame sampling confirmed all six
  scenes show the correct screenshots with established placement. The
  reproducible build script is committed at `scripts/build_walkthrough.py`.
- **BL-SITE-009** — Added two site-themed mermaid diagrams (harness flow,
  template-to-instance flow) rendered to PNG and inserted into the foundations
  page and the homepage "How it works" section. Added `.diagram-figure` CSS
  card style. Diagrams also copied into the implementation repository
  `docs/assets/` and one added to `ARCHITECTURE.md`.

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
