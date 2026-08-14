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

### Alpha.5 public-install containment closure

StatePort directive `OD-2026-08-14-ALPHA5-PUBLIC-CONTAINMENT`, admitted by
StatePort commit `320ecb31`, authorizes the exact Site commits, push, Pages
deployment, and remote verification needed to disable the promoted Alpha.5
install path and prepare its non-streaming replacement transport. Immutable
release bytes are anchored by Site commit
`eaa1ca6a67844259860917442a95c891d097939f`. The working candidate may be
reviewed, validated, committed, pushed, and deployed under that directive. It
does not authorize re-signing, a successor release, install re-enablement before
the exact-target probe, human acceptance, independent review, stability,
production qualification, or changes to retained Alpha.2, Alpha.3, or Alpha.5
bytes.

The Alpha.5 containment content closure is Site commit
`636e795230e286fb39470fe695d935266b4ee876`, remotely verified through Pages
build `1151605137`, run `31832575567`, and deployment `5912021497`. All 33
immutable Alpha.5 files and nine mutable containment surfaces matched local
bytes. Installation remains disabled; the sole remaining outcome is the
owner-run non-executing exact-target transport probe.

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
- Installation is temporarily disabled after the owner-reported first exact-host
  attempt failed partway through the streamed bootstrap. WSL2 remains
  `compatible_unvalidated`; no clean-install receipt exists.
- Completed reviews bind the failure to a 4,096-byte truncated pipe-to-shell
  transfer. The complete 8,971-byte bootstrap and signed release payload remain
  intact; the replacement must complete download, verify pinned size and digest,
  pass `/bin/sh -n`, and remain held back pending the exact-target probe.
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
2. Preserve the anchored Alpha.5 tree and byte-identical mutable bootstrap while
   mutable guidance remains fail-closed.
3. Deploy and remotely verify containment, then await the owner's non-executing
   Windows 11 + WSL2 + Ubuntu 24.04 transport probe before any re-enablement.

Everything else is backlog or history.
