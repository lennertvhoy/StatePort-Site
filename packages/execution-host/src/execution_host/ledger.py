"""Durable operation ledger for the execution-host daemon.

One atomic JSON document per workload plus a recovery journal.  On boot the
daemon reconciles the ledger against the engine's ``io.stateport.execution.managed``
enumeration *before* accepting new work: a workload the previous epoch left
non-terminal is marked ``interrupted``, its container is stopped and removed,
and the cleanup outcome is receipted.  Orphan managed containers with no
ledger entry are removed and receipted as well.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Mapping

from .daemon_contract import TERMINAL_STATES, canonical_digest


class LedgerError(RuntimeError):
    pass


def _atomic_write(path: Path, payload: Mapping[str, Any]) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    data = json.dumps(payload, indent=2, sort_keys=True) + "\n"
    with open(tmp, "w", encoding="utf-8") as handle:
        handle.write(data)
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(tmp, path)
    directory_fd = os.open(str(path.parent), os.O_RDONLY)
    try:
        os.fsync(directory_fd)
    finally:
        os.close(directory_fd)


class OperationLedger:
    def __init__(self, state_dir: Path) -> None:
        self._state_dir = Path(state_dir)
        self._workloads_dir = self._state_dir / "workloads"
        self._recovery_dir = self._state_dir / "recovery"
        for directory in (self._workloads_dir, self._recovery_dir):
            directory.mkdir(parents=True, exist_ok=True)
            os.chmod(directory, 0o700)

    @property
    def state_dir(self) -> Path:
        return self._state_dir

    def _path(self, workload_id: str) -> Path:
        return self._workloads_dir / f"{workload_id}.json"

    def get(self, workload_id: str) -> dict[str, Any] | None:
        path = self._path(workload_id)
        if not path.is_file():
            return None
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (ValueError, OSError) as exc:
            raise LedgerError(f"ledger entry for {workload_id} is unreadable: {exc}") from exc

    def all(self) -> list[dict[str, Any]]:
        entries: list[dict[str, Any]] = []
        for path in sorted(self._workloads_dir.glob("*.json")):
            try:
                entries.append(json.loads(path.read_text(encoding="utf-8")))
            except (ValueError, OSError) as exc:
                raise LedgerError(f"ledger entry {path.name} is unreadable: {exc}") from exc
        return entries

    def record_created(self, spec: Mapping[str, Any], *, at: str, container_id: str) -> dict[str, Any]:
        workload_id = str(spec["workloadId"])
        if self._path(workload_id).exists():
            raise LedgerError(f"workload {workload_id} already has a ledger entry")
        entry = {
            "workloadId": workload_id,
            "specDigest": canonical_digest(spec),
            "spec": dict(spec),
            "containerId": container_id,
            "state": "created",
            "createdAt": at,
            "updatedAt": at,
            "startedAt": None,
            "finishedAt": None,
            "exitStatus": None,
            "receipts": [],
        }
        _atomic_write(self._path(workload_id), entry)
        return entry

    def transition(
        self,
        workload_id: str,
        state: str,
        *,
        at: str,
        receipt: Mapping[str, Any] | None = None,
        exit_status: int | None = None,
        started_at: str | None = None,
        finished_at: str | None = None,
    ) -> dict[str, Any]:
        entry = self.get(workload_id)
        if entry is None:
            raise LedgerError(f"workload {workload_id} has no ledger entry")
        entry["state"] = state
        entry["updatedAt"] = at
        if exit_status is not None:
            entry["exitStatus"] = exit_status
        if started_at is not None:
            entry["startedAt"] = started_at
        if finished_at is not None:
            entry["finishedAt"] = finished_at
        if receipt is not None:
            entry["receipts"].append(dict(receipt))
        _atomic_write(self._path(workload_id), entry)
        return entry

    def record_recovery(self, report: Mapping[str, Any], *, at: str) -> Path:
        name = f"recovery-{at.replace(':', '').replace('-', '')}.json"
        path = self._recovery_dir / name
        _atomic_write(path, {"recordedAt": at, "report": dict(report)})
        return path

    def active_workload_ids(self) -> set[str]:
        return {
            str(entry["workloadId"])
            for entry in self.all()
            if entry["state"] not in TERMINAL_STATES
        }


def reconcile_on_boot(ledger: OperationLedger, engine: Any, *, at: str) -> dict[str, Any]:
    """Reconcile durable ledger state against managed engine containers.

    Returns the recovery report; every reconciliation action is recorded.
    The daemon must run this before accepting new work.
    """

    managed = engine.list_managed()
    managed_by_id = {
        str(item["workloadId"]): item for item in managed if item.get("workloadId")
    }
    report: dict[str, Any] = {"interrupted": [], "orphansRemoved": [], "failures": []}

    for entry in ledger.all():
        workload_id = str(entry["workloadId"])
        if entry["state"] in TERMINAL_STATES:
            if entry["state"] != "removed" and workload_id in managed_by_id:
                # Terminal in the ledger but still present in the engine:
                # finish the cleanup the previous epoch did not complete.
                try:
                    engine.remove(workload_id, force=True)
                    report["orphansRemoved"].append(workload_id)
                except Exception as exc:  # reconciliation records, never hides
                    report["failures"].append({"workloadId": workload_id, "error": str(exc)[:300]})
            continue
        # Non-terminal across a daemon restart: supervision is lost, so the
        # alpha policy is terminate-and-receipt, never adopt.
        try:
            if workload_id in managed_by_id:
                engine.stop(workload_id, timeout=2)
                engine.remove(workload_id, force=True)
            ledger.transition(
                workload_id,
                "interrupted",
                at=at,
                receipt={
                    "kind": "restart-recovery",
                    "detail": "daemon restart interrupted a non-terminal workload; container stopped and removed",
                    "cleanup": "performed" if workload_id in managed_by_id else "not-required",
                },
            )
            report["interrupted"].append(workload_id)
        except Exception as exc:
            report["failures"].append({"workloadId": workload_id, "error": str(exc)[:300]})

    ledger_ids = {str(entry["workloadId"]) for entry in ledger.all()}
    for workload_id in sorted(set(managed_by_id) - ledger_ids):
        try:
            engine.stop(workload_id, timeout=2)
            engine.remove(workload_id, force=True)
            report["orphansRemoved"].append(workload_id)
        except Exception as exc:
            report["failures"].append({"workloadId": workload_id, "error": str(exc)[:300]})

    ledger.record_recovery(report, at=at)
    return report
