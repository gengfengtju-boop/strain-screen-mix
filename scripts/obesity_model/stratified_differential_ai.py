"""Region- and disease-stratified lean-vs-obese differential strain tables,
with an AI (random-forest) multivariate importance layer per stratum.

Per stratum we combine:
  - statistical differential abundance (within-study median Δ + Cohen's d), and
  - an AI classifier (balanced random forest, lean vs obese) whose study-grouped
    CV AUC reports honest separability and whose Gini importance ranks the
    multivariate-relevant strains (accounts for correlations the univariate test
    misses).

Strata:
  - region (countries grouped): Western Europe / North America / East Asia /
    Middle East ... lean(no-IR) vs obese(any).
  - disease: healthy / T2D ... lean vs obese WITHIN that disease.
Honest: single-study strata are batch-confounded (flagged); abundance is
relative (%); only species with >=10% prevalence in the stratum are tested.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import GroupKFold, StratifiedKFold, cross_val_predict
from sklearn.metrics import roc_auc_score

ROOT = Path(__file__).resolve().parents[2]
PR = ROOT / "results/prediction_results"
OUT = PR / "stratified_differential"
EPS = 1e-3
MIN_PER_GROUP = 15
MIN_PREV = 0.10

REGION = {"NLD": "西欧", "GBR": "西欧", "DNK": "西欧", "FRA": "西欧", "DEU": "西欧",
          "ITA": "西欧", "ESP": "西欧", "SWE": "西欧", "AUT": "西欧", "IRL": "西欧", "LUX": "西欧",
          "CHN": "东亚", "JPN": "东亚", "KOR": "东亚",
          "USA": "北美", "CAN": "北美", "ISR": "中东", "IND": "南亚", "KAZ": "中亚"}


def differential(sub, species):
    """within-study median Δ (pp), log2FC, pooled Cohen's d, direction consistency."""
    studies = sub["study_id"].unique()
    deltas, l2s, ds = [], [], []
    for st in studies:
        s = sub[sub["study_id"] == st]
        L = s[s["grp"] == 1][species]; O = s[s["grp"] == 0][species]
        if len(L) < 5 or len(O) < 5:
            continue
        mL, mO = L.mean(), O.mean()
        sL, sO = L.std(ddof=1), O.std(ddof=1)
        psd = np.sqrt(((len(L)-1)*sL**2 + (len(O)-1)*sO**2) / (len(L)+len(O)-2)).replace(0, np.nan)
        deltas.append(mL - mO); l2s.append(np.log2((mL+EPS)/(mO+EPS))); ds.append((mL-mO)/psd)
    if not deltas:   # single-group-per-study; fall back to pooled
        L = sub[sub["grp"] == 1][species]; O = sub[sub["grp"] == 0][species]
        deltas = [L.mean() - O.mean()]; l2s = [np.log2((L.mean()+EPS)/(O.mean()+EPS))]
        psd = np.sqrt((L.var()+O.var())/2).replace(0, np.nan); ds = [(L.mean()-O.mean())/psd]
    dd = pd.concat(deltas, axis=1);
    med = dd.median(axis=1)
    nstud = dd.shape[1]
    nlean = (dd > 0).sum(axis=1)
    out = pd.DataFrame({"median_delta_pp": med.round(4),
                        "median_log2fc": pd.concat(l2s, axis=1).median(axis=1).round(3),
                        "cohens_d": pd.concat(ds, axis=1).median(axis=1).round(3),
                        "n_studies": nstud,
                        "consistency": (np.maximum(nlean, nstud-nlean)/nstud).round(2)})
    return out


def ai_importance(sub, species):
    X = sub[species].to_numpy(float); y = sub["grp"].to_numpy()
    groups = sub["study_id"].to_numpy()
    ng = len(np.unique(groups))
    rf = RandomForestClassifier(n_estimators=400, class_weight="balanced",
                                max_depth=6, min_samples_leaf=3, random_state=0, n_jobs=-1)
    try:
        if ng >= 3:
            cv = GroupKFold(n_splits=min(5, ng))
            proba = cross_val_predict(rf, X, y, cv=cv, groups=groups, method="predict_proba", n_jobs=-1)[:, 1]
            cvtype = f"group_{min(5,ng)}fold"
        else:
            cv = StratifiedKFold(5, shuffle=True, random_state=0)
            proba = cross_val_predict(rf, X, y, cv=cv, method="predict_proba", n_jobs=-1)[:, 1]
            cvtype = "stratified_5fold_single_study_confounded"
        auc = float(roc_auc_score(y, proba))
    except Exception:
        auc, cvtype = float("nan"), "cv_failed"
    rf.fit(X, y)
    imp = pd.Series(rf.feature_importances_, index=species)
    return auc, cvtype, imp


def run_stratum(name, kind, sub, abund_cols):
    species = [c for c in abund_cols if (sub[c] > 0).mean() >= MIN_PREV]
    nl, no = int((sub["grp"] == 1).sum()), int((sub["grp"] == 0).sum())
    stat = differential(sub, species)
    auc, cvtype, imp = ai_importance(sub, species)
    stat["ai_gini_importance"] = imp.reindex(stat.index).round(5)
    stat["ai_rank"] = stat["ai_gini_importance"].rank(ascending=False, method="first").astype("Int64")
    stat["direction"] = np.where(stat["median_delta_pp"] > 0, "lean_enriched", "obese_enriched")
    stat["stratum"] = name; stat["stratum_kind"] = kind
    stat = stat.reset_index().rename(columns={"index": "species"})
    stat = stat.sort_values("ai_gini_importance", ascending=False)
    OUT.mkdir(parents=True, exist_ok=True)
    stat.to_csv(OUT / f"{kind}_{name}_differential_20260625.csv", index=False, encoding="utf-8-sig")
    meta = {"stratum": name, "kind": kind, "lean": nl, "obese": no,
            "studies": int(sub["study_id"].nunique()), "n_species_tested": len(species),
            "ai_cv_auc": round(auc, 3) if auc == auc else None, "ai_cv": cvtype}
    return stat, meta


def main():
    m = pd.read_csv(ROOT / "data/metadata/sample_metadata_raw.csv")
    abund = pd.read_csv(ROOT / "data/taxonomic_profile/species_abundance_wide.csv").set_index("sample_id")
    cols = list(abund.columns)
    m = m.join(abund, on="sample_id").dropna(subset=[cols[0]])

    metas = []; tops = []
    # region strata: lean(no-IR) vs obese(any)
    m["region2"] = m["country"].map(REGION).fillna("其他")
    for reg in ["西欧", "北美", "东亚", "中东"]:
        sub = m[m["region2"] == reg].copy()
        sub["grp"] = np.where((sub["obesity_status"] == "lean") & (sub["disease_status"] == "healthy"), 1,
                              np.where(sub["obesity_status"] == "obesity", 0, -1))
        sub = sub[sub["grp"] >= 0]
        if (sub["grp"] == 1).sum() < MIN_PER_GROUP or (sub["grp"] == 0).sum() < MIN_PER_GROUP:
            continue
        st, meta = run_stratum(reg, "region", sub, cols); metas.append(meta)
        tops.append(st.head(12))
    # disease strata: lean vs obese WITHIN disease
    for dis in ["healthy", "T2D"]:
        sub = m[m["disease_status"] == dis].copy()
        sub["grp"] = np.where(sub["obesity_status"] == "lean", 1,
                              np.where(sub["obesity_status"] == "obesity", 0, -1))
        sub = sub[sub["grp"] >= 0]
        if (sub["grp"] == 1).sum() < MIN_PER_GROUP or (sub["grp"] == 0).sum() < MIN_PER_GROUP:
            continue
        st, meta = run_stratum(dis, "disease", sub, cols); metas.append(meta)
        tops.append(st.head(12))

    combined = pd.concat(tops, ignore_index=True)
    combined.to_csv(PR / "stratified_differential_top_strains_20260625.csv", index=False, encoding="utf-8-sig")
    (PR / "stratified_differential_summary_20260625.json").write_text(
        json.dumps({"strata": metas}, indent=2, ensure_ascii=False), encoding="utf-8")
    print("=== stratum AI separability (lean vs obese) ===")
    for d in metas:
        print(f"  {d['kind']:7} {d['stratum']:5} lean={d['lean']:4} obese={d['obese']:4} "
              f"studies={d['studies']:2} | AI CV-AUC={d['ai_cv_auc']} ({d['ai_cv']})")
    print("\nwrote", (PR / 'stratified_differential_top_strains_20260625.csv').relative_to(ROOT))


if __name__ == "__main__":
    main()
