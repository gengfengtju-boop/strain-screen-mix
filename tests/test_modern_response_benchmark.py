from proslim_ai.modern_response_benchmark import _modern_candidates, _promotion_decision


def test_modern_candidates_include_dependency_free_baselines() -> None:
    candidates, _ = _modern_candidates(["sample_size", "duration_weeks"])

    assert "logistic_l2_strong" in candidates
    assert "hist_gradient_boosting_regularized" in candidates
    assert "extra_trees_regularized" in candidates


def test_promotion_requires_gain_and_external_style_stability() -> None:
    baseline = {
        "model": "baseline",
        "repeated_roc_auc_mean": 0.65,
        "leave_one_study_out": {
            "roc_auc": 0.66,
            "study_equal_roc_auc": 0.64,
            "cluster_bootstrap_roc_auc_p025": 0.51,
            "average_precision": 0.60,
            "positive_prevalence": 0.40,
        },
    }
    candidate = {
        "model": "modern",
        "repeated_roc_auc_mean": 0.67,
        "leave_one_study_out": {
            "roc_auc": 0.67,
            "study_equal_roc_auc": 0.65,
            "cluster_bootstrap_roc_auc_p025": 0.52,
            "average_precision": 0.61,
            "positive_prevalence": 0.40,
        },
    }

    promoted, reasons = _promotion_decision(candidate, baseline, minimum_auc_gain=0.01)

    assert promoted is True
    assert reasons == ["all_promotion_checks_passed"]


def test_promotion_rejects_auc_gain_with_worse_study_equal_auc() -> None:
    baseline = {
        "model": "baseline",
        "repeated_roc_auc_mean": 0.65,
        "leave_one_study_out": {
            "roc_auc": 0.66,
            "study_equal_roc_auc": 0.64,
            "cluster_bootstrap_roc_auc_p025": 0.51,
            "average_precision": 0.60,
            "positive_prevalence": 0.40,
        },
    }
    candidate = {
        "model": "modern",
        "repeated_roc_auc_mean": 0.68,
        "leave_one_study_out": {
            "roc_auc": 0.67,
            "study_equal_roc_auc": 0.62,
            "cluster_bootstrap_roc_auc_p025": 0.52,
            "average_precision": 0.61,
            "positive_prevalence": 0.40,
        },
    }

    promoted, reasons = _promotion_decision(candidate, baseline, minimum_auc_gain=0.01)

    assert promoted is False
    assert "study_equal_auc_not_lower" in reasons
