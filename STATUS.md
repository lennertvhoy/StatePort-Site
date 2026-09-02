# StatePort Site status

**Updated At:** 2026-09-02
**Execution Mode:** operating
**Project State:** alpha12_published_public_test_candidate_install_enabled
**Canonical:** `main`; exact head derives from Git
**Hosting:** https://lennertvhoy.github.io/StatePort-Site/

## Current truth

- `v0.1.0-alpha.12` is the current signed public-test candidate for exact
  target `wsl2-ubuntu2404-linux-amd64-rootless-podman-quadlet`. It is
  published, install-enabled, and reported `compatible_unvalidated`.
- Its release-index SHA-256 is
  `8fab98e60b1f4ed067aa8b3f2c8552f3dda266b53328c601eb67ce93671bfabb` and
  signed payload is
  `sha256:a16b154f37270f4aed2d7c7e60ee32279c7f36b6a1759aa1b7301cc787f708b1`.
- The mutable installer route `download/install.sh` is byte-identical to the
  versioned Alpha.12 bootstrap (31,576 bytes, SHA-256
  `e552898fc2611d94bd6ec361624e8c95dcaaffcecc259ed1a7c20f08c01c2701`) and
  serves the Alpha.12 install path.
- Alpha.12 repairs the Alpha.11 install-path defect: the installer imports the
  updater wheel from its zip, and the release-contract schema loader reads
  schemas as zip members when no filesystem path exists. It packages the
  corrected updater wheel and seven reproducible images from source
  `2343197a` on the stock Windows 11 + WSL2 + Ubuntu 24.04 path.
- Alpha.12 is not yet accepted by the owner. A clean owner public-path install
  receipt is still pending; independent security review, stability, and
  production qualification remain absent.
- Alpha.11 is superseded and install-disabled: its mutable route now serves
  Alpha.12. Its exact immutable files remain published for inspection only as
  the retained predecessor record.
- Alpha.10 is owner-rejected and install-disabled after stock Ubuntu 24.04
  supplied Podman 4.9.3 below StatePort's floor while rehearsals had
  preinstalled 5.4.2. Its exact immutable files remain published for
  inspection only. Its containment commit `27bcf6c` was anonymously verified.
- Alpha.7 remains retained but superseded and install-disabled.
- Canonical source commit `2343197a` / tree `6e3a169c` remains private. Public
  snapshot `a925496a` / tree `50b75c58` is anonymously resolvable from
  `lennertvhoy/StatePort-Source`.
- Alpha.12 has no authenticated predecessor under its current trust root;
  rollback is unsupported.

## Exact next action

Run the Alpha.12 owner public-path install test on a real Windows 11 + WSL2 +
Ubuntu 24.04 host and record the clean-install receipt, then the human
acceptance verdict.
