# StatePort Site status

**Updated At:** 2026-08-31
**Execution Mode:** operating
**Project State:** alpha10_contained_alpha11_engineering_active
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
- Containment commit `27bcf6c` deployed through Pages build `1186377823`, run
  `33431377948`, and deployment `6188165170`. Anonymous checks matched all 20
  containment paths, all 39 Alpha.10 release and manifest files, and all 113
  publication-anchored immutable files across 140 unique live paths.
- The mutable Alpha.10 installer route is fail-closed. Versioned Alpha.10 files
  and signatures remain unchanged for inspection.
- Alpha.10 has no authenticated predecessor under its current trust root;
  rollback is unsupported. Alpha.7 remains retained but is superseded and its
  installer route is fail-closed.
- Canonical source commit `930c2d9a` / tree `726d1dcb` remains private. Public
  snapshot `457423be` / tree `7eff2b9b` is anonymously resolvable from
  `lennertvhoy/StatePort-Source`.
- Alpha.10 is owner-rejected, not clean-installed or accepted. Independent
  security review, stability, and production qualification remain absent.

## Exact next action

Implement the smallest secure Alpha.11 Podman provisioning correction, remove
material rehearsal-only runtime preparation, and prove the prospective exact
public bootstrap from a stock Ubuntu 24.04 guest before publication.
