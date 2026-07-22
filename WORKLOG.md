# Worklog

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
