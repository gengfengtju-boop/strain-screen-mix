"""Add a microbiome-dysregulation priority axis to candidate strains, from the obesity SHAP signature.

Legitimate use of the obesity STATE model (it has real signal): a candidate taxon that is
depleted-in-obesity / lean-protective (per the classifier's SHAP) earns a "restore a
depleted protective commensal" rationale. This is a SEPARATE interpretable axis, not merged
into the curated clinical score. It also surfaces SHAP-protective human-derived NGPs that are
not yet candidates -- the evidence-grounded targets for the NGP expansion.

    PYTHONPATH=src python scripts/combination_recommendation/microbiome_informed_priority.py
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
SHAP = ROOT / "results/SHAP_results/obesity_classifier_shap_importance_20260613.csv"
CAND = ROOT / "results/candidate_strain_scores/evidence_derived_candidate_strain_scores.csv"
OUT_ENRICHED = ROOT / "results/candidate_strain_scores/candidate_strains_microbiome_informed_20260613.csv"
OUT_NEW = ROOT / "results/candidate_strain_scores/ngp_restore_depleted_candidates_20260613.csv"

# human-derived NGP genera (for flagging new candidates)
NGP_GENERA = {
    "Akkermansia", "Faecalibacterium", "Bacteroides", "Parabacteroides", "Roseburia",
    "Anaerobutyricum", "Anaerostipes", "Christensenella", "Blautia", "Eubacterium",
    "Phascolarctobacterium", "Dysosmobacter", "Coprococcus",
}


def _sig_key(genus: str, species: str) -> str:
    return f"{genus}_{str(species).split()[0]}" if str(species).strip() else str(genus)


def main() -> None:
    shap = pd.read_csv(SHAP)
    shap_by_species = shap.set_index("species")
    cand = pd.read_csv(CAND)

    # --- 1. annotate existing candidates with their population obesity signal ---
    rows = []
    for _, c in cand.iterrows():
        key = _sig_key(str(c["genus"]), str(c.get("species", "")))
        rec = c.to_dict()
        if key in shap_by_species.index:
            s = shap_by_species.loc[key]
            protective = s["direction"] == "higher_abundance_lowers_obesity"
            rec["microbiome_signature_species"] = key
            rec["microbiome_shap_importance"] = round(float(s["mean_abs_shap"]), 4)
            rec["microbiome_role"] = "depleted_in_obesity_protective" if protective else "enriched_in_obesity"
            # restore-depleted rationale only boosts protective taxa
            rec["microbiome_priority"] = round(float(s["mean_abs_shap"]) * (1 if protective else -1), 4)
            rec["microbiome_rationale"] = (
                "restore depleted protective commensal" if protective
                else "taxon enriched in obesity - supplementation rationale weaker"
            )
        else:
            rec["microbiome_signature_species"] = ""
            rec["microbiome_shap_importance"] = ""
            rec["microbiome_role"] = "not_in_gut_signature"
            rec["microbiome_priority"] = 0.0
            rec["microbiome_rationale"] = "low-prevalence/exogenous taxon; no population signal"
        rows.append(rec)
    enriched = pd.DataFrame(rows).sort_values("microbiome_priority", ascending=False)
    enriched.to_csv(OUT_ENRICHED, index=False)

    # --- 2. surface SHAP-protective NGPs not yet among candidates (restore-depleted targets) ---
    cand_keys = {_sig_key(str(c["genus"]), str(c.get("species", ""))) for _, c in cand.iterrows()}
    protective = shap[shap["direction"] == "higher_abundance_lowers_obesity"].copy()
    protective["genus"] = protective["species"].str.split("_").str[0]
    new_ngp = protective[
        protective["genus"].isin(NGP_GENERA) & ~protective["species"].isin(cand_keys)
    ].copy()
    new_ngp = new_ngp.sort_values("mean_abs_shap", ascending=False)
    new_ngp["rationale"] = "restore depleted protective commensal (SHAP-ranked); NGP - requires genome safety gate"
    new_ngp["safety_gate"] = "pending_genome_safety"
    new_ngp[["species", "genus", "mean_abs_shap", "abundance_shap_corr", "rationale", "safety_gate"]].to_csv(OUT_NEW, index=False)

    print(f"Existing candidates annotated: {len(enriched)} -> {OUT_ENRICHED.name}")
    matched = enriched[enriched["microbiome_role"] != "not_in_gut_signature"]
    print(f"  with a population obesity signal: {len(matched)}")
    if len(matched):
        print(matched[["strain_name", "microbiome_role", "microbiome_priority"]].to_string(index=False))
    print(f"\nSHAP-protective NGPs not yet candidates (restore-depleted targets): {len(new_ngp)} -> {OUT_NEW.name}")
    print(new_ngp[["species", "mean_abs_shap"]].head(10).to_string(index=False))


if __name__ == "__main__":
    main()
