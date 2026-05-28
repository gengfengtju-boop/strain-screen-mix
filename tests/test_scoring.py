from proslim_ai.scoring import StrainScore, score_combination, score_strain


def test_score_strain_applies_safety_gate():
    weights = {
        "SCFA_functional_fit": 0.5,
        "bile_acid_metabolism_fit": 0.5,
    }
    passed = StrainScore(
        strain_id="A",
        safety_gate="pass",
        SCFA_functional_fit=1.0,
        bile_acid_metabolism_fit=0.5,
    )
    failed = StrainScore(
        strain_id="B",
        safety_gate="fail",
        SCFA_functional_fit=1.0,
        bile_acid_metabolism_fit=1.0,
    )
    assert score_strain(passed, weights) == 0.75
    assert score_strain(failed, weights) == 0.0


def test_score_combination_applies_safety_gate():
    weights = {
        "complementarity_score": 0.5,
        "microbiome_matching_score": 0.5,
    }
    components = {
        "complementarity_score": 0.8,
        "microbiome_matching_score": 0.6,
    }
    score = score_combination("C1", ("A", "B"), components, weights, safety_passed=True)
    failed = score_combination("C2", ("A", "B"), components, weights, safety_passed=False)
    assert score.total_score == 0.7
    assert failed.total_score == 0.0

