from __future__ import annotations

import json
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[2]
RESULTS = ROOT / "results/prediction_results"


def read_json(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


def metric_summary(metrics: dict[str, object]) -> dict[str, object]:
    logo = metrics["leave_one_group_out_metrics"]
    return {
        "repeated_auc_mean": metrics["roc_auc_mean"],
        "repeated_auc_std": metrics["roc_auc_std"],
        "leave_one_study_out_auc": logo["roc_auc"],
        "study_equal_auc": logo["study_equal_roc_auc"],
        "bootstrap_auc_p025": logo["cluster_bootstrap_roc_auc_p025"],
        "model_status": metrics["model_status"],
    }


def main() -> None:
    review_path = (
        ROOT
        / "data/intervention_data/intervention_review_worksheet.expanded_top160.dose_confirmed_v4_20260612.csv"
    )
    queue_path = RESULTS / "microbial_cfu_dose_gap_queue.dose_v4_20260612.csv"
    review = pd.read_csv(review_path)
    confirmed = review[review["review_status"].fillna("").str.lower() == "extracted"].copy()
    queue = pd.read_csv(queue_path)
    current = read_json(RESULTS / "study_endpoint_response_model_metrics.dose_v4_20260612.json")
    previous = read_json(RESULTS / "study_endpoint_response_model_metrics.dose_v3_20260612.json")
    modern = read_json(RESULTS / "modern_response_algorithm_benchmark.dose_v4_20260612.json")

    audit = {
        "date": "2026-06-12",
        "batch": "dose_v4_primary_source_confirmation",
        "newly_confirmed_evidence_ids": [
            "PMID:35845797",
            "PMID:38999741",
            "PMID:37111082",
            "PMID:40416368",
            "PMID:34434546",
            "PMID:36606510",
            "EUROPEPMC:40676704",
        ],
        "confirmed_rows_total": int(len(confirmed)),
        "remaining_gap_evidence_ids": queue["evidence_id"].astype(str).tolist(),
        "remaining_gap_count": int(len(queue)),
        "arm_specific_pending": {
            "PMID:37447365": (
                "Two active arms have different measured daily doses: probiotic 5.46e9 "
                "and synbiotic 1.97e9 CFU/day."
            )
        },
        "primary_sources": [
            "https://pmc.ncbi.nlm.nih.gov/articles/PMC9286749/",
            "https://pmc.ncbi.nlm.nih.gov/articles/PMC11243028/",
            "https://pmc.ncbi.nlm.nih.gov/articles/PMC10141052/",
            "https://pmc.ncbi.nlm.nih.gov/articles/PMC12100662/",
            "https://pmc.ncbi.nlm.nih.gov/articles/PMC8376682/",
            "https://pmc.ncbi.nlm.nih.gov/articles/PMC10000630/",
            "https://pmc.ncbi.nlm.nih.gov/articles/PMC12273011/",
            "https://pmc.ncbi.nlm.nih.gov/articles/PMC10346309/",
        ],
    }
    status = {
        "date": "2026-06-12",
        "update": "second primary-source dose enrichment and grouped model revalidation",
        "dose_coverage_rows": {"before": 33, "after": 58},
        "dose_coverage_studies": {"before": 10, "after": 17},
        "remaining_dose_gap_studies": int(len(queue)),
        "validation_before": metric_summary(previous),
        "validation_after": metric_summary(current),
        "modern_benchmark": {
            "selected_model": modern["selected_model"],
            "promoted_model": modern["promoted_model"],
            "decision": modern["decision"],
        },
        "decision": "retain_probability_gate_and_do_not_apply_model_to_combinations",
        "combination_output": (
            "results/combination_ranking/model_response_3to5_strain_combinations.dose_v4_20260612.csv"
        ),
        "combinations_with_model_probability": 0,
        "interpretation": (
            "Broader confirmed-dose coverage reduced apparent discrimination. Dose alone, "
            "sample size, and duration do not support stable cross-study response ranking in "
            "the current 37-study evidence set."
        ),
    }

    (RESULTS / "intervention_dose_confirmation_audit_v4_20260612.json").write_text(
        json.dumps(audit, indent=2), encoding="utf-8"
    )
    (RESULTS / "response_model_data_update_status_v4_20260612.json").write_text(
        json.dumps(status, indent=2), encoding="utf-8"
    )


if __name__ == "__main__":
    main()
