# NEXT_ACTIONS — active execution queue

**Updated At:** 2026-08-03
**Execution Mode:** operating
**Max Items:** 2

## P0 [BL-SITE-ALPHA2-ERRATUM] Keep the known defect visible and fail closed

**Status:** implemented_validation_pending

The download page and release ledger must state that alpha.2 is published but
known defective. `download/install.sh` and
`download/0.1.0-alpha.2/install.sh` must exit before downloads or changes and
point to the erratum. Signed artifacts remain available for inspection.

Run:

```sh
python3 scripts/validate_repo.py
python3 scripts/check_site_quality.py
git diff --check
git status --short --branch
```

**Exit:** the exact site head validates, GitHub Pages deploys it, and the live
bootstrap refusal plus public erratum are remotely verified.

## P0 [BL-SITE-SUCCESSOR-INSTALL] Publish only a freshly proven successor

**Status:** blocked_on_product_candidate

Wait for a corrected successor candidate with a fresh signed index, image set,
SBOMs, scans, provenance, signatures, clean-install receipt, restart/reread
evidence, and owner verdict. Publish it under a new immutable versioned path and
make the unversioned bootstrap point to that version only after remote
verification.

Do not overwrite alpha.2, remove its provenance artifacts, or imply its evidence
applies to changed bytes.

**Exit:** the new versioned bootstrap installs the exact accepted successor and
the public ledger names all remaining limitations.

## Completed since last update

- Published alpha.2’s signed artifacts and original one-command bootstrap.
- After the packaged-image defect was discovered, converted the alpha.2 public
  entrypoint into a fail-closed erratum while retaining immutable artifacts for
  inspection.
- Replaced stale site-agent instructions with a main-only, successor-only
  operating contract.
