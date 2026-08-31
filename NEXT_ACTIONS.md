# NEXT_ACTIONS - active execution queue

**Updated At:** 2026-08-31
**Execution Mode:** operating
**Max Items:** 1

## P0 [BL-ALPHA11-PODMAN-CLEAN-INSTALL] Contain Alpha.10 and publish a faithful Alpha.11

**Status:** Alpha.10 is owner-rejected. Stock Ubuntu 24.04 supplied Podman 4.9.3
below StatePort's floor, while the rehearsal had prepared Podman 5.4.2 first.

**Decision:** fail-close only the mutable Alpha.10 route, preserve its immutable
files, and publish Alpha.11 only after faithful stock-path proof.

**Exit:** Alpha.11 public bootstrap securely provisions supported Podman and the
exact live command passes the stock post-publication rehearsal without hidden
runtime preparation. Human acceptance remains separate.
