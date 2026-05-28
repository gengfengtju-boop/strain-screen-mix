from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re
from typing import Any

from .config import load_yaml
from .schemas import validate_csv_schema


@dataclass(frozen=True)
class ProvenanceValidationResult:
    table_name: str
    path: Path
    rows_checked: int
    schema_missing_columns: list[str]
    row_errors: list[str]

    @property
    def ok(self) -> bool:
        return not self.schema_missing_columns and not self.row_errors


def _has_value(value: Any) -> bool:
    if value is None:
        return False
    text = str(value).strip()
    return bool(text) and text.lower() not in {"na", "nan", "none", "unknown"}


def _identifier_text(value: Any) -> str:
    text = "" if value is None else str(value).strip()
    if text.endswith(".0") and text[:-2].isdigit():
        return text[:-2]
    return text


def _row_has_any(row: Any, fields: list[str]) -> bool:
    return any(_has_value(row.get(field)) for field in fields)


DOI_PATTERN = re.compile(r"^10\.\d{4,9}/\S+$", re.IGNORECASE)
PMID_PATTERN = re.compile(r"^\d{1,9}$")
URL_PATTERN = re.compile(r"^https?://\S+$", re.IGNORECASE)


def _split_multi_value(value: Any) -> list[str]:
    if not _has_value(value):
        return []
    return [
        _identifier_text(item)
        for item in re.split(r"[;,|]", str(value))
        if item.strip() and item.strip().lower() not in {"na", "nan", "none", "unknown"}
    ]


def _validate_identifier_format(row_number: int, field: str, value: Any) -> list[str]:
    errors: list[str] = []
    for item in _split_multi_value(value):
        if "doi" in field.lower() and not DOI_PATTERN.match(item):
            errors.append(f"row {row_number}: invalid DOI format in {field}: {item}")
        if "pmid" in field.lower() and not PMID_PATTERN.match(item):
            errors.append(f"row {row_number}: invalid PMID format in {field}: {item}")
        if field.endswith("_url") or field == "source_url":
            if not URL_PATTERN.match(item):
                errors.append(f"row {row_number}: invalid URL format in {field}: {item}")
    return errors


def _validate_registered_source(
    row_number: int,
    field: str,
    value: Any,
    registered_sources: set[str],
) -> list[str]:
    if not _has_value(value):
        return []
    errors: list[str] = []
    for item in _split_multi_value(value):
        if item not in registered_sources:
            errors.append(f"row {row_number}: unregistered source in {field}: {item}")
    return errors


def validate_provenance(config_dir: Path, table_name: str, csv_path: Path) -> ProvenanceValidationResult:
    import pandas as pd

    schema_result = validate_csv_schema(config_dir, table_name, csv_path)
    if not schema_result.ok:
        return ProvenanceValidationResult(
            table_name=table_name,
            path=csv_path,
            rows_checked=0,
            schema_missing_columns=schema_result.missing_columns,
            row_errors=[],
        )

    evidence_config = load_yaml(config_dir / "evidence_config.yaml")
    source_registry = load_yaml(config_dir / "source_registry.yaml")
    registered_sources = set(source_registry.get("sources", {}))
    rules = evidence_config.get("minimum_evidence_rules", {}).get(table_name)
    if not rules:
        return ProvenanceValidationResult(
            table_name=table_name,
            path=csv_path,
            rows_checked=0,
            schema_missing_columns=[],
            row_errors=[f"No provenance rule configured for table '{table_name}'."],
        )

    frame = pd.read_csv(csv_path).fillna("")
    row_errors: list[str] = []

    for index, row in frame.iterrows():
        row_number = index + 2
        for field in (
            "source_database",
            "genome_database",
            "annotation_database",
            "pathway_database",
            "database_source",
        ):
            if field in frame.columns:
                row_errors.extend(
                    _validate_registered_source(row_number, field, row.get(field), registered_sources)
                )
        for field in (
            "source_url",
            "genome_url",
            "publication_doi",
            "publication_pmid",
            "evidence_doi",
            "evidence_pmid",
            "evidence_doi_list",
            "evidence_pmid_list",
        ):
            if field in frame.columns:
                row_errors.extend(_validate_identifier_format(row_number, field, row.get(field)))
        if rules.get("require_genome_accession") and not _has_value(row.get("genome_accession")):
            row_errors.append(f"row {row_number}: missing genome_accession")
        if rules.get("require_genome_database") and not _has_value(row.get("genome_database")):
            row_errors.append(f"row {row_number}: missing genome_database")
        if rules.get("require_source_strain_ids") and not _has_value(row.get("source_strain_ids")):
            row_errors.append(f"row {row_number}: missing source_strain_ids")
        if rules.get("require_at_least_one_source_identifier"):
            fields = rules.get("source_identifier_fields", [])
            if not _row_has_any(row, fields):
                row_errors.append(
                    f"row {row_number}: missing source identifier; expected one of {', '.join(fields)}"
                )
        if rules.get("require_at_least_one_publication_identifier"):
            fields = rules.get("publication_identifier_fields", [])
            if not _row_has_any(row, fields):
                row_errors.append(
                    f"row {row_number}: missing publication identifier; expected one of {', '.join(fields)}"
                )
        if rules.get("require_manual_curation_fields"):
            for field in rules.get("manual_curation_fields", []):
                if not _has_value(row.get(field)):
                    row_errors.append(f"row {row_number}: missing manual curation field: {field}")

    return ProvenanceValidationResult(
        table_name=table_name,
        path=csv_path,
        rows_checked=len(frame),
        schema_missing_columns=[],
        row_errors=row_errors,
    )
