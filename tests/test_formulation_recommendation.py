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
