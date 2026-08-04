"""Focused persistent StudyDD application journey without private data."""

from __future__ import annotations

import os
import json
from pathlib import Path
import socket
import sys
from urllib.error import HTTPError
from urllib.request import Request, urlopen

import pytest

ROOT = Path(__file__).resolve().parents[1]
for relative in (
    "packages/statedd-core/src",
    "packages/template-validator/src",
    "packages/persistent-app/src",
    "packages/instance-backup/src",
    "packages/instance-catalog/src",
    "packages/diagnostics/src",
    "apps/runner/src",
):
    path = ROOT / relative
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from stateport_persistent_app import LocalLayout, PersistentApp  # noqa: E402
from service_test_product import service_product_fixture  # noqa: E402


@pytest.mark.skipif(not os.environ.get("STATEPORT_STUDYDD_MIRROR"), reason="set STATEPORT_STUDYDD_MIRROR to run the cross-repository journey")
def test_persistent_create_inspect_run_backup_and_metadata_reimport(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "config"))
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path / "data"))
    monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path / "state"))
    app = PersistentApp(LocalLayout.from_environment())
    app.setup_init()
    destination = app.layout.instances_root / "StudyDD-AI103"
    plan = app.plan_create(
        source_profile="builtin:studydd-local-alpha",
        destination=str(destination),
            instance_id="studydd-ai103",
            name="AI-103 Study",
            owner_name="Synthetic Owner",
            owner_handle="synthetic-owner",
            target_id="ai-103",
        target_title="AI-103",
        allow_development_candidate=True,
    )
    created = app.create(plan, app.approve(plan))
    assert created["ok"] is True
    assert app.inspect("studydd-ai103")["source"]["resolvedCommit"] == plan["source"]["resolvedCommit"]
    run = app.synthetic_run("studydd-ai103")
    assert run["status"] == "passed"
    backup = app.backup("studydd-ai103")
    assert backup["validation"] == "verified"
    app.setup_uninstall()
    assert destination.is_dir()
    app.setup_init()
    imported = app.import_instance(str(destination))
    assert imported["ok"] is True
    assert app.inspect("studydd-ai103")["recovery"]["status"] == "verified"


def test_service_stop_waits_for_listener_before_restart(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "config"))
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path / "data"))
    monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path / "state"))
    app = PersistentApp(LocalLayout.from_environment())
    app.setup_init()
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        port = int(probe.getsockname()[1])
    product_root = service_product_fixture(tmp_path, ROOT)
    first = app.service_start(port=port, repo_root=product_root)
    assert first["status"] == "running"
    first_pid = first["pid"]
    held_connection = socket.create_connection(("127.0.0.1", port), timeout=1)
    try:
        assert app.service_stop()["status"] == "stopped"
        assert app.service_status()["status"] == "stopped"
        with pytest.raises(OSError):
            socket.create_connection(("127.0.0.1", port), timeout=0.2)
        with socket.socket() as rebound:
            rebound.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            rebound.bind(("127.0.0.1", port))
        second = app.service_start(port=port, repo_root=product_root)
        assert second["status"] == "running" and second["pid"] != first_pid
    finally:
        held_connection.close()
        app.service_stop()


def test_recovery_revalidates_backup_archive_and_emits_receipt(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "config"))
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path / "data"))
    monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path / "state"))
    app = PersistentApp(LocalLayout.from_environment())
    app.setup_init()
    instance = app.layout.instances_root / "backup-fixture"
    (instance / ".statedd").mkdir(parents=True)
    (instance / "state").mkdir()
    (instance / "instance.yaml").write_text(
        "metadata:\n  id: backup-fixture\n  name: Backup fixture\n",
        encoding="utf-8",
    )
    (instance / ".statedd" / "lock.yaml").write_text(
        json.dumps({
            "formatVersion": "statedd.lock/v1",
            "instanceId": "backup-fixture",
            "template": {"id": "synthetic-template", "source": {"sourceDigest": "sha256:" + "1" * 64}},
            "files": [
                {"path": "instance.yaml", "owner": "instance", "sensitivity": "private"},
                {"path": ".statedd/lock.yaml", "owner": "generated", "sensitivity": "internal"},
                {"path": "state/notes.md", "owner": "instance", "sensitivity": "private"},
            ],
        }),
        encoding="utf-8",
    )
    (instance / "state" / "notes.md").write_text("durable backup fixture\n", encoding="utf-8")
    app.catalog.register(instance, instance_id="backup-fixture", name="Backup fixture", source={"templateId": "synthetic-template"})

    summary = app.backup("backup-fixture")
    assert summary["backupReceipt"]["formatVersion"] == "stateport.backup-receipt/v1"
    assert app.inspect("backup-fixture")["recovery"]["status"] == "verified"

    archive = Path(str(summary["archive"]))
    archive.write_bytes(archive.read_bytes() + b"tampered")
    recovery = app.inspect("backup-fixture")["recovery"]
    assert recovery["status"] == "degraded"
    assert recovery["operatorInspectionRequired"] is True
    assert recovery["verificationIssues"]


def test_service_exposes_typed_global_and_application_settings_with_receipts(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "config"))
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path / "data"))
    monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path / "state"))
    app = PersistentApp(LocalLayout.from_environment())
    app.setup_init()
    instance = app.layout.instances_root / "settings-fixture"
    instance.mkdir(parents=True)
    app.catalog.register(instance, instance_id="settings-fixture", name="Settings fixture", source={"templateId": "stateport.development-reference"})
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        port = int(probe.getsockname()[1])
    app.service_start(port=port)
    base = f"http://127.0.0.1:{port}"

    def session() -> tuple[str, str]:
        with urlopen(f"{base}/session") as response:
            payload = json.loads(response.read())["result"]
            return response.headers["Set-Cookie"].split(";", 1)[0], payload["csrfToken"]

    def request(path: str, cookie: str, csrf: str, method: str = "GET", body: dict[str, object] | None = None) -> dict[str, object]:
        headers = {"Cookie": cookie}
        data = None
        if body is not None:
            data = json.dumps(body).encode()
            headers.update({"Content-Type": "application/json", "Origin": base, "X-StatePort-CSRF": csrf})
        with urlopen(Request(f"{base}{path}", data=data, method=method, headers=headers)) as response:
            return json.loads(response.read())["result"]

    try:
        cookie, csrf = session()
        global_settings = request("/v1/settings", cookie, csrf)
        assert global_settings["formatVersion"] == "stateport.settings-projection/v1"
        application_settings = request("/v1/instances/settings-fixture/settings", cookie, csrf)
        assert application_settings["scope"] == "application"
        application_keys = {
            field["key"]
            for section in application_settings["sections"]
            for field in section["fields"]
        }
        assert "general.appearance" not in application_keys
        with pytest.raises(HTTPError) as application_scope_error:
            request(
                "/v1/instances/settings-fixture/settings",
                cookie,
                csrf,
                "POST",
                {"expectedRevision": 0, "changes": {"general.appearance": "dark"}},
            )
        # The service classifies a scope/authority mismatch as a conflict so
        # clients know to reload the effective projection rather than retrying
        # the same inert field.
        assert application_scope_error.value.code == 409
        changed = request("/v1/settings", cookie, csrf, "POST", {"expectedRevision": 0, "changes": {"general.defaultLandingView": "catalog"}})
        assert changed["receipt"]["formatVersion"] == "stateport.settings-mutation-receipt/v1"
        assert changed["projection"]["revision"] == 1
        with pytest.raises(HTTPError) as stale:
            request("/v1/settings", cookie, csrf, "POST", {"expectedRevision": 0, "changes": {"context.mode": "deeper"}})
        assert stale.value.code == 409
    finally:
        app.service_stop()
    second = app.service_start(port=port)
    assert second["status"] == "running"
    assert app.service_stop()["status"] == "stopped"


def test_inspect_describes_registered_fixture_without_instance_materialization(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """A registered development fixture (application.yaml only) must inspect honestly.

    Regression for the ProjectState CTO pilot P1: the instance was registered as a
    raw fixture and bypassed the install-time instance.yaml/.statedd/lock.yaml
    materialization, which previously crashed inspect() with operation_failed and
    made the application impossible to open from the browser.
    """
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "config"))
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path / "data"))
    monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path / "state"))
    app = PersistentApp(LocalLayout.from_environment())
    app.setup_init()

    fixture = app.layout.instances_root / "dev-raw-fixture"
    fixture.mkdir(parents=True)
    (fixture / "application.yaml").write_text(
        "formatVersion: stateport.application/v1\n"
        "applicationId: stateport.development-reference\n"
        "displayName: ProjectState\n"
        "description: A public-safe development application.\n"
        "sourceProfile: fixture:development-reference\n"
        "productionEligible: false\n",
        encoding="utf-8",
    )
    (fixture / "actions.yaml").write_text(
        "formatVersion: stateport.application-action/v1\n"
        "applicationId: stateport.development-reference\n"
        "actions: []\n",
        encoding="utf-8",
    )
    app.catalog.register(
        fixture,
        instance_id="dev-raw-fixture",
        name="Development raw fixture",
        source={"templateId": "stateport.development-reference"},
    )

    result = app.inspect("dev-raw-fixture")

    assert result["instance"]["id"] == "dev-raw-fixture"
    assert result["instance"]["pathState"] == "present"
    assert result["instance"]["descriptor"]["kind"] == "Application"
    assert result["source"]["templateId"] == "stateport.development-reference"
    assert result["ownership"]["counts"]["instance"] == 2
    assert "application.yaml" in result["ownership"]["paths"]["instance"]
    assert result["health"] == "valid"


def test_inspect_uses_lock_manifest_when_present(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """The StateSpec-style lock path stays authoritative when materialized."""

    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "config"))
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path / "data"))
    monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path / "state"))
    app = PersistentApp(LocalLayout.from_environment())
    app.setup_init()

    fixture = app.layout.instances_root / "lock-backed"
    fixture.mkdir(parents=True)
    (fixture / "instance.yaml").write_text("kind: Instance\nspec:\n  mode: guided\n", encoding="utf-8")
    (fixture / ".statedd").mkdir()
    (fixture / ".statedd" / "lock.yaml").write_text(
        "formatVersion: stateport.application-lock/v1\n"
        "template:\n"
        "  id: studydd\n"
        "  version: '1.2.3'\n"
        "  source:\n"
        "    repository: https://example.org/study.git\n"
        "    resolvedCommit: abcdef\n"
        "    profile: builtin\n"
        "    checkoutLocation: src\n"
        "files:\n"
        "  - {owner: template, path: AGENTS.md}\n"
        "  - {owner: instance, path: state/STUDY_STATE.yaml}\n",
        encoding="utf-8",
    )
    app.catalog.register(fixture, instance_id="lock-backed", name="Lock backed", source={"templateId": "studydd"})

    result = app.inspect("lock-backed")

    assert result["instance"]["descriptor"] == {"kind": "Instance", "mode": "guided"}
    assert result["version"] == "1.2.3"
    assert result["source"]["repository"] == "https://example.org/study.git"
    assert result["source"]["resolvedCommit"] == "abcdef"
    assert "profile" not in result["source"]
    assert "checkoutLocation" not in result["source"]
    assert result["ownership"]["counts"] == {"template": 1, "instance": 1, "generated": 0, "override": 0}
    assert result["ownership"]["paths"]["template"] == ["AGENTS.md"]
