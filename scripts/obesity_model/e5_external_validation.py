"""E5 — external validation of the obesity classifier (lean vs obesity).

The decisive test: does the model transfer to studies it never saw? Two designs:
  (1) Leave-one-study-out (LOSO): train on all other studies, predict the held-out study
      -> per-study external AUC distribution + one POOLED external AUC over all held-out preds.
  (2) Study-level 70/30 split x repeats: hold out whole studies as an external set.
Pre-registered success: external AUC > 0.65. Compared against the internal grouped-CV 0.729.

    PYTHONPATH=src python scripts/obesity_model/e5_external_validation.py
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.metrics import roc_auc_score

ROOT = Path(__file__).resolve().parents[2]
META = ROOT / "data/metadata/sample_metadata_raw.csv"
WIDE = ROOT / "data/taxonomic_profile/species_abundance_wide.csv"
OUT = ROOT / "results/prediction_results/e5_external_validation_20260614.json"
MIN_PER_CLASS = 8  # a held-out study needs >=8 lean and >=8 obese for a meaningful AUC


def _model():
    return HistGradientBoostingClassifier(max_depth=3, learning_rate=0.05, max_iter=400,
                                          l2_regularization=1.0, random_state=17)


def main() -> None:
    meta = pd.read_csv(META)[["sample_id", "study_id", "obesity_status"]]
    meta = meta[meta["obesity_status"].isin(["lean", "obesity"])]
    wide = pd.read_csv(WIDE)
    df = meta.merge(wide, on="sample_id", how="inner")
    species = [c for c in wide.columns if c != "sample_id"]
    prev = (df[species] > 0).mean()
    species = prev[prev >= 0.10].index.tolist()
    X = np.log10(df[species].astype(float) + 1e-4).to_numpy()
    y = (df["obesity_status"] == "obesity").astype(int).to_numpy()
    studies = df["study_id"].to_numpy()

    # ---- (1) leave-one-study-out external ----
    per_study = []
    oof = np.full(len(y), np.nan)
    for s in np.unique(studies):
        te = studies == s
        if y[te].sum() < MIN_PER_CLASS or (~y[te].astype(bool)).sum() < MIN_PER_CLASS:
            continue  # held-out study lacks both classes -> no within-study AUC
        m = _model(); m.fit(X[~te], y[~te])
        p = m.predict_proba(X[te])[:, 1]
        oof[te] = p
        per_study.append({"study": str(s), "n": int(te.sum()),
                          "obese_frac": round(float(y[te].mean()), 2),
                          "external_auc": round(float(roc_auc_score(y[te], p)), 4)})
    aucs = [r["external_auc"] for r in per_study]
    mask = ~np.isnan(oof)
    pooled_loso = float(roc_auc_score(y[mask], oof[mask]))

    # ---- (2) study-level 70/30 holdout x repeats ----
    uniq = np.unique(studies)
    rng = np.random.default_rng(17)
    split_aucs = []
    for _ in range(10):
        perm = rng.permutation(uniq)
        n_test = max(1, int(round(0.30 * len(uniq))))
        test_studies = set(perm[:n_test])
        te = np.array([s in test_studies for s in studies])
        if y[te].sum() < MIN_PER_CLASS or (~y[te].astype(bool)).sum() < MIN_PER_CLASS:
            continue
        m = _model(); m.fit(X[~te], y[~te])
        split_aucs.append(float(roc_auc_score(y[te], m.predict_proba(X[te])[:, 1])))

    report = {
        "experiment": "E5_external_validation_obesity_classifier",
        "design": "leave-one-study-out + study-level 70/30 holdout; lean vs obesity",
        "internal_grouped_cv_auc_reference": 0.729,
        "preregistered_success_threshold": 0.65,
        "loso": {
            "studies_with_both_classes": len(per_study),
            "pooled_external_auc": round(pooled_loso, 4),
            "per_study_auc_median": round(float(np.median(aucs)), 4) if aucs else None,
            "per_study_auc_iqr": [round(float(np.percentile(aucs, 25)), 4),
                                  round(float(np.percentile(aucs, 75)), 4)] if aucs else None,
            "per_study_auc_min_max": [round(min(aucs), 4), round(max(aucs), 4)] if aucs else None,
            "fraction_studies_auc_above_0p65": round(float(np.mean([a > 0.65 for a in aucs])), 3) if aucs else None,
            "per_study": sorted(per_study, key=lambda r: r["external_auc"]),
        },
        "study_holdout_70_30": {
            "repeats": len(split_aucs),
            "mean_external_auc": round(float(np.mean(split_aucs)), 4) if split_aucs else None,
            "std": round(float(np.std(split_aucs)), 4) if split_aucs else None,
            "min_max": [round(min(split_aucs), 4), round(max(split_aucs), 4)] if split_aucs else None,
        },
        "verdict": ("transfers_external_auc_above_threshold"
                    if pooled_loso > 0.65 else "below_external_threshold"),
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(report, indent=2), encoding="utf-8")

    print(f"LOSO studies with both classes: {len(per_study)}")
    print(f"POOLED leave-one-study-out external AUC: {pooled_loso:.4f}  (internal grouped 0.729; threshold 0.65)")
    if aucs:
        print(f"per-study external AUC: median {np.median(aucs):.3f}, "
              f"IQR [{np.percentile(aucs,25):.3f}, {np.percentile(aucs,75):.3f}], "
              f"min-max [{min(aucs):.3f}, {max(aucs):.3f}]")
        print(f"fraction of studies with AUC>0.65: {np.mean([a>0.65 for a in aucs]):.2f}")
    if split_aucs:
        print(f"study-level 70/30 external AUC: {np.mean(split_aucs):.4f} +/- {np.std(split_aucs):.4f}")
    print(f"VERDICT: {report['verdict']}")
    print(f"Report: {OUT}")


if __name__ == "__main__":
    main()
