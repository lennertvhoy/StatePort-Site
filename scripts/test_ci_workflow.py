#!/usr/bin/env python3
"""Regression checks for the current StatePort CI closure boundaries."""

from __future__ import annotations

from pathlib import Path
import tomllib

import yaml


ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github" / "workflows" / "validate.yml"
PREFLIGHT_WORKFLOW = ROOT / ".github" / "workflows" / "ai-vertical-preflight.yml"
ACTIONLINT_CONFIG = ROOT / ".github" / "actionlint.yaml"
GITLEAKS_CONFIG = ROOT / ".gitleaks.toml"
CHECKOUT_V7_NODE24 = "actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1"


def _workflow() -> dict[str, object]:
    data = yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))
    assert isinstance(data, dict)
    return data


def test_actionlint_declares_the_exact_private_runner_label() -> None:
    data = yaml.safe_load(ACTIONLINT_CONFIG.read_text(encoding="utf-8"))
    assert data == {"self-hosted-runner": {"labels": ["stateport"]}}


def test_workflows_pin_checkout_v7_node24_exactly() -> None:
    observed: list[str] = []
    for path in (WORKFLOW, PREFLIGHT_WORKFLOW):
        workflow = yaml.safe_load(path.read_text(encoding="utf-8"))
        assert isinstance(workflow, dict)
        jobs = workflow.get("jobs")
        assert isinstance(jobs, dict)
        for job in jobs.values():
            assert isinstance(job, dict)
            steps = job.get("steps")
            assert isinstance(steps, list)
            for step in steps:
                assert isinstance(step, dict)
                uses = step.get("uses")
                if isinstance(uses, str) and uses.startswith("actions/checkout@"):
                    observed.append(uses)
    assert observed
    assert set(observed) == {CHECKOUT_V7_NODE24}


def _commands(job: dict[str, object]) -> tuple[str, ...]:
    steps = job.get("steps")
    assert isinstance(steps, list)
    commands: list[str] = []
    for step in steps:
        assert isinstance(step, dict)
        command = step.get("run")
        if isinstance(command, str):
            commands.append(command)
    return tuple(commands)


def test_ci_runs_for_canonical_and_approved_private_integration_prs() -> None:
    workflow = _workflow()
    # PyYAML's YAML 1.1 resolver parses the unquoted GitHub key `on` as True.
    triggers = workflow.get("on", workflow.get(True))
    assert triggers == {
        "push": {"branches": ["main"]},
        "pull_request": {"branches": ["main", "agent/alpha-public-legal-boundary-001"]},
    }


def test_ci_uses_complete_backend_suite_and_repository_gates() -> None:
    jobs = _workflow()["jobs"]
    assert isinstance(jobs, dict)
    backend = jobs["backend"]
    assert isinstance(backend, dict)
    commands = _commands(backend)

    for expected in (
        "python3 -m venv .venv",
        "--require-hashes -r requirements/dev-test.txt",
        ".venv/bin/python scripts/validate_repo.py",
        ".venv/bin/python scripts/statedd_validate_schema.py",
        ".venv/bin/python scripts/validate_application_experience.py",
        ".venv/bin/python -m compileall -q apps packages scripts",
        'test "$(.venv/bin/ruff --version)" = "ruff 0.16.0"',
        ".venv/bin/ruff check apps packages scripts",
        ".venv/bin/python -m pytest -q",
    ):
        assert any(expected in command for command in commands), f"missing: {expected}"

    assert not any(command.startswith("python3 scripts/test_") for command in commands)


def test_ci_runs_locked_frontend_build_unit_dependency_and_browser_gates() -> None:
    jobs = _workflow()["jobs"]
    assert isinstance(jobs, dict)
    web = jobs["web"]
    assert isinstance(web, dict)
    commands = _commands(web)

    for expected in (
        "npm ci --ignore-scripts",
        "npm run typecheck",
        "npm run lint",
        "npm run test",
        "npm run build",
        "npm run check:bundle",
        "npm run test:build-isolation",
        "npm run check:dependencies",
        "python3 ../../scripts/validate_web_dependency_audit.py",
        "npx playwright install chromium",
        "npm run test:e2e",
    ):
        assert expected in commands

    e2e_port_selection = next(command for command in commands if "STATEPORT_E2E_PORT=" in command)
    # The browser service must not compete for the conventional developer
    # preview port on a shared runner. Keep its deterministic range disjoint
    # from the Compose range below.
    assert "30000 +" in e2e_port_selection
    assert "% 10000" in e2e_port_selection

    defaults = web["defaults"]
    assert isinstance(defaults, dict)
    run_defaults = defaults["run"]
    assert isinstance(run_defaults, dict)
    assert run_defaults["working-directory"] == "apps/web"


def test_self_hosted_jobs_reject_untrusted_fork_code_and_keep_secret_scan() -> None:
    jobs = _workflow()["jobs"]
    assert isinstance(jobs, dict)
    guard = (
        "github.event_name == 'push' || "
        "github.event.pull_request.head.repo.full_name == github.repository"
    )
    for job_name in (
        "backend",
        "web",
        "canonical-source-browser",
        "security",
        "package-validation",
        "compose-integration",
    ):
        job = jobs[job_name]
        assert isinstance(job, dict)
        assert job["runs-on"] == ["self-hosted", "linux", "x64", "stateport"]
        assert job["if"] == guard

    security = jobs["security"]
    assert isinstance(security, dict)
    assert "./scripts/gitleaks_scan.sh" in _commands(security)


def test_secret_scan_uses_an_exact_tree_and_keeps_staged_review_explicit() -> None:
    script = (ROOT / "scripts" / "gitleaks_scan.sh").read_text(encoding="utf-8")
    assert 'MODE="committed"' in script
    assert 'git -C "$ROOT" archive --format=tar HEAD' in script
    assert 'git -C "$ROOT" checkout-index --all' in script
    assert '"--staged"' in script
    assert '"--working-tree"' in script
    assert '--source="$SCAN_ROOT"' in script
    assert "--no-git" in script


def test_ci_compose_integration_builds_and_validates_delivered_product() -> None:
    jobs = _workflow()["jobs"]
    assert isinstance(jobs, dict)
    compose = jobs["compose-integration"]
    assert isinstance(compose, dict)
    assert compose["timeout-minutes"] == 30
    commands = _commands(compose)

    for expected in (
        "podman compose version",
        "podman-compose",
        "docker compose version",
        "git rev-parse --verify HEAD",
        "STATEPORT_BUILD_SOURCE_COMMIT",
        "STATEPORT_BUILD_SOURCE_TREE",
        "STATEPORT_BUILD_VERSION",
        "STATEPORT_BUILD_CREATED",
        "STATEPORT_BUILD_ADAPTER",
        "$COMPOSE build",
        "$COMPOSE up -d",
        "wait_web_healthy",
        "wait_internal_healthy stateport-api 8790 /readyz",
        "wait_internal_healthy stateport-worker 8791 /readyz",
        "STATEPORT_WEB_PORT",
        "$COMPOSE exec -T stateport-api",
        "$COMPOSE exec -T stateport-worker",
        "v1/capabilities",
        "$COMPOSE images",
        "$COMPOSE down -v --remove-orphans",
    ):
        assert any(expected in command for command in commands), f"missing: {expected}"

    compose_port_selection = next(
        command for command in commands if "COMPOSE_PROJECT_NAME=stateport-ci-" in command
    )
    # Only the authenticated same-origin web endpoint is host-published.
    assert "45000 +" in compose_port_selection
    assert "% 10000" in compose_port_selection
    assert "STATEPORT_WEB_PORT=${BASE_PORT}" in compose_port_selection
    assert "STATEPORT_API_PORT" not in compose_port_selection
    assert "STATEPORT_WORKER_PORT" not in compose_port_selection

    provenance = next(
        command
        for command in commands
        if 'SOURCE_COMMIT="$(git rev-parse --verify HEAD)"' in command
    )
    assert 'SOURCE_TREE="$(git rev-parse --verify "${SOURCE_COMMIT}^{tree}")"' in provenance
    assert 'SOURCE_EPOCH="$(git show -s --format=%ct "$SOURCE_COMMIT")"' in provenance
    assert "STATEPORT_BUILD_VERSION=0.0.0-ci." in provenance
    assert "STATEPORT_BUILD_CREATED=${SOURCE_CREATED}" in provenance
    assert "STATEPORT_BUILD_ADAPTER=github-actions-compose" in provenance
    assert "git rev-parse --verify 'HEAD^{tree}'" not in provenance

    health_contracts = "\n".join(
        command
        for command in commands
        if "API health response valid" in command
        or "Worker health response valid" in command
        or "API capabilities endpoint valid" in command
    )
    for expected in (
        "data.get('ok') is True",
        "result = data.get('result')",
        "result.get('status') == 'standby'",
        "result.get('executionEnabled') is False",
        "'operations' in result",
    ):
        assert expected in health_contracts

    assert any("failure()" in step.get("if", "") for step in compose["steps"])
    assert any("always()" in step.get("if", "") for step in compose["steps"])


def test_ci_package_validation_checks_dockerfiles_and_install_script() -> None:
    jobs = _workflow()["jobs"]
    assert isinstance(jobs, dict)
    pkg = jobs["package-validation"]
    assert isinstance(pkg, dict)
    assert pkg["timeout-minutes"] == 15
    commands = _commands(pkg)

    for expected in (
        "bash -n scripts/install.sh",
        "apps/${svc}/Dockerfile",
        "python3 scripts/validate_dockerfile_copy_sources.py",
        "test_compose_shape.py",
    ):
        assert any(expected in command for command in commands), f"missing: {expected}"

    assert not any("sed -n 's/.*COPY" in command for command in commands)


def test_ci_canonical_source_gate_uses_exact_public_fixture_and_live_browser() -> None:
    jobs = _workflow()["jobs"]
    assert isinstance(jobs, dict)
    canonical = jobs["canonical-source-browser"]
    assert isinstance(canonical, dict)
    commands = _commands(canonical)
    acceptance = next(
        command for command in commands if "npm run test:canonical-source-browser" in command
    )

    assert "mktemp -d" in acceptance
    assert "https://github.com/lennertvhoy/StudyDD_Template.git" in acceptance
    assert 'STATEPORT_BROWSER_STUDYDD_REPOSITORY="$source_root/repository"' in acceptance
    assert "STATEPORT_BROWSER_ARTIFACT_ROOT=" in acceptance
    assert "npm run test:canonical-source-browser" in acceptance
    assert "npm run test:live-core-browser" in commands
    assert "npm ci --ignore-scripts" in commands
    assert "npx playwright install chromium" in commands


def test_gitleaks_allowlist_is_exact_and_keeps_default_rules() -> None:
    config = tomllib.loads(GITLEAKS_CONFIG.read_text(encoding="utf-8"))
    assert config["extend"] == {"useDefault": True}
    assert config["allowlist"] == {
        "description": (
            "Ignore one exact keyboard chord and generated Vite copies of scanned source."
        ),
        "regexTarget": "match",
        "regexes": [r"""defaultKeys\s*:\s*['"]mod\+shift\+enter['"]"""],
        "paths": [r"apps/web/dist/", r"apps/web/dist-demo/"],
    }
