# NEXT_ACTIONS - active execution queue

**Updated At:** 2026-08-14
**Execution Mode:** operating
**Max Items:** 1

## P0 [BL-SITE-ALPHA5-CONTAINMENT] Deploy fail-closed Alpha.5 install containment

**Status:** Alpha.5 remains published, signed, byte-intact, and
`compatible_unvalidated`, but installation is disabled after the owner-reported
first exact-host command failed partway through its streamed bootstrap. No
Python installer ran and no receipt exists. Completed reviews bind the failure
to a 4,096-byte truncated pipe-to-shell transfer, not signed release bytes.

**Decision:** deploy fail-closed public guidance and retain the repaired
complete-download, pinned-size, pinned-digest, `/bin/sh -n` transport behind the
disabled state. Do not promote or execute it before the owner's non-executing
exact-WSL2 transport probe passes review.

**Exit:** containment is deployed and remotely verified, all immutable Alpha.5
and retained Alpha.2/3 bytes still match their anchors, and the exact-target
transport probe is the sole pending outcome. Re-enablement, human acceptance,
independent review, stability, and production qualification remain separate.
