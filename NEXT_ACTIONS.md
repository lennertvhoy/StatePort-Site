# NEXT_ACTIONS — active execution queue

**Updated At:** 2026-07-23
**Execution Mode:** operating
**Max Items:** 3

## P1 [BL-SITE-007] Obtain human acceptance of the reframed harness-narrative package

**Status:** pending

The homepage, docs, walkthrough, and diagrams are locally complete with the
harness narrative and the rebuilt MP4 matching its captions. Human review of
the copy, visual design, information architecture, and media voice is the
remaining gate before merge and deploy.

**Exit:** human review records acceptance or requested changes for the live
package — then deploy.

## P1 [BL-SITE-003] Add release-specific content only with public source evidence

**Status:** pending_external

Replace the release-preparation language only after a public source repository,
license decision, versioned artifact, checksums, and verified install path exist.

**Exit:** all download and release claims bind to an exact published release.

## Completed since last update (2026-07-23)

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

- **BL-SITE-005** — Locally validated an expanded public documentation package with a
  captioned, fixture-based local prototype walkthrough, four labelled product
  screens, the author-designated public Stateware whitepaper and source
  Markdown, and an Agent Kits roadmap. Static validation and desktop/mobile
  browser review passed. The release ledger remains the single public source
  for availability; draft review, merge, deployment, and runtime verification
  remain pending.

- **BL-SITE-004** — Authored the complete local documentation package for the
  whitepaper topics: foundations, model, lifecycle, governance, security and
  privacy, host portability, evidence, reference, and a receipt-reading
  tutorial. The static validator and desktop/mobile key-route browser review
  pass with no console errors. This worktree change is uncommitted, unpushed,
  and not deployed.
- **BL-SITE-001** — Local static validation passes; desktop and mobile browser
  review completed against a loopback static server with no console errors.
- **BL-SITE-002** — Created and pushed public repository
  `lennertvhoy/StatePort-Site` at `d4522dbee2a39d1f2c3c64766ac222b92ed17332`.
  Enabled GitHub Pages custom-workflow publishing. Workflow run `29853702366`
  passed for that exact SHA, and the public URL returned HTTP 200 in a browser.
