"""Validate the bottom-up strain-property program against the rigorously screened
Western-Europe result, then search for features that predict fat-loss potential.

Bottom-up program : scripts/strain_annotation/build_strain_screening_catalog.py
  -> infers a fat-loss ("protective") vs obesity-promoting label per species from
     obesity-classifier SHAP direction + genome functional potential (BSH /
     butyrate / mucin) + safety tier. Trained on ALL 8304 samples, 45 studies,
     WITHOUT age/sex adjustment and WITHOUT excluding T2D.

Gold standard    : results/prediction_results/we_healthy/ -- Western-Europe,
     disease-free, within-study age/sex matched, FDR + random-effects meta.

Part 1: concordance (does bottom-up match the corrected screen?)
Part 2: which strain features actually predict lean-enrichment (leave-one-genus-out
        CV to prevent taxonomic leakage).
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import LeaveOneGroupOut
from sklearn.metrics import roc_auc_score
from sklearn.preprocessing import StandardScaler

ROOT = Path(__file__).resolve().parents[2]
PR = ROOT / "results/prediction_results"
OUT = PR / "bottomup_validation"


def load():
    shap = pd.read_csv(ROOT / "results/SHAP_results/obesity_classifier_shap_importance_20260613.csv")
    shap["bottomup_pred"] = np.where(shap.direction == "higher_abundance_lowers_obesity",
                                     "lean_enriched", "obese_enriched")
    cat = pd.read_csv(ROOT / "results/candidate_strain_scores/strain_screening_catalog_20260613.csv")
    da = pd.read_csv(PR / "we_healthy/differential_abundance_adjusted.csv")
    da["observed"] = da.direction
    guild = pd.read_csv(ROOT / "data/strain_genome/genus_functional_guild_reference_20260613.csv").set_index("genus")
    return shap, cat, da, guild


def part1_concordance(shap, cat, da):
    m = da.merge(shap[["species", "bottomup_pred", "mean_abs_shap", "abundance_shap_corr"]],
                 on="species", how="inner")
    m["match"] = m.observed == m.bottomup_pred
    res = {}
    for name, sub in [("全部受检物种", m),
                      ("FDR<0.05 显著", m[m.fdr < 0.05]),
                      ("稳健差异菌", m[m.robust == True])]:
        if len(sub) == 0:
            continue
        # 2x2
        tab = pd.crosstab(sub.bottomup_pred, sub.observed)
        acc = float(sub.match.mean())
        # chance-corrected (Cohen's kappa)
        po = acc
        pe = sum((sub.bottomup_pred == k).mean() * (sub.observed == k).mean()
                 for k in ["lean_enriched", "obese_enriched"])
        kappa = (po - pe) / (1 - pe) if pe < 1 else np.nan
        res[name] = {"n": int(len(sub)), "一致率": round(acc, 3), "kappa": round(float(kappa), 3),
                     "混淆矩阵": tab.to_dict()}
        print(f"\n--- {name} (n={len(sub)}) ---")
        print(f"  一致率 = {acc:.1%} | Cohen's kappa = {kappa:.3f}")
        print(tab.to_string())
    # where does it disagree most?
    bad = m[(m.robust == True) & (~m.match)]
    print(f"\n[不一致的稳健差异菌] n={len(bad)}")
    for r in bad.itertuples():
        print(f"    {r.species[:34]:34} 实测={r.observed:14} 自下而上={r.bottomup_pred:14} "
              f"FC={r.fold_change_obese_vs_lean:.2f} SHAP重要性={r.mean_abs_shap:.3f}")
    m.to_csv(OUT / "concordance_per_species.csv", index=False, encoding="utf-8-sig")
    return res, m


def part2_features(da, guild, shap):
    """Which strain properties predict lean-enrichment in the corrected gold standard?"""
    d = da[da.fdr < 0.05].copy()          # only species with a real signal
    d["genus"] = d.species.str.split("_").str[0]
    d["y"] = (d.observed == "lean_enriched").astype(int)
    # ---- feature block ----
    for col, g in [("butyrate", "butyrate_scfa_potential"), ("propionate", "propionate_potential"),
                   ("mucin", "mucin_interaction"), ("bsh", "bsh_potential"),
                   ("lactate", "lactate_acetate")]:
        d[col] = d.genus.map(lambda x: float(guild.loc[x, g]) if x in guild.index else np.nan)
    d = d.merge(shap[["species", "mean_abs_shap", "abundance_shap_corr"]], on="species", how="left")
    # taxonomy one-hot for the big families (genus-level proxy)
    d["is_bacteroides"] = (d.genus == "Bacteroides").astype(int)
    d["is_clostridia"] = d.genus.isin(["Roseburia", "Eubacterium", "Coprococcus", "Blautia",
                                       "Dorea", "Ruminococcus", "Butyrivibrio", "Oscillibacter",
                                       "Intestinimonas", "Firmicutes", "Anaerostipes"]).astype(int)
    d["is_uncultured_cag"] = d.species.str.contains("CAG|_sp_", regex=True).astype(int)
    d["abs_effect"] = d.coef_obese_log10.abs()
    d["heterogeneity"] = d.I2_percent.fillna(50)

    feats = ["butyrate", "propionate", "mucin", "bsh", "lactate",
             "abundance_shap_corr", "mean_abs_shap",
             "is_bacteroides", "is_clostridia", "is_uncultured_cag"]
    d = d.dropna(subset=feats + ["y"])
    X, y, g = d[feats].to_numpy(float), d.y.to_numpy(), d.genus.to_numpy()
    print(f"\n=== 特征发现：n={len(d)} 显著物种, {len(np.unique(g))} 属, 瘦人富集比例={y.mean():.2f} ===")

    # leave-one-genus-out CV (prevents taxonomic leakage)
    oof_lr = np.full(len(y), np.nan); oof_rf = np.full(len(y), np.nan)
    for tr, te in LeaveOneGroupOut().split(X, y, g):
        if len(np.unique(y[tr])) < 2:
            continue
        sc = StandardScaler().fit(X[tr])
        oof_lr[te] = LogisticRegression(C=1.0, max_iter=2000).fit(sc.transform(X[tr]), y[tr]).predict_proba(sc.transform(X[te]))[:, 1]
        oof_rf[te] = RandomForestClassifier(n_estimators=400, max_depth=4, min_samples_leaf=2,
                                            class_weight="balanced", random_state=0, n_jobs=-1).fit(X[tr], y[tr]).predict_proba(X[te])[:, 1]
    ok = np.isfinite(oof_lr)
    auc_lr = roc_auc_score(y[ok], oof_lr[ok]); auc_rf = roc_auc_score(y[np.isfinite(oof_rf)], oof_rf[np.isfinite(oof_rf)])
    print(f"  留一属 CV: 逻辑回归 AUC={auc_lr:.3f} | 随机森林 AUC={auc_rf:.3f} (基线 0.5)")

    # single-feature discriminative power (AUC of each feature alone)
    singles = []
    for f in feats:
        v = d[f].to_numpy(float)
        if len(np.unique(v)) < 2:
            continue
        a = roc_auc_score(y, v)
        singles.append({"feature": f, "auc_alone": round(float(max(a, 1 - a)), 3),
                        "direction": "越高越瘦" if a > 0.5 else "越高越胖",
                        "lean_mean": round(float(v[y == 1].mean()), 3),
                        "obese_mean": round(float(v[y == 0].mean()), 3)})
    S = pd.DataFrame(singles).sort_values("auc_alone", ascending=False)
    print("\n  单特征判别力 (AUC):")
    for r in S.itertuples():
        print(f"    {r.feature:22} AUC={r.auc_alone:.3f}  {r.direction}  瘦均值={r.lean_mean} 胖均值={r.obese_mean}")

    # full-data model coefficients (interpretation)
    sc = StandardScaler().fit(X)
    lr = LogisticRegression(C=1.0, max_iter=2000).fit(sc.transform(X), y)
    coefs = pd.DataFrame({"feature": feats, "coef_std": lr.coef_[0].round(3)}).sort_values("coef_std", ascending=False)
    print("\n  多变量标准化系数(正=预示瘦人富集):")
    for r in coefs.itertuples():
        print(f"    {r.feature:22} {r.coef_std:+.3f}")
    S.to_csv(OUT / "feature_discriminative_power.csv", index=False, encoding="utf-8-sig")
    coefs.to_csv(OUT / "feature_coefficients.csv", index=False, encoding="utf-8-sig")
    d[["species", "genus", "observed", "y"] + feats].to_csv(OUT / "feature_matrix.csv", index=False, encoding="utf-8-sig")
    return {"n_species": int(len(d)), "n_genera": int(len(np.unique(g))),
            "loso_genus_auc_logreg": round(float(auc_lr), 3),
            "loso_genus_auc_rf": round(float(auc_rf), 3),
            "single_feature_auc": S.to_dict("records"),
            "multivariate_coefficients": coefs.to_dict("records")}


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    shap, cat, da, guild = load()
    print("=" * 70)
    print("第一部分：自下而上程序 vs 严格筛选结果 —— 一致性检验")
    print("=" * 70)
    conc, merged = part1_concordance(shap, cat, da)
    print("\n" + "=" * 70)
    print("第二部分：哪些菌株特征能预测减脂潜力")
    print("=" * 70)
    feat = part2_features(da, guild, shap)
    (OUT / "validation_summary.json").write_text(
        json.dumps({"concordance": conc, "feature_discovery": feat}, indent=2, ensure_ascii=False),
        encoding="utf-8")
    print("\nwrote", OUT.relative_to(ROOT))


if __name__ == "__main__":
    main()
