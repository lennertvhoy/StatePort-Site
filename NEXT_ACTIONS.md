# NEXT_ACTIONS - active execution queue

**Updated At:** 2026-08-14
**Execution Mode:** operating
**Max Items:** 1

## P0 [BL-SITE-ALPHA5-PUBLICATION] Publish and verify Alpha.5 for owner testing

**Status:** The corrected 33-file Alpha.5 release tree is committed and frozen
at `eaa1ca6a67844259860917442a95c891d097939f`. Its mutable bootstrap and public
instructions pass independent immutable-tree, release-identity,
source-disclosure, unqualified-claim, quality, shell, and unit-test checks.
Alpha.2 and Alpha.3 remain unchanged.

**Decision:** Validate the exact Site candidate, commit and push the authorized
closure to `main`, observe the managed legacy Pages deployment, and remotely
digest-check every Alpha.5 file plus the mutable bootstrap. The owner performs
the first Windows 11 + WSL2 + Ubuntu 24.04 run afterwards.

**Exit:** Alpha.5 and complete setup instructions are public and exact remote
bytes match the anchored manifest. The site labels WSL2
`compatible_unvalidated` and the real-host clean-install receipt as pending.
Human acceptance, independent review, stability, and production qualification
remain separate.
