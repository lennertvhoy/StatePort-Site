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
