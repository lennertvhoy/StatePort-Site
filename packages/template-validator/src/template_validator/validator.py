"""High-level validation API for StateDD templates and instances."""

from __future__ import annotations

from pathlib import Path

from statedd_core import (
    INSTANCE_SCHEMA_ID,
    LOCK_SCHEMA_ID,
    MANIFEST_V2_FORMAT,
    Instance,
    SchemaRegistryError,
    find_builtin_schema_registry,
    validate_lifecycle_lock,
)
from statedd_core.lifecycle import LifecycleError, load_template_manifest
from template_validator.checks import (
    INSTANCE_REQUIRED_FILES,
    TEMPLATE_REQUIRED_FILES,
    check_instance_schema,
    check_required_files,
    check_schema_files_exist,
    check_template_ref_resolves,
    check_template_schema,
    check_yaml_parseable,
)
from template_validator.result import ValidationIssue, ValidationResult


def _contract_issues(data: object, logical_id: str, path: str) -> list[ValidationIssue]:
    try:
        registry = find_builtin_schema_registry()
        issues = registry.validate(logical_id, data)
    except (OSError, UnicodeError, ValueError, SchemaRegistryError) as exc:
        return [ValidationIssue(path, f"schema registry validation failed: {exc}")]
    return [ValidationIssue(f"{path}:{issue.path}", issue.message) for issue in issues]


def _manifest_schema_issues(manifest: dict[str, object]) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    try:
        registry = find_builtin_schema_registry()
        for index, asset in enumerate(manifest.get("assets", [])):
            if not isinstance(asset, dict):
                continue
            logical_id = asset.get("schema")
            if logical_id is None:
                continue
            if not isinstance(logical_id, str):
                issues.append(
                    ValidationIssue(
                        f".statedd/manifest.yaml:assets[{index}].schema",
                        "schema ID must be a non-empty string",
                    )
                )
                continue
            registry.schema(logical_id)
        template = manifest.get("template")
        if (
            manifest.get("formatVersion") == MANIFEST_V2_FORMAT
            and isinstance(template, dict)
        ):
            logical_id = template.get("instanceSchemaVersion")
            if not isinstance(logical_id, str):
                issues.append(
                    ValidationIssue(
                        ".statedd/manifest.yaml:template.instanceSchemaVersion",
                        "instance schema version must be a registered string ID",
                    )
                )
            else:
                registry.schema(logical_id)
                declared = {
                    asset.get("schema")
                    for asset in manifest.get("assets", [])
                    if isinstance(asset, dict) and asset.get("path") == "instance.yaml"
                }
                if declared != {logical_id}:
                    issues.append(
                        ValidationIssue(
                            ".statedd/manifest.yaml:template.instanceSchemaVersion",
                            "instance schema version must match the instance.yaml asset schema",
                        )
                    )
    except (OSError, UnicodeError, ValueError, SchemaRegistryError) as exc:
        issues.append(ValidationIssue(".statedd/manifest.yaml", f"schema resolution failed: {exc}"))
    return issues


def validate_template(path: Path | str) -> ValidationResult:
    """Validate a StateSpec template folder."""
    target = Path(path)
    issues: list[ValidationIssue] = []

    manifest_path = target / ".statedd" / "manifest.yaml"
    manifest_data = None
    if manifest_path.exists() and manifest_path.is_file():
        manifest_issues, manifest_data = check_yaml_parseable(manifest_path)
        issues.extend(manifest_issues)
    is_v2 = (
        isinstance(manifest_data, dict)
        and manifest_data.get("formatVersion") == MANIFEST_V2_FORMAT
    )
    required_files = [".statedd/manifest.yaml"] if is_v2 else TEMPLATE_REQUIRED_FILES
    issues.extend(check_required_files(target, required_files))

    template_yaml = target / "template.yaml"
    if template_yaml.exists() and template_yaml.is_file():
        parse_issues, data = check_yaml_parseable(template_yaml)
        issues.extend(parse_issues)
        if data is not None:
            issues.extend(check_template_schema(data))

    if manifest_path.exists():
        try:
            normalized_manifest = load_template_manifest(target)
        except (LifecycleError, OSError, ValueError) as exc:
            issues.append(ValidationIssue(".statedd/manifest.yaml", str(exc)))
        else:
            issues.extend(_manifest_schema_issues(normalized_manifest))

    return ValidationResult(valid=not issues, issues=tuple(issues))


def validate_instance(
    path: Path | str,
    *,
    template_path_override: Path | str | None = None,
) -> ValidationResult:
    """Validate a StateSpec instance folder."""
    target = Path(path)
    issues: list[ValidationIssue] = []

    issues.extend(check_required_files(target, INSTANCE_REQUIRED_FILES))

    instance_yaml = target / "instance.yaml"
    data: object | None = None
    if instance_yaml.exists() and instance_yaml.is_file():
        parse_issues, data = check_yaml_parseable(instance_yaml)
        issues.extend(parse_issues)
        if data is not None:
            issues.extend(check_instance_schema(data))
            issues.extend(_contract_issues(data, INSTANCE_SCHEMA_ID, "instance.yaml"))
            try:
                Instance.from_dict(data)
            except ValueError as exc:
                issues.append(ValidationIssue("instance.yaml", str(exc)))
            spec = data.get("spec") if isinstance(data, dict) else None
            template_ref_path = ""
            template_ref_id = ""
            if isinstance(spec, dict):
                template_ref = spec.get("templateRef", {})
                if isinstance(template_ref, dict):
                    template_ref_id = template_ref.get("id", "")
                    raw_path = template_ref.get("path", "")
                    if isinstance(raw_path, str):
                        template_ref_path = raw_path
                    else:
                        issues.append(
                            ValidationIssue(
                                "spec.templateRef.path",
                                "template path must be a string",
                            )
                        )
            if (
                isinstance(spec, dict)
                and isinstance(template_ref, dict)
                and isinstance(raw_path, str)
                and template_ref_path
            ):
                if template_path_override is None:
                    ref_issues, template_path = check_template_ref_resolves(
                        target, template_ref_path
                    )
                    issues.extend(ref_issues)
                else:
                    template_path = Path(template_path_override)
                    if not template_path.is_dir() or template_path.is_symlink():
                        issues.append(
                            ValidationIssue(
                                "spec.templateRef.path",
                                "trusted template override must be a real directory",
                            )
                        )
                        template_path = None
                if template_path is not None:
                    template_result = validate_template(template_path)
                    for issue in template_result.issues:
                        prefix = "template"
                        if issue.path:
                            prefix = f"template:{issue.path}"
                        issues.append(
                            ValidationIssue(
                                prefix,
                                issue.message,
                            )
                        )
                    if template_result.ok:
                        # v2's manifest is authoritative and does not require a
                        # compatibility template.yaml document.
                        template_yaml_path = template_path / "template.yaml"
                        template_data = None
                        if template_yaml_path.is_file():
                            # Re-read the referenced compatibility template to
                            # discover its legacy state-file declarations.
                            _, template_data = check_yaml_parseable(template_yaml_path)
                        normalized_template = load_template_manifest(template_path)
                        template_metadata = (
                            template_data.get("metadata")
                            if isinstance(template_data, dict)
                            else None
                        )
                        template_id = (
                            template_metadata.get("id")
                            if isinstance(template_metadata, dict)
                            else normalized_template.get("templateId")
                        )
                        if template_ref_id and template_id != template_ref_id:
                            issues.append(
                                ValidationIssue(
                                    "spec.templateRef.id",
                                    f"template id mismatch: instance references "
                                    f"'{template_ref_id}' but template has id "
                                    f"'{template_id}'",
                                )
                            )
                        template_spec = (
                            template_data.get("spec")
                            if isinstance(template_data, dict)
                            else None
                        )
                        lifecycle = (
                            template_spec.get("lifecycle", [])
                            if isinstance(template_spec, dict)
                            else []
                        )
                        status = spec.get("status")
                        if (
                            isinstance(status, str)
                            and isinstance(lifecycle, list)
                            and status not in lifecycle
                        ):
                            issues.append(
                                ValidationIssue(
                                    "spec.status",
                                    f"instance status {status!r} is not declared by the template lifecycle",
                                )
                            )
                        schema_list = (
                            template_spec.get("schemas", [])
                            if isinstance(template_spec, dict)
                            else []
                        )
                        issues.extend(
                            check_schema_files_exist(
                                target,
                                schema_list,
                                path_prefix="state",
                            )
                        )

    lock_path = target / ".statedd" / "lock.yaml"
    if lock_path.exists():
        if not lock_path.is_file() or lock_path.is_symlink():
            issues.append(ValidationIssue(".statedd/lock.yaml", "lock must be a regular non-symlink file"))
        else:
            lock_parse_issues, lock_data = check_yaml_parseable(lock_path)
            issues.extend(
                ValidationIssue(".statedd/lock.yaml", issue.message)
                for issue in lock_parse_issues
            )
            if isinstance(lock_data, dict):
                issues.extend(_contract_issues(lock_data, LOCK_SCHEMA_ID, ".statedd/lock.yaml"))
                try:
                    validate_lifecycle_lock(lock_data)
                except LifecycleError as exc:
                    issues.append(ValidationIssue(".statedd/lock.yaml", str(exc)))
                if isinstance(data, dict):
                    metadata = data.get("metadata")
                    instance_id = metadata.get("id") if isinstance(metadata, dict) else None
                    if isinstance(instance_id, str) and lock_data.get("instanceId") != instance_id:
                        issues.append(
                            ValidationIssue(
                                ".statedd/lock.yaml:instanceId",
                                "lock instanceId does not match instance metadata.id",
                            )
                        )

    return ValidationResult(valid=not issues, issues=tuple(issues))
