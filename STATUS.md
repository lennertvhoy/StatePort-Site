# StatePort Site status

**Updated At:** 2026-08-31
**Execution Mode:** operating
**Project State:** alpha10_ghcr_verified_site_publication_prepared_pages_pending
**Canonical:** `main`; exact head derives from Git
**Hosting:** https://lennertvhoy.github.io/StatePort-Site/

## Current truth

- `v0.1.0-alpha.10` is the signed public-test candidate for exact target
  `wsl2-ubuntu2404-linux-amd64-rootless-podman-quadlet`.
- Its release-index SHA-256 is
  `2fc626fcab180f664f04f36d1fcceacaffa81ca96a658585f6684e3cf37abf89` and
  signed payload is
  `sha256:2478e9c69aac1679813c448d25a7648e68d81f44daaa2d7bc3085aaf86b7b222`.
- All seven exact image manifests are published to GHCR and anonymously match
  by both `0.1.0-alpha.10` tag and signed digest reference.
- Two independent governed clean Ubuntu 24.04 rehearsals passed install and
  identical rerun against the exact candidate through the prepublication
  digest-only registry transport.
- The exact Site release tree, mutable pinned bootstrap, public copy, and
  Alpha.7 fail-closed launcher are locally prepared. Pages deployment and
  anonymous byte verification are pending.
- Alpha.10 has no authenticated predecessor under its current trust root;
  rollback is unsupported. Alpha.7 remains retained but is superseded and its
  installer route is fail-closed.
- Canonical source commit `930c2d9a` / tree `726d1dcb` remains private. Public
  snapshot `457423be` / tree `7eff2b9b` is anonymously resolvable from
  `lennertvhoy/StatePort-Source`.
- Owner clean-install, human acceptance, independent security review, stability,
  and production qualification remain absent.

## Exact next action

Validate and publish the prepared Site content, anonymously match Pages bytes,
then run the direct public Site/GHCR rehearsal before owner handoff.
