import csv
import json

import pandas as pd
import pytest
from sklearn.dummy import DummyClassifier

from proslim_ai.response_model import (
    EXCLUDED_LABEL_DERIVED_FEATURES,
    LEAKAGE_SAFE_CATEGORICAL_FEATURES,
    _build_model,
    _select_feature_profile,
    apply_response_model_to_combinations,
    train_response_model,
)


def _structured_rows() -> pd.DataFrame:
    rows = []
    for study in range(8):
        for endpoint, domain in enumerate(("weight", "glucose")):
            positive = (study + endpoint) % 3 == 0
            rows.append(
                {
                    "evidence_id": f"PMID:{1000 + study}",
                    "outcome_domain": domain,
                    "endpoint_type": "adiposity" if domain == "weight" else "metabolic",
                    "analysis_population": "aggregate_trial",
                    "comparison": "intervention_vs_control",
                    "intervention_effect": -2.0 if positive else -0.2,
                    "control_effect": -0.1,
                    "effect_difference": -1.9 if positive else -0.1,
                    "between_group_p": 0.01 if positive else 0.4,
                    "within_group_p": 0.02 if positive else 0.5,
                    "direction": "decrease" if positive else "no significant effect",
                    "evidence_modifier": "" if positive else "between_group_not_significant",
                    "positive_efficacy_label": "yes" if positive else "no",
                }
            )
    return pd.DataFrame(rows)


def _test_paths(tmp_path):
    paths = [tmp_path / name for name in (
        "structured.csv", "rows.csv", "evidence.csv", "metrics.json", "model.pkl"
    )]
    return paths


def test_training_excludes_label_derived_features_and_uses_nested_groups(monkeypatch, tmp_path) -> None:
    paths = _test_paths(tmp_path)
    structured, rows_output, evidence_output, metrics_output, model_output = paths
    _structured_rows().to_csv(structured, index=False)

    def fast_candidates(numeric_features, categorical_features):
        return {
            "dummy_prior": _build_model(
                numeric_features,
                categorical_features,
                DummyClassifier(strategy="prior"),
            )
        }

    try:
        monkeypatch.setattr("proslim_ai.response_model._model_candidates", fast_candidates)
        train_response_model(structured, rows_output, evidence_output, metrics_output, model_output)

        metrics = json.loads(metrics_output.read_text(encoding="utf-8"))
        assert metrics["validation"].startswith("nested_stratified_group_cross_validated")
        assert metrics["feature_policy"] == "leakage_safe_descriptors_only"
        assert metrics["excluded_leakage_features"] == EXCLUDED_LABEL_DERIVED_FEATURES
        assert not set(EXCLUDED_LABEL_DERIVED_FEATURES) & set(LEAKAGE_SAFE_CATEGORICAL_FEATURES)
        assert metrics["model_status"] == "non_informative_do_not_apply_to_combinations"
    finally:
        for path in paths:
            path.unlink(missing_ok=True)


def test_training_accepts_review_features(monkeypatch, tmp_path) -> None:
    paths = _test_paths(tmp_path)
    structured, rows_output, evidence_output, metrics_output, model_output = paths
    review = tmp_path / "review.csv"
    source = _structured_rows()
    source.to_csv(structured, index=False)
    pd.DataFrame(
        {
            "evidence_id": source["evidence_id"],
            "outcome_domain": source["outcome_domain"],
            "review_status": "extracted",
            "sample_size_confirmed": "n=80",
            "time_point": "12 weeks",
            "title": "Randomized double-blind probiotic trial in adults with obesity",
        }
    ).to_csv(review, index=False)

    def fast_candidates(numeric_features, categorical_features):
        assert "sample_size" in numeric_features
        assert "intervention_class" in categorical_features
        return {
            "dummy_prior": _build_model(
                numeric_features,
                categorical_features,
                DummyClassifier(strategy="prior"),
            )
        }

    try:
        monkeypatch.setattr("proslim_ai.response_model._model_candidates", fast_candidates)
        train_response_model(
            structured,
            rows_output,
            evidence_output,
            metrics_output,
            model_output,
            review_paths=[review],
        )
        metrics = json.loads(metrics_output.read_text(encoding="utf-8"))
        assert metrics["review_rows_matched"] == len(source)
        assert metrics["review_feature_coverage"] == 1.0
        assert "duration_weeks" in metrics["features"]
    finally:
        review.unlink(missing_ok=True)
        for path in paths:
            path.unlink(missing_ok=True)


def test_training_can_lock_prespecified_model(monkeypatch, tmp_path) -> None:
    paths = _test_paths(tmp_path)
    structured, rows_output, evidence_output, metrics_output, model_output = paths
    _structured_rows().to_csv(structured, index=False)

    def fast_candidates(numeric_features, categorical_features):
        return {
            "locked_dummy": _build_model(
                numeric_features,
                categorical_features,
                DummyClassifier(strategy="prior"),
            )
        }

    try:
        monkeypatch.setattr("proslim_ai.response_model._model_candidates", fast_candidates)
        train_response_model(
            structured,
            rows_output,
            evidence_output,
            metrics_output,
            model_output,
            cv_repeats=2,
            locked_model="locked_dummy",
        )
        metrics = json.loads(metrics_output.read_text(encoding="utf-8"))
        assert metrics["selected_model"] == "locked_dummy"
        assert metrics["validation"].startswith("locked_repeated_")
        assert len(metrics["repeat_metrics"]) == 2
        assert metrics["leave_one_group_out_metrics"] is not None
        assert "study_equal_roc_auc" in metrics["leave_one_group_out_metrics"]
    finally:
        for path in paths:
            path.unlink(missing_ok=True)


def test_non_informative_classifier_is_not_applied_to_combinations(tmp_path) -> None:
    evidence = tmp_path / "evidence.csv"
    combinations = tmp_path / "combinations.csv"
    output = tmp_path / "combination_output.csv"
    status = tmp_path / "status.json"
    status.write_text(
        '{"predictive_model":{"model_status":"disabled","combination_ranking_enabled":false}}',
        encoding="utf-8",
    )
    with evidence.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=["evidence_id", "study_level_evidence_probability", "model_status"],
        )
        writer.writeheader()
        writer.writerow(
            {
                "evidence_id": "PMID:123",
                "study_level_evidence_probability": "0.91",
                "model_status": "non_informative_do_not_apply_to_combinations",
            }
        )
    with combinations.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "combination_id",
                "evidence_pmid_list",
                "clinical_evidence_score",
                "combination_design_score",
                "predicted_response_score",
                "validation_priority",
            ],
        )
        writer.writeheader()
        writer.writerow(
            {
                "combination_id": "C1",
                "evidence_pmid_list": "123",
                "clinical_evidence_score": "5",
                "combination_design_score": "6",
                "predicted_response_score": "",
                "validation_priority": "5.5",
            }
        )

    try:
        result = apply_response_model_to_combinations(
            combinations,
            evidence,
            output,
            research_status_path=status,
            hypothesis_only=True,
        )
        with output.open(encoding="utf-8") as handle:
            row = next(csv.DictReader(handle))
        assert result.combinations_with_model_probability == 0
        assert row["predicted_response_probability"] == ""
        assert row["response_model_level"] == "no_matching_model_evidence"
    finally:
        evidence.unlink(missing_ok=True)
        combinations.unlink(missing_ok=True)
        output.unlink(missing_ok=True)
        status.unlink(missing_ok=True)


def test_combination_application_obeys_disabled_research_gate(tmp_path) -> None:
    status = tmp_path / "status.json"
    status.write_text(
        '{"predictive_model":{"model_status":"no_signal","combination_ranking_enabled":false}}',
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="disabled by the research status"):
        apply_response_model_to_combinations(
            tmp_path / "combinations.csv",
            tmp_path / "evidence.csv",
            tmp_path / "output.csv",
            research_status_path=status,
        )


def test_numeric_feature_profile_excludes_high_cardinality_categories() -> None:
    categorical, numeric = _select_feature_profile(
        ["comparison", "intervention_class"],
        ["sample_size", "duration_weeks", "log10_cfu_day"],
        "numeric_only",
    )
    assert categorical == []
    assert numeric == ["sample_size", "duration_weeks", "log10_cfu_day"]
