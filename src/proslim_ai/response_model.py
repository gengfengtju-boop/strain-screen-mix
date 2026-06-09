from __future__ import annotations

import csv
import json
import pickle
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.base import clone
from sklearn.compose import ColumnTransformer
from sklearn.dummy import DummyClassifier
from sklearn.ensemble import GradientBoostingClassifier, RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score, brier_score_loss, roc_auc_score
from sklearn.model_selection import StratifiedGroupKFold, StratifiedKFold, cross_val_predict
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler


ROW_PREDICTION_FIELDS = [
    "evidence_id",
    "outcome_domain",
    "endpoint_type",
    "analysis_population",
    "positive_efficacy_label",
    "model_response_probability",
    "model_predicted_label",
    "effect_difference",
    "between_group_p",
    "evidence_modifier",
    "model_level",
]

EVIDENCE_PREDICTION_FIELDS = [
    "evidence_id",
    "study_level_response_probability",
    "positive_endpoint_fraction",
    "outcome_rows",
    "adiposity_probability",
    "metabolic_probability",
    "microbiome_probability",
    "model_level",
]


@dataclass(frozen=True)
class ResponseModelResult:
    row_predictions_output: Path
    evidence_predictions_output: Path
    metrics_output: Path
    model_output: Path
    rows_used: int
    evidence_count: int


@dataclass(frozen=True)
class CombinationResponseApplicationResult:
    output_path: Path
    rows_written: int
    combinations_with_model_probability: int


def train_response_model(
    structured_outcome_path: Path,
    row_predictions_output: Path,
    evidence_predictions_output: Path,
    metrics_output: Path,
    model_output: Path,
) -> ResponseModelResult:
    data = pd.read_csv(structured_outcome_path)
    data = data[data["positive_efficacy_label"].isin(["yes", "limited", "no"])].copy()
    data["label"] = (data["positive_efficacy_label"] == "yes").astype(int)

    if data["label"].nunique() < 2:
        raise ValueError("Response model requires at least one positive and one non-positive outcome row.")

    numeric_candidates = ["intervention_effect", "control_effect", "effect_difference", "between_group_p", "within_group_p"]
    categorical_features = [
        "outcome_domain",
        "endpoint_type",
        "analysis_population",
        "comparison",
        "direction",
        "evidence_modifier",
    ]
    for column in numeric_candidates:
        data[column] = pd.to_numeric(data.get(column), errors="coerce")
    min_observed_numeric_values = 5
    numeric_features = [
        column for column in numeric_candidates if int(data[column].notna().sum()) >= min_observed_numeric_values
    ]
    for column in categorical_features:
        data[column] = data.get(column, "").fillna("").astype(str)

    X = data[numeric_features + categorical_features]
    y = data["label"]
    groups = data["evidence_id"].fillna("").astype(str)
    model_candidates = _model_candidates(numeric_features, categorical_features)
    selected_name, probabilities, comparison, validation = _select_model(model_candidates, X, y, groups)

    final_model = clone(model_candidates[selected_name])
    final_model.fit(X, y)

    row_predictions = data.copy()
    row_predictions["model_response_probability"] = probabilities
    row_predictions["model_predicted_label"] = np.where(probabilities >= 0.5, "predicted_positive", "predicted_limited_or_negative")
    row_predictions["model_level"] = "study_endpoint_level_not_individual_microbiome"

    row_predictions_output.parent.mkdir(parents=True, exist_ok=True)
    row_predictions[ROW_PREDICTION_FIELDS].to_csv(row_predictions_output, index=False)

    evidence_predictions = _aggregate_evidence_predictions(row_predictions)
    evidence_predictions_output.parent.mkdir(parents=True, exist_ok=True)
    evidence_predictions.to_csv(evidence_predictions_output, index=False)

    metrics = _metrics(y.to_numpy(), probabilities)
    metrics.update(
        {
            "selected_model": selected_name,
            "model_comparison": comparison,
            "validation": validation,
            "rows_used": int(len(data)),
            "positive_rows": int(y.sum()),
            "non_positive_rows": int(len(y) - y.sum()),
            "evidence_count": int(evidence_predictions["evidence_id"].nunique()),
            "model_level": "study_endpoint_level_not_individual_microbiome",
            "limitation": "Trained on structured study endpoint rows, not subject-level baseline microbiome responders.",
        }
    )
    metrics_output.parent.mkdir(parents=True, exist_ok=True)
    metrics_output.write_text(json.dumps(metrics, indent=2, sort_keys=True), encoding="utf-8")

    model_output.parent.mkdir(parents=True, exist_ok=True)
    with model_output.open("wb") as handle:
        pickle.dump(
            {
                "model": final_model,
                "selected_model": selected_name,
                "numeric_features": numeric_features,
                "categorical_features": categorical_features,
                "model_level": "study_endpoint_level_not_individual_microbiome",
            },
            handle,
        )

    return ResponseModelResult(
        row_predictions_output=row_predictions_output,
        evidence_predictions_output=evidence_predictions_output,
        metrics_output=metrics_output,
        model_output=model_output,
        rows_used=len(data),
        evidence_count=int(evidence_predictions["evidence_id"].nunique()),
    )


def apply_response_model_to_combinations(
    combination_input: Path,
    evidence_predictions_path: Path,
    output_path: Path,
) -> CombinationResponseApplicationResult:
    with evidence_predictions_path.open("r", newline="", encoding="utf-8-sig") as handle:
        evidence_probabilities = {
            _text(row["evidence_id"]).replace("PMID:", ""): float(row["study_level_response_probability"])
            for row in csv.DictReader(handle)
            if _text(row.get("study_level_response_probability"))
        }

    rows: list[dict[str, str]] = []
    with combination_input.open("r", newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        fieldnames = list(reader.fieldnames or [])
        for row in reader:
            pmids = [_text(item) for item in _text(row.get("evidence_pmid_list")).split(";") if _text(item)]
            probabilities = [evidence_probabilities[pmid] for pmid in pmids if pmid in evidence_probabilities]
            if probabilities:
                probability = float(np.mean(probabilities))
                row["predicted_response_probability"] = f"{probability:.4f}"
                row["predicted_response_score"] = f"{probability * 10:.2f}"
                row["response_model_level"] = "study_endpoint_level_not_individual_microbiome"
                row["response_model_source"] = "clinical_outcome.structured_effects"
                row["response_model_pmids_used"] = "; ".join([pmid for pmid in pmids if pmid in evidence_probabilities])
                row["validation_priority"] = _recompute_validation_priority(row)
            else:
                row["predicted_response_probability"] = ""
                row["response_model_level"] = "no_matching_model_evidence"
                row["response_model_source"] = ""
                row["response_model_pmids_used"] = ""
            rows.append(row)

    rows.sort(key=lambda item: float(_text(item.get("validation_priority")) or 0), reverse=True)
    for index, row in enumerate(rows, start=1):
        row["combination_id"] = f"MR3TO5_{index:03d}"

    extra_fields = [
        "predicted_response_probability",
        "response_model_level",
        "response_model_source",
        "response_model_pmids_used",
    ]
    for field in extra_fields:
        if field not in fieldnames:
            fieldnames.append(field)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    return CombinationResponseApplicationResult(
        output_path=output_path,
        rows_written=len(rows),
        combinations_with_model_probability=sum(1 for row in rows if _text(row.get("predicted_response_probability"))),
    )


def _build_model(
    numeric_features: list[str],
    categorical_features: list[str],
    classifier: object,
    scale_numeric: bool = True,
) -> Pipeline:
    numeric_steps: list[tuple[str, object]] = [("imputer", SimpleImputer(strategy="median"))]
    if scale_numeric:
        numeric_steps.append(("scaler", StandardScaler()))
    preprocessor = ColumnTransformer(
        transformers=[
            (
                "numeric",
                Pipeline(numeric_steps),
                numeric_features,
            ),
            (
                "categorical",
                Pipeline(
                    [
                        ("imputer", SimpleImputer(strategy="constant", fill_value="missing")),
                        ("onehot", OneHotEncoder(handle_unknown="ignore")),
                    ]
                ),
                categorical_features,
            ),
        ]
    )
    return Pipeline(
        [
            ("preprocess", preprocessor),
            ("classifier", classifier),
        ]
    )


def _model_candidates(numeric_features: list[str], categorical_features: list[str]) -> dict[str, Pipeline]:
    return {
        "dummy_prior": _build_model(
            numeric_features,
            categorical_features,
            DummyClassifier(strategy="prior"),
        ),
        "logistic_l2_balanced": _build_model(
            numeric_features,
            categorical_features,
            LogisticRegression(class_weight="balanced", max_iter=1000, random_state=17),
        ),
        "random_forest_balanced": _build_model(
            numeric_features,
            categorical_features,
            RandomForestClassifier(
                n_estimators=300,
                max_depth=3,
                min_samples_leaf=3,
                class_weight="balanced_subsample",
                random_state=17,
            ),
            scale_numeric=False,
        ),
        "gradient_boosting_shallow": _build_model(
            numeric_features,
            categorical_features,
            GradientBoostingClassifier(
                n_estimators=80,
                learning_rate=0.05,
                max_depth=2,
                min_samples_leaf=3,
                random_state=17,
            ),
            scale_numeric=False,
        ),
    }


def _select_model(
    models: dict[str, Pipeline],
    X: pd.DataFrame,
    y: pd.Series,
    groups: pd.Series,
) -> tuple[str, np.ndarray, list[dict[str, object]], str]:
    validation, cv, use_groups = _cross_validation_strategy(y, groups)
    comparison: list[dict[str, object]] = []
    best_name = ""
    best_probabilities: np.ndarray | None = None
    best_key: tuple[float, float] | None = None

    for name, model in models.items():
        probabilities = _cross_validated_probabilities(model, X, y, groups, cv, use_groups)
        metrics = _metrics(y.to_numpy(), probabilities)
        row = {"model": name, **metrics}
        comparison.append(row)
        brier = float(metrics["brier_score"] if metrics["brier_score"] is not None else 1.0)
        average_precision = float(metrics["average_precision"] if metrics["average_precision"] is not None else 0.0)
        key = (brier, -average_precision)
        if best_key is None or key < best_key:
            best_name = name
            best_probabilities = probabilities
            best_key = key

    if best_probabilities is None:
        raise RuntimeError("No response model candidate produced probabilities.")
    return best_name, best_probabilities, comparison, validation


def _cross_validation_strategy(y: pd.Series, groups: pd.Series) -> tuple[str, object | None, bool]:
    min_class_count = int(y.value_counts().min())
    group_count = int(groups.nunique())
    n_splits = min(5, min_class_count, group_count)
    if n_splits >= 2:
        return (
            "stratified_group_cross_validated_by_evidence_id",
            StratifiedGroupKFold(n_splits=n_splits, shuffle=True, random_state=17),
            True,
        )
    n_splits = min(5, min_class_count)
    if n_splits >= 2:
        return ("stratified_cross_validated", StratifiedKFold(n_splits=n_splits, shuffle=True, random_state=17), False)
    return ("resubstitution_small_class_count", None, False)


def _cross_validated_probabilities(
    model: Pipeline,
    X: pd.DataFrame,
    y: pd.Series,
    groups: pd.Series,
    cv: object | None,
    use_groups: bool,
) -> np.ndarray:
    if cv is None:
        fitted = clone(model)
        fitted.fit(X, y)
        return fitted.predict_proba(X)[:, 1]
    if use_groups:
        return cross_val_predict(clone(model), X, y, groups=groups, cv=cv, method="predict_proba")[:, 1]
    return cross_val_predict(clone(model), X, y, cv=cv, method="predict_proba")[:, 1]


def _aggregate_evidence_predictions(row_predictions: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for evidence_id, group in row_predictions.groupby("evidence_id", sort=False):
        adiposity = group[group["endpoint_type"] == "adiposity"]["model_response_probability"]
        metabolic = group[group["endpoint_type"] == "metabolic"]["model_response_probability"]
        microbiome = group[group["endpoint_type"] == "microbiome"]["model_response_probability"]
        positive_fraction = float(group["label"].mean())
        endpoint_weighted = _weighted_endpoint_probability(adiposity, metabolic, microbiome)
        rows.append(
            {
                "evidence_id": evidence_id,
                "study_level_response_probability": f"{endpoint_weighted:.4f}",
                "positive_endpoint_fraction": f"{positive_fraction:.4f}",
                "outcome_rows": int(len(group)),
                "adiposity_probability": _format_probability(adiposity),
                "metabolic_probability": _format_probability(metabolic),
                "microbiome_probability": _format_probability(microbiome),
                "model_level": "study_endpoint_level_not_individual_microbiome",
            }
        )
    return pd.DataFrame(rows, columns=EVIDENCE_PREDICTION_FIELDS)


def _weighted_endpoint_probability(adiposity: pd.Series, metabolic: pd.Series, microbiome: pd.Series) -> float:
    parts: list[tuple[float, float]] = []
    if len(adiposity):
        parts.append((float(adiposity.mean()), 0.55))
    if len(metabolic):
        parts.append((float(metabolic.mean()), 0.30))
    if len(microbiome):
        parts.append((float(microbiome.mean()), 0.15))
    if not parts:
        return 0.0
    numerator = sum(value * weight for value, weight in parts)
    denominator = sum(weight for _, weight in parts)
    return numerator / denominator


def _format_probability(series: pd.Series) -> str:
    if not len(series):
        return ""
    return f"{float(series.mean()):.4f}"


def _metrics(y_true: np.ndarray, probabilities: np.ndarray) -> dict[str, float | None]:
    metrics: dict[str, float | None] = {"brier_score": float(brier_score_loss(y_true, probabilities))}
    try:
        metrics["roc_auc"] = float(roc_auc_score(y_true, probabilities))
    except ValueError:
        metrics["roc_auc"] = None
    try:
        metrics["average_precision"] = float(average_precision_score(y_true, probabilities))
    except ValueError:
        metrics["average_precision"] = None
    return metrics


def _recompute_validation_priority(row: dict[str, str]) -> str:
    clinical = float(_text(row.get("clinical_evidence_score")) or 0)
    design = float(_text(row.get("combination_design_score")) or 0)
    response = float(_text(row.get("predicted_response_score")) or 0)
    priority = 0.35 * clinical + 0.35 * design + 0.30 * response
    return f"{priority:.2f}"


def _text(value: object) -> str:
    return "" if value is None else str(value).strip()
