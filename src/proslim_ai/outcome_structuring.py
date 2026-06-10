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
    "effect_parse_method",
    "p_value_parse_method",
    "structure_warning",
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
    intervention, control, effect_method, effect_warning = _extract_effects(final_value)
    between_p, within_p, p_method, p_warning = _split_p_values(p_value)
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
        "effect_parse_method": effect_method,
        "p_value_parse_method": p_method,
        "structure_warning": "; ".join(filter(None, [effect_warning, p_warning])),
        "source_final_value": final_value,
        "source_note": note,
    }


def _text(value: object) -> str:
    return "" if value is None else str(value).strip()


def _extract_effects(text: str) -> tuple[str, str, str, str]:
    pattern = re.compile(r"(?<![A-Za-z])[-+]?\d+(?:\.\d+)?")
    normalized = text.replace("−", "-")
    parts = re.split(r"\s+vs\.?\s+", normalized, maxsplit=1, flags=re.IGNORECASE)
    if len(parts) == 2:
        intervention = pattern.search(parts[0])
        control = pattern.search(parts[1])
        warning = "multiple comparisons retained as first comparison only" if re.search(r"\s+vs\.?\s+", parts[1], re.I) else ""
        return (
            intervention.group(0) if intervention else "",
            control.group(0) if control else "",
            "labeled_groups_split_on_vs",
            warning,
        )
    number = pattern.search(normalized)
    if number:
        return number.group(0), "", "single_group_or_unlabeled_value", "control effect unavailable"
    return "", "", "qualitative_or_missing_value", "no numeric effect parsed"


def _split_p_values(text: str) -> tuple[str, str, str, str]:
    lower = text.lower()
    if "between-group" in lower:
        return (
            _labeled_p(lower, "between-group") or _first_p(lower),
            _labeled_p(lower, "within") if "within" in lower else "",
            "explicit_between_group",
            "",
        )
    if "group_by_time" in lower:
        return _first_p(lower), "", "group_by_time_as_between_group", ""
    if "within" in lower and "between" not in lower:
        return "", _labeled_p(lower, "within") or _first_p(lower), "explicit_within_group_only", "between-group P value unavailable"
    values = re.findall(r"(?:<\s*)?0?\.\d+", lower)
    warning = "multiple unlabeled P values; first retained" if len(values) > 1 else ""
    return _first_p(lower), "", "unlabeled_first_p_value", warning


def _first_p(text: str) -> str:
    if "<" in text:
        match = re.search(r"<\s*0?\.\d+", text)
        return match.group(0).replace(" ", "") if match else "<0.05"
    match = re.search(r"0?\.\d+", text)
    return match.group(0) if match else ""


def _labeled_p(text: str, label: str) -> str:
    label_start = text.find(label)
    if label_start < 0:
        return ""
    before = text[max(0, label_start - 60) : label_start]
    before_values = re.findall(r"(?:<\s*)?0?\.\d+", before)
    if before_values:
        return before_values[-1].replace(" ", "")
    after = text[label_start + len(label) : label_start + len(label) + 60]
    return _first_p(after)


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
