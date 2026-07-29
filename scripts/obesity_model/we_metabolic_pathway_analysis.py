"""Differential gut METABOLIC POTENTIAL between lean and obese (Western Europe).

IMPORTANT SCOPE STATEMENT
-------------------------
This analysis uses HUMAnN/MetaCyc **pathway abundance derived from shotgun
metagenomes** - i.e. the community's genetic CAPACITY to produce/consume
metabolites. It is NOT measured metabolomics (no LC-MS/GC-MS data exist in this
project). Conclusions must therefore be phrased as differences in metabolic
potential, and any metabolite-level statement is an inference.

Design
------
Primary   : the age/sex-matched pairs that also have pathway data (144 vs 144,
            all from one cohort, so batch is fully controlled by design).
Secondary : the whole disease-free lean/obese set with pathway data, with
            age + sex + study adjustment (more power, less balance).
Statistics: log10(relative abundance + pseudocount) ~ obesity + covariates,
            Benjamini-Hochberg FDR, plus Cliff's delta as a non-parametric
            effect size. No cross-study meta-analysis is possible because the
            pathway data covers essentially a single Western-European cohort -
            this is stated as a limitation rather than worked around.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.api as sm
from scipy import stats

ROOT = Path(__file__).resolve().parents[2]
PR = ROOT / "results/prediction_results"
OUT = PR / "we_metabolic"
WE = {"NLD", "GBR", "DNK", "FRA", "DEU", "ITA", "ESP", "SWE", "AUT", "IRL", "LUX"}
PSEUDO = 1e-4
MIN_PREV = 0.10

# pathway -> metabolite class (regex on the MetaCyc label)
CLASSES = [
    ("短链脂肪酸-丁酸", r"butanoate|butyrate"),
    ("短链脂肪酸-丙酸", r"propanoate|propionate|propionic"),
    ("短链脂肪酸-乙酸/发酵", r"acetate|acetyl.CoA.fermentation|fermentation"),
    ("胆汁酸", r"cholate|bile|DEHYDROX"),
    ("支链氨基酸(BCAA)", r"isoleucine|leucine|valine"),
    ("芳香族氨基酸/吲哚", r"tryptophan|tyrosine|phenylalanine|indole|chorismate"),
    ("其他氨基酸", r"lysine|arginine|methionine|threonine|serine|glutam|histidine|proline|cysteine|ornithine|asparagine"),
    ("多胺", r"polyamine|putrescine|spermidine"),
    ("B族维生素/辅因子", r"thiamin|riboflavin|folate|cobalamin|biotin|pantothenate|pyridoxine|menaquinone|ubiquinol|tetrahydrofolate|NAD"),
    ("糖类降解/利用", r"degradation.*(glucose|galactose|fucose|rhamnose|xylose|arabinose|mannose|starch|glycogen|sucrose|lactose)|glycolysis|pentose"),
    ("肽聚糖/细胞壁", r"peptidoglycan|lipopolysaccharide|O.antigen|teichoic|murein"),
    ("脂肪酸/脂质", r"fatty.acid|lipid|palmitate|oleate|phospholipid"),
    ("核苷酸", r"purine|pyrimidine|nucleotide|nucleoside|adenosine|guanosine"),
    ("硫/含硫代谢", r"sulf|taurine|thiosulfate"),
]


def classify(label: str) -> str:
    for name, pat in CLASSES:
        if re.search(pat, label, re.I):
            return name
    return "其他/未分类"


def clean_name(col: str) -> str:
    """X1CMET2.PWY..N10.formyl... -> 'N10-formyl...' with the MetaCyc id kept."""
    s = col
    s = re.sub(r"^X", "", s)
    parts = re.split(r"\.\.+", s, maxsplit=1)
    pid = parts[0].replace(".", "-")
    desc = parts[1].replace(".", " ").strip() if len(parts) > 1 else ""
    return pid, desc


def bh(p):
    p = np.asarray(p, float); n = len(p); o = np.argsort(p)
    q = np.empty(n); q[o] = np.minimum.accumulate((p[o] * n / (np.arange(n) + 1))[::-1])[::-1]
    return np.clip(q, 0, 1)


def cliffs_delta(a, b):
    a = np.asarray(a); b = np.asarray(b)
    gt = sum((a[:, None] > b[None, :]).sum(axis=1))
    lt = sum((a[:, None] < b[None, :]).sum(axis=1))
    return (gt - lt) / (len(a) * len(b))


def analyse(df, feats, covars, label):
    """OLS on log10 abundance with covariates; returns tidy результат table."""
    X = df[covars].astype(float).reset_index(drop=True)
    X = sm.add_constant(X, has_constant="add")
    y0 = df.obese.to_numpy()
    rows = []
    for f in feats:
        v = df[f].to_numpy(float)
        yv = np.log10(v + PSEUDO)
        try:
            fit = sm.OLS(yv, X).fit()
            beta, p = fit.params["obese"], fit.pvalues["obese"]
        except Exception:
            continue
        lean, ob = yv[y0 == 0], yv[y0 == 1]
        d = cliffs_delta(lean, ob)
        try:
            _, pmw = stats.mannwhitneyu(lean, ob)
        except ValueError:
            pmw = np.nan
        pid, desc = clean_name(f)
        rows.append({"pathway_id": pid, "pathway": desc or pid, "metabolite_class": classify(f),
                     "coef_obese_log10": round(float(beta), 4),
                     "fold_change_obese_vs_lean": round(float(10 ** beta), 3),
                     "cliffs_delta_lean_vs_obese": round(float(d), 3),
                     "p_ols": float(p), "p_mannwhitney": float(pmw),
                     "mean_lean_pct": round(float(df.loc[y0 == 0, f].mean()), 4),
                     "mean_obese_pct": round(float(df.loc[y0 == 1, f].mean()), 4),
                     "analysis": label})
    r = pd.DataFrame(rows)
    r["fdr"] = bh(r.p_ols.to_numpy())
    r["direction"] = np.where(r.coef_obese_log10 < 0, "lean_enriched", "obese_enriched")
    return r.sort_values("p_ols")


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    meta = pd.read_csv(ROOT / "data/metadata/sample_metadata_raw.csv")
    pw = pd.read_csv(ROOT / "data/functional_profile/pathway_abundance_wide.csv")
    matched = pd.read_csv(PR / "we_healthy/matched_cohort.csv")

    meta = meta[(meta.country.isin(WE)) & (meta.disease_status == "healthy")
                & (meta.obesity_status.isin(["lean", "obesity"]))
                & meta.age.notna() & meta.sex.isin(["male", "female"])].copy()
    meta["obese"] = (meta.obesity_status == "obesity").astype(int)
    meta["female"] = (meta.sex == "female").astype(int)
    d = meta.merge(pw, on="sample_id", how="inner")
    feats_all = [c for c in pw.columns if c != "sample_id"]

    print(f"=== 数据范围 ===")
    print(f"  西欧健康(瘦/胖)且有通路数据: {len(d)} 例  |  研究: {d.study_id.value_counts().to_dict()}")

    # ---------- primary: matched pairs with pathway data ----------
    mm = d[d.sample_id.isin(set(matched.sample_id))].copy()
    feats = [f for f in feats_all if (mm[f] > 0).mean() >= MIN_PREV]
    print(f"\n【主分析】年龄性别匹配子集: n={len(mm)} (瘦 {int((mm.obese==0).sum())} / 胖 {int((mm.obese==1).sum())})")
    print(f"  年龄 瘦 {mm[mm.obese==0].age.mean():.1f} vs 胖 {mm[mm.obese==1].age.mean():.1f} | "
          f"女性比 {mm[mm.obese==0].female.mean():.2f} vs {mm[mm.obese==1].female.mean():.2f}")
    print(f"  通路数(流行率≥10%): {len(feats)}")
    r1 = analyse(mm, feats, ["obese", "age", "female"], "matched_144v144")

    # ---------- secondary: full set, adjusted ----------
    dd = d.copy()
    feats2 = [f for f in feats_all if (dd[f] > 0).mean() >= MIN_PREV]
    covars = ["obese", "age", "female"]
    if dd.study_id.nunique() > 1:
        for s in sorted(dd.study_id.unique())[1:]:
            dd[f"st_{s}"] = (dd.study_id == s).astype(int)
            covars.append(f"st_{s}")
    print(f"\n【副分析】全集校正: n={len(dd)} (瘦 {int((dd.obese==0).sum())} / 胖 {int((dd.obese==1).sum())})，通路 {len(feats2)}")
    r2 = analyse(dd, feats2, covars, "adjusted_full")

    both = r1.merge(r2[["pathway_id", "coef_obese_log10", "fdr", "direction"]],
                    on="pathway_id", suffixes=("", "_full"))
    both["replicated"] = (both.fdr < 0.05) & (both.fdr_full < 0.05) & (both.direction == both.direction_full)

    pd.concat([r1, r2]).to_csv(OUT / "pathway_differential_all.csv", index=False, encoding="utf-8-sig")
    both.to_csv(OUT / "pathway_differential_merged.csv", index=False, encoding="utf-8-sig")

    sig1 = r1[r1.fdr < 0.05]; sig2 = r2[r2.fdr < 0.05]
    print(f"\n=== 结果 ===")
    print(f"  主分析 FDR<0.05: {len(sig1)} 条  |  副分析 FDR<0.05: {len(sig2)} 条  |  两者一致: {int(both.replicated.sum())} 条")

    print("\n【肥胖富集 Top12（主分析显著，按效应排序）】")
    for r in sig1[sig1.direction == "obese_enriched"].nlargest(12, "coef_obese_log10").itertuples():
        print(f"  [{r.metabolite_class:16}] {r.pathway[:52]:52} FC={r.fold_change_obese_vs_lean:.2f} δ={r.cliffs_delta_lean_vs_obese:+.2f} FDR={r.fdr:.1e}")
    print("\n【瘦人富集 Top12】")
    for r in sig1[sig1.direction == "lean_enriched"].nsmallest(12, "coef_obese_log10").itertuples():
        print(f"  [{r.metabolite_class:16}] {r.pathway[:52]:52} FC={r.fold_change_obese_vs_lean:.2f} δ={r.cliffs_delta_lean_vs_obese:+.2f} FDR={r.fdr:.1e}")

    # class-level summary
    cls = r1.groupby("metabolite_class").apply(
        lambda g: pd.Series({"n_pathways": len(g),
                             "n_sig": int((g.fdr < 0.05).sum()),
                             "n_obese_enriched": int(((g.fdr < 0.05) & (g.direction == "obese_enriched")).sum()),
                             "n_lean_enriched": int(((g.fdr < 0.05) & (g.direction == "lean_enriched")).sum()),
                             "mean_coef": round(float(g.coef_obese_log10.mean()), 4)}), include_groups=False
    ).reset_index().sort_values("n_sig", ascending=False)
    cls.to_csv(OUT / "metabolite_class_summary.csv", index=False, encoding="utf-8-sig")
    print("\n【代谢物类别汇总】")
    print(f"{'类别':20}{'通路数':>7}{'显著':>6}{'肥胖↑':>7}{'瘦人↑':>7}{'平均系数':>10}")
    for r in cls.itertuples():
        print(f"{r.metabolite_class:20}{r.n_pathways:>7}{r.n_sig:>6}{r.n_obese_enriched:>7}{r.n_lean_enriched:>7}{r.mean_coef:>10.4f}")

    (OUT / "summary.json").write_text(json.dumps({
        "scope": "HUMAnN/MetaCyc pathway abundance from shotgun metagenomes = metabolic POTENTIAL, not measured metabolites",
        "cohorts_with_pathway_data": d.study_id.value_counts().to_dict(),
        "primary": {"design": "age/sex-matched pairs, single cohort (batch controlled by design)",
                    "n": int(len(mm)), "lean": int((mm.obese == 0).sum()), "obese": int((mm.obese == 1).sum()),
                    "age_lean": round(float(mm[mm.obese == 0].age.mean()), 1),
                    "age_obese": round(float(mm[mm.obese == 1].age.mean()), 1),
                    "n_pathways": len(feats), "n_fdr_sig": int(len(sig1))},
        "secondary": {"design": "full disease-free set, age+sex(+study) adjusted",
                      "n": int(len(dd)), "lean": int((dd.obese == 0).sum()), "obese": int((dd.obese == 1).sum()),
                      "n_pathways": len(feats2), "n_fdr_sig": int(len(sig2))},
        "consistent_between_analyses": int(both.replicated.sum()),
        "limitation": "pathway data covers essentially one Western-European cohort; no cross-study meta-analysis possible",
    }, indent=2, ensure_ascii=False), encoding="utf-8")
    print("\nwrote", OUT.relative_to(ROOT))


if __name__ == "__main__":
    main()
