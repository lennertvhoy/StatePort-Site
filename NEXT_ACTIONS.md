# NEXT_ACTIONS - active execution queue

**Updated At:** 2026-08-14
**Execution Mode:** operating
**Max Items:** 1

## P0 [BL-SITE-ALPHA5-FRESH-CLEAN-INSTALL] Capture a fresh clean-install receipt

**Status:** Repaired install content `c8cd2080` is live through Pages build
`1151631061`, exact run `31834012760`, and deployment `5912274973`. All 16
changed mutable files and all 33 immutable Alpha.5 files matched anonymous live
bytes. Installation is enabled only through the repaired command.

**Decision:** perform one genuinely fresh Windows 11 + WSL2 + Ubuntu 24.04 AMD64
clean install using the repaired command. Retain the install and execution-host
receipts. Do not use the mutated prior distro.

**Exit:** exact host identity, successful install receipt, execution-host
receipt, and observed limits pass review. Until then support remains
`compatible_unvalidated`, unaccepted, and not production-qualified.
