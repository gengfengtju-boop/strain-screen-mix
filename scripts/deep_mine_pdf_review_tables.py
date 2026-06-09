from __future__ import annotations

import argparse
import csv
import re
from pathlib import Path

from pypdf import PdfReader


KEYWORDS = {
    "intervention": [
        "intervention",
        "supplement",
        "probiotic",
        "prebiotic",
        "synbiotic",
        "postbiotic",
        "capsule",
        "sachet",
        "yogurt",
        "diet",
        "exercise",
        "dose",
        "cfu",
    ],
    "results": [
        "result",
        "significant",
        "decreased",
        "increased",
        "reduced",
        "improved",
        "change",
        "difference",
        "p ",
        "p=",
        "p<",
    ],
    "anthropometric": [
        "body weight",
        "bmi",
        "body mass index",
        "waist",
        "visceral fat",
        "abdominal fat",
        "body fat",
        "fat mass",
        "adiposity",
    ],
    "metabolic": [
        "glucose",
        "insulin",
        "homa-ir",
        "hba1c",
        "triglyceride",
        "cholesterol",
        "ldl",
        "hdl",
        "crp",
        "inflammation",
    ],
    "microbiome": [
        "microbiota",
        "microbiome",
        "bifidobacterium",
        "lactobacillus",
        "akkermansia",
        "firmicutes",
        "bacteroidetes",
        "scfa",
    ],
    "safety": [
        "adverse",
        "tolerability",
        "safety",
        "side effect",
        "withdraw",
        "dropout",
    ],
}

VALUE_PATTERN = re.compile(
    r"(?:(?:mean|change|difference|decrease|increase|reduction|baseline|week)\b[^.;]{0,120}?"
    r"(?:[-+]?\d+(?:\.\d+)?\s*(?:kg/m2|kg/m²|kg|cm|%|mmol/L|mg/dL|g/day|mg/day|CFU|cfu)?)[^.;]{0,120}?"
    r"(?:p\s*(?:=|<|>)\s*0?\.\d+)?)",
    re.IGNORECASE,
)
PVALUE_PATTERN = re.compile(r"\bp\s*(?:=|<|>)\s*0?\.\d+\b", re.IGNORECASE)
ARM_PATTERN = re.compile(
    r"\b(?:placebo|control|intervention|probiotic|prebiotic|synbiotic|postbiotic|diet|exercise|"
    r"restricted calorie|energy restriction|nabilone|omega-3|VSL\s*#?3|Akkermansia|inulin)\b",
    re.IGNORECASE,
)
DOSE_PATTERN = re.compile(
    r"(?:\d+(?:\.\d+)?\s*(?:x|X)\s*10\s*\^?\s*\d+|10\s*\^?\s*\d+|"
    r"\d+(?:\.\d+)?\s*billion)\s*CFU(?:\s*/\s*day|\s*per\s*day|/day)?|"
    r"\d+(?:\.\d+)?\s*(?:g|mg|mcg)\s*(?:/day|per day|daily)?",
    re.IGNORECASE,
)
TIME_PATTERN = re.compile(r"\b\d+\s*(?:weeks?|wks?|months?|days?)\b", re.IGNORECASE)
SAMPLE_PATTERN = re.compile(
    r"\b(?:n\s*=\s*\d+|\d+\s+(?:participants|subjects|patients|adults|children|adolescents|women|men))\b",
    re.IGNORECASE,
)


def clean(text: str) -> str:
    text = (text or "").replace("\u2212", "-")
    return re.sub(r"\s+", " ", text).strip()


def first_unique(items: list[str], limit: int = 8) -> str:
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


def read_text(path: Path, max_pages: int) -> tuple[str, str, int]:
    if path.suffix.lower() == ".pdf":
        reader = PdfReader(path)
        chunks: list[str] = []
        page_limit = min(len(reader.pages), max_pages)
        for page in reader.pages[:page_limit]:
            try:
                chunks.append(page.extract_text() or "")
            except Exception:
                chunks.append("")
        return clean("\n".join(chunks)), str(len(reader.pages)), page_limit
    text = path.read_text(encoding="utf-8-sig", errors="replace")
    return clean(text), "csv", 1


def sentences(text: str) -> list[str]:
    parts = re.split(r"(?<=[.!?。；;])\s+", text)
    return [clean(part) for part in parts if len(clean(part)) >= 35]


def score_sentence(sentence: str, keyword_group: str) -> int:
    lower = sentence.lower()
    score = 0
    for keyword in KEYWORDS[keyword_group]:
        if keyword in lower:
            score += 2
    if PVALUE_PATTERN.search(sentence):
        score += 3
    if re.search(r"[-+]?\d", sentence):
        score += 1
    if VALUE_PATTERN.search(sentence):
        score += 2
    return score


def select_snippets(text: str, keyword_group: str, limit: int = 8) -> str:
    ranked = []
    for sentence in sentences(text):
        score = score_sentence(sentence, keyword_group)
        if score > 0:
            ranked.append((score, sentence[:520]))
    ranked.sort(key=lambda item: (-item[0], len(item[1])))
    return first_unique([sentence for _, sentence in ranked], limit)


def table_like_lines(text: str, limit: int = 10) -> str:
    candidates = []
    for raw in re.split(r"\s{2,}|\n", text):
        line = clean(raw)
        lower = line.lower()
        if len(line) < 35:
            continue
        if not re.search(r"\d", line):
            continue
        if any(keyword in lower for keyword in KEYWORDS["anthropometric"] + KEYWORDS["metabolic"]):
            candidates.append(line[:420])
        if len(candidates) >= limit:
            break
    return first_unique(candidates, limit)


def mine_record(row: dict[str, str], max_pages: int) -> dict[str, str]:
    path = Path(row["file_path"])
    mined = {
        "evidence_id": row.get("matched_evidence_id", ""),
        "source_accession": row.get("matched_source_accession", ""),
        "matched_title": row.get("matched_title", ""),
        "source_file": row.get("file_name", ""),
        "match_score": row.get("match_score", ""),
        "pages_total": row.get("pages", ""),
        "pages_mined": "",
        "second_pass_source_file": row.get("file_name", ""),
        "second_pass_match_score": row.get("match_score", ""),
        "second_pass_pages_total": row.get("pages", ""),
        "second_pass_intervention_snippets": "",
        "second_pass_results_snippets": "",
        "second_pass_anthropometric_snippets": "",
        "second_pass_metabolic_snippets": "",
        "second_pass_microbiome_snippets": "",
        "second_pass_safety_snippets": "",
        "second_pass_value_pvalue_candidates": "",
        "second_pass_table_like_lines": "",
        "second_pass_arm_terms": "",
        "second_pass_dose_terms": "",
        "second_pass_duration_terms": "",
        "second_pass_sample_terms": "",
        "second_pass_extraction_status": "ok",
        "second_pass_error": "",
    }
    try:
        text, pages_total, pages_mined = read_text(path, max_pages)
        mined["pages_total"] = pages_total
        mined["pages_mined"] = str(pages_mined)
        mined["second_pass_pages_total"] = pages_total
        mined["second_pass_intervention_snippets"] = select_snippets(text, "intervention")
        mined["second_pass_results_snippets"] = select_snippets(text, "results")
        mined["second_pass_anthropometric_snippets"] = select_snippets(text, "anthropometric")
        mined["second_pass_metabolic_snippets"] = select_snippets(text, "metabolic")
        mined["second_pass_microbiome_snippets"] = select_snippets(text, "microbiome")
        mined["second_pass_safety_snippets"] = select_snippets(text, "safety", limit=5)
        mined["second_pass_value_pvalue_candidates"] = first_unique(VALUE_PATTERN.findall(text), 18)
        mined["second_pass_table_like_lines"] = table_like_lines(text)
        mined["second_pass_arm_terms"] = first_unique(ARM_PATTERN.findall(text), 14)
        mined["second_pass_dose_terms"] = first_unique(DOSE_PATTERN.findall(text), 14)
        mined["second_pass_duration_terms"] = first_unique(TIME_PATTERN.findall(text), 10)
        mined["second_pass_sample_terms"] = first_unique(SAMPLE_PATTERN.findall(text), 10)
    except Exception as exc:  # noqa: BLE001 - keep the extraction batch moving.
        mined["second_pass_extraction_status"] = "error"
        mined["second_pass_error"] = str(exc)
    return mined


def load_best_index(index_path: Path, threshold: float) -> list[dict[str, str]]:
    with index_path.open(encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    best: dict[str, dict[str, str]] = {}
    for row in rows:
        if row.get("parse_status") != "ok":
            continue
        try:
            score = float(row.get("match_score") or 0)
        except ValueError:
            score = 0.0
        evidence_id = row.get("matched_evidence_id", "")
        if score < threshold or not evidence_id:
            continue
        if evidence_id not in best or score > float(best[evidence_id].get("match_score") or 0):
            best[evidence_id] = row
    return list(best.values())


def write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = list(rows[0].keys()) if rows else ["evidence_id"]
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def augment_tables(extract_rows: list[dict[str, str]], inputs: list[Path], suffix: str) -> None:
    by_evidence = {row["evidence_id"]: row for row in extract_rows}
    second_fields = [field for field in extract_rows[0] if field.startswith("second_pass_")] if extract_rows else []
    for source in inputs:
        with source.open(encoding="utf-8-sig", newline="") as handle:
            reader = csv.DictReader(handle)
            rows = list(reader)
            fields = list(reader.fieldnames or [])
        output = source.with_name(source.stem + suffix + ".csv")
        output_fields = fields + [field for field in second_fields if field not in fields]
        matched = 0
        with_results = 0
        for row in rows:
            mined = by_evidence.get(row.get("evidence_id", ""))
            if mined:
                matched += 1
                for field in second_fields:
                    row[field] = mined.get(field, "")
                if mined.get("second_pass_results_snippets"):
                    with_results += 1
            else:
                for field in second_fields:
                    row.setdefault(field, "")
        with output.open("w", encoding="utf-8-sig", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=output_fields)
            writer.writeheader()
            writer.writerows(rows)
        print(f"{output}\trows={len(rows)}\tsecond_pass_matched={matched}\twith_results={with_results}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--index", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--threshold", default=0.60, type=float)
    parser.add_argument("--max-pages", default=35, type=int)
    parser.add_argument("--augment-suffix", default="")
    parser.add_argument("--augment", nargs="*", default=[])
    args = parser.parse_args()

    records = load_best_index(args.index, args.threshold)
    mined = [mine_record(record, args.max_pages) for record in records]
    write_csv(args.output, mined)
    print(f"{args.output}\tevidence_rows={len(mined)}")
    print(f"errors={sum(row['second_pass_extraction_status'] != 'ok' for row in mined)}")
    print(f"with_results={sum(bool(row['second_pass_results_snippets']) for row in mined)}")
    print(f"with_value_pvalue={sum(bool(row['second_pass_value_pvalue_candidates']) for row in mined)}")
    print(f"with_table_like={sum(bool(row['second_pass_table_like_lines']) for row in mined)}")
    if args.augment:
        augment_tables(mined, [Path(item) for item in args.augment], args.augment_suffix)


if __name__ == "__main__":
    main()
