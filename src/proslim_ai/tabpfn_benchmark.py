from __future__ import annotations

import json
import re
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import average_precision_score, balanced_accuracy_score, roc_auc_score
from sklearn.model_selection import StratifiedGroupKFold
from sklearn.preprocessing import OrdinalEncoder


BASE_CATEGORICAL_FEATURES = [
    "outcome_domain",
    "endpoint_type",
    "analysis_population",
    "comparison",
]
ENRICHED_CATEGORICAL_FEATURES = [
    "intervention_class",
    "strain_family",
    "population_group",
    "blinding",
    "randomized_design",
    "placebo_control",
]
ENRICHED_NUMERIC_FEATURES = ["sample_size", "duration_weeks", "log10_cfu_day"]


def benchmark_tabpfn(
    structured_outcomes_path: Path,
    model_path: Path,
    output_path: Path,
    n_estimators: int = 2,
    random_seed: int = 17,
    cv_repeats: int = 1,
    review_paths: list[Path] | None = None,
) -> dict[str, object]:
    if cv_repeats < 1:
        raise ValueError("cv_repeats must be at least 1")
    if not model_path.is_file():
        raise FileNotFoundError(
            f"TabPFN checkpoint not found: {model_path}. "
            "Download the official checkpoint separately before benchmarking."
        )
    try:
        from tabpfn import TabPFNClassifier
    except ImportError as exc:
        raise RuntimeError("Install the optional 'tabular-foundation' dependencies first.") from exc

    data = pd.read_csv(structured_outcomes_path)
    data = data[data["positive_efficacy_label"].isin(["yes", "limited", "no"])].copy()
    data["label"] = (data["positive_efficacy_label"] == "yes").astype(int)
    feature_table, categorical_features, numeric_features, matched_review_rows = (
        build_response_feature_table(data, review_paths or [])
    )
    X_categorical = feature_table[categorical_features].fillna("missing").astype(str).to_numpy()
    X_numeric = feature_table[numeric_features].apply(pd.to_numeric, errors="coerce").to_numpy()
    y = data["label"].to_numpy(dtype=int)
    groups = data["evidence_id"].fillna("").astype(str).to_numpy()
    repeated_probabilities = []
    repeat_metrics = []
    for repeat in range(cv_repeats):
        repeat_seed = random_seed + repeat * 101
        folds = StratifiedGroupKFold(n_splits=5, shuffle=True, random_state=repeat_seed)
        probabilities = np.zeros(len(y), dtype=float)
        for train, test in folds.split(X_categorical, y, groups):
            encoder = OrdinalEncoder(handle_unknown="use_encoded_value", unknown_value=-1)
            train_categorical = encoder.fit_transform(X_categorical[train]).astype(np.float32)
            test_categorical = encoder.transform(X_categorical[test]).astype(np.float32)
            train_numeric = X_numeric[train].astype(np.float32)
            test_numeric = X_numeric[test].astype(np.float32)
            medians = np.nanmedian(train_numeric, axis=0)
            medians = np.where(np.isnan(medians), 0.0, medians)
            train_numeric = np.where(np.isnan(train_numeric), medians, train_numeric)
            test_numeric = np.where(np.isnan(test_numeric), medians, test_numeric)
            X_train = np.hstack([train_categorical, train_numeric])
            X_test = np.hstack([test_categorical, test_numeric])
            model = TabPFNClassifier(
                model_path=model_path,
                device="cpu",
                n_estimators=n_estimators,
                n_preprocessing_jobs=1,
                random_state=repeat_seed,
                categorical_features_indices=list(range(len(categorical_features))),
            )
            model.fit(X_train, y[train])
            probabilities[test] = model.predict_proba(X_test)[:, 1]
        repeated_probabilities.append(probabilities)
        repeat_predictions = probabilities >= 0.5
        repeat_metrics.append(
            {
                "repeat": repeat + 1,
                "seed": repeat_seed,
                "roc_auc": float(roc_auc_score(y, probabilities)),
                "average_precision": float(average_precision_score(y, probabilities)),
                "balanced_accuracy": float(balanced_accuracy_score(y, repeat_predictions)),
            }
        )

    probabilities = np.mean(repeated_probabilities, axis=0)
    predictions = probabilities >= 0.5
    auc_values = np.array([row["roc_auc"] for row in repeat_metrics])
    ap_values = np.array([row["average_precision"] for row in repeat_metrics])
    balanced_values = np.array([row["balanced_accuracy"] for row in repeat_metrics])
    auc_mean = float(auc_values.mean())
    auc_std = float(auc_values.std())
    ap_mean = float(ap_values.mean())
    metrics = {
        "model": "TabPFNClassifier",
        "n_estimators": n_estimators,
        "tabpfn_checkpoint": str(model_path),
        "rows": len(y),
        "evidence_groups": int(pd.Series(groups).nunique()),
        "validation": "repeated_five_fold_stratified_group_cross_validation_by_evidence_id",
        "cv_repeats": cv_repeats,
        "repeat_metrics": repeat_metrics,
        "roc_auc": float(roc_auc_score(y, probabilities)),
        "roc_auc_mean": auc_mean,
        "roc_auc_std": auc_std,
        "average_precision": float(average_precision_score(y, probabilities)),
        "average_precision_mean": ap_mean,
        "average_precision_std": float(ap_values.std()),
        "balanced_accuracy": float(balanced_accuracy_score(y, predictions)),
        "balanced_accuracy_mean": float(balanced_values.mean()),
        "balanced_accuracy_std": float(balanced_values.std()),
        "positive_prevalence": float(y.mean()),
        "eligible_for_combination_fusion": bool(
            auc_mean >= 0.55 and auc_mean - auc_std >= 0.50 and ap_mean > y.mean()
        ),
        "fusion_policy": "auc_mean>=0.55, auc_mean-auc_std>=0.50, ap_mean>prevalence",
        "feature_policy": "leakage_safe_descriptors_only",
        "features": categorical_features + numeric_features,
        "review_rows_matched": matched_review_rows,
        "review_feature_coverage": float(matched_review_rows / len(data)),
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(metrics, indent=2), encoding="utf-8")
    return metrics


def build_response_feature_table(
    data: pd.DataFrame,
    review_paths: list[Path],
) -> tuple[pd.DataFrame, list[str], list[str], int]:
    table = data.copy()
    if not review_paths:
        return table, BASE_CATEGORICAL_FEATURES, [], 0
    review_rows = []
    for path in review_paths:
        review = pd.read_csv(path)
        if "review_status" in review:
            review = review[review["review_status"] == "extracted"]
        review_rows.append(review)
    review = pd.concat(review_rows, ignore_index=True)
    review = review.drop_duplicates(["evidence_id", "outcome_domain"], keep="last")
    text_fields = [
        "title",
        "comparison",
        "reviewer_note",
        "pdf_deep_species_strain_terms",
        "pdf_deep_strain_codes",
        "download_deep_species_strain_terms",
        "download_deep_strain_codes",
        "second_pass_intervention_snippets",
        "second_pass_design_terms",
    ]
    keep = [
        "evidence_id",
        "outcome_domain",
        "time_point",
        "sample_size_confirmed",
        "pdf_deep_dose_terms",
        "download_deep_dose_terms",
        "second_pass_dose_terms",
        *text_fields,
    ]
    keep = [column for column in keep if column in review.columns]
    table = table.merge(
        review[keep], on=["evidence_id", "outcome_domain"], how="left", suffixes=("", "_review")
    )
    joined_text = table.apply(
        lambda row: " ".join(str(row.get(field, "")) for field in text_fields).lower(), axis=1
    )
    primary_text = table.apply(
        lambda row: " ".join(
            str(row.get(field, "")) for field in ("title", "comparison", "comparison_review")
        ).lower(),
        axis=1,
    )
    primary_class = primary_text.map(_intervention_class)
    fallback_class = joined_text.map(_intervention_class)
    table["intervention_class"] = primary_class.where(primary_class != "other", fallback_class)
    table["strain_family"] = joined_text.map(_strain_family)
    table["population_group"] = joined_text.map(_population_group)
    table["blinding"] = joined_text.map(_blinding)
    table["randomized_design"] = joined_text.map(
        lambda text: "randomized" if "random" in text else "not_reported"
    )
    table["placebo_control"] = joined_text.map(
        lambda text: "placebo" if "placebo" in text else "other_control"
    )
    sample_size = table.get("sample_size_confirmed", pd.Series(index=table.index, dtype=object))
    time_point = table.get("time_point", pd.Series(index=table.index, dtype=object))
    table["sample_size"] = sample_size.map(_sample_size)
    table["duration_weeks"] = time_point.map(_duration_weeks)
    table["log10_cfu_day"] = table.apply(_cfu_log10, axis=1)
    matched = int(table["sample_size_confirmed"].notna().sum())
    numeric_features = [
        column for column in ENRICHED_NUMERIC_FEATURES if table[column].notna().any()
    ]
    return (
        table,
        BASE_CATEGORICAL_FEATURES + ENRICHED_CATEGORICAL_FEATURES,
        numeric_features,
        matched,
    )


def _intervention_class(text: str) -> str:
    if "synbiotic" in text:
        return "synbiotic"
    if "prebiotic" in text or "inulin" in text or "fiber" in text or "fibre" in text:
        return "prebiotic"
    if "probiotic" in text or "lactobac" in text or "bifidobacter" in text:
        return "probiotic"
    if "exercise" in text or "weight-management" in text:
        return "multicomponent_lifestyle"
    if "diet" in text:
        return "diet"
    return "other"


def _strain_family(text: str) -> str:
    families = []
    for name, terms in {
        "lactobacillaceae": ("lactobac", "lacticaseibac", "lactiplantibac"),
        "bifidobacterium": ("bifidobacter",),
        "akkermansia": ("akkermansia",),
        "bacillus": ("bacillus",),
    }.items():
        if any(term in text for term in terms):
            families.append(name)
    return "+".join(families) if families else "non_strain_or_unreported"


def _population_group(text: str) -> str:
    if "children" in text or "adolescent" in text:
        return "pediatric"
    if "elderly" in text or "older adult" in text or "aged ≥65" in text:
        return "older_adult"
    if "type 2 diabetes" in text or "t2dm" in text:
        return "type2_diabetes"
    if "metabolic syndrome" in text:
        return "metabolic_syndrome"
    return "adult_overweight_obesity"


def _blinding(text: str) -> str:
    if "triple-blind" in text or "triple blind" in text:
        return "triple_blind"
    if "double-blind" in text or "double blind" in text:
        return "double_blind"
    if "single-blind" in text or "single blind" in text:
        return "single_blind"
    if "open-label" in text or "open label" in text:
        return "open_label"
    return "not_reported"


def _sample_size(value: object) -> float:
    match = re.search(r"(?:n\s*=\s*|n=)?(\d{1,4})", str(value), flags=re.IGNORECASE)
    return float(match.group(1)) if match else np.nan


def _duration_weeks(value: object) -> float:
    text = str(value).lower()
    match = re.search(r"(\d+(?:\.\d+)?)\s*(day|week|month|year)", text)
    if not match:
        return np.nan
    amount = float(match.group(1))
    return amount * {"day": 1 / 7, "week": 1, "month": 4.345, "year": 52.14}[match.group(2)]


def _cfu_log10(row: pd.Series) -> float:
    text = " ".join(
        str(row.get(field, ""))
        for field in ("pdf_deep_dose_terms", "download_deep_dose_terms", "second_pass_dose_terms")
    ).lower()
    power = re.search(r"10\s*(?:\^|×|x)?\s*(\d{1,2})\s*cfu", text)
    if power:
        return float(power.group(1))
    billion = re.search(r"(\d+(?:\.\d+)?)\s*billion\s*cfu", text)
    if billion:
        return float(np.log10(float(billion.group(1)) * 1e9))
    return np.nan
