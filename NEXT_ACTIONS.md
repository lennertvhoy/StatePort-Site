# NEXT_ACTIONS - active execution queue

**Updated At:** 2026-08-14
**Execution Mode:** operating
**Max Items:** 1

## P0 [BL-SITE-ALPHA5-MATERIALIZATION] Repair and publish safe preflight

**Status:** StatePort `c441ca7a` repairs bounded downloads and helper-parent
creation. Its 17,561-byte mutable render is staged; installation is disabled.

**Decision:** publish only that mutable bootstrap, verify exact live bytes, and
provide its non-installing exact-target materialization preflight.

**Exit:** the exact preflight passes on the owner host. Installation and fresh
clean-install evidence remain separate actions.
