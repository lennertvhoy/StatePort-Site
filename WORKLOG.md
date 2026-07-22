# Worklog

## 2026-07-22 — Product/UX overhaul merged, deployed, and runtime verified

- Reviewed exact PR #5 final head `4d890658a8723bd5c44959ea6d5a455918f1e36e`
  at desktop and 390px widths against the five comprehension tasks.
- Confirmed the concrete product definition, prototype-versus-software
  boundary, security limits, platform support contract, and evidence ladder.
- Confirmed mobile navigation open/close behavior, Escape handling, no
  horizontal overflow on deep pages, user-initiated captioned video, and clean
  browser console checks.
- Merged PR #5 as `905849ebc874391eb0449d619159fd5e78f02be2`.
- Pages deployment run `29915789073` passed. Public runtime checks returned
  HTTP 200 for the key routes, served the new UX/content, retained the exact
  prototype video hash, and exposed captions and the manifest.
- Human acceptance, full screen-reader testing, Lighthouse, axe, and task-based
  usability study remain separate and open.

## 2026-07-22 — Critical product and UX overhaul prepared and behavior head validated

- Audited the deployed plain-language site across product definition,
  positioning, information architecture, visual hierarchy, content, responsive
  interaction, keyboard access, metadata, privacy, performance, maintainability,
  release truth, and automated validation. The durable findings, decisions,
  acceptance criteria, rollback, and deferred work are recorded in
  `SITE_AUDIT.md`.
- Preserved the static HTML/CSS/progressive-JavaScript architecture, midnight
  state-atlas visual identity, accepted byte-for-byte shell mascot, captioned
  user-initiated prototype, zero-tracking boundary, and conservative release
  language. A framework rewrite was rejected as cost without user value.
- Rebuilt the homepage around a concrete product definition, current evidence,
  a shorter operating story, separate user and builder routes, and one detailed
  release boundary. Agent Kits was demoted to an explicitly scoped roadmap note.
- Replaced the flat documentation wall with a recommended four-step path,
  intent-based catalogue, accessible filter, grouped sidebars, breadcrumbs,
  local tables of contents, previous/next navigation, and code-copy feedback.
- Clarified tutorial sequence, time, outcomes, and proof limits. Rebuilt the
  release ledger to distinguish available public artifacts from unavailable
  software, implementation source, license, downloads, and installation
  material.
- Reworked progressive interaction: mobile navigation now manages hidden focus,
  Escape and outside close, focus transfer, and restoration; key entry routes
  have a no-JavaScript mobile-navigation fallback. Added print,
  increased-contrast, forced-colour, intrinsic-media, lazy-loading, and async
  decoding support.
- Added canonical URLs, Open Graph/Twitter metadata, schema.org JSON-LD, and a
  web app manifest to the primary entry routes without adding tracking or remote
  runtime dependencies.
- Expanded the dependency-free quality contract from local links and a narrow
  contrast case to document structure, unique IDs, skip targets, image
  alternatives, labelled controls, captioned video, local scripts, entry-point
  metadata, JSON-LD, internal fragments, sitemap coverage, manifest validity,
  tracking absence, safe DOM construction, and static asset budgets.
- The first exact-head CI run exposed a real pre-existing 404-page defect: no
  meta description and no skip link. Corrected the structure and replaced the
  jargon-heavy recovery copy with clear local routes rather than exempting the
  page from the contract.
- While the first draft was being assembled, PR #2 merged and canonical `main`
  advanced. Created `agent/site-product-ux-overhaul-mainline` directly from
  current `main` SHA `10846eaea05ebf915006fe0f4d65a1e1e4f9a82b`, reapplied only
  the intentional files as one clean commit, opened draft PR
  [`#5`](https://github.com/lennertvhoy/StatePort-Site/pull/5), and closed the
  superseded diverged draft PR #4 without merge.
- Behavior-bearing head `be8c63ffb14b34c0ec6c1cc657b8ea248b2eaa4b` passed
  GitHub Actions run `29914436990`. Authored-source JavaScript syntax, Python
  compilation, HTML parsing, and a synthetic twenty-page quality-contract run
  also passed.
- At preparation time, PR #5 was unmerged, undeployed, public-runtime
  unverified, and human unaccepted. Browser and human acceptance remained
  separate work.

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
