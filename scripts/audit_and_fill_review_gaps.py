from __future__ import annotations

import argparse
import csv
import re
from pathlib import Path

from pypdf import PdfReader


FINAL_PRIORITY = Path(
    "results/prediction_results/"
    "review_priority_top100.enriched.pdf_deep_augmented.download_augmented."
    "second_pass_augmented.download_second_pass_augmented.csv"
)
FINAL_OUTCOME = Path(
    "data/intervention_data/"
    "outcome_review_worksheet.review_priority_top100.pdf_deep_augmented.download_augmented."
    "second_pass_augmented.download_second_pass_augmented.csv"
)
FINAL_INTERVENTION = Path(
    "data/intervention_data/"
    "intervention_review_worksheet.top100.pdf_deep_augmented.download_augmented."
    "second_pass_augmented.download_second_pass_augmented.csv"
)


def clean(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").replace("\u2212", "-")).strip()


def first_unique(items: list[str], limit: int = 10) -> str:
    output: list[str] = []
    seen: set[str] = set()
    for item in items:
        value = clean(str(item))
        key = value.lower()
        if value and key not in seen:
            output.append(value)
            seen.add(key)
        if len(output) >= limit:
            break
    return " || ".join(output)


def load_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames: list[str] = []
    for row in rows:
        for field in row:
            if field not in fieldnames:
                fieldnames.append(field)
    if not fieldnames:
        fieldnames = ["evidence_id"]
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def source_records(index_paths: list[Path], threshold: float) -> dict[str, dict[str, str]]:
    best: dict[str, dict[str, str]] = {}
    for path in index_paths:
        for row in load_csv(path):
            try:
                score = float(row.get("match_score") or 0)
            except ValueError:
                score = 0
            evidence_id = row.get("matched_evidence_id", "")
            if row.get("parse_status") != "ok" or not evidence_id or score < threshold:
                continue
            if evidence_id not in best or score > float(best[evidence_id].get("match_score") or 0):
                best[evidence_id] = row
    return best


def text_from_source(path: Path) -> tuple[str, str]:
    if path.suffix.lower() == ".csv":
        return path.read_text(encoding="utf-8-sig", errors="replace"), "csv_text"
    reader = PdfReader(path)
    chunks: list[str] = []
    for page in reader.pages:
        try:
            chunks.append(page.extract_text() or "")
        except Exception:
            chunks.append("")
    text = clean("\n".join(chunks))
    if len(text) < 80:
        return text, "image_pdf_requires_ocr_or_manual_review"
    return text, "pdf_text"


def parse_clinicaltrials_csv(path: Path) -> dict[str, str]:
    rows = load_csv(path)
    if not rows:
        return {}
    row = rows[0]
    fields = {
        "third_pass_nct_enrollment": row.get("Enrollment", ""),
        "third_pass_nct_study_design": row.get("Study Design", ""),
        "third_pass_nct_interventions": row.get("Interventions", ""),
        "third_pass_nct_primary_outcomes": row.get("Primary Outcome Measures", ""),
        "third_pass_nct_secondary_outcomes": row.get("Secondary Outcome Measures", ""),
        "third_pass_nct_brief_summary": row.get("Brief Summary", ""),
    }
    return {key: clean(value) for key, value in fields.items()}


def mine_text(text: str) -> dict[str, str]:
    sentences = [clean(part) for part in re.split(r"(?<=[.!?。；;])\s+", text) if len(clean(part)) > 35]
    result_terms = [
        "body weight",
        "bmi",
        "waist",
        "visceral fat",
        "body fat",
        "fat mass",
        "glucose",
        "insulin",
        "homa-ir",
        "cholesterol",
        "triglyceride",
        "microbiota",
        "microbiome",
    ]
    result_snippets = []
    for sentence in sentences:
        lower = sentence.lower()
        if any(term in lower for term in result_terms) and re.search(r"\d|p\s*(?:=|<|>)", lower):
            result_snippets.append(sentence[:520])
    return {
        "third_pass_result_snippets": first_unique(result_snippets, 8),
        "third_pass_p_values": first_unique(re.findall(r"\bp\s*(?:=|<|>)\s*0?\.\d+\b", text, re.I), 16),
        "third_pass_numeric_values": first_unique(
            re.findall(
                r"[-+]?\d+(?:\.\d+)?\s*(?:kg/m2|kg/m²|kg|cm|%|mmol/L|mg/dL|g/day|mg/day|CFU|cfu)?",
                text,
                re.I,
            ),
            20,
        ),
        "third_pass_dose_terms": first_unique(
            re.findall(
                r"(?:\d+(?:\.\d+)?\s*(?:x|X)\s*10\s*\^?\s*\d+|10\s*\^?\s*\d+|"
                r"\d+(?:\.\d+)?\s*billion)\s*CFU(?:\s*/\s*day|\s*per\s*day|/day)?|"
                r"\d+(?:\.\d+)?\s*(?:g|mg|mcg)\s*(?:/day|per day|daily)?",
                text,
                re.I,
            ),
            12,
        ),
        "third_pass_duration_terms": first_unique(
            re.findall(r"\b\d+\s*(?:weeks?|wks?|months?|days?)\b", text, re.I), 10
        ),
        "third_pass_sample_terms": first_unique(
            re.findall(
                r"\b(?:n\s*=\s*\d+|\d+\s+(?:participants|subjects|patients|adults|children|adolescents|women|men))\b",
                text,
                re.I,
            ),
            10,
        ),
    }


def gaps_for_priority(row: dict[str, str], has_source: bool) -> list[str]:
    checks = {
        "local_source": has_source,
        "result_snippet": bool(row.get("second_pass_results_snippets")),
        "value_or_p": bool(row.get("second_pass_value_pvalue_candidates")),
        "dose": bool(row.get("second_pass_dose_terms")),
        "duration": bool(row.get("second_pass_duration_terms")),
        "sample": bool(row.get("second_pass_sample_terms")),
    }
    return [key for key, ok in checks.items() if not ok]


def build_gap_extracts(sources: dict[str, dict[str, str]], priority_rows: list[dict[str, str]]) -> list[dict[str, str]]:
    priority_by_id = {row["evidence_id"]: row for row in priority_rows}
    extracts: list[dict[str, str]] = []
    for evidence_id, source in sorted(sources.items()):
        priority_row = priority_by_id.get(evidence_id, {})
        gaps = gaps_for_priority(priority_row, has_source=True)
        if not gaps:
            continue
        source_path = Path(source["file_path"])
        base = {
            "evidence_id": evidence_id,
            "title": priority_row.get("title") or source.get("matched_title", ""),
            "source_file": source.get("file_name", ""),
            "source_path": source.get("file_path", ""),
            "match_score": source.get("match_score", ""),
            "priority_gaps_before_third_pass": ";".join(gaps),
            "third_pass_source_status": "",
            "third_pass_fill_note": "",
        }
        try:
            text, status = text_from_source(source_path)
            base["third_pass_source_status"] = status
            if source_path.suffix.lower() == ".csv":
                base.update(parse_clinicaltrials_csv(source_path))
            base.update(mine_text(text))
            if status == "image_pdf_requires_ocr_or_manual_review":
                base["third_pass_fill_note"] = "No machine-readable PDF text was available; OCR or manual PDF review is required."
            elif source_path.suffix.lower() == ".csv":
                base["third_pass_fill_note"] = "ClinicalTrials CSV fields were extracted where available."
            else:
                base["third_pass_fill_note"] = "Full machine-readable text was re-mined for missing fields."
        except Exception as exc:  # noqa: BLE001
            base["third_pass_source_status"] = "error"
            base["third_pass_fill_note"] = str(exc)
        extracts.append(base)
    return extracts


def augment_table(source: Path, extracts: list[dict[str, str]], output: Path) -> None:
    rows = load_csv(source)
    by_evidence = {row["evidence_id"]: row for row in extracts}
    add_fields: list[str] = []
    for extract in extracts:
        for field in extract:
            if field.startswith("third_pass_") and field not in add_fields:
                add_fields.append(field)
    add_fields = ["priority_gaps_before_third_pass"] + add_fields
    fieldnames = list(rows[0].keys()) + [field for field in add_fields if field not in rows[0]]
    matched = 0
    for row in rows:
        mined = by_evidence.get(row.get("evidence_id", ""))
        if mined:
            matched += 1
            for field in add_fields:
                row[field] = mined.get(field, "")
        else:
            for field in add_fields:
                row.setdefault(field, "")
    with output.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    print(f"{output}\trows={len(rows)}\tthird_pass_matched={matched}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--threshold", type=float, default=0.60)
    parser.add_argument("--out-dir", type=Path, default=Path("results/pdf_review_extracts"))
    args = parser.parse_args()

    sources = source_records(
        [
            Path("results/pdf_review_extracts/pdf_source_index.csv"),
            Path("results/pdf_review_extracts/download_pdf_source_index.csv"),
        ],
        args.threshold,
    )
    priority_rows = load_csv(FINAL_PRIORITY)
    outcome_rows = load_csv(FINAL_OUTCOME)
    intervention_rows = load_csv(FINAL_INTERVENTION)
    extracts = build_gap_extracts(sources, priority_rows)
    write_csv(args.out_dir / "third_pass_gap_extracts.csv", extracts)

    gap_summary = []
    for label, rows in [
        ("priority_top100", priority_rows),
        ("outcome_top100_rows", outcome_rows),
        ("intervention_top100", intervention_rows),
    ]:
        gap_summary.append(
            {
                "table": label,
                "rows": str(len(rows)),
                "with_local_source": str(sum(row.get("evidence_id") in sources for row in rows)),
                "missing_local_source": str(sum(row.get("evidence_id") not in sources for row in rows)),
                "missing_second_pass_results": str(sum(not row.get("second_pass_results_snippets") for row in rows)),
                "missing_second_pass_value_p": str(sum(not row.get("second_pass_value_pvalue_candidates") for row in rows)),
                "missing_second_pass_dose": str(sum(not row.get("second_pass_dose_terms") for row in rows)),
                "missing_second_pass_sample": str(sum(not row.get("second_pass_sample_terms") for row in rows)),
            }
        )
    write_csv(args.out_dir / "review_gap_audit_summary.csv", gap_summary)
    augment_table(FINAL_PRIORITY, extracts, FINAL_PRIORITY.with_name(FINAL_PRIORITY.stem + ".third_pass_gap_augmented.csv"))
    augment_table(FINAL_OUTCOME, extracts, FINAL_OUTCOME.with_name(FINAL_OUTCOME.stem + ".third_pass_gap_augmented.csv"))
    augment_table(
        FINAL_INTERVENTION,
        extracts,
        FINAL_INTERVENTION.with_name(FINAL_INTERVENTION.stem + ".third_pass_gap_augmented.csv"),
    )
    print(f"third_pass_gap_extracts={len(extracts)}")
    print(
        "requires_ocr_or_manual_review="
        f"{sum(row.get('third_pass_source_status') == 'image_pdf_requires_ocr_or_manual_review' for row in extracts)}"
    )


if __name__ == "__main__":
    main()
