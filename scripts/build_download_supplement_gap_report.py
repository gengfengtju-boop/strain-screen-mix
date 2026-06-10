from __future__ import annotations

import argparse
import csv
from collections import defaultdict
from pathlib import Path


def load(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("index", type=Path)
    parser.add_argument("confirmed_audit", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()

    confirmed_counts: dict[str, int] = defaultdict(int)
    for row in load(args.confirmed_audit):
        confirmed_counts[row["evidence_id"]] += 1

    grouped: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in load(args.index):
        if row.get("parse_status") == "ok":
            grouped[row["matched_evidence_id"]].append(row)

    output_rows = []
    for evidence_id, rows in sorted(grouped.items()):
        title = rows[0].get("matched_title", "")
        lower = title.lower()
        if evidence_id.startswith("NCT:") and all(row.get("file_type") == "csv" for row in rows):
            role = "trial_registry"
        elif any(term in lower for term in ("systematic review", "meta-analysis", "review")):
            role = "secondary_evidence"
        else:
            role = "primary_study"
        confirmed = confirmed_counts.get(evidence_id, 0)
        if confirmed:
            status = "structured_outcomes_confirmed"
            remaining = "confirm exact table effect sizes/units where audit notes request it"
        elif role == "trial_registry":
            status = "registry_fields_mined_no_confirmed_results"
            remaining = "obtain posted results or linked publication before efficacy extraction"
        elif role == "secondary_evidence":
            status = "secondary_source_mined_not_counted_as_trial_outcome"
            remaining = "use references to locate missing primary trials; do not pool review summary as one cohort"
        else:
            status = "full_text_mined_manual_table_confirmation_pending"
            remaining = "manually confirm arm-level effect sizes, units, analysis population and between-group P values"
        output_rows.append(
            {
                "evidence_id": evidence_id,
                "title": title,
                "evidence_role": role,
                "source_file_count": str(len(rows)),
                "source_files": "; ".join(row.get("file_name", "") for row in rows),
                "confirmed_outcome_rows": str(confirmed),
                "current_status": status,
                "remaining_manual_work": remaining,
            }
        )

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(output_rows[0]))
        writer.writeheader()
        writer.writerows(output_rows)
    print(f"{args.output}\tevidence_rows={len(output_rows)}")
    print(f"confirmed_evidence={sum(bool(int(row['confirmed_outcome_rows'])) for row in output_rows)}")
    print(f"primary_pending={sum(row['evidence_role'] == 'primary_study' and not int(row['confirmed_outcome_rows']) for row in output_rows)}")


if __name__ == "__main__":
    main()
