# NEXT_ACTIONS — active execution queue

**Updated At:** 2026-07-22
**Execution Mode:** operating
**Max Items:** 3

## P1 [BL-SITE-006] Validate the exact draft-PR site head before review

**Status:** ready_for_remote_validation

The documentation-button contrast repair, regression gate, capability-based
platform-support contract, and clean-install acceptance story are committed in
`5a9ef0202221ff215bc8b3879dbe4db405d3a82b`, the current head of draft PR #1.
A non-deploying validation workflow now needs to run on the exact updated PR
head. Pages and the public runtime remain unchanged.

**Exit:** the exact PR head has a recorded passing validation run, followed by
separate human review. Merge and deployment remain separate steps.

## P1 [BL-SITE-003] Add release-specific content only with public source evidence

**Status:** pending_external

Replace the release-preparation language only after a public source repository,
license decision, versioned artifact, checksums, and verified install path exist.

**Exit:** all download and release claims bind to an exact published release.

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
