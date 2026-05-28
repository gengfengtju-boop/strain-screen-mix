from __future__ import annotations

import csv
import re
from dataclasses import dataclass
from pathlib import Path


HINT_FIELDS = [
    "evidence_id",
    "source_database",
    "source_accession",
    "title",
    "sample_size_hint",
    "duration_hint",
    "cfu_hint",
    "dose_hint",
    "bmi_hint",
    "p_value_hint",
    "intervention_hint",
    "primary_outcome_hint",
    "body_weight_effect_hint",
    "bmi_effect_hint",
    "waist_effect_hint",
    "body_fat_effect_hint",
    "glucose_effect_hint",
    "lipid_effect_hint",
    "microbiome_effect_hint",
    "manual_extraction_note",
]


@dataclass(frozen=True)
class HintExtractionResult:
    input_path: Path
    output_path: Path
    rows_read: int
    rows_written: int


def _text(value: object) -> str:
    return "" if value is None else " ".join(str(value).split())


def _find_all(pattern: str, text: str, flags: int = re.IGNORECASE) -> str:
    matches = re.findall(pattern, text, flags)
    normalized: list[str] = []
    for match in matches:
        if isinstance(match, tuple):
            normalized.append(" ".join(part for part in match if part))
        else:
            normalized.append(match)
    return "; ".join(dict.fromkeys(item.strip() for item in normalized if item.strip()))


def _normalize_cfu_expression(value: str) -> str:
    text = value.replace("×", "x").replace("X", "x")
    text = re.sub(r"\s+", " ", text).strip()

    def repl(match: re.Match[str]) -> str:
        amount = match.group("amount")
        exponent = match.group("exponent")
        suffix = match.group("suffix") or ""
        if exponent.startswith("10") and len(exponent) > 2:
            exponent = exponent[2:]
        return f"{amount} x 10^{exponent} CFU{suffix}"

    return re.sub(
        r"(?P<amount>\d+(?:\.\d+)?)\s*x?\s*10\^?(?P<exponent>\d+)\s*CFU(?P<suffix>/day| daily)?",
        repl,
        text,
        flags=re.IGNORECASE,
    )


def _cfu_hint(text: str) -> str:
    raw = _find_all(
        r"\b\d+(?:\.\d+)?\s*(?:×|x|X)?\s*10\^?\d+\s*CFU(?:/day| daily)?\b|\b\d+(?:\.\d+)?\s*CFU/day\b",
        text,
    )
    if not raw:
        return ""
    return "; ".join(_normalize_cfu_expression(item) for item in raw.split("; "))


def _effect_sentence(text: str, terms: list[str]) -> str:
    sentences = re.split(r"(?<=[.!?])\s+", text)
    for sentence in sentences:
        lowered = sentence.lower()
        if any(term in lowered for term in terms) and any(
            signal in lowered for signal in ("reduc", "decreas", "increas", "improv", "significant", "p ")
        ):
            return sentence[:500]
    return ""


def extract_detail_hints(input_path: Path, output_path: Path) -> HintExtractionResult:
    rows: list[dict[str, str]] = []
    with input_path.open("r", newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            title = _text(row.get("title"))
            abstract = _text(row.get("abstract"))
            detail_text = " ".join(
                [
                    title,
                    abstract,
                    _text(row.get("clinical_interventions")),
                    _text(row.get("primary_outcomes")),
                    _text(row.get("secondary_outcomes")),
                    _text(row.get("arms")),
                ]
            )
            rows.append(
                {
                    "evidence_id": _text(row.get("evidence_id")),
                    "source_database": _text(row.get("source_database")),
                    "source_accession": _text(row.get("source_accession")),
                    "title": title,
                    "sample_size_hint": _find_all(
                        r"\b(?:n\s*=\s*\d+|\d+\s+(?:participants|subjects|individuals|children|adults|patients))\b",
                        detail_text,
                    )
                    or _text(row.get("enrollment")),
                    "duration_hint": _find_all(
                        r"\b\d+\s*(?:-|\s)?(?:week|weeks|month|months|day|days)\b",
                        detail_text,
                    ),
                    "cfu_hint": _cfu_hint(detail_text),
                    "dose_hint": _find_all(
                        r"\b\d+(?:\.\d+)?\s*(?:g|mg|µg|ug|capsules?|sachets?)(?:/day| daily)?\b",
                        detail_text,
                    ),
                    "bmi_hint": _find_all(
                        r"\bBMI\s*(?:[:=]|between|of)?\s*(?:[<>]=?|[≥≤])?\s*\d+(?:\.\d+)?(?:\s*[-–<]\s*\d+(?:\.\d+)?)?",
                        detail_text,
                    ),
                    "p_value_hint": _find_all(
                        r"\bp\s*(?:=|<|≤)\s*0?\.\d+\b",
                        detail_text,
                    ),
                    "intervention_hint": _text(row.get("clinical_interventions")),
                    "primary_outcome_hint": _text(row.get("primary_outcomes")),
                    "body_weight_effect_hint": _effect_sentence(detail_text, ["body weight", "weight"]),
                    "bmi_effect_hint": _effect_sentence(detail_text, ["bmi", "body mass index"]),
                    "waist_effect_hint": _effect_sentence(detail_text, ["waist"]),
                    "body_fat_effect_hint": _effect_sentence(detail_text, ["body fat", "fat mass", "visceral"]),
                    "glucose_effect_hint": _effect_sentence(detail_text, ["glucose", "insulin", "hba1c", "homa"]),
                    "lipid_effect_hint": _effect_sentence(detail_text, ["lipid", "triglyceride", "cholesterol"]),
                    "microbiome_effect_hint": _effect_sentence(detail_text, ["microbiota", "microbiome"]),
                    "manual_extraction_note": "Review source text before entering numeric values into final tables.",
                }
            )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=HINT_FIELDS)
        writer.writeheader()
        writer.writerows(rows)

    return HintExtractionResult(input_path, output_path, len(rows), len(rows))
