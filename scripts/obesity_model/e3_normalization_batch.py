"""E3 — normalization / batch-effect experiment for the obesity classifier.

Honest design note: classic batch correction (ComBat / MMUPHin) estimates per-batch
parameters and CANNOT be applied to a genuinely new cohort (its batch parameters are
unknown at prediction time), so it does not help EXTERNAL transfer -- it only helps
pooled meta-analysis. We therefore test sample-level, leakage-safe, transferable
normalizations that apply to any new sample without batch info:
  - log10 (current baseline)
  - CLR (centered log-ratio; compositionally correct)
  - within-sample rank (removes per-sample location/scale)
Each is evaluated under grouped 10-fold CV, random 10-fold CV (optimism gap) and
leave-one-study-out POOLED external AUC (same protocol as E5).

Pre-registered success: a transform improves external pooled AUC, or shrinks the
optimism gap (random - grouped) by >=30%, without lowering grouped AUC.

    PYTHONPATH=src python scripts/obesity_model/e3_normalization_batch.py
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import GroupKFold, StratifiedKFold

ROOT = Path(__file__).resolve().parents[2]
META = ROOT / "data/metadata/sample_metadata_raw.csv"
WIDE = ROOT / "data/taxonomic_profile/species_abundance_wide.csv"
OUT = ROOT / "results/prediction_results/e3_normalization_batch_20260614.json"
EPS = 1e-4
MIN_PER_CLASS = 8


def _model():
    return HistGradientBoostingClassifier(max_depth=3, learning_rate=0.05, max_iter=400,
                                          l2_regularization=1.0, random_state=17)


def _transform(rel: np.ndarray, kind: str) -> np.ndarray:
    x = rel.astype(float) + EPS
    if kind == "log10":
        return np.log10(x)
    if kind == "clr":
        logx = np.log(x)
        return logx - logx.mean(axis=1, keepdims=True)  # per-sample centered log-ratio
    if kind == "rank_within_sample":
        # per-sample rank of features scaled to [0,1]
        order = np.argsort(np.argsort(rel, axis=1), axis=1)
        return order / (rel.shape[1] - 1)
    raise ValueError(kind)


def _grouped(X, y, groups):
    gkf = GroupKFold(n_splits=10); p = np.zeros(len(y))
    for tr, te in gkf.split(X, y, groups):
        m = _model(); m.fit(X[tr], y[tr]); p[te] = m.predict_proba(X[te])[:, 1]
    return float(roc_auc_score(y, p))


def _random(X, y):
    skf = StratifiedKFold(n_splits=10, shuffle=True, random_state=17); p = np.zeros(len(y))
    for tr, te in skf.split(X, y):
        m = _model(); m.fit(X[tr], y[tr]); p[te] = m.predict_proba(X[te])[:, 1]
    return float(roc_auc_score(y, p))


def _loso_pooled(X, y, studies):
    oof = np.full(len(y), np.nan)
    for s in np.unique(studies):
        te = studies == s
        if y[te].sum() < MIN_PER_CLASS or (~y[te].astype(bool)).sum() < MIN_PER_CLASS:
            continue
        m = _model(); m.fit(X[~te], y[~te]); oof[te] = m.predict_proba(X[te])[:, 1]
    mask = ~np.isnan(oof)
    return float(roc_auc_score(y[mask], oof[mask]))


def main() -> None:
    meta = pd.read_csv(META)[["sample_id", "study_id", "obesity_status"]]
    meta = meta[meta["obesity_status"].isin(["lean", "obesity"])]
    wide = pd.read_csv(WIDE)
    df = meta.merge(wide, on="sample_id", how="inner")
    species = [c for c in wide.columns if c != "sample_id"]
    prev = (df[species] > 0).mean()
    species = prev[prev >= 0.10].index.tolist()
    rel = df[species].astype(float).to_numpy()
    y = (df["obesity_status"] == "obesity").astype(int).to_numpy()
    groups = df["study_id"].to_numpy()

    results = {}
    for kind in ("log10", "clr", "rank_within_sample"):
        X = _transform(rel, kind)
        g = _grouped(X, y, groups)
        r = _random(X, y)
        e = _loso_pooled(X, y, groups)
        results[kind] = {"grouped_cv_auc": round(g, 4), "random_cv_auc": round(r, 4),
                         "optimism_gap": round(r - g, 4), "loso_pooled_external_auc": round(e, 4)}
        print(f"{kind:20} grouped={g:.4f} random={r:.4f} gap={r-g:.4f} external_LOSO={e:.4f}")

    base = results["log10"]
    best_ext = max(results, key=lambda k: results[k]["loso_pooled_external_auc"])
    report = {
        "experiment": "E3_normalization_batch_transfer",
        "note": "ComBat/MMUPHin excluded: batch params unknown for a new cohort -> not transferable.",
        "transforms": results,
        "baseline": "log10",
        "best_external_transform": best_ext,
        "best_external_auc": results[best_ext]["loso_pooled_external_auc"],
        "improves_external_vs_baseline": results[best_ext]["loso_pooled_external_auc"] > base["loso_pooled_external_auc"],
        "optimism_gap_reduction_best": round(base["optimism_gap"] - min(results[k]["optimism_gap"] for k in results), 4),
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"\nbest external transform: {best_ext} ({results[best_ext]['loso_pooled_external_auc']:.4f} vs log10 {base['loso_pooled_external_auc']:.4f})")
    print(f"Report: {OUT}")


if __name__ == "__main__":
    main()
