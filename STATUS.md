# StatePort Site status

**Updated At:** 2026-09-02
**Execution Mode:** operating
**Project State:** alpha11_published_public_test_candidate_install_enabled
**Canonical:** `main`; exact head derives from Git
**Hosting:** https://lennertvhoy.github.io/StatePort-Site/

## Current truth

- `v0.1.0-alpha.11` is the current signed public-test candidate for exact
  target `wsl2-ubuntu2404-linux-amd64-rootless-podman-quadlet`. It is
  published, install-enabled, and reported `compatible_unvalidated`.
- Its release-index SHA-256 is
  `8a26f7d36b5c6883c314db7323c4a79a497e0973e0ec671c02c6b38f0f533f2c` and
  signed payload is
  `sha256:9b98e07040107fe0644a2b95648a19bef3aef50df540dde77460880dc204f51c`.
- The mutable installer route `download/install.sh` is byte-identical to the
  versioned Alpha.11 bootstrap (31,576 bytes, SHA-256
  `9aaea4790059579d22db4e5537485a84cc094d9f2b8b0bafc04c618b5e0052df`) and
  serves the Alpha.11 install path.
- Alpha.11 provisions a pinned, verified Podman 5.4.2 package set from the
  signed release bundle on the stock Windows 11 + WSL2 + Ubuntu 24.04 path.
- Alpha.11 is not yet accepted by the owner. A clean owner public-path install
  receipt is still pending; independent security review, stability, and
  production qualification remain absent.
- Alpha.10 is owner-rejected and install-disabled after stock Ubuntu 24.04
  supplied Podman 4.9.3 below StatePort's floor while rehearsals had
  preinstalled 5.4.2. Its exact immutable files remain published for
  inspection only. Its containment commit `27bcf6c` was anonymously verified.
- Alpha.7 remains retained but superseded and install-disabled.
- Canonical source commit `57dae10f` / tree `c17f0ba7` remains private. Public
  snapshot `34ca6ef4` / tree `408f0c0f` is anonymously resolvable from
  `lennertvhoy/StatePort-Source`.
- Alpha.11 has no authenticated predecessor under its current trust root;
  rollback is unsupported.

## Exact next action

Run the Alpha.11 owner public-path install test on a real Windows 11 + WSL2 +
Ubuntu 24.04 host and record the clean-install receipt, then the human
acceptance verdict.
