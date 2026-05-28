from pathlib import Path

import pandas as pd

from proslim_ai.extraction import build_extraction_drafts


def test_build_extraction_drafts_from_screening():
    root = Path(__file__).resolve().parents[1]
    screening = root / "tests" / "fixtures" / "evidence_screening_for_extraction.csv"
    intervention_output = root / "tests" / "fixtures" / "intervention_metadata.out.csv"
    outcome_output = root / "tests" / "fixtures" / "clinical_outcome.out.csv"

    try:
        result = build_extraction_drafts(
            root / "config",
            screening,
            intervention_output,
            outcome_output,
        )

        assert result.intervention_rows == 1
        intervention = pd.read_csv(intervention_output)
        outcome = pd.read_csv(outcome_output)
        assert intervention.loc[0, "intervention_type"] == "probiotic"
        assert str(intervention.loc[0, "publication_pmid"]) == "1"
        assert intervention.loc[0, "probiotic_species"] == "Lactobacillus gasseri"
        assert "SBT2055" in intervention.loc[0, "probiotic_strain"]
        assert outcome.loc[0, "weight_change"] == "needs_manual_extraction"
        assert outcome.loc[0, "FBG_change"] == "needs_manual_extraction"
    finally:
        intervention_output.unlink(missing_ok=True)
        outcome_output.unlink(missing_ok=True)
