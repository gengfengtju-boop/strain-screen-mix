from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class ReviewSubsetResult:
    output_path: Path
    rows_written: int
    selected_evidence: int


def _text(value: object) -> str:
    return "" if value is None else str(value).strip()


def _selected_evidence_ids(prediction_path: Path, confidence_levels: set[str]) -> set[str]:
    selected: set[str] = set()
    with prediction_path.open("r", newline="", encoding="utf-8-sig") as handle:
        for row in csv.DictReader(handle):
            if _text(row.get("confidence_level")) in confidence_levels:
                selected.add(_text(row.get("evidence_id")))
    return selected


def filter_review_worksheet(
    prediction_path: Path,
    review_path: Path,
    output_path: Path,
    confidence_levels: set[str],
) -> ReviewSubsetResult:
    selected = _selected_evidence_ids(prediction_path, confidence_levels)
    with review_path.open("r", newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        fieldnames = reader.fieldnames or []
        rows = [row for row in reader if _text(row.get("evidence_id")) in selected]

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    return ReviewSubsetResult(
        output_path=output_path,
        rows_written=len(rows),
        selected_evidence=len(selected),
    )

