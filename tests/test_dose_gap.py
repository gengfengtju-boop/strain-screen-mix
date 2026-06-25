import pandas as pd

from proslim_ai.dose_gap import build_dose_gap_queue


def test_build_dose_gap_queue_excludes_non_microbial_interventions(tmp_path) -> None:
    outcomes = tmp_path / "outcomes.csv"
    review = tmp_path / "review.csv"
    intervention_review = tmp_path / "intervention_review.csv"
    output = tmp_path / "output.csv"
    pd.DataFrame(
        [
            {
                "evidence_id": "PMID:1",
                "outcome_domain": "weight",
                "endpoint_type": "adiposity",
                "analysis_population": "aggregate_trial",
                "comparison": "probiotic_vs_control",
                "positive_efficacy_label": "yes",
            },
            {
                "evidence_id": "PMID:2",
                "outcome_domain": "weight",
                "endpoint_type": "adiposity",
                "analysis_population": "aggregate_trial",
                "comparison": "diet_vs_control",
                "positive_efficacy_label": "no",
            },
        ]
    ).to_csv(outcomes, index=False)
    pd.DataFrame(
        [
            {
                "evidence_id": "PMID:1",
                "outcome_domain": "weight",
                "review_status": "extracted",
                "title": "Double-blind probiotic trial",
                "sample_size_confirmed": "n=80",
            },
            {
                "evidence_id": "PMID:2",
                "outcome_domain": "weight",
                "review_status": "extracted",
                "title": "Calorie restriction trial",
                "sample_size_confirmed": "n=80",
            },
        ]
    ).to_csv(review, index=False)
    pd.DataFrame(
        [
            {
                "evidence_id": "PMID:1",
                "review_status": "pending",
                "suggested_cfu": "3 x 10^10 CFU/day",
            }
        ]
    ).to_csv(intervention_review, index=False)
    try:
        queue = build_dose_gap_queue(outcomes, [review, intervention_review], output)
        assert queue["evidence_id"].tolist() == ["PMID:1"]
        assert queue.iloc[0]["review_status"] == "pending_manual_dose_review"
        assert queue.iloc[0]["suggested_cfu"] == "3 x 10^10 CFU/day"
        assert "3 x 10^10 CFU/day" in queue.iloc[0]["existing_dose_text"]
    finally:
        outcomes.unlink(missing_ok=True)
        review.unlink(missing_ok=True)
        intervention_review.unlink(missing_ok=True)
        output.unlink(missing_ok=True)
