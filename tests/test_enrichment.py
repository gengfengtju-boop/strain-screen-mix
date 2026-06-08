from pathlib import Path

import pandas as pd

from proslim_ai.enrichment import enrich_prediction_hints


def test_enrich_prediction_hints_fills_intervention_and_taxa():
    root = Path(__file__).resolve().parents[1]
    predictions = root / "tests" / "fixtures" / "prediction_for_enrichment.csv"
    details = root / "tests" / "fixtures" / "details_for_enrichment.csv"
    output = root / "tests" / "fixtures" / "prediction_for_enrichment.out.csv"

    predictions.write_text(
        "\n".join(
            [
                "evidence_id,source_database,source_accession,title,intervention_type_hint,taxa_hint,study_tag,priority,relevance_score,preliminary_response_score,confidence_level,predicted_usefulness,main_positive_signals,main_limitations,source_url",
                "PMID:1,PubMed,1,Randomized probiotic trial in obesity,,,"
                "randomized_controlled_trial,high,4,12.0,high_for_manual_review,prioritize_extraction,signal,limitation,url",
            ]
        ),
        encoding="utf-8",
    )
    details.write_text(
        "\n".join(
            [
                "evidence_id,title,abstract,clinical_interventions,primary_outcomes,secondary_outcomes,arms",
                "PMID:1,Trial,Lactobacillus gasseri BNR17 improved body composition,Lactobacillus gasseri BNR17,body weight,,",
            ]
        ),
        encoding="utf-8",
    )

    try:
        result = enrich_prediction_hints(predictions, [details], output)

        assert result.intervention_filled == 1
        assert result.taxa_filled == 1
        frame = pd.read_csv(output, dtype=str).fillna("")
        row = frame.iloc[0]
        assert "probiotic" in row["enriched_intervention_type_hint"]
        assert "Lactobacillus gasseri" in row["enriched_taxa_hint"]
        assert "BNR17" in row["enriched_taxa_hint"]
    finally:
        predictions.unlink(missing_ok=True)
        details.unlink(missing_ok=True)
        output.unlink(missing_ok=True)
