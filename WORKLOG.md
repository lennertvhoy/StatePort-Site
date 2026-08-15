# Worklog

## 2026-08-15 - Alpha.5 repaired command re-enable candidate

- The owner reports the exact Windows 11 + WSL2 + Ubuntu 24.04 probe passed the
  13,702-byte bootstrap, pinned SHA-256, `/bin/sh -n`, and all seven manifest
  digests without executing the installer or creating a receipt.
- Re-enabled exactly one escaped command on the download page: complete download
  of mutable `/download/install.sh`, exact size and digest checks, shell syntax,
  then execution. Pipe-to-shell remains forbidden. A Lionheart retry is
  diagnostic only; clean-install evidence requires a genuinely fresh distro.

## 2026-08-14 - Alpha.5 mutable manifest publication remotely verified

- The owner authorized publishing only the unversioned mutable repair while
  keeping public installation disabled. StatePort commit `b75357d1` adds an
  exact-target `--transport-probe` branch before confirmation, sudo, package
  mutation, archive materialization, or installer invocation.
- Mutable `download/install.sh` is 13,702 bytes at SHA-256
  `3f1be353c095b6ef08ea78beca8430b0baea13a890abce8aaf74c49d40808f78`.
  Seven `download/alpha5-manifests/*.json` blobs match the signed image subject
  digests. Eleven focused tests and both Site validators pass; all versioned
  release files remain unchanged.
- Content `562c9cf` deployed through build `1151713417`, run `31838288831`, and
  deployment `5913017331`. All 16 changed mutable files, both unchanged minimal
  public pages, and all 33 immutable Alpha.5 files matched anonymous bytes.
  Publication is verified; the exact-target owner probe remains pending.

## 2026-08-14 - Alpha.5 signature-refusal containment remotely verified

- The owner reports that the complete immutable bootstrap passed transport and
  shell checks, executed, and refused the five private image signatures visible
  in the transcript because exact local manifest bytes were unavailable. The
  signed inventory contains seven affected paths. No install receipt exists.
- Removed the public install command and replaced user-facing incident copy with
  the neutral message `Alpha test temporarily unavailable.` Immutable Alpha.2,
  Alpha.3, and Alpha.5 paths remain untouched.
- Eleven focused containment tests and both Site validators pass. Repository
  validation first failed on one stale detailed-copy marker and passed after
  that exact validator expectation was corrected. Content `8cae82e5` deployed
  through build `1151656087`, run `31835252274`, and deployment `5912489564`;
  15 changed mutable files and all 33 immutable Alpha.5 files matched remotely.
- StatePort commit `df2cbb85` locally repairs all seven paths through the frozen
  installer's existing archive seam. No signed bytes change and no successor is
  technically required, but publication and probing remain owner-gated. The
  owner-host installer must not be rerun.
- Closure validation first failed when `known_defective` conflated the mutable
  transport omission with the signed Alpha.5 bytes; restoring that boundary to
  `false` made the repository validator pass.

## 2026-08-14 - Alpha.5 repaired install re-enabled and remotely verified

- Pushed re-enablement content `c8cd20804bc2307c5c49f1fbed75ea8c59f921ae`.
  Managed Pages build `1151631061`, exact run `31834012760`, and exact
  deployment `5912274973` completed successfully.
- The legacy Pages build endpoint reported prior state SHA `2100b810`, while the
  dynamic run and deployment bind to `c8cd2080`. Anonymous fetches resolved the
  discrepancy: all 16 changed mutable files and all 33 immutable Alpha.5 files
  matched local bytes.
- The repaired public-test command is enabled. The owner-reported transport
  probe is not a clean install or independent raw receipt; Alpha.5 remains
  `compatible_unvalidated`, unaccepted, and not production-qualified. The sole
  next action is a genuinely fresh exact-target install with receipts, never the
  mutated prior distro.

## 2026-08-14 - Alpha.5 repaired install re-enablement candidate

- The owner reports that the exact Windows 11 + WSL2 + Ubuntu 24.04 target
  downloaded all 8,971 bootstrap bytes, matched SHA-256
  `104c7fd6a87014548e583e524918550cece08aac71af4fc2f764ff5edae2ed0a`,
  and passed `/bin/sh -n` without executing the installer. This is reported
  terminal evidence, not an independently captured raw receipt or clean install.
- Re-enabled only the generator-bound command that downloads to a private
  temporary file, requires transfer success, verifies size and digest, checks
  shell syntax, and executes afterward. The failed partial streamed attempt and
  mutated prior distro remain explicitly excluded from clean-install evidence.
- The 11 focused containment tests and all 29 Site tests pass. Repository and
  quality validators, mutable and versioned bootstrap shell syntax, and diff
  checks pass. All immutable release paths remain untouched; deployment and
  remote verification are pending.

## 2026-08-14 - Alpha.5 public install containment remotely verified

- Pushed exact containment content commit
  `636e795230e286fb39470fe695d935266b4ee876`. Managed Pages build
  `1151605137`, run `31832575567`, and deployment `5912021497` completed
  successfully for that head.
- Anonymous public fetches matched all 33 immutable Alpha.5 files and nine
  mutable containment surfaces, including seven HTML pages, the held-back
  transport generator, and the unchanged mutable bootstrap. Installation
  remains disabled and no browser acceptance is claimed.
- Alpha.5 remains published, signed, byte-intact, `compatible_unvalidated`, and
  unaccepted. The owner-run non-executing exact-target transport probe is the
  sole active outcome; re-enablement remains a separate decision.

## 2026-08-14 - Alpha.5 public install containment candidate

- The owner reports that the first Windows 11 + WSL2 + Ubuntu 24.04 AMD64
  attempt installed prerequisites, then Dash failed on an unterminated quote
  before the Python installer ran. No receipt exists; this remains a reported
  failed partial attempt with side effects, not independently observed evidence.
- Reused completed reviews that bind the failure to a 4,096-byte truncated
  pipe-to-shell transfer. Removed executable install promotion from mutable
  pages and added a held-back complete-download transport with pinned 8,971-byte
  size, SHA-256, `/bin/sh -n`, private temporary file, and cleanup checks.
- The 11 focused containment tests and all 29 Site unit tests pass. Repository
  validation, shell syntax, and the Site quality contract pass; the quality gate
  first failed on missing and then overlong homepage clean-install metadata, and
  passed after those exact metadata defects were corrected.
- The immutable Alpha.2, Alpha.3, and 33-file Alpha.5 trees match their
  publication anchors. Versioned, mutable, and frozen Alpha.5 bootstraps remain
  8,971 bytes, mode 0755, and SHA-256
  `104c7fd6a87014548e583e524918550cece08aac71af4fc2f764ff5edae2ed0a`.
  Deployment and remote verification remain pending.

## 2026-08-14 - Alpha.5 Site publication remotely verified

- Pushed Alpha.5 release anchor `eaa1ca6a` and content/control closure
  `6cf95ca855e94f7648afb93fa870390a8c8bc8a7` to canonical `main`.
- Managed Pages build `1151371842`, workflow run `31820163492`, and deployment
  `5909824336` completed successfully for exact content head `6cf95ca8`.
- Anonymous public fetches matched all 33 immutable Alpha.5 files, mutable
  `download/install.sh` SHA-256
  `104c7fd6a87014548e583e524918550cece08aac71af4fc2f764ff5edae2ed0a`,
  and six current release surfaces. Browser automation remained unavailable,
  so no browser acceptance is claimed. The owner real-host test remains pending.

## 2026-08-14 - Alpha.5 Site publication candidate

- Anchored the corrected 33-file Alpha.5 WSL2 release tree at Site commit
  `eaa1ca6a67844259860917442a95c891d097939f` alongside unchanged Alpha.2 and
  Alpha.3 trees, then regenerated the independent immutable manifest.
- Replaced current Alpha.3 containment copy with complete Windows 11 + WSL2 +
  Ubuntu 24.04 setup instructions, the exact signed Alpha.5 bootstrap, and an
  explicit `compatible_unvalidated` boundary. The historical Alpha.3 erratum
  and dated video availability line remain labelled as historical evidence.
- Repository validation, the Site quality contract, shell syntax, and all 26
  unit tests pass. Local browser automation was unavailable; deployment and
  public-byte verification remain pending and no browser acceptance is claimed.

## 2026-08-12 - Overview replacement render deployed

- Replaced the rejected 44.544-second overview with the governed five-scene
  HyperFrames render: 33.067 seconds, 993 frames, H.264 High/AAC 1920x1080,
  MP4 SHA-256 `0a9fe50bea513053af21d3e49e9523776defcdb4392a66557219d00e4bce1d21`.
- Site validation, quality validation, full decode, representative frame review,
  and 26 unit tests passed. Commit `15e9f777` deployed through Pages run
  `31626192641` and deployment `94213107101`; anonymous MP4/VTT hashes match.

## 2026-08-11 - Overview transition revoice candidate

- Revoiced only `29.999-31.872` seconds of the overview narration using the established `en-US-AndrewNeural` voice. Video frames remain byte-identical; the candidate is H.264/AAC 1920x1080, 44.544 seconds, 1,336 frames, with MP4 SHA-256 `81e16caf22fa6a7d59b7443939dd0bd6f5c66be583567a939c413131440acfe2`.
- Product commit `2141697e8c9658adbb50d7178e8a4b2f75bdd253` is locally committed. Site validation, quality validation, full decode, and 24 unit tests pass. The unchanged VTT SHA-256 is `f0c5cb3e357ffbd665a92fb088408b95f3040cb1dc57575c8a82462582c7666f`.
- Push and managed Pages deployment remain pending; alpha.2/alpha.3 bytes and release truth are unchanged.

## 2026-08-11 - Overview transition revoice deployed

- Pushed the media candidate and postdeployment state through Site head `f6f0e27b6a66fa2de46126796e2eef268ca0ea73`.
- Managed Pages build `1145044708`, workflow run `31489384247`, and deployment `5850023681` completed successfully. Public home and walkthrough reference the overview MP4 and VTT; fetched MP4 SHA-256 `81e16caf22fa6a7d59b7443939dd0bd6f5c66be583567a939c413131440acfe2` and VTT SHA-256 `f0c5cb3e357ffbd665a92fb088408b95f3040cb1dc57575c8a82462582c7666f` match local evidence.
- Alpha.3 release bytes and install-disabled, unaccepted, unqualified truth are unchanged.

## 2026-08-11 - Overview revoice provenance correction

- The postdeployment full unit suite exposed stale predecessor digest bindings in `scripts/validate_repo.py` and `NOTICE`; no public media byte mismatch was observed.
- Updated both bindings to MP4 SHA-256 `81e16caf22fa6a7d59b7443939dd0bd6f5c66be583567a939c413131440acfe2`. The candidate remains limited to the `29.999-31.872` narration window; immutable release trees are unchanged.

## 2026-08-11 - Overview revoice provenance correction deployed

- Corrective commit `75ce76008a8f8560f094c87687d8eeb666b67d2b` was pushed after the full unit suite, repository validator, quality contract, and diff check passed.
- Managed Pages workflow `31489845427` succeeded; deployment `5850105929` reached `https://lennertvhoy.github.io/StatePort-Site/` successfully. Public MP4/VTT hashes remain `81e16caf22fa6a7d59b7443939dd0bd6f5c66be583567a939c413131440acfe2` and `f0c5cb3e357ffbd665a92fb088408b95f3040cb1dc57575c8a82462582c7666f`.

## 2026-08-06 — Alpha.3 publication gate blocked by Pages outage

- Publication commit `52b42dd47a11510220f33690075f1b6773f6a889` was pushed to
  `main` with the signed alpha.3 artifact tree, capability-gated bootstrap,
  support-tier table, and preserved alpha.2 erratum.
- Local `validate_repo.py`, `check_site_quality.py`, and `git diff --check`
  passed. Pages run `31125217806` was canceled with no steps started while
  GitHub reports the critical `Incident with Actions` outage.
- The live Pages URL still serves the predecessor alpha.2 erratum, so the
  public-URL clean-install receipt was not captured. The existing private-ops
  Ubuntu receipt (`install_receipt_63bba55c...`) is not relabelled as public
  proof.
- Alpha.3 is published but not owner-accepted. Human acceptance, independent
  security review, and production qualification remain pending.
- Detailed evidence is recorded in the private operator evidence ledger.

## 2026-08-06 — Publish v0.1.0-alpha.3 candidate

- Published the resigned v0.1.0-alpha.3 candidate from source commit
  `fa4ea4b7f08e78669e194c204b59206ab109a02f` with portable target
  `linux-amd64-rootless-podman-quadlet`.
- Added the exact signed release index, index bundle, trust key, installer,
  updater, source archive, current compose definition, quadlet bundle, seven
  image signature bundles, and supply-chain evidence. Signed artifact hashes
  remain byte-identical to the operator evidence.
- Published support tiers: Ubuntu 24.04 `validated_baseline`; Fedora 44
  `compatible_unvalidated`; Debian and rolling distributions not claimed. The
  installer delegates host qualification to `evaluate_linux_host` and refuses
  non-capable hosts without making an all-Linux claim.
- Alpha.2 remains immutable, superseded, known defective, and install-disabled.
- This is published but not owner-accepted. Human acceptance, independent
  security review, and production qualification remain pending. Public-URL
  clean-install proof is the next gated step; its receipt and Pages run are not
  yet recorded in this entry.

## 2026-08-03 — Publish v0.1.0-alpha.2 candidate

- Published the signed v0.1.0-alpha.2 alpha candidate after seven exact image
  evidence runs, bounded scan dispositions, GHCR image signatures, and full
  release-index rederivation/verification.
- Added the versioned installer, updater, source archive, release notes,
  limitations, public key, index signature, and export manifest under
  `download/0.1.0-alpha.2/`.
- Human acceptance, independent security review, and production qualification
  remain explicitly pending.

## 2026-08-02 — Public-alpha site quality slice

- Worked on the local-only branch `agent/public-alpha-site-quality-001`
  (continuing the same-day mascot, whitepaper, OG/JSON-LD, CSP, and updater
  copy commits already on that branch).
- Audited every published page for broken internal links, stale claims, and
  terminology. `StateDD` appears only as a clearly labelled legacy
  compatibility name (footer line and reference page); no production-readiness,
  hosted-SaaS, multi-user, independent-audit, completed-Azure, or
  "deploy anything" claim exists on any page.
- `docs/security-and-privacy.html` gained an explicit "Reporting a security
  issue" section: no public vulnerability-reporting route exists yet and the
  intake address will be published in the release ledger with the first
  public release, instead of an unwatched channel (commit `4cb496f`).
- Added `download/index.html`: the complete Linux AMD64 alpha download
  structure (alpha label, Ubuntu 24.04 + rootless Podman prerequisites,
  no-checkout installer, SHA-256 checksum, Cosign signature, alpha release
  public key and fingerprint, signed release index, source archive, image
  digests, SPDX SBOMs, vulnerability-scan dispositions, Compose definition,
  Quadlet units, install/update-policy/backup/uninstall lifecycle, and alpha
  limitations). Every artifact value is marked `PENDING-FINAL-CANDIDATE`;
  no artifact is offered and human acceptance remains pending. Wired it into
  `sitemap.xml`, the release-ledger sidebar and "Downloads or installers"
  row, and the homepage availability line (commit `4532d88`).
- Verified the block-arch mascot and favicon copies are byte-identical
  (SHA-256) to the canonical `apps/web/assets/brand/` sources in the private
  StatePort repository and parse as well-formed XML; no asset change needed.
- Validation: `scripts/validate_repo.py` and `scripts/check_site_quality.py`
  pass (26 pages). Browser spot-check over a loopback server on the download,
  home, and release pages: zero console errors and no horizontal overflow at
  desktop and narrow viewports. Local only: no push, no deploy, no
  release-ledger availability change.
- Enlarged the mascot after owner feedback that it rendered too small
  (commit `a94844e`): header brand mark 39px → 46px, hero atlas container
  430px → 560px (desktop) / 340px → 430px cap and 74vw → 84vw (narrow), and
  the hero mascot 37% → 50% of the atlas. Measured with Playwright:
  header 39→46px, hero mascot ~172px → ~293px desktop and ~178px at 390px
  emulated width; header stays 80px/72px with no wrap and no horizontal
  overflow; alt/aria conventions unchanged; both validators pass.
- Corrected mascot contrast after owner feedback that the dark-mode variant
  disappeared on the navy theme (commit `5942145`). A rendered A/B showed
  the `-dark.svg` file's dark-navy body fill merges into the navy hero while
  the `-light.svg` file's cream body pops. Theme wiring now matches actual
  contrast: the dark-theme surfaces (home header, hero atlas, and the
  always-navy footer on every page) render the light variant, and the
  light-theme headers (docs/tutorials/releases/download/papers) keep the
  dark variant. Sizes grew again: header brand mark 46→52px, hero mascot
  50→70% of the atlas (~410px desktop, ~226px at 390px), footer mark
  39→44px. `favicon-block-arch.svg` is the blue house-check (byte-identical
  to `favicon.svg`), verified clearly visible at 16/32px on simulated light
  and dark browser chrome — no favicon change needed, preserving byte
  identity with the canonical brand copies. Playwright: 0 console errors on
  home/download/study-state/releases, no horizontal overflow at 390px;
  both validators pass.
- Scaled every mascot render up by roughly a quarter after further owner
  feedback (commit `a366462`): header brand mark 52→65px (header stays
  80px/72px, nav single-row), hero mascot 70→88% of the atlas with the
  atlas cap 560→640px and the hero grid rebalanced (30rem text column,
  4rem max gap) so the mascot renders ~610px at 1440px and ~284px at
  390px, and the footer mark 44→55px. Playwright-measured, 0 console
  errors, no horizontal overflow at 390px; both validators pass.
- Made mascot sizes viewport-driven after owner feedback that fixed pixel
  sizes still read small on a wide monitor (commit `c2dcccf`): header
  brand mark `clamp(44px, 4.5vw, 84px)`, footer mark
  `clamp(44px, 4vw, 68px)`, hero atlas `min(100%, 44vw, 880px)` with the
  mascot at 88% (up to ~840px rendered on wide monitors) and the hero
  canvas widened to `min(1500px, calc(100% - 48px))` (header/footer stay
  on the 1180px page). The text column returned to 34rem because the
  vw-scaled hero H1 broke mid-word in a 30rem column at the 9.8rem font
  cap. Every page's `assets/site.css` link now carries a `?v=2026-08-02-3`
  cache-buster so returning browsers pick up the new sizes (the repo
  validators strip query strings before reference checks; both pass).
  Playwright-verified at wide/1440/390 emulation: 0 console errors, H1
  single-line everywhere, no horizontal overflow, nav single-row.

## 2026-08-01 — Application-first homepage and product pages

- **BL-SITE-015.** The homepage was coding-agent-framed ("StatePort drives an
  AI coding agent for you") and neither StudyState nor container deployment
  appeared on it. Rebalanced the hero, metadata, and lead statement so the
  installed application is the product: durable, user-owned AI applications
  with state that survives sessions and change that stays reviewable and
  undoable. Added a two-pillar section naming StudyState (primary example)
  and governed container deployment (second pillar), with links into the
  new documentation.
- Created four documentation pages from verified product truth in the
  private StatePort repository (StudyState application-experience and sample
  fixtures, the deployment package contract, the alpha limitations record,
  and the release programme): `docs/study-state.html` (Focus default,
  start/pause/redirect lifecycle, reflection → review → explicit apply,
  persistent Undo with receipts, restart durability, and deliberate
  non-goals), `docs/deployments.html` (inspect → plan → digest-bound
  approval → apply with health checks → operate → remove/purge, the alpha
  refusal contract, and an explicit not-yet-supported list including
  upgrade/rollback revisions, remote hosts, registry distribution, and any
  cloud deployment), `docs/limitations.html` (single-user local product,
  Linux AMD64 + rootless Podman only, Codex CLI as the only exercised
  execution provider, no hosted service, no public download, no independent
  security review, no Azure deployment), and `docs/updates.html` (digest-
  pinned release bundles and approval-before-application as the design,
  health-gated update with rollback-or-truthful-refusal as the acceptance
  target, clearly marked as not user-available; signing stated as not yet
  established).
- Deliberately weakened the slice brief where the source material disagreed:
  deployment "update and rollback" is excluded from the current deployment
  slice in the implementation repository, so it is presented as future
  work; a "signed release index" has no evidence (signing is explicitly
  listed as not established), so the updates page says so; no "manual/notify
  update policy" exists in the sources, so the page describes the governance
  default (no silent background updating) instead.
- Wired discovery: sitemap entries with current lastmod, documentation hub
  catalogue entries with filter keywords, the four pages in every
  documentation sidebar, homepage pillar and availability links, a
  limitations link in the release-ledger summary and sidebar, and
  cross-links between the new pages. The release ledger's "Not available"
  honesty is unchanged; no download or install page was created; the
  fail-closed support link remains hidden; no contribution intake was added.
- `python3 scripts/validate_repo.py` and `python3
  scripts/check_site_quality.py` pass on each of the seven commits. Local
  only on `agent/noob-friendly-copy-001`; no push, no Pages deploy, no
  release-ledger availability change. Owner review and human acceptance
  remain pending.

## 2026-07-31 — Pre-render whitepaper Mermaid diagrams to inline SVG

- **BL-SITE-014.** The public and candidate Stateware whitepapers emitted
  ```` ```mermaid ```` blocks as `<pre class="mermaid"><code>…</code></pre>`,
  but the static pages loaded no Mermaid runtime, so every diagram rendered
  as raw source text on the live site (e.g. the v1.1 paper's six
  architecture/flow figures).
- Fix follows the repo's existing build-time convention (`.mmd` → rendered
  artifact, committed) instead of adding a client-side library: Markdown
  stays the source of truth and renders natively on GitHub; a new
  `scripts/render_paper_diagrams.py` renders each block to a static SVG via
  `mmdc` with the project theme (`config/mermaid-theme.json`), scopes every
  internal id per-diagram so the six inline SVGs never collide, and inlines
  the result into `papers/*.html`. The source `.mmd` files are kept under
  `assets/diagrams/src/paper/` for traceability.
- No visitor-runtime JavaScript and no third-party dependency are added, so
  the diagrams display with JavaScript disabled, consistent with the
  site's static-first policy; the existing global `prefers-reduced-motion`
  rule covers the diagrams. Added `.paper-diagram` styling: diagrams render
  at natural size with legible labels and scroll horizontally inside a
  contained figure when wider than the column.
- Label-clipping correction: mermaid bakes each label's
  `<foreignObject width/height>` from its render-time font metrics, and any
  visitor whose font differs (the common case, since Inter is not bundled)
  had the text cropped by `overflow: hidden`. Added
  `.paper-diagram foreignObject { overflow: visible }` so labels are never
  cut off; every label still fits inside its node rect, so there is no
  neighbour overlap.
- Verified locally: both papers show six figures each with theme-coloured
  nodes/labels (15 px), zero of 83 label foreignObjects clip, wide diagrams
  scroll, zero console errors, `scripts/validate_repo.py` (including a new
  guard that rejects unrendered `<pre class="mermaid">` in any paper HTML)
  and `scripts/check_site_quality.py` pass.
- Local only on `agent/noob-friendly-copy-001`. No push, no Pages deploy,
  no release-ledger or whitepaper publication change. The live site still
  shows raw diagram text until the owner merges this to `main` (Pages
  auto-deploys on push to `main`) and accepts it.

## 2026-07-28 — Runtime-language and hidden-support reconciliation

- Corrected the local candidate's categorical container claim. Homepage
  metadata and hero copy now state that the application and durable files run
  locally while declared agent jobs may use a sandbox or container when the
  operator configures one and the host supports it. The walkthrough page and
  narration source use the same boundary.
- Rebuilt the local narrated walkthrough so its spoken track and six verbatim
  captions agree with the corrected copy: 66.254 seconds, MP4 SHA-256
  `79cf3b1377e0bb3bfcbb540bdbedbf1d522016ccc8b82520f8f35ee92f9eaf42`, VTT
  SHA-256 `c1d74a9107c5b19ba47e64a6878ccdbb2e1944605cef71f97c9d09353c3cb582`.
  The deployed public video remains unchanged.
- Changed fail-closed support rendering to omit both the Ko-fi destination and
  any "being configured" message until a valid owner-provided URL and settings
  attestation exist. The independent About section remains useful without a
  dead-end support call to action.
- `render_support.py --check`, four renderer unit tests,
  `scripts/validate_repo.py`, `scripts/check_site_quality.py`, and
  `git diff --check` pass. This is local validation only: no push, deploy,
  public-runtime verification, or human acceptance occurred.

## 2026-07-28 — Fail-closed Ko-fi support integration

- Implemented `BL-SUPPORT-001` locally on `agent/support-link-001` as behaviour
  commit `616f01e5007f2a04e673484d9cd9d2eeb45e59ff`. The homepage now has a
  cardless About/Support section using the approved independent-development
  copy. When activated, the same plain external `Support StatePort` link is
  rendered there and in the existing footer; it announces its new-tab
  behaviour and uses `external noopener noreferrer`.
- Added `config/support.json`, `scripts/render_support.py`, and
  `SUPPORT_SETUP.md`. The renderer accepts only a direct HTTPS `ko-fi.com`
  profile URL and requires an explicit settings attestation before emitting
  either link. The owner setup requires Ko-fi Free, Contributor mode disabled,
  one-time tips, and no memberships, gated content, or supporter obligations.
  The repository cannot verify those provider-side settings and no account was
  created or modified during this slice.
- The current configuration has `publicUrl: null` and
  `settingsAttested: false`; the visible section says the link is being
  configured and the footer contains no support destination. This is the
  intended fail-closed state, not a claim that support is publicly available.
- Added four renderer tests covering disabled, unattested, enabled-accessible,
  and malicious/ambiguous URL cases. `render_support.py --check`, the unit
  tests, `scripts/validate_repo.py`, `scripts/check_site_quality.py`, and
  `git diff --check` pass. Local browser review at 1440px and 390px confirmed
  the section layout and semantic structure with no console errors. No push or
  deployment was performed; human acceptance remains separate.

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
