# NEXT_ACTIONS - active execution queue

**Updated At:** 2026-08-14
**Execution Mode:** operating
**Max Items:** 1

## P0 [BL-SITE-ALPHA5-MATERIALIZATION] Repair and publish safe preflight

**Status:** The Lionheart diagnostic failed before root-helper materialization
because `/usr/local/libexec` was absent. Public installation is disabled.

**Decision:** isolate the HTTP 503 semantics and missing-parent assumption, then
publish only a non-installing exact-target materialization preflight.

**Exit:** the exact preflight passes on the owner host. Installation and fresh
clean-install evidence remain separate actions.
