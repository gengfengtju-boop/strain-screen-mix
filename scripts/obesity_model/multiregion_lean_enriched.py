"""Extrapolate the Western-Europe pipeline to other regional cohorts.

The pipeline is applied UNCHANGED per region:
  1. disease-free only (T2D / IGT / hypertension excluded)
  2. lean vs obese (overweight excluded), age+sex known
  3. per-study >=10 per group
  4. within-study 1:1 matching on sex and age (+-5 y), nearest neighbour, no replacement
  5. OLS: log10(abundance + 1e-3) ~ obese + age + sex (+ study when >1)
  6. Benjamini-Hochberg FDR
  7. per-study Hedges g + DerSimonian-Laird random effects (only when >=3 studies)
  8. robust = FDR<0.05 AND meta 95%CI excludes 0 AND same direction

Because the achievable rigour differs by region, each region is labelled with the
validation tier it actually supports; single-study regions cannot reach tier
"robust" and are reported at tier "adjusted" (FDR only). Regions with very few
obese subjects are marked exploratory.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.api as sm

ROOT = Path(__file__).resolve().parents[2]
PR = ROOT / "results/prediction_results"
OUT = PR / "multiregion"
PSEUDO = 1e-3
MIN_PER_GROUP = 10
MIN_PREV = 0.10
AGE_TOL = 5

REGION = {"NLD": "西欧", "GBR": "西欧", "DNK": "西欧", "FRA": "西欧", "DEU": "西欧", "ITA": "西欧",
          "ESP": "西欧", "SWE": "西欧", "AUT": "西欧", "IRL": "西欧", "LUX": "西欧",
          "CHN": "东亚", "JPN": "东亚", "KOR": "东亚", "MNG": "东亚",
          "USA": "北美", "CAN": "北美", "ISR": "中东", "IND": "南亚", "KAZ": "中亚",
          "PER": "南美", "CMR": "非洲", "MDG": "非洲", "RUS": "东欧"}


def bh(p):
    p = np.asarray(p, float); n = len(p); o = np.argsort(p)
    q = np.empty(n); q[o] = np.minimum.accumulate((p[o] * n / (np.arange(n) + 1))[::-1])[::-1]
    return np.clip(q, 0, 1)


def match_within_study(d, tol=AGE_TOL):
    keep = []
    for _, s in d.groupby("study_id"):
        pool = s[s.obese == 0].copy()
        for _, r in s[s.obese == 1].iterrows():
            cand = pool[(pool.female == r.female) & ((pool.age - r.age).abs() <= tol)]
            if len(cand) == 0:
                continue
            pick = cand.index[np.argmin((cand.age - r.age).abs().to_numpy())]
            keep += [r.name, pick]
            pool = pool.drop(pick)
    return d.loc[sorted(set(keep))]


def adjusted_da(df, species):
    covars = ["obese", "age", "female"]
    X = df[covars].astype(float).reset_index(drop=True)
    if df.study_id.nunique() > 1:
        D = pd.get_dummies(df.study_id, prefix="st", drop_first=True).astype(float).reset_index(drop=True)
        X = pd.concat([X, D], axis=1)
    X = sm.add_constant(X, has_constant="add")
    rows = []
    for sp in species:
        y = np.log10(df[sp].to_numpy(float) + PSEUDO)
        try:
            fit = sm.OLS(y, X).fit()
            rows.append({"species": sp, "coef_obese_log10": fit.params["obese"], "p": fit.pvalues["obese"]})
        except Exception:
            continue
    r = pd.DataFrame(rows)
    if not len(r):
        return r
    r["fdr"] = bh(r.p.to_numpy())
    r["direction"] = np.where(r.coef_obese_log10 < 0, "lean_enriched", "obese_enriched")
    r["fold_change_obese_vs_lean"] = (10 ** r.coef_obese_log10).round(3)
    return r


def meta(df, species):
    out = []
    for sp in species:
        gs, vs = [], []
        for _, s in df.groupby("study_id"):
            L = np.log10(s[s.obese == 0][sp].to_numpy(float) + PSEUDO)
            O = np.log10(s[s.obese == 1][sp].to_numpy(float) + PSEUDO)
            if len(L) < 5 or len(O) < 5:
                continue
            n1, n2 = len(L), len(O)
            sd = np.sqrt(((n1-1)*L.var(ddof=1) + (n2-1)*O.var(ddof=1)) / (n1+n2-2))
            if sd == 0 or not np.isfinite(sd):
                continue
            g = (1 - 3/(4*(n1+n2) - 9)) * (L.mean() - O.mean()) / sd
            gs.append(g); vs.append((n1+n2)/(n1*n2) + g**2/(2*(n1+n2)))
        k = len(gs)
        if k < 3:
            continue
        g = np.array(gs); v = np.array(vs); w = 1/v
        mu_f = (w*g).sum()/w.sum(); Q = (w*(g-mu_f)**2).sum()
        Cc = w.sum() - (w**2).sum()/w.sum()
        tau2 = max(0.0, (Q-(k-1))/Cc) if Cc > 0 else 0.0
        wr = 1/(v+tau2); mu = (wr*g).sum()/wr.sum(); se = np.sqrt(1/wr.sum())
        out.append({"species": sp, "meta_g": round(float(mu), 3),
                    "ci_low": round(float(mu-1.96*se), 3), "ci_high": round(float(mu+1.96*se), 3),
                    "I2_percent": round(float(max(0.0, (Q-(k-1))/Q*100) if Q > 0 else 0.0), 1),
                    "k_studies": k, "ci_excludes_zero": bool((mu-1.96*se)*(mu+1.96*se) > 0)})
    return pd.DataFrame(out)


def run_region(region, meta_df, ab, cols):
    d = meta_df[meta_df.region == region].copy()
    cnt = d.groupby(["study_id", "obesity_status"]).size().unstack(fill_value=0)
    if "lean" not in cnt or "obesity" not in cnt:
        return None
    ok = cnt[(cnt["lean"] >= MIN_PER_GROUP) & (cnt["obesity"] >= MIN_PER_GROUP)].index
    d = d[d.study_id.isin(ok)]
    if not len(d):
        return None
    d = d.join(ab, on="sample_id").dropna(subset=[cols[0]])
    mt = match_within_study(d)
    if (mt.obese == 1).sum() < 10:
        tier = "exploratory_underpowered"
    elif mt.study_id.nunique() >= 3:
        tier = "robust_capable"
    else:
        tier = "adjusted_only_single_study"
    species = [c for c in cols if (mt[c] > 0).mean() >= MIN_PREV]
    da = adjusted_da(mt, species)
    if not len(da):
        return None
    mm = meta(mt, species)
    res = da.merge(mm, on="species", how="left") if len(mm) else da.assign(
        meta_g=np.nan, ci_low=np.nan, ci_high=np.nan, I2_percent=np.nan,
        k_studies=np.nan, ci_excludes_zero=False)
    res["robust"] = (res.fdr < 0.05) & res.ci_excludes_zero.fillna(False) & \
                    (np.sign(-res.coef_obese_log10) == np.sign(res.meta_g))
    res["region"] = region; res["tier"] = tier
    info = {"region": region, "tier": tier, "studies": int(mt.study_id.nunique()),
            "study_ids": sorted(mt.study_id.unique().tolist()),
            "matched_n": int(len(mt)), "lean": int((mt.obese == 0).sum()), "obese": int((mt.obese == 1).sum()),
            "age_lean": round(float(mt[mt.obese == 0].age.mean()), 1),
            "age_obese": round(float(mt[mt.obese == 1].age.mean()), 1),
            "female_lean": round(float(mt[mt.obese == 0].female.mean()), 2),
            "female_obese": round(float(mt[mt.obese == 1].female.mean()), 2),
            "n_species": len(species), "n_fdr_sig": int((res.fdr < 0.05).sum()),
            "n_lean_enriched_sig": int(((res.fdr < 0.05) & (res.direction == "lean_enriched")).sum()),
            "n_robust": int(res.robust.sum())}
    return res, info


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    m = pd.read_csv(ROOT / "data/metadata/sample_metadata_raw.csv")
    ab = pd.read_csv(ROOT / "data/taxonomic_profile/species_abundance_wide.csv").set_index("sample_id")
    cols = list(ab.columns)
    m["region"] = m.country.map(REGION).fillna("其他")
    m = m[(m.disease_status == "healthy") & (m.obesity_status.isin(["lean", "obesity"]))
          & m.age.notna() & m.sex.isin(["male", "female"])].copy()
    m["obese"] = (m.obesity_status == "obesity").astype(int)
    m["female"] = (m.sex == "female").astype(int)

    all_res, infos = [], []
    for reg in ["西欧", "北美", "中东", "中亚", "东亚", "非洲"]:
        got = run_region(reg, m, ab, cols)
        if got is None:
            print(f"  {reg}: 不可行"); continue
        res, info = got
        all_res.append(res); infos.append(info)
        print(f"  {reg:4} [{info['tier']:26}] 研究{info['studies']} 匹配n={info['matched_n']} "
              f"(瘦{info['lean']}/胖{info['obese']}) 年龄{info['age_lean']}vs{info['age_obese']} "
              f"| 物种{info['n_species']} FDR显著{info['n_fdr_sig']} 瘦人富集{info['n_lean_enriched_sig']} 稳健{info['n_robust']}")

    R = pd.concat(all_res, ignore_index=True)
    R.to_csv(OUT / "regional_differential_all.csv", index=False, encoding="utf-8-sig")

    # ---- cross-region lean-enriched comparison ----
    sig = R[(R.fdr < 0.05) & (R.direction == "lean_enriched")]
    piv = R.pivot_table(index="species", columns="region", values="coef_obese_log10", aggfunc="first")
    fdr = R.pivot_table(index="species", columns="region", values="fdr", aggfunc="first")
    regions = [i["region"] for i in infos]
    lean_sig = pd.DataFrame({r: ((piv[r] < 0) & (fdr[r] < 0.05)) for r in regions if r in piv.columns})
    tested = pd.DataFrame({r: piv[r].notna() for r in regions if r in piv.columns})
    summary = pd.DataFrame({
        "在几个地区显著瘦人富集": lean_sig.sum(axis=1),
        "在几个地区受检": tested.sum(axis=1),
        "西欧方向": np.where(piv.get("西欧").notna(), np.where(piv.get("西欧") < 0, "瘦人", "肥胖"), "未检"),
    })
    for r in regions:
        if r in piv.columns:
            summary[f"{r}_系数"] = piv[r].round(4)
            summary[f"{r}_FDR"] = fdr[r].round(4)
    summary = summary.sort_values(["在几个地区显著瘦人富集", "在几个地区受检"], ascending=False)
    summary.to_csv(OUT / "cross_region_lean_enriched.csv", encoding="utf-8-sig")

    print(f"\n=== 跨地区瘦人富集汇总 ===")
    multi = summary[summary["在几个地区显著瘦人富集"] >= 2]
    print(f"  在 ≥2 个地区显著瘦人富集: {len(multi)} 个物种")
    for sp, r in multi.head(15).iterrows():
        regs = [x for x in regions if x in piv.columns and lean_sig.loc[sp, x]]
        print(f"    {sp[:36]:36} {int(r['在几个地区显著瘦人富集'])}/{int(r['在几个地区受检'])} 地区: {', '.join(regs)}")

    print(f"\n=== 各地区特有的瘦人富集菌（仅该地区显著）===")
    for reg in regions:
        if reg not in piv.columns: continue
        only = summary[(lean_sig[reg]) & (summary["在几个地区显著瘦人富集"] == 1)]
        print(f"  {reg}: {len(only)} 个 | " + ", ".join(list(only.index[:6])))

    (OUT / "regional_summary.json").write_text(json.dumps({
        "pipeline": "identical to Western-Europe: disease-free, lean vs obese, within-study 1:1 age(±5y)/sex matching, OLS+BH-FDR, DL random-effects meta when >=3 studies, robust=FDR+CI+direction",
        "regions": infos,
        "n_species_lean_enriched_in_2plus_regions": int(len(multi))},
        indent=2, ensure_ascii=False), encoding="utf-8")
    print("\nwrote", OUT.relative_to(ROOT))


if __name__ == "__main__":
    main()
