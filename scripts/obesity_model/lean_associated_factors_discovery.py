"""Beyond propionate: discover additional factors associated with lean-enriched
strains, using data-derived ecological features plus external knowledge axes.

Feature families (all independent of the obesity model itself, i.e. non-circular):
  ECOLOGICAL (computed from the matched Western-Europe cohort)
    - prevalence            : fraction of samples where present (core vs rare)
    - mean_log_abundance    : typical abundance level
    - diversity_association : correlation with Shannon diversity computed WITHIN
                              each group and averaged, so it is not simply a
                              restatement of the lean/obese label
    - cooccurrence_degree   : number of species it co-occurs with (|rho|>0.3)
    - lean_marker_affinity  : mean correlation with CONFIRMED lean markers,
                              excluding itself (guilt-by-association)
  KNOWLEDGE (external taxonomy-based, non-circular)
    - oral_origin           : known oral-cavity taxon (translocation marker)
    - strict_anaerobe       : oxygen tolerance
    - spore_former          : formulation-relevant robustness
    - fiber_degrader        : polysaccharide-utilisation specialist
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import LeaveOneGroupOut
from sklearn.metrics import roc_auc_score
from sklearn.preprocessing import StandardScaler

ROOT = Path(__file__).resolve().parents[2]
PR = ROOT / "results/prediction_results"
OUT = PR / "lean_factors"
PSEUDO = 1e-3

ORAL = {"Streptococcus", "Actinomyces", "Veillonella", "Gemella", "Rothia", "Haemophilus",
        "Fusobacterium", "Porphyromonas", "Prevotella_melaninogenica", "Neisseria",
        "Granulicatella", "Atopobium", "Solobacterium", "Lactobacillus_salivarius"}
FACULTATIVE = {"Streptococcus", "Escherichia", "Klebsiella", "Enterococcus", "Lactobacillus",
               "Actinomyces", "Haemophilus", "Gemella", "Rothia", "Staphylococcus",
               "Enterobacter", "Citrobacter", "Neisseria", "Bacillus", "Turicibacter"}
SPORE = {"Clostridium", "Bacillus", "Romboutsia", "Turicibacter", "Anaerostipes",
         "Roseburia", "Eubacterium", "Butyrivibrio", "Coprococcus", "Blautia",
         "Faecalibacterium", "Intestinimonas", "Oscillibacter", "Lawsonibacter",
         "Ruminococcus", "Dorea", "Flavonifractor", "Fusicatenibacter"}
FIBER = {"Bacteroides", "Prevotella", "Ruminococcus", "Bifidobacterium", "Roseburia",
         "Eubacterium", "Butyrivibrio", "Faecalibacterium", "Alistipes", "Barnesiella",
         "Parabacteroides", "Odoribacter", "Coprococcus"}


def shannon(x):
    p = x[x > 0] / 100.0
    p = p / p.sum() if p.sum() > 0 else p
    return float(-(p * np.log(p)).sum()) if len(p) else 0.0


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    da = pd.read_csv(PR / "we_healthy/differential_abundance_adjusted.csv")
    matched = pd.read_csv(PR / "we_healthy/matched_cohort.csv")
    ab = pd.read_csv(ROOT / "data/taxonomic_profile/species_abundance_wide.csv").set_index("sample_id")
    X = ab.loc[matched.sample_id]
    X.index = matched.index
    grp = matched.obese.to_numpy()

    sig = da[da.fdr < 0.05].copy()
    sig["genus"] = sig.species.str.split("_").str[0]
    sig["y"] = (sig.direction == "lean_enriched").astype(int)
    species = [s for s in sig.species if s in X.columns]
    sig = sig[sig.species.isin(species)].reset_index(drop=True)

    Xs = X[species]
    logX = np.log10(Xs + PSEUDO)
    div = np.array([shannon(r) for r in X.to_numpy(float)])

    # ---------- ecological features ----------
    prevalence = (Xs > 0).mean()
    mean_log_ab = logX.mean()
    # diversity association WITHIN group, averaged (reduces circularity)
    dassoc = {}
    for s in species:
        rs = []
        for g in (0, 1):
            m = grp == g
            if (Xs.loc[m, s] > 0).sum() > 20:
                r, _ = stats.spearmanr(logX.loc[m, s], div[m])
                if np.isfinite(r):
                    rs.append(r)
        dassoc[s] = float(np.mean(rs)) if rs else np.nan
    # co-occurrence degree over ALL species with prevalence>=10%
    allsp = [c for c in ab.columns if (X[c] > 0).mean() >= 0.10]
    corr = np.log10(X[allsp] + PSEUDO).corr(method="spearman")
    degree = {s: int((corr[s].abs() > 0.30).sum() - 1) for s in species if s in corr.columns}
    # guilt-by-association with confirmed robust lean markers (leave-self-out)
    lean_markers = da[(da.robust == True) & (da.direction == "lean_enriched")].species.tolist()
    lean_markers = [s for s in lean_markers if s in corr.columns]
    affinity = {}
    for s in species:
        if s not in corr.columns:
            affinity[s] = np.nan; continue
        others = [m for m in lean_markers if m != s]
        affinity[s] = float(corr.loc[s, others].mean()) if others else np.nan

    sig["prevalence"] = sig.species.map(prevalence)
    sig["mean_log_abundance"] = sig.species.map(mean_log_ab)
    sig["diversity_association"] = sig.species.map(dassoc)
    sig["cooccurrence_degree"] = sig.species.map(degree)
    sig["lean_marker_affinity"] = sig.species.map(affinity)
    # ---------- knowledge features ----------
    sig["oral_origin"] = sig.genus.isin(ORAL).astype(int)
    sig["strict_anaerobe"] = (~sig.genus.isin(FACULTATIVE)).astype(int)
    sig["spore_former"] = sig.genus.isin(SPORE).astype(int)
    sig["fiber_degrader"] = sig.genus.isin(FIBER).astype(int)

    FEATS = ["prevalence", "mean_log_abundance", "diversity_association",
             "cooccurrence_degree", "lean_marker_affinity",
             "oral_origin", "strict_anaerobe", "spore_former", "fiber_degrader"]
    d = sig.dropna(subset=FEATS).copy()
    y = d.y.to_numpy(); g = d.genus.to_numpy()
    print(f"=== 新特征筛选：n={len(d)} 显著物种（瘦人富集 {y.sum()}, 肥胖富集 {(1-y).sum()}）===\n")

    rows = []
    for f in FEATS:
        v = d[f].to_numpy(float)
        if len(np.unique(v)) < 2:
            continue
        a = roc_auc_score(y, v)
        lean_v, ob_v = v[y == 1], v[y == 0]
        try:
            _, p = stats.mannwhitneyu(lean_v, ob_v, alternative="two-sided")
        except ValueError:
            p = np.nan
        rows.append({"feature": f, "auc": round(float(max(a, 1 - a)), 3),
                     "direction": "越高越瘦" if a > 0.5 else "越高越胖",
                     "lean_mean": round(float(lean_v.mean()), 3),
                     "obese_mean": round(float(ob_v.mean()), 3),
                     "p_mannwhitney": float(p)})
    R = pd.DataFrame(rows)
    R["fdr"] = np.minimum(1, R.p_mannwhitney * len(R))
    R = R.sort_values("auc", ascending=False)
    print("单特征判别力：")
    for r in R.itertuples():
        star = "***" if r.fdr < 0.01 else ("**" if r.fdr < 0.05 else ("*" if r.p_mannwhitney < 0.05 else ""))
        print(f"  {r.feature:24} AUC={r.auc:.3f}  {r.direction}  瘦={r.lean_mean:>8.3f} 胖={r.obese_mean:>8.3f}  P={r.p_mannwhitney:.4f} {star}")

    # multivariate + leave-one-genus-out
    Xm = d[FEATS].to_numpy(float)
    oof = np.full(len(y), np.nan)
    for tr, te in LeaveOneGroupOut().split(Xm, y, g):
        if len(np.unique(y[tr])) < 2:
            continue
        sc = StandardScaler().fit(Xm[tr])
        oof[te] = LogisticRegression(C=0.5, max_iter=3000).fit(sc.transform(Xm[tr]), y[tr]).predict_proba(sc.transform(Xm[te]))[:, 1]
    ok = np.isfinite(oof)
    auc_cv = float(roc_auc_score(y[ok], oof[ok]))
    sc = StandardScaler().fit(Xm)
    lr = LogisticRegression(C=0.5, max_iter=3000).fit(sc.transform(Xm), y)
    coef = pd.DataFrame({"feature": FEATS, "coef_std": lr.coef_[0].round(3)}).sort_values("coef_std", ascending=False)
    print(f"\n多变量（留一属 CV）AUC = {auc_cv:.3f}  （基线 0.5，瘦人占比 {y.mean():.2f}）")
    print("标准化系数（正=预示瘦人富集）：")
    for r in coef.itertuples():
        print(f"  {r.feature:24} {r.coef_std:+.3f}")

    R.to_csv(OUT / "lean_factor_discriminative_power.csv", index=False, encoding="utf-8-sig")
    coef.to_csv(OUT / "lean_factor_coefficients.csv", index=False, encoding="utf-8-sig")
    d[["species", "genus", "direction", "y"] + FEATS].to_csv(OUT / "lean_factor_matrix.csv", index=False, encoding="utf-8-sig")
    (OUT / "summary.json").write_text(json.dumps({
        "n_species": int(len(d)), "n_lean": int(y.sum()), "n_obese": int((1 - y).sum()),
        "loso_genus_auc": round(auc_cv, 3),
        "single_features": R.to_dict("records"),
        "coefficients": coef.to_dict("records")}, indent=2, ensure_ascii=False), encoding="utf-8")
    print("\nwrote", OUT.relative_to(ROOT))


if __name__ == "__main__":
    main()
