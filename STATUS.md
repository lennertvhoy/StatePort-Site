# StatePort Site status

**Updated At:** 2026-08-02
**Execution Mode:** operating
**Project State:** alpha_release_alignment_local_in_progress
**Repository:** https://github.com/lennertvhoy/StatePort-Site
**Hosting:** https://lennertvhoy.github.io/StatePort-Site/

## Current truth

- A local **public-alpha site quality** slice sits on branch
  `agent/public-alpha-site-quality-001`: a full-page claim and terminology
  audit, an explicit no-security-reporting-route statement, and a new
  `download/` route holding the complete Linux AMD64 alpha download
  structure with every artifact value marked `PENDING-FINAL-CANDIDATE`, and a
  mascot visibility enlargement after owner feedback (dark-theme surfaces
  render the light mascot variant for contrast: header brand mark 52px,
  hero mascot ~410px desktop, footer 44px, Playwright-measured, no overflow
  at 390px).
  No artifact is offered; the release ledger's availability is unchanged.
  Local only: no push, no Pages deploy; the final candidate digests,
  checksums, signatures, and release key material remain with the primary
  integrator.
- The live public site is a static HTML/CSS/progressive-JavaScript deployment.
  It contains the product story, documentation, tutorials, release ledger,
  captioned local prototype walkthrough, public paper, and 404 route.
- The release ledger is the single public source for availability. No public
  product source, license, download, installer, support, compliance, benchmark,
  or production-readiness claim is made.
- The StatePort shell mascot remains the accepted byte-for-byte asset recorded
  in `PROJECT_DNA.yaml`; the product/UX overhaul does not modify it.
- The harness-narrative package (reframed homepage/docs, rebuilt walkthrough,
  two diagrams) is committed on `main` as `690b5f4` plus VTT fix `92d134b`,
  and is **deployed**: Pages run `30043401841` passed on 2026-07-23. Earlier
  state-file claims that this package was "uncommitted, unpushed, and not
  deployed" were stale and are corrected here and in `WORKLOG.md`.
- The current public walkthrough is the 95.173-second, 1280x720 H.264/AAC
  harness-narrative build with six verbatim VTT cues. Its MP4 SHA-256 is
  `057588edf3db94d9e022a1ca244edf5de9bddbb482f786e221bd0adf4d1875e1` and its
  VTT SHA-256 is `cab9d1ed26a31618874ef5c895a1d9cb1da6352a254118252dd67f74855a734d`.
  Both hashes were re-verified against the live public URLs on 2026-07-26 and
  match the repository files. The intermediate hash
  `f8ad9dad463d14e364284488272e261bfc45b85c8fe4e22f51e9b5bf8ea31d43` recorded on
  2026-07-23 belonged to the pre-VTT-fix build in `690b5f4` and is superseded.
- Provider honesty correction applies to current copy: Codex CLI is the only
  execution provider exercised in the private alpha; there is no "direct API"
  host; Pi is a reference direction, not a delivered adapter; OpenCode is
  unqualified. StatePort preserves canonical application state across
  execution-provider integrations; provider capabilities and behaviour differ
  and are explicitly profiled. Earlier "direct API as declared host" wording
  in site copy is being removed in the alpha-alignment slice.
- Historical deployment evidence (the 52-second, 105.746-second,
  65.824-second, and 103.968-second earlier walkthroughs and their merge,
  Pages, and runtime records) remains in `WORKLOG.md` as history; it described
  earlier public revisions, not the current one.
- The release-readiness remediation (`5a9ef020...`, capability-based
  platform-support contract, clean-install acceptance story, scoped
  documentation-button contrast repair) is merged and deployed.
- A local **alpha release alignment** slice is in progress on branch
  `agent/site-alpha-release-alignment-001` (base `92d134b`): hero visual
  repair, product-truth copy corrections, CTA and alpha-status note, a site
  licence boundary, a whitepaper v1.2 candidate, and a walkthrough
  narration/media rebuild. It is local-only: no push, no Pages deploy, no
  public release-ledger change, and no whitepaper re-publication without owner
  direction.
- A local **noob-friendly copy** slice sits on branch
  `agent/noob-friendly-copy-001` (base `1e4f1dd`, the alpha-alignment head),
  on the owner directive that first-time, non-engineer visitors come first:
  a plain-language hero with an accurate technical trio, a beginner-level
  walkthrough narration rebuilt locally (66.254 s, MP4 SHA-256
  `79cf3b1377e0bb3bfcbb540bdbedbf1d522016ccc8b82520f8f35ee92f9eaf42`, VTT
  SHA-256 `c1d74a9107c5b19ba47e64a6878ccdbb2e1944605cef71f97c9d09353c3cb582`,
  six verbatim cues), and "New here?" orientations on the two beginner entry
  docs. Local-only: no push, no Pages deploy; the deployed public walkthrough
  remains the 95.173 s `057588ed…` build recorded above.
- A local **support-link** slice is implemented on branch
  `agent/support-link-001` as behaviour commit `616f01e`: a restrained
  About/Support section, deterministic Ko-fi Free configuration renderer, and
  validation for the homepage and footer destinations. It is fail closed:
  there is no configured Ko-fi URL and no owner attestation that Contributor
  mode is disabled, so no public Ko-fi link or pending-support message is
  rendered. No account was
  created, no external settings were changed, and nothing was pushed or
  deployed.
- The local candidate now states the runtime boundary accurately: the
  StatePort application and durable files run locally, while declared agent
  jobs may use a sandbox or container when configured and supported. The
  homepage, walkthrough page, spoken narration source, captions, and rebuilt
  local video agree on that boundary. This correction is local-only and is not
  a claim about the currently deployed site.
- A local **whitepaper diagram render** fix (BL-SITE-014) is implemented on
  `agent/noob-friendly-copy-001`: the public v1.1 and candidate v1.2 papers
  previously showed Mermaid diagrams as raw text because the static pages
  loaded no renderer. A build-time step now inlines static, project-themed,
  id-scoped SVG (no client JavaScript, no third-party runtime) from the
  Markdown source, with a validator guard against regressions. This is
  local-only; the **deployed live site still shows raw diagram text** until
  the owner merges to `main` (Pages auto-deploys on push to `main`).
- A local **application-first rebalance** slice (BL-SITE-015) is implemented
  on `agent/noob-friendly-copy-001`: the homepage hero and lead sections now
  put durable, user-owned applications first, name StudyState as the primary
  example, and present governed container deployment as the second pillar;
  four new documentation pages (`docs/study-state.html`,
  `docs/deployments.html`, `docs/limitations.html`, `docs/updates.html`) are
  cross-linked from the homepage, the documentation hub, the documentation
  sidebars, and the release ledger, and listed in the sitemap. The updates
  page is explicitly framed as design/target where the candidate does not
  yet deliver it, and deployment upgrade/rollback is stated as not yet
  supported. The alpha-availability line now says the public download is in
  preparation; it still does not exist. Local-only: no push, no Pages
  deploy, no release-ledger availability change.

## What is not proven

- Public source availability, a licensed release, downloads, or an installation
  path for visitors.
- Human acceptance of the copy, visual design, information architecture, and
  media voice — including the deployed harness-narrative package.
- Human acceptance of the alpha-alignment package now in local preparation.
- A StatePort-owned Ko-fi destination and owner verification that the account
  uses Ko-fi Free with Contributor mode disabled.

## Next action

Complete and locally validate the alpha-alignment package on
`agent/site-alpha-release-alignment-001`, then obtain owner review. Merge,
deploy, and any release-ledger or whitepaper publication change remain
owner-gated. Keep release/download content tied to a public source release
and its evidence.
