from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path

from .config import load_table_schemas


@dataclass(frozen=True)
class EvidenceMergeResult:
    input_paths: list[Path]
    output_path: Path
    rows_read: int
    rows_written: int
    duplicates_removed: int


def _value(row: dict[str, str], field: str) -> str:
    return str(row.get(field, "") or "").strip()


def _dedup_key(row: dict[str, str]) -> tuple[str, str]:
    pmid = _value(row, "pmid")
    doi = _value(row, "doi").lower()
    source_database = _value(row, "source_database")
    source_accession = _value(row, "source_accession")
    if pmid:
        return ("pmid", pmid)
    if doi:
        return ("doi", doi)
    return (source_database, source_accession)


def merge_evidence_candidates(
    config_dir: Path,
    input_paths: list[Path],
    output_path: Path,
) -> EvidenceMergeResult:
    schemas = load_table_schemas(config_dir)
    fieldnames = schemas["evidence_registry"]
    seen: set[tuple[str, str]] = set()
    merged_rows: list[dict[str, str]] = []
    rows_read = 0

    for input_path in input_paths:
        with input_path.open("r", newline="", encoding="utf-8-sig") as handle:
            reader = csv.DictReader(handle)
            for row in reader:
                rows_read += 1
                key = _dedup_key(row)
                if key in seen:
                    continue
                seen.add(key)
                merged_rows.append({field: _value(row, field) for field in fieldnames})

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(merged_rows)

    return EvidenceMergeResult(
        input_paths=input_paths,
        output_path=output_path,
        rows_read=rows_read,
        rows_written=len(merged_rows),
        duplicates_removed=rows_read - len(merged_rows),
    )

