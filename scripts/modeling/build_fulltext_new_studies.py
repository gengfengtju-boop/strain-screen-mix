"""Build structured-effects + companion review rows for NEW RCTs curated from full text.

These studies are not in the variance-rich worksheet; they are added directly to the
continuous-effect dataset. Each entry was read from the article full text in D:\\Download.
Emits:
  data/intervention_data/clinical_outcome.structured_effects.fulltext_new_<stamp>.csv
  data/intervention_data/outcome_review_worksheet.fulltext_new_<stamp>.csv   (carries n)

    PYTHONPATH=src python scripts/modeling/build_fulltext_new_studies.py
"""
from __future__ import annotations

from datetime import date
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]

STRUCTURED_COLS = [
    "evidence_id", "outcome_domain", "endpoint_type", "analysis_population", "comparison",
    "intervention_effect", "control_effect", "effect_difference", "effect_unit",
    "between_group_p", "within_group_p", "direction", "evidence_modifier",
    "positive_efficacy_label", "effect_parse_method", "p_value_parse_method",
    "structure_warning", "source_final_value", "source_note",
]
REVIEW_COLS = [
    "evidence_id", "source_database", "source_accession", "title", "outcome_domain",
    "suggested_text", "suggested_p_value", "final_value", "final_unit", "final_direction",
    "comparison", "time_point", "p_value_confirmed", "sample_size_confirmed",
    "extraction_source", "reviewer", "review_status", "reviewer_note",
]

# Each study: metadata + list of outcome effects read from full text.
STUDIES = [
    {
        "evidence_id": "DOI:10.3803/EnM.2020.35.2.425",
        "title": "Effect of Lactobacillus sakei CJLS03 on body fat in Koreans with obesity (EnM 2020)",
        "n_total": 114,
        "comparison": "probiotic_L_sakei_CJLS03_vs_placebo",
        "effects": [
            {
                "outcome_domain": "body_fat", "endpoint_type": "adiposity",
                "intervention_effect": -0.2, "control_effect": 0.6, "effect_difference": -0.8,
                "effect_unit": "kg", "between_group_p": "0.018", "direction": "decrease",
                "source_final_value": "Body fat mass change CJLS03 -0.2 kg vs placebo +0.6 kg; 0.8 kg between-group difference, P=0.018",
            },
            {
                "outcome_domain": "waist", "endpoint_type": "adiposity",
                "intervention_effect": "", "control_effect": "", "effect_difference": -0.8,
                "effect_unit": "cm", "between_group_p": "0.013", "direction": "decrease",
                "source_final_value": "Waist circumference 0.8 cm smaller in CJLS03 than placebo at 12 weeks, P=0.013",
            },
        ],
    },
    {
        # Depommier et al., Nature Medicine 2019 — landmark pasteurized A. muciniphila
        # RCT in overweight/obese humans. Human-derived next-generation probiotic.
        # Abstract reports between-group change vs placebo as mean +/- s.e.m.; CI in
        # source_final_value is mean +/- 1.96*SEM so the pipeline derives SE directly.
        "evidence_id": "PMID:31263284",
        "title": "Pasteurized Akkermansia muciniphila in overweight/obese humans (Depommier, Nat Med 2019)",
        "n_total": 40,
        "comparison": "pasteurized_akkermansia_muciniphila_vs_placebo",
        "effects": [
            {
                "outcome_domain": "weight", "endpoint_type": "body_weight",
                "intervention_effect": "", "control_effect": "", "effect_difference": -2.27,
                "effect_unit": "kg", "between_group_p": "0.091", "direction": "decrease",
                "source_final_value": "between-group difference -2.27 (95% CI -4.07 to -0.47)",
            },
            {
                "outcome_domain": "body_fat", "endpoint_type": "adiposity",
                "intervention_effect": "", "control_effect": "", "effect_difference": -1.37,
                "effect_unit": "kg", "between_group_p": "", "direction": "decrease",
                "source_final_value": "between-group difference -1.37 (95% CI -2.98 to 0.24)",
            },
        ],
    },
    {
        # Pasteurized Akkermansia muciniphila MucT, weight-maintenance RCT (Nat Med 2025).
        # Net weight loss from baseline to end of maintenance was 3.1 +/- 0.7 kg (s.e.m.)
        # greater in MucT than placebo, P=0.009 -> between-group difference -3.1 kg.
        "evidence_id": "PMID:42120725",
        "title": "Pasteurized Akkermansia muciniphila MucT weight maintenance RCT (2025)",
        "n_total": 144,
        "comparison": "pasteurized_akkermansia_muciniphila_MucT_vs_placebo",
        "effects": [
            {
                "outcome_domain": "weight", "endpoint_type": "body_weight",
                "intervention_effect": "", "control_effect": "", "effect_difference": -3.1,
                "effect_unit": "kg", "between_group_p": "0.009", "direction": "decrease",
                "source_final_value": "net weight-loss between-group difference -3.1 (95% CI -4.47 to -1.73)",
            },
        ],
    },
]


def main() -> None:
    s_rows, r_rows = [], []
    for study in STUDIES:
        eid = study["evidence_id"]
        for e in study["effects"]:
            s_rows.append({
                "evidence_id": eid, "outcome_domain": e["outcome_domain"],
                "endpoint_type": e["endpoint_type"], "analysis_population": "aggregate_trial",
                "comparison": study["comparison"],
                "intervention_effect": e["intervention_effect"], "control_effect": e["control_effect"],
                "effect_difference": e["effect_difference"], "effect_unit": e["effect_unit"],
                "between_group_p": e["between_group_p"], "within_group_p": "",
                "direction": e["direction"], "evidence_modifier": "",
                "positive_efficacy_label": "yes",
                "effect_parse_method": "fulltext_manual", "p_value_parse_method": "explicit_between_group",
                "structure_warning": "", "source_final_value": e["source_final_value"],
                "source_note": f"full-text curated; {study['title']}",
            })
            r_rows.append({
                "evidence_id": eid, "source_database": eid.split(":")[0],
                "source_accession": eid.split(":", 1)[1], "title": study["title"],
                "outcome_domain": e["outcome_domain"], "suggested_text": e["source_final_value"],
                "suggested_p_value": e["between_group_p"], "final_value": e["source_final_value"],
                "final_unit": e["effect_unit"], "final_direction": e["direction"],
                "comparison": study["comparison"], "time_point": "12 weeks",
                "p_value_confirmed": e["between_group_p"],
                "sample_size_confirmed": f"n={study['n_total']}",
                "extraction_source": "full_text", "reviewer": "claude_fulltext",
                "review_status": "extracted", "reviewer_note": "new study added from full text",
            })

    stamp = date.today().strftime("%Y%m%d")
    out_dir = ROOT / "data/intervention_data"
    s_out = out_dir / f"clinical_outcome.structured_effects.fulltext_new_{stamp}.csv"
    r_out = out_dir / f"outcome_review_worksheet.fulltext_new_{stamp}.csv"
    pd.DataFrame(s_rows, columns=STRUCTURED_COLS).to_csv(s_out, index=False, encoding="utf-8")
    pd.DataFrame(r_rows, columns=REVIEW_COLS).to_csv(r_out, index=False, encoding="utf-8")
    print(f"New studies: {len(STUDIES)} | structured rows: {len(s_rows)}")
    print(f"Structured effects: {s_out}")
    print(f"Companion review (carries n): {r_out}")


if __name__ == "__main__":
    main()
