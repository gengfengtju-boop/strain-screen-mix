from __future__ import annotations

import csv
import re
from dataclasses import dataclass
from pathlib import Path

from .config import load_table_schemas


@dataclass(frozen=True)
class ExtractionDraftResult:
    input_path: Path
    intervention_output: Path
    outcome_output: Path
    rows_read: int
    intervention_rows: int
    outcome_rows: int


def _text(value: object) -> str:
    return "" if value is None else str(value).strip()


def _identifier(value: object) -> str:
    text = _text(value)
    if text.endswith(".0") and text[:-2].isdigit():
        return text[:-2]
    return text


def _split_hint(value: object) -> list[str]:
    text = _text(value)
    return [item.strip() for item in text.split(";") if item.strip()]


def _first_or_blank(items: list[str]) -> str:
    return items[0] if items else ""


def _species_from_title(title: str) -> str:
    genus_patterns = [
        "Lactobacillus",
        "Lacticaseibacillus",
        "Lactiplantibacillus",
        "Limosilactobacillus",
        "Bifidobacterium",
        "Akkermansia",
        "Bacillus",
        "Saccharomyces",
    ]
    for genus in genus_patterns:
        match = re.search(rf"\b({genus})\s+([a-z][a-z-]+)\b", title)
        if match:
            return f"{match.group(1)} {match.group(2)}"
    return ""


def _strain_hint_from_title(title: str) -> str:
    patterns = [
        r"\b[A-Z]{1,5}[- ]?\d{2,5}[A-Za-z-]*\b",
        r"\bDSM\s*\d+\b",
        r"\bBB\d+\b",
        r"\bBC\d+\b",
        r"\bIDCC\s*\d+\b",
        r"\bBBr\d+\b",
        r"\bKABP\d+\b",
    ]
    matches: list[str] = []
    for pattern in patterns:
        matches.extend(re.findall(pattern, title))
    return ";".join(dict.fromkeys(match.strip() for match in matches))


def _empty_row(fieldnames: list[str]) -> dict[str, str]:
    return {field: "" for field in fieldnames}


def build_extraction_drafts(
    config_dir: Path,
    screening_path: Path,
    intervention_output: Path,
    outcome_output: Path,
) -> ExtractionDraftResult:
    schemas = load_table_schemas(config_dir)
    intervention_fields = schemas["intervention_metadata"]
    outcome_fields = schemas["clinical_outcome"]
    intervention_rows: list[dict[str, str]] = []
    outcome_rows: list[dict[str, str]] = []
    rows_read = 0

    with screening_path.open("r", newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            rows_read += 1
            title = _text(row.get("title"))
            source_database = _text(row.get("source_database"))
            source_accession = _text(row.get("source_accession"))
            source_url = _text(row.get("source_url"))
            doi = _identifier(row.get("doi"))
            pmid = _identifier(row.get("pmid"))
            evidence_id = _text(row.get("evidence_id"))
            intervention_types = _split_hint(row.get("intervention_type_hint"))
            outcomes = _split_hint(row.get("outcome_hint"))

            intervention = _empty_row(intervention_fields)
            intervention.update(
                {
                    "study_id": evidence_id or source_accession,
                    "subject_id": "needs_manual_extraction",
                    "source_database": source_database,
                    "source_accession": source_accession,
                    "source_url": source_url,
                    "publication_doi": doi,
                    "publication_pmid": pmid,
                    "intervention_type": _first_or_blank(intervention_types) or "needs_manual_extraction",
                    "probiotic_species": _species_from_title(title),
                    "probiotic_strain": _strain_hint_from_title(title),
                    "number_of_strains": "needs_manual_extraction",
                    "total_CFU_per_day": "needs_manual_extraction",
                    "log10_CFU_per_day": "needs_manual_extraction",
                    "strain_specific_CFU": "needs_manual_extraction",
                    "prebiotic_type": "needs_manual_extraction"
                    if "prebiotic" in intervention_types or "synbiotic" in intervention_types
                    else "",
                    "prebiotic_dose_g_day": "needs_manual_extraction"
                    if "prebiotic" in intervention_types or "synbiotic" in intervention_types
                    else "",
                    "duration_weeks": "needs_manual_extraction",
                    "dosage_form": "needs_manual_extraction",
                    "placebo_type": "needs_manual_extraction",
                }
            )
            intervention_rows.append(intervention)

            outcome = _empty_row(outcome_fields)
            outcome.update(
                {
                    "subject_id": "needs_manual_extraction",
                    "study_id": evidence_id or source_accession,
                    "source_database": source_database,
                    "source_accession": source_accession,
                    "source_url": source_url,
                    "publication_doi": doi,
                    "publication_pmid": pmid,
                    "weight_change": "needs_manual_extraction" if "weight" in outcomes else "",
                    "BMI_change": "needs_manual_extraction" if "BMI" in outcomes else "",
                    "waist_change": "needs_manual_extraction" if "waist" in outcomes else "",
                    "body_fat_change": "needs_manual_extraction"
                    if "body_composition" in outcomes
                    else "",
                    "TG_change": "needs_manual_extraction" if "lipid" in outcomes else "",
                    "TC_change": "needs_manual_extraction" if "lipid" in outcomes else "",
                    "LDL_change": "needs_manual_extraction" if "lipid" in outcomes else "",
                    "HDL_change": "needs_manual_extraction" if "lipid" in outcomes else "",
                    "FBG_change": "needs_manual_extraction" if "glucose" in outcomes else "",
                    "FINS_change": "needs_manual_extraction" if "glucose" in outcomes else "",
                    "HOMA_IR_change": "needs_manual_extraction" if "glucose" in outcomes else "",
                    "responder_label": "needs_manual_definition",
                }
            )
            outcome_rows.append(outcome)

    intervention_output.parent.mkdir(parents=True, exist_ok=True)
    outcome_output.parent.mkdir(parents=True, exist_ok=True)
    with intervention_output.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=intervention_fields)
        writer.writeheader()
        writer.writerows(intervention_rows)
    with outcome_output.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=outcome_fields)
        writer.writeheader()
        writer.writerows(outcome_rows)

    return ExtractionDraftResult(
        input_path=screening_path,
        intervention_output=intervention_output,
        outcome_output=outcome_output,
        rows_read=rows_read,
        intervention_rows=len(intervention_rows),
        outcome_rows=len(outcome_rows),
    )
