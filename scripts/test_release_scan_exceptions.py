from __future__ import annotations

import json
from pathlib import Path
import sys

import pytest
import yaml


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from collect_release_evidence import (  # noqa: E402
    EvidenceError,
    evaluate_scan,
    load_scan_exceptions,
)


TODAY = "2026-08-02"


def _exceptions_config(records: list[dict]) -> dict:
    return {
        "formatVersion": "stateport.release-scan-exceptions/v1",
        "resolvedOn": TODAY,
        "exceptions": records,
    }


def _record(**overrides: object) -> dict:
    record = {
        "id": "RX-2026-001",
        "advisory": "CVE-2026-11940",
        "package": "python",
        "images": ["stateport-api"],
        "severity": "High",
        "surface": "CPython standard library in the control-plane runtime image.",
        "reachability": "No fixed CPython 3.13 release exists at the pin date; the defect is documented as unreachable through the service surface.",
        "evidence": "Grype scan retained under the release evidence root; upstream fix only in 3.15.0b4.",
        "remediation": "Rebase to the first fixed CPython 3.13.x or 3.15 base image when published.",
        "expiresOn": "2026-09-15",
    }
    record.update(overrides)
    return record


def _write_scan(tmp_path: Path, matches: list[dict]) -> Path:
    path = tmp_path / "scan.json"
    path.write_text(json.dumps({"matches": matches}), encoding="utf-8")
    return path


def _match(
    advisory: str = "CVE-2026-11940",
    package: str = "python",
    version: str = "3.13.14",
    severity: str = "High",
) -> dict:
    return {
        "vulnerability": {
            "id": advisory,
            "severity": severity,
            "fix": {"state": "wont-fix", "versions": []},
        },
        "artifact": {"name": package, "version": version},
    }


def test_repository_exception_contract_is_schema_valid_and_empty_by_default() -> None:
    config, digest = load_scan_exceptions()
    assert config["formatVersion"] == "stateport.release-scan-exceptions/v1"
    assert isinstance(config["exceptions"], list)
    assert digest.startswith("sha256:")


def test_exact_unexpired_exception_explains_a_finding(tmp_path: Path) -> None:
    scan = _write_scan(tmp_path, [_match()])
    result = evaluate_scan(
        scan_path=scan,
        image_id="stateport-api",
        exceptions_config=_exceptions_config([_record()]),
        today=TODAY,
    )
    assert result["unexplainedFindings"] == []
    assert [item["exceptionId"] for item in result["appliedExceptions"]] == ["RX-2026-001"]


def test_expired_exception_refuses_the_finding(tmp_path: Path) -> None:
    scan = _write_scan(tmp_path, [_match()])
    result = evaluate_scan(
        scan_path=scan,
        image_id="stateport-api",
        exceptions_config=_exceptions_config([_record(expiresOn="2026-08-01")]),
        today=TODAY,
    )
    assert len(result["unexplainedFindings"]) == 1
    assert result["appliedExceptions"] == []


def test_exception_for_another_image_refuses_the_finding(tmp_path: Path) -> None:
    scan = _write_scan(tmp_path, [_match()])
    result = evaluate_scan(
        scan_path=scan,
        image_id="stateport-web",
        exceptions_config=_exceptions_config([_record()]),
        today=TODAY,
    )
    assert len(result["unexplainedFindings"]) == 1


def test_advisory_mismatch_refuses_the_finding(tmp_path: Path) -> None:
    scan = _write_scan(tmp_path, [_match(advisory="CVE-2026-99999")])
    result = evaluate_scan(
        scan_path=scan,
        image_id="stateport-api",
        exceptions_config=_exceptions_config([_record()]),
        today=TODAY,
    )
    assert len(result["unexplainedFindings"]) == 1


def test_package_mismatch_refuses_the_finding(tmp_path: Path) -> None:
    scan = _write_scan(tmp_path, [_match(package="libssl3")])
    result = evaluate_scan(
        scan_path=scan,
        image_id="stateport-api",
        exceptions_config=_exceptions_config([_record()]),
        today=TODAY,
    )
    assert len(result["unexplainedFindings"]) == 1


def test_package_version_pin_refuses_drifted_version(tmp_path: Path) -> None:
    scan = _write_scan(tmp_path, [_match(version="3.13.15")])
    result = evaluate_scan(
        scan_path=scan,
        image_id="stateport-api",
        exceptions_config=_exceptions_config([_record(packageVersion="3.13.14")]),
        today=TODAY,
    )
    assert len(result["unexplainedFindings"]) == 1


def test_below_threshold_findings_do_not_gate(tmp_path: Path) -> None:
    scan = _write_scan(tmp_path, [_match(severity="Medium"), _match(severity="Low")])
    result = evaluate_scan(
        scan_path=scan,
        image_id="stateport-api",
        exceptions_config=_exceptions_config([]),
        today=TODAY,
    )
    assert result["unexplainedFindings"] == []
    assert result["findingsBySeverity"] == {"Medium": 1, "Low": 1}


def test_empty_exception_contract_refuses_every_gated_finding(tmp_path: Path) -> None:
    scan = _write_scan(tmp_path, [_match(), _match(severity="Critical")])
    result = evaluate_scan(
        scan_path=scan,
        image_id="stateport-api",
        exceptions_config=_exceptions_config([]),
        today=TODAY,
    )
    assert len(result["unexplainedFindings"]) == 2


def test_schema_rejects_exception_without_remediation(tmp_path: Path) -> None:
    from collect_release_evidence import SCAN_EXCEPTIONS

    record = _record()
    del record["remediation"]
    config = _exceptions_config([record])
    original = SCAN_EXCEPTIONS.read_bytes()
    try:
        SCAN_EXCEPTIONS.write_text(yaml.safe_dump(config), encoding="utf-8")
        with pytest.raises(EvidenceError):
            load_scan_exceptions()
    finally:
        SCAN_EXCEPTIONS.write_bytes(original)
