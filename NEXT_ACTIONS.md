# NEXT_ACTIONS - active execution queue

**Updated At:** 2026-08-15
**Execution Mode:** operating
**Max Items:** 1

## P0 [BL-SITE-ALPHA5-MATERIALIZATION] Deterministic bootstrap live; owner resets and reruns

**Status:** Owner directive `OD-2026-08-15-ALPHA5-RERUN-CONFLICT-FIX` supersedes
the install-wait sequencing. The owner rerun refused with
`image_archive_conflict` because runtime archive creation embedded fresh
mtimes; StatePort `dd61a7e6` makes it deterministic. The repinned 17,620-byte
bootstrap (SHA-256
`cf8b20d09bc0865e222281cb09a4cece675eff979a84b6cb2e71ba53338a6300`) deployed
in content `e72c8cf` through Pages build `1152792921`, run `31879838808`, and
deployment `5919578251`; all 3 changed paths and all 33 immutable files matched
anonymous live bytes.

**Decision:** the owner clears retained state on the exact target
(`rm -rf ~/.local/state/stateport-install`), then runs the pinned preflight,
then the pinned install command, on Windows 11 + WSL2 + Ubuntu 24.04.

**Exit:** the owner supplies the install result. Clean-install qualification
and acceptance remain separate owner actions.

## Completed since last update

- Deterministic-bootstrap content `e72c8cf5c2b6845d6c2459c69e3777079a90202e`
  deployed through Pages build `1152792921`, run `31879838808`, and deployment
  `5919578251`; all 3 changed paths and all 33 immutable files matched
  anonymous live bytes.
- Install re-enable content `2061319d50cf1a7b59bca4a0ee5906688aed1170` deployed
  through Pages build `1152707301`, run `31877244223`, and deployment
  `5919159551`; all 20 changed paths and all 33 immutable files matched
  anonymous live bytes.
- Public copy correction head `d334f739` deployed through run `31874362376` and
  deployment `5918682005`. All 28 changed HTML pages and four linked
  Markdown/metadata files matched anonymous live bytes. Versioned release files
  remained unchanged.
