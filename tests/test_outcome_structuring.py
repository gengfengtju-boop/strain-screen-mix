from proslim_ai.outcome_structuring import _extract_effects, _split_p_values


def test_effect_parser_uses_first_value_from_each_labeled_group() -> None:
    intervention, control, method, warning = _extract_effects(
        "probiotic 0 (-0.3; 0) vs control 0 (-0.1; 0.2)"
    )

    assert intervention == "0"
    assert control == "0"
    assert method == "labeled_groups_split_on_vs"
    assert warning == ""


def test_effect_parser_marks_single_group_values() -> None:
    intervention, control, method, warning = _extract_effects("synbiotic -4.21")

    assert intervention == "-4.21"
    assert control == ""
    assert method == "single_group_or_unlabeled_value"
    assert warning == "control effect unavailable"


def test_p_value_parser_separates_between_and_within_values() -> None:
    between, within, method, warning = _split_p_values(
        "0.588 between-group; 0.007 within intervention"
    )

    assert between == "0.588"
    assert within == "0.007"
    assert method == "explicit_between_group"
    assert warning == ""


def test_p_value_parser_warns_on_multiple_unlabeled_values() -> None:
    between, within, method, warning = _split_p_values("0.02 for arm A; 0.28 for arm B")

    assert between == "0.02"
    assert within == ""
    assert method == "unlabeled_first_p_value"
    assert warning == "multiple unlabeled P values; first retained"
