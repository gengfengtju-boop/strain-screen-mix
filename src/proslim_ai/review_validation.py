from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class ReviewValidationResult:
    path: Path
    rows_checked: int
    errors: list[str]

    @property
    def ok(self) -> bool:
        return not self.errors


def _text(value: object) -> str:
    return "" if value is None else str(value).strip()


def validate_outcome_review(path: Path) -> ReviewValidationResult:
    errors: list[str] = []
    rows_checked = 0
    with path.open("r", newline="", encoding="utf-8-sig") as handle:
        for index, row in enumerate(csv.DictReader(handle), start=2):
            rows_checked += 1
            if _text(row.get("review_status")) != "extracted":
                continue
            for field in ("final_value", "final_unit", "final_direction", "p_value_confirmed"):
                if not _text(row.get(field)):
                    errors.append(f"row {index}: extracted row missing {field}")
    return ReviewValidationResult(path=path, rows_checked=rows_checked, errors=errors)

