# StatePort Site status

**Updated At:** 2026-08-14
**Execution Mode:** operating
**Project State:** alpha5_published_deployed_and_remotely_verified_owner_test_pending
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
- Alpha.5 content commit `6cf95ca855e94f7648afb93fa870390a8c8bc8a7`
  is deployed through Pages build `1151371842`, run `31820163492`, and
  deployment `5909824336`. All 33 immutable Alpha.5 files, the mutable
  bootstrap, and six current release surfaces match local bytes remotely.

## Exact next action

The owner runs the published instructions on a fresh Windows 11 + WSL2 +
Ubuntu 24.04 host and returns the exact receipts. Until then Alpha.5 remains
`compatible_unvalidated`, unaccepted, and not production-qualified.
