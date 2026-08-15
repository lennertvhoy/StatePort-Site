---
repo_role: downstream_project
statedd_mode: operating
repo_mode: operating
statedd_version: statedd-template-v5
initialized_on: 2026-07-21
last_updated: 2026-08-14
---

# StatePort Site — canonical agent operating contract

This repository is the public website and release-distribution surface for
StatePort. `main` is the only canonical branch. Old `agent/*`, `candidate/*`,
and `archive/*` refs are historical transport, not work queues or authority.

## Mandatory entry gate

Choose the applicable mode before review or editing.

### Clean implementation mode

For a new slice with no declared owner-gated WIP:

```sh
cd /home/ff/Documents/Projects/StatePort-Site
git fetch origin --prune
test "$(git branch --show-current)" = "main"
test -z "$(git status --porcelain)"
test "$(git rev-parse HEAD)" = "$(git rev-parse origin/main)"
```

Stop on divergence or unexplained dirty work and preserve it. Do not switch to
an old site branch because its prose looks newer.

### Alpha.5 repaired public-install closure

StatePort directive `OD-2026-08-14-ALPHA5-PUBLIC-CONTAINMENT`, admitted by
StatePort commit `320ecb31`, with the successful owner-reported probe admitted
by `f45d9c80`, authorizes the exact Site commits, push, Pages deployment, and
remote verification needed to contain the promoted Alpha.5 install path and
re-enable only its non-streaming replacement transport after the exact-target
probe. Immutable
release bytes are anchored by Site commit
`eaa1ca6a67844259860917442a95c891d097939f`. The working candidate may be
reviewed, validated, committed, pushed, and deployed under that directive. It
does not authorize re-signing, a successor release, any pipe-to-shell path,
human acceptance, independent review, stability,
production qualification, or changes to retained Alpha.2, Alpha.3, or Alpha.5
bytes.

The Alpha.5 containment content closure is Site commit
`636e795230e286fb39470fe695d935266b4ee876`, remotely verified through Pages
build `1151605137`, run `31832575567`, and deployment `5912021497`. All 33
immutable Alpha.5 files and nine mutable containment surfaces matched local
bytes. That containment deployment held the path closed until the owner-run
non-executing exact-target transport probe.

The owner now reports that exact-target probe downloaded all 8,971 bytes,
matched the pinned SHA-256, and passed target `/bin/sh -n` without executing the
installer. This satisfies the directive condition for re-enabling only the
repaired command. It is not an independently captured raw receipt, clean
install, acceptance, or qualification.

Re-enablement content commit `c8cd20804bc2307c5c49f1fbed75ea8c59f921ae`
deployed through Pages build `1151631061`, exact run `31834012760`, and exact
deployment `5912274973`. All 16 changed mutable files and all 33 immutable
Alpha.5 files matched anonymous live bytes. The legacy build endpoint reported
the prior state SHA, but the run, deployment, and bytes bind the live content to
`c8cd2080`.

The owner subsequently reports that the complete bootstrap executed and refused
the five private image signatures visible in the transcript because exact local
manifest bytes were unavailable. The signed inventory contains seven affected
paths. No install receipt exists; the reported refusal JSON remains only on the
owner host. Installation is disabled again while the signature data path is
repaired. Public pages use minimal neutral copy; incident detail stays here and
in canonical evidence.

Signature-refusal containment commit
`8cae82e5b98b8d4884a18e50660852d2005c4842` deployed through Pages build
`1151656087`, run `31835252274`, and deployment `5912489564`. All 15 changed
mutable files and all 33 immutable Alpha.5 files matched anonymous live bytes.
StatePort commit `df2cbb851f9527550c1c40f28fe1bfd9424b982c` locally repairs
the omission for all seven signed private-manifest paths through the immutable
installer's existing archive seam. No signed bytes change; the repair is not
owner-probed, and public installation remains disabled. The owner now authorizes
publishing only the unversioned mutable repair and entering a non-installing
probe stage. StatePort commit `b75357d12ef5224a866e975bd1f9b2fb3c8ccf21`
adds that exact probe mode before any privileged or installer action.

Mutable publication commit `562c9cfdeff85b3449df37b0011d228ab3857e75`
deployed through Pages build `1151713417`, run `31838288831`, and deployment
`5913017331`. All 16 changed mutable files and all 33 immutable Alpha.5 files
matched anonymous bytes. The repair is published for a non-installing owner
probe only. The owner now reports the exact Windows 11 + WSL2 + Ubuntu 24.04
probe passed all seven manifests without installer execution. The repaired
complete-download command is authorized for re-enablement; no clean-install
receipt or acceptance follows.

## Mandatory read order

1. `AGENTS.md`
2. `STATUS.md`
3. `PROJECT_STATE.yaml`
4. `NEXT_ACTIONS.md`
5. the exact signed release index when touching release claims

Current state overrides old branch prose, PR bodies, screenshots, and handoffs.

## Current release truth

- Current candidate: `v0.1.0-alpha.5`, signed for exact target
  `wsl2-ubuntu2404-linux-amd64-rootless-podman-quadlet`.
- Signed index SHA-256:
  `4613fcad48ea1a2e7dd4350d61baa333efbc734b1fcba1a1c9ca62994d562b71`;
  signed payload:
  `sha256:e45d5c8ce6843bd0c3155ecd26940ff3dc11c5069a2de796a079708066faf98c`.
- Installation is enabled only through the repaired mutable complete-download,
  pinned-size/digest, and shell-syntax-checked command. WSL2 remains
  `compatible_unvalidated`; no clean-install receipt exists.
- Completed reviews bind the failure to a 4,096-byte truncated pipe-to-shell
  transfer. The complete 8,971-byte bootstrap and signed release payload remain
  intact; the replacement completes download, verifies pinned size and digest,
  passes `/bin/sh -n`, and executes only after every check succeeds.
- WSL1, native Linux, other distributions, ARM64, macOS, and Docker Desktop do
  not inherit this release target or its evidence.
- Canonical development Git remains private. The signed public snapshot
  `6911b7c1e73e0408af4a2a900aec585d15168a28` / tree
  `05ca882f4e41b98f4ffa6f9257e068d72472e765` is anonymously resolvable from
  `lennertvhoy/StatePort-Source`; the curated source archive is public and
  digest-bound.
- Alpha.3 remains signed, byte-intact, install-disabled, and governed by its
  historical erratum. Alpha.2 remains superseded and install-disabled. Their
  versioned trees are immutable.
- Human acceptance, independent security review, stability, clean-install
  qualification, and production qualification remain absent.
- Pages deploys from `main` through GitHub's managed legacy Pages build. The
  custom workflow is manual-only. Nothing is live until remotely verified.

Never call Alpha.5 clean-installed, qualified, owner-accepted, stable, audited,
or production-ready. Never alter Alpha.2, Alpha.3, or anchored Alpha.5 bytes.

## Repository rules

- Work only from current `main` unless the owner explicitly authorizes a
  temporary branch. Default branch and worktree budgets are zero.
- Integrate finished work promptly. Do not create handoff, candidate-number,
  preservation, or generated-media branches.
- Signed/versioned artifacts under `download/0.1.0-alpha.2/`,
  `download/0.1.0-alpha.3/`, and `download/0.1.0-alpha.5/` are immutable.
  External errata and a fail-closed bootstrap may prevent use without changing
  the signed candidate.
- `release-index.json` remains authority for version, digests, image references,
  and trust identity. Current site state and errata provide defect and
  acceptance status that the original index could not predict.
- Keep published, verified, installable, clean-installed, human-accepted,
  independently reviewed, production-qualified, and stable separate.
- No secrets, analytics, tracking, third-party runtime scripts, or mutable
  artifact references.
- Keep the site usable without JavaScript and preserve accessibility, CSP,
  contrast, local-reference, and reduced-motion guarantees.
- Run `python3 scripts/validate_repo.py` and
  `python3 scripts/check_site_quality.py` before claiming validation.
- Update `STATUS.md`, `PROJECT_STATE.yaml`, and `NEXT_ACTIONS.md` whenever
  release truth changes.

## Active scope

1. Preserve Alpha.2 and Alpha.3 exactly and keep the Alpha.3 erratum historical.
2. Preserve the anchored Alpha.5 tree and exact repaired mutable bootstrap.
3. Publish only the repaired complete-download command and classify any run on
   the mutated Lionheart distro as diagnostic rather than clean-install evidence.

Everything else is backlog or history.
