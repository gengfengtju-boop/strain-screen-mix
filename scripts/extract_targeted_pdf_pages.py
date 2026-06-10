from __future__ import annotations

import argparse
import csv
import re
from pathlib import Path

from pypdf import PdfReader


TERMS = (
    "table 2", "table 3", "table 4", "results", "body weight", "bmi", "waist",
    "fat mass", "body fat", "glucose", "insulin", "homa", "triglyceride", "cholesterol",
    "microbiota", "microbiome", "between-group", "group × time", "interaction",
)


def clean(value: str) -> str:
    return re.sub(r"\s+", " ", (value or "").replace("−", "-")).strip()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("index", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--evidence", action="append", default=[])
    args = parser.parse_args()

    with args.index.open(encoding="utf-8-sig", newline="") as handle:
        sources = list(csv.DictReader(handle))
    wanted = set(args.evidence)
    seen_hashes: set[str] = set()
    rows: list[dict[str, str]] = []
    for source in sources:
        if source.get("file_type") != "pdf" or source.get("matched_evidence_id") not in wanted:
            continue
        if source.get("sha256") in seen_hashes:
            continue
        seen_hashes.add(source.get("sha256", ""))
        reader = PdfReader(Path(source["file_path"]))
        for page_number, page in enumerate(reader.pages, start=1):
            text = clean(page.extract_text() or "")
            lower = text.lower()
            matched = [term for term in TERMS if term in lower]
            score = sum(lower.count(term) for term in matched)
            if score < 3:
                continue
            rows.append(
                {
                    "evidence_id": source["matched_evidence_id"],
                    "source_file": source["file_name"],
                    "page": str(page_number),
                    "hit_score": str(score),
                    "matched_terms": "; ".join(matched),
                    "page_text": text[:12000],
                }
            )
    rows.sort(key=lambda row: (row["evidence_id"], -int(row["hit_score"]), int(row["page"])))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]) if rows else ["evidence_id"])
        writer.writeheader()
        writer.writerows(rows)
    print(f"{args.output}\tpage_hits={len(rows)}\tevidence={len({row['evidence_id'] for row in rows})}")


if __name__ == "__main__":
    main()
