#!/usr/bin/env python3
"""Provision the stable execution-host daemon's host identity and units.

Renders a typed, deterministic provisioning plan from the signed target
topology: the ``stateport-exec`` user, the ``stateport-execution-control``
group, the group-confined control-socket directory (operator-provisioned
tmpfiles, per the signed execution contract), and the stable-host Quadlet
units rendered by ``render_stable_host_quadlet_bundle`` — the separately
governed, out-of-revision lifecycle.  The daemon itself never performs these
steps: its boot fails closed until this provisioning exists.

The CLI emits (or applies) a plan for a release index it has only
structurally validated; ``verificationBasis`` in the plan records that.  The
release pipeline calls :func:`render_provisioning_plan` with an already
signature-verified target instead.
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path, PurePosixPath
import subprocess
import sys
from typing import Any, Mapping, Sequence

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "packages" / "release-contracts" / "src"))

from stateport_release.contract import (  # noqa: E402
    ReleaseContractError,
    canonical_digest,
    load_release_index_file,
    render_stable_host_quadlet_bundle,
    validate_release_index,
)

EXEC_USER = "stateport-exec"
EXEC_GROUP = "stateport-execution-control"
TMPFILES_PATH = "/etc/tmpfiles.d/stateport-execution-control.conf"
EXEC_HOME = f"/var/lib/{EXEC_USER}"


def render_provisioning_plan(
    target: Mapping[str, Any],
    images: Sequence[Mapping[str, Any]],
    *,
    verification_basis: str,
) -> dict[str, Any]:
    """Render the ordered, typed provisioning plan for the stable exec host."""

    if target.get("executionHostMode") not in {
        "stable-host-daemon-client",
        "stable-host-daemon-bootstrap-only",
    }:
        raise ReleaseContractError("target has no stable execution host to provision")
    contract = target["executionContract"]
    bundle = render_stable_host_quadlet_bundle(target, images)
    quadlet_files = sorted(path for path in bundle if path.startswith(f"host/{EXEC_USER}/"))
    if not quadlet_files:
        raise ReleaseContractError("stable host bundle has no execution-host units")
    writes: list[dict[str, Any]] = [
        {
            "path": TMPFILES_PATH,
            "content": (
                f"d {contract['hostDirectory']} {contract['directoryMode']} "
                f"{contract['directoryOwner']} {contract['directoryGroup']} -\n"
            ),
            "mode": "0644",
            "owner": "root:root",
        }
    ]
    for relative in quadlet_files:
        content = bundle[relative].decode("utf-8")
        writes.append(
            {
                "path": f"{EXEC_HOME}/.config/containers/systemd/{PurePosixPath(relative).name}",
                "contentDigest": canonical_digest(content),
                "content": content,
                "mode": "0640",
                "owner": f"{EXEC_USER}:{EXEC_USER}",
            }
        )
    quadlet_paths = [write["path"] for write in writes if write["path"] != TMPFILES_PATH]
    steps: list[dict[str, Any]] = [
        {
            "step": "ensure-execution-control-group",
            "commands": [["groupadd", "--system", EXEC_GROUP]],
            "idempotent": True,
        },
        {
            "step": "ensure-stateport-exec-user",
            "commands": [
                [
                    "useradd",
                    "--system",
                    "--gid",
                    EXEC_GROUP,
                    "--home-dir",
                    EXEC_HOME,
                    "--shell",
                    "/usr/sbin/nologin",
                    EXEC_USER,
                ]
            ],
            "idempotent": True,
        },
        {
            "step": "confine-control-plane-client",
            "commands": [
                ["usermod", "--append", "--groups", EXEC_GROUP, contract["allowedClientUser"]]
            ],
            "idempotent": True,
        },
        {
            "step": "enable-exec-user-linger",
            "commands": [["loginctl", "enable-linger", EXEC_USER]],
            "idempotent": True,
        },
        {
            "step": "write-confined-socket-tmpfiles",
            "writes": [TMPFILES_PATH],
            "commands": [["systemd-tmpfiles", "--create", TMPFILES_PATH]],
            "idempotent": False,
        },
        {
            "step": "install-stable-host-quadlets",
            "writes": quadlet_paths,
            "commands": [
                ["runuser", "-u", EXEC_USER, "--", "systemctl", "--user", "daemon-reload"]
            ],
            "idempotent": False,
        },
        {
            "step": "start-exec-user-engine-socket",
            "commands": [
                [
                    "runuser",
                    "-u",
                    EXEC_USER,
                    "--",
                    "systemctl",
                    "--user",
                    "enable",
                    "--now",
                    "podman.socket",
                ]
            ],
            "idempotent": True,
        },
        {
            "step": "start-execution-host-daemon",
            "commands": [
                [
                    "runuser",
                    "-u",
                    EXEC_USER,
                    "--",
                    "systemctl",
                    "--user",
                    "enable",
                    "--now",
                    "stateport-execution-host",
                ]
            ],
            "idempotent": False,
        },
    ]
    plan: dict[str, Any] = {
        "schema": "stateport.execution-host-provisioning/v1",
        "releaseId": str(target["releaseId"]),
        "targetId": str(target["targetId"]),
        "topologyDigest": str(target["topologyDigest"]),
        "verificationBasis": verification_basis,
        "executionUser": EXEC_USER,
        "executionControlGroup": EXEC_GROUP,
        "allowedClientUser": contract["allowedClientUser"],
        "socketDirectory": contract["hostDirectory"],
        "socketDirectoryMode": contract["directoryMode"],
        "socketMode": contract["socketMode"],
        "quadletOwner": EXEC_USER,
        "writes": writes,
        "steps": steps,
    }
    plan["planDigest"] = canonical_digest(
        {key: value for key, value in plan.items() if key != "planDigest"}
    )
    return plan


def apply_plan(plan: Mapping[str, Any], *, runner: Any = subprocess.run) -> list[dict[str, Any]]:
    """Apply a rendered plan as root; every step and write is receipted."""

    if os.geteuid() != 0:
        raise ReleaseContractError("execution-host provisioning must run as root")
    receipts: list[dict[str, Any]] = []
    for write in plan["writes"]:
        path = Path(write["path"])
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(write["content"], encoding="utf-8")
        os.chmod(path, int(write["mode"], 8))
        receipts.append({"write": str(path), "owner": write["owner"], "result": "written"})
    for step in plan["steps"]:
        for command in step.get("commands", []):
            completed = runner(command, capture_output=True, text=True, timeout=300)
            failed = completed.returncode != 0
            if failed and step["idempotent"] and _already_satisfied(completed):
                failed = False
            receipts.append(
                {
                    "step": step["step"],
                    "command": command,
                    "returncode": completed.returncode,
                    "result": "failed" if failed else "applied",
                    "stderr": (completed.stderr or "").strip()[:300],
                }
            )
            if failed:
                raise ReleaseContractError(
                    f"provisioning step {step['step']} failed: "
                    f"{(completed.stderr or '').strip()[:300]}"
                )
    return receipts


def _already_satisfied(completed: Any) -> bool:
    text = ((completed.stderr or "") + (completed.stdout or "")).lower()
    return "already exists" in text or "already a member" in text


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--release-index", type=Path, required=True)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--emit-plan", action="store_true")
    mode.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    index = load_release_index_file(args.release_index)
    target = index.document["signed"]["targets"][0]
    plan = render_provisioning_plan(
        target,
        index.document["signed"]["images"],
        verification_basis=(
            "structural-only: CLI input is shape-validated; the pipeline path renders "
            "from a signature-verified target"
        ),
    )
    if args.emit_plan:
        json.dump(plan, sys.stdout, indent=2, sort_keys=True)
        sys.stdout.write("\n")
        return 0
    receipts = apply_plan(plan)
    json.dump(
        {"planDigest": plan["planDigest"], "receipts": receipts},
        sys.stdout,
        indent=2,
        sort_keys=True,
    )
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
