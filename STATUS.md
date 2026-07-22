# StatePort Site status

**Updated At:** 2026-07-22
**Execution Mode:** operating
**Project State:** product_ux_overhaul_in_draft_pr_behavior_head_validated_pending_review_merge_deployment_and_human_acceptance
**Repository:** https://github.com/lennertvhoy/StatePort-Site
**Hosting:** https://lennertvhoy.github.io/StatePort-Site/

## Current truth

- The live public site is a static HTML/CSS/progressive-JavaScript deployment.
  It contains the product story, documentation, tutorials, release ledger,
  captioned local prototype walkthrough, public paper, and 404 route.
- The release ledger is the single public source for availability. No public
  product source, license, download, installer, support, compliance, benchmark,
  or production-readiness claim is made.
- The StatePort shell mascot remains the accepted byte-for-byte asset recorded
  in `PROJECT_DNA.yaml`; the product/UX overhaul does not modify it.
- PR #2 merged as `8794d1bc9800fff186555fbd5546e7bf9c2d8fc2` after validation
  run `29912161044`. Pages deployment run `29912179462` passed, and the live
  plain-language baseline was verified for the homepage, documentation,
  walkthrough, release status, captions, video identity, and browser console.
- The live prototype video remains the 83.94-second captioned fixture capture
  with SHA-256
  `7f7ed41b2f010357369d22b402c4fbcfdd088dcc9b7d2eb9ab423c9134c12901`.
- A critical product, UX, content, accessibility, performance, metadata,
  privacy, and implementation audit is recorded in `SITE_AUDIT.md`.
- The audit found that the visual identity and static architecture should be
  preserved, while the first-visit product definition, homepage hierarchy,
  documentation wayfinding, mobile focus model, release-status detail,
  metadata, media hints, and automated quality contract required substantial
  improvement.
- The overhaul is committed and pushed on
  `agent/site-product-ux-overhaul-mainline` as draft PR
  [`#5`](https://github.com/lennertvhoy/StatePort-Site/pull/5). It is directly
  based on canonical `main` SHA
  `10846eaea05ebf915006fe0f4d65a1e1e4f9a82b`; the superseded diverged draft
  PR #4 was closed without merge.
- The exact behavior-bearing overhaul head
  `be8c63ffb14b34c0ec6c1cc657b8ea248b2eaa4b` passed GitHub Actions run
  `29914436990`. The repository-shape/public-boundary gate and the expanded
  structure, accessibility-basics, metadata, captions, fragments, sitemap,
  privacy, and asset-budget gate both passed.
- The first expanded-gate run correctly exposed an existing 404-page defect:
  it lacked a meta description and skip link. The page now uses clearer copy,
  local recovery routes, and the same document baseline as the rest of the site.
- Authored-source checks also passed for JavaScript syntax, Python compilation,
  HTML parsing, and a synthetic twenty-page quality-contract run. Those checks
  do not replace browser, assistive-technology, or human usability review.

## What is not proven

- PR #5 has not been merged, deployed, or verified on the public runtime.
- The overhaul has not yet completed desktop/mobile browser, keyboard,
  screen-reader, Lighthouse, axe, or task-based usability review on its exact
  final head.
- Static validation is not evidence of complete WCAG conformance, conversion
  improvement, product-market fit, security certification, or production
  readiness.
- Human acceptance of the live baseline and the proposed overhaul remains open.
- Public source availability, a licensed release, downloads, and a verified
  installation path remain absent.

## Next action

Review draft PR #5 against the explicit acceptance tasks in `NEXT_ACTIONS.md`.
Keep merge, Pages deployment, public-runtime verification, and human acceptance
as separate recorded steps.
