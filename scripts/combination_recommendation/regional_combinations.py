"""Region-specific strain combinations.

Same v2 scoring logic as synergistic_lean_combinations_v2.py, but every input is
recomputed WITHIN each region so that a region's formulation rests on its own
evidence:

  pool                : that region's significant lean-enriched species (FDR<0.05)
  effect score        : that region's own adjusted effect size
  diversity score     : Spearman(log10 abundance, Shannon) computed within that
                        region's matched cohort, group-wise then averaged
  guild / culturability: shared annotation (genus-level biology does not change)

Members are additionally tagged as universal core (significant lean-enriched in
>=2 regions) or region-specific, so a formulation can be read as
"universal core + regional add-on".
"""
from __future__ import annotations

import io
import json
import re
from itertools import combinations
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

ROOT = Path(__file__).resolve().parents[2]
PR = ROOT / "results/prediction_results"
OUT = ROOT / "results/combination_recommendations"
PSEUDO = 1e-3
MIN_PREV = 0.10
AGE_TOL = 5

W = {"diversity": 0.30, "effect": 0.24, "complementarity": 0.16,
     "propionate": 0.12, "quality": 0.10, "genus_diversity": 0.08}
PENALTY = {"spore_former": 0.05, "oral_origin": 0.10}

REGION = {"NLD": "西欧", "GBR": "西欧", "DNK": "西欧", "FRA": "西欧", "DEU": "西欧", "ITA": "西欧",
          "ESP": "西欧", "SWE": "西欧", "AUT": "西欧", "IRL": "西欧", "LUX": "西欧",
          "CHN": "东亚", "JPN": "东亚", "KOR": "东亚", "USA": "北美", "CAN": "北美",
          "ISR": "中东", "IND": "南亚", "KAZ": "中亚", "CMR": "非洲", "MDG": "非洲", "PER": "南美"}
CULT = {"Akkermansia_muciniphila": ("culturable_commercial", 1.0),
        "Faecalibacterium_prausnitzii": ("fastidious_anaerobe", 0.7),
        "Roseburia": ("culturable_anaerobe", 0.85), "Eubacterium": ("culturable_anaerobe", 0.85),
        "Butyrivibrio": ("culturable_anaerobe", 0.8), "Odoribacter": ("culturable_anaerobe", 0.8),
        "Barnesiella": ("culturable_anaerobe", 0.8), "Alistipes": ("culturable_anaerobe", 0.8),
        "Bacteroides": ("culturable_easy", 0.95), "Parabacteroides": ("culturable_easy", 0.9),
        "Oscillibacter": ("fastidious_anaerobe", 0.6), "Coprococcus": ("culturable_anaerobe", 0.8),
        "Methanobrevibacter": ("archaea_special_culture", 0.4),
        "Intestinimonas": ("culturable_anaerobe", 0.75), "Butyricimonas": ("culturable_anaerobe", 0.75),
        "Clostridium": ("culturable_anaerobe", 0.8), "Bifidobacterium": ("culturable_easy", 0.95),
        "Anaerostipes": ("culturable_anaerobe", 0.8), "Ruthenibacterium": ("culturable_anaerobe", 0.7),
        "Turicibacter": ("named_isolate_likely", 0.65), "Coprobacter": ("culturable_anaerobe", 0.7)}
SPORE = {"Clostridium", "Bacillus", "Romboutsia", "Turicibacter", "Anaerostipes", "Roseburia",
         "Eubacterium", "Butyrivibrio", "Coprococcus", "Blautia", "Faecalibacterium",
         "Intestinimonas", "Oscillibacter", "Ruminococcus", "Dorea", "Flavonifractor"}
ORAL = {"Streptococcus", "Actinomyces", "Veillonella", "Gemella", "Rothia", "Haemophilus", "Fusobacterium"}
ADVERSE = {"Bilophila", "Desulfovibrio", "Desulfovibrionaceae", "Eggerthella"}


def culturability(sp, genus):
    if re.search(r"CAG|_sp_|bacterium_[A-Z0-9]|_sp$", sp):
        return ("uncultured_or_MAG", 0.2)
    if sp in CULT: return CULT[sp]
    if genus in CULT: return CULT[genus]
    return ("named_isolate_likely", 0.65)


def shannon(x):
    p = x[x > 0] / 100.0
    p = p / p.sum() if p.sum() > 0 else p
    return float(-(p * np.log(p)).sum()) if len(p) else 0.0


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


def regional_diversity(mt, species):
    A = mt[species].to_numpy(float)
    sh = np.array([shannon(r) for r in mt[[c for c in mt.columns if c in species]].to_numpy(float)])
    out = {}
    logX = np.log10(mt[species] + PSEUDO)
    for sp in species:
        rs = []
        for g in (0, 1):
            m = (mt.obese == g).to_numpy()
            if (mt.loc[m, sp] > 0).sum() > 8:
                r, _ = stats.spearmanr(logX.loc[m, sp], sh[m])
                if np.isfinite(r):
                    rs.append(r)
        out[sp] = float(np.mean(rs)) if rs else np.nan
    return out


def main():
    m = pd.read_csv(ROOT / "data/metadata/sample_metadata_raw.csv")
    ab = pd.read_csv(ROOT / "data/taxonomic_profile/species_abundance_wide.csv").set_index("sample_id")
    cols = list(ab.columns)
    reg_res = pd.read_csv(PR / "multiregion/regional_differential_all.csv")
    cross = pd.read_csv(PR / "multiregion/cross_region_lean_enriched.csv", index_col=0)
    guild = pd.read_csv(ROOT / "data/strain_genome/genus_functional_guild_reference_20260613.csv").set_index("genus")

    m["region"] = m.country.map(REGION).fillna("其他")
    m = m[(m.disease_status == "healthy") & (m.obesity_status.isin(["lean", "obesity"]))
          & m.age.notna() & m.sex.isin(["male", "female"])].copy()
    m["obese"] = (m.obesity_status == "obesity").astype(int)
    m["female"] = (m.sex == "female").astype(int)

    universal = set(cross[cross["在几个地区显著瘦人富集"] >= 2].index)
    all_pools, all_combos, infos = [], [], []

    for region in ["西欧", "北美", "中东"]:
        rr = reg_res[(reg_res.region == region) & (reg_res.fdr < 0.05)
                     & (reg_res.direction == "lean_enriched")].copy()
        if not len(rr):
            continue
        d = m[m.region == region].copy()
        cnt = d.groupby(["study_id", "obesity_status"]).size().unstack(fill_value=0)
        ok = cnt[(cnt.get("lean", 0) >= 10) & (cnt.get("obesity", 0) >= 10)].index
        d = d[d.study_id.isin(ok)].join(ab, on="sample_id").dropna(subset=[cols[0]])
        mt = match_within_study(d)
        species = [c for c in cols if (mt[c] > 0).mean() >= MIN_PREV]
        div = regional_diversity(mt, species)

        p = rr.copy()
        p["genus"] = p.species.str.split("_").str[0]
        p["diversity_rho"] = p.species.map(div)
        for col, g in [("butyrate", "butyrate_scfa_potential"), ("propionate", "propionate_potential"),
                       ("mucin", "mucin_interaction")]:
            p[col] = p.genus.map(lambda x: float(guild.loc[x, g]) if x in guild.index else 0.0)
        p[["culturability_class", "culturability_score"]] = p.apply(
            lambda r: pd.Series(culturability(r.species, r.genus)), axis=1)
        p["spore_former"] = p.genus.isin(SPORE).astype(int)
        p["oral_origin"] = p.genus.isin(ORAL).astype(int)
        p = p[~p.genus.isin(ADVERSE)]
        p = p[~p.culturability_class.isin(["uncultured_or_MAG", "archaea_special_culture"])]
        if not len(p):
            continue
        p["diversity_score"] = (p.diversity_rho.fillna(0) / 0.38).clip(0, 1)
        p["effect_score"] = (p.coef_obese_log10.abs() / 0.60).clip(0, 1)
        p["propionate_score"] = (p.propionate / 2.0).clip(0, 1)
        p["scope"] = np.where(p.species.isin(universal), "跨地区通用", f"{region}特有")
        p["region"] = region
        p = p.reset_index(drop=True)
        all_pools.append(p)

        recs = []
        for size in (3, 4, 5):
            for combo in combinations(list(p.index), size):
                rows = p.loc[list(combo)]
                ax = {"propionate": int((rows.propionate > 0).any()),
                      "butyrate": int((rows.butyrate > 0).any()),
                      "mucin": int((rows.mucin > 0).any())}
                n_ax = sum(ax.values())
                if n_ax < 2:
                    continue
                gdiv = rows.genus.nunique() / size
                score = (W["diversity"] * rows.diversity_score.mean()
                         + W["effect"] * rows.effect_score.mean()
                         + W["complementarity"] * n_ax / 3.0
                         + W["propionate"] * rows.propionate_score.mean()
                         + W["quality"] * rows.culturability_score.mean()
                         + W["genus_diversity"] * gdiv
                         - PENALTY["spore_former"] * rows.spore_former.mean()
                         - PENALTY["oral_origin"] * rows.oral_origin.mean())
                recs.append({"region": region, "members": "; ".join(rows.species),
                             "n_strains": size, "axes": "+".join(k for k, v in ax.items() if v),
                             "n_axes": n_ax,
                             "n_universal_members": int(rows.scope.eq("跨地区通用").sum()),
                             "diversity_mean": round(float(rows.diversity_rho.mean()), 3),
                             "effect_mean": round(float(rows.coef_obese_log10.abs().mean()), 3),
                             "culturability_mean": round(float(rows.culturability_score.mean()), 3),
                             "composite": round(float(score), 4)})
        cdf = pd.DataFrame(recs).sort_values("composite", ascending=False).reset_index(drop=True)
        cdf.insert(0, "rank", range(1, len(cdf) + 1))
        all_combos.append(cdf)
        top = cdf.iloc[0]
        infos.append({"region": region, "pool_size": int(len(p)),
                      "universal_in_pool": int(p.scope.eq("跨地区通用").sum()),
                      "n_combinations": int(len(cdf)),
                      "top_members": top["members"].split("; "), "top_composite": float(top["composite"]),
                      "top_axes": str(top["axes"]), "top_universal_members": int(top["n_universal_members"]), "top_n_strains": int(top["n_strains"])})
        print(f"\n=== {region} ===  候选池 {len(p)} 株（含跨地区通用 {int(p.scope.eq('跨地区通用').sum())} 株）")
        for r in p.sort_values("diversity_score", ascending=False).head(10).itertuples():
            print(f"   {r.species[:32]:32} ρ={r.diversity_rho if pd.notna(r.diversity_rho) else 0:+.2f} "
                  f"|系数|={abs(r.coef_obese_log10):.2f} 丙酸={int(r.propionate)} [{r.scope}]")
        print(f"  首选（{int(top['n_strains'])}株, 轴{int(top['n_axes'])}/3, 通用成员{int(top['n_universal_members'])}）综合 {top['composite']:.4f}:")
        print("    " + " + ".join(x.replace("_", " ") for x in top["members"].split("; ")))

    P = pd.concat(all_pools, ignore_index=True)
    C = pd.concat(all_combos, ignore_index=True)
    P.to_csv(OUT / "regional_pools_20260625.csv", index=False, encoding="utf-8-sig")
    C.to_csv(OUT / "regional_combinations_20260625.csv", index=False, encoding="utf-8-sig")

    print("\n=== 各地区首选组合对比 ===")
    for i in infos:
        print(f"  {i['region']}: " + " + ".join(x.replace('_', ' ') for x in i['top_members'])
              + f"  (综合 {i['top_composite']:.4f}, 通用成员 {i['top_universal_members']}/{len(i['top_members'])})")
    shared = set.intersection(*[set(i["top_members"]) for i in infos]) if len(infos) > 1 else set()
    print(f"  三地区首选共有成员: {sorted(shared) if shared else '无'}")

    io.open(OUT / "regional_combinations_summary_20260625.json", "w", encoding="utf-8").write(
        json.dumps({"weights": W, "penalties": PENALTY,
                    "note": "per-region pool, effect and diversity association; shared guild/culturability annotation",
                    "regions": infos, "shared_top_members": sorted(shared)},
                   indent=2, ensure_ascii=False))
    print("\nwrote", (OUT / "regional_combinations_20260625.csv").relative_to(ROOT))


if __name__ == "__main__":
    main()
