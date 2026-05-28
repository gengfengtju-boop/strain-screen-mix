from pathlib import Path

import pandas as pd

from proslim_ai.finalize import finalize_clinical_outcomes


def test_finalize_clinical_outcomes_uses_extracted_rows_only():
    root = Path(__file__).resolve().parents[1]
    draft = root / "tests" / "fixtures" / "clinical_outcome_finalize_draft.csv"
    review = root / "tests" / "fixtures" / "outcome_review_extracted.csv"
    output = root / "tests" / "fixtures" / "clinical_outcome.final.out.csv"

    try:
        result = finalize_clinical_outcomes(root / "config", draft, review, output)

        assert result.extracted_review_rows == 1
        frame = pd.read_csv(output, dtype=str).fillna("")
        assert frame.loc[0, "weight_change"] == "-1.2"
        assert frame.loc[0, "BMI_change"] == ""
    finally:
        output.unlink(missing_ok=True)

