# StatePort Site status

**Updated At:** 2026-07-28
**Execution Mode:** operating
**Project State:** alpha_release_alignment_local_in_progress
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
  walkthrough narration rebuilt locally (64.292 s, MP4 SHA-256
  `fcb6efd6f1acbe8fed76352972b01ced4a4ffff7885fdc8549d2f51aef01aaf6`, VTT
  SHA-256 `149adacabae30771af5b69c7a542abc78981da731c17055011d46aaa866acb4d`,
  six verbatim cues), and "New here?" orientations on the two beginner entry
  docs. Local-only: no push, no Pages deploy; the deployed public walkthrough
  remains the 95.173 s `057588ed…` build recorded above.
- The local owner-test candidate `candidate/local-user-test-001` includes
  hero correction `4967425`: the complete catalog UI is shown at its native
  16:10 ratio instead of a deliberately enlarged, clipped crop. It is not
  deployed; owner review remains required before any Pages action.
- The same local owner-test candidate now carries truth-aligned checkpoint
  content through `7779112`: the current product candidate is separated from
  historical Podman evidence, exact-source agent validation is separated from
  human validation and acceptance, universal containment/recovery claims are
  narrowed, and the local problem-report boundary is documented. The rebuilt
  public-safe historical-fixture tour is 65.372 seconds (1280x720 H.264/AAC;
  MP4 SHA-256 `df6a160965d2f57fe7255a4e87bff39e381b4ed70d0597eb4ac7f502691e281e`;
  VTT SHA-256 `9eeb973ddac1a2b9ecc15094d79692ef866cebd4919e981067a464934ff1af82`).
  Both Site validators pass, and final loopback browser review passed at
  1440x900 and 390x844 for the homepage, release ledger, and problem-report
  instructions with zero console errors or warnings. This evidence is local
  only: no push, Pages deployment, product-candidate validation, human review,
  or human acceptance follows from it.

## What is not proven

- Public source availability, a licensed release, downloads, or an installation
  path for visitors.
- Human acceptance of the copy, visual design, information architecture, and
  media voice — including the deployed harness-narrative package.
- Human acceptance of the alpha-alignment package now in local preparation.
- Exact-source validation or acceptance of the current StatePort product
  candidate; this Site preview reports that process but cannot prove it.

## Next action

Complete and locally validate the alpha-alignment package on
`agent/site-alpha-release-alignment-001`, then obtain owner review. Merge,
deploy, and any release-ledger or whitepaper publication change remain
owner-gated. Keep release/download content tied to a public source release
and its evidence.
