# Evidence: alpha16-public-install-001

## Current status

On 2026-09-05, a fresh public Alpha.16 Ubuntu 24.04 QEMU/KVM rehearsal
failed package preflight: the bootstrap fetched the predecessor signature but
omitted its digest-addressed directory required by the production verifier.
Published Alpha.16 bytes remain immutable. Its source repair awaits a reviewed
additive successor and new qualification. Do not repeat the unchanged installer
as a repair. This is simulation evidence, not native WSL2 evidence.

Command: `python3 infra/qualification/wsl2_rehearsal.py --local-public` in StatePort.
Failure artifacts: `/home/ff/.local/state/stateport/qualification/local-public/alpha16-21ynxhq2/`;
StatePort evidence: `evidence/one-line-release-001/alpha16-rehearsal-failure.json`.
Missing predecessor slot:
`56d8761f1bcc23109cef0b20cdbd6adf3b9844cc7c2afb181bd48a16fa9802a7/release-index.sigstore.json`.


Alpha.16 is the additive successor to immutable Alpha.15. It carries the
smallest fix for the native installer defect observed during the Alpha.15
journey: provisioning reconciled the web service to port `18621`, while the
installer printed the stale pre-reconciliation port `18638`. Alpha.16 derives
the printed and persisted local URL from the live reconciled web unit.

The Alpha.16 release candidate is assembled, signed, scanned, and its seven
OCI images were pushed at exact digest-pinned GHCR references. These packages are currently private; the historical push and digest checks do not establish anonymous image access. The Site was
published from commit `a2225169a0450cd160b3aafa6fd0f2e16c9790ef` through the
guarded Pages push. Anonymous verification then matched all 66 Alpha.16
protected files and all 64 retained Alpha.15 versioned files, including their
response headers and final bytes. No native Windows 11 WSL2 receipt or human
acceptance is claimed here.

## Primary journey

Command:
`bash <(curl -fsSL https://lennertvhoy.github.io/StatePort-Site/download/install.sh)`

Environment: fresh Windows 11 AMD64 host, WSL2, stock Ubuntu 24.04, normal
sudo-capable user, anonymous public Pages and GHCR, with no checkout, prepared
packages, mirrors, shims, or staged files.

Status: `blocked`. Publication byte verification is historical transport evidence, not a passed primary journey. Native validation remains pending.

## Candidate identity

- Version: `0.1.0-alpha.16`.
- Release-index SHA-256:
  `8dad6399e66956d1dcb5aebb5a5119c6001617b3279902f0746857b5e6bfac47`.
- Signed payload digest:
  `sha256:5594dc7dc3711ffdfbd74da271012c02dc23e5fa626d12f59d41a768058b2bac`.
- Release-index signature bundle SHA-256:
  `ff36ca75c5139d58a92e7d9b78a53f120aa4e4f42cdf9be35603eef3e682b557`.
- Bootstrap SHA-256:
  `6feedf5273547f4a98f5d8edb6fe24e729104ad822c4d58da70cb1f0fdad417a`.
- Trust public-key SHA-256:
  `798d6ea6e2703993758f0fb45618b1f05b40f6ef116e7d286fd5a6867859b8ad`.
- Trust fingerprint:
  `sha256:df24c1ccdcf1ecf72da6d8d81ae8b0ffaca8d399826091b107cc4d6905915ea5`.
- StatePort source commit:
  `0807b68edca8a1ae6fc1c1f16ddba9740783a951`.
- StatePort source tree:
  `126587c310cf195e1ac06a59d76134ab6f8cc975`.
- Public source commit:
  `05c2ace3b07233c1a84bd2a4b006c7ec6d2a918f`.
- Public source tree:
  `cdc5769ff933599fba8c74d95842eb7cae0b0bd5`.
- Public source manifest:
  `sha256:53b8a5523ea187cfb196e9afc8cee5b115fc30cf0f5ab13c54db14c0959ba4e2`.
- Source archive:
  `sha256:7e106b4d72895f5d77593d0111d4d53bdb02a2318d2c63e0a364630c31e1d47c`.

Image manifest digests:

- `stateport-api`: `sha256:95c3adccacfaabfb70430d299a578c33ebafa2f0fb16ab129d0ac271847a3c73`
- `stateport-dev-workspace`: `sha256:fee3e363718c71222fdcacfd63fa61088ecae66da727c617a92ca9fc3e635e43`
- `stateport-execution-host`: `sha256:221ddc06dd59cd3c5810b2d38a0eb5c44aaaa4bb522abcdc8b5ed0e4d2b3793e`
- `stateport-playwright`: `sha256:885f078be50869a958f7867c74b75760dc7bafef33579877ef769d4cc2e182fe`
- `stateport-runner`: `sha256:38086218681ba5b64adece703cda8eed817a692c7f0436faccbe6bfae4143885`
- `stateport-web`: `sha256:bbb120242e44e77b79de85d924021b3a2950ed6ff304061c6a6f8482f98b486d`
- `stateport-worker`: `sha256:a4367aa99b222a80fe420afa1e48c937bda2a5c38bc2d6d5a202167a2d30fad3`

## Secondary checks

- Public source materialization passed for StatePort commit
  `0807b68edca8a1ae6fc1c1f16ddba9740783a951`; the sanitized public snapshot
  was published normally as public commit
  `05c2ace3b07233c1a84bd2a4b006c7ec6d2a918f`.
- Release bundle assembly, seven reproducible image builds, fresh vulnerability
  evidence collection, image signing, index signing, and Alpha.16 site staging
  passed through the existing guarded heavy-run path.
- Authenticated GHCR publication passed with exact remote manifest verification for all seven
  image references. The durable receipt is outside Git at
  `/home/ff/.local/state/stateport/release/alpha16/ghcr-publication-r3.json`.
- Guarded Pages publication passed from commit
  `a2225169a0450cd160b3aafa6fd0f2e16c9790ef`; the governor receipt is at
  `/home/ff/.local/state/stateport/release/alpha16/governor-site-publication-r1/background-safe-v1.json`.
- Anonymous protected-byte verification passed for all 66 Alpha.16 files and
  all 64 retained Alpha.15 versioned files. The receipt, including response
  headers, final URLs, complete hashes, source audit, and exact GHCR identity,
  is at `/home/ff/.local/state/stateport/release/alpha16/public-byte-verification-r2.json`.
- Anonymous current-page, CSS, mascot-asset, sitemap, and historical-claim
  verification passed for 13 public pages and 3 assets. The receipt is at
  `/home/ff/.local/state/stateport/release/alpha16/public-site-verification-r2.json`.
- Alpha.15 protected bytes remain covered by the pre-Alpha.16 inventory and the
  Site validator retains Alpha.15 as an immutable predecessor.
- The shared header mascot remains at the accepted approximately 1.75x desktop
  rendering contract; Alpha.16 does not alter its image bytes or layout.

## Artifacts

- Staged Site candidate: `/home/ff/.local/state/stateport/release/alpha16/staged-site-r3`.
- Alpha.16 release candidate: `/home/ff/.local/state/stateport/release/alpha16/candidate-r1`.
- Image build, signing, and scan evidence: `/home/ff/.local/state/stateport/release/alpha16`.
- Alpha.15 rollback/status inventory and protected-byte inventory:
  `/home/ff/.local/state/stateport/release/alpha15/luna-closure-backup/`.

## Limitations

- A genuinely fresh native Windows 11 WSL2 Ubuntu 24.04 run of the exact public
  command is pending. QEMU and prepared Linux evidence are not substitutes.
- Native service, execution, persistence, three-template, restart, WSL
  shutdown/restart, uninstall, reinstall, and human-acceptance results are not
  claimed until the native receipt exists.

## Next action

Publish the additional registry-failure guidance after its local checks. Resolve
anonymous access through reviewed release publication without exposing unreviewed
historical package versions. Qualify a reviewed
additive successor using agent-owned local disposable environments, then retain
separate native evidence when feasible. Do not ask the owner to retry Alpha.16.

## Site core refresh and documentation correction — 2026-09-05

Refreshed `scripts/projectstate_gate.py` from a fresh temporary core generated by
ProjectState_Template at required commit `7e4cb7c3397324d09f768eeb1d722316714c46e1`.
Reviewed generated instructions and `docs/UPGRADING.md`; retained the owner-authored
AGENTS notice, product contract, immutable release bytes, and untracked evidence.
Restored the native primary journey to `blocked` and retained public transport
verification above as a separate claim. Local checks are recorded below when run.
The named native journey remains blocked; the refresh notice remains in place.

Local checks: `python3 scripts/validate_repo.py` and
`python3 scripts/check_site_quality.py` passed (29 public pages, including
protected release-byte verification, links, metadata, privacy, and static layout
contracts). `python3 -m unittest scripts.test_render_support scripts.test_site_runtime
scripts.test_containment scripts.test_contrast` passed all 30 checks.
Upstream `python3 scripts/test_outcome_core.py` passed all 20 regression tests.
The corrected Site gate exits 1 (`OUTCOME NOT VALIDATED`) with no schema errors.
The direct `python3 scripts/test_render_support.py` invocation cannot resolve its
package imports; its existing module invocation above passes.
These edits are local only; no new publication or native installation is claimed.


## Additional anonymous registry blocker — 2026-09-05

The lead observed anonymous image access returning HTTP 401. Read-only GitHub
package inspection at 2026-09-05T07:59:34Z confirms all seven nested Alpha.16
GHCR packages are private. This is an additional installation boundary after
signature preflight, not evidence that the failed guest reached image startup.
Only seven exact Alpha.16 digests match reviewed signed records. Fourteen older
Alpha.5/6-tagged versions do not match the checked public signed indexes;
package-wide visibility must remain unchanged. Tags are not provenance.

Evidence: `/home/ff/.local/state/stateport/release/alpha17/registry-visibility-review.json`.
The prior signature-failure correction was deployed from `f2b0c4f`; the lead
verified twelve mutable pages anonymously against deployed bytes. The earlier
local-only statement describes that correction before deployment. This additional
registry notice is local pending lead review/publication. No installer, immutable
release files, package visibility, or owner-authored instructions were changed.

Current mutable install, release, and support notices disclose both blockers;
release/evidence pages no longer describe the private images as publicly
available. Native and complete-product qualification remain blocked.

Checks for the registry correction: `python3 scripts/validate_repo.py` passed,
including protected immutable bytes; `python3 scripts/check_site_quality.py`
passed for 29 pages. `python3 -m unittest scripts.test_render_support
scripts.test_site_runtime scripts.test_containment scripts.test_contrast`
passed all 30 tests. `python3 scripts/projectstate_gate.py` exits 1 as expected
(`OUTCOME NOT VALIDATED`: installation and native journey remain blocked).
`git diff --check` passed. These are local Site checks, not deployment or
installed-runtime qualification.

## Public experience review — 2026-09-05

Reviewed the persistent-threads handoff upgrade guidance, core instructions, and
gate. The installed gate already byte-matches that reference. Added optional
thread rules without starting threads or changing models. Existing staged
AGENTS edits and untracked alpha14 evidence are preserved. The named fresh
Windows 11 WSL2 journey cannot run in this Linux session and remains blocked;
no product checkout or installer was executed. Refresh notices remain pending
that validation. The user authorized improving Site and Papers and explicitly
restricted StatePort to read-only access. Documentation work continues within
the current slice without altering release artifacts or qualification claims.

## Integrated experience refresh — local result, 2026-09-05

The site, papers reading room, documentation navigation, static contents, and
71-second narrated field guide are implemented locally. The mascot bytes and
size contract remain unchanged. The Site's existing staged/unstaged AGENTS
changes and untracked alpha14 evidence were preserved. No StatePort product
checkout file was edited and no product runtime or installer was executed.

Defects corrected: mobile status link collapsed into a narrow column; stale
StateSpec breadcrumb on the install guide; oversized guide headers; install
copy that risked replacing existing WSL configuration; retries recommended
despite known Alpha.16 blockers; no-JavaScript filter presented as usable;
long documentation contents dependent on JavaScript. The reading-room hub
distinguishes the public 1.1 paper from its 1.2 candidate.

Local environment: Linux workstation, Python 3.14, Chromium 151.0.7922.173 (Arch Linux),
Playwright from the managed Codex runtime; http.server at 127.0.0.1:4173.
Browser version was obtained from `chromium --version`.

Checks:

- `python3 scripts/validate_repo.py`: passed, including immutable release and
  mascot-byte/size protection. It reports the existing product outcome blockers.
- `python3 scripts/check_site_quality.py`: passed for 31 HTML pages, including
  local references, metadata, media, caption duration, privacy and asset budgets.
- `python3 -m unittest scripts.test_render_support scripts.test_site_runtime
  scripts.test_containment scripts.test_contrast`: all 30 passed.
- Headless focused journey: 48 views across eight routes, 360/768/1440px, with
  and without JavaScript; no overflow, broken loaded images, missing H1 or
  script errors. Filter, gallery dismissal, mobile navigation, and actual video
  playback passed. `experience-browser.json` contains the results.
- Final sitemap journey: all 29 sitemap routes, phone with JavaScript and
  desktop without it (58 views), passed the same structural browser checks.
  `experience-all-pages.json` contains the results. The separate quality check
  includes non-sitemap historical/error pages as well.
- Rendered page screenshots were inspected; mobile status layout and reading
  headers were corrected after visual review. Source checks alone did not catch
  the status-column defect. Lazy images were decoded before image validation.
- HyperFrames 0.8.29: zero lint/runtime/layout/motion warnings after corrections;
  50/50 text contrast checks passed. Final video: H.264, 1920x1080, 24fps, 71s,
  AAC audio, 16 WebVTT cues. Captions match the narration text and served duration.
  Rendered frames, cursor placement and chapter cuts inspected; FFmpeg found no
  black interval of 0.25s or longer. Audio-level evidence is in the local review
  directory. This is documentation footage, not installed-product evidence.
- `git diff --check`: passed.

Media source, voice stems, original ambient audio and render logs are preserved
outside the Pages tree at `/home/ff/Projects/.local/stateport-site-media-sep05/`.
The media manifest records final public asset hashes. Site screenshots and
render inspection files are in ignored `output/experience-review/`. The media
render used a separate transient 3G/150% CPU scope; the product release governor
requires product-release inputs and was not invoked for this media-only job.

No commit, push, deployment, native WSL2 installation, or human acceptance is
claimed for this refresh. Existing publication receipts earlier in this summary
remain historical. The site primary journey and refresh notices remain blocked
until the named complete-product Windows journey is actually validated.


## Owner steering — handoff only, 2026-09-05

The owner requested implementation in a fresh session. The latest local
ProjectState template must be integrated into the papers, the mascot must
be 25% smaller, and the video must show StatePort itself. The owner rejected
the documentation-footage direction. Earlier technical checks remain
historical evidence, not acceptance of that video or validation of these
pending revisions. No product/UI/media changes were made for this handoff.

Canonical next-session handoff: `HANDOFF_2026-09-05-PRODUCT-VIDEO-AND-PAPERS.md`.
StatePort remains read-only; preserve all existing work.


## Product capture prerequisite — 2026-09-05 resumed session

Reviewed the queued reference's upgrade guidance, core instructions and gate;
the installed gate byte-matches the reference and optional threads remain inert.
The native Windows primary journey is still unavailable; retain refresh notices.
Downloaded the public installer anonymously to `output/product-refresh/public-install.sh`.
Its SHA-256 still matches the immutable Alpha.16 bootstrap
`6feedf5273547f4a98f5d8edb6fe24e729104ad822c4d58da70cb1f0fdad417a`.
Running `bash output/product-refresh/public-install.sh` on this native Linux
workstation exits 1 before changes: `WSL2 is required; WSL1 and native Linux
are not this release target.` This is a local install refusal, not a native
Windows journey attempt or an installed product. The outcome gate exits 1.
Fresh screenshots and product video depend on a usable separately installed
public release; the development checkout/runtime remains untouched.


## Independent local build and visual corrections — in progress

The owner authorized a local-file installation after the public path refused.
Created an independent snapshot of committed StatePort source
`28f72db7ef8f30e6a3a24641c4d61f8b58d5a297` at
`/home/ff/.local/share/stateport-local/releases/28f72db7ef8f30e6a3a24641c4d61f8b58d5a297`.
It has its own Git metadata and no development-checkout symlinks/remotes.
Prepared a uv-managed Python environment build, separate XDG data paths and
three local service units on ports 18780/18790/18791. No usable installation
is claimed until build/start and the real product journey pass.
The governor refused admission with exit 75 because another release compilation
holds the shared lock; that process was not disturbed.

Gallery image CSS now preserves intrinsic proportions without a stretched
letterbox border. Corrected the old conversation caption to match the actual
development fixture. Header/footer mascot rendered dimensions are 75% of
previous values, with artwork byte checks retained. Template docs explain the
current v6 workflow independently of product validation. Site validators pass,
58 sitemap browser views report no structural defects, and all 30 unit tests
pass. New product captures and video remain pending local startup.


## Fresh installed-product media and local result — 2026-09-05

The public bootstrap refused native Linux before mutation. With the owner's
explicit fallback authorization, installed an independent local source snapshot
under `/home/ff/.local/share/stateport-local`, using uv-managed CPython 3.13.15
and the source's hashed runtime dependency lock. Frontend dependencies were
installed from its lock and the production frontend built in that snapshot.
The guarded build passed after the existing release compilation released the
mission lock. The snapshot's Git metadata is independent; no dev checkout
symlinks/remotes are used. Original commit: `28f72db7ef8f30e6a3a24641c4d61f8b58d5a297`.

Local URL: `http://127.0.0.1:18780`; controls: `stateport-local`
`start|stop|restart|status|logs`; app launcher: **StatePort (Local)**. Three
separate systemd user services use isolated XDG data and loopback ports
18780/18790/18791. The target is enabled for user login. This does not claim a
machine reboot test. No provider credentials were copied and no model choice
was changed. External execution-host setup, worker execution and provider
configuration remain separate limitations, visible in readiness.

Real local journey passed: installed StudyState Sample through Catalog;
prepared and approved the exact Start change; drafted, reviewed and applied a
reflection; inspected the applied receipt; restarted the service and verified
50% progress plus the exact reflection persisted. Self-reported evidence is
explicitly unassessed. `local-installation.json` records the changed PIDs and
checks. An exploratory duplicate proposal was rejected through the normal UI.
The capture script initially waited for a control hidden by the success panel;
reloading showed the successful persisted change. No UI result was fabricated.

Replaced all four homepage preview captures with fresh images from this
installation, including the phone view. Corrected their alt text, captions and
intrinsic dimensions; the gallery keeps the image's aspect ratio and the phone
thumbnail uses contain. Historical originals are retained in the external media
source. The immutable historical 33-second overview is unchanged.

Replaced the rejected documentation guide with an 86-second H.264/AAC product
guide, narrated with Edge Andrew, with 20 matching caption cues, a fresh poster,
chapter timings and verbatim transcript. Real captured controls determine the
animated pointer positions; the actions themselves were performed during capture.
HyperFrames checks: zero lint/runtime/layout/motion errors or warnings, 50/50
contrast checks passed. Inspected rendered review, reflection and restart frames.
FFmpeg found no black interval at least 0.25s; audio mean -21.9dB, peak -2.9dB.

Source: `/home/ff/Projects/.local/stateport-product-guide-sep05/`. Media rendering
used the handoff's separate 3G/150% CPU scope. A first attempt at release-governor
admission found another release job; that lock was not changed or bypassed.
The optional Nice setting was unsupported on a scope and was moved to the
wrapped `nice` command. `experience-media.json` records final asset hashes.

Papers: latest-template content and 25% mascot reduction are independently
validated in its own evidence; nine PDFs, 120 pages. The product checkout
remains read-only. Local installation and sample behavior do not satisfy the
fresh Windows WSL2 public release journey; its gate remains blocked.

The independent installation also imported snapshots of the actual local
ProjectState and StudyState templates (tracked working changes included).
Original source repositories are unchanged; the import root is restricted to
`stateport-local/imports`. Both managed applications appear after reload.
The capture automation raced automatic navigation after import and timed out;
a new browser session confirmed both completed imports. Imported ProjectState
reports unavailable package metadata and Runs, so no template execution claim
is made. Sample review/apply/persistence remains the verified local workflow.

Final sitemap browser check: 58 views, zero structural defects; video playback
uses the new 86-second asset and captions. Site validators and diff whitespace
check pass. Separate gallery checks are recorded in `product-gallery.json`.

Publication proof is written to
`/home/ff/Projects/.local/stateport-product-guide-sep05/publication-verification.json`
by the guarded publisher's anonymous verifier. That receipt records exact
remote-byte matches and the observed commit after deployment; absence or a
failed result does not establish publication. This fixed evidence pointer
avoids a companion state-only commit after deployment.

Final checks: Site validators pass; all 30 unit tests pass; 58 sitemap views
and 12 gallery views pass. The native outcome gate still exits 1 with the
recorded release blockers. Prior untracked Alpha.14 evidence is unrelated
legacy material and remains preserved outside this change's staging.
