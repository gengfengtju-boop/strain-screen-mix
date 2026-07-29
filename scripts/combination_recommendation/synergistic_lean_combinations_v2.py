"""Synergistic fat-loss combinations - VERSION 2 (evidence-reweighted).

Changes from v1 (scripts/combination_recommendation/synergistic_lean_combinations.py),
each driven by a validation result rather than assumption:

  POOL   v1: 53 lean-enriched species from the GLOBAL unadjusted analysis.
         v2: lean-enriched species from the Western-Europe healthy, T2D-excluded,
             age/sex-matched, FDR + random-effects-meta validated analysis.

  WEIGHTS                          v1        v2      reason
   diversity association            -       0.30     AUC 0.920, the only feature
                                                     that generalises across
                                                     genera (leave-one-genus-out
                                                     0.878)
   observed lean-vs-obese effect   0.10*    0.24     direct evidence from the
                                                     rigorous screen (meta g)
   mechanism complementarity       0.28     0.16     still a design principle for
                                                     combinations, but no longer
                                                     the dominant term
   propionate potential            (in fat) 0.12     AUC 0.647 in-sample; does not
                                                     generalise across genera
   culturability / strain quality  0.14     0.10     unchanged in spirit
   genus diversity                 0.06     0.08     combination-level
   BSH "cholesterol"               0.16     0.00     REMOVED: AUC 0.517 (P=0.85),
                                                     cross-genus 0.027, and adding
                                                     it degraded the best model
                                                     0.878 -> 0.798
   butyrate as a positive term     implicit  none    AUC 0.540 and inverted
                                                     (78% lean vs 84% baseline)
   PENALTIES                        -       spore-former / oral-origin members
                                             (obese-enriched tendencies)

v1 outputs are left untouched; v2 writes *_v2_20260625.csv.
"""
from __future__ import annotations

import json
import re
from itertools import combinations
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
PR = ROOT / "results/prediction_results"
OUT = ROOT / "results/combination_recommendations"

W = {"diversity": 0.30, "effect": 0.24, "complementarity": 0.16,
     "propionate": 0.12, "quality": 0.10, "genus_diversity": 0.08}
PENALTY = {"spore_former": 0.05, "oral_origin": 0.10}

CULT = {"Akkermansia_muciniphila": ("culturable_commercial", 1.0),
        "Faecalibacterium_prausnitzii": ("fastidious_anaerobe", 0.7),
        "Roseburia": ("culturable_anaerobe", 0.85), "Eubacterium": ("culturable_anaerobe", 0.85),
        "Butyrivibrio": ("culturable_anaerobe", 0.8), "Odoribacter": ("culturable_anaerobe", 0.8),
        "Barnesiella": ("culturable_anaerobe", 0.8), "Alistipes": ("culturable_anaerobe", 0.8),
        "Bacteroides": ("culturable_easy", 0.95), "Parabacteroides": ("culturable_easy", 0.9),
        "Oscillibacter": ("fastidious_anaerobe", 0.6), "Coprococcus": ("culturable_anaerobe", 0.8),
        "Methanobrevibacter": ("archaea_special_culture", 0.4),
        "Intestinimonas": ("culturable_anaerobe", 0.75), "Butyricimonas": ("culturable_anaerobe", 0.75),
        "Clostridium": ("culturable_anaerobe", 0.8), "Bifidobacterium": ("culturable_easy", 0.95)}
SPORE = {"Clostridium", "Bacillus", "Romboutsia", "Turicibacter", "Anaerostipes", "Roseburia",
         "Eubacterium", "Butyrivibrio", "Coprococcus", "Blautia", "Faecalibacterium",
         "Intestinimonas", "Oscillibacter", "Ruminococcus", "Dorea", "Flavonifractor"}
ORAL = {"Streptococcus", "Actinomyces", "Veillonella", "Gemella", "Rothia", "Haemophilus", "Fusobacterium"}
ADVERSE = {"Bilophila", "Desulfovibrio", "Desulfovibrionaceae"}  # H2S producers


def culturability(sp, genus):
    if re.search(r"CAG|_sp_|bacterium_[A-Z0-9]|_sp$", sp):
        return ("uncultured_or_MAG", 0.2)
    if sp in CULT: return CULT[sp]
    if genus in CULT: return CULT[genus]
    return ("named_isolate_likely", 0.65)


def build_pool():
    da = pd.read_csv(PR / "we_healthy/differential_abundance_adjusted.csv")
    div = pd.read_csv(PR / "lean_factors/diversity_association_all_species.csv")[["species", "diversity_rho"]]
    guild = pd.read_csv(ROOT / "data/strain_genome/genus_functional_guild_reference_20260613.csv").set_index("genus")
    p = da[(da.robust == True) & (da.direction == "lean_enriched")].merge(div, on="species", how="left").copy()
    p["genus"] = p.species.str.split("_").str[0]
    for col, g in [("butyrate", "butyrate_scfa_potential"), ("propionate", "propionate_potential"),
                   ("mucin", "mucin_interaction"), ("bsh", "bsh_potential")]:
        p[col] = p.genus.map(lambda x: float(guild.loc[x, g]) if x in guild.index else 0.0)
    p[["culturability_class", "culturability_score"]] = p.apply(
        lambda r: pd.Series(culturability(r.species, r.genus)), axis=1)
    p["spore_former"] = p.genus.isin(SPORE).astype(int)
    p["oral_origin"] = p.genus.isin(ORAL).astype(int)
    p = p[~p.genus.isin(ADVERSE)]
    # normalised scores
    p["diversity_score"] = ((p.diversity_rho.fillna(0) - 0) / 0.38).clip(0, 1)
    p["effect_score"] = (p.meta_g.abs() / 0.42).clip(0, 1)
    p["propionate_score"] = (p.propionate / 2.0).clip(0, 1)
    # exclude MAG-only and archaea from formulation feasibility
    p = p[~p.culturability_class.isin(["uncultured_or_MAG", "archaea_special_culture"])]
    return p.reset_index(drop=True)


def main():
    pool = build_pool()
    pool = pool.sort_values("diversity_score", ascending=False)
    pool.to_csv(OUT / "synergistic_pool_v2_20260625.csv", index=False, encoding="utf-8-sig")
    print(f"=== v2 候选池：{len(pool)} 株（西欧严格验证的稳健瘦人富集菌，去除促炎/未培养/古菌）===")
    for r in pool.itertuples():
        print(f"  {r.species[:34]:34} ρ={r.diversity_rho:+.2f} g={r.meta_g:+.2f} "
              f"丙酸={int(r.propionate)} {r.culturability_class}")

    def axes(rows):
        return {"propionate": int((rows.propionate > 0).any()),
                "butyrate": int((rows.butyrate > 0).any()),
                "mucin": int((rows.mucin > 0).any())}

    recs = []
    idx = list(pool.index)
    for size in (3, 4, 5):
        for combo in combinations(idx, size):
            rows = pool.loc[list(combo)]
            ax = axes(rows); n_ax = sum(ax.values())
            if n_ax < 2:
                continue
            comp = n_ax / 3.0
            gdiv = rows.genus.nunique() / size
            score = (W["diversity"] * rows.diversity_score.mean()
                     + W["effect"] * rows.effect_score.mean()
                     + W["complementarity"] * comp
                     + W["propionate"] * rows.propionate_score.mean()
                     + W["quality"] * rows.culturability_score.mean()
                     + W["genus_diversity"] * gdiv
                     - PENALTY["spore_former"] * rows.spore_former.mean()
                     - PENALTY["oral_origin"] * rows.oral_origin.mean())
            recs.append({"members": "; ".join(rows.species), "n_strains": size,
                         "axes": "+".join(k for k, v in ax.items() if v), "n_axes": n_ax,
                         "diversity_mean": round(float(rows.diversity_rho.mean()), 3),
                         "effect_mean_g": round(float(rows.meta_g.mean()), 3),
                         "propionate_frac": round(float((rows.propionate > 0).mean()), 2),
                         "culturability_mean": round(float(rows.culturability_score.mean()), 3),
                         "genus_diversity": round(float(gdiv), 2),
                         "spore_frac": round(float(rows.spore_former.mean()), 2),
                         "composite_v2": round(float(score), 4)})
    res = pd.DataFrame(recs).sort_values("composite_v2", ascending=False).drop_duplicates("members").reset_index(drop=True)
    res.insert(0, "rank", range(1, len(res) + 1))
    res.to_csv(OUT / "synergistic_lean_combinations_v2_20260625.csv", index=False, encoding="utf-8-sig")

    print(f"\n=== v2 组合评分：{len(res)} 个候选 ===")
    print("\nTop 8：")
    for r in res.head(8).itertuples():
        print(f"\n#{r.rank} 综合 {r.composite_v2:.4f} | {r.n_strains}株 轴{r.n_axes}/3[{r.axes}] "
              f"| 多样性ρ均值 {r.diversity_mean:+.2f} 效应g {r.effect_mean_g:+.2f} 可培养 {r.culturability_mean:.2f}")
        print("    " + " + ".join(m.replace("_", " ") for m in r.members.split("; ")))

    # ---- compare with v1 ----
    v1p = PR / "synergistic_lean_combinations_20260625.csv"
    cmp = {}
    if v1p.is_file():
        v1 = pd.read_csv(v1p)
        v1_top = set(v1.head(1).members.iloc[0].split("; "))
        v2_top = set(res.head(1).members.iloc[0].split("; "))
        cmp = {"v1_top1": sorted(v1_top), "v2_top1": sorted(v2_top),
               "shared": sorted(v1_top & v2_top),
               "dropped_from_v1": sorted(v1_top - v2_top), "new_in_v2": sorted(v2_top - v1_top)}
        print("\n=== v1 vs v2 首选组合对比 ===")
        print("  v1:", ", ".join(x.replace("_", " ") for x in sorted(v1_top)))
        print("  v2:", ", ".join(x.replace("_", " ") for x in sorted(v2_top)))
        print("  保留:", ", ".join(x.replace("_", " ") for x in cmp["shared"]) or "无")
        print("  剔除:", ", ".join(x.replace("_", " ") for x in cmp["dropped_from_v1"]) or "无")
        print("  新增:", ", ".join(x.replace("_", " ") for x in cmp["new_in_v2"]) or "无")

    (OUT / "synergistic_v2_summary_20260625.json").write_text(json.dumps({
        "version": 2, "weights": W, "penalties": PENALTY,
        "pool_source": "we_healthy robust lean-enriched (T2D-excluded, age/sex-matched, FDR+meta)",
        "pool_size": int(len(pool)), "n_combinations": int(len(res)),
        "removed_from_v1": {"bsh_cholesterol_weight": 0.16,
                            "reason": "AUC 0.517 (P=0.85); cross-genus 0.027; adding it degraded 0.878->0.798"},
        "top1": res.head(1).to_dict("records")[0], "v1_vs_v2": cmp},
        indent=2, ensure_ascii=False), encoding="utf-8")
    print("\nwrote", (OUT / "synergistic_lean_combinations_v2_20260625.csv").relative_to(ROOT))


if __name__ == "__main__":
    main()
