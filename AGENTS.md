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

- Public candidate: `v0.1.0-alpha.3`.
- Signed payload:
  `sha256:2639e29d6ca0a5bd83d07013edb49f22692efaf53a6049234fe6b70810c89166`.
- Alpha.3 is **published but not owner-accepted**. Its capability-gated
  installer and signed artifacts are public; clean-install evidence exists for
  Ubuntu 24.04 (`validated_baseline`) and Fedora 44 (`compatible_unvalidated`).
- The portable target is `linux-amd64-rootless-podman-quadlet`; distribution
  branding is observation, not eligibility. Debian and rolling distributions
  are not claimed.
- The public one-command bootstrap is published. Public-URL clean-install
  proof on the receipted Ubuntu VM remains a separate verification step.
- Alpha.2 is **known defective, superseded, and unaccepted**. Its packaged web
  image omitted the updater and preview-gateway source trees required by the
  AppServer. Its signed bytes remain immutable and its bootstrap remains
  fail-closed.
- Independent security review and production qualification remain absent.

Never call alpha.3 accepted, stable, audited, or production-ready. Never
silently replace alpha.2 signed bytes or transfer its supply-chain evidence to
alpha.3.

## Repository rules

- Work only from current `main` unless the owner explicitly authorizes a
  temporary branch. Default branch and worktree budgets are zero.
- Integrate finished work promptly. Do not create handoff, candidate-number,
  preservation, or generated-media branches.
- Signed/versioned artifacts under `download/0.1.0-alpha.2/` and
  `download/0.1.0-alpha.3/` are immutable.
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

1. Preserve alpha.2's fail-closed erratum and alpha.3's exact signed artifacts.
2. Complete the public-URL clean-install proof and record it as published
   evidence; human acceptance remains a separate owner decision.

Everything else is backlog or history.
