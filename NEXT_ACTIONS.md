# NEXT_ACTIONS — active execution queue

**Updated At:** 2026-08-03
**Execution Mode:** operating
**Max Items:** 2

## P0 [BL-ALPHA2-CLEAN-INSTALL] Verify the public one-command install

**Status:** pending_external

Run exactly:

```sh
curl -fsSL https://lennertvhoy.github.io/StatePort-Site/download/0.1.0-alpha.2/install.sh | sh
```

on a fresh Ubuntu 24.04 AMD64 host. Preserve the exact installer receipt,
runtime URL, host facts, and first owner verdict. A refusal is evidence and
must be fixed in a new candidate; do not edit signed alpha.2 bytes.

**Exit:** downloaded public bootstrap and signed alpha.2 artifacts install from
zero StatePort state, all services report healthy exact runtime identity, the
receipt survives reread/restart, and the owner records accepted or rejected.

## P1 [BL-LINUX-CAPABILITY-TARGET] Replace distro-name gating in a later release

**Status:** designed_not_implemented

The next candidate should target capabilities rather than the literal Ubuntu
name: Linux AMD64, cgroup v2, systemd user services, rootless Podman with
Quadlet, subordinate UID/GID mappings, Python bootstrap support, and required
filesystem/socket semantics. Validate at least Ubuntu, Debian, Fedora, and one
rolling distribution before calling the matrix supported. Keep Ubuntu 24.04 as
the alpha.2 validated baseline; never bypass that signed contract in place.

**Exit:** a new signed target and installer pass the clean-install matrix, with
per-distribution prerequisites and typed capability refusals.

## Completed since last update

- Published `v0.1.0-alpha.2`, its signed index, digest-pinned GHCR references,
  versioned artifacts, checksums, release key, signatures, limitations, and
  source/export evidence.
- Published versioned and convenience `install.sh` bootstraps, reducing the
  public entry path to one copy-paste command while retaining checksum,
  signature, key, exact-image, confirmation, and receipt boundaries.
- Retired all old site branch narratives from current authority; `main` and the
  signed index are the only current sources of truth.
