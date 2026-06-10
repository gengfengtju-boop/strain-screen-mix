from __future__ import annotations

import csv
from pathlib import Path


UNAVAILABLE_IDS = {
    "NCT:NCT01433120",
    "NCT:NCT04962633",
    "NCT:NCT05114018",
    "NCT:NCT06989177",
    "PMID:32521799",
    "PMID:39340527",
    "PMID:40814108",
    "PMID:40951500",
}

CSV_TARGETS = (
    Path("results/pdf_review_extracts/download_supplement_source_index_20260610.csv"),
    Path("results/pdf_review_extracts/download_supplement_second_pass_extracts_20260610.csv"),
    Path("results/pdf_review_extracts/download_supplement_gap_report_remaining_20260610.csv"),
    Path(
        "data/intervention_data/"
        "outcome_review_worksheet.review_priority_top100."
        "download_supplement_remaining_confirmed_20260610.csv"
    ),
    Path(
        "results/prediction_results/"
        "outcome_aware_response_prioritization.download_supplement_remaining_20260610.csv"
    ),
)


def load(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        return list(reader.fieldnames or []), list(reader)


def evidence_id(row: dict[str, str]) -> str:
    return row.get("evidence_id") or row.get("matched_evidence_id") or ""


def write(path: Path, fields: list[str], rows: list[dict[str, str]]) -> None:
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    audit_path = (
        root
        / "data/intervention_data/"
        "download_supplement_unavailable_evidence_removed_20260610.csv"
    )
    gap_path = root / CSV_TARGETS[2]
    _, gap_rows = load(gap_path)
    audit_rows = [row for row in gap_rows if evidence_id(row) in UNAVAILABLE_IDS]
    if not audit_rows and audit_path.exists():
        _, audit_rows = load(audit_path)
    if {evidence_id(row) for row in audit_rows} != UNAVAILABLE_IDS:
        raise RuntimeError("Gap report does not contain every unavailable evidence ID")

    removed_files: set[str] = set()
    summary: list[tuple[str, int, int]] = []
    for relative in CSV_TARGETS:
        path = root / relative
        fields, rows = load(path)
        kept = [row for row in rows if evidence_id(row) not in UNAVAILABLE_IDS]
        removed = [row for row in rows if evidence_id(row) in UNAVAILABLE_IDS]
        if relative == CSV_TARGETS[0]:
            removed_files.update(row["file_name"] for row in removed)
        write(path, fields, kept)
        summary.append((relative.as_posix(), len(rows), len(removed)))

    manifest_path = root / "config/download_supplement_manifest_20260610.txt"
    manifest_lines = manifest_path.read_text(encoding="utf-8-sig").splitlines()
    kept_lines = [line for line in manifest_lines if line not in removed_files]
    manifest_path.write_text("\n".join(kept_lines) + "\n", encoding="utf-8")

    audit_fields = [
        "evidence_id",
        "title",
        "evidence_role",
        "source_file_count",
        "source_files",
        "removal_reason",
        "removal_scope",
    ]
    audit = [
        {
            **{field: row.get(field, "") for field in audit_fields},
            "removal_reason": "no obtainable primary efficacy result for this supplement pass",
            "removal_scope": "download supplement package only",
        }
        for row in audit_rows
    ]
    write(audit_path, audit_fields, audit)

    for name, before, removed in summary:
        print(f"{name}\tbefore={before}\tremoved={removed}\tafter={before - removed}")
    print(
        f"manifest\tbefore={len(manifest_lines)}\tremoved={len(manifest_lines) - len(kept_lines)}"
        f"\tafter={len(kept_lines)}"
    )
    print(f"audit\t{audit_path}\trows={len(audit)}")


if __name__ == "__main__":
    main()
