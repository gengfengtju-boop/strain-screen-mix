"""From the lean(no-IR)-vs-obese differential abundance, (1) export the full
trusted differential list (both directions), then (2) screen the lean-enriched
species by functional relevance, mechanism complementarity and culturability,
to produce data-driven candidate targets for weight-loss combination design.
"""
from __future__ import annotations

import re
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
PR = ROOT / "results/prediction_results"

# culturability priors for notable taxa (named isolate availability / fastidiousness)
CULT = {
    "Akkermansia_muciniphila": ("culturable_commercial", 1.0),
    "Faecalibacterium_prausnitzii": ("fastidious_anaerobe", 0.7),
    "Roseburia": ("culturable_anaerobe", 0.85),
    "Eubacterium": ("culturable_anaerobe", 0.85),
    "Butyrivibrio": ("culturable_anaerobe", 0.8),
    "Odoribacter": ("culturable_anaerobe", 0.8),
    "Barnesiella": ("culturable_anaerobe", 0.8),
    "Alistipes": ("culturable_anaerobe", 0.8),
    "Bacteroides": ("culturable_easy", 0.95),
    "Parabacteroides": ("culturable_easy", 0.9),
    "Oscillibacter": ("fastidious_anaerobe", 0.6),
    "Coprococcus": ("culturable_anaerobe", 0.8),
    "Methanobrevibacter": ("archaea_special_culture", 0.4),
    "Clostridium": ("culturable_anaerobe", 0.8),
}


def culturability(species: str, genus: str):
    if re.search(r"CAG|_sp_CAG|unclassified|_bacterium_[A-Z0-9]|_sp_$", species) or species.endswith("_sp"):
        return ("uncultured_or_MAG", 0.2)
    if species in CULT:
        return CULT[species]
    if genus in CULT:
        return CULT[genus]
    if re.search(r"_sp_", species):
        return ("uncultured_or_MAG", 0.25)
    return ("named_isolate_likely", 0.65)


def main() -> None:
    r = pd.read_csv(PR / "lean_vs_obese_differential_abundance_20260625.csv")
    trusted = r[r["consistency"] >= 0.70].copy()
    trusted = trusted.sort_values(["direction", "abs_median_diff_pp"], ascending=[True, False])
    trusted.to_csv(PR / "lean_vs_obese_trusted_differential_20260625.csv", index=False)

    guild = pd.read_csv(ROOT / "data/strain_genome/genus_functional_guild_reference_20260613.csv").set_index("genus")
    le = trusted[trusted["direction"] == "lean_enriched"].copy()
    le["genus"] = le["species"].str.split("_").str[0]

    rows = []
    for _, x in le.iterrows():
        g = x["genus"]
        gr = guild.loc[g] if g in guild.index else None
        bsh = int(gr["bsh_potential"]) if gr is not None else 0
        but = int(gr["butyrate_scfa_potential"]) if gr is not None else 0
        pro = int(gr["propionate_potential"]) if gr is not None else 0
        muc = int(gr["mucin_interaction"]) if gr is not None else 0
        lac = int(gr["lactate_acetate"]) if gr is not None else 0
        adverse = bool(pd.notna(gr["adverse_mechanism_flag"])) if gr is not None else False
        mech = str(gr["obesity_mechanism"]) if gr is not None else ""
        cult_class, cult_score = culturability(x["species"], g)

        # complementarity: axes NOT covered by current Lactobacillus/Bifidobacterium
        # combos (those cover BSH + lactate); reward butyrate / propionate / mucin.
        complement = (1.0 if but > 0 else 0) + (0.7 if muc > 0 else 0) + (0.5 if pro > 0 else 0)
        # functional relevance: favorable SCFA/mucin biology, penalise adverse
        functional = min(1.0, 0.5 * (but > 0) + 0.4 * (muc > 0) + 0.2 * (pro > 0) + 0.15 * (bsh > 0)) - (0.5 if adverse else 0)
        functional = max(0.0, functional)
        # effect: standardized separation
        eff = min(1.0, abs(float(x["pooled_cohens_d"])) / 0.3)
        composite = round(0.32 * eff + 0.28 * complement / 2.2 + 0.20 * functional + 0.20 * cult_score, 3)

        rows.append({
            "species": x["species"], "genus": g,
            "median_abund_diff_pp": x["median_abund_diff_pp"],
            "median_log2fc": x["median_log2fc"], "cohens_d": x["pooled_cohens_d"],
            "consistency": f"{x['studies_consistent']}/15",
            "butyrate": but, "propionate": pro, "mucin": muc, "bsh": bsh, "lactate": lac,
            "adverse_flag": adverse, "obesity_mechanism": mech,
            "culturability_class": cult_class, "culturability_score": cult_score,
            "complementarity_score": round(complement, 2),
            "functional_score": round(functional, 2),
            "effect_score": round(eff, 2),
            "composite_screen_score": composite,
        })
    out = pd.DataFrame(rows).sort_values("composite_screen_score", ascending=False)
    out.to_csv(PR / "lean_enriched_screened_candidates_20260625.csv", index=False)

    print(f"trusted differential: {len(trusted)} (lean {int((trusted.direction=='lean_enriched').sum())}, "
          f"obese {int((trusted.direction=='obese_enriched').sum())})")
    print("\n=== screened lean-enriched candidates (top 12 by composite) ===")
    cols = ["species", "cohens_d", "butyrate", "mucin", "propionate",
            "culturability_class", "composite_screen_score"]
    for _, x in out.head(12).iterrows():
        flags = "".join(["B" if x["butyrate"] else "-", "M" if x["mucin"] else "-",
                         "P" if x["propionate"] else "-"])
        print(f"  {x['species'][:34]:34} d={x['cohens_d']:+.2f} 机制[{flags}] "
              f"{x['culturability_class']:22} score={x['composite_screen_score']:.3f}")
    print("\nwrote", (PR / "lean_vs_obese_trusted_differential_20260625.csv").relative_to(ROOT))
    print("wrote", (PR / "lean_enriched_screened_candidates_20260625.csv").relative_to(ROOT))


if __name__ == "__main__":
    main()
