from pathlib import Path

import pandas as pd

from proslim_ai.screening import screen_evidence_registry


def test_screen_evidence_registry_tags_priority_and_hints():
    root = Path(__file__).resolve().parents[1]
    input_path = root / "tests" / "fixtures" / "evidence_registry_screening.csv"
    output_path = root / "tests" / "fixtures" / "evidence_screening.out.csv"

    try:
        result = screen_evidence_registry(root / "config", input_path, output_path)

        assert result.rows_written == 3
        frame = pd.read_csv(output_path)
        assert "high" in set(frame["priority"])
        assert frame["relevance_score"].max() >= 1
        assert "randomized_controlled_trial" in set(frame["study_tag"])
        assert any(frame["taxa_hint"].fillna("").str.contains("Lactobacillus"))
        assert any(frame["outcome_hint"].fillna("").str.contains("weight"))
    finally:
        output_path.unlink(missing_ok=True)
