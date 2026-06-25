"""E1b — do HUMAnN functional pathways add orthogonal signal beyond taxonomy?

Pathways encode gene/functional content, partly orthogonal to species composition. Tests
species-only vs pathway-only vs species+pathway under grouped 10-fold CV + leave-one-study-out
POOLED external AUC (same protocol as E5). Pre-registered success: species+pathway external
AUC > species-only by >=0.02.

    PYTHONPATH=src python scripts/obesity_model/e1b_functional_pathways.py
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import GroupKFold

ROOT = Path(__file__).resolve().parents[2]
META = ROOT / "data/metadata/sample_metadata_raw.csv"
WIDE = ROOT / "data/taxonomic_profile/species_abundance_wide.csv"
PATH = ROOT / "data/functional_profile/pathway_abundance_wide.csv"
OUT = ROOT / "results/prediction_results/e1b_functional_pathways_20260614.json"
EPS = 1e-4
MIN_PER_CLASS = 8


def _model():
    return HistGradientBoostingClassifier(max_depth=3, learning_rate=0.05, max_iter=400,
                                          l2_regularization=1.0, random_state=17)


def _grouped(X, y, g):
    gkf = GroupKFold(n_splits=10); p = np.zeros(len(y))
    for tr, te in gkf.split(X, y, g):
        m = _model(); m.fit(X[tr], y[tr]); p[te] = m.predict_proba(X[te])[:, 1]
    return float(roc_auc_score(y, p))


def _loso(X, y, st):
    oof = np.full(len(y), np.nan)
    for s in np.unique(st):
        te = st == s
        if y[te].sum() < MIN_PER_CLASS or (~y[te].astype(bool)).sum() < MIN_PER_CLASS:
            continue
        m = _model(); m.fit(X[~te], y[~te]); oof[te] = m.predict_proba(X[te])[:, 1]
    mask = ~np.isnan(oof)
    return float(roc_auc_score(y[mask], oof[mask]))


def main() -> None:
    meta = pd.read_csv(META)[["sample_id", "study_id", "obesity_status"]]
    meta = meta[meta["obesity_status"].isin(["lean", "obesity"])]
    sp = pd.read_csv(WIDE)
    pw = pd.read_csv(PATH)
    df = meta.merge(sp, on="sample_id").merge(pw, on="sample_id", suffixes=("_sp", "_pw"))
    print(f"samples with both species and pathways: {len(df)}")

    sp_cols = [c for c in sp.columns if c != "sample_id"]
    pw_cols = [c for c in pw.columns if c != "sample_id"]
    # prevalence filter both
    sp_keep = [c for c in sp_cols if (df[c] > 0).mean() >= 0.10]
    pw_keep = [c for c in pw_cols if (df[c] > 0).mean() >= 0.10]
    print(f"species features {len(sp_keep)} | pathway features {len(pw_keep)}")

    Xsp = np.log10(df[sp_keep].astype(float).to_numpy() + EPS)
    Xpw = np.log10(df[pw_keep].astype(float).to_numpy() + EPS)
    Xboth = np.column_stack([Xsp, Xpw])
    y = (df["obesity_status"] == "obesity").astype(int).to_numpy()
    g = df["study_id"].to_numpy()

    res = {}
    for name, X in (("species_only", Xsp), ("pathway_only", Xpw), ("species_plus_pathway", Xboth)):
        gr = _grouped(X, y, g); ex = _loso(X, y, g)
        res[name] = {"n_features": X.shape[1], "grouped_cv_auc": round(gr, 4), "loso_external_auc": round(ex, 4)}
        print(f"{name:22} feats={X.shape[1]:4d} grouped={gr:.4f} external_LOSO={ex:.4f}")

    base = res["species_only"]; both = res["species_plus_pathway"]
    report = {
        "experiment": "E1b_functional_pathways_orthogonal_information",
        "samples": int(len(df)), "results": res,
        "external_delta_vs_species": round(both["loso_external_auc"] - base["loso_external_auc"], 4),
        "grouped_delta_vs_species": round(both["grouped_cv_auc"] - base["grouped_cv_auc"], 4),
        "preregistered_success": "species+pathway external AUC +>=0.02",
        "verdict": "pathways_add_orthogonal_signal" if both["loso_external_auc"] - base["loso_external_auc"] >= 0.02
                   else "no_meaningful_orthogonal_gain",
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"\nexternal delta (species+pathway vs species): {report['external_delta_vs_species']:+.4f} -> {report['verdict']}")
    print(f"Report: {OUT}")


if __name__ == "__main__":
    main()
