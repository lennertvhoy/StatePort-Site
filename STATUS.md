# StatePort Site status

**Updated At:** 2026-07-23
**Execution Mode:** operating
**Project State:** harness_narrative_and_video_rebuilt_local_validated_deploy_pending
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
- The public voice now leads with work, ownership, and the product surface.
  Availability is kept in one quiet release ledger rather than repeated across
  every page; technical documentation retains the distinctions it needs.
- The release-readiness remediation is committed as
  `5a9ef0202221ff215bc8b3879dbe4db405d3a82b` and is already the head of draft
  PR #1. It adds a capability-based platform-support contract, clean-install
  acceptance story, and scoped documentation-button contrast repair. The
  static gate verifies the CSS override, white-on-dark WCAG contrast, and
  visible keyboard focus treatment. Desktop and mobile loopback review passed
  with no console errors; the mobile matrix scrolls inside its region without
  widening the document.
- The non-deploying draft-PR validation workflow passed on behavior-bearing head
  `dbed5a9e62594ea19a5d8289c47776cbdfa3aeda` in GitHub Actions run
  `29908699477`. It exercised the public-boundary, local-link, contrast, and
  immutable-action-pin contracts only; it did not deploy Pages.
- The plain-language revision is deployed: the homepage, documentation entry
  points, walkthrough page, captions, and narration now use ordinary product
  language. Pages deployment run `29912179462` deployed merge commit
  `8794d1bc9800fff186555fbd5546e7bf9c2d8fc2`.
- A narrative reframing is implemented locally on 2026-07-23 but **not
  deployed**: the homepage, docs overview, foundations, hosts-and-portability,
  walkthrough narration source, and WebVTT captions now lead with StatePort's
  actual differentiator — it is a harness that orchestrates coding agents
  (Codex today; Pi, OpenCode, direct API as declared hosts) headlessly in
  managed environments, where each application is a Stateware template of
  durable state files plus cockpit scripts.
- The walkthrough MP4 was rebuilt from the reframed narration via a
  reproducible build script (`scripts/build_walkthrough.py`) using the free
  public Edge TTS `en-US-AndrewNeural` voice at build time only (no
  credentials; only public narration text leaves the machine). The new MP4 is
  95.17s, 1280x720 H.264/AAC, SHA-256
  `f8ad9dad463d14e364284488272e261bfc45b85c8fe4e22f51e9b5bf8ea31d43`; its six
  VTT cues align to the audio. Frame sampling confirmed scene/image placement.
- Two site-themed mermaid diagrams were rendered to PNG and inserted: the
  harness flow on the foundations page and the template-to-instance flow as a
  recap under the homepage "How it works" steps. They were also copied into the
  implementation repository `docs/assets/` and one added to `ARCHITECTURE.md`.
- `validate_repo.py` and `check_site_quality.py` pass. The package is
  uncommitted, unpushed, and not deployed.

## What is not proven

- Public source availability, a licensed release, downloads, or an installation
  path for visitors.
- Human acceptance of the copy, visual design, or information architecture.
- Human acceptance of the plain-language copy, visual design, information
  architecture, and media voice.

## Next action

Regenerate the walkthrough MP4 spoken track from the reframed narration source
so captions and audio match, then obtain human acceptance of the reframed
harness-narrative package before deploying. Keep release/download content tied
to a public source release and its evidence.
