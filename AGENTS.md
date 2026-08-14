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

### Alpha.5 publication closure

StatePort directive `OD-2026-08-14-WSL2-ALPHA5-PRIORITY-RESET` authorizes the
exact Alpha.5 signing, publication, Site deployment, and remote verification
needed for the owner's first WSL2 test. Immutable release bytes are anchored by
Site commit `eaa1ca6a67844259860917442a95c891d097939f`. The working candidate may
be reviewed, validated, committed, pushed, and deployed under that directive.
It does not grant human acceptance, independent review, stability, production
qualification, unsupported-platform claims, or changes to retained Alpha.2 or
Alpha.3 bytes.

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
- Installation is enabled only as an explicitly unqualified public test.
  WSL2 reports `compatible_unvalidated` until a real Windows 11 + WSL2 +
  Ubuntu 24.04 clean-install receipt exists.
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
2. Publish the anchored Alpha.5 tree, byte-identical mutable bootstrap, complete
   WSL2 setup instructions, and exact unqualified claim boundary.
3. Validate, push, observe the managed Pages deployment, and remotely digest-
   check every Alpha.5 file before reporting publication.

Everything else is backlog or history.
