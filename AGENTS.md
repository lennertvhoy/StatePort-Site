---
repo_role: downstream_project
statedd_mode: operating
repo_mode: operating
statedd_version: statedd-template-v5
initialized_on: 2026-07-21
last_updated: 2026-08-03
---

# StatePort Site — canonical agent operating contract

This repository is the public website and release-distribution surface for
StatePort. `main` is the only canonical branch. Old `agent/*`, `candidate/*`,
and `archive/*` refs are historical transport, not work queues or authority.

## Mandatory entry gate

Before editing:

```sh
cd /home/ff/Documents/Projects/StatePort-Site
git fetch origin --prune
test "$(git branch --show-current)" = "main"
test -z "$(git status --porcelain)"
test "$(git rev-parse HEAD)" = "$(git rev-parse origin/main)"
```

Stop on divergence or dirty work and preserve it. Do not switch to an old site
branch because its prose looks newer.

## Mandatory read order

1. `AGENTS.md`
2. `STATUS.md`
3. `PROJECT_STATE.yaml`
4. `NEXT_ACTIONS.md`
5. the exact signed release index when touching release claims

Current state overrides old branch prose, PR bodies, screenshots, and handoffs.

## Current release truth

- Public candidate: `v0.1.0-alpha.2`.
- Signed payload:
  `sha256:692f63cdbdfe531aa4d6379d12ad6e98cd408d7343392bf94f5c01abc46af9aa`.
- The signed index and immutable artifacts remain publicly inspectable.
- Alpha.2 is **known defective and unaccepted**. Its packaged web image omitted
  the updater and preview-gateway source trees required by the AppServer.
- No successful install receipt exists. The public bootstrap must refuse rather
  than start an installation.
- A source fix exists in the implementation repository, but no corrected image,
  signature, release index, successor download, clean-install receipt, or owner
  acceptance has been published.
- The signed alpha.2 target remains Ubuntu 24.04 AMD64. Fedora 44 was an
  unsupported-host diagnostic investigation, not a support or acceptance claim.

Never call alpha.2 usable, repaired, installable, accepted, stable, audited, or
production-ready. Never silently replace its signed bytes or transfer its
supply-chain evidence to a successor.

## Repository rules

- Work only from current `main` unless the owner explicitly authorizes a
  temporary branch. Default branch and worktree budgets are zero.
- Integrate finished work promptly. Do not create handoff, candidate-number,
  preservation, or generated-media branches.
- Signed/versioned artifacts under `download/0.1.0-alpha.2/` are immutable.
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

1. Keep the public alpha.2 entrypoint fail-closed and the known defect visible.
2. Publish a new one-command path only after a corrected successor has a fresh
   signed index, clean-install receipt, restart/reread evidence, and owner
   verdict.

Everything else is backlog or history.
