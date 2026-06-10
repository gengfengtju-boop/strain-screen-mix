import pytest

from proslim_ai.outcome_prioritization import _aggregate_domain_scores, _score_extracted_outcome


def test_repeated_endpoints_are_averaged_within_domain() -> None:
    one_weight_endpoint = _aggregate_domain_scores({"weight": [2.0], "glucose": [1.0]})
    repeated_weight_endpoints = _aggregate_domain_scores(
        {"weight": [2.0, 2.0, 2.0], "glucose": [1.0]}
    )

    assert one_weight_endpoint == 3.0
    assert repeated_weight_endpoints == one_weight_endpoint


def test_conflicting_endpoints_reduce_domain_score() -> None:
    score = _aggregate_domain_scores({"weight": [2.0, -1.0]})

    assert score == 0.5


def test_completer_only_early_terminated_trial_is_penalized() -> None:
    score, _, limitation = _score_extracted_outcome(
        {
            "outcome_domain": "weight",
            "final_direction": "decrease",
            "comparison": "treatment_vs_placebo_completers",
            "p_value_confirmed": "<0.001",
            "final_value": "greater decrease",
            "sample_size_confirmed": "n=8 completers",
            "reviewer_note": "Trial terminated early after withdrawals.",
        }
    )

    assert score == pytest.approx(0.44)
    assert "high attrition or completer-only analysis" in limitation
