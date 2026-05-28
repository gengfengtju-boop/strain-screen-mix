from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path


OUTCOME_FIELDS = [
    "evidence_id",
    "source_database",
    "source_accession",
    "title",
    "priority",
    "preliminary_response_score",
    "final_outcome_score",
    "final_total_score",
    "confidence_level",
    "predicted_usefulness",
    "confirmed_outcome_domains",
    "strongest_confirmed_signal",
    "confirmed_limitations",
    "main_positive_signals",
    "source_url",
]


OUTCOME_DOMAIN_WEIGHTS = {
    "body_fat": 3.0,
    "weight": 2.2,
    "BMI": 1.5,
    "waist": 1.5,
    "glucose": 1.0,
    "lipid": 1.0,
    "microbiome": 0.8,
}


@dataclass(frozen=True)
class OutcomePrioritizationResult:
    output_path: Path
    rows_written: int
    extracted_review_rows: int


def _text(value: object) -> str:
    return "" if value is None else str(value).strip()


def _score_extracted_outcome(row: dict[str, str]) -> tuple[float, str, str]:
    domain = _text(row.get("outcome_domain"))
    direction = _text(row.get("final_direction")).lower()
    comparison = _text(row.get("comparison")).lower()
    p_value = _text(row.get("p_value_confirmed")).lower()
    value = _text(row.get("final_value"))

    limitations: list[str] = []
    signal = f"{domain}: {value}"
    domain_weight = OUTCOME_DOMAIN_WEIGHTS.get(domain, 0.5)
    has_benefit = (
        "decrease" in direction
        or "improve" in direction
        or "changed" in direction
        or "suppressed increase" in direction
    )
    is_null = (
        "no significant" in direction
        or "no meaningful" in direction
        or "no beneficial" in direction
        or "unfavorable" in direction
    )
    is_between = "vs" in comparison or "between" in comparison
    is_change = "change" in comparison
    is_within = "within" in p_value or "baseline_to_post" in comparison
    is_significant = _is_significant_p_value(p_value)

    if is_null:
        limitations.append(f"{domain} no significant confirmed effect")
        score = -0.45 * domain_weight
    elif has_benefit and is_between and is_significant:
        score = domain_weight
        if is_change:
            score += 0.45
    elif has_benefit and is_between and not is_significant:
        limitations.append(f"{domain} between-group effect not significant")
        score = 0.15 * domain_weight
    elif has_benefit and is_within and is_significant:
        limitations.append(f"{domain} mainly within-group evidence")
        score = 0.30 * domain_weight
    elif has_benefit:
        limitations.append(f"{domain} benefit lacks clear between-group significance")
        score = 0.20 * domain_weight
    else:
        score = 0.0

    if "not significant" in p_value:
        limitations.append(f"{domain} p not significant")
    if "unfavorable" in p_value:
        limitations.append(f"{domain} significant change was unfavorable")
        score -= 0.5 * domain_weight

    if "caution" in _text(row.get("reviewer_note")).lower():
        limitations.append(f"{domain} extraction caution")
        score -= 0.5

    return max(score, -1.0), signal, "; ".join(dict.fromkeys(limitations))


def _is_significant_p_value(value: str) -> bool:
    if "not significant" in value:
        return False
    numbers: list[float] = []
    for token in value.replace("=", " ").replace(";", " ").replace(",", " ").split():
        try:
            numbers.append(float(token))
        except ValueError:
            continue
    if "between-group" in value and numbers:
        return numbers[0] < 0.05
    if "<" in value:
        return True
    for number in numbers:
        if number < 0.05:
            return True
    return False


def build_outcome_prioritized_predictions(
    preliminary_path: Path,
    outcome_review_path: Path,
    output_path: Path,
) -> OutcomePrioritizationResult:
    with preliminary_path.open("r", newline="", encoding="utf-8-sig") as handle:
        preliminary_rows = list(csv.DictReader(handle))

    outcomes_by_id: dict[str, list[dict[str, str]]] = {}
    extracted_rows = 0
    with outcome_review_path.open("r", newline="", encoding="utf-8-sig") as handle:
        for row in csv.DictReader(handle):
            if _text(row.get("review_status")) != "extracted":
                continue
            evidence_id = _text(row.get("evidence_id"))
            if not evidence_id:
                continue
            outcomes_by_id.setdefault(evidence_id, []).append(row)
            extracted_rows += 1

    output_rows: list[dict[str, str]] = []
    for row in preliminary_rows:
        evidence_id = _text(row.get("evidence_id"))
        preliminary_score = float(_text(row.get("preliminary_response_score")) or 0)
        outcome_score = 0.0
        domains: list[str] = []
        signals: list[tuple[float, str]] = []
        limitations: list[str] = []

        for outcome in outcomes_by_id.get(evidence_id, []):
            score, signal, limitation = _score_extracted_outcome(outcome)
            outcome_score += score
            domains.append(_text(outcome.get("outcome_domain")))
            signals.append((score, signal))
            if limitation:
                limitations.append(limitation)

        outcome_score = min(outcome_score, 10.0)
        total_score = preliminary_score + outcome_score
        if outcome_score <= 0:
            confidence = _text(row.get("confidence_level"))
        elif total_score >= 18:
            confidence = "high_with_confirmed_outcomes"
        elif total_score >= 12:
            confidence = "medium_with_confirmed_outcomes"
        else:
            confidence = _text(row.get("confidence_level"))

        output_rows.append(
            {
                "evidence_id": evidence_id,
                "source_database": _text(row.get("source_database")),
                "source_accession": _text(row.get("source_accession")),
                "title": _text(row.get("title")),
                "priority": _text(row.get("priority")),
                "preliminary_response_score": f"{preliminary_score:.2f}",
                "final_outcome_score": f"{outcome_score:.2f}",
                "final_total_score": f"{total_score:.2f}",
                "confidence_level": confidence,
                "predicted_usefulness": "prioritize_modeling" if outcome_score > 0 else _text(row.get("predicted_usefulness")),
                "confirmed_outcome_domains": "; ".join(dict.fromkeys(filter(None, domains))),
                "strongest_confirmed_signal": max(signals, default=(0.0, ""))[1],
                "confirmed_limitations": "; ".join(dict.fromkeys(filter(None, limitations))),
                "main_positive_signals": _text(row.get("main_positive_signals")),
                "source_url": _text(row.get("source_url")),
            }
        )

    output_rows.sort(key=lambda item: float(item["final_total_score"]), reverse=True)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=OUTCOME_FIELDS)
        writer.writeheader()
        writer.writerows(output_rows)

    return OutcomePrioritizationResult(output_path, len(output_rows), extracted_rows)
