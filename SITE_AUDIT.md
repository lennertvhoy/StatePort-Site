# StatePort Site — critical product, UX, content, and implementation audit

**Audit date:** 2026-07-22  
**Audited baseline:** `main` plus the plain-language work at PR #2 head
`4445cc5a7eb27fee979e62ac5135a1b418422faa`  
**Improvement branch:** `agent/site-product-ux-overhaul`  
**Scope:** public website and its repository contract; not the private StatePort
implementation

## Executive verdict

The site already has a distinctive visual identity, unusually honest release
language, a useful prototype walkthrough, and an appropriately simple static
architecture. Those strengths should be preserved.

The critical weakness is not visual polish. It is product comprehension and
information flow. A first-time visitor must currently infer what StatePort is
from a category thesis, a long sequence of sections, and specialist terms. The
site mixes three different jobs—explaining a future product, documenting a
system design, and publishing release evidence—without making the visitor
choose a route. The documentation then exposes almost every page at the same
priority.

Automated validation also overstates what “quality” means: the original gate
proves local links and one narrow contrast case, but not document structure,
metadata, mobile navigation focus, captions, fragment integrity, tracking
absence, sitemap completeness, or asset budgets.

The recommended path is an evolutionary overhaul, not a framework rewrite:
keep static HTML/CSS/JavaScript and the established art direction, make the
product concrete, separate user and builder journeys, improve wayfinding and
keyboard behaviour, add complete entry-point metadata, and make the validation
contract match the public quality claims.

## What was strong and preserved

- A recognisable editorial visual system instead of a generic SaaS template.
- Conservative availability language and a dedicated release ledger.
- Captions, a reduced-motion path, semantic landmarks, and visible focus styles.
- A fixture-based prototype rather than fabricated telemetry or stock mock-ups.
- No behavioural tracking, remote font dependency, framework runtime, or data
  collection surface.
- A static deployment model that is cheap, portable, inspectable, and easy to
  roll back.
- The accepted shell mascot, preserved without modification.

## Critical findings

### P0 — canonical project truth had drifted

The public product argues that current truth should be inspectable, but the
repository's main-branch status files continued to describe merged PR #1 as
pending. PR #2 corrects part of that state, but `STATUS.md` still contains stale
PR #1 language. The branch `agent/public-showcase` was also reused after merge
and now diverges from `main`, making review scope harder to understand.

**Impact:** credibility and operational risk. A Stateware project cannot treat
its own status files as secondary narration.

**Decision:** record the exact stacked branch, dependency, validation state,
and acceptance boundary. Do not imply deployment or human acceptance.

### P1 — the product was still less concrete than the philosophy

PR #2 substantially improves the language, but the first screen still does not
plainly define the product form, what stays in a project, what AI contributes,
and what a person can inspect. “AI work” and “Stateware” are broad abstractions
before the visitor has a mental model of a named application with readable
files, decisions, permissions, and history.

**Impact:** visitors can admire the thesis without understanding the product.

**Decision:** lead with one concrete definition, one current prototype, and one
availability boundary. Keep technical vocabulary, but introduce it after the
user-visible model.

### P1 — the homepage had too many competing stories

The baseline homepage moves through product thesis, prototype, principles,
workflow, Agent Kits, learning links, release summary, and another release CTA.
Several sections repeat the same ownership/continuity claim. Agent Kits receives
homepage-level prominence despite being explicitly roadmap-only.

**Impact:** the primary product feels less mature because a future sub-concept
competes with the unreleased core product.

**Decision:** remove the standalone Agent Kits homepage section, retain one
scoped roadmap link, and use a shorter sequence: definition, evidence,
principles, operating model, visitor path, release ledger.

### P1 — documentation architecture was a flat wall

The documentation sidebar and overview expose roughly fifteen destinations at
nearly equal weight. There is no recommended reading order, route grouping,
filter, local table of contents, or previous/next path. On mobile, the long
sidebar becomes a large block before the article.

**Impact:** high cognitive load, weak orientation, and poor continuation between
pages.

**Decision:** group routes by intent—start, design, operate, evidence—add a
four-step first-read path and topic filter, collapse long navigation on mobile,
generate page tables of contents, and provide previous/next links.

### P1 — mobile navigation was visually hidden but still focusable

At widths below 800px, the base CSS makes the primary navigation transparent
and pointer-inactive until JavaScript opens it. The links can still remain in
the keyboard order. The interaction also lacked Escape-to-close, outside-click
handling, focus transfer, and focus restoration. Without JavaScript, the key
entry-point navigation is hidden.

**Impact:** keyboard users can tab into invisible controls; no-JavaScript users
lose primary navigation on the most important routes.

**Decision:** manage focusability and `aria-hidden` with JavaScript, support
Escape/outside close and focus restoration, and provide a CSS no-JavaScript
fallback on public entry points.

### P1 — release status did not distinguish available evidence from software

The release page correctly says software is unavailable, but its ledger is
almost entirely negative. Public documentation, the paper, and the prototype
walkthrough are real available artifacts and should be named separately from a
software release.

**Impact:** visitors cannot quickly tell what they can inspect today, and may
conflate the public website repository with public product source.

**Decision:** publish a detailed status matrix with explicit positive and
negative states, a review date, available-now routes, and the evidence required
to change software status.

### P2 — SEO and link-preview metadata were incomplete

The baseline provides titles and descriptions but lacks canonical URLs, Open
Graph/Twitter metadata, structured data, and a web app manifest on the primary
entry routes.

**Impact:** weaker search consolidation, poor social previews, and less explicit
machine-readable page identity.

**Decision:** add canonical, social, JSON-LD, and manifest metadata to home,
documentation, tutorials, and release status. Do not mark the unreleased product
as a downloadable `SoftwareApplication`.

### P2 — media loading left avoidable layout and decode work

Homepage screenshots lacked intrinsic dimensions, lazy-loading hints, and async
decoding. The video is correctly user-initiated and metadata-only, but the page
still benefits from reserving media space and delaying below-the-fold images.

**Impact:** avoidable layout movement and main-thread decode pressure.

**Decision:** add known dimensions, lazy loading, async decoding, and
`content-visibility` for suitable below-the-fold sections. Do not add a build
pipeline merely to optimise four images; introduce WebP/AVIF only with a
repeatable source-asset workflow.

### P2 — the automated quality contract was too narrow

Passing CI was evidence for repository shape, local links, immutable Action
pins, one CSS cascade repair, and specific contrast ratios. It was not evidence
for complete accessibility, SEO, performance, browser compatibility, or UX.

**Impact:** the phrase “validation passed” can be read more broadly than the
checks justify.

**Decision:** add dependency-free checks for page landmarks, one H1, unique IDs,
skip-link targets, image alternatives, labels, video captions, entry metadata,
JSON-LD validity, internal fragments, sitemap coverage, manifest shape,
tracking absence, unsafe HTML injection, and static asset budgets. Browser and
human acceptance remain separate.

### P2 — repeated hand-authored shells will eventually drift

The repository repeats the header, footer, sidebar, and metadata across many
HTML files. At the current scale, static files remain simpler than introducing a
site generator, but repeated edits already create inconsistent navigation and
footer content.

**Impact:** increasing maintenance cost and inconsistency risk as routes grow.

**Decision:** use progressive enhancement for cross-page navigation features
now. Revisit a tiny deterministic template generator only when repeated shell
changes become a frequent source of defects. Do not adopt a client framework.

### P3 — measurement is intentionally absent, so conversion claims are unknown

No analytics or tracking is installed, which is a valid privacy and simplicity
decision. It also means the site has no behavioural evidence for whether people
understand the product or reach the release ledger.

**Impact:** content decisions remain based on review and qualitative testing,
not observed task completion.

**Decision:** do not add tracking by default. Validate with five concrete manual
usability tasks first. Consider privacy-preserving aggregate analytics only
through a separate explicit decision.

## Implemented improvement slice

### Product and content

- Reframed the hero around a concrete product boundary and current availability.
- Added a compact product definition covering what the project keeps, what AI
  contributes, and what people can inspect.
- Tightened the homepage sequence and demoted Agent Kits to a labelled roadmap
  note.
- Split prospective-user and builder/operator paths.
- Rewrote the release ledger to distinguish public artifacts from unavailable
  software, source, license, downloads, and installation material.
- Removed decorative coordinates that added no product meaning and could be
  mistaken for location data.

### Information architecture

- Added a four-step documentation reading path.
- Grouped the documentation catalogue by visitor intent.
- Added an accessible documentation topic filter.
- Added progressive breadcrumbs, grouped long sidebars, mobile sidebar
  disclosure, local tables of contents, and previous/next navigation.

### UI and responsive behaviour

- Preserved the established visual system and added only an additive stylesheet.
- Improved product-definition, audience, tutorial, and release-ledger layouts.
- Added print styles and high-contrast/forced-colour accommodations.
- Added no-JavaScript mobile navigation fallback to the key entry pages.

### Accessibility and interaction

- Added keyboard-safe mobile menu state, Escape close, outside close, focus
  transfer, and focus restoration.
- Added page-level tables of contents with active-section indication.
- Added accessible code-copy controls with a non-Clipboard API fallback.
- Added explicit form labels, live filter results, media dimensions, and caption
  checks.

### SEO, sharing, and platform metadata

- Added canonical URLs, Open Graph, Twitter cards, schema.org JSON-LD, and a
  web app manifest to the key entry routes.
- Used the existing fixture screenshot for social previews instead of inventing
  a marketing asset.

### Performance, privacy, and validation

- Added lazy loading, async image decoding, intrinsic media dimensions, and
  below-the-fold rendering containment.
- Kept all scripts local and retained the zero-tracking boundary.
- Expanded deterministic validation across structure, accessibility basics,
  metadata, captions, fragments, sitemap, manifest, privacy, and asset budgets.

## Acceptance criteria

The change is ready for review when all of the following are true on one exact
commit:

1. `python3 scripts/validate_repo.py` passes.
2. `python3 scripts/check_site_quality.py` passes.
3. JavaScript parses without syntax errors.
4. The homepage, docs overview, one deep documentation page, tutorials, and
   release ledger are reviewed at desktop and 390px widths.
5. Keyboard review confirms visible focus, mobile menu open/close, Escape,
   documentation disclosure, filter, table of contents, and code copy.
6. The prototype remains user-initiated and captioned.
7. No product download, public implementation source, license, support, or
   production-readiness claim is introduced.
8. Human acceptance, merge, deployment, and public-runtime verification are
   recorded as separate states.

## Risks and rollback

- **Stacked-branch risk:** this work starts from PR #2's exact head. It should be
  reviewed as a dependent change and retargeted to `main` only after PR #2 is
  integrated or superseded deliberately.
- **Hand-authored HTML risk:** deeper pages rely on JavaScript to load the
  additive stylesheet; their base content remains readable if enhancement
  loading fails. Key entry points load it directly.
- **Browser evidence gap:** deterministic checks do not replace screen-reader,
  browser, Lighthouse, axe, or human usability testing.
- **Content evidence gap:** the clearer positioning is a product decision, not a
  proven conversion improvement.

Rollback is low-risk: revert the content files, `assets/site.js`, and the
additive stylesheet/manifest/checker. There is no database, migration, user
state, external service, or tracking configuration to undo.

## Deferred work, in order

1. Complete manual browser, keyboard, and screen-reader smoke testing on the
   exact PR head.
2. Run Lighthouse and axe in a reproducible browser job only after choosing a
   stable test harness and thresholds that will be maintained.
3. Produce responsive WebP/AVIF images only through a documented deterministic
   source-asset pipeline.
4. Conduct five task-based usability sessions: explain StatePort, find current
   availability, find the product walkthrough, find security limits, and explain
   proposal versus acceptance.
5. Introduce a minimal template generator only if shell drift continues; keep
   generated HTML deployable without a framework runtime.
6. Decide separately whether privacy-preserving aggregate analytics provides
   enough value to justify its governance and operational cost.
