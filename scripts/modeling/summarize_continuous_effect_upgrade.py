from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

import pandas as pd

from proslim_ai.run_stamp import production_run_stamp


ROOT = Path(__file__).resolve().parents[2]


def _json(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> None:
    stamp = production_run_stamp()
    report_date = datetime.strptime(stamp, "%Y%m%d").date().isoformat()
    result_dir = ROOT / "results/prediction_results"
    arms_path = ROOT / f"data/intervention_data/study_arm_registry.upgrade_{stamp}.csv"
    effects_path = ROOT / f"data/intervention_data/continuous_effect_sizes.upgrade_{stamp}.csv"
    metrics_path = result_dir / f"continuous_effect_model_metrics_{stamp}.json"
    meta_path = result_dir / f"effect_meta_analysis_hksj_{stamp}.json"
    robust_path = result_dir / f"missing_variance_robustness_{stamp}.json"
    quality_path = result_dir / f"effect_quality_report_{stamp}.json"
    layers_path = result_dir / f"evidence_layer_sensitivity_{stamp}.json"
    body_path = result_dir / f"body_fat_hypothesis_audit_{stamp}.json"
    feature_path = result_dir / f"intervention_feature_completeness_{stamp}.json"
    partial_pooling_path = result_dir / f"partial_pooling_effect_metrics_{stamp}.json"
    external_validation_path = result_dir / f"external_validation_readiness_{stamp}.json"
    direct_gap_path = result_dir / f"direct_variance_gap_report_{stamp}.json"
    direct_candidate_path = result_dir / f"direct_variance_candidate_report_{stamp}.json"
    balanced_n_path = result_dir / f"balanced_arm_n_sensitivity_{stamp}.json"

    arms = pd.read_csv(arms_path)
    effects = pd.read_csv(effects_path)
    metrics = _json(metrics_path)
    meta = _json(meta_path)
    robust = _json(robust_path)
    quality = _json(quality_path)
    layers = _json(layers_path)
    body = _json(body_path)
    feature_report = _json(feature_path)
    partial_pooling = _json(partial_pooling_path)
    external_validation = _json(external_validation_path)
    direct_gap = _json(direct_gap_path)
    direct_candidates = _json(direct_candidate_path)
    balanced_n = _json(balanced_n_path)
    high = effects[effects["confidence"].fillna("").str.lower().eq("high")]
    direct = high[high["variance_provenance"].isin(["reported_ci", "arm_sd_and_n"])]

    analyzed_meta = [
        {
            key: row.get(key)
            for key in (
                "stratum",
                "k_studies",
                "pooled_effect",
                "ci95_low",
                "ci95_high",
                "i2_percent",
                "prediction_interval_low",
                "prediction_interval_high",
                "evidence_state",
                "replication_ready",
            )
        }
        for row in meta["strata"]
        if row.get("status") == "random_effects_meta_analyzed"
    ]
    report = {
        "date": report_date,
        "upgrade": "pinned arm-level continuous effects with leakage-safe validation",
        "input_manifest": "config/continuous_effect_upgrade_manifest.json",
        "arm_registry": {
            "studies": int(arms["study_id"].nunique()),
            "arms": int(len(arms)),
        },
        "continuous_effects": {
            "rows_all_confidence": int(len(effects)),
            "studies_all_confidence": int(effects["evidence_id"].nunique()),
            "high_confidence_rows": int(len(high)),
            "high_confidence_studies": int(high["evidence_id"].nunique()),
            "direct_variance_high_confidence_rows": int(len(direct)),
            "direct_variance_high_confidence_studies": int(direct["evidence_id"].nunique()),
            "pvalue_backcalculated_rows": int(
                high["variance_provenance"].eq("pvalue_backcalculated").sum()
            ),
        },
        "predictive_model": {
            "modeled_strata": metrics["modeled_strata"],
            "strata_beating_null_baseline": metrics["strata_beating_null_baseline"],
            "minimum_relative_mae_improvement": 0.10,
            "model_status": metrics["model_status"],
            "combination_ranking_enabled": False,
        },
        "small_sample_meta_analysis": {
            "strata_meta_analyzed": meta["strata_meta_analyzed"],
            "strata_with_ci_excluding_zero": meta[
                "strata_with_pooled_effect_excluding_zero"
            ],
            "strata_replication_ready": meta["strata_replication_ready"],
            "strata": analyzed_meta,
        },
        "missing_variance_robustness": {
            "strata_analyzed": robust["strata_analyzed"],
            "evidence_state_counts": robust["evidence_state_counts"],
            "pvalue_backcalculated_variance_policy": "treated_as_missing",
        },
        "effect_quality_audit": quality,
        "evidence_layer_sensitivity": {
            "strata_analyzed": layers["strata_analyzed"],
            "conclusion_counts": layers["conclusion_counts"],
        },
        "body_fat_hypothesis_audit": body,
        "direct_variance_curation": direct_gap,
        "direct_variance_candidate_patch": direct_candidates,
        "balanced_arm_n_sensitivity": balanced_n,
        "intervention_feature_completeness": feature_report,
        "partial_pooling_baseline": partial_pooling,
        "external_validation_readiness": external_validation,
        "overall_decision": (
            "continuous_effect_model_not_enabled_for_combination_ranking; "
            "retain endpoint findings as replication hypotheses"
        ),
        "artifacts": {
            "arms": str(arms_path.relative_to(ROOT)).replace("\\", "/"),
            "effects": str(effects_path.relative_to(ROOT)).replace("\\", "/"),
            "model_metrics": str(metrics_path.relative_to(ROOT)).replace("\\", "/"),
            "meta_analysis": str(meta_path.relative_to(ROOT)).replace("\\", "/"),
            "missing_variance_robustness": str(robust_path.relative_to(ROOT)).replace(
                "\\", "/"
            ),
            "partial_pooling_metrics": str(partial_pooling_path.relative_to(ROOT)).replace(
                "\\", "/"
            ),
            "external_validation_readiness": str(
                external_validation_path.relative_to(ROOT)
            ).replace("\\", "/"),
            "direct_variance_candidate_report": str(
                direct_candidate_path.relative_to(ROOT)
            ).replace("\\", "/"),
            "balanced_arm_n_sensitivity": str(
                balanced_n_path.relative_to(ROOT)
            ).replace("\\", "/"),
        },
    }
    output = result_dir / f"continuous_effect_upgrade_status_{stamp}.json"
    output.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(output)


if __name__ == "__main__":
    main()
