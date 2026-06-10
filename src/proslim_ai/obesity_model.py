from __future__ import annotations

import json
import pickle
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.linear_model import ElasticNet, LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    balanced_accuracy_score,
    f1_score,
    mean_absolute_error,
    mean_squared_error,
    r2_score,
    roc_auc_score,
)
from sklearn.model_selection import GroupKFold, StratifiedGroupKFold, cross_val_predict
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler


MIN_SAMPLES = 30
MIN_STUDIES = 3
MIN_CLASS_SAMPLES = 10


@dataclass(frozen=True)
class ObesityModelResult:
    metrics_output: Path
    classifier_output: Path
    bmi_regressor_output: Path
    samples_used: int
    studies_used: int


def train_obesity_models(
    metadata_path: Path,
    feature_matrix_path: Path,
    metrics_output: Path,
    classifier_output: Path,
    bmi_regressor_output: Path,
) -> ObesityModelResult:
    metadata = pd.read_csv(metadata_path)
    features = pd.read_csv(feature_matrix_path)
    data, feature_columns = _prepare_training_data(metadata, features)
    _validate_training_data(data, feature_columns)

    groups = data["study_id"].astype(str)
    classification = data[data["obesity_label"].notna()].copy()
    classification_groups = classification["study_id"].astype(str)
    classifier = _classification_pipeline(feature_columns)
    classifier_cv = StratifiedGroupKFold(
        n_splits=min(5, classification_groups.nunique()), shuffle=True, random_state=17
    )
    classifier_probability = cross_val_predict(
        classifier,
        classification[feature_columns],
        classification["obesity_label"].astype(int),
        groups=classification_groups,
        cv=classifier_cv,
        method="predict_proba",
    )[:, 1]
    classifier.fit(classification[feature_columns], classification["obesity_label"].astype(int))

    regression = data[data["BMI"].notna()].copy()
    regression_groups = regression["study_id"].astype(str)
    regressor = _regression_pipeline(feature_columns)
    regression_cv = GroupKFold(n_splits=min(5, regression_groups.nunique()))
    bmi_prediction = cross_val_predict(
        regressor,
        regression[feature_columns],
        regression["BMI"].astype(float),
        groups=regression_groups,
        cv=regression_cv,
    )
    regressor.fit(regression[feature_columns], regression["BMI"].astype(float))

    labels = classification["obesity_label"].astype(int).to_numpy()
    predicted_labels = (classifier_probability >= 0.5).astype(int)
    metrics = {
        "model_level": "sample_level_microbiome_baseline",
        "validation": "grouped_cross_validation_by_study_id",
        "samples_used": int(len(data)),
        "studies_used": int(groups.nunique()),
        "feature_count": len(feature_columns),
        "obesity_classification": {
            "rows": int(len(classification)),
            "auc": float(roc_auc_score(labels, classifier_probability)),
            "accuracy": float(accuracy_score(labels, predicted_labels)),
            "balanced_accuracy": float(balanced_accuracy_score(labels, predicted_labels)),
            "f1": float(f1_score(labels, predicted_labels, zero_division=0)),
        },
        "bmi_regression": {
            "rows": int(len(regression)),
            "r2": float(r2_score(regression["BMI"], bmi_prediction)),
            "mae": float(mean_absolute_error(regression["BMI"], bmi_prediction)),
            "rmse": float(np.sqrt(mean_squared_error(regression["BMI"], bmi_prediction))),
        },
        "limitations": [
            "Internal grouped cross-validation is not an external validation cohort.",
            "Overweight/uncertain obesity labels are excluded from binary OMS classification.",
        ],
    }
    metrics_output.parent.mkdir(parents=True, exist_ok=True)
    metrics_output.write_text(json.dumps(metrics, indent=2, sort_keys=True), encoding="utf-8")
    _write_model(classifier_output, classifier, feature_columns, "obesity_microbiome_classifier")
    _write_model(bmi_regressor_output, regressor, feature_columns, "bmi_regressor")
    return ObesityModelResult(
        metrics_output=metrics_output,
        classifier_output=classifier_output,
        bmi_regressor_output=bmi_regressor_output,
        samples_used=len(data),
        studies_used=int(groups.nunique()),
    )


def _prepare_training_data(
    metadata: pd.DataFrame, features: pd.DataFrame
) -> tuple[pd.DataFrame, list[str]]:
    required_metadata = {"sample_id", "study_id", "BMI", "obesity_status"}
    missing_metadata = required_metadata - set(metadata.columns)
    if missing_metadata:
        raise ValueError(f"Metadata missing required columns: {sorted(missing_metadata)}")
    if "sample_id" not in features.columns:
        raise ValueError("Feature matrix must contain sample_id.")
    if features["sample_id"].duplicated().any():
        raise ValueError("Feature matrix must be wide with exactly one row per sample_id.")
    feature_columns = [column for column in features.columns if column != "sample_id"]
    for column in feature_columns:
        features[column] = pd.to_numeric(features[column], errors="coerce")
    data = metadata.merge(features, on="sample_id", how="inner", validate="one_to_one")
    data["BMI"] = pd.to_numeric(data["BMI"], errors="coerce")
    data["obesity_label"] = data["obesity_status"].map(_obesity_label)
    usable_features = [
        column for column in feature_columns if int(data[column].notna().sum()) >= MIN_CLASS_SAMPLES
    ]
    return data, usable_features


def _obesity_label(value: object) -> float:
    text = str(value or "").strip().lower().replace("_", "-")
    if text in {"obese", "obesity", "yes", "1", "case"}:
        return 1.0
    if text in {"normal", "normal-weight", "non-obese", "healthy", "no", "0", "control"}:
        return 0.0
    return np.nan


def _validate_training_data(data: pd.DataFrame, feature_columns: list[str]) -> None:
    if len(data) < MIN_SAMPLES:
        raise ValueError(f"At least {MIN_SAMPLES} matched samples are required; found {len(data)}.")
    studies = int(data["study_id"].astype(str).nunique())
    if studies < MIN_STUDIES:
        raise ValueError(f"At least {MIN_STUDIES} studies are required; found {studies}.")
    if not feature_columns:
        raise ValueError("No feature has enough observed numeric values for modeling.")
    class_counts = data["obesity_label"].value_counts()
    if len(class_counts) < 2 or int(class_counts.min()) < MIN_CLASS_SAMPLES:
        raise ValueError(
            f"OMS classification requires at least {MIN_CLASS_SAMPLES} samples in each binary class."
        )
    if int(data["BMI"].notna().sum()) < MIN_SAMPLES:
        raise ValueError(f"BMI regression requires at least {MIN_SAMPLES} non-missing BMI values.")


def _preprocessor(feature_columns: list[str]) -> ColumnTransformer:
    return ColumnTransformer(
        [
            (
                "microbiome",
                Pipeline(
                    [
                        ("imputer", SimpleImputer(strategy="median")),
                        ("scaler", StandardScaler()),
                    ]
                ),
                feature_columns,
            )
        ]
    )


def _classification_pipeline(feature_columns: list[str]) -> Pipeline:
    return Pipeline(
        [
            ("preprocess", _preprocessor(feature_columns)),
            ("classifier", LogisticRegression(class_weight="balanced", max_iter=2000, random_state=17)),
        ]
    )


def _regression_pipeline(feature_columns: list[str]) -> Pipeline:
    return Pipeline(
        [
            ("preprocess", _preprocessor(feature_columns)),
            ("regressor", ElasticNet(alpha=0.05, l1_ratio=0.5, max_iter=5000, random_state=17)),
        ]
    )


def _write_model(path: Path, model: Pipeline, features: list[str], model_type: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("wb") as handle:
        pickle.dump(
            {
                "model": model,
                "model_type": model_type,
                "feature_columns": features,
                "model_level": "sample_level_microbiome_baseline",
            },
            handle,
        )
