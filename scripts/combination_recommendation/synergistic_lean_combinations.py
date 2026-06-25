"""Screen synergistic fat-loss strain combinations from the lean-enriched pool.

Predictive basis: every member is a lean(no-IR)-enriched species whose direction
is consistent across >=11/15 studies (data-driven). "Synergy" is operationalised
as MECHANISM COMPLEMENTARITY - a combination is rewarded for covering distinct
functional axes (butyrate, propionate, mucin/barrier, BSH/cholesterol) rather
than stacking redundant strains. Combinations are scored on:
  - strain properties (culturability; pro-inflammatory taxa already excluded)
  - fat-loss potential (lean-vs-obese effect size x SCFA/barrier mechanism)
  - cholesterol-lowering ability (bile salt hydrolase, BSH)
  - mechanism complementarity (axis coverage) and genus diversity
"""
from __future__ import annotations

from itertools import combinations
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
PR = ROOT / "results/prediction_results"
DMAX = 0.32  # max observed Cohen's d for normalisation


def per_strain(s: pd.DataFrame) -> pd.DataFrame:
    s = s.copy()
    eff = (s["cohens_d"].clip(lower=0) / DMAX).clip(0, 1)
    scfa = (1.0 * (s["butyrate"] > 0) + 0.6 * (s["propionate"] > 0) + 0.7 * (s["mucin"] > 0)).clip(0, 1.4) / 1.4
    s["fat_loss_potential"] = (0.45 * eff + 0.55 * scfa).round(3)
    s["cholesterol_potential"] = (s["bsh"] / 2.0).round(3)   # BSH 0/1/2 -> 0/0.5/1.0
    s["strain_quality"] = s["culturability_score"].round(3)
    s["effort_norm"] = eff.round(3)
    return s


def main() -> None:
    s = pd.read_csv(PR / "lean_enriched_screened_candidates_20260625.csv")
    pool = s[(~s["culturability_class"].isin(["uncultured_or_MAG", "archaea_special_culture"]))
             & (~s["adverse_flag"])].copy()
    pool = per_strain(pool)
    # base merit to keep the enumeration to strong, well-characterised members
    pool["base_merit"] = (0.5 * pool["fat_loss_potential"] + 0.25 * pool["strain_quality"]
                          + 0.15 * pool["effort_norm"] + 0.10 * pool["cholesterol_potential"])
    # curated pool: top members, but guarantee axis representatives are present
    top = pool.sort_values("base_merit", ascending=False).head(13)
    must = pool[(pool["butyrate"] > 0) | (pool["bsh"] >= 2)].sort_values("base_merit", ascending=False).head(3)
    cur = pd.concat([top, must]).drop_duplicates("species").reset_index(drop=True)

    def axes(rows):
        return {"butyrate": int((rows["butyrate"] > 0).any()),
                "propionate": int((rows["propionate"] > 0).any()),
                "mucin": int((rows["mucin"] > 0).any()),
                "bsh": int((rows["bsh"] > 0).any())}

    recs = []
    idx = list(cur.index)
    for size in (3, 4, 5):
        for combo in combinations(idx, size):
            rows = cur.loc[list(combo)]
            ax = axes(rows)
            n_axes = sum(ax.values())
            if n_axes < 3:            # require genuine complementarity
                continue
            synergy = n_axes / 4.0
            fat = rows["fat_loss_potential"].mean()
            chol = rows["bsh"].max() / 2.0
            qual = rows["strain_quality"].mean()
            eff = rows["effort_norm"].mean()
            gdiv = rows["genus"].nunique() / size
            score = (0.28 * synergy + 0.26 * fat + 0.16 * chol
                     + 0.14 * qual + 0.10 * eff + 0.06 * gdiv)
            recs.append({
                "members": "; ".join(rows["species"]),
                "n_strains": size, "n_axes_covered": n_axes,
                "axes": "+".join(k for k, v in ax.items() if v),
                "synergy": round(synergy, 2),
                "fat_loss": round(float(fat), 3),
                "cholesterol": round(float(chol), 3),
                "strain_quality": round(float(qual), 3),
                "mean_effect_d": round(float(rows["cohens_d"].mean()), 3),
                "genus_diversity": round(float(gdiv), 2),
                "composite": round(float(score), 4),
            })
    res = pd.DataFrame(recs).sort_values("composite", ascending=False)
    # de-duplicate near-identical supersets: keep best per member-set signature
    res = res.drop_duplicates("members").reset_index(drop=True)
    res.insert(0, "rank", range(1, len(res) + 1))
    res.to_csv(PR / "synergistic_lean_combinations_20260625.csv", index=False)
    cur[["species", "genus", "cohens_d", "median_abund_diff_pp", "butyrate",
         "propionate", "mucin", "bsh", "fat_loss_potential", "cholesterol_potential",
         "strain_quality", "culturability_class"]].to_csv(
        PR / "synergistic_combination_pool_20260625.csv", index=False)

    print(f"curated pool: {len(cur)} strains | scored combinations: {len(res)}")
    print("\n=== Top 8 synergistic fat-loss combinations ===")
    for _, r in res.head(8).iterrows():
        print(f"\n#{int(r['rank'])} 综合 {r['composite']:.3f} | 轴 {r['n_axes_covered']}/4 [{r['axes']}] "
              f"| 减脂 {r['fat_loss']:.2f} 降胆固醇 {r['cholesterol']:.2f} 菌株性质 {r['strain_quality']:.2f}")
        print("    " + " + ".join(m.replace("_", " ") for m in r["members"].split("; ")))
    print("\nwrote", (PR / "synergistic_lean_combinations_20260625.csv").relative_to(ROOT))


if __name__ == "__main__":
    main()
