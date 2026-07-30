"""v3: a separate prediction method for FOOD-GRADE strains.

Why a separate method is required
---------------------------------
Food-grade probiotics cannot be scored by the cohort pipeline used for resident
gut taxa:
  * most Lactobacillus-family species never reach 10% prevalence in the gut
    cohorts, so no differential-abundance evidence exists for them at all;
  * within the food-grade catalogue every strain is identical on the axes that
    discriminated lean-associated residents (butyrate 0, propionate 0, mucin 0) -
    they are all lactate/acetate producers, so those axes cannot rank them.

So v3 scores STRAIN PROPERTIES only, using criteria transferred from what the
lean-group analysis taught us, combined with the bottom-up catalogue
(safety tier, clinical evidence, culturability).

Six axes (weights sum to 1.0; the last is a penalty)
  1. cross-feeding donor capacity   0.22  lactate/acetate output feeds resident
                                          butyrate/propionate producers - the
                                          "cooperative" ecology that
                                          characterised lean subjects. Stated as
                                          a mechanistic hypothesis, not validated
                                          here.
  2. bile-acid modulation (BSH)      0.15  the one legitimate place for BSH: the
                                          SUPPLEMENTED-strain paradigm. BSH was
                                          shown to fail as a resident-ecology
                                          lean predictor, but the literature
                                          supports BSH -> cholesterol for
                                          supplemented lactobacilli.
  3. safety tier                     0.22  QPS/GRAS vs strain-level review needed
  4. clinical evidence               0.15  human-trial precedent in the catalogue
  5. industrial feasibility          0.14  culturability + stability (spores and
                                          yeasts are manufacturing-robust; this
                                          is deliberately kept separate from the
                                          ecological spore-former concern)
  6. obesity-signature penalty      -0.12  oral-origin genus (validated
                                          obese-enriched in Western Europe) and
                                          sugar-degradation-dominant profile

Cohort evidence is deliberately EXCLUDED from the score, per the design brief.
It is reported separately as a "cohort contradiction flag" for any strain that is
significantly obese-enriched in any region, because ignoring such a signal would
be imprudent even though it does not enter the ranking.
"""
from __future__ import annotations

import io
import json
from itertools import combinations
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
PR = ROOT / "results/prediction_results"
OUT = ROOT / "results/combination_recommendations"

W = {"cross_feeding": 0.22, "bile_acid": 0.15, "safety": 0.22,
     "clinical": 0.15, "industrial": 0.14}
PEN = {"obesity_signature": 0.12}

# industrial robustness prior (fermentation yield, freeze-drying / shelf stability)
INDUSTRIAL = {
    "Bacillus": 1.00,            # spore-forming, room-temperature stable
    "Saccharomyces": 0.95,       # yeast, very robust
    "Lactiplantibacillus": 0.90, "Lacticaseibacillus": 0.90, "Lactobacillus": 0.85,
    "Limosilactobacillus": 0.85, "Lactococcus": 0.85, "Pediococcus": 0.85,
    "Bifidobacterium": 0.60,     # oxygen-sensitive, harder to stabilise
    "Streptococcus": 0.75,
}
ORAL_GENERA = {"Streptococcus"}
# genera whose carbohydrate metabolism is dominated by simple-sugar degradation,
# the profile enriched in obese subjects in the pathway analysis
SUGAR_DOMINANT = {"Streptococcus", "Lactococcus", "Pediococcus"}


def main():
    cat = pd.read_csv(ROOT / "results/candidate_strain_scores/strain_screening_catalog_functional_20260613.csv")
    f = cat[cat.category == "food_grade_probiotic"].copy()
    f["genus"] = f.species.str.split("_").str[0]

    # ---------- axis scores from strain properties only ----------
    f["cross_feeding"] = (f.lactate_acetate / 2.0).clip(0, 1)
    f["bile_acid"] = (f.bsh_potential / 2.0).clip(0, 1)
    f["safety"] = np.where(f.safety_tier == "qps_gras_lower_barrier", 1.0,
                           np.where(f.safety_tier == "requires_strain_level_safety_review", 0.25, 0.5))
    f["clinical"] = np.where(f.clinical_evidence == "yes", 1.0, 0.35)
    f["industrial"] = f.genus.map(INDUSTRIAL).fillna(0.6)
    f["oral_origin"] = f.genus.isin(ORAL_GENERA).astype(int)
    f["sugar_dominant"] = f.genus.isin(SUGAR_DOMINANT).astype(int)
    f["obesity_signature"] = (0.6 * f.oral_origin + 0.4 * f.sugar_dominant).clip(0, 1)

    f["v3_score"] = (W["cross_feeding"] * f.cross_feeding + W["bile_acid"] * f.bile_acid
                     + W["safety"] * f.safety + W["clinical"] * f.clinical
                     + W["industrial"] * f.industrial
                     - PEN["obesity_signature"] * f.obesity_signature).round(4)

    # ---------- cohort contradiction flag (reported, NOT scored) ----------
    reg = pd.read_csv(PR / "multiregion/regional_differential_all.csv")
    bad = reg[(reg.fdr < 0.05) & (reg.direction == "obese_enriched")]
    good = reg[(reg.fdr < 0.05) & (reg.direction == "lean_enriched")]
    flag, note = {}, {}
    for sp in f.species:
        b = bad[bad.species == sp]; g = good[good.species == sp]
        if len(b):
            flag[sp] = "队列反证：肥胖富集"
            note[sp] = "; ".join(f"{r.region} FC={r.fold_change_obese_vs_lean:.2f}" for r in b.itertuples())
        elif len(g):
            flag[sp] = "队列支持：瘦人富集"
            note[sp] = "; ".join(f"{r.region} FC={r.fold_change_obese_vs_lean:.2f}" for r in g.itertuples())
        elif sp in set(reg.species):
            flag[sp] = "队列受检但不显著"; note[sp] = ""
        else:
            flag[sp] = "队列无数据（不可得）"; note[sp] = ""
    f["cohort_flag"] = f.species.map(flag)
    f["cohort_detail"] = f.species.map(note)

    f = f.sort_values("v3_score", ascending=False).reset_index(drop=True)
    keep = ["species", "genus", "v3_score", "cross_feeding", "bile_acid", "safety", "clinical",
            "industrial", "obesity_signature", "cohort_flag", "cohort_detail",
            "safety_tier", "clinical_evidence", "priority_tier"]
    f[keep].to_csv(OUT / "foodgrade_v3_strain_scores_20260625.csv", index=False, encoding="utf-8-sig")

    print(f"=== v3 食源菌评分（{len(f)} 株，纯菌株性质，不含队列）===")
    print(f"{'物种':34}{'v3':>7}{'交叉喂养':>9}{'BSH':>6}{'安全':>6}{'临床':>6}{'工业':>6}  队列旗标")
    for r in f.head(18).itertuples():
        print(f"{r.species[:33]:34}{r.v3_score:>7.3f}{r.cross_feeding:>9.1f}{r.bile_acid:>6.1f}"
              f"{r.safety:>6.2f}{r.clinical:>6.2f}{r.industrial:>6.2f}  {r.cohort_flag}")

    # ---------- combinations ----------
    # exclude strains needing strain-level safety review, and those with a cohort
    # contradiction, from the buildable pool (reported separately)
    pool = f[(f.safety >= 0.5) & (f.cohort_flag != "队列反证：肥胖富集")].reset_index(drop=True)
    print(f"\n可建组合池: {len(pool)} 株（排除需菌株级安全审查者与队列反证者）")
    recs = []
    for size in (2, 3, 4):
        for cb in combinations(list(pool.index), size):
            rows = pool.loc[list(cb)]
            gdiv = rows.genus.nunique() / size
            # reward complementary property profiles: one strong BSH + one strong
            # cross-feeder + genus spread
            comp = (int((rows.bile_acid >= 1.0).any()) + int((rows.cross_feeding >= 1.0).any())
                    + int(rows.genus.nunique() >= 2)) / 3.0
            score = 0.72 * rows.v3_score.mean() + 0.18 * comp + 0.10 * gdiv
            recs.append({"members": "; ".join(rows.species), "n_strains": size,
                         "mean_v3": round(float(rows.v3_score.mean()), 4),
                         "has_strong_bsh": bool((rows.bile_acid >= 1.0).any()),
                         "has_strong_crossfeeder": bool((rows.cross_feeding >= 1.0).any()),
                         "n_genera": int(rows.genus.nunique()),
                         "clinical_members": int((rows.clinical >= 1.0).sum()),
                         "cohort_supported_members": int(rows.cohort_flag.eq("队列支持：瘦人富集").sum()),
                         "composite_v3": round(float(score), 4)})
    C = pd.DataFrame(recs).sort_values("composite_v3", ascending=False).reset_index(drop=True)
    C.insert(0, "rank", range(1, len(C) + 1))
    C.to_csv(OUT / "foodgrade_v3_combinations_20260625.csv", index=False, encoding="utf-8-sig")

    print("\n=== v3 食源菌组合 Top 8 ===")
    for r in C.head(8).itertuples():
        print(f"  #{r.rank} 综合 {r.composite_v3:.4f} | {r.n_strains}株/{r.n_genera}属 "
              f"| 强BSH={'有' if r.has_strong_bsh else '无'} 强交叉喂养={'有' if r.has_strong_crossfeeder else '无'} "
              f"| 临床证据成员 {r.clinical_members} 队列支持 {r.cohort_supported_members}")
        print("      " + " + ".join(x.replace("_", " ") for x in r.members.split("; ")))

    excluded = f[(f.safety < 0.5) | (f.cohort_flag == "队列反证：肥胖富集")]
    print(f"\n=== 被排除的 {len(excluded)} 株 ===")
    for r in excluded.itertuples():
        why = []
        if r.safety < 0.5: why.append("需菌株级安全审查")
        if r.cohort_flag == "队列反证：肥胖富集": why.append(f"队列反证({r.cohort_detail})")
        print(f"  {r.species[:34]:34} {' / '.join(why)}")

    io.open(OUT / "foodgrade_v3_summary_20260625.json", "w", encoding="utf-8").write(json.dumps({
        "method": "v3 food-grade: strain properties only; cohort evidence reported as a flag, not scored",
        "weights": W, "penalty": PEN,
        "n_food_grade": int(len(f)), "buildable_pool": int(len(pool)), "excluded": int(len(excluded)),
        "n_combinations": int(len(C)),
        "top1": C.iloc[0].to_dict(),
        "cohort_flag_counts": f.cohort_flag.value_counts().to_dict(),
        "limitation": "cross-feeding and industrial axes are mechanistic/engineering priors, not validated against fat-loss outcomes here",
    }, indent=2, ensure_ascii=False))
    print("\nwrote", (OUT / "foodgrade_v3_combinations_20260625.csv").relative_to(ROOT))


if __name__ == "__main__":
    main()
