# Evidence: alpha16-public-install-001

## Current status

Alpha.16 is the additive successor to immutable Alpha.15. It carries the
smallest fix for the native installer defect observed during the Alpha.15
journey: provisioning reconciled the web service to port `18621`, while the
installer printed the stale pre-reconciliation port `18638`. Alpha.16 derives
the printed and persisted local URL from the live reconciled web unit.

The Alpha.16 release candidate is assembled, signed, scanned, and its seven
OCI images are published at exact digest-pinned GHCR references. The Site was
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

Status: `publicly_verified`; native validation is pending an approved Windows target.

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
- GHCR publication passed with exact remote manifest verification for all seven
  image references. The durable receipt is outside Git at
  `/home/ff/.local/state/stateport/release/alpha16/ghcr-publication-r3.json`.
- Guarded Pages publication passed from commit
  `a2225169a0450cd160b3aafa6fd0f2e16c9790ef`; the governor receipt is at
  `/home/ff/.local/state/stateport/release/alpha16/governor-site-publication-r1/background-safe-v1.json`.
- Anonymous protected-byte verification passed for all 66 Alpha.16 files and
  all 64 retained Alpha.15 versioned files. The receipt, including response
  headers, final URLs, complete hashes, source audit, and exact GHCR identity,
  is at `/home/ff/.local/state/stateport/release/alpha16/public-byte-verification-r1.json`.
- Anonymous current-page, CSS, mascot-asset, sitemap, and historical-claim
  verification passed for 13 public pages and 3 assets. The receipt is at
  `/home/ff/.local/state/stateport/release/alpha16/public-site-verification-r1.json`.
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

Run the existing native WSL2 qualification command on an approved Windows 11
host and retain its machine-generated receipt before requesting human
acceptance.
