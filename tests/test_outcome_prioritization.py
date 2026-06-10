from proslim_ai.outcome_prioritization import _aggregate_domain_scores


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
