from pathlib import Path

import pandas as pd

from proslim_ai.review import build_review_worksheets


def test_build_review_worksheets_creates_long_form_rows():
    root = Path(__file__).resolve().parents[1]
    hints = root / "tests" / "fixtures" / "extraction_hints_for_review.csv"
    outcome_output = root / "tests" / "fixtures" / "outcome_review.out.csv"
    intervention_output = root / "tests" / "fixtures" / "intervention_review.out.csv"

    try:
        result = build_review_worksheets(
            root / "config",
            hints,
            outcome_output,
            intervention_output,
            reviewer="fg",
        )

        assert result.evidence_rows == 1
        assert result.outcome_rows == 2
        assert result.intervention_rows == 1

        outcome = pd.read_csv(outcome_output, dtype=str).fillna("")
        intervention = pd.read_csv(intervention_output, dtype=str).fillna("")
        assert set(outcome["outcome_domain"]) == {"weight", "BMI"}
        assert set(outcome["review_status"]) == {"pending"}
        assert intervention.loc[0, "suggested_cfu"] == "3 x 10^10 CFU/day"
        assert intervention.loc[0, "reviewer"] == "fg"
    finally:
        outcome_output.unlink(missing_ok=True)
        intervention_output.unlink(missing_ok=True)

