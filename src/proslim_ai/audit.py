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
    configuration_errors: list[str]

    @property
    def ok(self) -> bool:
        return (
            self.project_check.ok
            and not self.template_errors
            and not self.source_registry_errors
            and not self.configuration_errors
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


def audit_model_configuration(root: Path) -> list[str]:
    validation = load_yaml(root / "config" / "validation_config.yaml")
    scoring = load_yaml(root / "config" / "scoring_weights.yaml")
    errors: list[str] = []

    strategies = validation.get("validation_strategies", {})
    for name in ("external_database_validation", "country_region_validation"):
        strategy = strategies.get(name, {})
        if strategy.get("enabled") and strategy.get("implementation_status", "").startswith(
            "planned"
        ):
            errors.append(f"{name}: planned validation cannot be enabled")

    for section_name in (
        "combination_scores",
        "combination_design_weights",
        "robust_optimizer.score_weight_center",
    ):
        if "." in section_name:
            parent, child = section_name.split(".", 1)
            weights = scoring.get(parent, {}).get(child, {})
        else:
            weights = scoring.get(section_name, {})
        try:
            weight_sum = sum(float(value) for value in weights.values())
        except (AttributeError, TypeError, ValueError):
            errors.append(f"{section_name}: all weights must be numeric")
        else:
            if abs(weight_sum - 1.0) > 1e-9:
                errors.append(
                    f"{section_name}: weights must sum to 1.0; found {weight_sum:.6f}"
                )

    concentration = scoring.get("robust_optimizer", {}).get("dirichlet_concentration", 0)
    if float(concentration) <= 0:
        errors.append("robust_optimizer.dirichlet_concentration must be positive")

    generation = scoring.get("combination_generation", {})
    minimum = int(generation.get("min_strains", 0))
    maximum = int(generation.get("max_strains", 0))
    if minimum < 1 or maximum < minimum:
        errors.append("combination_generation: require 1 <= min_strains <= max_strains")
    return errors


def audit_project(root: Path) -> AuditResult:
    from .paths import ProjectPaths

    return AuditResult(
        project_check=check_project(ProjectPaths(root)),
        template_errors=audit_templates(root),
        source_registry_errors=audit_source_registry(root),
        configuration_errors=audit_model_configuration(root),
    )
