# Evidence: alpha17-public-install-001

## Alpha.17 signed candidate published — 2026-09-13

StatePort `0.1.0-alpha.17` is the current signed candidate for Windows 11,
WSL2, and Ubuntu 24.04. Its complete installed-product rehearsal passed in an
isolated simulation environment; native Windows 11/WSL2 qualification on the
public route follows this publication and remains pending. This is not human
acceptance and the release is not yet qualified.

## Primary journey

From a genuinely fresh Windows 11 WSL2 Ubuntu 24.04 AMD64 environment, run the
one anonymous public command (`curl -fsSL
https://lennertvhoy.github.io/StatePort-Site/download/install.sh | sh`),
receive the complete product, exercise it, reboot, uninstall, and reinstall.
Status: **native installation qualified on the real public route
(2026-09-14 14:07Z)** — from a retained Windows 11 (build 10.0.26200) VM with
genuine WSL2 (no identity shims, `identityShims: []`), the anonymous public
command installed and ran the complete service stack (web, control API,
worker, execution host with `grantBound: true`), re-ran installation, and
passed both runtime smokes and the provider sandbox executing the real codex
CLI, all against the real public route (anonymous Pages + anonymous GHCR).
Receipt `native-wsl2-qualification-r3/rehearsal-receipt.json` sha256
`ea5b8468452af80cac96f9797123f2e8d112438b5aa8929ea30cfa4250fdf0f3`
(byte-identical guest and host copies), substrate `native-wsl2`, binding
`releaseIndexDigest sha256:e2391732…`. The earlier simulation-class
rehearsal of the
exact published bytes passed end-to-end (install, all services healthy,
execution host bound, provider sandbox executing the real codex CLI with full
boundary evidence, install-rerun, runtime smokes):
`installed-rehearsal-qemu-r4/rehearsal-receipt.json` — result `passed`,
evidenceClass `simulation_only`, version `0.1.0-alpha.17`, release index
digest `sha256:e2391732872e05402c2ae8bdb018b1b64b284c2490d88197a37cf011b6f8b809`,
bootstrap digest
`sha256:2278267220fdb069180723ac2982db7a4f4de3309167ec2fe5e95e6da2741b98`.
Three earlier honest rehearsal failures and their root causes are recorded in
[rehearsal-iterations.json](rehearsal-iterations.json). A simulation is not
native evidence; the native journey receipt will be recorded here when run.

## Secondary checks

- Independent adversarial verifier PASS on the r5 signed candidate:
  `phase5-review-r3/phase5-verifier-review-r3.json` — all eight checks
  (re-derivation, signature, predecessor, images, evidence, bundle,
  semantics, fabrication hunt) passed at `2026-09-13T16:15:42Z`; signed
  payload digest
  `sha256:f5bebd221a33e787c1d61ebb59e3fd39c318faca2bafe63a2211c1f76e1168e8`;
  production trust fingerprint `sha256:df24c1cc…`.
- Published route bytes: the `download/0.1.0-alpha.17/` tree,
  `download/alpha17-manifests/`, and the mutable `download/install.sh` are
  byte-identical to the rehearsal-proven mirror (48 files, every sha256
  verified against the mirror manifest and the signed index);
  `notes/release-notes.md` (`sha256:b49d2edd…`) and
  `limitations/known-limitations.md` (`sha256:32562eaf…`) match the signed
  index pins. The deliberate omission of `quadlet/`, `supply-chain/`, and the
  unsigned candidate index from the site route is recorded in the staging
  commit; nothing the bootstrap fetches is affected.
- All seven release images are anonymously resolvable on
  `ghcr.io/lennertvhoy/stateport-<image>@<digest>` with digest equality
  (`ghcr-publish-r9c-r1/transport-receipt-r1.json`).
- The immutable Alpha.16 and earlier versioned trees are unchanged
  (immutable-set verification exit 0 before every push).

## Artifacts

- Signed index trio staged at product-repo
  `release/alpha17/candidate-r2/` (index
  `sha256:e2391732872e05402c2ae8bdb018b1b64b284c2490d88197a37cf011b6f8b809`,
  payload `sha256:f5bebd221a33e787…`, sigstore `sha256:810a9a5e27e03063…`).
- Public source snapshot:
  `https://github.com/lennertvhoy/StatePort-Source.git` public-main
  `f8cca58a` (tree `8d9fbbd3`, 1414 files, anonymous clone + codeload
  verified).
- Rehearsal evidence root (product machine):
  `/home/ff/.local/state/stateport/stage1-alpha17-production-20260912/`.

## Limitations

- The reboot/uninstall/reinstall lifecycle cycle, three-template journeys,
  installed UI audit rows and whole-stack efficiency measurement remain open.
- Final owner review remains outstanding; no such claim is made.
- Rollback to the Alpha.16 predecessor is unsupported by the signed index
  (no-rollback successor semantics, recorded at signing).
- The installed UI audit rows, three-template journeys, whole-stack
  efficiency measurement, and update/rollback lane remain open in the
  product campaign.
