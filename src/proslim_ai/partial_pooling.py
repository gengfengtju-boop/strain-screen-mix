from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.linear_model import Ridge
from sklearn.metrics import mean_absolute_error
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from .arm_effects import _add_interpretable_intervention_features


NUMERIC_FEATURES = ["log10_cfu_per_day", "duration_weeks", "sample_size"]
CATEGORICAL_FEATURES = [
    "stratum",
    "intervention_class",
    "microbial_family",
    "formulation_complexity",
    "dose_status",
    "duration_status",
    "dosage_form_group",
]


def evaluate_partial_pooling_baseline(
    quality_path: Path,
    arm_path: Path,
    metrics_output: Path,
    predictions_output: Path,
    minimum_studies_per_stratum: int = 5,
    minimum_relative_improvement: float = 0.10,
) -> dict[str, object]:
    quality = pd.read_csv(quality_path)
    data = quality[
        quality["primary_analysis_eligible"].astype(str).str.lower().eq("true")
    ].copy()
    data["stratum"] = (
        data["outcome_domain"].astype(str) + "|" + data["canonical_unit"].astype(str)
    )
    data = _collapse_study_strata(data)
    arms = pd.read_csv(arm_path)
    active = arms[arms["arm_role"].eq("intervention")][
        [
            "study_id",
            "intervention_class",
            "species",
            "strain",
            "log10_cfu_per_day",
            "duration_weeks",
            "dosage_form",
            "sample_size",
        ]
    ]
    data = data.drop(
        columns=["intervention_class"], errors="ignore"
    ).merge(active, on="study_id", how="left")
    data = _add_interpretable_intervention_features(data)
    valid_strata = data.groupby("stratum")["analysis_study_id"].nunique()
    valid_strata = set(valid_strata[valid_strata >= minimum_studies_per_stratum].index)
    data = data[data["stratum"].isin(valid_strata)].reset_index(drop=True)
    if not len(data):
        raise ValueError("No strata meet the partial-pooling minimum study count")

    predictions = np.full(len(data), np.nan)
    null_predictions = np.full(len(data), np.nan)
    groups = data["analysis_study_id"].astype(str).to_numpy()
    features = NUMERIC_FEATURES + CATEGORICAL_FEATURES
    for held_out in np.unique(groups):
        test = groups == held_out
        train = ~test
        training = data.loc[train].copy()
        testing = data.loc[test].copy()
        stats = training.groupby("stratum")["estimate"].agg(["mean", "std", "count"])
        eligible_test = testing["stratum"].map(stats["count"]).fillna(0) >= 3
        if not eligible_test.any():
            continue
        training = training[training["stratum"].isin(testing.loc[eligible_test, "stratum"])]
        means = training["stratum"].map(stats["mean"]).astype(float)
        scales = training["stratum"].map(stats["std"]).astype(float).fillna(1.0)
        scales = scales.mask(scales.abs() < 1e-9, 1.0)
        normalized_target = (training["estimate"].astype(float) - means) / scales
        model = _partial_pooling_pipeline()
        model.fit(training[features], normalized_target)
        test_indices = testing.index[eligible_test]
        test_rows = data.loc[test_indices]
        predicted_z = model.predict(test_rows[features])
        test_means = test_rows["stratum"].map(stats["mean"]).astype(float).to_numpy()
        test_scales = (
            test_rows["stratum"].map(stats["std"]).astype(float).fillna(1.0).to_numpy()
        )
        test_scales = np.where(np.abs(test_scales) < 1e-9, 1.0, test_scales)
        predictions[test_indices] = test_means + predicted_z * test_scales
        null_predictions[test_indices] = test_means

    evaluated = np.isfinite(predictions) & np.isfinite(null_predictions)
    prediction_table = data.loc[evaluated, [
        "effect_id", "study_id", "analysis_study_id", "stratum", "estimate"
    ]].copy()
    prediction_table["predicted_effect"] = predictions[evaluated]
    prediction_table["null_predicted_effect"] = null_predictions[evaluated]
    prediction_table["residual"] = (
        prediction_table["estimate"] - prediction_table["predicted_effect"]
    )

    strata: list[dict[str, object]] = []
    for stratum, group in prediction_table.groupby("stratum"):
        mae = float(mean_absolute_error(group["estimate"], group["predicted_effect"]))
        null_mae = float(
            mean_absolute_error(group["estimate"], group["null_predicted_effect"])
        )
        improvement = (null_mae - mae) / null_mae if null_mae > 0 else 0.0
        strata.append(
            {
                "stratum": stratum,
                "rows": int(len(group)),
                "studies": int(group["analysis_study_id"].nunique()),
                "mae": mae,
                "null_mae": null_mae,
                "relative_mae_improvement": float(improvement),
                "passes_improvement_gate": bool(improvement >= minimum_relative_improvement),
            }
        )
    report = {
        "model_level": "cross_outcome_partial_pooling_ridge_baseline",
        "validation": "leave_one_canonical_trial_out_with_fold_local_stratum_scaling",
        "rows_evaluated": int(len(prediction_table)),
        "studies_evaluated": int(prediction_table["analysis_study_id"].nunique()),
        "strata_evaluated": int(len(strata)),
        "minimum_relative_mae_improvement": minimum_relative_improvement,
        "strata_passing_improvement_gate": int(
            sum(row["passes_improvement_gate"] for row in strata)
        ),
        "strata": strata,
        "combination_ranking_enabled": False,
        "limitation": (
            "Shared ridge coefficients provide partial pooling after fold-local outcome "
            "standardization. This is not a strain-specific random-effects estimate and "
            "does not replace prospective external validation."
        ),
    }
    predictions_output.parent.mkdir(parents=True, exist_ok=True)
    prediction_table.to_csv(predictions_output, index=False)
    metrics_output.write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report


def _collapse_study_strata(data: pd.DataFrame) -> pd.DataFrame:
    rows: list[pd.Series] = []
    for _, group in data.groupby(["analysis_study_id", "stratum"], sort=False):
        direct = group[group["variance_provenance"].isin(["reported_ci", "arm_sd_and_n"])]
        if len(direct):
            rows.append(direct.sort_values("variance").iloc[0])
        else:
            row = group.iloc[0].copy()
            row["estimate"] = float(group["estimate"].astype(float).median())
            rows.append(row)
    return pd.DataFrame(rows).reset_index(drop=True)


def _partial_pooling_pipeline() -> Pipeline:
    preprocess = ColumnTransformer(
        [
            (
                "numeric",
                Pipeline(
                    [
                        ("impute", SimpleImputer(strategy="median", keep_empty_features=True)),
                        ("scale", StandardScaler()),
                    ]
                ),
                NUMERIC_FEATURES,
            ),
            (
                "categorical",
                Pipeline(
                    [
                        ("impute", SimpleImputer(strategy="most_frequent")),
                        ("encode", OneHotEncoder(handle_unknown="ignore")),
                    ]
                ),
                CATEGORICAL_FEATURES,
            ),
        ]
    )
    return Pipeline([("preprocess", preprocess), ("ridge", Ridge(alpha=10.0))])
