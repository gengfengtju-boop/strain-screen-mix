"""AI screening predictor: predict a taxon's lean-vs-obese enrichment DIRECTION
from mechanism-independent features (functional guild + abundance), validated by
leave-one-genus-out CV. This turns the mechanism screen into a predictor that can
score strains beyond the 83 observed differential taxa, and tests whether function
predicts lean-association above chance.

Honest design: features are genus-level functional priors, so CV groups are GENERA
(leave-one-genus-out) to avoid leakage; effect size / log2FC / direction are NOT
used as features (they define the label).
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import LeaveOneGroupOut
from sklearn.metrics import roc_auc_score
from sklearn.preprocessing import StandardScaler

ROOT = Path(__file__).resolve().parents[2]
PR = ROOT / "results/prediction_results"
FEATS = ["butyrate", "propionate", "mucin", "bsh", "lactate", "log_mean_abundance"]


def main() -> None:
    diff = pd.read_csv(PR / "lean_vs_obese_trusted_differential_20260625.csv")
    guild = pd.read_csv(ROOT / "data/strain_genome/genus_functional_guild_reference_20260613.csv").set_index("genus")
    df = diff.copy()
    df["genus"] = df["species"].str.split("_").str[0]
    df = df[df["genus"].isin(guild.index)].copy()
    for col, gcol in [("butyrate", "butyrate_scfa_potential"), ("propionate", "propionate_potential"),
                      ("mucin", "mucin_interaction"), ("bsh", "bsh_potential"), ("lactate", "lactate_acetate")]:
        df[col] = df["genus"].map(lambda g: float(guild.loc[g, gcol]))
    df["log_mean_abundance"] = np.log10(((df["mean_abund_lean_pp"] + df["mean_abund_obese_pp"]) / 2) + 1e-3)
    df["label"] = (df["direction"] == "lean_enriched").astype(int)

    X = df[FEATS].to_numpy(float)
    y = df["label"].to_numpy()
    groups = df["genus"].to_numpy()

    # leave-one-genus-out CV
    logo = LeaveOneGroupOut()
    oof = np.full(len(y), np.nan)
    for tr, te in logo.split(X, y, groups):
        if len(np.unique(y[tr])) < 2:
            oof[te] = y[tr].mean()
            continue
        sc = StandardScaler().fit(X[tr])
        m = LogisticRegression(penalty="l2", C=1.0, max_iter=1000)
        m.fit(sc.transform(X[tr]), y[tr])
        oof[te] = m.predict_proba(sc.transform(X[te]))[:, 1]
    auc = roc_auc_score(y, oof)
    null = y.mean()

    # full-data model for coefficients + predicted scores
    sc = StandardScaler().fit(X)
    full = LogisticRegression(penalty="l2", C=1.0, max_iter=1000).fit(sc.transform(X), y)
    coef = dict(zip(FEATS, full.coef_[0].round(3)))
    df["ai_lean_score"] = oof.round(3)

    df_out = df[["species", "genus", "direction", "label", *FEATS, "ai_lean_score"]].sort_values("ai_lean_score", ascending=False)
    df_out.to_csv(PR / "ai_screening_predictions_20260625.csv", index=False)
    report = {
        "model": "leave_one_genus_out_logistic_regression",
        "features": FEATS, "n_taxa": int(len(y)), "n_genera": int(len(np.unique(groups))),
        "lean_prevalence": round(float(null), 3),
        "leave_one_genus_out_auc": round(float(auc), 3),
        "beats_chance": bool(auc > 0.6),
        "coefficients": coef,
        "note": "Genus-level functional features predict lean-vs-obese direction; "
                "grouped CV by genus avoids leakage. Effect/log2FC excluded (define label).",
    }
    import json
    (PR / "ai_screening_predictor_metrics_20260625.json").write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"taxa={len(y)} genera={len(np.unique(groups))} lean_prev={null:.2f}")
    print(f"leave-one-genus-out AUC = {auc:.3f}  (chance {null:.2f})")
    print("coefficients (standardized):", coef)
    print("\nwrote", (PR / 'ai_screening_predictions_20260625.csv').relative_to(ROOT))
    print("wrote", (PR / 'ai_screening_predictor_metrics_20260625.json').relative_to(ROOT))


if __name__ == "__main__":
    main()
