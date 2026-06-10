from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path

from .config import load_yaml


PREDICTION_FIELDS = [
    "evidence_id",
    "source_database",
    "source_accession",
    "title",
    "intervention_type_hint",
    "taxa_hint",
    "study_tag",
    "priority",
    "relevance_score",
    "preliminary_response_score",
    "score_type",
    "confidence_level",
    "predicted_usefulness",
    "main_positive_signals",
    "main_limitations",
    "source_url",
]


@dataclass(frozen=True)
class PreliminaryPredictionResult:
    output_path: Path
    rows_written: int


def _text(value: object) -> str:
    return "" if value is None else str(value).strip()


def _has(value: object) -> bool:
    return bool(_text(value))


def _as_int(value: object) -> int:
    text = _text(value)
    try:
        return int(float(text))
    except ValueError:
        return 0


def _score_row(screening: dict[str, str], hints: dict[str, str], weights: dict[str, float]) -> tuple[float, list[str], list[str]]:
    score = 0.0
    positive: list[str] = []
    limitations: list[str] = []

    priority = _text(screening.get("priority"))
    study_tag = _text(screening.get("study_tag"))
    relevance_score = _as_int(screening.get("relevance_score"))

    if priority == "high":
        score += weights["priority_high"]
        positive.append("high priority evidence")
    elif priority == "medium":
        score += weights["priority_medium"]

    if study_tag in weights:
        score += weights[study_tag]
        positive.append(study_tag)

    score += relevance_score * weights["relevance_score"]
    if relevance_score:
        positive.append(f"relevance score {relevance_score}")

    for field in (
        "sample_size_hint",
        "duration_hint",
        "cfu_hint",
        "dose_hint",
        "p_value_hint",
        "body_weight_effect_hint",
        "bmi_effect_hint",
        "waist_effect_hint",
        "body_fat_effect_hint",
        "glucose_effect_hint",
        "lipid_effect_hint",
        "microbiome_effect_hint",
    ):
        if _has(hints.get(field)):
            score += weights[field]
            positive.append(field.replace("_hint", ""))
        elif field in {"sample_size_hint", "duration_hint", "p_value_hint"}:
            limitations.append(f"missing {field.replace('_hint', '')}")

    if not _has(screening.get("taxa_hint")):
        limitations.append("taxa not identified from title")
    if not _has(screening.get("intervention_type_hint")):
        limitations.append("intervention type needs manual confirmation")

    return score, positive, limitations


def _confidence(score: float, config: dict) -> str:
    rules = config["confidence_rules"]
    if score >= float(rules["high_min_score"]):
        return "high_for_manual_review"
    if score >= float(rules["medium_min_score"]):
        return "medium_for_manual_review"
    return "low_for_manual_review"


def build_preliminary_predictions(
    config_dir: Path,
    screening_path: Path,
    hints_path: Path,
    output_path: Path,
) -> PreliminaryPredictionResult:
    config = load_yaml(config_dir / "preliminary_prediction.yaml")
    weights = config["weights"]
    max_score = float(config["score_caps"]["max_score"])

    with screening_path.open("r", newline="", encoding="utf-8-sig") as handle:
        screening_rows = list(csv.DictReader(handle))
    with hints_path.open("r", newline="", encoding="utf-8-sig") as handle:
        hint_rows = {_text(row.get("evidence_id")): row for row in csv.DictReader(handle)}

    prediction_rows: list[dict[str, str]] = []
    for screening in screening_rows:
        evidence_id = _text(screening.get("evidence_id"))
        hints = hint_rows.get(evidence_id, {})
        raw_score, positive, limitations = _score_row(screening, hints, weights)
        score = min(raw_score, max_score)
        confidence = _confidence(score, config)
        prediction_rows.append(
            {
                "evidence_id": evidence_id,
                "source_database": _text(screening.get("source_database")),
                "source_accession": _text(screening.get("source_accession")),
                "title": _text(screening.get("title")),
                "intervention_type_hint": _text(screening.get("intervention_type_hint")),
                "taxa_hint": _text(screening.get("taxa_hint")),
                "study_tag": _text(screening.get("study_tag")),
                "priority": _text(screening.get("priority")),
                "relevance_score": _text(screening.get("relevance_score")),
                "preliminary_response_score": f"{score:.2f}",
                "score_type": "heuristic_extraction_priority_not_probability",
                "confidence_level": confidence,
                "predicted_usefulness": "prioritize_extraction" if score >= 6 else "defer_or_screen_manually",
                "main_positive_signals": "; ".join(dict.fromkeys(positive)),
                "main_limitations": "; ".join(dict.fromkeys(limitations)),
                "source_url": _text(screening.get("source_url")),
            }
        )

    prediction_rows.sort(key=lambda row: float(row["preliminary_response_score"]), reverse=True)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=PREDICTION_FIELDS)
        writer.writeheader()
        writer.writerows(prediction_rows)

    return PreliminaryPredictionResult(output_path=output_path, rows_written=len(prediction_rows))
