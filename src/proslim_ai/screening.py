from __future__ import annotations

import csv
import re
from dataclasses import dataclass
from pathlib import Path

from .config import load_yaml


@dataclass(frozen=True)
class ScreeningResult:
    input_path: Path
    output_path: Path
    rows_read: int
    rows_written: int


SCREENING_FIELDS = [
    "evidence_id",
    "source_database",
    "source_accession",
    "doi",
    "pmid",
    "title",
    "year",
    "evidence_type",
    "priority",
    "relevance_score",
    "study_tag",
    "intervention_type_hint",
    "taxa_hint",
    "outcome_hint",
    "needs_manual_review",
    "source_url",
]


def _norm(value: object) -> str:
    return "" if value is None else str(value).strip()


def _contains_any(text: str, terms: list[str]) -> bool:
    lowered = text.lower()
    return any(term.lower() in lowered for term in terms)


def _matching_keys(text: str, grouped_terms: dict[str, list[str]]) -> list[str]:
    matches: list[str] = []
    for key, terms in grouped_terms.items():
        if _contains_any(text, terms):
            matches.append(key)
    return matches


def _taxa_matches(text: str, taxa_patterns: list[str]) -> list[str]:
    matches: list[str] = []
    for taxon in taxa_patterns:
        pattern = re.compile(rf"(?<![A-Za-z]){re.escape(taxon)}(?![A-Za-z])", re.IGNORECASE)
        if pattern.search(text):
            matches.append(taxon)
    return matches


def _study_tag(title: str, evidence_type: str) -> str:
    lowered = title.lower()
    if "meta-analysis" in lowered or "systematic review" in lowered:
        return "meta_analysis_or_systematic_review"
    if "randomized" in lowered or "randomised" in lowered or "placebo-controlled" in lowered:
        return "randomized_controlled_trial"
    if evidence_type == "clinical_trial":
        return "clinical_trial_registry"
    if any(term in lowered for term in ("mouse", "mice", "rat", "animal model", "obese mouse")):
        return "preclinical_or_animal"
    if "review" in lowered:
        return "review"
    return "needs_manual_classification"


def _priority(title: str, evidence_type: str, config: dict) -> str:
    rules = config.get("priority_rules", {})
    if evidence_type == "clinical_trial":
        return "high"
    if _contains_any(title, rules.get("high", [])):
        return "high"
    if _contains_any(title, rules.get("medium", [])):
        return "medium"
    if _contains_any(title, rules.get("lower", [])):
        return "lower"
    return "medium"


def _relevance_score(title: str, config: dict) -> int:
    grouped_terms = config.get("target_relevance_terms", {})
    score = 0
    for terms in grouped_terms.values():
        if _contains_any(title, terms):
            score += 1
    return score


def screen_evidence_registry(
    config_dir: Path,
    input_path: Path,
    output_path: Path,
) -> ScreeningResult:
    config = load_yaml(config_dir / "screening_config.yaml")
    rows: list[dict[str, str]] = []

    with input_path.open("r", newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            title = _norm(row.get("title"))
            evidence_type = _norm(row.get("evidence_type"))
            rows.append(
                {
                    "evidence_id": _norm(row.get("evidence_id")),
                    "source_database": _norm(row.get("source_database")),
                    "source_accession": _norm(row.get("source_accession")),
                    "doi": _norm(row.get("doi")),
                    "pmid": _norm(row.get("pmid")),
                    "title": title,
                    "year": _norm(row.get("year")),
                    "evidence_type": evidence_type,
                    "priority": _priority(title, evidence_type, config),
                    "relevance_score": str(_relevance_score(title, config)),
                    "study_tag": _study_tag(title, evidence_type),
                    "intervention_type_hint": ";".join(
                        _matching_keys(title, config.get("intervention_terms", {}))
                    ),
                    "taxa_hint": ";".join(_taxa_matches(title, config.get("taxa_patterns", []))),
                    "outcome_hint": ";".join(_matching_keys(title, config.get("outcome_terms", {}))),
                    "needs_manual_review": "true",
                    "source_url": _norm(row.get("source_url")),
                }
            )

    priority_order = {"high": 0, "medium": 1, "lower": 2}
    rows.sort(
        key=lambda item: (
            priority_order.get(item["priority"], 9),
            -int(item["relevance_score"] or 0),
            -(int(item["year"]) if item["year"].isdigit() else 0),
        )
    )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=SCREENING_FIELDS)
        writer.writeheader()
        writer.writerows(rows)

    return ScreeningResult(
        input_path=input_path,
        output_path=output_path,
        rows_read=len(rows),
        rows_written=len(rows),
    )
