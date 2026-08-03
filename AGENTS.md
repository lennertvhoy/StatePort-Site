---
repo_role: downstream_project
statedd_mode: operating
repo_mode: operating
statedd_version: statedd-template-v5
initialized_on: 2026-07-21
last_updated: 2026-08-03
---

# StatePort Site — agent operating contract

This repository is the public website and release-distribution surface for
StatePort. **`main` is the only canonical branch.** Old `agent/*`, `candidate/*`,
and `archive/*` refs are historical transport, not work queues or authority.
Do not resume them, merge them, or infer current product state from them.

## Mandatory read order

1. `AGENTS.md`
2. `STATUS.md`
3. `PROJECT_STATE.yaml`
4. `NEXT_ACTIONS.md`
5. the exact signed release index when touching release claims

## Current release truth

- Public candidate: `v0.1.0-alpha.2`.
- Download page: `https://lennertvhoy.github.io/StatePort-Site/download/`.
- One-command bootstrap: `https://lennertvhoy.github.io/StatePort-Site/download/install.sh`.
- Signed index: `download/0.1.0-alpha.2/release-index.json`.
- The candidate is published and downloadable, but **clean-install human
  acceptance, independent security review, and production qualification are
  not claimed**.
- The signed alpha.2 target is Ubuntu 24.04 AMD64. Other Linux distributions
  must not be claimed as supported until a new capability-based signed target
  and clean-install matrix exist. Do not modify alpha.2 artifacts in place.

## Repository rules

- Work from current `main`; fetch and compare local `main` with `origin/main`
  before editing. Stop on divergence or unrelated dirty work.
- Default branch/worktree budget is zero additional branches and zero additional
  worktrees. Use a temporary branch only when the owner explicitly asks, and
  delete it immediately after integration.
- Integrate finished work promptly. Do not accumulate handoff branches, draft
  PRs, duplicated candidates, or generated media variants.
- Signed/versioned artifacts under `download/0.1.0-alpha.2/` are immutable.
  Corrections require a new version, except clearly external errata that do not
  alter signed bytes.
- `release-index.json` is the authority for version, digests, image references,
  trust identity, and limitations. Site prose must not contradict it.
- Never collapse published, verified, clean-installed, human-accepted,
  independently reviewed, production-qualified, and stable into one status.
- No secrets, analytics, tracking, third-party runtime scripts, or mutable
  download references.
- Keep the site usable without JavaScript and retain accessibility, reduced
  motion, local-reference, CSP, and contrast guarantees.
- Run `python3 scripts/validate_repo.py` and
  `python3 scripts/check_site_quality.py` before claiming a site change is
  validated.
- Update `STATUS.md`, `PROJECT_STATE.yaml`, and `NEXT_ACTIONS.md` whenever
  release or deployment truth changes.

## Active scope

Only two outcomes are active:

1. verify the public one-command alpha.2 install on a clean Ubuntu 24.04 AMD64
   machine and record the exact receipt plus owner verdict;
2. design and ship a later capability-based Linux target without weakening or
   silently bypassing the signed alpha.2 contract.

Everything else is backlog or history.
