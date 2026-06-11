from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import average_precision_score, balanced_accuracy_score, roc_auc_score
from sklearn.model_selection import StratifiedGroupKFold
from sklearn.preprocessing import OrdinalEncoder


FEATURES = ["outcome_domain", "endpoint_type", "analysis_population", "comparison"]


def benchmark_tabpfn(
    structured_outcomes_path: Path,
    model_path: Path,
    output_path: Path,
    n_estimators: int = 2,
    random_seed: int = 17,
) -> dict[str, object]:
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
    X_raw = data[FEATURES].fillna("missing").astype(str).to_numpy()
    y = data["label"].to_numpy(dtype=int)
    groups = data["evidence_id"].fillna("").astype(str).to_numpy()
    folds = StratifiedGroupKFold(n_splits=5, shuffle=True, random_state=random_seed)
    probabilities = np.zeros(len(y), dtype=float)
    for train, test in folds.split(X_raw, y, groups):
        encoder = OrdinalEncoder(handle_unknown="use_encoded_value", unknown_value=-1)
        X_train = encoder.fit_transform(X_raw[train]).astype(np.float32)
        X_test = encoder.transform(X_raw[test]).astype(np.float32)
        model = TabPFNClassifier(
            model_path=model_path,
            device="cpu",
            n_estimators=n_estimators,
            n_preprocessing_jobs=1,
            random_state=random_seed,
            categorical_features_indices=list(range(len(FEATURES))),
        )
        model.fit(X_train, y[train])
        probabilities[test] = model.predict_proba(X_test)[:, 1]

    predictions = probabilities >= 0.5
    metrics = {
        "model": "TabPFNClassifier",
        "tabpfn_checkpoint": str(model_path),
        "rows": len(y),
        "evidence_groups": int(pd.Series(groups).nunique()),
        "validation": "five_fold_stratified_group_cross_validation_by_evidence_id",
        "roc_auc": float(roc_auc_score(y, probabilities)),
        "average_precision": float(average_precision_score(y, probabilities)),
        "balanced_accuracy": float(balanced_accuracy_score(y, predictions)),
        "positive_prevalence": float(y.mean()),
        "eligible_for_combination_fusion": bool(
            roc_auc_score(y, probabilities) >= 0.55
            and average_precision_score(y, probabilities) > y.mean()
        ),
        "feature_policy": "leakage_safe_descriptors_only",
        "features": FEATURES,
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(metrics, indent=2), encoding="utf-8")
    return metrics
