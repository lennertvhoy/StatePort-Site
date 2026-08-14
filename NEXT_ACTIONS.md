# NEXT_ACTIONS - active execution queue

**Updated At:** 2026-08-14
**Execution Mode:** operating
**Max Items:** 1

## P0 [BL-SITE-ALPHA5-OWNER-TEST] Capture the first real-host Alpha.5 receipt

**Status:** Alpha.5 content commit `6cf95ca855e94f7648afb93fa870390a8c8bc8a7`
is deployed through Pages build `1151371842`, run `31820163492`, and deployment
`5909824336`. All 33 immutable Alpha.5 files, the mutable bootstrap, and six
current HTML surfaces match local bytes remotely. Alpha.2 and Alpha.3 remain
unchanged.

**Decision:** The owner performs the first test from the published install guide
on a fresh Windows 11 + WSL2 + Ubuntu 24.04 AMD64 host. Do not connect to
`lionheart` or `sharestation`; `ff-win` no longer exists. Preserve the install
and execution-host receipts without relabelling a failed or partial run.

**Exit:** The exact Alpha.5 source, host identity, install receipt, execution-host
receipt, checks, and observed limits are reviewed. Only a passing exact-host run
may change `compatible_unvalidated`; human acceptance, independent review,
stability, and production qualification remain separate decisions.
