# NEXT_ACTIONS - active execution queue

**Updated At:** 2026-08-14
**Execution Mode:** operating
**Max Items:** 1

## P0 [BL-SITE-ALPHA5-SAFE-REENABLE] Deploy the repaired install command

**Status:** The owner reports the exact-target non-executing probe downloaded all
8,971 bytes, matched the pinned SHA-256, and passed `/bin/sh -n` without running
the installer. This satisfies the directive's re-enablement condition but is not
a clean install or independently captured raw receipt.

**Decision:** deploy and remotely verify only the repaired complete-download,
pinned-size, pinned-digest, syntax-checked install command. Preserve the failed
partial first attempt and keep support `compatible_unvalidated`.

**Exit:** the repaired command is live and all immutable release bytes remain
unchanged. The next action is a genuinely fresh exact-target clean install with
receipts retained; never reuse the mutated prior distro as evidence.
