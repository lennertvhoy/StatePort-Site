# Evidence: alpha17-public-install-001

## Alpha.17 signed candidate staged — 2026-09-13

StatePort `0.1.0-alpha.17` is the current signed candidate for Windows 11,
WSL2, and Ubuntu 24.04. Its complete installed-product rehearsal passed in an
isolated simulation environment; native Windows 11/WSL2 qualification on the
public route is pending. This is not human acceptance and the release is not
yet qualified.

- Verifier PASS (r5 signed candidate):
  `phase5-review-r3/phase5-verifier-review-r3.json` — releaseId
  `stateport-alpha-0.1.0-alpha.17`, status `signed-private-candidate`,
  independent verifier `deepseek-v4-pro`, all eight checks passed at
  `2026-09-13T16:15:42Z`; signed payload digest
  `sha256:f5bebd221a33e787c1d61ebb59e3fd39c318faca2bafe63a2211c1f76e1168e8`.
- Simulation rehearsal PASSED: `installed-rehearsal-qemu-r4/rehearsal-receipt.json`
  — result `passed`, evidenceClass `simulation_only`, version
  `0.1.0-alpha.17`, release index digest
  `sha256:e2391732872e05402c2ae8bdb018b1b64b284c2490d88197a37cf011b6f8b809`,
  bootstrap digest
  `sha256:2278267220fdb069180723ac2982db7a4f4de3309167ec2fe5e95e6da2741b98`.
- Native qualification: PENDING. The native Windows 11 WSL2 journey on the
  public route cannot run until the Alpha.17 route is published; simulation is
  not native evidence.

Site staging: the `download/0.1.0-alpha.17/` tree, `download/alpha17-manifests/`,
and the mutable `download/install.sh` are byte-identical to the r4 mirror
(48 files, every sha256 verified); `notes/release-notes.md` and
`limitations/known-limitations.md` are staged at the conventional paths. The
site states Alpha.17 as the current signed candidate with pending native
qualification while retaining the published Alpha.16 blocker history.

Limitations: no native receipt, no human acceptance, not yet qualified.
Rollback to Alpha.16 is unsupported by the signed index.
