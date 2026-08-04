"""Rootless Podman CLI engine adapter for the execution-host daemon.

The daemon owns every container argument: argv is built only from fixed
templates plus typed, validated spec fields, then re-asserted against an
allowlist before execution (hardening rules reused from
``packages/container-runner``: digest-pinned images, no privilege, no host
namespaces, no mounts, bounded resources).  The engine never touches a
control-plane socket; only the execution user's own rootless socket (or the
default rootless CLI) is used.
"""

from __future__ import annotations

import json
import os
import subprocess
from typing import Any, Mapping, Sequence

from .daemon_contract import MAX_REQUEST_TIMEOUT_SECONDS


MANAGED_LABEL = "io.stateport.execution.managed=true"
WORKLOAD_LABEL = "io.stateport.execution.workload"
KIND_LABEL = "io.stateport.execution.kind"

# Sockets that belong to the control plane or a system engine.  The execution
# host owns its own rootless socket and must never observe these.
CONTROL_PLANE_SOCKETS = frozenset(
    {
        "/run/podman/podman.sock",
        "/var/run/podman/podman.sock",
        "/var/run/docker.sock",
        "/run/docker.sock",
    }
)

# Daemon-owned workload supervisor entrypoint.  Every value it consumes
# arrives as a validated typed environment variable; no client-controlled
# string is ever spliced into a command line.
_WORKLOAD_TEMPLATE = (
    "set -eu; "
    'echo "stateport-workload-start kind=$STATEPORT_WORKLOAD_KIND id=$STATEPORT_WORKLOAD_ID"; '
    'if [ "$STATEPORT_PARAM_EMIT_BYTES" -gt 0 ]; then '
    'head -c "$STATEPORT_PARAM_EMIT_BYTES" /dev/zero | tr "\\0" "s"; echo; fi; '
    'sleep "$STATEPORT_PARAM_WORK_SECONDS"; '
    'echo "stateport-workload-complete id=$STATEPORT_WORKLOAD_ID"'
)

# Fixed allowlist for the constructed create argv (flag position 0 is the
# podman binary itself).  Anything outside this set fails closed.
_ALLOWED_CREATE_FLAGS = frozenset(
    {
        "create",
        "--name",
        "--label",
        "--network",
        "--read-only",
        "--cap-drop",
        "--security-opt",
        "--pids-limit",
        "--memory",
        "--tmpfs",
        "--env",
        "--entrypoint",
        "--stop-signal",
        "--stop-timeout",
        "--pull",
        "--quiet",
    }
)


class EngineError(RuntimeError):
    """A typed engine failure; the daemon converts it into a refusal receipt."""


def container_name(workload_id: str) -> str:
    return f"stateport-exec-{workload_id}"


def build_create_argv(spec: Mapping[str, Any]) -> list[str]:
    """Build the hardened create argv from a validated sealed spec."""

    name = container_name(spec["workloadId"])
    parameters = spec["parameters"]
    env = {
        "STATEPORT_WORKLOAD_ID": spec["workloadId"],
        "STATEPORT_WORKLOAD_KIND": spec["kind"],
        "STATEPORT_PARAM_WORK_SECONDS": str(parameters["workSeconds"]),
        "STATEPORT_PARAM_EMIT_BYTES": str(parameters["emitBytes"]),
    }
    for field, raw in parameters.items():
        if field in {"workSeconds", "emitBytes"}:
            continue
        # Identity fields are validated typed strings (ids, digests, references).
        env["STATEPORT_PARAM_" + field.upper()] = str(raw)
    argv = [
        "create",
        "--name",
        name,
        "--label",
        MANAGED_LABEL,
        "--label",
        f"{WORKLOAD_LABEL}={spec['workloadId']}",
        "--label",
        f"{KIND_LABEL}={spec['kind']}",
        "--network",
        "none",
        "--read-only",
        "--cap-drop",
        "ALL",
        "--security-opt",
        "no-new-privileges",
        "--pids-limit",
        str(spec["resources"]["pidsMax"]),
        "--memory",
        str(spec["resources"]["memoryMaxBytes"]),
        "--tmpfs",
        "/tmp:rw,noexec,nosuid,nodev,size=16m",
        "--pull",
        "never",
        "--stop-signal",
        "SIGKILL",
        "--stop-timeout",
        "2",
        "--entrypoint",
        "/bin/sh",
        "--quiet",
    ]
    for key in sorted(env):
        argv.extend(["--env", f"{key}={env[key]}"])
    argv.extend([spec["image"]["reference"], "-c", _WORKLOAD_TEMPLATE])
    assert_create_argv_hardened(argv)
    return argv


def assert_create_argv_hardened(argv: Sequence[str]) -> None:
    """Re-assert the constructed argv against the fixed flag allowlist."""

    flags = {item for item in argv if item.startswith("--")}
    unknown = flags - _ALLOWED_CREATE_FLAGS
    if unknown:
        raise EngineError(f"constructed argv carries unapproved flags: {sorted(unknown)}")
    text = list(argv)
    for forbidden in ("--privileged", "--device", "--volume", "--mount", "--cap-add", "--userns"):
        if forbidden in text:
            raise EngineError(f"constructed argv carries a forbidden flag: {forbidden}")
    if any(value in {"host", "container", "ns"} for value in text):
        raise EngineError("constructed argv references a host or shared namespace")
    if any(CONTROL_PLANE_SOCKETS & {item} for item in text):
        raise EngineError("constructed argv references a control-plane socket")


class PodmanCliEngine:
    """Rootless Podman over the CLI, optionally against the owned socket."""

    def __init__(
        self,
        *,
        binary: str = "podman",
        socket_path: str | None = None,
        runner: Any = subprocess.run,
    ) -> None:
        if socket_path is not None:
            normalized = os.path.normpath(socket_path)
            if normalized in CONTROL_PLANE_SOCKETS or not normalized.startswith("/"):
                raise EngineError(
                    f"engine socket {socket_path!r} is a control-plane or relative path; refused"
                )
            socket_path = normalized
        self._binary = binary
        self._socket_path = socket_path
        self._runner = runner

    @property
    def identity(self) -> dict[str, str]:
        return {
            "engine": f"{self._binary}-cli",
            "socket": self._socket_path or "default-rootless",
        }

    def _env(self) -> dict[str, str]:
        env = dict(os.environ)
        env.pop("DOCKER_HOST", None)
        if self._socket_path is not None:
            env["CONTAINER_HOST"] = f"unix://{self._socket_path}"
        else:
            env.pop("CONTAINER_HOST", None)
        return env

    def _run(self, args: Sequence[str], *, timeout: int = MAX_REQUEST_TIMEOUT_SECONDS) -> subprocess.CompletedProcess[str]:
        if any(item in CONTROL_PLANE_SOCKETS for item in args):
            raise EngineError("engine invocation references a control-plane socket")
        try:
            completed = self._runner(
                [self._binary, *args],
                capture_output=True,
                text=True,
                timeout=timeout,
                env=self._env(),
                stdin=subprocess.DEVNULL,
            )
        except subprocess.TimeoutExpired as exc:
            raise EngineError(f"engine call timed out: {args[0]}") from exc
        except FileNotFoundError as exc:
            raise EngineError(f"engine binary is unavailable: {self._binary}") from exc
        return completed

    def _require_ok(self, completed: subprocess.CompletedProcess[str], action: str) -> str:
        if completed.returncode != 0:
            detail = completed.stderr.strip() or completed.stdout.strip()
            raise EngineError(f"{action} failed: {detail[:300]}")
        return completed.stdout.strip()

    def version(self) -> dict[str, str]:
        out = self._require_ok(self._run(["version", "--format", "json"], timeout=30), "podman version")
        try:
            parsed = json.loads(out)
            return {"engine": "podman", "engineVersion": str(parsed.get("Client", {}).get("Version", "unknown"))}
        except (ValueError, AttributeError):
            return {"engine": "podman", "engineVersion": "unknown"}

    def create(self, spec: Mapping[str, Any]) -> str:
        argv = build_create_argv(spec)
        return self._require_ok(self._run(argv), "workload create")

    def start(self, workload_id: str) -> None:
        self._require_ok(self._run(["start", container_name(workload_id)]), "workload start")

    def stop(self, workload_id: str, *, timeout: int = 2) -> None:
        completed = self._run(["stop", "--time", str(timeout), container_name(workload_id)])
        if completed.returncode != 0 and "no such container" not in completed.stderr.lower():
            raise EngineError(f"workload stop failed: {completed.stderr.strip()[:300]}")

    def kill(self, workload_id: str) -> None:
        completed = self._run(["kill", container_name(workload_id)])
        if completed.returncode != 0 and "no such container" not in completed.stderr.lower():
            raise EngineError(f"workload kill failed: {completed.stderr.strip()[:300]}")

    def remove(self, workload_id: str, *, force: bool = True) -> None:
        args = ["rm"]
        if force:
            args.append("--force")
        args.append(container_name(workload_id))
        completed = self._run(args)
        if completed.returncode != 0 and "no such container" not in completed.stderr.lower():
            raise EngineError(f"workload remove failed: {completed.stderr.strip()[:300]}")

    def inspect(self, workload_id: str) -> dict[str, Any]:
        out = self._run(
            [
                "inspect",
                "--format",
                "{{json .}}",
                container_name(workload_id),
            ]
        )
        if out.returncode != 0:
            return {"present": False}
        try:
            raw = json.loads(out.stdout)
        except ValueError as exc:
            raise EngineError("engine inspect returned malformed JSON") from exc
        state = raw.get("State", {}) if isinstance(raw, Mapping) else {}
        config = raw.get("Config", {}) if isinstance(raw, Mapping) else {}
        return {
            "present": True,
            "status": str(state.get("Status", "unknown")),
            "running": bool(state.get("Running", False)),
            "exitStatus": state.get("ExitCode") if "ExitCode" in state else None,
            "startedAt": state.get("StartedAt") or None,
            "finishedAt": state.get("FinishedAt") or None,
            "imageDigest": raw.get("ImageDigest") or None,
            "labels": dict(config.get("Labels") or {}),
        }

    def logs(self, workload_id: str, *, max_bytes: int) -> dict[str, Any]:
        completed = self._run(["logs", container_name(workload_id)])
        if completed.returncode != 0:
            raise EngineError(f"workload logs failed: {completed.stderr.strip()[:300]}")
        data = completed.stdout.encode("utf-8", "replace")
        truncated = len(data) > max_bytes
        return {
            "bytes": data[:max_bytes].decode("utf-8", "replace"),
            "byteCount": min(len(data), max_bytes),
            "truncated": truncated,
        }

    def list_managed(self) -> list[dict[str, Any]]:
        completed = self._run(
            ["ps", "--all", "--filter", f"label={MANAGED_LABEL}", "--format", "json"]
        )
        if completed.returncode != 0:
            raise EngineError(f"managed enumeration failed: {completed.stderr.strip()[:300]}")
        try:
            entries = json.loads(completed.stdout or "[]")
        except ValueError as exc:
            raise EngineError("managed enumeration returned malformed JSON") from exc
        managed: list[dict[str, Any]] = []
        for entry in entries:
            labels = entry.get("Labels") or {}
            if isinstance(labels, str):
                labels = dict(
                    item.split("=", 1) for item in labels.split(",") if "=" in item
                )
            workload = labels.get(WORKLOAD_LABEL)
            names = entry.get("Names") or []
            if not workload and names:
                workload = str(names[0]).removeprefix("stateport-exec-") or None
            managed.append(
                {
                    "workloadId": workload,
                    "state": str(entry.get("State", "unknown")),
                    "labels": labels,
                }
            )
        return managed
