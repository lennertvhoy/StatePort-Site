#!/usr/bin/env python3
"""Regression coverage for StateSpec logical schemas and approval metadata."""

from __future__ import annotations

import json
import os
import shutil
import sys
import tempfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
for relative in ("packages/statedd-core/src", "scripts"):
    sys.path.insert(0, str(ROOT / relative))

from statedd_core import (  # noqa: E402
    INSTANCE_SCHEMA_ID,
    Instance,
    SchemaRegistryError,
    load_schema_registry,
)
from statedd_core.yaml import parse_yaml_text  # noqa: E402
from validate_statespec_schema_registry import validate_repository  # noqa: E402


def test_repository_registry_and_generated_locks_pass() -> None:
    result = validate_repository(ROOT)
    assert result["observed"] == [
        "statedd.stateport.io/instance/v1alpha1",
        "statedd.stateport.io/lock/v1",
    ]
    assert result["generatedLockVariants"] == ["v1", "v2-local"]


@pytest.mark.parametrize(
    "decision",
    ["auto", "require_approval", "require_admin", 1, True],
)
def test_legacy_or_non_string_approval_values_fail_closed(decision: object) -> None:
    value = parse_yaml_text(
        (ROOT / "instances/demo-classdd/instance.yaml").read_text(encoding="utf-8")
    )
    value["spec"]["approvalPolicy"]["L2"] = decision
    with pytest.raises(ValueError, match="require_explicit_approval"):
        Instance.from_dict(value)
    registry = load_schema_registry(
        ROOT / "config/statespec-schema-registry.v1.json", root=ROOT
    )
    assert registry.validate(INSTANCE_SCHEMA_ID, value)


def test_missing_policy_keeps_all_write_levels_explicit() -> None:
    value = parse_yaml_text(
        (ROOT / "instances/demo-classdd/instance.yaml").read_text(encoding="utf-8")
    )
    value["spec"].pop("approvalPolicy")
    policy = Instance.from_dict(value).spec.approval_policy
    assert {policy.L2, policy.L3, policy.L4, policy.L5} == {
        "require_explicit_approval"
    }


def test_registry_refuses_traversal_and_symlinks() -> None:
    with tempfile.TemporaryDirectory() as temporary:
        root = Path(temporary) / "repo"
        shutil.copytree(ROOT / "schemas", root / "schemas")
        (root / "config").mkdir(parents=True)
        value = json.loads(
            (ROOT / "config/statespec-schema-registry.v1.json").read_text(
                encoding="utf-8"
            )
        )
        value["entries"][0]["path"] = "../outside.json"
        path = root / "config/registry.json"
        path.write_text(json.dumps(value), encoding="utf-8")
        with pytest.raises(SchemaRegistryError, match="escapes"):
            load_schema_registry(path, root=root)

        value["entries"][0]["path"] = "schemas/linked.json"
        os.symlink(root / "schemas/instance.v1alpha1.schema.json", root / "schemas/linked.json")
        path.write_text(json.dumps(value), encoding="utf-8")
        with pytest.raises(SchemaRegistryError, match="symlink"):
            load_schema_registry(path, root=root)


def test_schema_id_mismatch_fails() -> None:
    with tempfile.TemporaryDirectory() as temporary:
        root = Path(temporary) / "repo"
        shutil.copytree(ROOT / "schemas", root / "schemas")
        (root / "config").mkdir(parents=True)
        registry_path = root / "config/registry.json"
        registry_path.write_text(
            (ROOT / "config/statespec-schema-registry.v1.json").read_text(
                encoding="utf-8"
            ),
            encoding="utf-8",
        )
        schema_path = root / "schemas/instance.v1alpha1.schema.json"
        schema = json.loads(schema_path.read_text(encoding="utf-8"))
        schema["$id"] = "wrong"
        schema_path.write_text(json.dumps(schema), encoding="utf-8")
        with pytest.raises(SchemaRegistryError, match="mismatched"):
            load_schema_registry(registry_path, root=root)
