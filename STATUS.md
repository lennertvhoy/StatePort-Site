# StatePort Site status

**Updated At:** 2026-09-03
**Execution Mode:** operating
**Project State:** alpha12_published_public_test_candidate_install_enabled_mutable_install_carries_transport_repairs
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
- The versioned Alpha.12 bootstrap remains immutable (31,576 bytes, SHA-256
  `e552898fc2611d94bd6ec361624e8c95dcaaffcecc259ed1a7c20f08c01c2701`).
- The mutable installer route `download/install.sh` now carries transport
  repairs over that immutable bootstrap (33,276 bytes, SHA-256
  `efc4f388e259ab6a25fc4d9be438629ea122aef7920732695473befcf7bfd95a`): it
  stages the release-index and every image signature bundle into its
  content-addressed `$tmp/<sha256>/<name>` slot, and it installs the real
  `python3-venv` package (Ubuntu universe, exactly matching the signed bundle
  record) before the immutable installer's package-preflight admission. The owner's Alpha.12 public-path test first
  refused with `signature bundle is not a regular file` on the missing digest
  slots, then after that fix with `installed python3-venv package identity is
  malformed` caused by apt leaving a negative not-installed record when only
  `python3.12-venv` was installed without `python3-venv` itself.
- Alpha.12 is not yet accepted by the owner. A clean owner public-path install
  receipt is still pending after the mutable-route repair; independent security
  review, stability, and production qualification remain absent.
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
