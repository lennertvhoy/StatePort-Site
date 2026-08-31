# StatePort Site status

**Updated At:** 2026-08-31
**Execution Mode:** operating
**Project State:** alpha10_published_public_transport_verified_owner_journey_pending
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
- Content commit `24428baa` deployed through Pages build `1185989241`, run
  `33408727082`, and deployment `6184162311`. Anonymous checks matched all 75
  changed paths, all 39 Alpha.10 release and manifest files, and all 81 retained
  immutable files.
- A fresh governed guest then used anonymous Pages and GHCR directly, with no
  guest-local Site, registry mirror, or retained-archive transport. Bootstrap
  fetch, runtime smoke, all seven manifest checks, materialization preflight,
  install, and identical rerun passed.
- Alpha.10 has no authenticated predecessor under its current trust root;
  rollback is unsupported. Alpha.7 remains retained but is superseded and its
  installer route is fail-closed.
- Canonical source commit `930c2d9a` / tree `726d1dcb` remains private. Public
  snapshot `457423be` / tree `7eff2b9b` is anonymously resolvable from
  `lennertvhoy/StatePort-Source`.
- Owner clean-install, human acceptance, independent security review, stability,
  and production qualification remain absent.

## Exact next action

The owner runs the published Windows 11, WSL2, Ubuntu 24.04, and private
`Study_Lenny` journey and records the human verdict. Engineering publication
evidence does not supply that owner outcome.
