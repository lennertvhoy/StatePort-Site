#!/usr/bin/env python3
"""Run StatePort's fail-closed, reproducible local closure gate.

The runner deliberately records only sanitized local evidence.  It is not a
replacement for remote CI and never records environment variable values.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import signal
import subprocess
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Mapping, Sequence


ROOT = Path(__file__).resolve().parents[1]
GOVERNED_RUNNER_SRC = ROOT / "packages" / "governed-runner" / "src"
if str(GOVERNED_RUNNER_SRC) not in sys.path:
    sys.path.insert(0, str(GOVERNED_RUNNER_SRC))

from governed_runner.workspaces import (  # noqa: E402
    WorkspaceLifecycleError,
    WorkspaceLifecycleManager,
)
FORMAT_VERSION = "stateport.local-closure-gate/v1"
ENVIRONMENT_LABELS = ("active", "fresh", "container")
SOURCE_REPOSITORY_ENV = "STATEPORT_BROWSER_STUDYDD_REPOSITORY"
_SENSITIVE_ENV_NAME = re.compile(
    r"(?:api[_-]?key|auth|bearer|credential|password|secret|token)", re.IGNORECASE
)
_SENSITIVE_ASSIGNMENT = re.compile(
    r"(?i)\b(api[_-]?key|authorization|bearer|credential|password|secret|token)"
    r"\s*[:=]\s*([^\s,;]+)"
)
_URI_CREDENTIALS = re.compile(r"([a-z][a-z0-9+.-]*://)[^/@\s:]+(?::[^/@\s]*)?@", re.IGNORECASE)
_HOME_PATH = re.compile(r"(?<![A-Za-z0-9._-])/home/[^/\s]+")
_SAFE_COMMAND_LABEL = re.compile(r"^[A-Za-z0-9_.-]+$")


@dataclass(frozen=True)
class CommandSpec:
    """One argv-only command in the closure plan."""

    label: str
    argv: tuple[str, ...]
    cwd: str = "."
    timeout_seconds: int = 120
    required_environment: tuple[str, ...] = ()
    browser_artifacts: bool = False


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _git(repo_root: Path, *args: str) -> str:
    completed = subprocess.run(
        ["git", "-C", str(repo_root), *args],
        check=False,
        capture_output=True,
        text=True,
        timeout=30,
    )
    if completed.returncode:
        raise RuntimeError(f"git {' '.join(args)} failed")
    return completed.stdout.strip()


def _redaction_values(
    repo_root: Path,
    output_dir: Path,
    environment: Mapping[str, str],
) -> list[tuple[str, str]]:
    values: list[tuple[str, str]] = [
        (str(repo_root.resolve()), "[REPO]"),
        (str(output_dir.resolve()), "[OUTPUT]"),
        (str(Path.home().resolve()), "[HOME]"),
    ]
    source = environment.get(SOURCE_REPOSITORY_ENV, "")
    if source:
        values.append((source, "[SOURCE_REPOSITORY]"))
    for name, value in environment.items():
        if value and len(value) >= 4 and _SENSITIVE_ENV_NAME.search(name):
            values.append((value, f"[{name}_REDACTED]"))
    return sorted(set(values), key=lambda item: len(item[0]), reverse=True)


def sanitize_text(text: str, redactions: Sequence[tuple[str, str]]) -> str:
    """Remove local paths and common credential shapes from captured output."""

    sanitized = text
    for value, replacement in redactions:
        if value:
            sanitized = sanitized.replace(value, replacement)
    sanitized = _HOME_PATH.sub("[HOME]", sanitized)
    sanitized = _URI_CREDENTIALS.sub(r"\1[REDACTED]@", sanitized)
    sanitized = _SENSITIVE_ASSIGNMENT.sub(lambda match: f"{match.group(1)}=[REDACTED]", sanitized)
    return sanitized


def _execution_environment(environment: Mapping[str, str]) -> dict[str, str]:
    """Drop credentials and host overrides before running validation tools."""

    safe: dict[str, str] = {}
    for name, value in environment.items():
        if name == SOURCE_REPOSITORY_ENV:
            safe[name] = value
            continue
        if _SENSITIVE_ENV_NAME.search(name):
            continue
        if name in {"PYTHONHOME", "PYTHONPATH", "PYTHONSTARTUP"}:
            continue
        if name.startswith(("GIT_", "SSH_", "STATEPORT_")):
            continue
        safe[name] = value
    return safe


def default_commands(max_timeout_seconds: int) -> tuple[CommandSpec, ...]:
    """Return the repository-authoritative local closure command plan."""

    def bounded(requested: int) -> int:
        return min(requested, max_timeout_seconds)

    python = "python3"
    return (
        CommandSpec("complete_pytest", (python, "-m", "pytest", "-q"), timeout_seconds=bounded(900)),
        CommandSpec("statespec_schema_validation", (python, "scripts/statedd_validate_schema.py"), timeout_seconds=bounded(180)),
        CommandSpec("repository_validation", (python, "scripts/validate_repo.py"), timeout_seconds=bounded(240)),
        CommandSpec(
            "python_compileall",
            (python, "-m", "compileall", "-q", "apps", "packages", "scripts"),
            timeout_seconds=bounded(240),
        ),
        CommandSpec(
            "functionality_preservation_validation",
            (python, "scripts/validate_application_experience.py"),
            timeout_seconds=bounded(180),
        ),
        CommandSpec(
            "web_dependency_install",
            ("npm", "ci", "--ignore-scripts"),
            cwd="apps/web",
            timeout_seconds=bounded(360),
        ),
        CommandSpec("web_typecheck", ("npm", "run", "typecheck"), cwd="apps/web", timeout_seconds=bounded(180)),
        CommandSpec("web_lint", ("npm", "run", "lint"), cwd="apps/web", timeout_seconds=bounded(180)),
        CommandSpec("web_unit_tests", ("npm", "run", "test"), cwd="apps/web", timeout_seconds=bounded(360)),
        CommandSpec(
            "web_build",
            ("npm", "run", "build"),
            cwd="apps/web",
            timeout_seconds=bounded(240),
        ),
        CommandSpec(
            "web_build_isolation",
            ("npm", "run", "test:build-isolation"),
            cwd="apps/web",
            timeout_seconds=bounded(240),
        ),
        CommandSpec(
            "web_dependency_tree",
            ("npm", "run", "check:dependencies"),
            cwd="apps/web",
            timeout_seconds=bounded(180),
        ),
        CommandSpec(
            "web_dependency_audit",
            ("python3", "../../scripts/validate_web_dependency_audit.py"),
            cwd="apps/web",
            timeout_seconds=bounded(240),
        ),
        CommandSpec(
            "web_mock_browser_acceptance",
            ("npm", "run", "test:e2e"),
            cwd="apps/web",
            timeout_seconds=bounded(720),
            browser_artifacts=True,
        ),
        CommandSpec(
            "live_core_browser_acceptance",
            ("npm", "run", "test:live-core-browser"),
            cwd="apps/web",
            timeout_seconds=bounded(720),
            browser_artifacts=True,
        ),
        CommandSpec(
            "canonical_source_browser_acceptance",
            ("npm", "run", "test:canonical-source-browser"),
            cwd="apps/web",
            timeout_seconds=bounded(720),
            required_environment=(SOURCE_REPOSITORY_ENV,),
            browser_artifacts=True,
        ),
        CommandSpec(
            "repository_gitleaks",
            ("bash", "scripts/gitleaks_scan.sh"),
            timeout_seconds=bounded(360),
        ),
        CommandSpec("git_diff_check", ("git", "diff", "--check"), timeout_seconds=bounded(60)),
        CommandSpec(
            "git_status_porcelain",
            ("git", "status", "--porcelain=v2", "--untracked-files=all"),
            timeout_seconds=bounded(60),
        ),
        CommandSpec("git_object_integrity", ("git", "fsck", "--full"), timeout_seconds=bounded(360)),
    )


def _preflight(
    commands: Sequence[CommandSpec], environment: Mapping[str, str]
) -> list[str]:
    blockers: list[str] = []
    executables = sorted({spec.argv[0] for spec in commands if spec.argv})
    for executable in executables:
        if shutil.which(executable) is None:
            blockers.append(f"required executable unavailable: {executable}")
    required_environment = sorted(
        {name for spec in commands for name in spec.required_environment}
    )
    for name in required_environment:
        if not environment.get(name):
            blockers.append(f"required environment variable unavailable: {name}")
    if any(spec.label == "repository_gitleaks" for spec in commands):
        if not any(shutil.which(name) for name in ("gitleaks", "podman", "docker")):
            blockers.append("gitleaks requires gitleaks, podman, or docker")
    return blockers


def _version(
    argv: Sequence[str],
    cwd: Path,
    redactions: Sequence[tuple[str, str]],
    environment: Mapping[str, str],
) -> str:
    try:
        completed = subprocess.run(
            list(argv), cwd=cwd, env=dict(environment), check=False, capture_output=True, text=True, timeout=30
        )
    except (OSError, subprocess.TimeoutExpired):
        return "unavailable"
    output = (completed.stdout or completed.stderr).strip().splitlines()
    if completed.returncode or not output:
        return "unavailable"
    return sanitize_text(output[0], redactions)[:240]


def _tool_versions(
    repo_root: Path,
    redactions: Sequence[tuple[str, str]],
    environment: Mapping[str, str],
) -> dict[str, str]:
    versions = {
        "python": _version(("python3", "--version"), repo_root, redactions, environment),
        "pytest": _version(("python3", "-m", "pytest", "--version"), repo_root, redactions, environment),
        "git": _version(("git", "--version"), repo_root, redactions, environment),
        "node": _version(("node", "--version"), repo_root, redactions, environment),
        "npm": _version(("npm", "--version"), repo_root, redactions, environment),
    }
    web_root = repo_root / "apps" / "web"
    playwright = web_root / "node_modules" / ".bin" / "playwright"
    versions["playwright"] = _version((str(playwright), "--version"), web_root, redactions, environment) if playwright.is_file() else "unavailable"
    if shutil.which("gitleaks"):
        versions["gitleaks"] = _version(("gitleaks", "version"), repo_root, redactions, environment)
    elif shutil.which("podman"):
        versions["gitleaksRunner"] = _version(("podman", "--version"), repo_root, redactions, environment)
        versions["gitleaksImage"] = "zricethezav/gitleaks:v8.24.2"
    elif shutil.which("docker"):
        versions["gitleaksRunner"] = _version(("docker", "--version"), repo_root, redactions, environment)
        versions["gitleaksImage"] = "zricethezav/gitleaks:v8.24.2"
    else:
        versions["gitleaks"] = "unavailable"
    return versions


def _terminate(process: subprocess.Popen[bytes]) -> None:
    try:
        os.killpg(process.pid, signal.SIGTERM)
        process.wait(timeout=5)
    except (ProcessLookupError, subprocess.TimeoutExpired):
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        process.wait()


def _container_detected(environment: Mapping[str, str]) -> bool:
    return bool(
        environment.get("container")
        or Path("/.dockerenv").is_file()
        or Path("/run/.containerenv").is_file()
    )


def _sanitize_browser_artifacts(
    root: Path,
    redactions: Sequence[tuple[str, str]],
    *,
    artifact_prefix: str,
) -> dict[str, object]:
    """Sanitize text artifacts, hash screenshots, and discard raw traces."""

    if not root.is_dir():
        return {"files": [], "removedUnsafeArtifacts": []}
    text_suffixes = {".json", ".jsonl", ".log", ".md", ".txt", ".xml"}
    image_suffixes = {".jpg", ".jpeg", ".png", ".webp"}
    files: list[dict[str, str]] = []
    removed: list[str] = []
    for path in sorted(root.rglob("*")):
        if path.is_dir():
            continue
        relative = path.relative_to(root).as_posix()
        if path.is_symlink():
            path.unlink()
            removed.append(relative)
            continue
        suffix = path.suffix.lower()
        if suffix in text_suffixes:
            content = path.read_text(encoding="utf-8", errors="replace")
            path.write_text(sanitize_text(content, redactions), encoding="utf-8")
            path.chmod(0o600)
        elif suffix not in image_suffixes:
            path.unlink()
            removed.append(relative)
            continue
        files.append({"path": f"{artifact_prefix}/{relative}", "sha256": _sha256(path)})
    return {"files": files, "removedUnsafeArtifacts": removed}


def _run_command(
    spec: CommandSpec,
    *,
    repo_root: Path,
    output_dir: Path,
    environment: Mapping[str, str],
    redactions: Sequence[tuple[str, str]],
) -> dict[str, object]:
    cwd = (repo_root / spec.cwd).resolve()
    if not cwd.is_relative_to(repo_root.resolve()) or not cwd.is_dir():
        raise RuntimeError(f"unsafe or missing command cwd for {spec.label}")
    command_environment = dict(environment)
    browser_root = output_dir / "browser" / spec.label
    if spec.browser_artifacts:
        command_environment["STATEPORT_BROWSER_ARTIFACT_ROOT"] = str(browser_root)
    started_at = _utc_now()
    started = time.monotonic()
    timed_out = False
    process = subprocess.Popen(
        list(spec.argv),
        cwd=cwd,
        env=command_environment,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        start_new_session=True,
    )
    try:
        stdout, _ = process.communicate(timeout=spec.timeout_seconds)
    except subprocess.TimeoutExpired as exc:
        timed_out = True
        partial = exc.output or b""
        _terminate(process)
        remainder = process.stdout.read() if process.stdout is not None else b""
        stdout = partial + remainder
    duration = time.monotonic() - started
    decoded = stdout.decode("utf-8", errors="replace")
    sanitized = sanitize_text(decoded, redactions)
    log_path = output_dir / "logs" / f"{spec.label}.log"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    log_path.parent.chmod(0o700)
    log_path.write_text(sanitized, encoding="utf-8")
    log_path.chmod(0o600)
    exit_code = process.returncode
    passed = exit_code == 0 and not timed_out
    result: dict[str, object] = {
        "label": spec.label,
        "argv": [sanitize_text(value, redactions) for value in spec.argv],
        "cwd": "[REPO]" if spec.cwd == "." else f"[REPO]/{spec.cwd}",
        "timeoutSeconds": spec.timeout_seconds,
        "startedAt": started_at,
        "durationSeconds": round(duration, 3),
        "exitCode": exit_code,
        "timedOut": timed_out,
        "passed": passed,
        "log": {
            "path": f"logs/{log_path.name}",
            "sha256": _sha256(log_path),
        },
    }
    if spec.browser_artifacts:
        result["artifacts"] = _sanitize_browser_artifacts(
            browser_root,
            redactions,
            artifact_prefix=f"browser/{spec.label}",
        )
    return result


def _summary_path(output_dir: Path) -> Path:
    return output_dir / "local_closure_gate.json"


def _write_summary(output_dir: Path, summary: Mapping[str, object]) -> None:
    path = _summary_path(output_dir)
    path.write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    path.chmod(0o600)


def run_gate(
    *,
    repo_root: Path,
    output_dir: Path,
    environment_label: str,
    commands: Sequence[CommandSpec] | None = None,
    environment: Mapping[str, str] | None = None,
    max_timeout_seconds: int = 900,
    dry_run: bool = False,
    workspace_state_root: Path | None = None,
) -> dict[str, object]:
    """Run the closure plan. ``commands`` is injectable for bounded unit tests."""

    repo_root = repo_root.resolve()
    output_dir = output_dir.resolve()
    if environment_label not in ENVIRONMENT_LABELS:
        raise ValueError(f"invalid environment label: {environment_label}")
    if output_dir == repo_root or output_dir.is_relative_to(repo_root):
        raise ValueError("output directory must be outside the repository")
    if output_dir.exists() and any(output_dir.iterdir()):
        raise ValueError("output directory must be absent or empty")
    output_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
    output_dir.chmod(0o700)
    command_plan = tuple(commands) if commands is not None else default_commands(max_timeout_seconds)
    if not command_plan or any(not item.argv for item in command_plan):
        raise ValueError("closure command plan must contain argv-only commands")
    labels = [item.label for item in command_plan]
    if len(labels) != len(set(labels)):
        raise ValueError("closure command labels must be unique")
    if any(not _SAFE_COMMAND_LABEL.fullmatch(label) for label in labels):
        raise ValueError(
            "closure command labels may contain only letters, digits, dots, dashes, and underscores"
        )
    source_environment = dict(os.environ if environment is None else environment)
    redactions = _redaction_values(repo_root, output_dir, source_environment)
    process_environment = _execution_environment(source_environment)
    started_at = _utc_now()
    started = time.monotonic()
    commit = _git(repo_root, "rev-parse", "HEAD")
    tree = _git(repo_root, "rev-parse", "HEAD^{tree}")
    status_before = _git(repo_root, "status", "--porcelain=v2", "--untracked-files=all")
    clean_before = status_before == ""
    blockers = _preflight(command_plan, process_environment)
    workspace_lifecycle: dict[str, object]
    try:
        workspace_lifecycle = WorkspaceLifecycleManager(
            repo_root,
            state_root=workspace_state_root,
        ).assert_repository_closed()
    except (OSError, WorkspaceLifecycleError) as exc:
        code = exc.code if isinstance(exc, WorkspaceLifecycleError) else "inventory_unknown"
        workspace_lifecycle = {"ok": False, "code": code, "detail": str(exc)}
        blockers.append(f"workspace lifecycle closure failed: {code}")
    container_detected = _container_detected(process_environment)
    if environment_label == "container" and not container_detected:
        blockers.append("container environment label was not corroborated by the execution environment")
    if not clean_before:
        blockers.append("Git worktree was not clean before the gate")

    records: list[dict[str, object]] = []
    if dry_run:
        blockers.append("dry run does not execute or validate closure commands")
    elif not blockers:
        for spec in command_plan:
            records.append(
                _run_command(
                    spec,
                    repo_root=repo_root,
                    output_dir=output_dir,
                    environment=process_environment,
                    redactions=redactions,
                )
            )

    status_after = _git(repo_root, "status", "--porcelain=v2", "--untracked-files=all")
    clean_after = status_after == ""
    if not clean_after:
        blockers.append("Git worktree was not clean after the gate")
    failed_labels = [str(item["label"]) for item in records if not item["passed"]]
    blockers.extend(f"command failed: {label}" for label in failed_labels)
    tool_versions = _tool_versions(repo_root, redactions, process_environment)
    if commands is None:
        required_versions = ("python", "pytest", "git", "node", "npm", "playwright")
        blockers.extend(
            f"required tool version unavailable: {name}"
            for name in required_versions
            if tool_versions.get(name) == "unavailable"
        )
    completed_at = _utc_now()
    duration_seconds = round(time.monotonic() - started, 3)
    passed = (
        not dry_run
        and not blockers
        and len(records) == len(command_plan)
        and all(bool(item["passed"]) for item in records)
        and clean_before
        and clean_after
    )
    required_environment = sorted(
        {name for spec in command_plan for name in spec.required_environment}
    )
    summary: dict[str, object] = {
        "formatVersion": FORMAT_VERSION,
        "classification": (
            "locally_closure_validated_from_this_checkout; remote_CI_not_run; not_remotely_CI_verified"
            if passed
            else "local_closure_failed_or_not_run; remote_CI_not_run; not_remotely_CI_verified"
        ),
        "environmentLabel": environment_label,
        "executionContext": {"containerDetected": container_detected},
        "startedAt": started_at,
        "completedAt": completed_at,
        "durationSeconds": duration_seconds,
        "repository": {
            "commit": commit,
            "tree": tree,
            "cleanBefore": clean_before,
            "cleanAfter": clean_after,
        },
        "workspaceLifecycle": workspace_lifecycle,
        "requiredEnvironment": {name: "present" if process_environment.get(name) else "missing" for name in required_environment},
        "toolVersions": tool_versions,
        "commands": records,
        "plannedCommands": [item.label for item in command_plan],
        "maxCommandTimeoutSeconds": max_timeout_seconds,
        "passed": passed,
        "blockers": sorted(set(blockers)),
        "remoteCI": {
            "included": False,
            "verified": False,
            "statement": "This record is local closure evidence, not remote CI.",
        },
        "privacy": {
            "environmentValuesRecorded": False,
            "sensitiveEnvironmentPassedToCommands": False,
            "credentialsRecorded": False,
            "rawTelegramContentRecorded": False,
            "rawTerminalContentRecorded": False,
        },
    }
    _write_summary(output_dir, summary)
    return summary


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--environment-label", required=True, choices=ENVIRONMENT_LABELS)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument(
        "--max-command-timeout-seconds",
        type=int,
        default=900,
        help="Upper bound applied to every command timeout (default: 900)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Write a fail-closed plan record without executing commands",
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    if args.max_command_timeout_seconds < 1:
        raise SystemExit("--max-command-timeout-seconds must be positive")
    try:
        summary = run_gate(
            repo_root=ROOT,
            output_dir=args.output_dir,
            environment_label=args.environment_label,
            max_timeout_seconds=args.max_command_timeout_seconds,
            dry_run=args.dry_run,
        )
    except (OSError, RuntimeError, ValueError) as exc:
        print(f"local closure gate could not start: {exc}", file=sys.stderr)
        return 2
    print("local closure summary: [OUTPUT]/local_closure_gate.json")
    return 0 if summary["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
