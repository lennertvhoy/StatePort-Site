# StatePort Site status

**Updated At:** 2026-08-14
**Execution Mode:** operating
**Project State:** alpha5_site_candidate_locally_validated_awaiting_commit_push_and_deployment
**Canonical:** `main`; exact head derives from Git
**Hosting:** https://lennertvhoy.github.io/StatePort-Site/

## Current truth

- `v0.1.0-alpha.5` is the current signed public-test candidate for exact target
  `wsl2-ubuntu2404-linux-amd64-rootless-podman-quadlet`. Its signed index
  SHA-256 is `4613fcad48ea1a2e7dd4350d61baa333efbc734b1fcba1a1c9ca62994d562b71`
  and signed payload is
  `sha256:e45d5c8ce6843bd0c3155ecd26940ff3dc11c5069a2de796a079708066faf98c`.
- The immutable 33-file Alpha.5 tree is anchored by Site commit
  `eaa1ca6a67844259860917442a95c891d097939f`. The mutable bootstrap is
  byte-identical at SHA-256
  `104c7fd6a87014548e583e524918550cece08aac71af4fc2f764ff5edae2ed0a`.
- Installation is enabled only for a controlled Windows 11 + WSL2 + Ubuntu
  24.04 AMD64 public test. WSL2 reports `compatible_unvalidated`; no real-host
  clean-install receipt exists yet. Owner acceptance, independent security
  review, stability, and production qualification are absent.
- Canonical source commit `256d8761` / tree `e7fb80c5` remains in private
  development Git. Signed public snapshot `6911b7c1` / tree `05ca882f` is
  anonymously resolvable from `lennertvhoy/StatePort-Source`. The curated
  Alpha.5 source archive is public and AGPL/CC-BY classified.
- Alpha.3 remains signed, byte-intact, install-disabled, and historical. Its
  erratum remains public. Alpha.2 remains superseded and install-disabled.
  Neither retained release tree changed.
- The last remotely verified Pages deployment still predates Alpha.5. The
  local publication candidate is not public until it is pushed, deployed by
  the managed legacy Pages provider, and remotely digest-checked.

## Exact next action

Commit and push the locally validated Alpha.5 publication closure, then verify
the managed Pages deployment and every public Alpha.5 file without claiming
the deferred real-host result.
