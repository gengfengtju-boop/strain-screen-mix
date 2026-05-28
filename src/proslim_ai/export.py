from __future__ import annotations

import csv
from pathlib import Path


def _ascii_safe(value: object) -> str:
    if value is None:
        return ""
    return str(value).encode("ascii", errors="xmlcharrefreplace").decode("ascii")


def export_ascii_safe_csv(input_path: Path, output_path: Path) -> int:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with input_path.open("r", newline="", encoding="utf-8-sig") as source:
        reader = csv.DictReader(source)
        fieldnames = reader.fieldnames or []
        with output_path.open("w", newline="", encoding="utf-8") as target:
            writer = csv.DictWriter(target, fieldnames=fieldnames)
            writer.writeheader()
            rows = 0
            for row in reader:
                writer.writerow({field: _ascii_safe(row.get(field, "")) for field in fieldnames})
                rows += 1
    return rows

