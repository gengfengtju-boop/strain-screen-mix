from pathlib import Path

import pandas as pd

from proslim_ai.cleaning import clean_sample_metadata


def test_clean_sample_metadata():
    root = Path(__file__).resolve().parents[1]
    input_path = root / "tests" / "fixtures" / "sample_metadata_dirty.csv"
    output_path = root / "tests" / "fixtures" / "sample_metadata_clean.out.csv"

    try:
        summary = clean_sample_metadata(root / "config", input_path, output_path)

        assert summary.rows_in == 2
        assert summary.rows_out == 2
        assert summary.added_columns == ["age_missing"]

        frame = pd.read_csv(output_path)
        assert frame.loc[0, "sex"] == "male"
        assert frame.loc[0, "time_point"] == "baseline"
        assert frame.loc[0, "obesity_status"] == "lean"
        assert frame.loc[1, "time_point"] == "post"
        assert frame.loc[1, "obesity_status"] == "obesity"
        assert bool(frame.loc[1, "age_missing"])
    finally:
        output_path.unlink(missing_ok=True)
