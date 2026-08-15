# NEXT_ACTIONS - active execution queue

**Updated At:** 2026-08-14
**Execution Mode:** operating
**Max Items:** 1

## P0 [BL-SITE-ALPHA5-SIGNATURE-MANIFEST] Re-enable repaired safe command

**Status:** The owner reports the exact-target seven-manifest probe passed without
installer execution. The repaired mutable command is published once on the
download page; deployment verification is pending.

**Decision:** deploy only the complete-download, 13,702-byte, pinned-SHA-256,
`/bin/sh -n` command. Never restore pipe-to-shell.

**Exit:** changed mutable surfaces and all immutable files match remotely. A
fresh distro remains required for clean-install evidence.
