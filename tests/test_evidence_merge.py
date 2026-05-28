from pathlib import Path

import pandas as pd

from proslim_ai.evidence_merge import merge_evidence_candidates


def test_merge_evidence_candidates_deduplicates_by_pmid():
    root = Path(__file__).resolve().parents[1]
    output_path = root / "tests" / "fixtures" / "evidence_registry_merged.out.csv"
    inputs = [
        root / "tests" / "fixtures" / "evidence_candidates_pubmed_a.csv",
        root / "tests" / "fixtures" / "evidence_candidates_europepmc_overlap.csv",
    ]

    try:
        result = merge_evidence_candidates(root / "config", inputs, output_path)

        assert result.rows_read == 4
        assert result.rows_written == 3
        assert result.duplicates_removed == 1

        frame = pd.read_csv(output_path)
        assert set(frame["pmid"].astype(str)) == {"111", "222", "333"}
    finally:
        output_path.unlink(missing_ok=True)

