#!/usr/bin/env python3
"""Regression tests for the current-state contradiction validator.

Fixtures build real git topologies (main + review branch) with TRACKED,
committed state files, mirroring the typed head model: STATUS.md and
PROJECT_STATE.yaml live on a review branch ahead of main, the canonical
branch is named (main) with its exact head derived from Git refs at
validation time. Legacy fixtures use only stateBinding.behaviouralHead;
dual-head fixtures also bind the independently typed repository-control
commit through stateBinding.controlHead.
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path
from unittest import mock

import pytest

ROOT = Path(__file__).resolve().parents[1]
VALIDATOR = ROOT / "scripts" / "validate_state_consistency.py"

sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "packages" / "statedd-core" / "src"))

import validate_state_consistency as vsc

REVIEW_BRANCH = "agent/review-001"


def _git(root: Path, *args: str) -> str:
    # Inject committer identity for every fixture call (including merge/rebase)
    # so the suite passes on machines without a global git identity.
    completed = subprocess.run(
        [
            "git",
            "-c",
            "user.email=stateport-tests@example.com",
            "-c",
            "user.name=StatePort Tests",
            *args,
        ],
        cwd=root,
        capture_output=True,
        text=True,
        check=True,
    )
    return completed.stdout.strip()


def _commit(root: Path, message: str) -> str:
    _git(
        root,
        "-c",
        "user.email=test@example.com",
        "-c",
        "user.name=Test",
        "commit",
        "-m",
        message,
    )
    return _git(root, "rev-parse", "HEAD")


def _commit_files(root: Path, files: dict[str, str], message: str) -> str:
    for relative, content in files.items():
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        _git(root, "add", relative)
    return _commit(root, message)


def _state_files(
    *,
    behavioural: str,
    control: str | None = None,
    branch: str = "main",
    review_branch: str | None = REVIEW_BRANCH,
    review_status: str | None = None,
    canonical_observed: str = "0" * 40,
    release_freeze: str = "false",
    incident_status: str = "lifted",
    incident: bool = True,
    duplicate_incident: bool = False,
    policy: str = "state_only_descendant",
    canonical_line: str | None = None,
    status_body: str = "All good.\n",
    next_actions_body: str = "Nothing contradicting.\n",
) -> dict[str, str]:
    canonical_header = canonical_line or (
        f"**Canonical:** branch `{branch}`; the exact canonical head is derived "
        "from Git at validation time (last observed "
        f"`{canonical_observed}` as a typed historical observation)\n"
    )
    review_line = (
        f"**Review Branch:** `{review_branch}` (head derived from the branch ref at validation time)\n"
        if review_branch is not None
        else ""
    )
    control_line = (
        f"**Control Head:** `{control}` (typed-head policy/validator binding)\n"
        if control is not None
        else ""
    )
    status = (
        "# Status\n"
        "\n"
        f"{canonical_header}"
        f"{review_line}"
        f"**Behavioural Head:** `{behavioural}` (state binding: state_only_descendant)\n"
        f"{control_line}"
        "\n"
        "Phase: operating;\n"
        "\n"
        "## Current truth\n"
        "\n"
        f"{status_body}"
    )
    next_actions = (
        "# NEXT_ACTIONS\n"
        "\n"
        "**Max Items:** 4\n"
        "\n"
        "## P1 Some work\n"
        "\n"
        f"{next_actions_body}"
        "\n"
        "## Completed since last update (2026-07-22)\n"
        "\n"
        "- historical notes.\n"
    )
    incidents_block = ""
    if incident:
        incidents_block = (
            "incidents:\n"
            '  - id: "INC-2026-07-21-RELEASE-FREEZE-P0"\n'
            f"    status: {incident_status}\n"
        )
        if duplicate_incident:
            incidents_block += (
                '  - id: "INC-2026-07-22-RELEASE-FREEZE-P0-DUPLICATE"\n'
                f"    status: {incident_status}\n"
            )
    review_block = "  review:\n"
    if review_status is not None:
        review_block += f"    status: {review_status}\n"
    if review_branch is not None:
        review_block += f"    branch: {review_branch}\n"
    control_field = f"    controlHead: {control}\n" if control is not None else ""
    project_state = (
        "workflow:\n"
        f"  release_freeze: {release_freeze}\n"
        f"{incidents_block}"
        "current_state:\n"
        "  repository:\n"
        f"    canonicalBranch: {branch}\n"
        "    canonicalHeadObserved:\n"
        f"      commit: {canonical_observed}\n"
        '      observedAt: "2026-07-25"\n'
        "      classification: historical_observation\n"
        f"{review_block}"
        "  stateBinding:\n"
        f"    behaviouralHead: {behavioural}\n"
        f"{control_field}"
        f"    reconciliationPolicy: {policy}\n"
    )
    return {
        "STATUS.md": status,
        "NEXT_ACTIONS.md": next_actions,
        "PROJECT_STATE.yaml": project_state,
    }


def make_repo(tmp_path: Path, **state_kwargs: str) -> tuple[Path, str]:
    """main with one behavioural commit; review branch with committed state files.

    Returns (repo_root, main_sha). The state files name main as the canonical
    branch and main_sha as the behavioural head, so the fixture passes by
    default. State files are always committed and tracked.
    """
    root = tmp_path / "repo"
    root.mkdir(parents=True)
    _git(root, "init", "-b", "main")
    main_sha = _commit_files(root, {"app.py": "print('v1')\n"}, "feat: base product")
    _git(root, "checkout", "-b", REVIEW_BRANCH)
    files = _state_files(
        behavioural=main_sha, canonical_observed=main_sha, **state_kwargs
    )
    _commit_files(root, files, "docs(state): bind state files")
    return root, main_sha


def rebind(root: Path, *, behavioural: str, **state_kwargs: str) -> str:
    """State-only follow-up commit that rebinds the supplied typed heads."""
    files = _state_files(behavioural=behavioural, **state_kwargs)
    return _commit_files(root, files, "docs(state): rebind typed heads")


def rule_ids(findings: list[vsc.Finding]) -> set[str]:
    return {finding.rule for finding in findings}


# ---------------------------------------------------------------------------
# Pass cases
# ---------------------------------------------------------------------------


def test_real_repo_has_only_pending_rebind_findings() -> None:
    """Until the state-only binding commit lands, the only allowed findings
    on the real repo are typed-head rebind findings over an authorized pending
    product or control slice; after reconciliation, no findings at all."""
    findings = vsc.validate_repo_state(ROOT)
    assert {finding.rule for finding in findings} <= {"stale-head", "stale-control-head"}, findings


def test_minimal_repo_passes(tmp_path: Path) -> None:
    root, _ = make_repo(tmp_path)
    assert vsc.validate_repo_state(root) == []


def test_state_only_descendant_passes(tmp_path: Path) -> None:
    """behaviouralHead ancestor + state-only commits since -> pass."""
    root, main_sha = make_repo(tmp_path)
    _commit_files(
        root,
        {"WORKLOG.md": "history entry\n", "docs/EVIDENCE_LOG.md": "evidence\n"},
        "docs(state): append-only history update",
    )
    rebind(root, behavioural=main_sha)
    assert vsc.validate_repo_state(root) == []


def test_dated_state_archive_descendant_passes(tmp_path: Path) -> None:
    """A narrowly named dated state rotation remains state-only authority."""
    root, main_sha = make_repo(tmp_path)
    _commit_files(
        root,
        {"docs/history/state/WORKLOG-2026-07-29.md": "rotated history\n"},
        "docs(state): rotate dated worklog",
    )
    rebind(root, behavioural=main_sha)
    assert vsc.validate_repo_state(root) == []


def test_arbitrary_state_history_path_does_not_gain_authority(tmp_path: Path) -> None:
    """The archive directory is not a blanket state-only allowlist."""
    root, _ = make_repo(tmp_path)
    _commit_files(
        root,
        {"docs/history/state/NOTES-2026-07-29.md": "not a typed state archive\n"},
        "docs: add arbitrary history note",
    )
    findings = vsc.validate_repo_state(root)
    assert "stale-head" in rule_ids(findings), findings


def test_dual_behavioural_and_control_heads_pass(tmp_path: Path) -> None:
    """Product and typed-head protocol commits bind independently."""
    root, behavioural = make_repo(tmp_path)
    control = _commit_files(
        root,
        {"AGENTS.md": "typed-head control contract\n"},
        "chore(control): update typed-head contract",
    )
    rebind(root, behavioural=behavioural, control=control)
    assert vsc.validate_repo_state(root) == []


def test_product_after_control_passes_when_behavioural_head_is_rebound(
    tmp_path: Path,
) -> None:
    """Product changes do not stale an independently bound control head."""
    root, _ = make_repo(tmp_path)
    control = _commit_files(
        root,
        {"AGENTS.md": "typed-head control contract\n"},
        "chore(control): update typed-head contract",
    )
    behavioural = _commit_files(
        root,
        {"feature.py": "print('new behaviour')\n"},
        "feat: add newer product behaviour",
    )
    rebind(root, behavioural=behavioural, control=control)
    assert vsc.validate_repo_state(root) == []


def test_normal_merge_with_state_only_descendant_passes(tmp_path: Path) -> None:
    """Behavioural branch merged normally; state-only descendant after -> pass."""
    root, _ = make_repo(tmp_path)
    _git(root, "checkout", "-b", "feat", "main")
    feature_sha = _commit_files(root, {"feature.py": "print('f')\n"}, "feat: work")
    _git(root, "checkout", REVIEW_BRANCH)
    _git(root, "merge", "--no-ff", "-m", "merge feat", "feat")
    rebind(root, behavioural=feature_sha)
    assert vsc.validate_repo_state(root) == []


def test_post_merge_state_only_reconciliation_passes(tmp_path: Path) -> None:
    """A further state-only reconciliation commit after the merge still passes."""
    root, _ = make_repo(tmp_path)
    _git(root, "checkout", "-b", "feat", "main")
    feature_sha = _commit_files(root, {"feature.py": "print('f')\n"}, "feat: work")
    _git(root, "checkout", REVIEW_BRANCH)
    _git(root, "merge", "--no-ff", "-m", "merge feat", "feat")
    rebind(root, behavioural=feature_sha)
    _commit_files(
        root, {"WORKLOG.md": "post-merge reconciliation\n"}, "docs(state): reconcile"
    )
    assert vsc.validate_repo_state(root) == []


def test_fast_forward_integration_passes(tmp_path: Path) -> None:
    """Fast-forward of the complete review line into main, ending with a
    state-only rebind on main -> pass (topology b)."""
    root, _ = make_repo(tmp_path)
    feature_sha = _commit_files(root, {"feature.py": "print('f')\n"}, "feat: work")
    rebind(root, behavioural=feature_sha)
    _git(root, "checkout", "main")
    _git(root, "merge", "--ff-only", REVIEW_BRANCH)
    _commit_files(
        root, {"WORKLOG.md": "post-ff reconciliation\n"}, "docs(state): reconcile on main"
    )
    assert vsc.validate_repo_state(root) == []


def test_merge_into_main_with_state_only_reconciliation_passes(tmp_path: Path) -> None:
    """The real acceptance sequence (topology a): product commit on the review
    branch, behavioural rebind, merge commit of the review branch INTO main,
    then a state-only reconciliation commit on main -> pass on the final main
    checkout with the canonical head derived from git."""
    root, _ = make_repo(tmp_path)
    feature_sha = _commit_files(root, {"feature.py": "print('f')\n"}, "feat: work")
    rebind(root, behavioural=feature_sha)
    _git(root, "checkout", "main")
    _git(root, "merge", "--no-ff", "-m", "merge review line into main", REVIEW_BRANCH)
    _commit_files(
        root,
        {"WORKLOG.md": "post-merge reconciliation\n"},
        "docs(state): reconcile on main",
    )
    assert _git(root, "branch", "--show-current") == "main"
    assert vsc.validate_repo_state(root) == []


def test_historical_scope_mentions_do_not_trigger(tmp_path: Path) -> None:
    root, _ = make_repo(
        tmp_path,
        status_body=(
            "All good.\n"
            "\n"
            "## Historical (2026-07-21, pre-merge) — old freeze\n"
            "\n"
            "At the time the release freeze was still active and main is frozen.\n"
            "The AI vertical was then unmerged.\n"
            "No current result is remotely merged.\n"
            "`agent/bl-ai-vertical-002` carried the work.\n"
            "\n"
            "### Historical — deeper detail\n"
            "\n"
            "This does not lift the freeze.\n"
        ),
        next_actions_body=(
            "Nothing contradicting.\n"
            "\n"
            "## Completed since last update (2026-07-22)\n"
            "\n"
            "- the release freeze is still active; main is frozen; the\n"
            "  AI vertical is unmerged; `agent/bl-ai-vertical-002` lives.\n"
        ),
    )
    assert vsc.validate_repo_state(root) == []


def test_annotated_deleted_branch_mentions_do_not_trigger(tmp_path: Path) -> None:
    root, _ = make_repo(
        tmp_path,
        status_body=(
            "- re-acceptance proceeds from closed-PR refs or a recut branch\n"
            "  (`agent/kimi-frontend-integration` and\n"
            "  `agent/acceptance-sidebar-mascot` were both deleted 2026-07-25).\n"
            "\n"
            "PR #11 merged into the deleted\n"
            "`agent/public-release-closure-001`.\n"
        ),
        next_actions_body=(
            "main was fast-forwarded to the reviewed\n"
            "`agent/bl-ai-vertical-002` line; PR #7 marked merged.\n"
        ),
    )
    assert vsc.validate_repo_state(root) == []


def test_historical_block_under_historical_heading_passes(tmp_path: Path) -> None:
    root, _ = make_repo(
        tmp_path,
        status_body=(
            "All good.\n"
            "\n"
            "### Historical containment record (kept as history)\n"
            "\n"
            "- Historical revert notes live here.\n"
        ),
    )
    assert vsc.validate_repo_state(root) == []


# ---------------------------------------------------------------------------
# Fail cases: text rules (freeze-language rules derive from the freeze flag;
# merge/branch/acceptance rules run regardless of it)
# ---------------------------------------------------------------------------


def test_freeze_active_rule_triggers(tmp_path: Path) -> None:
    root, _ = make_repo(
        tmp_path, status_body="The P0 platform release freeze is still active.\n"
    )
    assert "freeze-active" in rule_ids(vsc.validate_repo_state(root))


def test_truthful_active_freeze_passes(tmp_path: Path) -> None:
    """freeze: true + active incident + current text saying the freeze is
    still active is truthful and must pass."""
    root, _ = make_repo(
        tmp_path,
        release_freeze="true",
        incident_status="active",
        status_body=(
            "The P0 platform release freeze is still active and main is frozen.\n"
        ),
    )
    assert vsc.validate_repo_state(root) == []


def test_freeze_lifted_claim_rejected_when_freeze_true(tmp_path: Path) -> None:
    """When the freeze is genuinely active, current-scope text claiming it is
    lifted or thawed is rejected."""
    for index, body in enumerate(
        (
            "The release freeze is lifted.\n",
            "The platform freeze has been thawed.\n",
            "This directive lifted the release freeze.\n",
        )
    ):
        root, _ = make_repo(
            tmp_path / str(index),
            release_freeze="true",
            incident_status="active",
            status_body=body,
        )
        findings = vsc.validate_repo_state(root)
        assert "freeze-lifted-claim" in rule_ids(findings), (body, findings)


def test_merge_acceptance_rules_run_regardless_of_freeze(tmp_path: Path) -> None:
    """An active freeze must not disable the merge/branch/acceptance rules."""
    root, _ = make_repo(
        tmp_path,
        release_freeze="true",
        incident_status="active",
        status_body=(
            "The release freeze is still active.\n"
            "The AI vertical is currently unmerged.\n"
            "No current result is reviewed or merged.\n"
        ),
    )
    findings = rule_ids(vsc.validate_repo_state(root))
    assert "vertical-unmerged" in findings, findings
    assert "acceptance-not-merged" in findings, findings


def test_frozen_main_rule_triggers(tmp_path: Path) -> None:
    for index, body in enumerate(
        ("The frozen `main` line awaits review.\n", "Note: main is frozen.\n")
    ):
        root, _ = make_repo(tmp_path / str(index), status_body=body)
        findings = vsc.validate_repo_state(root)
        assert "frozen-main" in rule_ids(findings), (body, findings)


def test_freeze_not_lifted_rule_triggers(tmp_path: Path) -> None:
    root, _ = make_repo(
        tmp_path,
        next_actions_body="This evidence does not lift the release freeze.\n",
    )
    assert "freeze-not-lifted" in rule_ids(vsc.validate_repo_state(root))


def test_vertical_unmerged_rule_triggers(tmp_path: Path) -> None:
    root, _ = make_repo(
        tmp_path, status_body="The AI vertical is currently unmerged.\n"
    )
    assert "vertical-unmerged" in rule_ids(vsc.validate_repo_state(root))


def test_unmerged_without_vertical_context_does_not_trigger(tmp_path: Path) -> None:
    root, _ = make_repo(
        tmp_path, status_body="PR #8/#10 closed unmerged, archived elsewhere.\n"
    )
    assert "vertical-unmerged" not in rule_ids(vsc.validate_repo_state(root))


def test_previously_unmerged_now_merged_does_not_trigger(tmp_path: Path) -> None:
    root, _ = make_repo(
        tmp_path,
        status_body=(
            "The previously unmerged AI vertical is now merged.\n"
            "The AI vertical, then unmerged, was merged to `main` via PR #7.\n"
        ),
    )
    assert "vertical-unmerged" not in rule_ids(vsc.validate_repo_state(root))


def test_acceptance_not_merged_rule_triggers(tmp_path: Path) -> None:
    root, _ = make_repo(
        tmp_path, status_body="No current result is reviewed or merged.\n"
    )
    assert "acceptance-not-merged" in rule_ids(vsc.validate_repo_state(root))


def test_acceptance_not_merged_rule_is_case_insensitive(tmp_path: Path) -> None:
    root, _ = make_repo(
        tmp_path, status_body="no current result is remotely merged.\n"
    )
    assert "acceptance-not-merged" in rule_ids(vsc.validate_repo_state(root))


def test_stale_deleted_branch_rule_triggers(tmp_path: Path) -> None:
    root, _ = make_repo(
        tmp_path,
        status_body="Work continues on `agent/bl-ai-vertical-002` today.\n",
    )
    assert "stale-deleted-branch" in rule_ids(vsc.validate_repo_state(root))


# ---------------------------------------------------------------------------
# Fail cases: typed head model
# ---------------------------------------------------------------------------


def test_dual_behavioural_head_rejects_state_only_commit(tmp_path: Path) -> None:
    """Regression: a reconciliation commit cannot become behavioural truth."""
    root, _ = make_repo(tmp_path)
    control = _commit_files(
        root,
        {"AGENTS.md": "typed-head control contract\n"},
        "chore(control): update typed-head contract",
    )
    state_only = _commit_files(
        root,
        {"WORKLOG.md": "state-only reconciliation\n"},
        "chore(state): reconcile evidence",
    )
    rebind(root, behavioural=state_only, control=control)
    findings = vsc.validate_repo_state(root)
    assert "behavioural-head-type" in rule_ids(findings), findings


def test_dual_control_head_rejects_state_only_commit(tmp_path: Path) -> None:
    """A state-only reconciliation commit cannot become control truth."""
    root, behavioural = make_repo(tmp_path)
    _commit_files(
        root,
        {"AGENTS.md": "typed-head control contract\n"},
        "chore(control): update typed-head contract",
    )
    state_only = _commit_files(
        root,
        {"WORKLOG.md": "state-only reconciliation\n"},
        "chore(state): reconcile evidence",
    )
    rebind(root, behavioural=behavioural, control=state_only)
    findings = vsc.validate_repo_state(root)
    assert "control-head-type" in rule_ids(findings), findings


def test_new_control_change_requires_control_rebind(tmp_path: Path) -> None:
    """A later typed-head protocol change stales only the control binding."""
    root, behavioural = make_repo(tmp_path)
    control = _commit_files(
        root,
        {"AGENTS.md": "typed-head control contract\n"},
        "chore(control): update typed-head contract",
    )
    rebind(root, behavioural=behavioural, control=control)
    _commit_files(
        root,
        {"PROJECT_DNA.yaml": "typed_head_contract: revised\n"},
        "chore(control): revise typed-head architecture",
    )
    findings = vsc.validate_repo_state(root)
    assert "stale-control-head" in rule_ids(findings), findings
    assert "stale-head" not in rule_ids(findings), findings


def test_workspace_lifecycle_control_allowlist_is_exact() -> None:
    expected = {
        "apps/admin-cli/src/admin_cli/authority.py",
        "apps/admin-cli/src/admin_cli/workspaces.py",
        "config/authority-policy.v1.yaml",
        "config/workspace-lifecycle.v1.yaml",
        "packages/governed-runner/src/governed_runner/authority.py",
        "packages/governed-runner/src/governed_runner/workspaces.py",
        "packages/statebench/src/statebench/devloop.py",
        "schemas/authority-action-receipt.v1.schema.json",
        "schemas/authority-grant.v1.schema.json",
        "schemas/authority-policy.v1.schema.json",
        "schemas/workspace-lease.v1.schema.json",
        "scripts/test_authority_policy.py",
        "scripts/local_closure_gate.py",
        "scripts/test_workspace_authority_integration.py",
        "scripts/validate_authority_policy.py",
        "scripts/test_workspace_lifecycle.py",
        "scripts/validate_workspace_lifecycle.py",
    }
    assert all(vsc._is_control_path(path) for path in expected)
    assert vsc._is_control_path("packages/governed-runner/src/governed_runner/other.py") is False
    assert vsc._is_control_path("schemas/unrelated-runtime.schema.json") is False


def test_control_head_disagreement_fails(tmp_path: Path) -> None:
    root, behavioural = make_repo(tmp_path)
    control = _commit_files(
        root,
        {"AGENTS.md": "typed-head control contract\n"},
        "chore(control): update typed-head contract",
    )
    rebind(root, behavioural=behavioural, control=control)
    _rewrite_project_state(root, {"controlHead": "a" * 40})
    findings = vsc.validate_repo_state(root)
    assert "control-head-disagreement" in rule_ids(findings), findings


def test_control_head_requires_both_state_anchors(tmp_path: Path) -> None:
    root, behavioural = make_repo(tmp_path)
    control = _commit_files(
        root,
        {"AGENTS.md": "typed-head control contract\n"},
        "chore(control): update typed-head contract",
    )
    files = _state_files(behavioural=behavioural, control=control)
    files["STATUS.md"] = re.sub(r"^\*\*Control Head:.*\n", "", files["STATUS.md"], flags=re.MULTILINE)
    _commit_files(root, files, "docs(state): omit one control anchor")
    findings = vsc.validate_repo_state(root)
    assert "head-anchor-missing" in rule_ids(findings), findings


def test_stale_head_product_file_in_delta(tmp_path: Path) -> None:
    """behaviouralHead ancestor + product file in delta -> stale-head fail."""
    root, _ = make_repo(tmp_path)
    _commit_files(root, {"scripts/example.py": "print('product work')\n"}, "feat: code")
    findings = vsc.validate_repo_state(root)
    assert "stale-head" in rule_ids(findings), findings
    assert any(
        "scripts/example.py" in finding.matched
        for finding in findings
        if finding.rule == "stale-head"
    ), findings


def test_docs_release_delta_fails(tmp_path: Path) -> None:
    """docs/release/** is authority-bearing and NOT in the state-only allowlist."""
    root, _ = make_repo(tmp_path)
    _commit_files(
        root,
        {"docs/release/ledger.yaml": "decision: port\n"},
        "docs(release): authority-bearing ledger change",
    )
    findings = vsc.validate_repo_state(root)
    assert "stale-head" in rule_ids(findings), findings
    assert any(
        "docs/release/ledger.yaml" in finding.matched
        for finding in findings
        if finding.rule == "stale-head"
    ), findings


def test_uncommitted_product_change_fails(tmp_path: Path) -> None:
    """Tracked worktree changes since behaviouralHead also fail closed."""
    root, _ = make_repo(tmp_path)
    (root / "app.py").write_text("print('v2')\n", encoding="utf-8")
    findings = vsc.validate_repo_state(root)
    assert "stale-head" in rule_ids(findings), findings


def test_canonical_branch_disagreement_fails(tmp_path: Path) -> None:
    """STATUS.md says main while the state file names another canonical branch."""
    root, _ = make_repo(
        tmp_path,
        branch="other",
        canonical_line=(
            "**Canonical:** branch `main`; the exact canonical head is derived "
            "from Git at validation time\n"
        ),
    )
    findings = vsc.validate_repo_state(root)
    assert "canonical-head-truth" in rule_ids(findings), findings


def test_canonical_branch_must_be_main_fails(tmp_path: Path) -> None:
    """A canonical branch other than main is rejected even when both files agree."""
    root, _ = make_repo(tmp_path, branch="other")
    findings = vsc.validate_repo_state(root)
    assert "canonical-head-truth" in rule_ids(findings), findings


def test_canonical_head_falls_back_to_origin_ref(tmp_path: Path) -> None:
    """Detached-HEAD CI checkouts may lack the local branch ref; the
    remote-tracking ref origin/<branch> must satisfy the canonical check."""
    root, main_sha = make_repo(tmp_path)
    _git(root, "update-ref", "refs/remotes/origin/main", main_sha)
    _git(root, "branch", "-D", "main")
    assert vsc.validate_repo_state(root) == []


def test_canonical_ref_divergence_fails(tmp_path: Path) -> None:
    """When BOTH local main and origin/main exist they must be equal: a stale
    local main must not mask a newer remote (and vice versa)."""
    root, main_sha = make_repo(tmp_path)
    _git(root, "checkout", "main")
    new_main = _commit_files(root, {"app.py": "print('v2')\n"}, "feat: advance main")
    _git(root, "checkout", REVIEW_BRANCH)
    _git(root, "update-ref", "refs/remotes/origin/main", main_sha)
    findings = vsc.validate_repo_state(root)
    assert "canonical-ref-divergence" in rule_ids(findings), findings
    divergence = [
        finding for finding in findings if finding.rule == "canonical-ref-divergence"
    ][0]
    assert new_main in divergence.matched and main_sha in divergence.matched
    assert "fetch" in divergence.fact


def test_persisted_canonical_head_in_state_fails(tmp_path: Path) -> None:
    """A repository.head field persisting an exact canonical SHA as current
    truth is forbidden; only typed historical observations may keep SHAs."""
    root, main_sha = make_repo(tmp_path)
    path = root / "PROJECT_STATE.yaml"
    text = path.read_text(encoding="utf-8")
    text = text.replace(
        "    canonicalBranch: main\n",
        f"    canonicalBranch: main\n    head: {main_sha}\n",
    )
    path.write_text(text, encoding="utf-8")
    findings = vsc.validate_repo_state(root)
    assert "canonical-head-persisted" in rule_ids(findings), findings


def test_old_style_status_canonical_line_fails(tmp_path: Path) -> None:
    """The old '**Canonical:** branch `main` at `<short>` (<sha40>)' form binds
    the branch to an exact SHA as current truth and is rejected."""
    root, _ = make_repo(
        tmp_path,
        canonical_line=(
            f"**Canonical:** branch `main` at `ccccccc` ({'c' * 40})\n"
        ),
    )
    findings = vsc.validate_repo_state(root)
    assert "canonical-head-persisted" in rule_ids(findings), findings


def test_review_head_persisted_in_state_fails(tmp_path: Path) -> None:
    """review.headObserved must not persist an exact review head; the head
    derives from the branch ref at validation time."""
    root, main_sha = make_repo(tmp_path)
    path = root / "PROJECT_STATE.yaml"
    text = path.read_text(encoding="utf-8")
    text = text.replace(
        f"    branch: {REVIEW_BRANCH}\n",
        f"    branch: {REVIEW_BRANCH}\n    headObserved: {main_sha}\n",
    )
    path.write_text(text, encoding="utf-8")
    findings = vsc.validate_repo_state(root)
    assert "review-head-persisted" in rule_ids(findings), findings


def test_review_branch_unresolvable_fails(tmp_path: Path) -> None:
    """The review branch named in state must resolve as a local or remote ref."""
    root, _ = make_repo(tmp_path, review_branch="agent/does-not-exist")
    findings = vsc.validate_repo_state(root)
    assert "review-head" in rule_ids(findings), findings


def test_review_status_closed_unresolvable_branch_passes(tmp_path: Path) -> None:
    """A closed review needs no resolvable branch: canonical main must keep
    validating after the merged review branch is deleted."""
    root, _ = make_repo(
        tmp_path, review_status="closed", review_branch="agent/does-not-exist"
    )
    assert vsc.validate_repo_state(root) == []


def test_review_status_closed_without_branch_passes(tmp_path: Path) -> None:
    """A closed review may omit the branch field entirely."""
    root, _ = make_repo(tmp_path, review_status="closed", review_branch=None)
    assert vsc.validate_repo_state(root) == []


def test_review_status_invalid_fails(tmp_path: Path) -> None:
    """review.status must be active or closed; anything else fails closed."""
    root, _ = make_repo(tmp_path, review_status="archived")
    findings = vsc.validate_repo_state(root)
    assert "review-status" in rule_ids(findings), findings


def test_squash_merge_fails_head_not_ancestor(tmp_path: Path) -> None:
    """A squashed behavioural commit names a non-ancestor ref."""
    root, _ = make_repo(tmp_path)
    _git(root, "checkout", "-b", "feat", "main")
    feature_sha = _commit_files(root, {"feature.py": "print('f')\n"}, "feat: work")
    _git(root, "checkout", REVIEW_BRANCH)
    _git(root, "merge", "--squash", "feat")
    _commit(root, "feat: squashed work")
    rebind(root, behavioural=feature_sha)
    findings = vsc.validate_repo_state(root)
    assert "head-not-ancestor" in rule_ids(findings), findings


def test_rebase_fails_with_actionable_message(tmp_path: Path) -> None:
    """Rewritten ancestry fails closed and tells the operator to rebind."""
    root, _ = make_repo(tmp_path)
    behavioural = _commit_files(root, {"feature.py": "print('f')\n"}, "feat: work")
    rebind(root, behavioural=behavioural)
    _git(root, "checkout", "-b", "base2", "main")
    _commit_files(root, {"base2.py": "print('b')\n"}, "feat: divergent base")
    _git(root, "checkout", REVIEW_BRANCH)
    _git(root, "rebase", "base2")
    findings = vsc.validate_repo_state(root)
    assert "head-not-ancestor" in rule_ids(findings), findings
    assert any(
        "rebind" in finding.fact.lower()
        for finding in findings
        if finding.rule == "head-not-ancestor"
    ), findings


def test_short_sha_in_formal_fields_fails(tmp_path: Path) -> None:
    root, main_sha = make_repo(tmp_path)
    findings = vsc.validate_repo_state(
        _rewrite_project_state(root, {"behaviouralHead": main_sha[:7]})
    )
    assert "sha-format" in rule_ids(findings), findings


def _rewrite_project_state(root: Path, replacements: dict[str, str]) -> Path:
    path = root / "PROJECT_STATE.yaml"
    text = path.read_text(encoding="utf-8")
    for key, value in replacements.items():
        text = re.sub(rf"({key}: )[0-9a-f]{{40}}", rf"\g<1>{value}", text)
    path.write_text(text, encoding="utf-8")
    return root


def test_behavioural_head_disagreement_fails(tmp_path: Path) -> None:
    root, main_sha = make_repo(tmp_path)
    _rewrite_project_state(root, {"behaviouralHead": "a" * 40})
    findings = vsc.validate_repo_state(root)
    assert "head-disagreement" in rule_ids(findings), findings


def test_wrong_reconciliation_policy_fails(tmp_path: Path) -> None:
    root, _ = make_repo(tmp_path, policy="any_descendant")
    findings = vsc.validate_repo_state(root)
    assert "reconciliation-policy" in rule_ids(findings), findings


def test_archive_ref_plan_delta_fails(tmp_path: Path) -> None:
    """Regression: docs/release/ARCHIVE_REF_PLAN.yaml is authority-bearing and
    NOT a state-only doc; changing it after behaviouralHead fails the gate."""
    root, _ = make_repo(tmp_path)
    _commit_files(
        root,
        {"docs/release/ARCHIVE_REF_PLAN.yaml": "plan: durable archive refs\n"},
        "docs(release): archive ref plan",
    )
    findings = vsc.validate_repo_state(root)
    assert "stale-head" in rule_ids(findings), findings
    assert any(
        "docs/release/ARCHIVE_REF_PLAN.yaml" in finding.matched
        for finding in findings
        if finding.rule == "stale-head"
    ), findings


def test_advanced_target_main_fails(tmp_path: Path) -> None:
    """Topology c: an unrelated product commit lands on main after the
    behavioural rebind; the behavioural delta names it and the gate fails."""
    root, _ = make_repo(tmp_path)
    feature_sha = _commit_files(root, {"feature.py": "print('f')\n"}, "feat: work")
    rebind(root, behavioural=feature_sha)
    _git(root, "checkout", "main")
    _git(root, "merge", "--no-ff", "-m", "merge review line into main", REVIEW_BRANCH)
    _commit_files(root, {"hotfix.py": "print('h')\n"}, "feat: unrelated commit on main")
    findings = vsc.validate_repo_state(root)
    assert "stale-head" in rule_ids(findings), findings
    assert any(
        "hotfix.py" in finding.matched
        for finding in findings
        if finding.rule == "stale-head"
    ), findings


def test_squash_merge_into_main_fails_actionable(tmp_path: Path) -> None:
    """Topology d: squash-merging the review line into main breaks ancestry;
    the failure message names the rule and gives explicit rebind instructions."""
    root, _ = make_repo(tmp_path)
    feature_sha = _commit_files(root, {"feature.py": "print('f')\n"}, "feat: work")
    rebind(root, behavioural=feature_sha)
    _git(root, "checkout", "main")
    _git(root, "merge", "--squash", REVIEW_BRANCH)
    _commit(root, "feat: squashed review line")
    findings = vsc.validate_repo_state(root)
    assert "head-not-ancestor" in rule_ids(findings), findings
    assert any(
        "re-record behaviouralhead" in finding.fact.lower()
        for finding in findings
        if finding.rule == "head-not-ancestor"
    ), findings


def test_rebase_merge_into_main_fails_actionable(tmp_path: Path) -> None:
    """Topology d: rebasing the review line onto main and fast-forwarding main
    rewrites the recorded behavioural head; the failure is actionable."""
    root, _ = make_repo(tmp_path)
    feature_sha = _commit_files(root, {"feature.py": "print('f')\n"}, "feat: work")
    rebind(root, behavioural=feature_sha)
    _git(root, "checkout", "main")
    _commit_files(root, {"base2.py": "print('b')\n"}, "feat: divergent base")
    _git(root, "checkout", REVIEW_BRANCH)
    _git(root, "rebase", "main")
    _git(root, "checkout", "main")
    _git(root, "merge", "--ff-only", REVIEW_BRANCH)
    findings = vsc.validate_repo_state(root)
    assert "head-not-ancestor" in rule_ids(findings), findings
    assert any(
        "re-record behaviouralhead" in finding.fact.lower()
        for finding in findings
        if finding.rule == "head-not-ancestor"
    ), findings


# ---------------------------------------------------------------------------
# Fail cases: freeze anchors, structure, fail-closed git
# ---------------------------------------------------------------------------


def test_freeze_incident_open_while_freeze_false_triggers(tmp_path: Path) -> None:
    root, _ = make_repo(tmp_path, incident_status="open")
    findings = vsc.validate_repo_state(root)
    assert "freeze-incident-open" in rule_ids(findings), findings


def test_freeze_incident_lifted_while_freeze_true_triggers(tmp_path: Path) -> None:
    root, _ = make_repo(tmp_path, release_freeze="true", incident_status="lifted")
    findings = vsc.validate_repo_state(root)
    assert "freeze-incident-closed" in rule_ids(findings), findings


def test_freeze_true_with_active_incident_is_consistent(tmp_path: Path) -> None:
    root, _ = make_repo(tmp_path, release_freeze="true", incident_status="active")
    findings = vsc.validate_repo_state(root)
    assert "freeze-incident-open" not in rule_ids(findings)
    assert "freeze-incident-closed" not in rule_ids(findings)


def test_freeze_incident_missing_fails(tmp_path: Path) -> None:
    """Exactly one RELEASE-FREEZE incident record is required; none fails closed."""
    root, _ = make_repo(tmp_path, incident=False)
    findings = vsc.validate_repo_state(root)
    assert "freeze-incident-missing" in rule_ids(findings), findings


def test_freeze_incident_duplicate_fails(tmp_path: Path) -> None:
    """Exactly one RELEASE-FREEZE incident record is required; two fail closed."""
    root, _ = make_repo(tmp_path, duplicate_incident=True)
    findings = vsc.validate_repo_state(root)
    assert "freeze-incident-duplicate" in rule_ids(findings), findings


def test_freeze_incident_unrecognized_status_fails(tmp_path: Path) -> None:
    """An incident status that agrees with neither flag direction fails closed."""
    root, _ = make_repo(tmp_path, incident_status="monitoring")
    findings = vsc.validate_repo_state(root)
    assert "freeze-incident-status" in rule_ids(findings), findings


def test_historical_paragraph_in_current_scope_fails(tmp_path: Path) -> None:
    root, _ = make_repo(
        tmp_path,
        status_body="Historical containment record (kept as history):\n",
    )
    findings = vsc.validate_repo_state(root)
    assert "historical-outside-heading" in rule_ids(findings), findings


def test_section_after_completed_fails(tmp_path: Path) -> None:
    root, _ = make_repo(
        tmp_path,
        next_actions_body=(
            "Nothing contradicting.\n"
            "\n"
            "## Completed since last update (2026-07-22)\n"
            "\n"
            "- historical notes.\n"
            "\n"
            "## Late section\n"
            "\n"
            "Out of place.\n"
        ),
    )
    findings = vsc.validate_repo_state(root)
    assert "completed-not-final" in rule_ids(findings), findings


def test_git_failure_fails_closed(tmp_path: Path) -> None:
    root = tmp_path / "repo"
    root.mkdir()
    for relative, content in _state_files(
        behavioural="c" * 40, canonical_observed="c" * 40
    ).items():
        (root / relative).write_text(content, encoding="utf-8")
    findings = vsc.validate_repo_state(root)
    assert "head-unverifiable" in rule_ids(findings), findings


def test_git_timeout_fails_closed(tmp_path: Path) -> None:
    root, _ = make_repo(tmp_path)
    with mock.patch(
        "validate_state_consistency.subprocess.run",
        side_effect=vsc.subprocess.TimeoutExpired(cmd="git", timeout=30),
    ):
        findings = vsc.validate_repo_state(root)
    assert "head-unverifiable" in rule_ids(findings), findings


def test_cli_exit_codes(tmp_path: Path) -> None:
    root, _ = make_repo(tmp_path / "clean")
    ok = subprocess.run(
        [sys.executable, str(VALIDATOR), str(root)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert ok.returncode == 0, ok.stdout + ok.stderr

    bad, _ = make_repo(tmp_path / "bad", status_body="main is frozen.\n")
    failed = subprocess.run(
        [sys.executable, str(VALIDATOR), str(bad)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert failed.returncode == 1
    assert "frozen-main" in failed.stdout


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-q"]))
