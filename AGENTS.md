---
repo_role: downstream_project
statedd_mode: operating
repo_mode: operating
statedd_version: statedd-template-v5
initialized_on: 2026-07-21
last_updated: 2026-07-21
---

# StatePort Site — Agent Notes

This repository is the public-facing website and documentation home for
StatePort. It is a StateSpec-governed downstream project, separate from the
private StatePort implementation repository.

## Read order

1. `AGENTS.md`
2. `STATUS.md`
3. `PROJECT_STATE.yaml`
4. `PROJECT_DNA.yaml`
5. `NEXT_ACTIONS.md`
6. `BACKLOG.md` and `WORKLOG.md` when planning or reviewing history

## Hard rules

- No fake completeness or unverified public claims.
- StatePort is currently in a private local-alpha/release-preparation phase.
  Do not describe the implementation repository as public, link visitors to
  a private source repository, invent a version, or offer a download before
  it exists.
- Use **Stateware**, **State-Centric Engineering**, and **StateSpec** in
  current public copy. Mention `StateDD` only as a clearly labelled legacy
  compatibility name when continuity requires it.
- Keep releases, availability, benchmarks, security, compliance, and
  production-readiness language conservative and traceable to the current
  project facts.
- The site is static HTML, CSS, and small progressive-enhancement JavaScript.
  Keep it usable without JavaScript and respect reduced-motion preferences.
- Never add secrets, tracking IDs, user data collection, or third-party
  credentials to the repository.
- Keep the visual system spare: one blue accent, generous space, no generic
  dashboard-card grids, and one clear action per section.
- Preserve the copied StatePort shell mascot byte-for-byte. Its source and
  checksum are recorded in `PROJECT_DNA.yaml`.
- Run `python3 scripts/validate_repo.py` before finishing a slice.
- Update `PROJECT_STATE.yaml`, `NEXT_ACTIONS.md`, and `WORKLOG.md` whenever
  current truth changes. Update `STATUS.md` for a material delivery-state
  change.
