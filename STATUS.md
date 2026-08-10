# StatePort Site status

**Updated At:** 2026-08-10
**Execution Mode:** operating
**Project State:** alpha3_published_install_disabled_containment_deployed_site_candidate_remotely_verified
**Canonical:** `main`; exact head derives from Git
**Hosting:** https://lennertvhoy.github.io/StatePort-Site/

## Current truth

- `v0.1.0-alpha.3` is published as a signed alpha candidate for the portable
  `linux-amd64-rootless-podman-quadlet` target. Its signed bytes are intact
  and unchanged.
- The signed release index raw SHA-256 is
  `d02709a250369b96c7bf5c39659d9080ff53d0cf0e20d391222fe5c1b0d4ae93` and its
  signed payload digest is
  `sha256:2639e29d6ca0a5bd83d07013edb49f22692efaf53a6049234fe6b70810c89166`.
- Alpha.3 is install-disabled: all seven signed image scans and databases
  exceed their 24-hour maximum age, so current-time verification refuses, and
  the committed installer/runtime defects (execution host not provisioned or
  protocol-health-checked; synthetic goal execution) require a successor
  release. Historical local Ubuntu/Fedora receipts are not current install
  proof. Owner acceptance, independent security review, and production
  qualification do not exist.
- The mutable-surface containment is **deployed and publicly verified**. The
  home page, download page, release
  ledger, and limitations page no longer promote the one-command install;
  they plainly state installation is currently disabled and link the new
  plain-language erratum at `download/erratum-alpha3.html`. The mutable
  convenience bootstrap `download/install.sh` is now a fail-closed stub
  (executes nothing, exits 2, points to the erratum); the immutable versioned
  bootstraps keep their original signed bytes. The erratum's source section
  distinguishes the canonical private source identity
  (`fa4ea4b7f08e78669e194c204b59206ab109a02f` /
  `aec60303045e7a9c8255b941c761d904af85ec10`) from the signed public snapshot
  identity (`43d6b4491b962c963a0ecafc060e0dfc7e334dc0` /
  `3bbe46db14a7c929e6f0a17ca153ec686192aa51`, not remotely resolvable), and
  stale "private alpha"/"no download" copy is corrected. All pages share one
  refreshed `site.css` cache key.
- Pages deployed containment content commit
  `c1384061a093f8f4fc7e68f8ca7126558e1e97a5` through successful legacy build
  `1141200639`, run `31315882234`, and deployment `5819133762`. Public checks
  observed the disabled state on home/download/releases, the erratum, no mobile
  horizontal overflow at 390px, and zero console errors. The custom deploy
  workflow remains manual-only and is not the live provider.
- Both immutable release trees are unchanged and now pinned by exact
  path-and-SHA-256 manifest `config/immutable-release-trees.json`
  (alpha.2: 17 files, alpha.3: 31 files), **anchored to the verified
  publication commits** (`4043534a` alpha.2, `52b42dd4` alpha.3):
  `scripts/build_immutable_manifest.py` refuses to regenerate from bytes
  that differ from the anchors, and `scripts/validate_repo.py` independently
  re-checks the manifest against them. The validator rejects additions,
  deletions, and byte changes, promotes-while-disabled copy,
  installable-while-defective copy, stale Pages provider claims, mixed
  alpha.2/alpha.3 identities, and diverging stylesheet cache keys;
  `scripts/check_site_quality.py` extends the same honesty rules to page
  metadata.
- Public verification fetched all 48 immutable release files and found zero
  byte-count or SHA-256 mismatches. The live mutable bootstrap is byte-identical
  to the reviewed file at SHA-256
  `6f69d31ae819539138dcfaaa83aeec2a3635f5b610ba37a2b78bb4c192d34e02`;
  it names the erratum, contains no download/runtime command, and exits 2.
- The curated alpha.3 source archive is digest-valid and AGPL-classified;
  the canonical development repository remains private, and alpha.3's signed
  public Git snapshot identity is not remotely resolvable.
- `v0.1.0-alpha.2` remains immutable, superseded, known defective, and
  install-disabled for inspection. Its files were not rewritten.
- The unified UX/media product commit is
  `d56d67bf48f2edbde03ec2fd050e9ea794211eaa`. It is deployed as Site commit
  `b9d2edf0692c0c8672de8984d511a17c3303e02b`, remotely verified through Pages
  run `31392022484` and deployment `5832690455`. This does not change alpha.3
  release truth: it remains install-disabled, immutable, unaccepted, and not
  independently reviewed, stable, or production-qualified.

## Exact next action

Keep the deployed containment in place until a corrected successor is built,
freshly evidenced, signed, and separately authorized for publication. Do not
restore an install command or change immutable alpha.2/alpha.3 bytes. Successor
signing, human acceptance, independent review, and production qualification
remain separate and ungranted.
