from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class ExtractionQueueResult:
    input_path: Path
    output_path: Path
    rows_read: int
    rows_written: int
    excluded_evidence: int


def build_extraction_queue(
    screening_path: Path,
    output_path: Path,
    priority_levels: set[str],
    top_n: int,
    min_relevance_score: int = 0,
    exclude_paths: list[Path] | None = None,
) -> ExtractionQueueResult:
    excluded = _load_excluded_ids(exclude_paths or [])
    with screening_path.open("r", newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        fieldnames = list(reader.fieldnames or [])
        rows = list(reader)

    candidates = [
        row
        for row in rows
        if _text(row.get("priority")) in priority_levels
        and _as_int(row.get("relevance_score")) >= min_relevance_score
        and _text(row.get("evidence_id")) not in excluded
    ]
    candidates.sort(key=_queue_sort_key)
    selected = candidates[:top_n]

    output_fields = [*fieldnames]
    for field in ("queue_rank", "queue_reason"):
        if field not in output_fields:
            output_fields.append(field)

    for rank, row in enumerate(selected, start=1):
        row["queue_rank"] = str(rank)
        row["queue_reason"] = _queue_reason(row)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=output_fields)
        writer.writeheader()
        writer.writerows(selected)

    return ExtractionQueueResult(
        input_path=screening_path,
        output_path=output_path,
        rows_read=len(rows),
        rows_written=len(selected),
        excluded_evidence=len(excluded),
    )


def _load_excluded_ids(paths: list[Path]) -> set[str]:
    excluded: set[str] = set()
    for path in paths:
        if not path.exists():
            continue
        with path.open("r", newline="", encoding="utf-8-sig") as handle:
            for row in csv.DictReader(handle):
                evidence_id = _text(row.get("evidence_id"))
                if evidence_id:
                    excluded.add(evidence_id)
    return excluded


def _queue_sort_key(row: dict[str, str]) -> tuple[int, int, int, str]:
    priority_order = {"high": 0, "medium": 1, "lower": 2}
    priority = priority_order.get(_text(row.get("priority")), 9)
    relevance = _as_int(row.get("relevance_score"))
    year = _as_int(row.get("year"))
    return (priority, -relevance, -year, _text(row.get("evidence_id")))


def _queue_reason(row: dict[str, str]) -> str:
    parts = [
        f"priority={_text(row.get('priority')) or 'unknown'}",
        f"relevance={_text(row.get('relevance_score')) or '0'}",
    ]
    study_tag = _text(row.get("study_tag"))
    if study_tag:
        parts.append(f"study_tag={study_tag}")
    taxa = _text(row.get("taxa_hint"))
    if taxa:
        parts.append(f"taxa={taxa}")
    outcomes = _text(row.get("outcome_hint"))
    if outcomes:
        parts.append(f"outcomes={outcomes}")
    return "; ".join(parts)


def _text(value: object) -> str:
    return "" if value is None else str(value).strip()


def _as_int(value: object) -> int:
    try:
        return int(float(_text(value)))
    except ValueError:
        return 0
