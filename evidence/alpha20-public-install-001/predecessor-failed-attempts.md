# Predecessor failed attempts retained by the Alpha.20 slice

Retained lineage for `delivery_boundary.failed_attempts`: the same honest record the
Alpha.17 slice carried, kept under the current slice's evidence directory per the
ProjectState v6 gate.

- Alpha.17's three rehearsal failures (updater genesis precondition, grant-digest
  injection path matching, harness provider-status expectation) were each root-caused
  and fixed before its passing end-to-end simulation rehearsal; detail remains at
  `../alpha17-public-install-001/rehearsal-iterations.json`.
- Alpha.16's fresh public install failed its package signature check (predecessor
  signature layout); detail remains at `../alpha16-public-install-001/`.
- The Alpha.20 candidate itself has no recorded failed publication attempt; its native
  install and keep-alive session-close survival legs are measured green in
  `summary.md`, and Windows reboot survival remains unmeasured.
