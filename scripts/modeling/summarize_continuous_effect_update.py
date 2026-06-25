from __future__ import annotations

import json
from datetime import date
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[2]


def main() -> None:
    stamp = date.today().strftime("%Y%m%d")
    arms_path = ROOT / f"data/intervention_data/study_arm_registry.upgrade_{stamp}.csv"
    effects_path = ROOT / f"data/intervention_data/continuous_effect_sizes.upgrade_{stamp}.csv"
    metrics_path = ROOT / f"results/prediction_results/continuous_effect_model_metrics_{stamp}.json"
    meta_path = ROOT / f"results/prediction_results/effect_meta_analysis_hksj_{stamp}.json"
    robustness_path = (
        ROOT / f"results/prediction_results/missing_variance_robustness_{stamp}.json"
    )
    body_fat_audit_path = (
        ROOT / f"results/prediction_results/body_fat_hypothesis_audit_{stamp}.json"
    )
    quality_path = ROOT / f"results/prediction_results/effect_quality_report_{stamp}.json"
    layer_path = (
        ROOT / f"results/prediction_results/evidence_layer_sensitivity_{stamp}.json"
    )
    queue_path = ROOT / f"results/prediction_results/variance_rich_curation_queue_{stamp}.csv"

    arms = pd.read_csv(arms_path)
    effects = pd.read_csv(effects_path)
    metrics = json.loads(metrics_path.read_text(encoding="utf-8"))
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    robustness = json.loads(robustness_path.read_text(encoding="utf-8"))
    body_fat_audit = json.loads(body_fat_audit_path.read_text(encoding="utf-8"))
    quality = json.loads(quality_path.read_text(encoding="utf-8"))
    layers = json.loads(layer_path.read_text(encoding="utf-8"))
    queue = pd.read_csv(queue_path)
    high = effects[effects["confidence"].fillna("").str.lower() == "high"]
    ready = high[pd.to_numeric(high["standard_error"], errors="coerce").gt(0)]

    analyzed = [
        {
            key: row.get(key)
            for key in (
                "stratum",
                "k_studies",
                "pooled_effect",
                "ci95_low",
                "ci95_high",
                "i2_percent",
                "ci_excludes_zero",
            )
        }
        for row in meta["strata"]
        if row.get("status") == "random_effects_meta_analyzed"
    ]
    report = {
        "date": date.today().isoformat(),
        "upgrade": "arm-level continuous effects with small-sample robust synthesis",
        "arm_registry": {
            "studies": int(arms["study_id"].nunique()),
            "arms": int(len(arms)),
        },
        "continuous_effects": {
            "rows_all_confidence": int(len(effects)),
            "studies_all_confidence": int(effects["study_id"].nunique()),
            "high_confidence_rows": int(len(high)),
            "high_confidence_studies": int(high["study_id"].nunique()),
            "se_bearing_high_confidence_rows": int(len(ready)),
            "se_bearing_high_confidence_studies": int(ready["study_id"].nunique()),
            "modeling_eligible_rows_all_confidence": metrics["modeling_rows_all_confidence"],
            "modeling_eligible_rows_high_confidence": metrics["modeling_rows_high_confidence"],
            "modeling_high_confidence_studies": metrics["high_confidence_independent_studies"],
            "validation_ready_modeling_rows_high_confidence": metrics[
                "validation_ready_rows_high_confidence"
            ],
            "newly_curated_studies": ["PMID:31965834", "PMID:34919684", "PMID:35332040"],
        },
        "predictive_model": {
            "modeled_strata": metrics["modeled_strata"],
            "strata_beating_null_baseline": metrics["strata_beating_null_baseline"],
            "model_status": metrics["model_status"],
            "combination_ranking_enabled": metrics["combination_ranking_enabled"],
        },
        "small_sample_meta_analysis": {
            "method": meta["method"],
            "strata_meta_analyzed": meta["strata_meta_analyzed"],
            "strata_with_ci_excluding_zero": meta["strata_with_pooled_effect_excluding_zero"],
            "strata": analyzed,
            "interpretation": (
                "No endpoint stratum excludes zero under the modified Hartung-Knapp interval. "
                "The earlier DerSimonian-Laird body-fat signal is not robust to small-study inference."
            ),
        },
        "missing_variance_robustness": {
            "method": robustness["method"],
            "strata_analyzed": robustness["strata_analyzed"],
            "evidence_state_counts": robustness["evidence_state_counts"],
            "combination_ranking_enabled": robustness["combination_ranking_enabled"],
            "interpretation": (
                "After splitting a mixed percent/kg extraction, body-fat reduction remains "
                "a replication hypothesis only. Its observed-variance PM/HKSJ interval and "
                "nonparametric bootstrap interval both cross zero."
            ),
        },
        "body_fat_hypothesis_audit": {
            key: body_fat_audit[key]
            for key in (
                "studies",
                "observed_variance_studies",
                "negative_effect_studies",
                "positive_effect_studies",
                "studies_with_cointervention_flags",
                "moderator_ready_studies",
                "decision",
            )
        },
        "effect_quality_audit": {
            "analysis_trial_ids": quality["analysis_trial_ids"],
            "primary_analysis_eligible_rows": quality["primary_analysis_eligible_rows"],
            "primary_analysis_trials": quality["primary_analysis_trials"],
            "cointervention_rows": quality["cointervention_rows"],
            "duplicate_alias_groups": quality["duplicate_alias_groups"],
            "excluded_nonmicrobial_comparisons": quality[
                "excluded_nonmicrobial_comparisons"
            ],
        },
        "evidence_layer_sensitivity": {
            "strata_analyzed": layers["strata_analyzed"],
            "conclusion_counts": layers["conclusion_counts"],
            "combination_ranking_enabled": layers["combination_ranking_enabled"],
            "interpretation": (
                "Any interval support confined to a stricter subset is treated as possible "
                "selection sensitivity, not confirmation of efficacy."
            ),
        },
        "next_curation_batch": {
            "eligible_primary_trials": int(len(queue)),
            "trials_with_ci_or_sd": int((queue["has_ci"] | queue["has_sd"]).sum()),
            "review_like_titles_remaining": int(
                queue["title"].fillna("").str.contains("review|meta-analysis", case=False).sum()
            ),
            "outcome_review_draft": (
                f"data/intervention_data/outcome_review_worksheet.variance_rich_draft_{stamp}.csv"
            ),
            "intervention_review_draft": (
                f"data/intervention_data/intervention_review_worksheet.variance_rich_draft_{stamp}.csv"
            ),
        },
        "artifacts": {
            "arms": str(arms_path.relative_to(ROOT)).replace("\\", "/"),
            "effects": str(effects_path.relative_to(ROOT)).replace("\\", "/"),
            "model_metrics": str(metrics_path.relative_to(ROOT)).replace("\\", "/"),
            "meta_analysis": str(meta_path.relative_to(ROOT)).replace("\\", "/"),
            "missing_variance_robustness": str(robustness_path.relative_to(ROOT)).replace(
                "\\", "/"
            ),
            "body_fat_hypothesis_audit": str(
                body_fat_audit_path.relative_to(ROOT)
            ).replace("\\", "/"),
            "effect_quality_audit": str(quality_path.relative_to(ROOT)).replace("\\", "/"),
            "evidence_layer_sensitivity": str(layer_path.relative_to(ROOT)).replace(
                "\\", "/"
            ),
            "curation_queue": str(queue_path.relative_to(ROOT)).replace("\\", "/"),
        },
    }
    output = ROOT / f"results/prediction_results/continuous_effect_upgrade_status_{stamp}.json"
    output.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(output)


if __name__ == "__main__":
    main()
