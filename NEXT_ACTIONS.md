# NEXT_ACTIONS - active execution queue

**Updated At:** 2026-08-14
**Execution Mode:** operating
**Max Items:** 1

## P0 [BL-SITE-ALPHA5-SIGNATURE-MANIFEST] Await non-installing owner probe

**Status:** Mutable publication `562c9cf` is remotely verified through build
`1151713417`, run `31838288831`, and deployment `5913017331`. All seven manifest
blobs and all 33 immutable Alpha.5 files match; no install command is shown.

**Decision:** provide only the pinned `--transport-probe` command and await the
owner result. Keep installation disabled and do not run the installer.

**Exit:** the owner returns the exact probe output. Installation, qualification,
and acceptance remain separate actions.
