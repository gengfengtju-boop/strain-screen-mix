from proslim_ai.formulation_recommendation import _build_combination_rows


def test_recombined_combinations_allow_split_members_with_penalty() -> None:
    rows = _build_combination_rows(min_strains=3, max_strains=5, top_n=50)

    split_rows = [row for row in rows if float(row["split_evidence_penalty"]) > 0]

    assert rows
    assert split_rows
    assert all(3 <= int(row["total_strain_count"]) <= 5 for row in rows)


def test_top_combination_prioritizes_complementary_retained_formulations() -> None:
    rows = _build_combination_rows(min_strains=3, max_strains=5, top_n=1)
    top = rows[0]

    assert "FORM_LF_K7_K8_K11" in top["formulation_blocks"]
    assert "FORM_BB536_MCC1274" in top["formulation_blocks"]
    assert float(top["synergy_score"]) >= 9.0
    assert float(top["original_formulation_recovery_score"]) == 10.0


def test_pending_safety_combinations_are_hypotheses_not_response_predictions() -> None:
    row = _build_combination_rows(min_strains=3, max_strains=3, top_n=1)[0]

    assert row["ranking_type"] == "preclinical_hypothesis_not_response_probability"
    assert row["hypothesis_priority"]
    assert row["predicted_response_score"] == ""
    assert row["safety_eligible_for_validation"] == "no"
    assert row["validation_priority"] == ""


def test_failed_safety_strain_is_excluded_from_all_combinations() -> None:
    rows = _build_combination_rows(
        min_strains=3,
        max_strains=5,
        top_n=50,
        safety_statuses={"LF_K7": "fail"},
    )

    assert rows
    assert all("LF_K7" not in row["source_strain_ids"] for row in rows)
