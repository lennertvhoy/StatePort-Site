# Evidence: alpha15-public-install-001

## Primary journey

Command: `bash <(curl -fsSL https://lennertvhoy.github.io/StatePort-Site/download/install.sh)`

Environment: fresh Windows 11 AMD64 host, WSL2, stock Ubuntu 24.04, normal
sudo-capable user, anonymous public Pages and GHCR, with no checkout, prepared
packages, mirrors, shims, or staged files.

The Site candidate is committed at
`d61e195d937f078f15855be93a7e8c227162e06a`. Guarded publication completed and
anonymous verification confirms the public Pages route serves Alpha.15. The
genuine fresh Windows 11 WSL2 Ubuntu 24.04 journey and human acceptance remain
unrecorded.

- Public publication: passed through the existing guarded Pages push.
- Anonymous protected-byte verification: passed for all 65 Alpha.15 protected
  files; the public installer and release-index hashes match the fixed values.
- Native WSL2 acceptance: pending an approved Windows host; no native result is
  inferred from the local Linux or QEMU environments.

## Secondary checks

- StatePort source: `6f6b6b7b1dd1ef5374883e2229cec351cc8b3cbc`, tree
  `0be1aef3c5cfaa09d92588f6e4ac8b5e869c314a`.
- Public source snapshot: `f4badb23696b74d0569668d5cca5ba16626fa4db`,
  tree `3e1104e1ea7c615d51b8c4742e1005810c72b8ae`; anonymous audit passed.
- Signed index SHA-256:
  `931cc726628c40cf749e99ee14478dba228478884980d63cd3ce0ce96d817097`;
  signed payload `sha256:66483f166570dea5135b732bd3c31a05d52691d48a3e8ddd94ae793d3654a47d`.
- Seven twice-reproducible, scanned, signed images were published to GHCR and
  anonymously verified by both tag and exact digest.
- Bootstrap SHA-256:
  `a045d3d0c6478bae04b20923fe7e98025e46ea4c6b10f69667cc46852cf3a51f`.
- Fresh isolated Ubuntu 24.04 rehearsal passed bootstrap fetch, transport,
  materialization preflight, full install, installed health gates, exact
  runtime-package checks, identical rerun, and the second runtime smoke:
  retained Alpha.15 QEMU rehearsal receipt in the external closure evidence
  directory. This is simulation-only evidence, not native WSL2 acceptance.
- The retained installed guest twice passed web/API/worker health, exact image
  digest checks, browser session establishment, application catalog loading,
  and real StudyState instance creation. The obsolete diagnostic tail failed
  twice because its minimal-container introspection command exits nonzero;
  that approach must not be retried. Partial receipts:
  `surface-smoke-r1.json` and `surface-smoke-r2.json`.
- The production HTTP template lifecycle journey passed locally for the real
  ProjectState and StudyState repositories plus an independent generic
  StateSpec template, including exact-commit import, trusted action, source
  non-mutation, and service-restart continuity.
- Public verification receipts and headers are retained in the external closure
  evidence directory as `public-byte-verification-r1.json`,
  `public-site-verification-r2.json`, and
  `public-mascot-visual-verification-r1.json`.

## Artifacts

- Alpha.15 artifacts: `download/0.1.0-alpha.15/`.
- Exact manifest transport: `download/alpha15-manifests/`.
- Mutable installer bytes equal the tested bootstrap: `download/install.sh`.
- New/updated install, template, platform, lifecycle, limitations, evidence,
  release, technical-files, docs-index, and homepage copy is published as the
  Alpha.15 candidate.
- The v6 gate and validator use the canonical inputs; the v5 files remain inert
  legacy snapshots.
- Shared mascot measurements and isolated responsive screenshots are recorded
  in `mascot-measurements.json` and the closure evidence directory.

## Limitations

- Genuine native Windows 11 WSL2 acceptance and explicit human acceptance are
  not yet recorded. The current agent host cannot run the existing native
  runner because it has no Windows/WSL2 substrate.
