# NEXT_ACTIONS — active execution queue

**Updated At:** 2026-07-22
**Execution Mode:** operating
**Max Items:** 3

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
