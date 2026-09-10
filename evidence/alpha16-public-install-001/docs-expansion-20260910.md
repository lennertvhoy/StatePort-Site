# Public documentation expansion — 10 September 2026

User request: drastically improve incomplete public documentation, using Luna
subagents. Three bounded draft groups and one read-only fact review used Luna;
only the coordinator edited the canonical repository. No product runtime,
provider account, template repository, or immutable release was changed.

## Continuation and queued refresh

Reviewed the 2026-09-06 reference UPGRADING.md, core AGENTS.md and applicable gate.
Continuation/persistent-thread guidance is already merged; the local gate matches
the reference byte for byte. Existing AGENTS.md changes and untracked Alpha.14
evidence are owner/pre-existing work and are excluded from this docs commit.
The current Linux 7.1.9-arch1-2 workstation is not a fresh Windows 11 WSL2 target.
The real primary remains blocked by that environment and the recorded signature
preflight/private-GHCR failures. No unchanged installer retry was admitted;
refresh notices remain and migration completion is not claimed. Next event for
that lane is a corrected qualified successor and genuine intended environment.

Continue: this independent documentation increment addresses the unchanged clear
public documentation acceptance criterion. The smallest useful boundary is a
reader following concrete instructions, supported by source review, static checks,
and a phone/desktop browser journey. No heavy runtime build is necessary.

## What changed

- Added everyday-work, project-state and troubleshooting guides.
- Expanded installation, template import, StudyState, approvals, AI readiness,
  lifecycle/backup/recovery, updates/uninstall, model, privacy, reference and index.
- All 21 docs pages have common static navigation; updated the sitemap, HTML
  tables of contents and progressive navigation. Core content needs no JavaScript.
- Shared script route labels now derive from the reading sequence to stay within
  the existing 24 KB budget. Cache keys advanced on mutable pages only.
- Existing section IDs remain available. Added pages receive the same copy checks.
- Corrected uninstall SHA-256 from stale 7930d29b… to b49dbcde… (the exact linked
  Alpha.16 installer). The code now runs in a fail-fast subshell with cleanup.
  No uninstall command was executed during documentation verification.

## Sources and review

Versioned Alpha.16 bootstrap.sh, release-index.json and stateport-installer govern
public installer commands, prompts, package flow, target and identity. Current
StatePort read-only source informed conditionally available UI controls:
CatalogPage/ImportRepositoryDrawer; StudyJourney; ProviderSettings; ReadinessSummary;
ExecutionHostPage; receipts; BACKUP_RESTORE.md. ProjectState_Template and
StudyState_Template contracts informed template guides. Public source behavior
was paraphrased; private repository contents/paths and secrets were not published.
Existing verified 72-second field-guide transcript grounds the sample walkthrough.
Current-source controls are not represented as a newly qualified Alpha.16 install.

Coordinator corrections include: sample reflection completes the activity (not
merely starts it); re-import is not instance migration; local restore is not a
cross-host migration wizard; provider verification can consume account quota;
uninstall checksum matches actual artifact; full shell newlines replace HTML br;
original navigation shell, social metadata and anchors retained. A review concern
about apt commands used the inner installer rather than bootstrap; the versioned
bootstrap lines 215–217 explicitly perform apt update/install, so this description
was retained and prerequisite packages are not falsely called version-pinned.

## Validation and delivery

Local environment: loopback HTTP server on 4196, isolated headless Chromium,
360/1440px, JavaScript on/off. Browser connector unavailable (empty discovery);
standalone headless Chromium used without touching the owner's desktop.

Commands/reports under `output/docs-expansion-20260910/`:
- `browser.cjs`: all 21 docs pages × four views, 84 render checks.
- `journey.cjs`: docs → first session → import → ProjectState, troubleshooting →
  provider setup; catalogue filter and mobile/static navigation across four views.
- `content-checks.json`: original IDs preserved, uninstall shell parses, linked
  artifact checksum matches. Source article text expanded from ~5,900 to ~11,000
  words; word count is coverage context, not comprehension or acceptance proof.
- `python3 scripts/validate_repo.py`: site validation passes; separately reports
  the unchanged blocked product outcome.
- `python3 scripts/check_site_quality.py`: 34-page quality contract passes.
- `python3 -B -m unittest discover -s scripts -p 'test_*.py'`: 30 tests pass.
- `python3 scripts/projectstate_gate.py`: expected exit 1, primary blocked.

The initial browser probe falsely classified a deferred lazy image as broken;
loading/decode checks fixed that fixture. Reading automation twice missed the
mobile toggle because CSS-generated text contributes to its accessible name;
using its observed name prefix fixed the locator without weakening the journey.
All final render/navigation results and desktop/phone screenshots are retained.

Publication is through the required heavy-run governor after cheap checks. The
fixed receipt `output/docs-expansion-20260910/public.json` records anonymous HTTP
byte matches for changed public files; `live.json` and `live-journey.json` record
live browser results. Absence or failure of those receipts does not establish
publication. Native install qualification and the human's product verdict remain
separate pending work.
