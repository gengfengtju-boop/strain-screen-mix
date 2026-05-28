from pathlib import Path

import pandas as pd

from proslim_ai.preliminary_prediction import build_preliminary_predictions


def test_build_preliminary_predictions_ranks_stronger_evidence_first():
    root = Path(__file__).resolve().parents[1]
    screening = root / "tests" / "fixtures" / "screening_for_prediction.csv"
    hints = root / "tests" / "fixtures" / "hints_for_prediction.csv"
    output = root / "tests" / "fixtures" / "preliminary_predictions.out.csv"

    try:
        result = build_preliminary_predictions(root / "config", screening, hints, output)

        assert result.rows_written == 2
        frame = pd.read_csv(output, dtype=str)
        assert frame.loc[0, "evidence_id"] == "PMID:1"
        assert float(frame.loc[0, "preliminary_response_score"]) > float(
            frame.loc[1, "preliminary_response_score"]
        )
        assert frame.loc[0, "predicted_usefulness"] == "prioritize_extraction"
    finally:
        output.unlink(missing_ok=True)

