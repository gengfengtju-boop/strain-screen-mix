"""Leave-one-subject-out (LOSO) individual baseline-microbiome -> response pilot.

This is the modeling scaffold for the highest-leverage path: predicting an
*individual's* metabolic response (e.g. delta BMI / delta weight, or responder
status) from that subject's baseline gut microbiome. It is deliberately small and
honestly gated:

- Validation is leave-one-subject-out (each subject held out once); never random
  row splits, because repeated samples from one subject leak.
- A model is only declared useful if it beats the no-information null (predict the
  training mean for regression, predict prevalence for classification) by a
  configurable margin.

It does NOT ship with real data. Supply (1) a baseline taxonomic abundance table
indexed by subject and (2) a per-subject outcome. Until a probiotic intervention
RCT with deposited per-subject sequencing AND recoverable individual outcomes is
curated, this runs only on the synthetic self-test below.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression, Ridge
from sklearn.metrics import mean_absolute_error, roc_auc_score
from sklearn.preprocessing import StandardScaler

MIN_SUBJECTS = 12
MIN_RELATIVE_MAE_IMPROVEMENT = 0.10
MIN_AUC = 0.65


@dataclass
class PilotResult:
    task: str
    n_subjects: int
    n_features: int
    metric_name: str
    metric_value: float
    null_value: float
    beats_null: bool
    enabled_for_use: bool
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "task": self.task,
            "n_subjects": self.n_subjects,
            "n_features": self.n_features,
            "metric_name": self.metric_name,
            "metric_value": round(float(self.metric_value), 4),
            "null_value": round(float(self.null_value), 4),
            "beats_null": bool(self.beats_null),
            "individual_model_enabled": bool(self.enabled_for_use),
            "notes": self.notes,
        }


def leave_one_subject_out(
    profiles: pd.DataFrame,
    outcomes: pd.Series,
    task: str = "regression",
) -> PilotResult:
    """Run LOSO CV. `profiles` is subjects x taxa (baseline); `outcomes` is the
    per-subject label aligned by index."""
    shared = profiles.index.intersection(outcomes.index)
    X_all = profiles.loc[shared]
    y_all = outcomes.loc[shared].astype(float)
    n = len(shared)
    notes: list[str] = []
    if n < MIN_SUBJECTS:
        notes.append(f"only {n} subjects (< {MIN_SUBJECTS}); underpowered")

    preds = np.full(n, np.nan)
    nulls = np.full(n, np.nan)
    X = X_all.to_numpy(dtype=float)
    y = y_all.to_numpy(dtype=float)
    for i in range(n):
        train = np.arange(n) != i
        scaler = StandardScaler().fit(X[train])
        Xtr, Xte = scaler.transform(X[train]), scaler.transform(X[i : i + 1])
        if task == "classification":
            if len(np.unique(y[train])) < 2:
                preds[i] = y[train].mean()
            else:
                model = LogisticRegression(penalty="l2", C=0.5, max_iter=1000)
                model.fit(Xtr, y[train])
                preds[i] = model.predict_proba(Xte)[0, 1]
            nulls[i] = y[train].mean()
        else:
            model = Ridge(alpha=10.0)
            model.fit(Xtr, y[train])
            preds[i] = model.predict(Xte)[0]
            nulls[i] = y[train].mean()

    if task == "classification":
        try:
            metric = float(roc_auc_score(y, preds))
        except ValueError:
            metric = float("nan")
        null_val = 0.5
        beats = np.isfinite(metric) and metric >= MIN_AUC
        result = PilotResult("classification", n, X.shape[1], "roc_auc",
                             metric, null_val, beats, beats and n >= MIN_SUBJECTS, notes)
    else:
        mae = float(mean_absolute_error(y, preds))
        null_mae = float(mean_absolute_error(y, nulls))
        rel = (null_mae - mae) / null_mae if null_mae else 0.0
        beats = rel >= MIN_RELATIVE_MAE_IMPROVEMENT
        notes.append(f"relative_mae_improvement={rel:.3f}")
        result = PilotResult("regression", n, X.shape[1], "mae",
                             mae, null_mae, beats, beats and n >= MIN_SUBJECTS, notes)
    return result


def synthetic_demo(seed: int = 0, signal: bool = True) -> PilotResult:
    """Self-test: build a small subjects x taxa baseline table where (optionally) a
    few taxa drive the outcome, and confirm LOSO recovers signal vs noise."""
    rng = np.random.default_rng(seed)
    n, p = 40, 25
    X = rng.lognormal(mean=0.0, sigma=1.0, size=(n, p))
    X = X / X.sum(axis=1, keepdims=True)
    idx = [f"subject{i:02d}" for i in range(n)]
    profiles = pd.DataFrame(X, index=idx, columns=[f"taxon{j}" for j in range(p)])
    if signal:
        beta = np.zeros(p)
        beta[:4] = np.array([8.0, -6.0, 5.0, -4.0])
        y = X @ beta + rng.normal(0, 0.2, size=n)
    else:
        y = rng.normal(0, 1.0, size=n)
    outcomes = pd.Series(y, index=idx)
    return leave_one_subject_out(profiles, outcomes, task="regression")
