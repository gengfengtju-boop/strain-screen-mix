from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path

from .config import load_table_schemas


OUTCOME_TO_COLUMNS = {
    "weight": ["weight_change", "weight_change_percent"],
    "BMI": ["BMI_change"],
    "waist": ["waist_change"],
    "body_fat": ["body_fat_change"],
    "glucose": ["FBG_change", "FINS_change", "HOMA_IR_change"],
    "lipid": ["TG_change", "TC_change", "LDL_change", "HDL_change"],
}


@dataclass(frozen=True)
class FinalizeResult:
    output_path: Path
    rows_written: int
    extracted_review_rows: int


def _text(value: object) -> str:
    return "" if value is None else str(value).strip()


def finalize_clinical_outcomes(
    config_dir: Path,
    draft_path: Path,
    review_path: Path,
    output_path: Path,
) -> FinalizeResult:
    schemas = load_table_schemas(config_dir)
    fields = schemas["clinical_outcome"]

    with draft_path.open("r", newline="", encoding="utf-8-sig") as handle:
        draft_rows = list(csv.DictReader(handle))
    by_study = {_text(row.get("study_id")): {field: _text(row.get(field)) for field in fields} for row in draft_rows}

    extracted_count = 0
    with review_path.open("r", newline="", encoding="utf-8-sig") as handle:
        for row in csv.DictReader(handle):
            if _text(row.get("review_status")) != "extracted":
                continue
            evidence_id = _text(row.get("evidence_id"))
            outcome_domain = _text(row.get("outcome_domain"))
            final_value = _text(row.get("final_value"))
            if not evidence_id or not final_value:
                continue
            target = by_study.setdefault(evidence_id, {field: "" for field in fields})
            target["study_id"] = evidence_id
            target["subject_id"] = target.get("subject_id") or "aggregate_study_level"
            for column in OUTCOME_TO_COLUMNS.get(outcome_domain, []):
                if not target.get(column) or target.get(column) == "needs_manual_extraction":
                    target[column] = final_value
                    break
            extracted_count += 1

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(by_study.values())

    return FinalizeResult(output_path, len(by_study), extracted_count)

