from pathlib import Path

from proslim_ai.review_validation import validate_outcome_review


def test_validate_outcome_review_requires_final_fields_for_extracted_rows():
    root = Path(__file__).resolve().parents[1]
    review = root / "tests" / "fixtures" / "outcome_review_invalid_extracted.csv"

    result = validate_outcome_review(review)

    assert not result.ok
    assert any("missing final_unit" in error for error in result.errors)
    assert any("missing p_value_confirmed" in error for error in result.errors)

