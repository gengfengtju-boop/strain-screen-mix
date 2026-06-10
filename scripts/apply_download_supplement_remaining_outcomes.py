from __future__ import annotations

import argparse
import csv
from pathlib import Path


def result(value: str, unit: str, direction: str, comparison: str, time: str, p: str, sample: str, note: str) -> dict[str, str]:
    return {
        "final_value": value,
        "final_unit": unit,
        "final_direction": direction,
        "comparison": comparison,
        "time_point": time,
        "p_value_confirmed": p,
        "sample_size_confirmed": sample,
        "reviewer_note": note,
    }


CONFIRMED = {
    ("EUROPEPMC:41413231", "weight"): result("adjusted difference -1.16 (95% CI -1.36 to -0.97)", "kg", "decrease", "synbiotic_vs_placebo_adjusted", "4 months", "<0.001 between-group", "n=96 randomized; n=85 completed; modified ITT", "Older adults with T2DM and high cardiovascular risk."),
    ("EUROPEPMC:41413231", "BMI"): result("adjusted difference -0.44 (95% CI -0.51 to -0.36)", "kg/m2", "decrease", "synbiotic_vs_placebo_adjusted", "4 months", "<0.001 between-group", "n=96 randomized; n=85 completed; modified ITT", "Linear mixed ANCOVA."),
    ("EUROPEPMC:41413231", "glucose"): result("FPG -22.83 mg/dL (95% CI -31.30 to -14.36); HOMA-IR -1.31 (-1.75 to -0.86)", "adjusted between-group difference", "improve", "synbiotic_vs_placebo_adjusted", "4 months", "FPG p=0.003; HOMA-IR p=0.001; insulin p=0.060", "n=96 randomized; n=85 completed; modified ITT", "HbA1c and insulin did not show significant between-group effects."),
    ("EUROPEPMC:41413231", "lipid"): result("LDL-C -10.83 mg/dL; total cholesterol -11.78 mg/dL", "adjusted between-group difference", "improve", "synbiotic_vs_placebo_adjusted", "4 months", "LDL-C p=0.002; total cholesterol p=0.012; TG p=0.416", "n=96 randomized; n=85 completed; modified ITT", "Triglycerides decreased within synbiotic arm but not between groups."),
    ("PMID:28730743", "body_fat"): result("whey -0.9 +/- 1.6 kg and -0.9 +/- 1.6% vs control +0.1 +/- 1.4 kg and +0.2 +/- 1.1%", "fat mass change", "decrease", "whey_vs_control_change", "12 weeks", "significant between-group; exact p requires table confirmation", "four-arm RCT; group n requires table confirmation", "Body-fat effect belonged to whey protein, not inulin-type fructans."),
    ("PMID:28730743", "weight"): result("no significant change in body weight, BMI or waist circumference in any group", "qualitative", "no significant between-group effect", "ITF_whey_combination_vs_control", "12 weeks", "not significant", "four-arm RCT", "Prebiotic altered microbiota and appetite but did not improve weight loss."),
    ("PMID:33763720", "weight"): result("isocaloric Mediterranean diet effect independent of body-weight change", "qualitative", "no significant weight effect", "Mediterranean_diet_vs_habitual_diet", "8 weeks", "body-weight change not significant", "n=82 randomized; MD n=43, control n=39", "Mechanistic dietary study, not a weight-loss intervention."),
    ("PMID:33763720", "BMI"): result("no intervention-related BMI reduction reported", "qualitative", "no significant weight effect", "Mediterranean_diet_vs_habitual_diet", "8 weeks", "not significant", "n=82 randomized", "Isocaloric intervention."),
    ("PMID:33763720", "glucose"): result("HOMA-IR -23.9% at week 8 in low baseline OEA/PEA subgroup", "subgroup within Mediterranean-diet arm", "improve in subgroup", "baseline_biomarker_subgroup_within_MD", "8 weeks", "0.01 subgroup within-group", "n=82 randomized; subgroup quartile", "Post-randomization biomarker subgroup; not an overall randomized treatment effect."),
    ("PMID:33763720", "microbiome"): result("Akkermansia muciniphila abundance increased", "qualitative microbiome result", "changed", "Mediterranean_diet_vs_habitual_diet", "8 weeks", "0.026 between-group/time analysis", "n=82 randomized; ITT microbiome analysis", "Effect occurred independently of body-weight change."),
    ("PMID:35247098", "weight"): result("no significant anthropometric differences", "qualitative", "no significant between-group effect", "27_g_day_wheat_aleurone_vs_cellulose", "4 weeks", "not significant", "aleurone n=34; placebo n=33", "Aleurone did not improve clinical anthropometric markers."),
    ("PMID:35247098", "BMI"): result("no significant BMI difference", "qualitative", "no significant between-group effect", "27_g_day_wheat_aleurone_vs_cellulose", "4 weeks", "not significant", "aleurone n=34; placebo n=33", "Primary homocysteine and other clinical outcomes were null."),
    ("PMID:35247098", "microbiome"): result("Shannon diversity higher; Roseburia inulinivorans enriched", "qualitative microbiome result", "changed", "27_g_day_wheat_aleurone_vs_cellulose", "4 weeks", "Shannon significant; R. inulinivorans FDR p=0.0499", "aleurone n=34; placebo n=33", "No significant fecal SCFA difference."),
    ("PMID:35351144", "BMI"): result("inulin main effect; strongest in increased-PA group (39.7 to 38.1 kg/m2)", "BMI", "decrease", "inulin_by_physical_activity_interaction", "3 months", "inulin p=0.012; interaction p=0.044", "n=61; four post-randomization PA strata", "Physical activity was not randomized; interaction is exploratory."),
    ("PMID:35351144", "glucose"): result("fasting insulin 18.1 to 13.6 mU/L in inulin plus increased-PA group", "metabolic change", "improve in subgroup", "inulin_by_physical_activity_interaction", "3 months", "inulin main effect p=0.005; HOMA-IR p=0.07", "n=61; four post-randomization PA strata", "PA subgroup is observational within randomized inulin trial."),
    ("PMID:35351144", "lipid"): result("total cholesterol 192.9 to 176.1 mg/dL in inulin plus increased-PA group", "mg/dL", "decrease in subgroup", "inulin_by_physical_activity_interaction", "3 months", "inulin p=0.031; interaction p<0.001", "n=61; four post-randomization PA strata", "Interaction with non-randomized PA change limits causal interpretation."),
    ("PMID:35351144", "microbiome"): result("Bifidobacterium increased most with inulin plus increased PA", "qualitative microbiome result", "changed", "inulin_by_physical_activity_interaction", "3 months", "p and q <0.05", "n=61", "Bifidobacterium change correlated with BMI, weight and HOMA measures."),
    ("PMID:37545298", "weight"): result("ILCD -0.98 +/- 1.40 vs ICR -0.84 +/- 0.96", "kg change at day 28", "no significant between-group effect", "intermittent_low_carb_vs_intermittent_calorie_restriction", "28 days", "0.80 between-group", "n=34; 17 per arm", "Both short dietary interventions reduced weight similarly."),
    ("PMID:37545298", "waist"): result("ILCD -0.17 +/- 2.46 vs ICR -1.15 +/- 1.78", "cm change at day 28", "no significant between-group effect", "intermittent_low_carb_vs_intermittent_calorie_restriction", "28 days", "0.31 between-group", "n=34; 17 per arm", "No differential waist effect."),
    ("PMID:37545298", "glucose"): result("FBG -0.27 vs -0.15 mmol/L; HOMA-IR -1.00 vs -1.14", "change", "no significant between-group effect", "intermittent_low_carb_vs_intermittent_calorie_restriction", "14 days for biomarkers", "FBG p=0.18; HOMA-IR p=0.16", "n=34", "Glycemic improvements were similar between diets."),
    ("PMID:37545298", "lipid"): result("LDL-C +0.34 vs -0.03; TG -0.19 vs -0.09; total cholesterol +0.20 vs -0.20", "mmol/L change", "unfavorable for intermittent low-carbohydrate diet", "intermittent_low_carb_vs_intermittent_calorie_restriction", "14 days", "LDL p=0.03; TG p=0.02; total cholesterol p=0.02", "n=34", "ILCD produced less favorable short-term lipid changes than ICR."),
    ("PMID:37545298", "microbiome"): result("diet-specific gut microbiota changes without demonstrated mediation", "qualitative microbiome result", "changed", "intermittent_low_carb_vs_intermittent_calorie_restriction", "14 days", "exploratory multiple taxa", "n=34", "Short-duration dietary study; microbiome findings are exploratory."),
    ("PMID:40375569", "weight"): result("waist changes were similar across placebo, probiotic, curcumin and combined groups", "qualitative anthropometric result", "no significant between-group effect", "four_arm_curcumin_probiotic_trial", "8 weeks", "between-group not significant", "n=128 randomized; n=104 per-protocol; 26 per arm analyzed", "Primary outcomes were mental health and quality of life; baseline BMI/waist imbalances and per-protocol analysis."),
    ("PMID:40732984", "weight"): result("WLM3P -20.6 vs LCD -12.9; adjusted group difference -6.50 (95% CI -11.93 to -1.07)", "kg change", "decrease", "WLM3P_vs_low_calorie_diet", "6 months", "0.01 between-group; interaction <0.001", "n=58 randomized; 29 per arm", "Multicomponent weight-management program versus low-calorie diet."),
    ("PMID:40732984", "BMI"): result("WLM3P -7.1 vs LCD -4.6; adjusted difference -2.61 (95% CI -3.69 to -1.52)", "kg/m2 change", "decrease", "WLM3P_vs_low_calorie_diet", "6 months", "<0.001 between-group", "n=58 randomized", "Large change reflects multicomponent program, not a probiotic intervention."),
    ("PMID:40732984", "body_fat"): result("fat mass adjusted difference -6.09 kg; visceral fat -30.70 cm2", "between-group difference", "decrease", "WLM3P_vs_low_calorie_diet", "6 months", "both p<0.001", "n=58 randomized", "Faecalibacterium association with fat loss was exploratory and adjusted observational analysis."),
    ("PMID:40732984", "lipid"): result("no significant LDL-C, HDL-C or triglyceride difference", "qualitative", "no significant between-group effect", "WLM3P_vs_low_calorie_diet", "6 months", "LDL p=0.62; HDL p=0.58; TG p=0.64", "n=58 randomized", "Both groups improved some lipid measures over time."),
    ("PMID:40732984", "microbiome"): result("WLM3P Shannon p=0.03 and beta-diversity p<0.01; multiple genera changed", "qualitative microbiome result", "changed", "WLM3P_vs_low_calorie_diet", "6 months", "within WLM3P diversity changes; taxa FDR controlled", "n=58 randomized", "Faecalibacterium interaction with fat-mass outcomes p<0.001; mediation not established."),
    ("PMID:40828642", "weight"): result("intervention -2.6 +/- 1.5 vs control +0.57 +/- 0.84", "kg change", "decrease", "energy_restriction_plus_exercise_vs_usual_lifestyle", "3 weeks", "<0.001 ANCOVA", "n=30; intervention n=18, control n=12", "Combined lifestyle intervention; not microbiome-targeted."),
    ("PMID:40828642", "body_fat"): result("intervention -1.5 +/- 1.3 vs control +0.2 +/- 1.0", "kg fat-mass change", "decrease", "energy_restriction_plus_exercise_vs_usual_lifestyle", "3 weeks", "0.001 ANCOVA", "n=30; DEXA n=28", "Fat-free mass also decreased modestly."),
    ("PMID:40828642", "glucose"): result("insulin -23.5 +/- 38.1 vs +4.2 +/- 24.1 pmol/L; HOMA2%S +48.7 vs +11.0", "change", "improve", "energy_restriction_plus_exercise_vs_usual_lifestyle", "3 weeks", "insulin p=0.034; HOMA2%S p=0.016; glucose p=0.195", "n=30", "Insulin sensitivity improved without significant fasting-glucose difference."),
    ("PMID:40828642", "lipid"): result("total cholesterol -0.70 vs -0.09; LDL-C -0.53 vs -0.06", "mmol/L change", "improve", "energy_restriction_plus_exercise_vs_usual_lifestyle", "3 weeks", "total cholesterol p<0.001; LDL p=0.004; TG p=0.101", "n=30", "Short intensive lifestyle intervention."),
    ("PMID:40828642", "microbiome"): result("no alpha/beta diversity or differential taxon/pathway change", "qualitative microbiome result", "no significant between-group effect", "energy_restriction_plus_exercise_vs_usual_lifestyle", "3 weeks", "alpha p=0.934; species beta p=0.101; pathway beta p=0.639; all taxa q>0.1", "n=30", "Metabolic improvements occurred without detectable gut microbiome change."),
}


APPENDED = {
    ("NCT:NCT03261466", "BMI"): result("BMI decreased over time in both arms; probiotic-specific interaction not established", "qualitative", "no clear between-group effect", "B_breve_BR03_B632_vs_placebo_during_diet_training", "8 weeks", "time effect p<0.01; treatment interaction not reported", "n=101 first period", "Carry-over invalidated full crossover; first period analyzed."),
    ("NCT:NCT03261466", "waist"): result("adjusted probiotic cohort mean -3.41 cm vs placebo", "cm adjusted difference", "decrease", "B_breve_BR03_B632_vs_placebo_during_diet_training", "8 weeks", "<0.05", "n=101 first period", "Dietary training in both arms; baseline metabolic differences remained."),
    ("NCT:NCT03261466", "glucose"): result("QUICKI interaction +0.013; ISI interaction +0.654", "model interaction coefficient", "improve", "B_breve_BR03_B632_by_time", "8 weeks", "QUICKI p=0.05; ISI p=0.097", "n=101; OGTT subsets smaller", "Borderline insulin-sensitivity interaction; crossover carry-over limits interpretation."),
    ("NCT:NCT03261466", "microbiome"): result("E. coli concentration adjusted difference -0.4 log CFU/g", "log CFU/g", "decrease", "B_breve_BR03_B632_vs_placebo_during_diet_training", "8 weeks", "<0.02", "n=101; stool subsets", "Targeted qPCR rather than global community profiling."),
    ("NCT:NCT06795607", "weight"): result("probiotic -0.8 vs placebo -0.6", "kg change", "no significant between-group effect", "SF68_formulation_vs_placebo", "12 weeks", "0.965 between-group", "n=40; 20 per arm", "Single-blind small study; formulation also contained phytosterols and 6S-5MeTHF."),
    ("NCT:NCT06795607", "BMI"): result("probiotic -0.3 vs placebo -0.2", "kg/m2 change", "no significant between-group effect", "SF68_formulation_vs_placebo", "12 weeks", "0.988 between-group", "n=40; 20 per arm", "No probiotic-specific BMI benefit."),
    ("NCT:NCT06795607", "waist"): result("probiotic -1.8 vs placebo -1.2", "cm change", "no significant between-group effect", "SF68_formulation_vs_placebo", "12 weeks", "0.403 between-group", "n=40; 20 per arm", "Both groups improved within arm."),
    ("NCT:NCT06795607", "body_fat"): result("fat mass -1.8 vs -1.3 kg; fat percentage -1.7 vs -1.1", "change", "no significant between-group effect", "SF68_formulation_vs_placebo", "12 weeks", "kg p=0.447; percentage p=0.430", "n=40; 20 per arm", "Within-group reductions did not translate to between-group efficacy."),
    ("NCT:NCT06795607", "glucose"): result("glucose +3.6 vs +5.1 mg/dL; HOMA +0.1 vs +0.3", "change", "no significant between-group effect", "SF68_formulation_vs_placebo", "12 weeks", "glucose p=0.221; HOMA p=0.261", "n=40", "No glycemic treatment effect."),
    ("NCT:NCT06795607", "lipid"): result("HDL/LDL ratio +0.1 vs 0; total cholesterol -11 vs +6.2 mg/dL", "change", "mixed lipid result", "SF68_formulation_vs_placebo", "12 weeks", "HDL/LDL ratio p=0.048; total cholesterol p=0.106; LDL p=0.227; TG p=0.739", "n=40", "Only HDL/LDL ratio reached between-group significance."),
    ("NCT:NCT06795607", "microbiome"): result("Evenness increased within probiotic arm; Lachnospirales decreased", "qualitative microbiome result", "changed within intervention group", "SF68_formulation_within_group", "12 weeks", "Evenness p=0.031; PERMANOVA p=0.9874", "n=40", "No significant beta-diversity separation; within-arm exploratory result."),
}


TITLES = {
    "NCT:NCT03261466": "Bifidobacterium breve BR03 and B632 in children and adolescents with obesity",
    "NCT:NCT06795607": "SF68, phytosterols, and 6S-5-methyltetrahydrofolic acid in adults with overweight or obesity",
}


def blank_row(fields: list[str], evidence_id: str, domain: str) -> dict[str, str]:
    row = {field: "" for field in fields}
    row.update(
        {
            "evidence_id": evidence_id,
            "title": TITLES[evidence_id],
            "source_database": "ClinicalTrials.gov linked publication",
            "source_accession": evidence_id.replace("NCT:", ""),
            "outcome_domain": domain,
        }
    )
    return row


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
    by_key = {(row.get("evidence_id", ""), row.get("outcome_domain", "")): row for row in rows}
    audit_rows = []
    for key, values in {**CONFIRMED, **APPENDED}.items():
        row = by_key.get(key)
        if row is None:
            row = blank_row(fields, *key)
            rows.append(row)
            by_key[key] = row
        row.update(values)
        row["extraction_source"] = "full-text PDF targeted table review"
        row["reviewer"] = "Codex targeted table extraction 2026-06-10"
        row["review_status"] = "extracted"
        audit_rows.append({"evidence_id": key[0], "outcome_domain": key[1], **values})
    with args.output.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    with args.audit.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(audit_rows[0]))
        writer.writeheader()
        writer.writerows(audit_rows)
    print(f"{args.output}\trows={len(rows)}\tconfirmed={len(audit_rows)}\tappended={len(APPENDED)}")


if __name__ == "__main__":
    main()
