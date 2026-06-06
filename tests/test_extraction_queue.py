from pathlib import Path

import pandas as pd

from proslim_ai.extraction_queue import build_extraction_queue


def test_build_extraction_queue_filters_sorts_and_excludes():
    root = Path(__file__).resolve().parents[1]
    screening = root / "tests" / "fixtures" / "screening_for_queue.csv"
    output = root / "tests" / "fixtures" / "extraction_queue.out.csv"
    exclude = root / "tests" / "fixtures" / "queue_exclude.csv"
    screening.write_text(
        "\n".join(
            [
                "evidence_id,priority,relevance_score,year,study_tag,taxa_hint,outcome_hint,title",
                "PMID:1,medium,5,2024,randomized_controlled_trial,Lactobacillus,weight,A",
                "PMID:2,high,1,2020,review,,BMI,B",
                "PMID:3,high,4,2025,clinical_trial_registry,Bifidobacterium,body_composition,C",
                "PMID:4,lower,9,2026,preclinical_or_animal,Akkermansia,weight,D",
            ]
        ),
        encoding="utf-8",
    )
    exclude.write_text("evidence_id\nPMID:2\n", encoding="utf-8")

    try:
        result = build_extraction_queue(
            screening,
            output,
            priority_levels={"high", "medium"},
            top_n=2,
            min_relevance_score=1,
            exclude_paths=[exclude],
        )

        assert result.rows_read == 4
        assert result.excluded_evidence == 1
        assert result.rows_written == 2

        frame = pd.read_csv(output, dtype=str)
        assert list(frame["evidence_id"]) == ["PMID:3", "PMID:1"]
        assert list(frame["queue_rank"]) == ["1", "2"]
        assert "priority=high" in frame.loc[0, "queue_reason"]
    finally:
        screening.unlink(missing_ok=True)
        output.unlink(missing_ok=True)
        exclude.unlink(missing_ok=True)
