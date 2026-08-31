# StatePort Site status

**Updated At:** 2026-08-31
**Execution Mode:** operating
**Project State:** alpha10_owner_rejected_mutable_installer_containment_pending
**Canonical:** `main`; exact head derives from Git
**Hosting:** https://lennertvhoy.github.io/StatePort-Site/

## Current truth

- `v0.1.0-alpha.10` remains signed and immutable for exact target
  `wsl2-ubuntu2404-linux-amd64-rootless-podman-quadlet`.
- Its release-index SHA-256 is
  `2fc626fcab180f664f04f36d1fcceacaffa81ca96a658585f6684e3cf37abf89` and
  signed payload is
  `sha256:2478e9c69aac1679813c448d25a7648e68d81f44daaa2d7bc3085aaf86b7b222`.
- All seven exact image manifests are published to GHCR and anonymously match
  by both `0.1.0-alpha.10` tag and signed digest reference.
- The owner rejected Alpha.10 on a freshly created stock Windows 11, WSL2, and
  Ubuntu 24.04 instance before `Study_Lenny`: Noble supplied Podman 4.9.3 below
  StatePort's floor.
- The rehearsals had preinstalled Questing Podman 5.4.2 before running the
  bootstrap. Their install passes therefore do not prove the clean owner path.
- Content commit `24428baa` deployed through Pages build `1185989241`, run
  `33408727082`, and deployment `6184162311`. Anonymous checks matched all 75
  changed paths, all 39 Alpha.10 release and manifest files, and all 81 retained
  immutable files.
- The mutable Alpha.10 installer route is being fail-closed. Versioned Alpha.10
  files and signatures remain unchanged for inspection.
- Alpha.10 has no authenticated predecessor under its current trust root;
  rollback is unsupported. Alpha.7 remains retained but is superseded and its
  installer route is fail-closed.
- Canonical source commit `930c2d9a` / tree `726d1dcb` remains private. Public
  snapshot `457423be` / tree `7eff2b9b` is anonymously resolvable from
  `lennertvhoy/StatePort-Source`.
- Alpha.10 is owner-rejected, not clean-installed or accepted. Independent
  security review, stability, and production qualification remain absent.

## Exact next action

Deploy and anonymously verify the Alpha.10 mutable-route containment, then
publish only an Alpha.11 successor whose exact public bootstrap provisions a
pinned supported Podman and passes a stock-path post-publication rehearsal.
