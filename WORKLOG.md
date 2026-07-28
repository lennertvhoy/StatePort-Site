# Worklog

## 2026-07-28 — Owner-test Site matrix complete and validation copy aligned

- Re-ran both deterministic gates on the clean local owner-test candidate:
  `scripts/validate_repo.py` passed and `scripts/check_site_quality.py` passed
  all 21 pages.
- Completed the remaining loopback browser matrix: homepage at
  1440/1280/1024/768/390/320 and 120%/150%-equivalent layout widths; release
  ledger and problem-report instructions at 1440/390/320. Each viewport had
  `scrollWidth == innerWidth`; all 26 homepage reveal elements became visible
  through scroll; mobile navigation opened, Escape closed it, and focus
  returned to the toggle. Browser console: zero errors and zero warnings.
- Preview review caught one newly stale statement after the private product
  candidate completed exact-runtime agent validation. Updated only the
  bounded homepage and release-ledger availability wording at
  `1a307e6e1af740950dfb34d2076ab0f4f75abc68`: local automated and
  exact-runtime agent validation passed; human validation, owner acceptance,
  remote CI, release closure, and public download remain open or absent.
- Classification: local Site owner-review readiness; review independence not
  established. No push, Pages deployment, public-runtime change, product
  acceptance, human validation, or human acceptance was performed.

## 2026-07-28 — Local owner-checkpoint truth alignment

- Audited the local Site owner-test candidate against the exact StatePort
  candidate boundary. Corrected copy that conflated the current native
  loopback candidate with historical rootless-Podman packaging evidence,
  treated agent validation as human acceptance, implied universal container
  isolation or recovery controls, and exposed the unpublished v1.2 candidate
  paper through the sitemap.
- Added the complete evidence ladder and a local problem-report guide that
  explains optional screenshot handling, safe candidate/runtime/instance
  context, privacy exclusions, local evidence storage, and the absence of an
  active public support or vulnerability-intake route. The current product
  candidate is reported as undergoing exact-source revalidation; earlier
  terminal evidence is not transferred across the new behavioural head.
- Rebuilt the public-safe historical-fixture walkthrough from the corrected
  containment narration using the existing build pipeline and public
  `en-US-AndrewNeural` voice. Result: 65.372 s, 1280x720 H.264/AAC, MP4
  SHA-256 `df6a160965d2f57fe7255a4e87bff39e381b4ed70d0597eb4ac7f502691e281e`,
  VTT SHA-256 `9eeb973ddac1a2b9ecc15094d79692ef866cebd4919e981067a464934ff1af82`,
  narration SHA-256 `ff6b3afcff0dd684961765caea37d31df23cd415165680c0754acec54ca6dd67`.
- Content heads are `90a1757` (truth-aligned package) and `7779112`
  (exact-source validation-boundary correction). `python3
  scripts/validate_repo.py`, `python3 scripts/check_site_quality.py`, and
  `git diff --check` passed. Final loopback browser review passed at 1440x900
  and 390x844 on the homepage, release ledger, and problem-report instructions
  with zero console errors or warnings. The wider requested viewport/zoom
  matrix remains open.
- Review class is `internal_multi_agent` with independence not established.
  No push, Pages deployment, product-candidate validation, public release,
  human validation, or human acceptance was performed or inferred.

## 2026-07-27 — Local owner-test hero framing correction

- Corrected the homepage hero screenshot on `candidate/local-user-test-001`
  (`4967425`). The catalog UI now uses its complete native 16:10 frame rather
  than a 164%-wide, horizontally clipped crop.
- `python3 scripts/check_site_quality.py` and
  `python3 scripts/validate_repo.py` passed. Preview is local only; no push,
  Pages deployment, or public-release claim was made.

## 2026-07-27 — Noob-friendly copy and beginner walkthrough narration

- Opened local branch `agent/noob-friendly-copy-001` (base
  `1e4f1ddf5d4b04eb1cc5e7d4875aeca6c699a296`, the head of
  `agent/site-alpha-release-alignment-001`) on the owner directive that the
  walkthrough video must be understandable to non-engineers first, since most
  visitors only open the site and maybe watch the video. Local only — no
  push, no Pages deploy, no release-ledger or whitepaper change.
- Rewrote the homepage hero (`e990b26`): a plain-English deck a non-engineer
  can parse, then an accurate three-point technical layer (a coding agent
  orchestrated safely with approvals and records; containers on the visitor's
  own machine; applications and data that stay theirs across provider or
  model changes). Title/meta/og/twitter/JSON-LD descriptions moved to the
  same register; the meta description was shortened to fit the 80–170
  character quality contract. The private-alpha note, release-ledger routing,
  and deployed-product claims are unchanged.
- Rebuilt the walkthrough from a beginner-level narration (`06ed537`):
  `scripts/build_walkthrough.py` with the work directory under `output/`
  (tmpfs discipline), en-US-AndrewNeural, six scenes and screenshots kept.
  New local media: 64.292 s, 1280x720 H.264/AAC, MP4 SHA-256
  `fcb6efd6f1acbe8fed76352972b01ced4a4ffff7885fdc8549d2f51aef01aaf6`, VTT
  SHA-256 `149adacabae30771af5b69c7a542abc78981da731c17055011d46aaa866acb4d`;
  six verbatim cues timed to the actual audio. The SSML markup source and the
  walkthrough-page storyboard, duration note (1 minute 4 seconds), and header
  copy were updated to match. The deployed public walkthrough (95.173 s,
  `057588ed…`) remains the live artifact; nothing was deployed.
- Added short "New here?" orientation paragraphs to the two beginner entry
  pages — `docs/getting-started.html` and `tutorials/first-application.html`
  (`fb4162d`). Deep technical docs are untouched.
- `python3 scripts/validate_repo.py` and `python3 scripts/check_site_quality.py`
  both pass on the final head. Human acceptance of the new copy and media
  voice remains unproven and owner-gated.

## 2026-07-26 — Deployment-state reconciliation and alpha-alignment slice opened

- Corrected stale current-truth claims. The 2026-07-23 entries below recorded
  the harness-narrative package as "uncommitted, unpushed, and not deployed";
  in fact it was committed on `main` the same day (`690b5f4` narrative and
  media rebuild, `92d134b` VTT verbatim fix) and deployed by Pages run
  `30043401841` (passed 2026-07-23, confirmed via
  `gh run list --repo lennertvhoy/StatePort-Site`). `STATUS.md`,
  `NEXT_ACTIONS.md`, and `PROJECT_STATE.yaml` now record this.
- Re-verified the live walkthrough media against the repository on 2026-07-26:
  `curl` of the live MP4 and VTT SHA-256 match the working-tree files exactly
  (MP4 `057588edf3db94d9e022a1ca244edf5de9bddbb482f786e221bd0adf4d1875e1`,
  VTT `cab9d1ed26a31618874ef5c895a1d9cb1da6352a254118252dd67f74855a734d`;
  95.173 s, 1280x720 H.264/AAC per `ffprobe`). The hash `f8ad9dad…` recorded
  on 2026-07-23 was the pre-VTT-fix intermediate build inside `690b5f4`; the
  deployed build is the `92d134b` re-render. Earlier walkthrough revisions and
  their merge/Pages/runtime records below remain as history only.
- Removed the exact local filesystem path from `PROJECT_STATE.yaml`
  (`delivery.local_repository`); public state files no longer carry local
  machine paths.
- Opened local branch `agent/site-alpha-release-alignment-001` (base
  `92d134b`) for the v0.1.0-alpha.1 private-RC site alignment: hero visual
  repair, product-truth copy corrections, CTA/alpha-status note, site licence
  boundary, whitepaper v1.2 candidate, and walkthrough rebuild. Local only —
  no push, no Pages deploy, no release-ledger availability change, no
  whitepaper publication without owner direction.

## 2026-07-23 — Walkthrough video rebuilt and mermaid diagrams added

- Rebuilt the local-prototype walkthrough MP4 from the reframed narration so
  the spoken track matches the new harness narrative and the captions.
  Method (reproducible, committed as `scripts/build_walkthrough.py`): split the
  narration into six scenes, synthesise per-scene audio with the free public
  Edge TTS endpoint using the `en-US-AndrewNeural` voice (build-time only, no
  credentials, only public narration text leaves the machine), then assemble a
  1280x720 H.264/AAC MP4 on the established `#0B132B` night background —
  landscape screenshots scaled to 1152x720 centred, the mobile screenshot
  centred at height-fit — with 0.45s pauses between scenes. VTT captions are
  regenerated from the measured scene timings.
- Result: `stateport-local-prototype-walkthrough.mp4`, 95.17s, SHA-256
  `f8ad9dad463d14e364284488272e261bfc45b85c8fe4e22f51e9b5bf8ea31d43`; VTT has
  six cues aligned to the audio. Frame sampling confirmed each scene shows the
  intended screenshot and the mobile scene is centred (332x720).
- Added two mermaid diagrams rendered to PNG (site-themed: blue accent on
  white, ink text), generated with `@mermaid-js/mermaid-cli`:
  `assets/diagrams/stateport-diagram-harness.png` (replaceable hosts -> harness
  -> durable instance) on the foundations page, and
  `assets/diagrams/stateport-diagram-template.png` (template -> harness ->
  agent -> instance) as a recap under the homepage "How it works" steps. Added
  a spare `.diagram-figure` card style to `site.css`. Both diagrams were also
  copied into the implementation repository under `docs/assets/` and the
  harness diagram was inserted into `ARCHITECTURE.md`.
- `python3 scripts/validate_repo.py` and `check_site_quality.py` pass.
- The reframed homepage/docs, the rebuilt video, and the diagrams are now a
  consistent local package. It is uncommitted, unpushed, and not deployed;
  human acceptance and the public deploy remain open. No release, download,
  production-readiness, or host-qualification claim is made.

## 2026-07-23 — Narrative reframing: StatePort as a harness for coding agents

- Responded to product-owner review that the public site read as a vague
  generic AI-app platform and hid StatePort's actual differentiator: it is a
  harness/wrapper that orchestrates coding agents headlessly in managed
  environments, where each application is a Stateware template of durable state
  files plus the cockpit scripts the agent runs.
- Rewrote the homepage copy to lead with the harness thesis: hero deck and
  tagline, the "idea" statement, the four-step "how it works" route
  (WRAP / TEMPLATE / RUN / KEEP), and two of the three principles
  ("Your state stays yours"; "Agents are replaceable" naming Codex, Pi,
  OpenCode, and direct API). Visual structure and the one-accent system are
  unchanged; only copy moved.
- Rewrote the docs overview "What is StatePort?" lead, added a "Where the
  coding agent fits" section to the foundations page, and strengthened the
  hosts-and-portability "Where the host work stands" section to state the
  host-neutral harness model (Codex exercised locally; OpenCode and direct-API
  adapters in-model; Pi a reference direction).
- Rewrote the walkthrough narration source and WebVTT captions to open and
  close on the harness framing while keeping the middle scenes accurate to the
  recorded UI (home, conversation, source trust, mobile).
- `python3 scripts/validate_repo.py` and `python3 scripts/check_site_quality.py`
  pass.
- Truth boundaries preserved: no link to the private implementation repo; no
  release, download, production-readiness, Pi-integration, or host-qualification
  claim; availability stays tied to the release ledger.
- Follow-up: the deployed MP4 spoken track carried the prior plain-language
  narration. Done the same day — see the next entry: the MP4 was rebuilt from
  the reframed narration.
- This worktree change is uncommitted, unpushed, and not deployed.

## 2026-07-22 — Plain-language revision deployed and verified

- Merged PR #2 as `8794d1bc9800fff186555fbd5546e7bf9c2d8fc2` after the exact
  branch validation passed in run `29912161044`.
- Pages deployment run `29912179462` passed.
- Public runtime checks returned HTTP 200 for the homepage, docs, walkthrough,
  release status, captions, and video. The live video SHA-256 matches
  `7f7ed41b2f010357369d22b402c4fbcfdd088dcc9b7d2eb9ab423c9134c12901`.
- Human acceptance of the copy, visual design, information architecture, and
  media voice remains open.

## 2026-07-22 — Plain-language public copy and narration revision

- Responded to product-owner review that the public site and walkthrough were
  too jargon-heavy for a first-time visitor.
- Rewrote the homepage and documentation entry points around plain language:
  work, files, decisions, what happened, what is ready, and what needs
  attention. Specialist terms remain available in deeper technical pages.
- Rewrote the walkthrough page and WebVTT captions, and replaced the spoken
  track with a plain-English narration generated from the local Piper voice.
  The original 83.94-second visual track was preserved; the revised MP4 is
  `7f7ed41b2f010357369d22b402c4fbcfdd088dcc9b7d2eb9ab423c9134c12901`.
- Local static validation, link/contrast checks, and desktop browser review
  passed. Pages deployment of this revision remains pending.

## 2026-07-22 — Draft-PR validation and current-truth reconciliation

- Corrected the stale claim that the platform-support and contrast remediation
  was uncommitted or absent from draft PR #1. It is committed as
  `5a9ef0202221ff215bc8b3879dbe4db405d3a82b`, the draft PR head; it is still
  unmerged, undeployed, and unaccepted.
- Added a non-deploying draft-PR workflow that runs the existing repository
  validator and a deterministic local-link/documentation-button-contrast
  contract. It has read-only repository permissions and does not publish Pages.
- Pinned every GitHub Action currently used by the Site workflows to an exact
  full commit SHA. The validation gate refuses future mutable action tags.
- GitHub Actions run `29908699477` passed the non-deploying validation contract
  for behavior-bearing draft head `dbed5a9e62594ea19a5d8289c47776cbdfa3aeda`.
  It does not change the public site, release ledger, source availability,
  download status, or human acceptance.

## 2026-07-21 — Local platform-support and documentation-button accessibility remediation

- Added `docs/platform-support.html` as a qualification contract rather than a
  current installation claim. It distinguishes browser/durable-storage proof
  from host-integrated execution for Linux, Docker Desktop for Linux, macOS +
  Docker Desktop, and Windows + Docker Desktop/WSL 2; it also records the
  first clean-install acceptance story that a future signed release must prove.
- Wired the route into documentation navigation, the overview, the hosts page,
  the sitemap, route validation, and current project state. The release ledger
  remains the source for availability.
- Corrected the `.prose a` cascade so dark and outlined documentation buttons
  retain their intended colors. The static validator now requires those scoped
  overrides, calculates white-on-dark WCAG contrast (including hover), and
  requires visible keyboard focus treatment.
- Ran `python3 scripts/validate_repo.py`, reviewed the route on a loopback
  server at desktop and 390px mobile widths, and observed no browser console
  errors. The matrix remains horizontally scrollable on mobile without causing
  document-level horizontal overflow.
- The remediation was subsequently committed and pushed as
  `5a9ef0202221ff215bc8b3879dbe4db405d3a82b`, the head of draft PR #1. It has
  not been merged, deployed, or accepted as release evidence.

## 2026-07-21 — Public prototype, paper, and Agent Kits package locally validated

- Added an 83.94-second H.264/AAC local prototype walkthrough with English
  WebVTT captions, four fixture-based UI captures, and an evidence-bound
  documentation route. The video uses user-initiated controls; it does not
  autoplay or claim a public install, hosted service, acceptance, or release.
- Added the author-designated public Stateware whitepaper source Markdown and
  an HTML reader generated from that exact source, with a publication note
  routing availability claims to the release ledger. The source digest is
  recorded in `PROJECT_STATE.yaml`.
- Added a public Agent Kits roadmap that frames a template-first, portable,
  governed direction without claiming a schema, exporter, registry, Docker
  image, installation flow, or benchmark result.
- Updated the homepage hierarchy to lead with the real local capture and a
  concise durable-state proposition; documentation navigation, sitemap, and
  validation requirements now include the new routes and assets.
- Ran `python3 scripts/validate_repo.py` and completed fresh desktop and mobile
  browser review of the homepage, prototype media, Agent Kits route, and
  release ledger. The package is ready for commit/push and deployment
  verification; the public release ledger remains unchanged.
- Tightened the public voice so the page leads with work, ownership, and the
  product surface. Availability now has one quiet home in the release ledger;
  technical distinctions remain where the documentation needs them.
- Pushed the package to `agent/public-showcase` and opened draft PR
  [`#1`](https://github.com/lennertvhoy/StatePort-Site/pull/1). It awaits
  review, merge, Pages deployment, and public-runtime verification.

## 2026-07-21 — Complete documentation package authored locally

- Added a navigable documentation reading path covering Stateware foundations,
  the application model, lifecycle, governance, security and privacy, execution
  host portability, evidence and roadmap, and a reference/FAQ.
- Added a receipt-reading tutorial so readers can practice separating planned,
  approved, applied, validated, and accepted states without treating the
  example as a release artifact.
- Preserved the public-preview boundary throughout: the new pages make no
  public-source, installer, hosted-service, benchmark, production-readiness,
  or release claim. The hosts page describes direct Codex only as unmerged local
  evidence and keeps Pi as an unconnected reference-host direction.
- Updated the documentation index, tutorial navigation, sitemap, and static
  validation route list. `python3 scripts/validate_repo.py` passed.
- Reviewed the documentation index, Foundations at desktop and mobile widths,
  and Evidence and roadmap through a loopback static server. No browser console
  errors were observed.
- The documentation package is local and intentionally uncommitted, unpushed,
  and undeployed; the existing public site remains bound to its initial commit.

## 2026-07-21 — Initial StatePort Site foundation

- Created a standalone StateSpec-governed sibling repository for the public
  StatePort website.
- Established the factual boundary: the implementation repository is private,
  no public release or download is published, and the site must not present a
  future release as current availability.
- Added the static deployment shape, documentation/tutorial/release routes,
  and the accepted StatePort shell mascot copied byte-for-byte with recorded
  provenance.
- Ran `python3 scripts/validate_repo.py`: passed. The gate checks required
  StateSpec files, route and asset references, Pages workflow presence, and
  the no-private-source-link boundary.
- Completed local browser review at desktop and mobile widths, including the
  responsive menu, homepage, documentation page, and release page. No browser
  console errors were observed.
- Created public repository `https://github.com/lennertvhoy/StatePort-Site`
  and pushed `main` at `d4522dbee2a39d1f2c3c64766ac222b92ed17332`.
- Configured GitHub Pages for custom-workflow publishing. The initial push run
  started before Pages configuration and failed at `configure-pages`; after
  configuration, workflow-dispatch run `29853702366` deployed the same exact
  commit successfully. This is a configuration-ordering fact, not a content or
  runtime failure.
- Verified `https://lennertvhoy.github.io/StatePort-Site/` in a browser: HTTP
  200, expected title and content, no console errors. Human acceptance remains
  separately unproven.
