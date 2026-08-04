#!/usr/bin/env python3
"""Deterministic current-state contradiction validator for StatePort.

Rejects known contradictions between the canonical current-state files
(STATUS.md, NEXT_ACTIONS.md, PROJECT_STATE.yaml) and the machine-readable
anchor facts recorded in PROJECT_STATE.yaml. Append-only history files
(WORKLOG.md, docs/EVIDENCE_LOG.md, HANDOFF_*.md) are never scanned.

Scope convention (must match the reconciled state files):

- STATUS.md: a ``##``/``###`` section whose heading contains "Historical"
  (case-insensitive) is historical through to the next heading of
  same-or-higher level; everything else is current scope. Historical
  content MUST live under such a heading: a current-scope paragraph or
  list item whose text begins with "Historical" is a violation.
- NEXT_ACTIONS.md: everything under the "## Completed since last update"
  heading is historical; everything above it is current scope. That
  heading must exist and must be the FINAL level-2 (##) section.
- PROJECT_STATE.yaml holds the anchor facts: ``workflow.release_freeze``,
  ``current_state.repository.canonicalBranch``, ``current_state.review.branch``,
  ``current_state.stateBinding``, and exactly one RELEASE-FREEZE incident
  record in ``incidents[]``.

FREEZE MODEL: ``workflow.release_freeze`` and the single RELEASE-FREEZE
incident record must exist and agree bidirectionally (true <-> open/active,
false <-> lifted/resolved; missing, duplicate, or unrecognized statuses fail
closed). Freeze-language text rules derive from the actual flag: claims that
the freeze is active are rejected when the flag is false, and claims that the
freeze is lifted or thawed are rejected when the flag is true; when the flag
is unreadable both directions are rejected (fail closed). Merge, branch, and
acceptance rules run regardless of the freeze state — an active freeze must
not disable them.

TYPED HEAD MODEL: a commit cannot contain its own SHA, so head identity is
split into typed fields instead of one false "Main HEAD":

- Canonical branch: STATUS.md ``**Canonical:**`` line and
  ``current_state.repository.canonicalBranch`` name the canonical branch
  (``main``) and nothing else. The exact canonical head derives from Git at
  validation time (``git rev-parse main`` / ``origin/main`` per the
  divergence rule below) and is NEVER persisted in current-state files: a
  persisted canonical SHA goes stale the moment canonical advances, which
  makes any such protocol unmergeable. When BOTH local ``main`` and
  ``origin/main`` exist they must be equal (``canonical-ref-divergence``);
  the local ref is used only when ``origin/main`` genuinely does not exist.
  A previously observed canonical SHA may remain only as a typed historical
  observation (``canonicalHeadObserved`` with ``classification:
  historical_observation``) and is never parsed as current truth. A
  feature-branch commit must never be recorded as the canonical head.
- Behavioural head: STATUS.md ``**Behavioural Head:**`` and
  ``current_state.stateBinding.behaviouralHead`` — the last product/runtime
  behaviour commit the state documents describe.
- Control head: STATUS.md ``**Control Head:**`` and
  ``current_state.stateBinding.controlHead`` — the last commit that changes
  this repository's typed-head policy or validator. The control head is
  optional only for legacy state records; once either file declares it,
  both files must declare the same full SHA.
- Both typed heads must resolve and be ancestors of HEAD. With the dual-head
  contract active, the behavioural-head commit must itself change a product
  path and the control-head commit must itself change a control path. This
  rejects a state-only reconciliation commit bound as either typed head.
  Since the behavioural head, only state/history and control paths may have
  changed; since the control head, only state/history and product paths may
  have changed. These complementary NET tree diffs (plus tracked worktree
  changes; untracked files are not authority and are ignored) ensure every
  newer product change rebinds the behavioural head and every newer protocol
  change rebinds the control head. State/history paths are the live state
  files, narrowly named dated archives under ``docs/history/state/``, and
  root-level ``HANDOFF*.md``. Runtime policy, release authority, schemas, and
  arbitrary documentation remain product paths and are not exempted.
  Squash/rebase rewrites break ancestry and fail closed: re-record the
  affected typed head as the rewritten commit.
- Review branch lifecycle: ``current_state.review.status`` is ``active`` or
  ``closed`` (absent means ``active``). ``active``: ``review.branch`` is
  required and its head derives from the branch ref at validation time
  (local ref, else ``origin/<branch>``), never from a persisted SHA in
  current state. ``closed``: the branch field is optional and no ref
  resolution is required, so canonical ``main`` keeps validating after a
  merged review branch is deleted.

Intentionally stdlib-only plus statedd_core.yaml.parse_yaml_text, mirroring
statedd_validate_schema.py. Importable: validate_repo_state() returns
findings; main() wraps the CLI.
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

CORE_SRC = REPO_ROOT / "packages" / "statedd-core" / "src"
if str(CORE_SRC) not in sys.path:
    sys.path.insert(0, str(CORE_SRC))

from statedd_core.yaml import StateDDYamlError, parse_yaml_text

STATUS_FILE = "STATUS.md"
NEXT_ACTIONS_FILE = "NEXT_ACTIONS.md"
PROJECT_STATE_FILE = "PROJECT_STATE.yaml"

FREEZE_INCIDENT_MARKER = "RELEASE-FREEZE"
EXPECTED_RECONCILIATION_POLICY = "state_only_descendant"
CANONICAL_BRANCH = "main"

FREEZE_FACT = (
    "PROJECT_STATE.yaml workflow.release_freeze is false and incident "
    "INC-2026-07-21-RELEASE-FREEZE-P0 is lifted (2026-07-25 product-owner "
    "directive); main is the single canonical version"
)
FREEZE_ACTIVE_FACT = (
    "PROJECT_STATE.yaml workflow.release_freeze is true and the "
    "RELEASE-FREEZE incident is active; current-scope text may not claim "
    "the freeze is lifted or thawed"
)
FREEZE_INCIDENT_FACT = (
    "exactly one RELEASE-FREEZE incident record must exist and its status "
    "must agree with workflow.release_freeze in both directions "
    "(true <-> open/active, false <-> lifted/resolved)"
)
MERGED_FACT = (
    "BL-AI-VERTICAL-002 is merged to canonical main via PR #7 at ed3055f "
    "(2026-07-25); branch agent/bl-ai-vertical-002 is deleted"
)
BRANCH_FACT = (
    "stale release-program branches were deleted 2026-07-25; content is "
    "preserved via closed-PR refs and main is canonical"
)
CANONICAL_FACT = (
    "the canonical branch is main and its exact head derives from Git refs "
    "at validation time (git rev-parse main / origin/main); state files "
    "record only the branch name as current truth — a persisted canonical "
    "SHA (STATUS.md 'branch `main` at `<sha>`' or repository.head) is "
    "forbidden, and observed SHAs may remain only as typed "
    "canonicalHeadObserved historical observations"
)
DIVERGENCE_FACT = (
    "local main and origin/main must name the same commit; run "
    "git fetch origin and reconcile the refs (fast-forward the stale side "
    "or push the missing commits) before state can be validated"
)
BEHAVIOURAL_FACT = (
    "stateBinding.behaviouralHead names the last product/runtime behaviour "
    "commit the state describes; with the dual-head contract active, only "
    "state/history and typed-head control files may change after it — "
    "re-record behaviouralHead as the newest product commit in a state-only "
    "commit"
)
CONTROL_FACT = (
    "stateBinding.controlHead names the last typed-head policy/validator "
    "commit the state describes; only state/history and product files may "
    "change after it — re-record controlHead as the newest typed-head "
    "control commit in a state-only commit"
)
REBIND_FACT = (
    "the named head must be an ancestor of HEAD; if the commit was "
    "rewritten (squash/rebase), rebind STATUS.md Behavioural Head and "
    "PROJECT_STATE.yaml stateBinding.behaviouralHead: re-record "
    "behaviouralHead as the rewritten (new) non-state commit in a "
    "state-only commit"
)
CONTROL_REBIND_FACT = (
    "the named control head must be an ancestor of HEAD; if the commit was "
    "rewritten (squash/rebase), rebind STATUS.md Control Head and "
    "PROJECT_STATE.yaml stateBinding.controlHead to the rewritten typed-head "
    "control commit in a state-only commit"
)

# State/history paths are deliberately narrow. Dated rotations use an exact
# basename/date/extension grammar so arbitrary files cannot gain state-only
# authority merely by being placed under docs/history/state/.
STATE_DOC_PATHS = frozenset(
    {
        STATUS_FILE,
        NEXT_ACTIONS_FILE,
        PROJECT_STATE_FILE,
        "WORKLOG.md",
        "docs/EVIDENCE_LOG.md",
    }
)
ROOT_HANDOFF_RE = re.compile(r"^HANDOFF[^/]*\.md$")
DATED_STATE_ARCHIVE_RE = re.compile(
    r"^docs/history/state/"
    r"(?:STATUS|NEXT_ACTIONS|PROJECT_STATE|WORKLOG|EVIDENCE_LOG)-"
    r"\d{4}-\d{2}-\d{2}\.(?:md|yaml)$"
)

# This is intentionally an exact allowlist for executable repository-control
# protocols. Runtime product paths, release ledgers, unrelated schemas,
# general scripts, and arbitrary tests remain product paths. The workspace
# lifecycle entries were added under typed owner directive
# OD-2026-07-29-CONVERGENCE-CORRECTIVE. The standing-authority entries were
# added under OD-2026-07-29-BOUNDED-DELEGATION; any further expansion still
# requires owner review.
CONTROL_PATHS = frozenset(
    {
        "AGENTS.md",
        "PROJECT_DNA.yaml",
        "apps/admin-cli/src/admin_cli/main.py",
        "apps/admin-cli/src/admin_cli/authority.py",
        "apps/admin-cli/src/admin_cli/workspaces.py",
        "config/authority-policy.v1.yaml",
        "config/workspace-lifecycle.v1.yaml",
        "docs/operations/authority.md",
        "docs/operations/workspace-lifecycle.md",
        "fixtures/statebench/workspace-lifecycle-incident-2026-07-29.yaml",
        "packages/governed-runner/README.md",
        "packages/governed-runner/src/governed_runner/__init__.py",
        "packages/governed-runner/src/governed_runner/authority.py",
        "packages/governed-runner/src/governed_runner/workspaces.py",
        "packages/statebench/src/statebench/devloop.py",
        "schemas/authority-action-receipt.v1.schema.json",
        "schemas/authority-grant.v1.schema.json",
        "schemas/authority-policy.v1.schema.json",
        "schemas/workspace-budget.v1.schema.json",
        "schemas/workspace-lease.v1.schema.json",
        "scripts/local_closure_gate.py",
        "scripts/test_authority_policy.py",
        "scripts/test_local_closure_gate.py",
        "scripts/test_statebench_devloop.py",
        "scripts/validate_state_consistency.py",
        "scripts/test_validate_authority_policy.py",
        "scripts/test_validate_state_consistency.py",
        "scripts/test_validate_workspace_lifecycle.py",
        "scripts/test_workspace_authority_integration.py",
        "scripts/test_workspace_lifecycle.py",
        "scripts/validate_authority_policy.py",
        "scripts/validate_repo.py",
        "scripts/validate_workspace_lifecycle.py",
    }
)
SHA40_RE = re.compile(r"[0-9a-f]{40}")


@dataclass(frozen=True)
class Rule:
    """A current-scope contradiction rule applied line by line."""

    id: str
    pattern: re.Pattern[str]
    fact: str
    # Optional second pattern that must also match the same line.
    also: re.Pattern[str] | None = None
    # Optional same-line exemption that suppresses the match.
    unless: re.Pattern[str] | None = None


# State-independent rules: merge/branch/acceptance contradictions run
# regardless of the freeze flag — an active freeze must not disable them.
TEXT_RULES: tuple[Rule, ...] = (
    Rule(
        id="vertical-unmerged",
        pattern=re.compile(r"\bunmerged\b"),
        also=re.compile(
            r"BL-AI-VERTICAL-002|bl-ai-vertical-002|AI vertical|AI application vertical",
            re.IGNORECASE,
        ),
        # Truthful retrospective lines ("previously unmerged ... now merged")
        # are not contradictions.
        unless=re.compile(r"now merged|merged to (the )?`?main", re.IGNORECASE),
        fact=MERGED_FACT,
    ),
    Rule(
        id="acceptance-not-merged",
        pattern=re.compile(r"No current result is [^.]*\bmerged\b", re.IGNORECASE),
        fact=MERGED_FACT,
    ),
)


def _freeze_rules(release_freeze: bool | None) -> tuple[Rule, ...]:
    """Freeze-language rules derived from the actual freeze flag.

    False: claims that the freeze is active are contradictions.
    True: claims that the freeze is lifted or thawed are contradictions.
    None (flag unreadable): both directions are rejected (fail closed).
    """
    active_claims = (
        Rule(
            id="freeze-active",
            pattern=re.compile(
                r"(P0\s+)?(platform\s+)?release freeze (remains|is) (still )?active",
                re.IGNORECASE,
            ),
            fact=FREEZE_FACT,
        ),
        Rule(
            id="frozen-main",
            pattern=re.compile(r"frozen `?main", re.IGNORECASE),
            fact=FREEZE_FACT,
        ),
        Rule(
            id="frozen-main",
            pattern=re.compile(r"main is frozen", re.IGNORECASE),
            fact=FREEZE_FACT,
        ),
        Rule(
            id="freeze-not-lifted",
            pattern=re.compile(
                r"does not lift the (P0\s+)?(platform\s+)?(release\s+)?freeze",
                re.IGNORECASE,
            ),
            fact=FREEZE_FACT,
        ),
    )
    lifted_claims = (
        Rule(
            id="freeze-lifted-claim",
            pattern=re.compile(
                r"(release\s+)?freeze\s+(is\s+|has\s+been\s+|was\s+|remains\s+)?(now\s+)?(lifted|thawed)\b",
                re.IGNORECASE,
            ),
            fact=FREEZE_ACTIVE_FACT,
        ),
        Rule(
            id="freeze-lifted-claim",
            pattern=re.compile(
                r"(lifted|thawed) the (P0\s+)?(platform\s+)?(release\s+)?freeze",
                re.IGNORECASE,
            ),
            fact=FREEZE_ACTIVE_FACT,
        ),
    )
    if release_freeze is True:
        return lifted_claims
    if release_freeze is False:
        return active_claims
    return active_claims + lifted_claims

# Branch references that are stale unless the enclosing line / list item /
# paragraph carries an explicit archival annotation.
STALE_BRANCH_RE = re.compile(
    r"agent/bl-ai-vertical-002|agent/kimi-frontend-integration|"
    r"agent/acceptance-sidebar-mascot|agent/public-release-closure-001"
)
BRANCH_ANNOTATION_RE = re.compile(
    r"deleted|merged|closed|historical|preserved|superseded", re.IGNORECASE
)

HEADING_RE = re.compile(r"^(#{1,6})\s+(.*)$")
LEVEL2_HEADING_RE = re.compile(r"^##\s+(?!#)(.*)$")
LIST_ITEM_RE = re.compile(r"^\s*(?:[-*+]|\d+\.)\s")
HISTORICAL_HEADING_RE = re.compile(r"historical", re.IGNORECASE)
COMPLETED_HEADING_RE = re.compile(r"^##\s+Completed since last update", re.IGNORECASE)
HISTORICAL_BLOCK_START_RE = re.compile(
    r"^\s*(?:[-*+]\s+|\d+\.\s+)?historical\b", re.IGNORECASE
)

CANONICAL_LINE_RE = re.compile(r"\*\*Canonical:\*\*\s*branch `([^`]+)`")
# Forbidden old form: the Canonical line binding the branch to an exact SHA
# as current truth ("branch `main` at `<short>` (<sha40>)").
CANONICAL_PERSISTED_STATUS_RE = re.compile(
    r"\*\*Canonical:\*\*[^\n]*\bat\s+`[0-9a-fA-F]{7,40}`\s*\([0-9a-fA-F]{40}\)"
)
BEHAVIOURAL_LINE_RE = re.compile(r"\*\*Behavioural Head:\*\*\s*`([0-9a-fA-F]+)`")
CONTROL_LINE_RE = re.compile(r"\*\*Control Head:\*\*\s*`([0-9a-fA-F]+)`")


@dataclass(frozen=True)
class Finding:
    file: str
    line: int
    rule: str
    matched: str
    fact: str

    def render(self) -> str:
        return (
            f"{self.file}:{self.line}: RULE {self.rule}: "
            f"matched {self.matched!r} — contradicts canonical fact: {self.fact}"
        )


# ---------------------------------------------------------------------------
# Current-scope extraction
# ---------------------------------------------------------------------------


def status_current_lines(text: str) -> list[tuple[int, str]]:
    """Return (line_number, line) pairs in current (non-historical) scope."""
    current: list[tuple[int, str]] = []
    historical_level: int | None = None
    for lineno, line in enumerate(text.splitlines(), 1):
        heading = HEADING_RE.match(line)
        if heading:
            level = len(heading.group(1))
            title = heading.group(2)
            if historical_level is not None and level <= historical_level:
                historical_level = None
            if level >= 2 and HISTORICAL_HEADING_RE.search(title):
                historical_level = level
                continue
            if historical_level is not None:
                continue
            current.append((lineno, line))
            continue
        if historical_level is not None:
            continue
        current.append((lineno, line))
    return current


def next_actions_current_lines(text: str) -> list[tuple[int, str]]:
    """Return (line_number, line) pairs above the completed-history heading."""
    current: list[tuple[int, str]] = []
    historical = False
    for lineno, line in enumerate(text.splitlines(), 1):
        if not historical and COMPLETED_HEADING_RE.match(line):
            historical = True
        if historical:
            continue
        current.append((lineno, line))
    return current


def _blocks(scoped_lines: list[tuple[int, str]]) -> list[list[tuple[int, str]]]:
    """Group scoped lines into logical blocks.

    A block is a list item together with its continuation lines, or a
    paragraph of consecutive non-blank lines. Blank lines and headings start
    a new block. Branch annotations apply to the whole block so a wrapped
    line is excused by an annotation on its own logical statement.
    """
    blocks: list[list[tuple[int, str]]] = []
    current: list[tuple[int, str]] = []
    for lineno, line in scoped_lines:
        if not line.strip():
            if current:
                blocks.append(current)
                current = []
            continue
        if HEADING_RE.match(line) or LIST_ITEM_RE.match(line):
            if current:
                blocks.append(current)
            current = [(lineno, line)]
            continue
        current.append((lineno, line))
    if current:
        blocks.append(current)
    return blocks


# ---------------------------------------------------------------------------
# Rule checks
# ---------------------------------------------------------------------------


def check_text_rules(
    scoped: list[tuple[int, str]],
    filename: str,
    release_freeze: bool | None,
) -> list[Finding]:
    findings: list[Finding] = []
    rules = TEXT_RULES + _freeze_rules(release_freeze)
    for lineno, line in scoped:
        for rule in rules:
            match = rule.pattern.search(line)
            if not match:
                continue
            if rule.also is not None and not rule.also.search(line):
                continue
            if rule.unless is not None and rule.unless.search(line):
                continue
            findings.append(
                Finding(filename, lineno, rule.id, match.group(0), rule.fact)
            )
    for block in _blocks(scoped):
        block_text = "\n".join(line for _, line in block)
        if BRANCH_ANNOTATION_RE.search(block_text):
            continue
        for lineno, line in block:
            match = STALE_BRANCH_RE.search(line)
            if match:
                findings.append(
                    Finding(
                        filename,
                        lineno,
                        "stale-deleted-branch",
                        match.group(0),
                        BRANCH_FACT,
                    )
                )
                break
    return findings


def check_historical_block_placement(
    scoped: list[tuple[int, str]],
) -> list[Finding]:
    """Historical content must live under a heading containing 'Historical'."""
    findings: list[Finding] = []
    for lineno, line in scoped:
        if HEADING_RE.match(line):
            continue
        match = HISTORICAL_BLOCK_START_RE.match(line)
        if match:
            findings.append(
                Finding(
                    STATUS_FILE,
                    lineno,
                    "historical-outside-heading",
                    match.group(0).strip(),
                    "historical content must live under a STATUS.md heading "
                    "containing 'Historical'; current scope is current truth only",
                )
            )
    return findings


def check_next_actions_structure(text: str) -> list[Finding]:
    """'## Completed since last update' must exist and be the final ## section."""
    findings: list[Finding] = []
    completed_line: int | None = None
    trailing: list[tuple[int, str]] = []
    for lineno, line in enumerate(text.splitlines(), 1):
        if COMPLETED_HEADING_RE.match(line):
            completed_line = lineno
            continue
        if completed_line is not None and LEVEL2_HEADING_RE.match(line):
            trailing.append((lineno, line.strip()))
    if completed_line is None:
        findings.append(
            Finding(
                NEXT_ACTIONS_FILE,
                1,
                "completed-heading-missing",
                "## Completed since last update",
                "NEXT_ACTIONS.md must end with a '## Completed since last "
                "update' history section as its final level-2 section",
            )
        )
        return findings
    for lineno, heading in trailing:
        findings.append(
            Finding(
                NEXT_ACTIONS_FILE,
                lineno,
                "completed-not-final",
                heading,
                "'## Completed since last update' must be the final level-2 "
                "section of NEXT_ACTIONS.md; move this section above it",
            )
        )
    return findings


# ---------------------------------------------------------------------------
# PROJECT_STATE.yaml anchor extraction
# ---------------------------------------------------------------------------


def _find_section(state: dict, key: str) -> dict | None:
    section = state.get(key)
    if isinstance(section, dict):
        return section
    current_state = state.get("current_state")
    if isinstance(current_state, dict) and isinstance(current_state.get(key), dict):
        return current_state[key]
    return None


def _find_incidents(state: dict) -> list:
    incidents = state.get("incidents")
    return incidents if isinstance(incidents, list) else []


def _match_line(text: str, pattern: re.Pattern[str], start: int = 0) -> int | None:
    """First 1-based line number matching pattern at or after start, or None."""
    for lineno, line in enumerate(text.splitlines(), 1):
        if lineno < start:
            continue
        if pattern.search(line):
            return lineno
    return None


def _line_of(text: str, pattern: re.Pattern[str], start: int = 0) -> int:
    """First 1-based line number matching pattern at or after start."""
    return _match_line(text, pattern, start) or 1


def _mapping_span(
    text: str, key: str
) -> tuple[int, int, list[tuple[int, str]]] | None:
    """Locate a YAML mapping key; return (key_line, indent, body_lines).

    body_lines holds (lineno, line) pairs for non-blank, non-comment lines
    indented deeper than the key — i.e. the mapping's own extent, so guards
    never match sibling or later sections.
    """
    lines = text.splitlines()
    key_re = re.compile(rf"^(\s*){re.escape(key)}:\s*(?:#.*)?$")
    for index, line in enumerate(lines):
        match = key_re.match(line)
        if not match:
            continue
        indent = len(match.group(1))
        body: list[tuple[int, str]] = []
        for body_index in range(index + 1, len(lines)):
            body_line = lines[body_index]
            if not body_line.strip() or body_line.lstrip().startswith("#"):
                continue
            if len(body_line) - len(body_line.lstrip()) <= indent:
                break
            body.append((body_index + 1, body_line))
        return index + 1, indent, body
    return None


def check_project_state_anchors(
    root: Path,
) -> tuple[list[Finding], bool | None, dict | None, str]:
    """Load PROJECT_STATE.yaml and check the freeze anchors bidirectionally.

    Returns (findings, release_freeze, parsed_state, raw_text).
    release_freeze is None when it cannot be determined (fail closed).
    """
    findings: list[Finding] = []
    path = root / PROJECT_STATE_FILE
    if not path.is_file():
        findings.append(
            Finding(
                PROJECT_STATE_FILE,
                1,
                "missing-state-file",
                PROJECT_STATE_FILE,
                FREEZE_FACT,
            )
        )
        return findings, None, None, ""
    raw = path.read_text(encoding="utf-8")
    try:
        state = parse_yaml_text(raw)
    except StateDDYamlError as exc:
        findings.append(
            Finding(PROJECT_STATE_FILE, 1, "state-unparseable", str(exc), FREEZE_FACT)
        )
        return findings, None, None, raw
    if not isinstance(state, dict):
        findings.append(
            Finding(
                PROJECT_STATE_FILE,
                1,
                "state-unparseable",
                "top-level YAML value is not a mapping",
                FREEZE_FACT,
            )
        )
        return findings, None, None, raw

    workflow = state.get("workflow")
    release_freeze: bool | None = None
    if isinstance(workflow, dict) and isinstance(workflow.get("release_freeze"), bool):
        release_freeze = workflow["release_freeze"]
    else:
        findings.append(
            Finding(
                PROJECT_STATE_FILE,
                _line_of(raw, re.compile(r"^workflow:")),
                "freeze-anchor-missing",
                "workflow.release_freeze",
                FREEZE_FACT,
            )
        )

    # Exactly one RELEASE-FREEZE incident record must exist, and the freeze
    # flag and the incident status must agree in both directions; an
    # unrecognized status fails closed.
    if release_freeze is not None:
        incidents_start = _line_of(raw, re.compile(r"^incidents:"))
        freeze_incidents = [
            incident
            for incident in _find_incidents(state)
            if isinstance(incident, dict)
            and FREEZE_INCIDENT_MARKER in str(incident.get("id", "")).upper()
        ]
        if not freeze_incidents:
            findings.append(
                Finding(
                    PROJECT_STATE_FILE,
                    incidents_start,
                    "freeze-incident-missing",
                    "no RELEASE-FREEZE incident record",
                    FREEZE_INCIDENT_FACT,
                )
            )
        elif len(freeze_incidents) > 1:
            findings.append(
                Finding(
                    PROJECT_STATE_FILE,
                    incidents_start,
                    "freeze-incident-duplicate",
                    f"{len(freeze_incidents)} RELEASE-FREEZE incident records",
                    FREEZE_INCIDENT_FACT,
                )
            )
        active_statuses = {"open", "active"}
        closed_statuses = {"lifted", "resolved"}
        for incident in freeze_incidents:
            incident_id = str(incident.get("id", ""))
            status = str(incident.get("status", "")).strip().lower()
            line = _line_of(
                raw, re.compile(re.escape(incident_id)), start=incidents_start
            )
            if release_freeze is False:
                if status in active_statuses:
                    findings.append(
                        Finding(
                            PROJECT_STATE_FILE,
                            line,
                            "freeze-incident-open",
                            f"id {incident_id} status {status} while release_freeze is false",
                            FREEZE_INCIDENT_FACT,
                        )
                    )
                elif status not in closed_statuses:
                    findings.append(
                        Finding(
                            PROJECT_STATE_FILE,
                            line,
                            "freeze-incident-status",
                            f"id {incident_id} has unrecognized status {status!r}",
                            FREEZE_INCIDENT_FACT,
                        )
                    )
            else:
                if status in closed_statuses:
                    findings.append(
                        Finding(
                            PROJECT_STATE_FILE,
                            line,
                            "freeze-incident-closed",
                            f"id {incident_id} status {status} while release_freeze is true",
                            FREEZE_INCIDENT_FACT,
                        )
                    )
                elif status not in active_statuses:
                    findings.append(
                        Finding(
                            PROJECT_STATE_FILE,
                            line,
                            "freeze-incident-status",
                            f"id {incident_id} has unrecognized status {status!r}",
                            FREEZE_INCIDENT_FACT,
                        )
                    )

    return findings, release_freeze, state, raw


# ---------------------------------------------------------------------------
# Git helpers (bounded; every failure path fails closed)
# ---------------------------------------------------------------------------

GIT_TIMEOUT_SECONDS = 30


def _git(root: Path, *args: str) -> subprocess.CompletedProcess[str] | None:
    """Run git bounded; None on timeout/OS error."""
    try:
        return subprocess.run(
            ["git", *args],
            cwd=root,
            capture_output=True,
            text=True,
            check=False,
            timeout=GIT_TIMEOUT_SECONDS,
        )
    except (OSError, subprocess.SubprocessError):
        # subprocess.TimeoutExpired is a SubprocessError subclass and lands
        # here, turning a timeout into the same fail-closed path as any
        # other git failure.
        return None


def _git_rev_parse(root: Path, ref: str) -> str | None:
    completed = _git(root, "rev-parse", "--verify", "--quiet", f"{ref}^{{commit}}")
    if completed is None or completed.returncode != 0:
        return None
    return completed.stdout.strip() or None


def _git_is_ancestor(root: Path, ref: str) -> bool:
    completed = _git(root, "merge-base", "--is-ancestor", ref, "HEAD")
    return completed is not None and completed.returncode == 0


def _git_changed_paths(root: Path, ref: str) -> list[str] | None:
    """Net tree diff for the committed range plus tracked worktree changes.

    Untracked files are not authority and are ignored (e.g. intentionally
    untracked operator assets must not fail the gate).
    """
    changed: set[str] = set()
    for args in (("diff", "--name-only", f"{ref}..HEAD"), ("diff", "--name-only", ref)):
        completed = _git(root, *args)
        if completed is None or completed.returncode != 0:
            return None
        changed.update(line for line in completed.stdout.splitlines() if line.strip())
    return sorted(changed)


def _git_commit_paths(root: Path, ref: str) -> list[str] | None:
    """Return paths changed by one commit against all of its parents.

    ``--root`` covers a root commit and ``-m`` makes merge commits explicit.
    The union is sufficient for typed-head classification: a state-only
    merge cannot masquerade as product or protocol work.
    """
    completed = _git(
        root,
        "diff-tree",
        "--root",
        "-m",
        "--no-commit-id",
        "--name-only",
        "-r",
        ref,
    )
    if completed is None or completed.returncode != 0:
        return None
    return sorted(
        {line for line in completed.stdout.splitlines() if line.strip()}
    )


def _is_state_doc_path(path: str) -> bool:
    return (
        path in STATE_DOC_PATHS
        or ROOT_HANDOFF_RE.fullmatch(path) is not None
        or DATED_STATE_ARCHIVE_RE.fullmatch(path) is not None
    )


def _is_control_path(path: str) -> bool:
    return path in CONTROL_PATHS


def _is_product_path(path: str) -> bool:
    return not _is_state_doc_path(path) and not _is_control_path(path)


# ---------------------------------------------------------------------------
# Typed head model checks
# ---------------------------------------------------------------------------


@dataclass
class _HeadField:
    value: str | None
    line: int


def _extract_status_heads(
    scoped: list[tuple[int, str]],
) -> tuple[_HeadField, _HeadField, _HeadField]:
    branch = _HeadField(None, 1)
    behavioural = _HeadField(None, 1)
    control = _HeadField(None, 1)
    for lineno, line in scoped:
        canonical_match = CANONICAL_LINE_RE.search(line)
        if canonical_match and branch.value is None:
            branch = _HeadField(canonical_match.group(1), lineno)
        behavioural_match = BEHAVIOURAL_LINE_RE.search(line)
        if behavioural_match and behavioural.value is None:
            behavioural = _HeadField(behavioural_match.group(1), lineno)
        control_match = CONTROL_LINE_RE.search(line)
        if control_match and control.value is None:
            control = _HeadField(control_match.group(1), lineno)
    return branch, behavioural, control


def _sha40_ok(value: str | None) -> bool:
    return value is not None and SHA40_RE.fullmatch(value) is not None


def check_typed_heads(
    root: Path,
    status_scoped: list[tuple[int, str]],
    state: dict | None,
    state_raw: str,
) -> list[Finding]:
    findings: list[Finding] = []

    status_branch, status_behavioural, status_control = _extract_status_heads(
        status_scoped
    )

    repository = _find_section(state, "repository") if state else None
    review = _find_section(state, "review") if state else None
    binding = _find_section(state, "stateBinding") if state else None

    repo_branch = repository.get("canonicalBranch") if repository else None
    review_branch = review.get("branch") if review else None
    review_status_raw = review.get("status") if review else None
    # Absent status means active (backward compatible); anything other than
    # active | closed is a violation reported below.
    review_status = (
        str(review_status_raw).strip() if review_status_raw is not None else "active"
    )
    review_active = review_status == "active"
    binding_behavioural = (
        str(binding["behaviouralHead"]).strip()
        if binding and binding.get("behaviouralHead") is not None
        else None
    )
    binding_control = (
        str(binding["controlHead"]).strip()
        if binding and binding.get("controlHead") is not None
        else None
    )
    binding_policy = binding.get("reconciliationPolicy") if binding else None
    dual_heads = status_control.value is not None or binding_control is not None

    # --- persisted-head guards --------------------------------------------
    # An exact canonical or review head must never live in current-state
    # files; observed SHAs may remain only as typed historical observations
    # (e.g. canonicalHeadObserved with classification historical_observation).
    for lineno, line in status_scoped:
        if CANONICAL_PERSISTED_STATUS_RE.search(line):
            findings.append(
                Finding(
                    STATUS_FILE,
                    lineno,
                    "canonical-head-persisted",
                    line.strip(),
                    CANONICAL_FACT,
                )
            )
            break
    repository_map = _mapping_span(state_raw, "repository")
    if repository_map is not None:
        _, repo_indent, repo_body = repository_map
        repo_head_re = re.compile(
            rf"^\s{{{repo_indent + 2}}}head:\s*[0-9a-fA-F]{{7,40}}\s*$"
        )
        for lineno, line in repo_body:
            if repo_head_re.match(line):
                findings.append(
                    Finding(
                        PROJECT_STATE_FILE,
                        lineno,
                        "canonical-head-persisted",
                        "repository.head persists an exact canonical SHA as current truth",
                        CANONICAL_FACT,
                    )
                )
                break
    review_map = _mapping_span(state_raw, "review")
    if review_map is not None:
        _, review_indent, review_body = review_map
        review_observed_re = re.compile(rf"^\s{{{review_indent + 2}}}headObserved:")
        for lineno, line in review_body:
            if review_observed_re.match(line):
                findings.append(
                    Finding(
                        PROJECT_STATE_FILE,
                        lineno,
                        "review-head-persisted",
                        "review.headObserved persists an exact review head",
                        "the review-branch head derives from its ref at validation "
                        "time (local ref, else origin/<branch>) and must not be "
                        "persisted as current state",
                    )
                )
                break

    # --- anchors present -------------------------------------------------
    if review_status not in ("active", "closed"):
        findings.append(
            Finding(
                PROJECT_STATE_FILE,
                1,
                "review-status",
                f"review.status {review_status!r}",
                "current_state.review.status must be 'active' or 'closed' "
                "(absent means 'active'): 'active' requires review.branch to "
                "resolve; 'closed' makes the branch optional so canonical "
                "main validates after the review branch is deleted",
            )
        )
    missing: list[tuple[str, str]] = []
    if status_branch.value is None:
        missing.append((STATUS_FILE, "**Canonical:**"))
    if status_behavioural.value is None:
        missing.append((STATUS_FILE, "**Behavioural Head:**"))
    if dual_heads and status_control.value is None:
        missing.append((STATUS_FILE, "**Control Head:**"))
    if repo_branch is None:
        missing.append((PROJECT_STATE_FILE, "repository.canonicalBranch"))
    if binding_behavioural is None or binding_policy is None:
        missing.append((PROJECT_STATE_FILE, "stateBinding"))
    if dual_heads and binding_control is None:
        missing.append((PROJECT_STATE_FILE, "stateBinding.controlHead"))
    if review_branch is None and review_active:
        missing.append((PROJECT_STATE_FILE, "review.branch"))
    for filename, anchor in missing:
        findings.append(
            Finding(filename, 1, "head-anchor-missing", anchor, BEHAVIOURAL_FACT)
        )
    if missing:
        return findings

    # --- sha-format: formal SHA fields are full 40-char lowercase hex ----
    if not _sha40_ok(status_behavioural.value):
        findings.append(
            Finding(
                STATUS_FILE,
                status_behavioural.line,
                "sha-format",
                f"STATUS.md Behavioural Head = {status_behavioural.value!r}",
                "formal SHA fields must be full 40-character lowercase hex",
            )
        )
    if not _sha40_ok(binding_behavioural):
        findings.append(
            Finding(
                PROJECT_STATE_FILE,
                1,
                "sha-format",
                f"stateBinding.behaviouralHead = {binding_behavioural!r}",
                "formal SHA fields must be full 40-character lowercase hex",
            )
        )
    if dual_heads and not _sha40_ok(status_control.value):
        findings.append(
            Finding(
                STATUS_FILE,
                status_control.line,
                "sha-format",
                f"STATUS.md Control Head = {status_control.value!r}",
                "formal SHA fields must be full 40-character lowercase hex",
            )
        )
    if dual_heads and not _sha40_ok(binding_control):
        findings.append(
            Finding(
                PROJECT_STATE_FILE,
                1,
                "sha-format",
                f"stateBinding.controlHead = {binding_control!r}",
                "formal SHA fields must be full 40-character lowercase hex",
            )
        )

    # --- canonical branch: STATUS.md and state agree, and it is main -----
    if str(repo_branch) != str(status_branch.value):
        findings.append(
            Finding(
                PROJECT_STATE_FILE,
                1,
                "canonical-head-truth",
                f"repository.canonicalBranch {repo_branch!r} != STATUS.md canonical branch {status_branch.value!r}",
                CANONICAL_FACT,
            )
        )
    if str(status_branch.value) != CANONICAL_BRANCH:
        findings.append(
            Finding(
                STATUS_FILE,
                status_branch.line,
                "canonical-head-truth",
                f"canonical branch {status_branch.value!r} != {CANONICAL_BRANCH!r}",
                CANONICAL_FACT,
            )
        )

    # --- canonical head derives from git; local and remote must agree -----
    # When BOTH local main and origin/main exist they must be equal — a
    # stale local main must not mask a newer remote. The local ref is used
    # only when origin/main genuinely does not exist.
    branch_name = str(status_branch.value)
    local_ref = _git_rev_parse(root, branch_name)
    remote_ref = _git_rev_parse(root, f"origin/{branch_name}")
    if local_ref is not None and remote_ref is not None and local_ref != remote_ref:
        findings.append(
            Finding(
                PROJECT_STATE_FILE,
                1,
                "canonical-ref-divergence",
                f"local {branch_name} {local_ref} != origin/{branch_name} {remote_ref}",
                DIVERGENCE_FACT,
            )
        )
    if local_ref is None and remote_ref is None:
        findings.append(
            Finding(
                PROJECT_STATE_FILE,
                1,
                "head-unverifiable",
                f"git rev-parse {branch_name} and origin/{branch_name} both failed; failing closed",
                CANONICAL_FACT,
            )
        )

    # --- review branch: an active review requires a resolvable ref -------
    # Its head derives from the ref at validation time. A closed review
    # needs no ref: canonical main must keep validating after the merged
    # review branch is deleted.
    if review_active and review_branch is not None:
        review_ref = _git_rev_parse(root, str(review_branch))
        if review_ref is None:
            review_ref = _git_rev_parse(root, f"origin/{review_branch}")
        if review_ref is None:
            findings.append(
                Finding(
                    PROJECT_STATE_FILE,
                    1,
                    "review-head",
                    f"review.branch {review_branch}",
                    "the review-branch head derives from its ref at validation "
                    "time; the ref must resolve locally or as origin/<branch>",
                )
            )

    # --- cross-file behavioural head agreement ---------------------------
    if (
        _sha40_ok(status_behavioural.value)
        and _sha40_ok(binding_behavioural)
        and status_behavioural.value != binding_behavioural
    ):
        findings.append(
            Finding(
                PROJECT_STATE_FILE,
                1,
                "head-disagreement",
                f"STATUS.md Behavioural Head {status_behavioural.value!r} != stateBinding.behaviouralHead {binding_behavioural!r}",
                BEHAVIOURAL_FACT,
            )
        )

    # --- cross-file control head agreement -------------------------------
    if (
        dual_heads
        and _sha40_ok(status_control.value)
        and _sha40_ok(binding_control)
        and status_control.value != binding_control
    ):
        findings.append(
            Finding(
                PROJECT_STATE_FILE,
                1,
                "control-head-disagreement",
                f"STATUS.md Control Head {status_control.value!r} != stateBinding.controlHead {binding_control!r}",
                CONTROL_FACT,
            )
        )

    # --- reconciliation policy -------------------------------------------
    if binding_policy != EXPECTED_RECONCILIATION_POLICY:
        findings.append(
            Finding(
                PROJECT_STATE_FILE,
                1,
                "reconciliation-policy",
                f"reconciliationPolicy {binding_policy!r}",
                f"stateBinding.reconciliationPolicy must be {EXPECTED_RECONCILIATION_POLICY!r}",
            )
        )

    # --- behavioural head: resolves, typed commit, bounded net delta ------
    if _sha40_ok(binding_behavioural):
        if (
            _git_rev_parse(root, binding_behavioural) is None
            or not _git_is_ancestor(root, binding_behavioural)
        ):
            findings.append(
                Finding(
                    PROJECT_STATE_FILE,
                    1,
                    "head-not-ancestor",
                    f"stateBinding.behaviouralHead {binding_behavioural}",
                    REBIND_FACT,
                )
            )
        else:
            if dual_heads:
                commit_paths = _git_commit_paths(root, binding_behavioural)
                if commit_paths is None:
                    findings.append(
                        Finding(
                            PROJECT_STATE_FILE,
                            1,
                            "head-unverifiable",
                            f"git diff-tree {binding_behavioural} failed; failing closed",
                            BEHAVIOURAL_FACT,
                        )
                    )
                elif not any(_is_product_path(path) for path in commit_paths):
                    findings.append(
                        Finding(
                            STATUS_FILE,
                            status_behavioural.line,
                            "behavioural-head-type",
                            f"behaviouralHead {binding_behavioural[:7]} changed only state/control paths: {', '.join(commit_paths) or '(none)'}",
                            "with the dual-head contract active, behaviouralHead "
                            "must name a commit that itself changes at least one "
                            "product/runtime path; a state-only reconciliation "
                            "commit is not behavioural truth",
                        )
                    )
            changed = _git_changed_paths(root, binding_behavioural)
            if changed is None:
                findings.append(
                    Finding(
                        PROJECT_STATE_FILE,
                        1,
                        "head-unverifiable",
                        f"git diff --name-only {binding_behavioural}..HEAD failed; failing closed",
                        BEHAVIOURAL_FACT,
                    )
                )
            else:
                for path in changed:
                    allowed = _is_state_doc_path(path) or (
                        dual_heads and _is_control_path(path)
                    )
                    if not allowed:
                        findings.append(
                            Finding(
                                STATUS_FILE,
                                status_behavioural.line,
                                "stale-head",
                                f"{path} changed since behaviouralHead {binding_behavioural[:7]} without a state-only rebind",
                                BEHAVIOURAL_FACT,
                            )
                        )

    # --- control head: resolves, typed commit, bounded net delta ----------
    if dual_heads and _sha40_ok(binding_control):
        if (
            _git_rev_parse(root, binding_control) is None
            or not _git_is_ancestor(root, binding_control)
        ):
            findings.append(
                Finding(
                    PROJECT_STATE_FILE,
                    1,
                    "control-head-not-ancestor",
                    f"stateBinding.controlHead {binding_control}",
                    CONTROL_REBIND_FACT,
                )
            )
        else:
            commit_paths = _git_commit_paths(root, binding_control)
            if commit_paths is None:
                findings.append(
                    Finding(
                        PROJECT_STATE_FILE,
                        1,
                        "head-unverifiable",
                        f"git diff-tree {binding_control} failed; failing closed",
                        CONTROL_FACT,
                    )
                )
            elif not any(_is_control_path(path) for path in commit_paths):
                findings.append(
                    Finding(
                        STATUS_FILE,
                        status_control.line,
                        "control-head-type",
                        f"controlHead {binding_control[:7]} changed no typed-head control path: {', '.join(commit_paths) or '(none)'}",
                        "controlHead must name a commit that itself changes at "
                        "least one exact typed-head policy/validator path; a "
                        "state-only reconciliation commit is not control truth",
                    )
                )

            changed = _git_changed_paths(root, binding_control)
            if changed is None:
                findings.append(
                    Finding(
                        PROJECT_STATE_FILE,
                        1,
                        "head-unverifiable",
                        f"git diff --name-only {binding_control}..HEAD failed; failing closed",
                        CONTROL_FACT,
                    )
                )
            else:
                for path in changed:
                    if _is_control_path(path):
                        findings.append(
                            Finding(
                                STATUS_FILE,
                                status_control.line,
                                "stale-control-head",
                                f"{path} changed since controlHead {binding_control[:7]} without a state-only rebind",
                                CONTROL_FACT,
                            )
                        )

    return findings


# ---------------------------------------------------------------------------
# Orchestration and CLI
# ---------------------------------------------------------------------------


def validate_repo_state(root: Path) -> list[Finding]:
    """Return all current-state contradiction findings under root."""
    findings: list[Finding] = []

    anchor_findings, release_freeze, state, state_raw = check_project_state_anchors(
        root
    )
    findings.extend(anchor_findings)

    scoped_by_file: dict[str, list[tuple[int, str]]] = {}
    raw_by_file: dict[str, str] = {}
    for filename, extractor in (
        (STATUS_FILE, status_current_lines),
        (NEXT_ACTIONS_FILE, next_actions_current_lines),
    ):
        path = root / filename
        if not path.is_file():
            findings.append(
                Finding(filename, 1, "missing-state-file", filename, FREEZE_FACT)
            )
            scoped_by_file[filename] = []
            raw_by_file[filename] = ""
            continue
        raw_by_file[filename] = path.read_text(encoding="utf-8")
        scoped_by_file[filename] = extractor(raw_by_file[filename])

    # Text contradiction rules always run; historical scoping shields
    # point-in-time records. Freeze-language rules derive from the actual
    # release_freeze flag; merge/branch/acceptance rules run regardless.
    for filename, scoped in scoped_by_file.items():
        findings.extend(check_text_rules(scoped, filename, release_freeze))

    findings.extend(check_historical_block_placement(scoped_by_file[STATUS_FILE]))
    if raw_by_file[NEXT_ACTIONS_FILE]:
        findings.extend(check_next_actions_structure(raw_by_file[NEXT_ACTIONS_FILE]))

    findings.extend(
        check_typed_heads(root, scoped_by_file[STATUS_FILE], state, state_raw)
    )
    return findings


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Reject known current-state contradictions in StatePort state files"
    )
    parser.add_argument(
        "root",
        nargs="?",
        default=str(REPO_ROOT),
        help="Repo root to validate (default: parent of scripts/)",
    )
    return parser.parse_args(argv[1:])


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv)
    root = Path(args.root).resolve()
    findings = validate_repo_state(root)
    if findings:
        for finding in findings:
            print(f"FAIL: {finding.render()}")
        print(f"FAILED: {len(findings)} state-consistency violation(s) found")
        return 1
    print(
        "PASS: state consistency checks passed "
        "(STATUS.md, NEXT_ACTIONS.md, PROJECT_STATE.yaml)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
