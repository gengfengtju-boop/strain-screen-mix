"""SHAP interpretability for the trained obesity classifier (lean vs obesity).

Explains which gut species drive the model's obesity prediction. Produces a beeswarm
summary, a mean-|SHAP| bar chart, and a ranked importance CSV. Uses the study-grouped
model's features (log10 species abundance, >=10% prevalence).

    PYTHONPATH=src python scripts/visualization/obesity_model_shap.py
"""
from __future__ import annotations

import pickle
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import shap

ROOT = Path(__file__).resolve().parents[2]
META = ROOT / "data/metadata/sample_metadata_raw.csv"
WIDE = ROOT / "data/taxonomic_profile/species_abundance_wide.csv"
MODEL = ROOT / "models/obesity_classifier/obesity_classifier_20260613.pkl"
OUT = ROOT / "results/SHAP_results"
SUBSAMPLE = 1500  # samples for SHAP (speed); explainer is exact on the tree model


def main() -> None:
    with open(MODEL, "rb") as fh:
        bundle = pickle.load(fh)
    model = bundle["model"]
    features = bundle.get("feature_columns") or bundle["features"]

    meta = pd.read_csv(META)[["sample_id", "obesity_status"]]
    meta = meta[meta["obesity_status"].isin(["lean", "obesity"])]
    wide = pd.read_csv(WIDE)
    df = meta.merge(wide, on="sample_id", how="inner")
    X = np.log10(df[features].astype(float) + 1e-4)
    rng = np.random.default_rng(17)
    idx = rng.choice(len(X), size=min(SUBSAMPLE, len(X)), replace=False)
    Xs = X.iloc[idx]

    # tree-exact SHAP for the histogram gradient boosting classifier
    try:
        tree_model = model.named_steps["classifier"]
        transformed = model.named_steps["preprocess"].transform(Xs)
        explainer = shap.TreeExplainer(tree_model)
        sv = explainer.shap_values(transformed)
    except Exception as exc:  # fall back to model-agnostic on a small background
        print(f"TreeExplainer failed ({exc}); using sampling explainer.")
        bg = shap.utils.sample(X, 100, random_state=17)
        explainer = shap.Explainer(lambda d: model.predict_proba(d)[:, 1], bg)
        sv = explainer(Xs).values
    sv = sv[1] if isinstance(sv, list) else sv  # positive (obesity) class

    OUT.mkdir(parents=True, exist_ok=True)

    # 1. ranked importance CSV. Direction = corr(feature abundance, its SHAP value):
    # positive => higher abundance pushes the prediction toward obesity. (The signed
    # MEAN SHAP is a poor direction proxy because it averages over both tails.)
    Xs_arr = Xs.to_numpy()
    feat_shap_corr = np.array([
        np.corrcoef(Xs_arr[:, j], sv[:, j])[0, 1] if Xs_arr[:, j].std() > 0 else 0.0
        for j in range(len(features))
    ])
    imp = pd.DataFrame({
        "species": features,
        "mean_abs_shap": np.abs(sv).mean(axis=0),
        "abundance_shap_corr": feat_shap_corr,
    }).sort_values("mean_abs_shap", ascending=False)
    imp["direction"] = np.where(
        imp["abundance_shap_corr"] > 0, "higher_abundance_raises_obesity", "higher_abundance_lowers_obesity"
    )
    imp.to_csv(OUT / "obesity_classifier_shap_importance_20260613.csv", index=False)

    # 2. beeswarm summary (top 20)
    plt.figure()
    shap.summary_plot(sv, Xs, feature_names=features, max_display=20, show=False)
    plt.title("Obesity classifier — SHAP beeswarm (top 20 gut species)")
    plt.tight_layout()
    plt.savefig(OUT / "obesity_shap_beeswarm_20260613.png", dpi=150, bbox_inches="tight")
    plt.close()

    # 3. mean-|SHAP| bar (top 20)
    plt.figure()
    shap.summary_plot(sv, Xs, feature_names=features, plot_type="bar", max_display=20, show=False)
    plt.title("Obesity classifier — mean |SHAP| importance (top 20)")
    plt.tight_layout()
    plt.savefig(OUT / "obesity_shap_bar_20260613.png", dpi=150, bbox_inches="tight")
    plt.close()

    print(f"SHAP computed on {len(idx)} samples, {len(features)} species features.")
    print(f"Outputs -> {OUT}")
    print("\nTop 12 species by mean|SHAP|:")
    print(imp.head(12)[["species", "mean_abs_shap", "direction"]].to_string(index=False))


if __name__ == "__main__":
    main()
