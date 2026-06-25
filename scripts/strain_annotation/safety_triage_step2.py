"""Step 2 — taxonomy/QPS knowledge-based safety triage of the screening catalog.

IMPORTANT: this is a knowledge PRIOR (EFSA QPS list + established clinical microbiology),
NOT genome-level screening. It cannot detect strain-specific AMR genes, mobile elements, or
virulence factors -- those require downloading each genome and running AMRFinderPlus / abricate
(CARD, VFDB) / ResFinder, which is a separate bioinformatics pipeline. Every non-QPS taxon
stays `requires_genome_level_confirmation`. Output: a first-pass safety stratification to
prioritize which actionable (isolate-genome) candidates go to real screening first.

    PYTHONPATH=src python scripts/strain_annotation/safety_triage_step2.py
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
CAT = ROOT / "results/candidate_strain_scores/strain_screening_catalog_genomes_20260613.csv"
OUT = ROOT / "results/candidate_strain_scores/strain_screening_catalog_safety_20260613.csv"

# EFSA QPS genera (presumed safe with qualifications; food/feed chain history)
QPS_GENERA = {
    "Lactobacillus", "Lacticaseibacillus", "Lactiplantibacillus", "Limosilactobacillus",
    "Ligilactobacillus", "Lacticaseibacillus", "Bifidobacterium", "Lactococcus",
    "Leuconostoc", "Pediococcus", "Propionibacterium", "Acidipropionibacterium",
    "Saccharomyces",
}
QPS_SPECIES = {  # only these species of an otherwise non-QPS genus are QPS
    "Streptococcus_thermophilus", "Bacillus_subtilis", "Bacillus_coagulans",
    "Bacillus_licheniformis", "Bacillus_amyloliquefaciens", "Bacillus_velezensis",
}
# genera containing pathogens / opportunists / AMR reservoirs -> strain-level review mandatory
ELEVATED_GENERA = {
    "Escherichia", "Klebsiella", "Enterobacter", "Salmonella", "Shigella", "Proteus",
    "Morganella", "Citrobacter", "Serratia", "Enterococcus", "Staphylococcus",
    "Haemophilus", "Fusobacterium", "Campylobacter", "Helicobacter", "Clostridioides",
    "Bilophila", "Veillonella", "Streptococcus",  # Streptococcus minus thermophilus
}
AMR_RESERVOIR_GENERA = {"Enterococcus", "Escherichia", "Klebsiella", "Staphylococcus",
                        "Enterobacter", "Citrobacter", "Serratia"}
# species-level concerns inside otherwise-benign genera
ELEVATED_SPECIES = {"Bacteroides_fragilis", "Eggerthella_lenta", "Ruminococcus_gnavus"}
# human-derived taxa with live-biotherapeutic / human-trial precedent (de-risked, still needs genome check)
LBP_PRECEDENT = {
    "Akkermansia_muciniphila", "Faecalibacterium_prausnitzii", "Anaerobutyricum_hallii",
    "Eubacterium_hallii", "Clostridium_butyricum", "Christensenella_minuta",
    "Roseburia_intestinalis", "Parabacteroides_distasonis", "Anaerostipes_caccae",
    "Hafnia_alvei",
}
# Clostridium genus is ambiguous (pathogens + beneficial); flag for species-level care
AMBIGUOUS_GENERA = {"Clostridium"}


def _triage(species: str, genus: str) -> dict[str, object]:
    flags = []
    if genus in AMR_RESERVOIR_GENERA:
        flags.append("amr_reservoir_genus")
    if species in ELEVATED_SPECIES:
        flags.append("species_opportunist_concern")
    if genus in AMBIGUOUS_GENERA:
        flags.append("genus_contains_pathogens_species_level_care")

    if species in QPS_SPECIES or genus in QPS_GENERA:
        risk = "low_qps_history"
        action = "lower_barrier; strain-level genome QC still recommended"
    elif species in ELEVATED_SPECIES or genus in ELEVATED_GENERA:
        risk = "elevated_pathogen_or_amr_genus"
        action = "strain-level review MANDATORY; exclude unless a documented safe strain"
    elif species in LBP_PRECEDENT:
        risk = "moderate_lbp_precedent"
        action = "human-trial precedent; requires genome AMR/virulence confirmation before use"
    else:
        risk = "moderate_novel_commensal"
        action = "novel human commensal; genome-level AMR/virulence screening required"
    return {"safety_risk_class": risk, "safety_flags": "; ".join(flags),
            "recommended_action": action,
            "needs_genome_confirmation": risk != "low_qps_history"}


def main() -> None:
    cat = pd.read_csv(CAT)
    tri = cat.apply(lambda r: _triage(str(r["species"]), str(r["genus"])), axis=1, result_type="expand")
    out = pd.concat([cat, tri], axis=1)
    out.to_csv(OUT, index=False)

    print(f"Safety-triaged {len(out)} catalog entries -> {OUT.name}\n")
    print("safety_risk_class distribution:")
    print(out["safety_risk_class"].value_counts().to_string())

    actionable = out[out["assembly_level"].isin(["Complete Genome", "Chromosome"])]
    print("\nActionable (isolate genome) by risk class:")
    print(actionable["safety_risk_class"].value_counts().to_string())

    ready = actionable[actionable["safety_risk_class"].isin(["low_qps_history", "moderate_lbp_precedent"])]
    print(f"\nFirst screening batch (isolate genome + QPS/LBP-precedent): {len(ready)}")
    print(ready[["species", "safety_risk_class", "priority_tier", "genome_accession"]]
          .sort_values("priority_tier").head(20).to_string(index=False))
    elevated = out[out["safety_risk_class"] == "elevated_pathogen_or_amr_genus"]
    print(f"\nFlagged elevated (exclude/review): {len(elevated)} e.g. {list(elevated['species'].head(6))}")


if __name__ == "__main__":
    main()
