#!/usr/bin/env python3
"""Focused tests for the local closure and human-ready evidence gates."""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(ROOT / "scripts"))

from build_human_ready_gate import (  # noqa: E402
    REQUIRED_CHECKS,
    HumanReadyGateError,
    assemble_human_ready_gate,
)
from local_closure_gate import CommandSpec, default_commands, run_gate  # noqa: E402


COMMIT = "a" * 40
TREE = "b" * 40
DIGEST = "c" * 64


def _repo(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    repo.mkdir(parents=True)
    subprocess.run(["git", "init", "-q", str(repo)], check=True)
    subprocess.run(["git", "-C", str(repo), "config", "user.name", "Closure Test"], check=True)
    subprocess.run(["git", "-C", str(repo), "config", "user.email", "closure@example.invalid"], check=True)
    (repo / "README.md").write_text("fixture\n", encoding="utf-8")
    config = repo / "config"
    config.mkdir()
    (config / "workspace-lifecycle.v1.yaml").write_text(
        (ROOT / "config" / "workspace-lifecycle.v1.yaml").read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    subprocess.run(["git", "-C", str(repo), "add", "README.md", "config/workspace-lifecycle.v1.yaml"], check=True)
    subprocess.run(["git", "-C", str(repo), "commit", "-qm", "fixture"], check=True)
    return repo


def test_injected_tiny_gate_passes_and_sanitizes_logs(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    output = tmp_path / "evidence"
    source = tmp_path / "public-source"
    secret = "SENTINEL_" + "CLOSURE_" + "VALUE_987654321"
    code = (
        "import os; from pathlib import Path; "
        "artifacts=Path(os.environ['STATEPORT_BROWSER_ARTIFACT_ROOT']); "
        "artifacts.mkdir(parents=True); "
        f"(artifacts/'results.json').write_text(os.getcwd() + {secret!r}); "
        "(artifacts/'trace.zip').write_bytes(b'raw trace'); "
        "(artifacts/'screen.png').write_bytes(b'public-safe image'); "
        "print(os.getcwd()); "
        "print(os.environ['STATEPORT_BROWSER_STUDYDD_REPOSITORY']); "
        f"print('token=' + {secret!r}); "
        "print('test-token-env=' + str('TEST_TOKEN' in os.environ))"
    )
    environment = dict(os.environ)
    environment.update({"STATEPORT_BROWSER_STUDYDD_REPOSITORY": str(source), "TEST_TOKEN": secret})
    summary = run_gate(
        repo_root=repo,
        output_dir=output,
        environment_label="fresh",
        commands=(
            CommandSpec(
                "tiny",
                (sys.executable, "-c", code),
                timeout_seconds=10,
                required_environment=("STATEPORT_BROWSER_STUDYDD_REPOSITORY",),
                browser_artifacts=True,
            ),
        ),
        environment=environment,
        workspace_state_root=tmp_path / "workspace-state",
    )
    assert summary["passed"] is True
    record = summary["commands"][0]
    log = (output / record["log"]["path"]).read_text(encoding="utf-8")
    assert str(repo) not in log and str(source) not in log and secret not in log
    assert "[REPO]" in log and "[SOURCE_REPOSITORY]" in log and "[REDACTED]" in log
    assert "test-token-env=False" in log
    assert hashlib.sha256(log.encode()).hexdigest() == record["log"]["sha256"]
    results = (output / "browser" / "tiny" / "results.json").read_text(encoding="utf-8")
    assert str(repo) not in results and secret not in results
    assert not (output / "browser" / "tiny" / "trace.zip").exists()
    assert record["artifacts"]["removedUnsafeArtifacts"] == ["trace.zip"]
    assert {item["path"] for item in record["artifacts"]["files"]} == {
        "browser/tiny/results.json", "browser/tiny/screen.png",
    }
    stored = json.loads((output / "local_closure_gate.json").read_text(encoding="utf-8"))
    assert stored["remoteCI"]["verified"] is False
    assert stored["privacy"]["environmentValuesRecorded"] is False
    assert stored["privacy"]["sensitiveEnvironmentPassedToCommands"] is False


def test_gate_fails_closed_for_missing_environment_without_running(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    summary = run_gate(
        repo_root=repo,
        output_dir=tmp_path / "evidence",
        environment_label="active",
        commands=(CommandSpec("never", (sys.executable, "-c", "raise SystemExit(99)"), required_environment=("MISSING_GATE_VALUE",)),),
        environment={"PATH": os.environ["PATH"]},
        workspace_state_root=tmp_path / "workspace-state",
    )
    assert summary["passed"] is False
    assert summary["commands"] == []
    assert summary["requiredEnvironment"] == {"MISSING_GATE_VALUE": "missing"}
    assert "required environment variable unavailable: MISSING_GATE_VALUE" in summary["blockers"]


def test_gate_rejects_command_labels_that_could_escape_evidence_paths(
    tmp_path: Path,
) -> None:
    repo = _repo(tmp_path)
    with pytest.raises(ValueError, match="command labels"):
        run_gate(
            repo_root=repo,
            output_dir=tmp_path / "evidence",
            environment_label="active",
            commands=(
                CommandSpec(
                    "../escape",
                    (sys.executable, "-c", "raise SystemExit(99)"),
                    browser_artifacts=True,
                ),
            ),
            workspace_state_root=tmp_path / "workspace-state",
        )


def test_authoritative_plan_covers_every_local_closure_boundary() -> None:
    commands = default_commands(75)
    labels = {item.label for item in commands}
    assert labels == {
        "complete_pytest",
        "statespec_schema_validation",
        "repository_validation",
        "python_compileall",
        "functionality_preservation_validation",
        "web_dependency_install",
        "web_typecheck",
        "web_lint",
        "web_unit_tests",
        "web_build",
        "web_build_isolation",
        "web_dependency_tree",
        "web_dependency_audit",
        "web_mock_browser_acceptance",
        "live_core_browser_acceptance",
        "canonical_source_browser_acceptance",
        "repository_gitleaks",
        "git_diff_check",
        "git_status_porcelain",
        "git_object_integrity",
    }
    assert all(item.timeout_seconds <= 75 for item in commands)
    browser = next(item for item in commands if item.label == "canonical_source_browser_acceptance")
    assert browser.required_environment == ("STATEPORT_BROWSER_STUDYDD_REPOSITORY",)
    assert browser.browser_artifacts is True
    assert next(
        item for item in commands if item.label == "live_core_browser_acceptance"
    ).browser_artifacts is True


def test_mock_browser_suite_honors_the_isolated_evidence_root() -> None:
    config = (ROOT / "apps" / "web" / "playwright.config.ts").read_text(
        encoding="utf-8"
    )
    screenshots = (
        ROOT / "apps" / "web" / "tests" / "e2e" / "screenshots.spec.ts"
    ).read_text(encoding="utf-8")
    assert "STATEPORT_BROWSER_ARTIFACT_ROOT" in config
    assert "path.join(artifactRoot, 'test-results')" in config
    assert "path.join(artifactRoot, 'results.json')" in config
    assert "STATEPORT_BROWSER_ARTIFACT_ROOT" in screenshots
    assert "'screenshots'" in screenshots


def test_gate_records_failure_timeout_and_dirty_worktree(tmp_path: Path) -> None:
    failure_repo = _repo(tmp_path / "failure")
    failed = run_gate(
        repo_root=failure_repo,
        output_dir=tmp_path / "failure-evidence",
        environment_label="active",
        commands=(CommandSpec("failure", (sys.executable, "-c", "raise SystemExit(7)"), timeout_seconds=10),),
        workspace_state_root=tmp_path / "failure-workspace-state",
    )
    assert failed["passed"] is False
    assert failed["commands"][0]["exitCode"] == 7

    timeout_repo = _repo(tmp_path / "timeout")
    timed = run_gate(
        repo_root=timeout_repo,
        output_dir=tmp_path / "timeout-evidence",
        environment_label="fresh",
        commands=(CommandSpec("timeout", (sys.executable, "-c", "import time; time.sleep(5)"), timeout_seconds=1),),
        workspace_state_root=tmp_path / "timeout-workspace-state",
    )
    assert timed["commands"][0]["timedOut"] is True
    assert timed["passed"] is False

    dirty_repo = _repo(tmp_path / "dirty")
    (dirty_repo / "dirty.txt").write_text("dirty\n", encoding="utf-8")
    dirty = run_gate(
        repo_root=dirty_repo,
        output_dir=tmp_path / "dirty-evidence",
        environment_label="active",
        commands=(CommandSpec("never", (sys.executable, "-c", "raise SystemExit(99)")),),
        workspace_state_root=tmp_path / "dirty-workspace-state",
    )
    assert dirty["commands"] == []
    assert dirty["repository"]["cleanBefore"] is False
    assert "Git worktree was not clean before the gate" in dirty["blockers"]


def _evidence() -> dict[str, object]:
    return {
        "functionalCommit": COMMIT,
        "functionalTree": TREE,
        "checks": {
            name: {
                "passed": True,
                "evidence": [{"artifact": f"validation/{name}.json", "sha256": DIGEST}],
            }
            for name in REQUIRED_CHECKS
        },
    }


def test_human_ready_gate_defaults_missing_checks_to_false() -> None:
    gate = assemble_human_ready_gate(
        {"functionalCommit": COMMIT, "functionalTree": TREE},
        generated_at="2026-07-15T00:00:00Z",
    )
    assert gate["readyForHumanAcceptance"] is False
    assert gate["humanSession"]["permitted"] is False
    assert gate["blockers"] == list(REQUIRED_CHECKS)
    assert all(not value["passed"] for value in gate["checks"].values())


def test_human_ready_gate_requires_hashed_evidence_and_all_checks() -> None:
    evidence = _evidence()
    gate = assemble_human_ready_gate(evidence, generated_at="2026-07-15T00:00:00Z")
    assert gate["readyForHumanAcceptance"] is True
    assert gate["humanSession"] == {
        "permitted": True,
        "maximumMinutes": 20,
        "scope": "subjective clarity, control, trust, and acceptance only",
    }
    evidence["checks"]["fullSuitePassed"] = {"passed": True, "evidence": []}
    with pytest.raises(HumanReadyGateError, match="cannot pass without hashed evidence"):
        assemble_human_ready_gate(evidence)


@pytest.mark.parametrize("artifact", ["/absolute.json", "../escape.json", "a/../../escape.json", "a\\b.json"])
def test_human_ready_gate_rejects_unsafe_evidence_paths(artifact: str) -> None:
    evidence = _evidence()
    evidence["checks"]["fullSuitePassed"]["evidence"][0]["artifact"] = artifact
    with pytest.raises(HumanReadyGateError, match="artifact"):
        assemble_human_ready_gate(evidence)
