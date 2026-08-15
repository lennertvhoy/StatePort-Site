# NEXT_ACTIONS - active execution queue

**Updated At:** 2026-08-15
**Execution Mode:** operating
**Max Items:** 1

## P0 [BL-SITE-ALPHA5-MATERIALIZATION] Install re-enabled; await owner result

**Status:** Owner directive `OD-2026-08-15-ALPHA5-INSTALL-REENABLE` supersedes
the preflight-wait sequencing. The live mutable bootstrap was anonymously
byte-verified to carry the `c441ca7a` repair before re-enablement; all 33
immutable Alpha.5 files matched. The install command is restored with the
pinned preflight shown as the recommended first step.

**Decision:** the owner runs the preflight, then the install, on Windows 11 +
WSL2 + Ubuntu 24.04.

**Exit:** the owner supplies the install result. Clean-install qualification
and acceptance remain separate owner actions.

## Completed since last update

- Install re-enable content committed under
  `OD-2026-08-15-ALPHA5-INSTALL-REENABLE`; deployment and remote verification
  pending at content-commit time.
- Public copy correction head `d334f739` deployed through run `31874362376` and
  deployment `5918682005`. All 28 changed HTML pages and four linked
  Markdown/metadata files matched anonymous live bytes. Versioned release files
  remained unchanged.
