# NEXT_ACTIONS — active execution queue

**Updated At:** 2026-07-21
**Execution Mode:** operating
**Max Items:** 3

## P1 [BL-SITE-006] Review the local release-readiness remediation before submission

**Status:** ready_for_review

The local worktree adds the documentation-button contrast repair and its
regression gate, plus the capability-based platform-support contract and
clean-install acceptance story. It has not changed draft PR #1, Pages, or the
public runtime.

**Exit:** an explicitly reviewed exact commit reaches draft PR #1, then its
matching remote checks and human review are recorded separately.

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
