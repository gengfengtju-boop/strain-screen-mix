"""Western-Europe healthy cohort: complete standalone analysis (T2D excluded).

Design
------
Population   : Western-European adults, DISEASE-FREE (T2D / IGT / hypertension all
               excluded), lean (BMI<25 by curated obesity_status) vs obese.
Confounding  : age and sex are handled twice, independently —
               (1) within-study 1:1 matching (also removes batch), and
               (2) covariate adjustment in the regression model.
Differential : per-species OLS on log10 relative abundance with obesity + age +
               sex + study fixed effects; Benjamini-Hochberg FDR.
Robustness   : per-study effect sizes + DerSimonian-Laird random-effects meta
               analysis (I2, 95% CI) — a species must agree in both.
AI           : random forest, leave-one-study-out, on the matched cohort.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.api as sm
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import LeaveOneGroupOut
from sklearn.metrics import roc_auc_score

ROOT = Path(__file__).resolve().parents[2]
PR = ROOT / "results/prediction_results"
OUT = PR / "we_healthy"
WE = {"NLD", "GBR", "DNK", "FRA", "DEU", "ITA", "ESP", "SWE", "AUT", "IRL", "LUX"}
MIN_PER_GROUP = 10      # per-study eligibility
MIN_PREV = 0.10         # species prevalence within cohort
PSEUDO = 1e-3           # % pseudocount
AGE_TOL = 5             # matching tolerance (years)


# ---------------------------------------------------------------- cohort
def build_cohort():
    m = pd.read_csv(ROOT / "data/metadata/sample_metadata_raw.csv")
    n0 = len(m)
    steps = [("原始样本", n0)]
    m = m[m.country.isin(WE)];              steps.append(("西欧国家", len(m)))
    m = m[m.disease_status == "healthy"];   steps.append(("无疾病(排除T2D/IGT/高血压)", len(m)))
    m = m[m.obesity_status.isin(["lean", "obesity"])]; steps.append(("瘦或肥胖(排除超重)", len(m)))
    m = m[m.age.notna() & m.sex.isin(["male", "female"])]; steps.append(("年龄性别完整", len(m)))
    # per-study eligibility
    cnt = m.groupby(["study_id", "obesity_status"]).size().unstack(fill_value=0)
    ok = cnt[(cnt.get("lean", 0) >= MIN_PER_GROUP) & (cnt.get("obesity", 0) >= MIN_PER_GROUP)].index
    m = m[m.study_id.isin(ok)];             steps.append((f"研究内两组各≥{MIN_PER_GROUP}", len(m)))
    m = m.copy()
    m["obese"] = (m.obesity_status == "obesity").astype(int)
    m["female"] = (m.sex == "female").astype(int)
    return m, steps


def cohort_table(m):
    rows = []
    for (sid, ctry), s in m.groupby(["study_id", "country"]):
        L, O = s[s.obese == 0], s[s.obese == 1]
        if len(L) < MIN_PER_GROUP or len(O) < MIN_PER_GROUP:
            continue
        rows.append({"study_id": sid, "country": ctry, "n_lean": len(L), "n_obese": len(O),
                     "age_lean": round(L.age.mean(), 1), "age_obese": round(O.age.mean(), 1),
                     "female_lean": round(L.female.mean(), 2), "female_obese": round(O.female.mean(), 2),
                     "bmi_lean": round(L.BMI.mean(), 1), "bmi_obese": round(O.BMI.mean(), 1),
                     "seq": s.sequencing_type.mode()[0] if s.sequencing_type.notna().any() else ""})
    return pd.DataFrame(rows).sort_values("n_obese", ascending=False)


# ---------------------------------------------------------------- matching
def match_within_study(m, tol=AGE_TOL, seed=0):
    rng = np.random.default_rng(seed)
    keep = []
    for sid, s in m.groupby("study_id"):
        pool = s[s.obese == 0].copy()
        for _, r in s[s.obese == 1].iterrows():
            cand = pool[(pool.female == r.female) & ((pool.age - r.age).abs() <= tol)]
            if len(cand) == 0:
                continue
            pick = cand.index[np.argmin((cand.age - r.age).abs().to_numpy())]
            keep += [r.name, pick]
            pool = pool.drop(pick)
    return m.loc[sorted(set(keep))]


# ---------------------------------------------------------------- differential
def adjusted_da(df, species):
    """OLS: log10(abund+eps) ~ obese + age + female + C(study); BH-FDR on obese term."""
    D = pd.get_dummies(df["study_id"], prefix="st", drop_first=True).astype(float)
    base = pd.concat([df[["obese", "age", "female"]].astype(float).reset_index(drop=True),
                      D.reset_index(drop=True)], axis=1)
    X = sm.add_constant(base, has_constant="add")
    res = []
    for sp in species:
        y = np.log10(df[sp].to_numpy(float) + PSEUDO)
        try:
            fit = sm.OLS(y, X).fit()
            res.append({"species": sp, "coef_obese_log10": fit.params["obese"],
                        "se": fit.bse["obese"], "p": fit.pvalues["obese"],
                        "coef_age": fit.params["age"], "coef_female": fit.params["female"]})
        except Exception:
            continue
    r = pd.DataFrame(res)
    r["fdr"] = _bh(r["p"].to_numpy())
    r["direction"] = np.where(r.coef_obese_log10 < 0, "lean_enriched", "obese_enriched")
    r["fold_change_obese_vs_lean"] = (10 ** r.coef_obese_log10).round(3)
    return r.sort_values("p")


def _bh(p):
    p = np.asarray(p, float); n = len(p); o = np.argsort(p)
    q = np.empty(n); q[o] = np.minimum.accumulate((p[o] * n / (np.arange(n) + 1))[::-1])[::-1]
    return np.clip(q, 0, 1)


def meta_analysis(df, species):
    """per-study Hedges g + DerSimonian-Laird random effects."""
    out = []
    for sp in species:
        gs, vs, ns = [], [], 0
        for sid, s in df.groupby("study_id"):
            L = np.log10(s[s.obese == 0][sp].to_numpy(float) + PSEUDO)
            O = np.log10(s[s.obese == 1][sp].to_numpy(float) + PSEUDO)
            if len(L) < 5 or len(O) < 5:
                continue
            n1, n2 = len(L), len(O)
            sp_ = np.sqrt(((n1-1)*L.var(ddof=1) + (n2-1)*O.var(ddof=1)) / (n1+n2-2))
            if sp_ == 0 or not np.isfinite(sp_):
                continue
            d = (L.mean() - O.mean()) / sp_                      # + = lean higher
            J = 1 - 3/(4*(n1+n2) - 9)
            g = J * d
            v = (n1+n2)/(n1*n2) + g**2/(2*(n1+n2))
            gs.append(g); vs.append(v); ns += 1
        if ns < 3:
            continue
        g = np.array(gs); v = np.array(vs); w = 1/v
        mu_f = (w*g).sum()/w.sum()
        Q = (w*(g-mu_f)**2).sum()
        C = w.sum() - (w**2).sum()/w.sum()
        tau2 = max(0.0, (Q - (ns-1))/C) if C > 0 else 0.0
        wr = 1/(v+tau2); mu = (wr*g).sum()/wr.sum(); se = np.sqrt(1/wr.sum())
        I2 = max(0.0, (Q-(ns-1))/Q*100) if Q > 0 else 0.0
        out.append({"species": sp, "meta_g": round(float(mu), 3),
                    "ci_low": round(float(mu-1.96*se), 3), "ci_high": round(float(mu+1.96*se), 3),
                    "I2_percent": round(float(I2), 1), "k_studies": ns,
                    "ci_excludes_zero": bool((mu-1.96*se)*(mu+1.96*se) > 0)})
    return pd.DataFrame(out)


# ---------------------------------------------------------------- AI
def loso_auc(df, species, seed=0):
    X = df[species].to_numpy(float); y = df.obese.to_numpy(); g = df.study_id.to_numpy()
    oof = np.full(len(y), np.nan)
    for tr, te in LeaveOneGroupOut().split(X, y, g):
        if len(np.unique(y[tr])) < 2:
            continue
        mdl = RandomForestClassifier(n_estimators=500, class_weight="balanced", max_depth=6,
                                     min_samples_leaf=3, random_state=seed, n_jobs=-1).fit(X[tr], y[tr])
        oof[te] = mdl.predict_proba(X[te])[:, 1]
    ok = np.isfinite(oof)
    per = {}
    for sid in np.unique(g):
        msk = ok & (g == sid)
        if msk.sum() > 10 and len(np.unique(y[msk])) > 1:
            per[str(sid)] = round(float(roc_auc_score(y[msk], oof[msk])), 3)
    return float(roc_auc_score(y[ok], oof[ok])), per


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    m, steps = build_cohort()
    ab = pd.read_csv(ROOT / "data/taxonomic_profile/species_abundance_wide.csv").set_index("sample_id")
    cols = list(ab.columns)
    m = m.join(ab, on="sample_id").dropna(subset=[cols[0]])

    ct = cohort_table(m)
    ct.to_csv(OUT / "cohort_sources.csv", index=False, encoding="utf-8-sig")
    print("=== 队列筛选流程 ===")
    for k, v in steps:
        print(f"  {k}: {v}")
    print(f"\n=== 合格队列: {len(ct)} 项研究 / {ct.n_lean.sum()} 瘦 / {ct.n_obese.sum()} 肥胖 ===")
    print(ct.to_string(index=False))

    matched = match_within_study(m)
    print(f"\n=== 研究内 1:1 年龄(±{AGE_TOL}岁)/性别匹配后: n={len(matched)} "
          f"(瘦 {int((matched.obese==0).sum())} / 肥胖 {int((matched.obese==1).sum())}) ===")
    print(f"  年龄 瘦 {matched[matched.obese==0].age.mean():.1f} vs 肥胖 {matched[matched.obese==1].age.mean():.1f}"
          f" | 女性 {matched[matched.obese==0].female.mean():.2f} vs {matched[matched.obese==1].female.mean():.2f}")
    matched[["sample_id", "study_id", "country", "obese", "age", "female", "BMI"]].to_csv(
        OUT / "matched_cohort.csv", index=False, encoding="utf-8-sig")

    species = [c for c in cols if (matched[c] > 0).mean() >= MIN_PREV]
    print(f"  流行率≥{MIN_PREV:.0%} 物种数: {len(species)}")

    da = adjusted_da(matched, species)
    meta = meta_analysis(matched, species)
    merged = da.merge(meta, on="species", how="left")
    merged["robust"] = (merged.fdr < 0.05) & (merged.ci_excludes_zero.fillna(False)) & \
                       (np.sign(-merged.coef_obese_log10) == np.sign(merged.meta_g))
    merged.to_csv(OUT / "differential_abundance_adjusted.csv", index=False, encoding="utf-8-sig")

    sig = merged[merged.fdr < 0.05]
    rob = merged[merged.robust]
    print(f"\n=== 差异分析（校正年龄/性别/研究）===")
    print(f"  FDR<0.05: {len(sig)} 个物种 | 同时 meta 95%CI 排除 0 且方向一致（稳健）: {len(rob)}")
    print("\n  稳健瘦人富集 Top10:")
    for r in rob[rob.direction == "lean_enriched"].sort_values("meta_g", ascending=False).head(10).itertuples():
        print(f"    {r.species[:36]:36} g={r.meta_g:+.2f}[{r.ci_low:+.2f},{r.ci_high:+.2f}] "
              f"FC={r.fold_change_obese_vs_lean:.2f} FDR={r.fdr:.1e} I2={r.I2_percent:.0f}%")
    print("\n  稳健胖人富集 Top10:")
    for r in rob[rob.direction == "obese_enriched"].sort_values("meta_g").head(10).itertuples():
        print(f"    {r.species[:36]:36} g={r.meta_g:+.2f}[{r.ci_low:+.2f},{r.ci_high:+.2f}] "
              f"FC={r.fold_change_obese_vs_lean:.2f} FDR={r.fdr:.1e} I2={r.I2_percent:.0f}%")

    auc, per = loso_auc(matched, species)
    auc_demo, _ = None, None
    Xd = matched[["age", "female"]].to_numpy(float)
    oof = np.full(len(matched), np.nan); y = matched.obese.to_numpy(); g = matched.study_id.to_numpy()
    for tr, te in LeaveOneGroupOut().split(Xd, y, g):
        if len(np.unique(y[tr])) < 2: continue
        mdl = RandomForestClassifier(n_estimators=300, class_weight="balanced", max_depth=4,
                                     min_samples_leaf=5, random_state=0, n_jobs=-1).fit(Xd[tr], y[tr])
        oof[te] = mdl.predict_proba(Xd[te])[:, 1]
    ok = np.isfinite(oof); auc_demo = float(roc_auc_score(y[ok], oof[ok]))
    print(f"\n=== AI 验证（匹配队列，留一研究）===")
    print(f"  菌群 LOSO-AUC = {auc:.3f} | 仅年龄性别 = {auc_demo:.3f}")
    print("  各研究:", per)

    rep = {"cohort_filter_steps": [{"step": k, "n": v} for k, v in steps],
           "eligible_studies": int(len(ct)), "countries": sorted(ct.country.unique().tolist()),
           "n_lean_total": int(ct.n_lean.sum()), "n_obese_total": int(ct.n_obese.sum()),
           "matched": {"n": int(len(matched)), "lean": int((matched.obese == 0).sum()),
                       "obese": int((matched.obese == 1).sum()),
                       "age_lean": round(float(matched[matched.obese == 0].age.mean()), 1),
                       "age_obese": round(float(matched[matched.obese == 1].age.mean()), 1),
                       "female_lean": round(float(matched[matched.obese == 0].female.mean()), 2),
                       "female_obese": round(float(matched[matched.obese == 1].female.mean()), 2)},
           "n_species_tested": len(species),
           "n_fdr_significant": int(len(sig)), "n_robust": int(len(rob)),
           "ai_matched_loso_auc": round(auc, 3), "ai_demographics_only_auc": round(auc_demo, 3),
           "ai_per_study_auc": per}
    (OUT / "analysis_summary.json").write_text(json.dumps(rep, indent=2, ensure_ascii=False), encoding="utf-8")
    print("\nwrote", OUT.relative_to(ROOT))


if __name__ == "__main__":
    main()
