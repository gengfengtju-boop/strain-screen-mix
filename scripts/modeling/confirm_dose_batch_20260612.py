from __future__ import annotations

import math
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[2]
INPUT = ROOT / "data/intervention_data/intervention_review_worksheet.expanded_top160.dose_confirmed_20260612.csv"
EXPANSION = ROOT / "data/intervention_data/intervention_review_worksheet.expansion_new_top300.csv"
OUTPUT = ROOT / "data/intervention_data/intervention_review_worksheet.expanded_top160.dose_confirmed_v4_20260612.csv"


CONFIRMATIONS = {
    "PMID:35845797": {
        "final_species": "Lactobacillus acidophilus; Lacticaseibacillus rhamnosus; Bifidobacterium bifidum; Bifidobacterium longum; Enterococcus faecium",
        "final_total_CFU_per_day": 2.5e9,
        "final_duration_weeks": 12.0,
        "final_dosage_form": "sachet",
        "reviewer_note": "PMC9286749: one sachet daily; total 2.5e9 CFU per sachet for 12 weeks.",
    },
    "PMID:38999741": {
        "final_species": "Lacticaseibacillus paracasei; Lactiplantibacillus plantarum",
        "final_strain": "BEPC22; BELP53",
        "final_total_CFU_per_day": 5.0e10,
        "final_duration_weeks": 12.0,
        "final_dosage_form": "2 g sachet",
        "reviewer_note": "PMC11243028: one BN-202M sachet daily; 5e10 CFU blend per sachet for 12 weeks.",
    },
    "PMID:37111082": {
        "final_species": "Lacticaseibacillus rhamnosus; Lactobacillus gasseri; Lactobacillus salivarius; Bifidobacterium animalis subsp. lactis; Bifidobacterium longum; Bifidobacterium breve; Bifidobacterium longum subsp. infantis",
        "final_strain": "LR3; BNR17; LS1; BL2; BG3; BR2; BT",
        "final_total_CFU_per_day": 3.7e10,
        "final_prebiotic_type": "fructooligosaccharides",
        "final_prebiotic_dose_g_day": 2.0,
        "final_duration_weeks": 12.0,
        "final_dosage_form": "sachet",
        "reviewer_note": "PMC10141052: daily multispecies dose 37e9 CFU plus 2 g FOS for 12 weeks.",
    },
    "PMID:40416368": {
        "final_species": "Bacillus coagulans",
        "final_strain": "BC99",
        "final_total_CFU_per_day": 5.0e9,
        "final_duration_weeks": 8.0,
        "final_dosage_form": "packet",
        "reviewer_note": "PMC12100662: BC99 5e9 CFU once daily for 8 weeks; 3 g refers to carrier mass.",
    },
    "PMID:34434546": {
        "final_species": "Lactiplantibacillus plantarum; Streptococcus thermophilus; Bifidobacterium bifidum",
        "final_total_CFU_per_day": 1.0e9,
        "final_prebiotic_type": "fructooligosaccharides",
        "final_prebiotic_dose_g_day": 0.48,
        "final_duration_weeks": 8.0,
        "final_dosage_form": "sachet",
        "reviewer_note": "PMC8376682: one Rillus sachet daily; total 1e9 CFU plus 480 mg FOS for 8 weeks.",
    },
    "PMID:36606510": {
        "final_species": "Bifidobacterium longum; Lactobacillus helveticus; Lactococcus lactis; Streptococcus thermophilus",
        "final_total_CFU_per_day": 1.0e10,
        "final_duration_weeks": 4.0,
        "final_dosage_form": "tablet",
        "reviewer_note": "PMC10000630: one tablet daily containing 10 x 10^9 CFU for one month.",
    },
    "EUROPEPMC:40676704": {
        "final_species": "Bifidobacterium longum subsp. longum",
        "final_strain": "BL21",
        "final_total_CFU_per_day": 2.0e10,
        "final_duration_weeks": 8.0,
        "final_dosage_form": "powder packet",
        "reviewer_note": "PMC12273011: BL21 2e10 CFU once daily for 8 weeks; 3 g is maltodextrin carrier mass.",
    },
}


def main() -> None:
    review = pd.read_csv(INPUT)
    expansion = pd.read_csv(EXPANSION)
    text_columns = [
        "final_species",
        "final_strain",
        "final_prebiotic_type",
        "final_dosage_form",
        "reviewer",
        "review_status",
        "reviewer_note",
    ]
    for column in text_columns:
        review[column] = review[column].astype(object)
    missing = [evidence_id for evidence_id in CONFIRMATIONS if evidence_id not in set(review["evidence_id"])]
    if missing:
        additions = expansion[expansion["evidence_id"].isin(missing)].copy()
        unresolved = sorted(set(missing) - set(additions["evidence_id"]))
        if unresolved:
            raise ValueError(f"Missing source rows for {unresolved}")
        review = pd.concat([review, additions[review.columns]], ignore_index=True)

    for evidence_id, values in CONFIRMATIONS.items():
        mask = review["evidence_id"] == evidence_id
        if mask.sum() != 1:
            raise ValueError(f"Expected one row for {evidence_id}, found {int(mask.sum())}")
        for column, value in values.items():
            review.loc[mask, column] = value
        cfu = float(values["final_total_CFU_per_day"])
        review.loc[mask, "final_log10_CFU_per_day"] = math.log10(cfu)
        review.loc[mask, "reviewer"] = "codex_primary_source_review"
        review.loc[mask, "review_status"] = "extracted"

    ambiguous = review["evidence_id"] == "PMID:37447365"
    review.loc[ambiguous, "reviewer"] = "codex_primary_source_review"
    review.loc[ambiguous, "review_status"] = "pending"
    review.loc[ambiguous, "reviewer_note"] = (
        "PMC10346309 reports two active arms with different measured daily doses: "
        "probiotic 5.46e9 CFU/day and synbiotic 1.97e9 CFU/day. Keep pending until "
        "the evidence schema supports arm-specific intervention rows."
    )

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    review.to_csv(OUTPUT, index=False)
    print(f"Wrote {OUTPUT} with {(review['review_status'] == 'extracted').sum()} confirmed rows")


if __name__ == "__main__":
    main()
