from __future__ import annotations

import argparse
import csv
from pathlib import Path


CONFIRMED = {
    ("EUROPEPMC:40676704", "weight"): {
        "final_value": "BL21 -1.22 +/- 2.78 vs placebo -0.98 +/- 2.06",
        "final_unit": "kg change",
        "final_direction": "no significant between-group effect",
        "comparison": "BL21_vs_placebo_change",
        "time_point": "8 weeks",
        "p_value_confirmed": "0.81 between-group; BL21 within p=0.02; placebo within p=0.01",
        "sample_size_confirmed": "n=66 randomized",
        "reviewer_note": "Both groups lost weight; no BL21-specific between-group effect.",
    },
    ("EUROPEPMC:40676704", "lipid"): {
        "final_value": "BL21 -0.21 +/- 1.09",
        "final_unit": "triglyceride change; source unit requires table confirmation",
        "final_direction": "decrease within intervention group",
        "comparison": "BL21_within_group_change",
        "time_point": "8 weeks",
        "p_value_confirmed": "0.04 within BL21; between-group p not reported in abstract",
        "sample_size_confirmed": "n=66 randomized",
        "reviewer_note": "Within-group triglyceride signal only; not a confirmed between-group treatment effect.",
    },
    ("EUROPEPMC:40676704", "microbiome"): {
        "final_value": "beta-diversity differed; Parasutterella, Parabacteroides, Blautia, Dorea and Butyricicoccus enriched",
        "final_unit": "qualitative microbiome result",
        "final_direction": "changed",
        "comparison": "BL21_vs_placebo",
        "time_point": "8 weeks",
        "p_value_confirmed": "significant; exact p not stated in abstract",
        "sample_size_confirmed": "n=66 randomized",
        "reviewer_note": "Multi-omics result; taxa and pathway findings are exploratory.",
    },
    ("EUROPEPMC:40218949", "body_fat"): {
        "final_value": "LMT1-48 30.0 +/- 4.4 to 28.3 +/- 4.1",
        "final_unit": "kg body fat mass",
        "final_direction": "decrease within intervention group",
        "comparison": "LMT1-48_within_group_change",
        "time_point": "12 weeks",
        "p_value_confirmed": "0.009 within group; between-group p not stated in abstract",
        "sample_size_confirmed": "n=106 randomized",
        "reviewer_note": "Abstract reports within-group change; between-group treatment effect requires table confirmation.",
    },
    ("EUROPEPMC:40218949", "BMI"): {
        "final_value": "no confirmed between-group BMI estimate in abstract",
        "final_unit": "qualitative",
        "final_direction": "unclear",
        "comparison": "LMT1-48_vs_placebo",
        "time_point": "12 weeks",
        "p_value_confirmed": "not reported in abstract",
        "sample_size_confirmed": "n=106 randomized",
        "reviewer_note": "Do not infer BMI efficacy from the body-fat within-group result.",
    },
    ("EUROPEPMC:40218949", "microbiome"): {
        "final_value": "obesity-associated microbial taxa changed",
        "final_unit": "qualitative microbiome result",
        "final_direction": "changed",
        "comparison": "LMT1-48_vs_placebo",
        "time_point": "12 weeks",
        "p_value_confirmed": "exact p not stated in abstract",
        "sample_size_confirmed": "n=106 randomized",
        "reviewer_note": "Taxa-level details require table/supplement confirmation.",
    },
    ("PMID:32615727", "body_fat"): {
        "final_value": "CJLS03 -0.2 vs placebo +0.6",
        "final_unit": "kg body fat mass change",
        "final_direction": "decrease",
        "comparison": "CJLS03_vs_placebo_change",
        "time_point": "12 weeks",
        "p_value_confirmed": "0.018 between-group",
        "sample_size_confirmed": "n=114 randomized",
        "reviewer_note": "Primary body-fat outcome favored CJLS03; adverse events were mild and similar.",
    },
    ("PMID:32615727", "waist"): {
        "final_value": "CJLS03 0.8 cm lower than placebo",
        "final_unit": "cm between-group difference",
        "final_direction": "decrease",
        "comparison": "CJLS03_vs_placebo_change",
        "time_point": "12 weeks",
        "p_value_confirmed": "0.013 between-group",
        "sample_size_confirmed": "n=114 randomized",
        "reviewer_note": "Waist circumference change favored CJLS03.",
    },
    ("PMID:36944956", "weight"): {
        "final_value": "no significant difference in mean change across dose groups",
        "final_unit": "qualitative",
        "final_direction": "no significant between-group effect",
        "comparison": "four_K56_doses_vs_placebo_change",
        "time_point": "60 days",
        "p_value_confirmed": "between-group not significant",
        "sample_size_confirmed": "n=74 randomized across 5 groups",
        "reviewer_note": "Pilot dose-ranging study; weight changes were not significantly different between groups.",
    },
    ("PMID:36944956", "BMI"): {
        "final_value": "no significant difference in mean change across dose groups",
        "final_unit": "qualitative",
        "final_direction": "no significant between-group effect",
        "comparison": "four_K56_doses_vs_placebo_change",
        "time_point": "60 days",
        "p_value_confirmed": "between-group not significant",
        "sample_size_confirmed": "n=74 randomized across 5 groups",
        "reviewer_note": "BMI reductions in some K56 groups were not significant between groups.",
    },
    ("PMID:36944956", "body_fat"): {
        "final_value": "2x10^9 CFU/day K56: -0.72 kg fat mass; -0.867 percentage points body fat",
        "final_unit": "kg and percentage-point within-group change",
        "final_direction": "decrease within selected dose group",
        "comparison": "K56_2x10^9_CFU_within_group_change",
        "time_point": "60 days",
        "p_value_confirmed": "fat mass p=0.018; percent body fat p=0.004; overall between-group anthropometric changes not significant",
        "sample_size_confirmed": "n=74 randomized across 5 groups",
        "reviewer_note": "Dose-selected within-group signal; not a confirmed overall between-group efficacy result.",
    },
    ("PMID:36944956", "waist"): {
        "final_value": "2x10^9 CFU/day K56: -1.7 cm",
        "final_unit": "cm within-group change",
        "final_direction": "decrease within selected dose group",
        "comparison": "K56_2x10^9_CFU_within_group_change",
        "time_point": "60 days",
        "p_value_confirmed": "0.01 within group; between-group not significant",
        "sample_size_confirmed": "n=74 randomized across 5 groups",
        "reviewer_note": "Within-group dose-selected result; between-group anthropometric changes were not significant.",
    },
    ("PMID:37252684", "body_fat"): {
        "final_value": "no significant between-group change in body-composition parameters",
        "final_unit": "qualitative",
        "final_direction": "no significant between-group effect",
        "comparison": "green_lipped_mussel_vs_placebo_change",
        "time_point": "3 months",
        "p_value_confirmed": "between-group not significant",
        "sample_size_confirmed": "n=49 randomized; n=47 table analysis",
        "reviewer_note": "3 g/day whole green-lipped mussel powder; baseline body-fat imbalance noted.",
    },
    ("PMID:38393021", "weight"): {
        "final_value": "no effect on body weight",
        "final_unit": "qualitative",
        "final_direction": "no significant effect",
        "comparison": "L_bulgaricus_vs_placebo",
        "time_point": "12 weeks",
        "p_value_confirmed": "not significant",
        "sample_size_confirmed": "n=36 randomized",
        "reviewer_note": "1x10^8 CFU/day pilot trial.",
    },
    ("PMID:38393021", "BMI"): {
        "final_value": "no effect on BMI or fat percentage",
        "final_unit": "qualitative",
        "final_direction": "no significant effect",
        "comparison": "L_bulgaricus_vs_placebo",
        "time_point": "12 weeks",
        "p_value_confirmed": "not significant",
        "sample_size_confirmed": "n=36 randomized",
        "reviewer_note": "Pilot trial did not support weight-loss efficacy.",
    },
    ("PMID:38393021", "lipid"): {
        "final_value": "triglycerides decreased in probiotic-treated group",
        "final_unit": "qualitative lipid result",
        "final_direction": "decrease",
        "comparison": "L_bulgaricus_vs_placebo",
        "time_point": "12 weeks",
        "p_value_confirmed": "exact between-group p requires table confirmation",
        "sample_size_confirmed": "n=36 randomized",
        "reviewer_note": "TG signal accompanied by changes in VLDL/HDL triglyceride fractions.",
    },
    ("PMID:24795503", "glucose"): {
        "final_value": "VSL#3 improved insulin sensitivity",
        "final_unit": "qualitative insulin-sensitivity result",
        "final_direction": "improve",
        "comparison": "VSL3_vs_placebo_relative_change",
        "time_point": "6 weeks",
        "p_value_confirmed": "<0.01",
        "sample_size_confirmed": "n=60 randomized; n=15 per arm",
        "reviewer_note": "Four-arm trial; baseline imbalances and relative-change analysis should be considered.",
    },
    ("PMID:24795503", "lipid"): {
        "final_value": "total cholesterol, triglyceride, LDL and VLDL decreased; HDL increased",
        "final_unit": "qualitative lipid profile",
        "final_direction": "improve",
        "comparison": "VSL3_vs_placebo_relative_change",
        "time_point": "6 weeks",
        "p_value_confirmed": "<0.05",
        "sample_size_confirmed": "n=60 randomized; n=15 per arm",
        "reviewer_note": "Small four-arm trial; exact effect sizes remain table-level extraction targets.",
    },
    ("PMID:24795503", "microbiome"): {
        "final_value": "VSL#3 favorably altered gut microbial composition",
        "final_unit": "qualitative microbiome result",
        "final_direction": "changed",
        "comparison": "VSL3_vs_placebo",
        "time_point": "6 weeks",
        "p_value_confirmed": "exact p not stated in abstract",
        "sample_size_confirmed": "n=60 randomized; n=15 per arm",
        "reviewer_note": "Culture-based colonization/composition result; exact taxa counts require table extraction.",
    },
    ("PMID:40353878", "weight"): {
        "final_value": "low-dose nabilone completers decreased more than placebo",
        "final_unit": "qualitative completer-only result",
        "final_direction": "decrease",
        "comparison": "low_dose_nabilone_vs_placebo_completers",
        "time_point": "12 weeks",
        "p_value_confirmed": "<0.001 treatment effect",
        "sample_size_confirmed": "n=18 randomized; n=15 dosed; n=8 completers",
        "reviewer_note": "Trial terminated early for poor tolerability; all high-dose participants withdrew. Very high risk of attrition bias.",
    },
    ("PMID:40353878", "BMI"): {
        "final_value": "low-dose nabilone completers decreased more than placebo",
        "final_unit": "qualitative completer-only result",
        "final_direction": "decrease",
        "comparison": "low_dose_nabilone_vs_placebo_completers",
        "time_point": "12 weeks",
        "p_value_confirmed": "<0.001 treatment effect",
        "sample_size_confirmed": "n=18 randomized; n=15 dosed; n=8 completers",
        "reviewer_note": "Early termination and severe differential attrition prevent efficacy inference.",
    },
    ("PMID:40353878", "microbiome"): {
        "final_value": "greater Bray-Curtis compositional change with low-dose nabilone",
        "final_unit": "qualitative beta-diversity result",
        "final_direction": "changed",
        "comparison": "low_dose_nabilone_vs_placebo_completers",
        "time_point": "12 weeks",
        "p_value_confirmed": "<0.05",
        "sample_size_confirmed": "n=8 completers",
        "reviewer_note": "Exploratory completer-only microbiome result in an early-terminated trial.",
    },
    ("PMID:38713231", "body_fat"): {
        "final_value": "trunk fat mass at 6 months and trunk fat percentage at 3 months favored prebiotic",
        "final_unit": "qualitative body-composition result",
        "final_direction": "decrease",
        "comparison": "16_g_day_inulin_vs_maltodextrin_change",
        "time_point": "3 and 6 months",
        "p_value_confirmed": "trunk fat percentage p=0.014; other exact p values require table confirmation",
        "sample_size_confirmed": "n=54; prebiotic n=31, placebo n=21 reported in abstract",
        "reviewer_note": "Population had knee osteoarthritis and obesity; mostly women.",
    },
    ("PMID:38713231", "microbiome"): {
        "final_value": "37 ASVs differed between groups; Bifidobacterium correlated with physical function",
        "final_unit": "qualitative microbiome result",
        "final_direction": "changed",
        "comparison": "16_g_day_inulin_vs_maltodextrin",
        "time_point": "6 months",
        "p_value_confirmed": "multiple-comparison details require supplement confirmation",
        "sample_size_confirmed": "n=54; prebiotic n=31, placebo n=21 reported in abstract",
        "reviewer_note": "Taxa result is exploratory; correlation does not establish mediation.",
    },
}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("input", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("audit", type=Path)
    args = parser.parse_args()

    with args.input.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        rows = list(reader)
        fields = list(reader.fieldnames or [])

    audit_rows: list[dict[str, str]] = []
    for row in rows:
        key = (row.get("evidence_id", ""), row.get("outcome_domain", ""))
        confirmed = CONFIRMED.get(key)
        if not confirmed:
            continue
        row.update(confirmed)
        row["extraction_source"] = f"full-text PDF/abstract; {row.get('second_pass_source_file', '')}"
        row["reviewer"] = "Codex download supplement extraction 2026-06-10"
        row["review_status"] = "extracted"
        audit_rows.append({
            "evidence_id": key[0],
            "outcome_domain": key[1],
            "final_value": row["final_value"],
            "comparison": row["comparison"],
            "p_value_confirmed": row["p_value_confirmed"],
            "sample_size_confirmed": row["sample_size_confirmed"],
            "source_file": row.get("second_pass_source_file", ""),
            "reviewer_note": row["reviewer_note"],
        })

    missing = sorted(set(CONFIRMED) - {(row["evidence_id"], row["outcome_domain"]) for row in audit_rows})
    if missing:
        raise SystemExit(f"Confirmed outcome keys missing from input: {missing}")

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    args.audit.parent.mkdir(parents=True, exist_ok=True)
    with args.audit.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(audit_rows[0]))
        writer.writeheader()
        writer.writerows(audit_rows)
    print(f"{args.output}\trows={len(rows)}\tnewly_confirmed={len(audit_rows)}")
    print(f"{args.audit}\trows={len(audit_rows)}")


if __name__ == "__main__":
    main()
