from __future__ import annotations

import importlib.metadata
import json
from dataclasses import dataclass
from pathlib import Path

import pandas as pd
from sklearn.ensemble import ExtraTreesClassifier, HistGradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline

from .response_model import (
    _build_model,
    _leave_one_group_out_metrics,
    _locked_group_predictions,
)
from .tabpfn_benchmark import build_response_feature_table


@dataclass(frozen=True)
class ModernResponseBenchmarkResult:
    output_path: Path
    selected_model: str
    promoted_model: str | None
    rows_used: int
    evidence_count: int


def benchmark_modern_response_models(
    structured_outcomes_path: Path,
    output_path: Path,
    review_paths: list[Path] | None = None,
    cv_repeats: int = 5,
    random_seed: int = 17,
    minimum_auc_gain: float = 0.01,
) -> ModernResponseBenchmarkResult:
    if cv_repeats < 2:
        raise ValueError("Modern model promotion requires at least two CV repeats.")
    data = pd.read_csv(structured_outcomes_path)
    data = data[data["positive_efficacy_label"].isin(["yes", "limited", "no"])].copy()
    data["label"] = (data["positive_efficacy_label"] == "yes").astype(int)
    feature_table, _, numeric_features, matched_review_rows = build_response_feature_table(
        data, review_paths or []
    )
    if not numeric_features:
        raise ValueError("Modern response benchmark requires at least one numeric feature.")

    X = feature_table[numeric_features]
    y = data["label"]
    groups = data["evidence_id"].fillna("").astype(str)
    candidates, unavailable = _modern_candidates(numeric_features)
    candidate_results: list[dict[str, object]] = []

    for name, model in candidates.items():
        _, _, _, validation, _, repeat_metrics = _locked_group_predictions(
            candidates,
            name,
            X,
            y,
            groups,
            cv_repeats=cv_repeats,
            random_seed=random_seed,
        )
        leave_one_study_out = _leave_one_group_out_metrics(model, X, y, groups)
        candidate_results.append(
            {
                "model": name,
                "validation": validation,
                "repeat_metrics": repeat_metrics,
                "repeated_roc_auc_mean": _mean(repeat_metrics, "roc_auc"),
                "repeated_roc_auc_std": _std(repeat_metrics, "roc_auc"),
                "repeated_average_precision_mean": _mean(
                    repeat_metrics, "average_precision"
                ),
                "leave_one_study_out": leave_one_study_out,
            }
        )

    baseline = next(
        row for row in candidate_results if row["model"] == "logistic_l2_strong"
    )
    for row in candidate_results:
        promoted, reasons = _promotion_decision(row, baseline, minimum_auc_gain)
        row["promotion_eligible"] = promoted
        row["promotion_reasons"] = reasons

    promoted = [row for row in candidate_results if row["promotion_eligible"]]
    promoted_model = None
    selected_model = "logistic_l2_strong"
    if promoted:
        best = max(
            promoted,
            key=lambda row: (
                float(row["repeated_roc_auc_mean"]),
                float(row["leave_one_study_out"]["study_equal_roc_auc"]),
            ),
        )
        selected_model = str(best["model"])
        promoted_model = selected_model

    report = {
        "benchmark": "modern_study_endpoint_response_algorithms",
        "rows_used": int(len(data)),
        "evidence_count": int(groups.nunique()),
        "positive_prevalence": float(y.mean()),
        "features": numeric_features,
        "review_rows_matched": matched_review_rows,
        "cv_repeats": cv_repeats,
        "random_seed": random_seed,
        "baseline_model": "logistic_l2_strong",
        "selected_model": selected_model,
        "promoted_model": promoted_model,
        "promotion_policy": (
            f"repeated AUC gain >= {minimum_auc_gain:.3f}; leave-one-study-out AUC and "
            "study-equal AUC must not decline; cluster-bootstrap AUC p025 >= 0.50; "
            "leave-one-study-out AP must exceed prevalence"
        ),
        "candidate_results": candidate_results,
        "unavailable_optional_algorithms": unavailable,
        "package_versions": _package_versions(),
        "decision": (
            f"promote_{promoted_model}" if promoted_model else "retain_logistic_l2_strong"
        ),
        "limitation": (
            "Internal grouped validation only. Algorithm promotion does not establish external "
            "or clinical validity."
        ),
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
    return ModernResponseBenchmarkResult(
        output_path=output_path,
        selected_model=selected_model,
        promoted_model=promoted_model,
        rows_used=len(data),
        evidence_count=int(groups.nunique()),
    )


def _modern_candidates(
    numeric_features: list[str],
) -> tuple[dict[str, Pipeline], list[dict[str, str]]]:
    candidates = {
        "logistic_l2_strong": _build_model(
            numeric_features,
            [],
            LogisticRegression(
                C=0.01, class_weight="balanced", max_iter=2000, random_state=17
            ),
        ),
        "hist_gradient_boosting_regularized": _build_model(
            numeric_features,
            [],
            HistGradientBoostingClassifier(
                max_iter=60,
                learning_rate=0.03,
                max_leaf_nodes=3,
                min_samples_leaf=15,
                l2_regularization=10.0,
                class_weight="balanced",
                random_state=17,
            ),
            scale_numeric=False,
        ),
        "extra_trees_regularized": _build_model(
            numeric_features,
            [],
            ExtraTreesClassifier(
                n_estimators=400,
                max_depth=2,
                min_samples_leaf=8,
                max_features=1.0,
                class_weight="balanced",
                random_state=17,
                n_jobs=1,
            ),
            scale_numeric=False,
        ),
    }
    unavailable: list[dict[str, str]] = []
    try:
        from lightgbm import LGBMClassifier

        candidates["lightgbm_regularized"] = _build_model(
            numeric_features,
            [],
            LGBMClassifier(
                n_estimators=60,
                learning_rate=0.03,
                num_leaves=3,
                max_depth=2,
                min_child_samples=20,
                min_split_gain=0.05,
                reg_alpha=2.0,
                reg_lambda=12.0,
                class_weight="balanced",
                verbosity=-1,
                random_state=17,
                n_jobs=1,
            ),
            scale_numeric=False,
        )
    except ImportError:
        unavailable.append({"algorithm": "LightGBM", "extra": "modeling"})

    try:
        from catboost import CatBoostClassifier

        candidates["catboost_ordered_regularized"] = _build_model(
            numeric_features,
            [],
            CatBoostClassifier(
                iterations=100,
                depth=2,
                learning_rate=0.03,
                l2_leaf_reg=15.0,
                random_strength=0.25,
                auto_class_weights="Balanced",
                boosting_type="Ordered",
                loss_function="Logloss",
                verbose=False,
                allow_writing_files=False,
                thread_count=1,
                random_seed=17,
            ),
            scale_numeric=False,
        )
    except ImportError:
        unavailable.append({"algorithm": "CatBoost", "extra": "modern-modeling"})
    return candidates, unavailable


def _promotion_decision(
    candidate: dict[str, object],
    baseline: dict[str, object],
    minimum_auc_gain: float,
) -> tuple[bool, list[str]]:
    if candidate["model"] == baseline["model"]:
        return False, ["baseline_reference"]
    candidate_logo = candidate["leave_one_study_out"]
    baseline_logo = baseline["leave_one_study_out"]
    checks = {
        "repeated_auc_gain": float(candidate["repeated_roc_auc_mean"])
        >= float(baseline["repeated_roc_auc_mean"]) + minimum_auc_gain,
        "leave_one_study_out_auc_not_lower": float(candidate_logo["roc_auc"] or 0.0)
        >= float(baseline_logo["roc_auc"] or 0.0),
        "study_equal_auc_not_lower": float(candidate_logo["study_equal_roc_auc"] or 0.0)
        >= float(baseline_logo["study_equal_roc_auc"] or 0.0),
        "bootstrap_lower_bound": float(
            candidate_logo["cluster_bootstrap_roc_auc_p025"] or 0.0
        )
        >= 0.50,
        "average_precision_above_prevalence": float(
            candidate_logo["average_precision"] or 0.0
        )
        > float(candidate_logo["positive_prevalence"] or 0.0),
    }
    failed = [name for name, passed in checks.items() if not passed]
    return not failed, failed or ["all_promotion_checks_passed"]


def _mean(rows: list[dict[str, float | int]], field: str) -> float:
    return float(sum(float(row[field]) for row in rows) / len(rows))


def _std(rows: list[dict[str, float | int]], field: str) -> float:
    mean = _mean(rows, field)
    return float((sum((float(row[field]) - mean) ** 2 for row in rows) / len(rows)) ** 0.5)


def _package_versions() -> dict[str, str]:
    versions = {}
    for package in ("scikit-learn", "lightgbm", "catboost"):
        try:
            versions[package] = importlib.metadata.version(package)
        except importlib.metadata.PackageNotFoundError:
            continue
    return versions
