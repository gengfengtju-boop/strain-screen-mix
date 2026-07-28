"""Deep analysis of the Western-Europe stratum (strongest AI separability).

Audits whether the AI CV-AUC 0.745 is real obesity biology or an artifact:
  A. CONFOUND: the obese group contains T2D patients while lean is healthy-only.
     Re-run restricted to healthy-only obese.
  B. HONEST CV: leave-one-STUDY-out (harder than grouped 5-fold).
  C. CROSS-COUNTRY generalization: train on some countries, test on unseen ones.
  D. STABLE MARKERS: species consistent across WE countries (not study-specific).
  E. SEX/AGE: check demographic imbalance between groups.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import LeaveOneGroupOut, GroupKFold, cross_val_predict
from sklearn.metrics import roc_auc_score

ROOT = Path(__file__).resolve().parents[2]
PR = ROOT / "results/prediction_results"
WE = {"NLD", "GBR", "DNK", "FRA", "DEU", "ITA", "ESP", "SWE", "AUT", "IRL", "LUX"}
MIN_PREV = 0.10
EPS = 1e-3


def rf():
    return RandomForestClassifier(n_estimators=500, class_weight="balanced", max_depth=6,
                                  min_samples_leaf=3, random_state=0, n_jobs=-1)


def grouped_auc(X, y, groups, loso=False):
    ng = len(np.unique(groups))
    if ng < 2 or len(np.unique(y)) < 2:
        return float("nan")
    cv = LeaveOneGroupOut() if loso else GroupKFold(n_splits=min(5, ng))
    # LOSO folds can be single-class in test; collect out-of-fold probabilities
    oof = np.full(len(y), np.nan)
    for tr, te in cv.split(X, y, groups):
        if len(np.unique(y[tr])) < 2:
            continue
        m = rf().fit(X[tr], y[tr])
        oof[te] = m.predict_proba(X[te])[:, 1]
    ok = np.isfinite(oof)
    if len(np.unique(y[ok])) < 2:
        return float("nan")
    return float(roc_auc_score(y[ok], oof[ok]))


def diff_table(sub, species):
    """within-study median delta / d / consistency."""
    rows = []
    per_study = []
    for st, s in sub.groupby("study_id"):
        L, O = s[s.grp == 1][species], s[s.grp == 0][species]
        if len(L) < 5 or len(O) < 5:
            continue
        psd = np.sqrt(((len(L)-1)*L.std(ddof=1)**2 + (len(O)-1)*O.std(ddof=1)**2) / (len(L)+len(O)-2)).replace(0, np.nan)
        per_study.append(pd.DataFrame({"delta": L.mean()-O.mean(), "d": (L.mean()-O.mean())/psd}))
    if not per_study:
        return pd.DataFrame()
    D = pd.concat([p["delta"] for p in per_study], axis=1)
    DD = pd.concat([p["d"] for p in per_study], axis=1)
    n = D.shape[1]
    nl = (D > 0).sum(axis=1)
    return pd.DataFrame({"median_delta_pp": D.median(axis=1).round(4),
                         "cohens_d": DD.median(axis=1).round(3),
                         "n_studies": n,
                         "consistency": (np.maximum(nl, n-nl)/n).round(2)})


def main():
    m = pd.read_csv(ROOT / "data/metadata/sample_metadata_raw.csv")
    ab = pd.read_csv(ROOT / "data/taxonomic_profile/species_abundance_wide.csv").set_index("sample_id")
    cols = list(ab.columns)
    m = m[m.country.isin(WE)].join(ab, on="sample_id").dropna(subset=[cols[0]])
    m["grp"] = np.where((m.obesity_status == "lean") & (m.disease_status == "healthy"), 1,
                        np.where(m.obesity_status == "obesity", 0, -1))
    base = m[m.grp >= 0].copy()

    report = {}

    # ---------- A. confound: T2D inside the obese group ----------
    full = base
    healthy_only = base[base.disease_status == "healthy"].copy()
    variants = {}
    for name, sub in [("all_obese_incl_T2D", full), ("healthy_only_obese", healthy_only)]:
        sp = [c for c in cols if (sub[c] > 0).mean() >= MIN_PREV]
        X, y, g = sub[sp].to_numpy(float), sub.grp.to_numpy(), sub.study_id.to_numpy()
        auc5 = grouped_auc(X, y, g)
        auc_loso = grouped_auc(X, y, g, loso=True)
        variants[name] = {"lean": int((y == 1).sum()), "obese": int((y == 0).sum()),
                          "studies": int(len(np.unique(g))), "n_species": len(sp),
                          "grouped5fold_auc": round(auc5, 3), "leave_one_study_out_auc": round(auc_loso, 3)}
        print(f"[A/B] {name}: lean={variants[name]['lean']} obese={variants[name]['obese']} "
              f"studies={variants[name]['studies']} | 5foldAUC={auc5:.3f} LOSO-AUC={auc_loso:.3f}")
    report["confound_and_honest_cv"] = variants

    # T2D-vs-healthy discrimination inside obese (is disease the real signal?)
    ob = base[base.grp == 0].copy()
    ob["is_t2d"] = (ob.disease_status == "T2D").astype(int)
    if ob.is_t2d.nunique() > 1:
        sp = [c for c in cols if (ob[c] > 0).mean() >= MIN_PREV]
        auc_t2d = grouped_auc(ob[sp].to_numpy(float), ob.is_t2d.to_numpy(), ob.study_id.to_numpy())
        report["t2d_vs_healthy_within_obese_auc"] = round(auc_t2d, 3)
        print(f"[A] T2D vs healthy WITHIN obese: grouped AUC={auc_t2d:.3f}")

    # ---------- C. cross-country generalization (healthy-only, honest) ----------
    hc = healthy_only
    cc = {}
    for test_c in ["NLD", "GBR", "DNK", "FRA", "DEU"]:
        tr = hc[hc.country != test_c]; te = hc[hc.country == test_c]
        if (te.grp == 1).sum() < 10 or (te.grp == 0).sum() < 10:
            continue
        sp = [c for c in cols if (tr[c] > 0).mean() >= MIN_PREV]
        mdl = rf().fit(tr[sp].to_numpy(float), tr.grp.to_numpy())
        p = mdl.predict_proba(te[sp].to_numpy(float))[:, 1]
        cc[test_c] = {"auc": round(float(roc_auc_score(te.grp.to_numpy(), p)), 3),
                      "lean": int((te.grp == 1).sum()), "obese": int((te.grp == 0).sum())}
        print(f"[C] train-others -> test {test_c}: AUC={cc[test_c]['auc']} (lean {cc[test_c]['lean']}/obese {cc[test_c]['obese']})")
    report["cross_country_holdout"] = cc

    # ---------- D. stable markers across WE countries (healthy-only) ----------
    sp_all = [c for c in cols if (hc[c] > 0).mean() >= MIN_PREV]
    per_country = {}
    for c_, s in hc.groupby("country"):
        if (s.grp == 1).sum() < 15 or (s.grp == 0).sum() < 15:
            continue
        t = diff_table(s, sp_all)
        if len(t):
            per_country[c_] = t["cohens_d"]
    if per_country:
        Dm = pd.DataFrame(per_country)
        stab = pd.DataFrame({"mean_d": Dm.mean(axis=1).round(3),
                             "n_countries": Dm.notna().sum(axis=1),
                             "sign_agree": (np.sign(Dm).eq(np.sign(Dm.mean(axis=1)), axis=0) & Dm.notna()).sum(axis=1)})
        stab["agree_frac"] = (stab.sign_agree / stab.n_countries).round(2)
        stab = stab[stab.n_countries >= 2].sort_values("mean_d", ascending=False)
        stab = stab.join(Dm.round(2))
        stab.to_csv(PR / "western_europe_stable_markers_20260625.csv", encoding="utf-8-sig")
        top_lean = stab[(stab.agree_frac >= 0.75)].head(10)
        top_ob = stab[(stab.agree_frac >= 0.75)].tail(10)
        print("\n[D] stable lean-enriched (WE, agree>=75%):")
        for i, r in top_lean.iterrows():
            print(f"    {i[:34]:34} mean_d={r.mean_d:+.2f} ({int(r.n_countries)} countries, agree {r.agree_frac:.0%})")
        print("[D] stable obese-enriched:")
        for i, r in top_ob.iloc[::-1].iterrows():
            print(f"    {i[:34]:34} mean_d={r.mean_d:+.2f} ({int(r.n_countries)} countries, agree {r.agree_frac:.0%})")
        report["stable_markers_file"] = "results/prediction_results/western_europe_stable_markers_20260625.csv"
        report["n_stable_markers_agree75"] = int((stab.agree_frac >= 0.75).sum())

    # ---------- E. demographics ----------
    demo = {}
    for name, sub in [("all", full), ("healthy_only", healthy_only)]:
        d = {}
        for gval, lab in [(1, "lean"), (0, "obese")]:
            s = sub[sub.grp == gval]
            d[lab] = {"n": int(len(s)), "age_mean": round(float(s.age.mean()), 1),
                      "female_frac": round(float((s.sex == "female").mean()), 2),
                      "bmi_mean": round(float(s.BMI.mean()), 1)}
        demo[name] = d
    report["demographics"] = demo
    print("\n[E] demographics(healthy-only):", json.dumps(demo["healthy_only"], ensure_ascii=False))

    (PR / "western_europe_deep_analysis_20260625.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print("\nwrote", (PR / "western_europe_deep_analysis_20260625.json").relative_to(ROOT))


if __name__ == "__main__":
    main()
