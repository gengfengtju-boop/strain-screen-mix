"""Build a 100-200 entry strain screening catalog (probiotics + human-derived non-pathogens).

The clinical-evidence candidate list is tiny (~10) because it only holds strains tested in
curated obesity RCTs. The SCREENING universe is much larger: every human-derived gut species
the obesity model sees (>=10% prevalence) plus food-grade probiotics. This assembles them with
obesity signal (SHAP), genome functional potential, safety tier, and a priority tier.

    PYTHONPATH=src python scripts/strain_annotation/build_strain_screening_catalog.py
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd
import yaml

ROOT = Path(__file__).resolve().parents[2]
SHAP = ROOT / "results/SHAP_results/obesity_classifier_shap_importance_20260613.csv"
UNIVERSE = ROOT / "config/species_universe.yaml"
GENOME = ROOT / "data/strain_genome/strain_genomic_functional_features.csv"
CAND = ROOT / "results/candidate_strain_scores/evidence_derived_candidate_strain_scores.csv"
OUT = ROOT / "results/candidate_strain_scores/strain_screening_catalog_20260613.csv"

# genera needing strain-level safety review (contain pathogens/opportunists; some members
# ARE safe probiotics e.g. E. coli Nissle, E. faecium, S. thermophilus -> review, not exclude)
REVIEW_GENERA = {
    "Escherichia", "Klebsiella", "Haemophilus", "Fusobacterium", "Streptococcus",
    "Enterococcus", "Clostridioides", "Shigella", "Salmonella", "Campylobacter",
    "Helicobacter", "Veillonella", "Actinomyces", "Morganella", "Proteus",
}
FOOD_GRADE_GENERA = {
    "Lactobacillus", "Lacticaseibacillus", "Lactiplantibacillus", "Limosilactobacillus",
    "Bifidobacterium", "Streptococcus", "Lactococcus", "Pediococcus", "Bacillus", "Saccharomyces",
}


def main() -> None:
    sig = pd.read_csv(SHAP)
    sig["genus"] = sig["species"].str.split("_").str[0]
    genome = pd.read_csv(GENOME).set_index("genus")
    universe = yaml.safe_load(UNIVERSE.read_text(encoding="utf-8"))
    ngp_genera = set(universe.get("human_derived_ngp", {}).keys())
    clinical = pd.read_csv(CAND)
    clinical_species = {f"{r.genus}_{str(r.species).split()[0]}" for r in clinical.itertuples()}

    rows = []
    # --- source 1: every human-derived gut species the obesity model uses ---
    for _, s in sig.iterrows():
        genus = s["genus"]
        protective = s["direction"] == "higher_abundance_lowers_obesity"
        review = genus in REVIEW_GENERA
        is_food = genus in FOOD_GRADE_GENERA
        is_ngp = genus in ngp_genera
        rows.append({
            "species": s["species"], "genus": genus,
            "category": "food_grade_probiotic" if is_food else
                        "human_derived_ngp" if is_ngp else "human_derived_commensal",
            "source": "obesity_microbiome_signature",
            "obesity_signal": "depleted_in_obesity_protective" if protective else "enriched_in_obesity",
            "shap_importance": round(float(s["mean_abs_shap"]), 4),
            "bsh_potential": genome.loc[genus, "bsh_potential"] if genus in genome.index else "",
            "butyrate_scfa_potential": genome.loc[genus, "butyrate_scfa_potential"] if genus in genome.index else "",
            "mucin_interaction": genome.loc[genus, "mucin_interaction"] if genus in genome.index else "",
            "safety_tier": "requires_strain_level_safety_review" if review else
                           "qps_gras_lower_barrier" if is_food else
                           "requires_genome_safety_lbp" if is_ngp else "requires_genome_safety_review",
            "clinical_evidence": "yes" if s["species"] in clinical_species else "screening_only",
        })

    # --- source 2: food-grade probiotic species not captured above (low gut prevalence) ---
    seen = {r["species"] for r in rows}
    for genus, species_list in universe.get("food_grade_probiotics", {}).items():
        for sp in species_list:
            key = f"{genus}_{sp}"
            if key in seen:
                continue
            rows.append({
                "species": key, "genus": genus, "category": "food_grade_probiotic",
                "source": "species_universe_food_grade",
                "obesity_signal": "not_in_gut_signature_low_prevalence", "shap_importance": "",
                "bsh_potential": genome.loc[genus, "bsh_potential"] if genus in genome.index else "",
                "butyrate_scfa_potential": genome.loc[genus, "butyrate_scfa_potential"] if genus in genome.index else "",
                "mucin_interaction": genome.loc[genus, "mucin_interaction"] if genus in genome.index else "",
                "safety_tier": "requires_strain_level_safety_review" if genus in REVIEW_GENERA
                               else "qps_gras_lower_barrier",
                "clinical_evidence": "yes" if key in clinical_species else "screening_only",
            })

    cat = pd.DataFrame(rows).drop_duplicates("species")

    # priority tier
    def tier(r):
        if r["clinical_evidence"] == "yes":
            return "A_clinical_evidence"
        if r["safety_tier"] == "requires_strain_level_safety_review":
            return "C_pathogen_genus_review"
        if r["obesity_signal"] == "depleted_in_obesity_protective":
            return "B_protective_screening"
        if r["category"] == "food_grade_probiotic":
            return "B_food_grade_screening"
        return "C_screening_hypothesis"
    cat["priority_tier"] = cat.apply(tier, axis=1)
    cat = cat.sort_values(["priority_tier", "shap_importance"], ascending=[True, False])
    OUT.parent.mkdir(parents=True, exist_ok=True)
    cat.to_csv(OUT, index=False)

    print(f"Strain screening catalog: {len(cat)} entries -> {OUT.name}")
    print("\nby priority tier:")
    print(cat["priority_tier"].value_counts().to_string())
    print("\nby category:")
    print(cat["category"].value_counts().to_string())
    print("\nby safety tier:")
    print(cat["safety_tier"].value_counts().to_string())
    print("\nTier B protective screening (top 12 by SHAP):")
    b = cat[cat["priority_tier"] == "B_protective_screening"].head(12)
    print(b[["species", "category", "shap_importance"]].to_string(index=False))


if __name__ == "__main__":
    main()
