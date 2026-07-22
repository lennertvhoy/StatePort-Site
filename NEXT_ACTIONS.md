# NEXT_ACTIONS — active execution queue

**Updated At:** 2026-07-22
**Execution Mode:** operating
**Max Items:** 3

## P1 [BL-SITE-009] Review the exact product and UX overhaul

**Status:** ready_for_review

Draft PR [`#5`](https://github.com/lennertvhoy/StatePort-Site/pull/5) contains
the audit-backed homepage, documentation, tutorial, release-ledger, 404,
interaction, metadata, privacy, performance, and quality-contract changes. The
behavior-bearing head `be8c63ffb14b34c0ec6c1cc657b8ea248b2eaa4b` passed
GitHub Actions run `29914436990`.

Review at desktop and 390px widths, then complete keyboard and screen-reader
smoke tests. Use five tasks: explain StatePort after the first screen; distinguish
the prototype from downloadable software; find security limits; find platform
support; explain proposal versus validation versus human acceptance.

**Exit:** human review records accepted changes or concrete revisions against
the exact PR head. Static validation alone does not close this item.

## P1 [BL-SITE-010] Merge, deploy, and verify an accepted exact revision

**Status:** blocked_on_BL-SITE-009

After review acceptance, merge the exact accepted PR head, record the merge
commit, require a successful Pages deployment, and verify the public homepage,
documentation, release ledger, 404 route, captions, media, mobile navigation,
and browser console.

**Exit:** one exact revision is separately recorded as merged, deployed,
public-runtime verified, and human accepted. Do not collapse those states.

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
