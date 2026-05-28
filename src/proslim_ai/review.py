from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path

from .config import load_yaml


OUTCOME_HINT_COLUMNS = {
    "weight": "body_weight_effect_hint",
    "BMI": "bmi_effect_hint",
    "waist": "waist_effect_hint",
    "body_fat": "body_fat_effect_hint",
    "glucose": "glucose_effect_hint",
    "lipid": "lipid_effect_hint",
    "microbiome": "microbiome_effect_hint",
}


@dataclass(frozen=True)
class ReviewWorksheetResult:
    hints_path: Path
    outcome_output: Path
    intervention_output: Path
    evidence_rows: int
    outcome_rows: int
    intervention_rows: int


def _text(value: object) -> str:
    return "" if value is None else str(value).strip()


def _empty(fields: list[str]) -> dict[str, str]:
    return {field: "" for field in fields}


def build_review_worksheets(
    config_dir: Path,
    hints_path: Path,
    outcome_output: Path,
    intervention_output: Path,
    reviewer: str = "",
) -> ReviewWorksheetResult:
    config = load_yaml(config_dir / "review_fields.yaml")
    outcome_fields = config["outcome_review_fields"]
    intervention_fields = config["intervention_review_fields"]

    with hints_path.open("r", newline="", encoding="utf-8-sig") as handle:
        hint_rows = list(csv.DictReader(handle))

    outcome_rows: list[dict[str, str]] = []
    intervention_rows: list[dict[str, str]] = []

    for row in hint_rows:
        common = {
            "evidence_id": _text(row.get("evidence_id")),
            "source_database": _text(row.get("source_database")),
            "source_accession": _text(row.get("source_accession")),
            "title": _text(row.get("title")),
        }
        p_value_hint = _text(row.get("p_value_hint"))
        sample_size_hint = _text(row.get("sample_size_hint"))

        for outcome_domain, hint_column in OUTCOME_HINT_COLUMNS.items():
            suggested_text = _text(row.get(hint_column))
            if not suggested_text:
                continue
            review_row = _empty(outcome_fields)
            review_row.update(
                {
                    **common,
                    "outcome_domain": outcome_domain,
                    "suggested_text": suggested_text,
                    "suggested_p_value": p_value_hint,
                    "sample_size_confirmed": sample_size_hint,
                    "extraction_source": "detail_hint",
                    "reviewer": reviewer,
                    "review_status": "pending",
                }
            )
            outcome_rows.append(review_row)

        intervention_row = _empty(intervention_fields)
        intervention_row.update(
            {
                **common,
                "intervention_component": "primary_intervention",
                "suggested_intervention": _text(row.get("intervention_hint")),
                "suggested_duration": _text(row.get("duration_hint")),
                "suggested_cfu": _text(row.get("cfu_hint")),
                "suggested_dose": _text(row.get("dose_hint")),
                "reviewer": reviewer,
                "review_status": "pending",
            }
        )
        intervention_rows.append(intervention_row)

    outcome_output.parent.mkdir(parents=True, exist_ok=True)
    intervention_output.parent.mkdir(parents=True, exist_ok=True)
    with outcome_output.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=outcome_fields)
        writer.writeheader()
        writer.writerows(outcome_rows)
    with intervention_output.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=intervention_fields)
        writer.writeheader()
        writer.writerows(intervention_rows)

    return ReviewWorksheetResult(
        hints_path=hints_path,
        outcome_output=outcome_output,
        intervention_output=intervention_output,
        evidence_rows=len(hint_rows),
        outcome_rows=len(outcome_rows),
        intervention_rows=len(intervention_rows),
    )

