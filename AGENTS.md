---
repo_role: downstream_project
statedd_mode: operating
repo_mode: operating
statedd_version: statedd-template-v5
initialized_on: 2026-07-21
last_updated: 2026-08-09
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

### Unified UX closure integration

OD-2026-08-08-KIMI-LONG-RUN authorized the historical containment based on
`a894b5b4aacac368e00f345c9ec1fc6f7c1f16f5`; it was committed as
`c1384061a093f8f4fc7e68f8ca7126558e1e97a5`, deployed, and publicly verified.
That verdict is consumed. Current dirty-candidate review, validation, commit,
push, and managed deployment authority is OD-2026-08-10-UNIFIED-UX-CLOSURE.
Its Site candidate is locally rendered and validated, but remains uncommitted
and not deployed until the authorized commit/push sequence and managed Pages
verification; no deployment or release claim follows.

## Mandatory read order

1. `AGENTS.md`
2. `STATUS.md`
3. `PROJECT_STATE.yaml`
4. `NEXT_ACTIONS.md`
5. the exact signed release index when touching release claims

Current state overrides old branch prose, PR bodies, screenshots, and handoffs.

## Current release truth

- Public candidate: `v0.1.0-alpha.3` — published, signed, byte-intact,
  **install-disabled**, and not owner-accepted.
- Signed payload:
  `sha256:2639e29d6ca0a5bd83d07013edb49f22692efaf53a6049234fe6b70810c89166`.
- Installation is disabled because every signed image carries 2026-08-06
  scan/database evidence under a 24-hour maximum (current verification
  refuses: Grype database stale) and the released bytes carry known
  installer/runtime defects (no execution-host provisioning or protocol
  health check; synthetic goal execution).
- Earlier local install receipts for Ubuntu 24.04 (`validated_baseline`) and
  Fedora 44 (`compatible_unvalidated`) are historical evidence recorded while
  the freshness window was open. They are not current install proof.
- The portable target is `linux-amd64-rootless-podman-quadlet`; distribution
  branding is observation, not eligibility. Debian and rolling distributions
  are not claimed.
- The mutable convenience bootstrap (`download/install.sh`) is a fail-closed
  stub; the immutable versioned bootstraps under the release trees are
  unchanged signed evidence. Mutable surfaces promote no install command and
  link `download/erratum-alpha3.html`.
- Canonical development Git is private. The curated alpha.3 source archive is
  publicly distributed and AGPL-classified; the signed public Git snapshot
  identity (`43d6b4491b962c963a0ecafc060e0dfc7e334dc0`) is not remotely
  resolvable — a successor-release blocker.
- Alpha.2 is **known defective, superseded, install-disabled, and
  unaccepted**. Its signed bytes remain immutable and its bootstrap remains
  fail-closed.
- Independent security review and production qualification remain absent.
- Mutable containment content commit
  `c1384061a093f8f4fc7e68f8ca7126558e1e97a5` is live and verified through
  Pages run `31315882234` and deployment `5819133762`. All 48 immutable remote
  release files match their publication-anchored manifest.
- Pages deploys from `main` through GitHub's managed legacy Pages build. The
  repository's custom deploy workflow is manual-only and is not the provider.
  Nothing is "live" until it is actually deployed and publicly verified.

Never call alpha.3 installable, accepted, stable, audited, or
production-ready. Never silently replace alpha.2 signed bytes or transfer its
supply-chain evidence to alpha.3.

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

1. Preserve alpha.2's fail-closed erratum and alpha.3's exact signed artifacts;
   keep the immutable release trees byte-identical against their anchored
   publication manifests.
2. Keep mutable surfaces honestly contained (no promoted install command,
   erratum linked, fail-closed convenience bootstrap) until a corrected,
   separately authorized successor candidate exists.

Everything else is backlog or history.
