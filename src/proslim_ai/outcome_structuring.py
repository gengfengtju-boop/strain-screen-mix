from __future__ import annotations

import csv
import re
from dataclasses import dataclass
from pathlib import Path


STRUCTURED_OUTCOME_FIELDS = [
    "evidence_id",
    "outcome_domain",
    "endpoint_type",
    "analysis_population",
    "comparison",
    "intervention_effect",
    "control_effect",
    "effect_difference",
    "effect_unit",
    "between_group_p",
    "within_group_p",
    "direction",
    "evidence_modifier",
    "positive_efficacy_label",
    "source_final_value",
    "source_note",
]


@dataclass(frozen=True)
class StructuredOutcomeResult:
    output_path: Path
    rows_written: int


def structure_outcome_review(review_path: Path, output_path: Path) -> StructuredOutcomeResult:
    rows: list[dict[str, str]] = []
    with review_path.open("r", newline="", encoding="utf-8-sig") as handle:
        for row in csv.DictReader(handle):
            if _text(row.get("review_status")) != "extracted":
                continue
            rows.append(_structure_row(row))

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=STRUCTURED_OUTCOME_FIELDS)
        writer.writeheader()
        writer.writerows(rows)
    return StructuredOutcomeResult(output_path=output_path, rows_written=len(rows))


def _structure_row(row: dict[str, str]) -> dict[str, str]:
    final_value = _text(row.get("final_value"))
    p_value = _text(row.get("p_value_confirmed"))
    note = _text(row.get("reviewer_note"))
    comparison = _text(row.get("comparison"))
    direction = _text(row.get("final_direction"))
    intervention, control = _extract_first_two_effects(final_value)
    between_p, within_p = _split_p_values(p_value)
    population = _analysis_population(note, p_value)
    modifier = _evidence_modifier(note, p_value, comparison)
    positive = _positive_label(direction, between_p, modifier)
    return {
        "evidence_id": _text(row.get("evidence_id")),
        "outcome_domain": _text(row.get("outcome_domain")),
        "endpoint_type": _endpoint_type(_text(row.get("outcome_domain"))),
        "analysis_population": population,
        "comparison": comparison,
        "intervention_effect": intervention,
        "control_effect": control,
        "effect_difference": _effect_difference(intervention, control),
        "effect_unit": _text(row.get("final_unit")),
        "between_group_p": between_p,
        "within_group_p": within_p,
        "direction": direction,
        "evidence_modifier": modifier,
        "positive_efficacy_label": positive,
        "source_final_value": final_value,
        "source_note": note,
    }


def _text(value: object) -> str:
    return "" if value is None else str(value).strip()


def _extract_first_two_effects(text: str) -> tuple[str, str]:
    pattern = re.compile(r"(?<![A-Za-z])[-+]?\d+(?:\.\d+)?")
    numbers = pattern.findall(text.replace("−", "-"))
    if len(numbers) < 2:
        return "", ""
    return numbers[0], numbers[1]


def _split_p_values(text: str) -> tuple[str, str]:
    lower = text.lower()
    if "between-group" in lower:
        return _first_p(lower), _first_p(lower.split("within", 1)[1]) if "within" in lower else ""
    if "group_by_time" in lower:
        return _first_p(lower), ""
    if "within" in lower and "between" not in lower:
        return "", _first_p(lower)
    return _first_p(lower), ""


def _first_p(text: str) -> str:
    if "<" in text:
        match = re.search(r"<\s*0?\.\d+", text)
        return match.group(0).replace(" ", "") if match else "<0.05"
    match = re.search(r"0?\.\d+", text)
    return match.group(0) if match else ""


def _analysis_population(note: str, p_value: str) -> str:
    text = f"{note} {p_value}".lower()
    if "itt" in text and "not significant" in text:
        return "PP_positive_ITT_not_significant"
    if "subgroup" in text or "overweight subgroup" in text:
        return "subgroup"
    if "pp" in text or "per-protocol" in text:
        return "PP"
    if "fas" in text:
        return "FAS"
    return "aggregate_trial"


def _evidence_modifier(note: str, p_value: str, comparison: str) -> str:
    text = f"{note} {p_value} {comparison}".lower()
    modifiers: list[str] = []
    if "between-group" in text and ("not significant" in text or _numeric_p_ge_005(text)):
        modifiers.append("between_group_not_significant")
    if "within" in text:
        modifiers.append("within_group_only_or_mixed")
    if "itt" in text and "not significant" in text:
        modifiers.append("PP_only")
    if "subgroup" in text:
        modifiers.append("subgroup_only")
    if "diet" in text or "energy-restricted" in text or "low-calorie" in text:
        modifiers.append("diet_confounded")
    if "unfavorable" in text:
        modifiers.append("unfavorable")
    if "caution" in text:
        modifiers.append("manual_caution")
    return "; ".join(dict.fromkeys(modifiers))


def _numeric_p_ge_005(text: str) -> bool:
    match = re.search(r"between-group[^0-9<]*(0?\.\d+)", text)
    return bool(match and float(match.group(1)) >= 0.05)


def _positive_label(direction: str, between_p: str, modifier: str) -> str:
    lower = direction.lower()
    if "no significant" in lower or "no meaningful" in lower or "no beneficial" in lower or "unfavorable" in lower:
        return "no"
    if "between_group_not_significant" in modifier or "unfavorable" in modifier:
        return "no"
    if between_p and (_p_less_than_005(between_p) or between_p.startswith("<")):
        return "yes"
    return "limited"


def _p_less_than_005(value: str) -> bool:
    try:
        return float(value.replace("<", "")) < 0.05
    except ValueError:
        return False


def _effect_difference(intervention: str, control: str) -> str:
    try:
        return f"{float(intervention) - float(control):.3f}"
    except ValueError:
        return ""


def _endpoint_type(domain: str) -> str:
    if domain in {"body_fat", "weight", "BMI", "waist"}:
        return "adiposity"
    if domain in {"glucose", "lipid"}:
        return "metabolic"
    if domain == "microbiome":
        return "microbiome"
    return "other"
