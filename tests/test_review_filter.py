from pathlib import Path

import pandas as pd

from proslim_ai.review_filter import filter_review_worksheet


def test_filter_review_worksheet_keeps_high_and_medium():
    root = Path(__file__).resolve().parents[1]
    predictions = root / "tests" / "fixtures" / "predictions_for_review_filter.csv"
    review = root / "tests" / "fixtures" / "outcome_review_for_filter.csv"
    output = root / "tests" / "fixtures" / "outcome_review.filtered.out.csv"

    try:
        result = filter_review_worksheet(
            predictions,
            review,
            output,
            {"high_for_manual_review", "medium_for_manual_review"},
        )

        assert result.selected_evidence == 2
        assert result.rows_written == 3
        frame = pd.read_csv(output, dtype=str)
        assert set(frame["evidence_id"]) == {"PMID:1", "PMID:3"}
    finally:
        output.unlink(missing_ok=True)

