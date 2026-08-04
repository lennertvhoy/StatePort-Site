#!/usr/bin/env python3
"""Validate external candidate identity, recovery, and retention contracts."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import secrets
import subprocess
import tempfile
from typing import Any, Mapping, Sequence

import jsonschema
import yaml


ROOT = Path(__file__).resolve().parents[1]
CONTRACT_ROOT = ROOT / "config" / "candidate-provenance"
SCHEMA_PATH = ROOT / "schemas" / "candidate-provenance.v1.schema.json"
ABSOLUTE_WINDOWS = re.compile(r"^[A-Za-z]:[\\/]")
TOOL_RECEIPT = re.compile(r"^snapshot_receipt_[0-9a-f]{32}$")


# Tool-issued receipt identities are deterministic and content-bound: the
# pinned validation/materialization tooling derives them from the exact
# digests the receipt accounts for, so an operator without a broker daemon
# can produce a verifiable provenance contract (agent-native operation).
# Broker-issued authority_receipt_* identities pass through unchanged.
def _derive_tool_receipt(purpose: str, *bound_digests: str) -> str:
    payload = "stateport.tool-receipt/v1|" + purpose + "|" + "|".join(bound_digests)
    return "snapshot_receipt_" + hashlib.sha256(payload.encode("utf-8")).hexdigest()[:32]


def _expected_tool_receipts(value: Mapping[str, Any]) -> dict[str, str]:
    artifacts = value["artifacts"]
    bundle = artifacts["gitBundle"]
    return {
        "materialization.receipt.id": _derive_tool_receipt(
            "materialization", value["materialization"]["receipt"]["digest"]
        ),
        "artifacts.gitBundle.recoveryReceipt": _derive_tool_receipt("recovery", bundle["sha256"]),
        "retention.preservationReceipt": _derive_tool_receipt(
            "preservation",
            bundle["sha256"],
            artifacts["auditedSourceArchive"]["sha256"],
        ),
    }


def _verify_tool_receipts(value: Mapping[str, Any]) -> None:
    observed = {
        "materialization.receipt.id": value["materialization"]["receipt"]["id"],
        "artifacts.gitBundle.recoveryReceipt": value["artifacts"]["gitBundle"]["recoveryReceipt"],
        "retention.preservationReceipt": value["retention"]["preservationReceipt"],
    }
    expected = _expected_tool_receipts(value)
    for field, receipt in observed.items():
        if TOOL_RECEIPT.fullmatch(receipt) is None:
            continue
        if not secrets.compare_digest(receipt, expected[field]):
            raise CandidateProvenanceError(
                f"tool-issued receipt does not match its content derivation at {field}"
            )


class CandidateProvenanceError(RuntimeError):
    """Candidate provenance is malformed, ambiguous, or unrecoverable."""


def _load(path: Path) -> Any:
    try:
        return yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, yaml.YAMLError) as exc:
        raise CandidateProvenanceError(f"could not parse {path.name}") from exc


def _walk(value: Any, field: str = "$") -> None:
    if isinstance(value, Mapping):
        for key, child in value.items():
            _walk(child, f"{field}.{key}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            _walk(child, f"{field}[{index}]")
    elif isinstance(value, str):
        if value.startswith(("/", "~/")) or ABSOLUTE_WINDOWS.match(value):
            raise CandidateProvenanceError(f"absolute host path is forbidden at {field}")


def validate_contract(value: Any, schema: Mapping[str, Any]) -> Mapping[str, Any]:
    try:
        jsonschema.Draft202012Validator.check_schema(schema)
        jsonschema.Draft202012Validator(schema).validate(value)
    except (jsonschema.SchemaError, jsonschema.ValidationError) as exc:
        raise CandidateProvenanceError(
            f"candidate contract schema validation failed: {exc.message}"
        ) from exc
    if not isinstance(value, Mapping):
        raise CandidateProvenanceError("candidate contract must be an object")
    _walk(value)
    _verify_tool_receipts(value)
    repository = value["repository"]
    artifacts = value["artifacts"]
    if artifacts["auditedSourceArchive"]["embeddedCommit"] != repository["commit"]:
        raise CandidateProvenanceError("source archive embedded commit does not match candidate")
    bundle = artifacts["gitBundle"]
    if bundle["ref"] != repository["ref"]:
        raise CandidateProvenanceError("bundle ref does not match candidate ref")
    recovery = value["verification"]["recovery"]
    if recovery["bundleLocator"] != bundle["locator"]:
        raise CandidateProvenanceError("recovery command locator does not match bundle locator")
    return value


def _git(repository: Path, *args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", "-C", str(repository), *args],
        check=check,
        text=True,
        capture_output=True,
    )


def validate_repository_relationship(value: Mapping[str, Any], repository: Path = ROOT) -> None:
    source = value["materialization"]
    candidate = value["repository"]
    if (
        _git(
            repository, "cat-file", "-e", f"{source['sourceCommit']}^{{commit}}", check=False
        ).returncode
        != 0
    ):
        raise CandidateProvenanceError(
            "materialization source commit is not retained by the primary repository"
        )
    source_tree = _git(repository, "rev-parse", f"{source['sourceCommit']}^{{tree}}").stdout.strip()
    if not secrets.compare_digest(source_tree, str(source["sourceTree"])):
        raise CandidateProvenanceError(
            "materialization source tree does not match the source commit"
        )
    for label in ("materializer", "exporter", "policy"):
        tool = source[label]
        blob = str(tool["gitBlob"])
        blob_type = _git(repository, "cat-file", "-t", blob, check=False)
        if blob_type.returncode != 0 or blob_type.stdout.strip() != "blob":
            raise CandidateProvenanceError(f"materialization {label} blob is not retained")
        payload = subprocess.run(
            ["git", "-C", str(repository), "cat-file", "blob", blob],
            check=True,
            capture_output=True,
        ).stdout
        if hashlib.sha256(payload).hexdigest() != tool["sha256"]:
            raise CandidateProvenanceError(f"materialization {label} blob digest does not match")
    if (
        _git(
            repository, "cat-file", "-e", f"{candidate['commit']}^{{commit}}", check=False
        ).returncode
        == 0
    ):
        raise CandidateProvenanceError(
            "candidate unexpectedly resolves in the primary repository; update its namespace contract"
        )


def verify_bundle(value: Mapping[str, Any], bundle: Path) -> None:
    if not bundle.is_file() or bundle.is_symlink():
        raise CandidateProvenanceError("operator bundle is missing or unsafe")
    expected = value["artifacts"]["gitBundle"]
    digest = hashlib.sha256(bundle.read_bytes()).hexdigest()
    if digest != expected["sha256"] or bundle.stat().st_size != expected["bytes"]:
        raise CandidateProvenanceError("operator bundle digest or size does not match the contract")
    listed = subprocess.run(
        ["git", "bundle", "list-heads", str(bundle)], check=True, text=True, capture_output=True
    ).stdout.strip()
    candidate = value["repository"]
    if listed != f"{candidate['commit']} {candidate['ref']}":
        raise CandidateProvenanceError("operator bundle does not contain the exact candidate ref")
    subprocess.run(
        ["git", "bundle", "verify", str(bundle)], check=True, text=True, capture_output=True
    )
    with tempfile.TemporaryDirectory(prefix="stateport-candidate-recovery-") as temporary:
        recovered = Path(temporary) / "candidate"
        subprocess.run(
            [
                "git",
                "-c",
                "init.defaultBranch=main",
                "clone",
                "--quiet",
                "--no-checkout",
                str(bundle),
                str(recovered),
            ],
            check=True,
        )
        head = _git(recovered, "rev-parse", "origin/public-main").stdout.strip()
        tree = _git(recovered, "rev-parse", "origin/public-main^{tree}").stdout.strip()
        if head != candidate["commit"] or tree != candidate["tree"]:
            raise CandidateProvenanceError("recovered bundle identity does not match the contract")
        _git(recovered, "fsck", "--full", "--strict", "--no-reflogs")


def validate_all(root: Path = ROOT, bundle: Path | None = None) -> tuple[str, ...]:
    schema = json.loads(
        (root / "schemas" / "candidate-provenance.v1.schema.json").read_text(encoding="utf-8")
    )
    contracts = sorted((root / "config" / "candidate-provenance").glob("*.yaml"))
    if not contracts:
        raise CandidateProvenanceError("at least one candidate provenance contract is required")
    identities: set[str] = set()
    validated: list[str] = []
    for path in contracts:
        value = validate_contract(_load(path), schema)
        candidate_id = str(value["candidateId"])
        if candidate_id in identities or path.stem != candidate_id:
            raise CandidateProvenanceError(
                "candidate ID is duplicate or does not match its file name"
            )
        identities.add(candidate_id)
        validate_repository_relationship(value, root)
        if bundle is not None:
            if len(contracts) != 1:
                raise CandidateProvenanceError("--bundle requires exactly one candidate contract")
            verify_bundle(value, bundle)
        validated.append(candidate_id)
    return tuple(validated)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--bundle", type=Path)
    args = parser.parse_args(argv)
    try:
        candidates = validate_all(args.root.resolve(), args.bundle)
    except (
        CandidateProvenanceError,
        OSError,
        subprocess.CalledProcessError,
        json.JSONDecodeError,
    ) as exc:
        print(f"FAIL: {exc}")
        return 1
    if args.bundle is None:
        print(
            f"PASS: {len(candidates)} external candidate provenance contract(s) are typed; "
            "external recovery bundle not inspected"
        )
    else:
        print(
            f"PASS: {len(candidates)} external candidate provenance contract(s) are typed "
            "and the exact recovery bundle was verified"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
