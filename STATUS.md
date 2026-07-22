# StatePort Site status

**Updated At:** 2026-07-22
**Execution Mode:** operating
**Project State:** product_ux_overhaul_video_plain_revision_merged_deployed_public_runtime_verified_human_acceptance_pending
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
- The live video is now a 52-second captioned walkthrough built from clean
  local prototype screens. Its MP4 SHA-256 is
  `f125eed97be3591c59f41f2fb9316648660ff025106a1f02c6d7f1e326291a9e`.
  It removes the baked-in text cards and uses a plain-English narration. PR #7
  merged as `b9a22283278b548628d3f4f591c159e55afa98d6`; Pages deployment run
  `29916907351` passed and the public runtime matches the asset hash and
  duration.
- A critical product, UX, content, accessibility, performance, metadata,
  privacy, and implementation audit is recorded in `SITE_AUDIT.md`.
- The audit found that the visual identity and static architecture should be
  preserved, while the first-visit product definition, homepage hierarchy,
  documentation wayfinding, mobile focus model, release-status detail,
  metadata, media hints, and automated quality contract required substantial
  improvement.
- The overhaul was merged from
  `agent/site-product-ux-overhaul-mainline` by PR
  [`#5`](https://github.com/lennertvhoy/StatePort-Site/pull/5). Its exact final
  head was `4d890658a8723bd5c44959ea6d5a455918f1e36e`; merge commit
  `905849ebc874391eb0449d619159fd5e78f02be2` is now on canonical `main`.
  The superseded diverged draft PR #4 was closed without merge.
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
- The exact final head passed desktop and 390px browser review, keyboard
  navigation checks, deep-page no-overflow checks, caption/media checks, and
  clean browser-console checks. The public runtime now serves that merge
  commit through Pages deployment run `29915789073`.
- The video revision's public runtime was checked directly: the MP4 is 52
  seconds, the new captions are served, and the walkthrough route returns HTTP
  200. Human acceptance remains separate.

## What is not proven

- A full screen-reader session, Lighthouse run, axe run, and task-based
  usability study have not been completed. Browser accessibility snapshots and
  keyboard smoke checks are evidence of interaction behavior, not a complete
  assistive-technology or usability acceptance record.
- Static validation is not evidence of complete WCAG conformance, conversion
  improvement, product-market fit, security certification, or production
  readiness.
- Human acceptance of the live baseline and the proposed overhaul remains open.
- Public source availability, a licensed release, downloads, and a verified
  installation path remain absent.

## Next action

Obtain human acceptance of the deployed overhaul against the five explicit
acceptance tasks in `NEXT_ACTIONS.md`. Keep merge, Pages deployment,
public-runtime verification, and human acceptance as separate recorded steps.
