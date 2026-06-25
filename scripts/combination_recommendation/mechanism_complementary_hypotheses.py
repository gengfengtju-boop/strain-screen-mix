"""Mechanism-complementary combination DESIGN hypotheses from the safety-eligible pool.

Generates multi-strain formulation hypotheses that cover complementary metabolic guilds
(lactate/BSH donor + butyrate producer + propionate/mucin specialist) and exploit known
cross-feeding (lactate -> butyrate via Anaerostipes; fiber/mucin -> propionate). This is a
PRECLINICAL DESIGN axis (the recommender's combination_design_score), NOT efficacy: predicted
response stays empty and combination_ranking_enabled remains false. Every member is safety
'pending' (needs the step-2 genome screen).

    PYTHONPATH=src python scripts/combination_recommendation/mechanism_complementary_hypotheses.py
"""
from __future__ import annotations

from itertools import combinations
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
ELIG = ROOT / "results/candidate_strain_scores/combination_safety_gate_eligibility_20260613.csv"
OUT = ROOT / "results/combination_recommendations/mechanism_complementary_hypotheses_20260613.csv"

# guild anchors hand-picked from the eligible pool (best characterized representative per niche)
ANCHORS = {
    # lactate/BSH donors (QPS, deliverable; also cross-feeding lactate donors)
    "Bifidobacterium_longum": "lactate_bsh_donor",
    "Lactobacillus_acidophilus": "lactate_bsh_donor",
    "Lacticaseibacillus_rhamnosus": "lactate_bsh_donor",
    # butyrate producers (Anaerostipes is a lactate->butyrate cross-feeder)
    "Anaerostipes_hadrus": "butyrate_crossfeeder",
    "Faecalibacterium_prausnitzii": "butyrate",
    "Roseburia_intestinalis": "butyrate",
    "Intestinimonas_butyriciproducens": "butyrate",
    # propionate / mucin specialists
    "Phascolarctobacterium_faecium": "propionate",
    "Parabacteroides_distasonis": "propionate",
    "Akkermansia_muciniphila": "mucin_propionate",
}
NICHE = {"lactate_bsh_donor": "lactate/BSH", "butyrate_crossfeeder": "butyrate",
         "butyrate": "butyrate", "propionate": "propionate", "mucin_propionate": "mucin+propionate"}


def main() -> None:
    pool = pd.read_csv(ELIG)
    pool = pool[pool["species"].isin(ANCHORS)].copy()
    pool["anchor_role"] = pool["species"].map(ANCHORS)
    info = pool.set_index("species")

    rows = []
    for size in (3, 4):
        for combo in combinations(ANCHORS, size):
            niches = {NICHE[ANCHORS[s]] for s in combo}
            genera = {s.split("_")[0] for s in combo}
            if len(genera) < size:          # distinct genera only
                continue
            if len(niches) < 3:             # require >=3 complementary mechanisms
                continue
            crossfeed = ("lactate/BSH" in niches and
                         any(ANCHORS[s] == "butyrate_crossfeeder" for s in combo))
            has_qps = any(info.loc[s, "safety_risk_class"] == "low_qps_history" for s in combo)
            has_protective = any(info.loc[s, "obesity_signal"] == "depleted_in_obesity_protective" for s in combo)
            # DESIGN score (mechanism complementarity), NOT efficacy
            design = len(niches) + 1.5 * crossfeed + 0.5 * has_qps + 0.5 * has_protective + 0.25 * len(genera)
            rows.append({
                "members": "; ".join(combo),
                "n_strains": size,
                "mechanisms_covered": "; ".join(sorted(niches)),
                "n_mechanisms": len(niches),
                "lactate_to_butyrate_crossfeeding": "yes" if crossfeed else "no",
                "includes_qps_deliverable_anchor": "yes" if has_qps else "no",
                "includes_depleted_protective_taxon": "yes" if has_protective else "no",
                "design_complementarity_score": round(design, 2),
                "predicted_response_score": "",  # GATED: efficacy unknown
                "ranking_type": "preclinical_mechanism_hypothesis_not_efficacy",
                "combination_safety_gate": "pending_all_members_need_genome_screen",
                "rationale": f"covers {len(niches)} SCFA/bile niches"
                             + ("; lactate->butyrate cross-feeding" if crossfeed else "")
                             + ("; includes QPS deliverable strain" if has_qps else "")
                             + ("; restores depleted protective taxon" if has_protective else ""),
            })

    out = pd.DataFrame(rows).sort_values("design_complementarity_score", ascending=False)
    out.insert(0, "hypothesis_id", [f"MECHCOMBO_{i:03d}" for i in range(1, len(out) + 1)])
    OUT.parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(OUT, index=False)

    print(f"Mechanism-complementary combination hypotheses: {len(out)} -> {OUT.name}\n")
    print("Top 8 (by design complementarity, NOT efficacy):")
    for _, r in out.head(8).iterrows():
        print(f"  [{r['hypothesis_id']}] {r['members']}")
        print(f"       {r['mechanisms_covered']} | crossfeed={r['lactate_to_butyrate_crossfeeding']} "
              f"QPS={r['includes_qps_deliverable_anchor']} protective={r['includes_depleted_protective_taxon']} "
              f"| design={r['design_complementarity_score']}")
    print("\nGATE: predicted_response empty; combination_ranking_enabled stays FALSE. These are "
          "mechanism design hypotheses for wet-lab/clinical testing, not efficacy predictions.")


if __name__ == "__main__":
    main()
