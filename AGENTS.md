---
repo_role: downstream_project
statedd_mode: operating
repo_mode: operating
statedd_version: statedd-template-v5
initialized_on: 2026-07-21
last_updated: 2026-08-15
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
cd /home/ff/Projects/StatePort-Site
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

Re-enablement content `d5491f32cabda022630b0292e4db440d64760c7d`
deployed through Pages build `1152517815`, run `31871418918`, and deployment
`5918210420`. All 15 changed paths and all 33 immutable Alpha.5 files matched
anonymous live bytes. The repaired command is public; a Lionheart run remains
diagnostic only and cannot supply fresh-distro evidence.

The continued Lionheart diagnostic run encountered an HTTP 503, later prepared
the signed execution-host plan, and then failed because
`/usr/local/libexec/stateport-execution-host-provision` had no parent directory.
No install or execution-host receipt exists. Public installation is disabled
while both premises are isolated and a non-installing preflight is prepared.

StatePort `c441ca7a` makes static downloads explicitly bounded, atomic, and
labeled; creates and verifies the root-owned helper parent before installation;
and adds a non-installing fake-root materialization preflight. Only its mutable
17,561-byte render may be published. Installation remains disabled pending the
exact-target preflight result.

Mutable preflight publication `c561db2afd156eb09e61ce4e2da3158ea596a587`
deployed through Pages build `1152559503`, run `31872664883`, and deployment
`5918407409`. All ten changed paths and all 33 immutable Alpha.5 files matched
anonymous bytes.

Owner directive `OD-2026-08-15-ALPHA5-INSTALL-REENABLE` supersedes the
preflight-wait sequencing and authorizes restoring the public install command.
Anonymous byte-verification confirmed the live mutable bootstrap carries the
`c441ca7a` repair and that all 33 immutable Alpha.5 files are intact before
re-enablement. The download page shows the pinned non-installing preflight as
the recommended first step, then the exact pinned install command. The owner
install result is pending.

The owner rerun refused with `image_archive_conflict`: runtime OCI archive
creation embedded fresh mtimes, so retained bytes differed on every rerun.
StatePort `dd61a7e6` makes archive creation deterministic under owner
directive `OD-2026-08-15-ALPHA5-RERUN-CONFLICT-FIX`. Content
`e72c8cf5c2b6845d6c2459c69e3777079a90202e` deployed through Pages build
`1152792921`, run `31879838808`, and deployment `5919578251`; all 3 changed
mutable paths and all 33 immutable Alpha.5 files matched anonymous live bytes.
The mutable bootstrap is now 17,620 bytes at SHA-256
`cf8b20d09bc0865e222281cb09a4cece675eff979a84b6cb2e71ba53338a6300`, and the
pinned preflight and install commands were repinned. The owner clears retained
state (`rm -rf ~/.local/state/stateport-install`), then reruns the pinned
preflight and install command; the result is pending.

## Mandatory read order

1. `AGENTS.md`
2. `STATUS.md`
3. `PROJECT_STATE.yaml`
4. `NEXT_ACTIONS.md`
5. the exact signed release index when touching release claims

Current state overrides old branch prose, PR bodies, screenshots, and handoffs.

## Current release truth

- Current candidate: `v0.1.0-alpha.7`, signed for exact target
  `wsl2-ubuntu2404-linux-amd64-rootless-podman-quadlet`.
- Signed index SHA-256:
  `d60a1c1060ae84aab91bc92ab497c9bca9c5e82dc6267688398e1a2b18b9bcd9`;
  signed payload:
  `sha256:15171f61eecb5138c1cd35cab5fb0f496d4d4bf954468c95957c68abcedb3cda`.
- Alpha.7 has passed the governed clean Ubuntu rehearsal, including install and
  identical rerun plus extended R1-R6. It is available for a first owner test;
  WSL2 remains `compatible_unvalidated` and no clean-install acceptance receipt
  exists.
- Published Alpha.6 is superseded and its installer route is fail-closed because
  the candidate carries the updater venv cache-drift defect. Its signed index and
  artifacts remain retained.
  WSL2 remains `compatible_unvalidated`; no clean-install receipt exists.
- Completed reviews bind the failure to a 4,096-byte truncated pipe-to-shell
  transfer. The complete 8,971-byte bootstrap and signed release payload remain
  intact; the replacement completes download, verifies pinned size and digest,
  passes `/bin/sh -n`, and executes only after every check succeeds.
- WSL1, native Linux, other distributions, ARM64, macOS, and Docker Desktop do
  not inherit this release target or its evidence.
- Canonical development Git remains private. The signed public snapshot
  `60cef2f9727d7a34485398eedb5d522f11b212ae` / tree
  `20784f5977cb2222ff72b2fbd755c59acafbc60c` is anonymously resolvable from
  `lennertvhoy/StatePort-Source`; the curated source archive is public and
  digest-bound.
- Alpha.3 remains signed, byte-intact, install-disabled, and governed by its
  historical erratum. Alpha.2 remains superseded and install-disabled. Their
  versioned trees are immutable.
- Human acceptance, independent security review, stability, clean-install
  qualification, and production qualification remain absent.
- Pages deploys from `main` through GitHub's managed legacy Pages build. The
  custom workflow is manual-only. Nothing is live until remotely verified.

Never call Alpha.7 clean-installed, qualified, owner-accepted, stable, audited,
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
3. Present the pinned Alpha.7 non-installing preflight as the recommended first
   step and the exact pinned install command as the primary download action;
   owner clean-install and acceptance remain pending.

Everything else is backlog or history.
