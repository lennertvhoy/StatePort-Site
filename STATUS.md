# StatePort Site status

**Updated At:** 2026-07-22
**Execution Mode:** operating
**Project State:** working_platform_walkthrough_story_revision_screenshot_gallery_deployed_public_runtime_verified_human_acceptance_pending
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
- The previously deployed public video was the earlier 52-second captioned walkthrough built from clean
  local prototype screens. Its MP4 SHA-256 is
  `b1be27a1cc2a1001050839dbfd3b0476a2e78cfa89478a03e15f0554ed51cadc`.
  It removes the baked-in text cards, uses plain-English narration, and keeps
  each spoken section on the screen it describes. PR #9 merged as
  `b9d0b757536608b05433781dd32dda157893ad06`; Pages deployment run
  `29917446210` passed and the public runtime matched the asset hash, captions,
  and duration.
- The previously deployed replacement walkthrough was a 105.746-second,
  1920×1200 capture of the
  working public-safe fixture. It shows the catalog, project view, real
  conversation answer, approval boundary, governed result, evidence drawer,
  settings, and a second application’s capability boundary. Its local MP4
  SHA-256 is
  `b69e18dfcac398e2839f2b6f6733b7cb440631903ea6fc9cf1bec603d7f76293`.
  Static validation and local runtime playback passed. PR #11 merged as
  `9567f1c223f3c536bebe51ae8f4580709a748b76`; Pages deployment run
  `29919971077` passed, and that revision was publicly verified.
- The previous public walkthrough was the 65.824-second, 1920×1200 capture using the male US
  `en-US-AndrewNeural` Edge neural voice and SSML-style markup. Its MP4
  SHA-256 is `b5d39209fd6bb7180f7eba651ce67e720125ad12447ed620675f2807395452d2`.
  The ten VTT cues exactly match the ten markup scene texts and the screenshot
  holds are built from the same scene durations. The build sent only public
  narration text to the synthesis service; visitors have no runtime dependency.
- PR #16 merged as `a51e2f7c55c02f9f2418099d10004cd7afafd2aa`; Pages deployment
  run `29923458869` passed. The live public runtime hash, duration, captions,
  and walkthrough copy were verified directly.
- The current public walkthrough is the 103.968-second story revision. It
  starts by defining StatePort and its core idea—chat helps, but the work
  needs a lasting home—before showing a complete checklist workflow, the
  approval and result, evidence, settings, a second workspace, and the
  takeaway. It remains a 1920×1200 working public-safe fixture with no baked
  text overlay. Its MP4 SHA-256 is
  `f57949d33bdfe9ee8bebde37dfe32446adb01c5c9136fdd6927724758aaa9467`.
  The 16 VTT cues exactly match the 16 narration scene texts; each screen is
  held for its corresponding scene and the narration has a 750 ms scene pause.
- PR #18 merged as `0d4875d15f3b5f613dca6a70e625ae459692cd52`; Pages deployment
  run `29924837231` passed. The public MP4 and VTT hashes, 103.968-second
  H.264/AAC metadata, and 1:44 introductory walkthrough copy were verified
  directly from the live URL.
- PR #20 merged as `cc856c25f7a75e1f42e076e3e30372e40399463f`; Pages deployment
  run `29926750701` passed. The homepage's four interface screens now use their
  full inline column instead of sharing it with captions, and the settings
  screen is no longer artificially narrow. Each remains a direct image link
  when JavaScript is unavailable; with JavaScript, it opens a full-size,
  keyboard-operable gallery with controls, live slide status, Escape/outside-
  click close, and focus restoration. The live source exposes all four entry
  points and gallery assets; a live 390px browser check opened a screen,
  advanced it with ArrowRight, closed it with Escape, and found no console
  errors.
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
- Human acceptance of the deployed story revision remains open.
- Human acceptance of the screenshot gallery remains open.

## Next action

No further deployment work is queued for this slice. Human acceptance of the
public screenshot gallery remains separate and pending.
