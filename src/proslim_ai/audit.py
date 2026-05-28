from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .config import load_table_schemas, load_yaml
from .project import CheckResult, check_project
from .schemas import validate_csv_schema


@dataclass(frozen=True)
class AuditResult:
    project_check: CheckResult
    template_errors: list[str]
    source_registry_errors: list[str]

    @property
    def ok(self) -> bool:
        return (
            self.project_check.ok
            and not self.template_errors
            and not self.source_registry_errors
        )


def audit_templates(root: Path) -> list[str]:
    schemas = load_table_schemas(root / "config")
    errors: list[str] = []
    template_dir = root / "data" / "metadata" / "templates"
    for table_name in schemas:
        template_path = template_dir / f"{table_name}.csv"
        if not template_path.exists():
            errors.append(f"missing template: {template_path}")
            continue
        result = validate_csv_schema(root / "config", table_name, template_path, allow_extra_columns=False)
        if result.missing_columns:
            errors.append(f"{table_name}: {', '.join(result.missing_columns)}")
    return errors


def audit_source_registry(root: Path) -> list[str]:
    evidence_config = load_yaml(root / "config" / "evidence_config.yaml")
    source_registry = load_yaml(root / "config" / "source_registry.yaml")
    registered = set(source_registry.get("sources", {}))
    errors: list[str] = []

    allowed_groups = evidence_config.get("allowed_database_sources", {})
    for group_name, source_names in allowed_groups.items():
        for source_name in source_names:
            if source_name not in registered:
                errors.append(f"{group_name}: source is not registered: {source_name}")

    for source_name, source_info in source_registry.get("sources", {}).items():
        if not isinstance(source_info, dict):
            errors.append(f"{source_name}: source entry must be a mapping")
            continue
        for required_field in ("category", "homepage", "identifier_examples"):
            if required_field not in source_info:
                errors.append(f"{source_name}: missing {required_field}")
    return errors


def audit_project(root: Path) -> AuditResult:
    from .paths import ProjectPaths

    return AuditResult(
        project_check=check_project(ProjectPaths(root)),
        template_errors=audit_templates(root),
        source_registry_errors=audit_source_registry(root),
    )

