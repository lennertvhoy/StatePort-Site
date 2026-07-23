# StatePort Site status

**Updated At:** 2026-07-23
**Execution Mode:** operating
**Project State:** harness_narrative_and_video_rebuilt_local_validated_deploy_pending
**Repository:** https://github.com/lennertvhoy/StatePort-Site
**Hosting:** https://lennertvhoy.github.io/StatePort-Site/

## Current truth

- A static, accessible public site is implemented locally with a homepage,
  documentation index, introductory guide, tutorial path, release ledger,
  404 page, sitemap, and GitHub Pages workflow.
- The release ledger is the public source for availability. It does not link
  to the private implementation repository.
- The StatePort shell mascot was copied byte-for-byte from the accepted shell
  asset; its provenance and hashes are recorded in `PROJECT_DNA.yaml`.
- `python3 scripts/validate_repo.py` passes. It verifies StateSpec state-file
  consistency, required public routes, local links/assets, the Pages workflow,
  and the no-private-source-link boundary.
- Desktop and mobile browser review completed locally against a loopback static
  server. The homepage, documentation, release page, responsive navigation,
  and release-status copy rendered without console errors.
- GitHub repository `lennertvhoy/StatePort-Site` is public. The initial
  public-site content commit is
  `d4522dbee2a39d1f2c3c64766ac222b92ed17332`.
- GitHub Pages is configured for a custom workflow. Workflow-dispatch run
  `29853702366` successfully deployed that exact commit, and the public URL
  returned HTTP 200 and rendered correctly in a browser with no console errors.
- The expanded public documentation package includes foundations, model,
  lifecycle, governance, security and privacy, hosts and portability, evidence
  and roadmap, reference and FAQ, and a receipt-reading tutorial.
- A captioned 83-second local prototype walkthrough, four fixture-based UI
  screenshots, a public whitepaper reader plus source Markdown, an Agent Kits
  roadmap, and a LinkedIn post draft are complete on
  `agent/public-showcase` and pushed as draft PR
  [`#1`](https://github.com/lennertvhoy/StatePort-Site/pull/1). `python3
  scripts/validate_repo.py` passes; fresh desktop and mobile browser review of
  the homepage, media, Agent Kits route, and release ledger found no console
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
