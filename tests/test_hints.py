from pathlib import Path

import pandas as pd

from proslim_ai.hints import _normalize_cfu_expression, extract_detail_hints


def test_normalize_cfu_expression_formats_exponent():
    assert _normalize_cfu_expression("3 × 1010 CFU/day") == "3 x 10^10 CFU/day"
    assert _normalize_cfu_expression("5.0 × 109 CFU") == "5.0 x 10^9 CFU"
    assert _normalize_cfu_expression("3 x 10^10 CFU/day") == "3 x 10^10 CFU/day"


def test_extract_detail_hints_finds_core_patterns():
    root = Path(__file__).resolve().parents[1]
    input_path = root / "tests" / "fixtures" / "evidence_details_for_hints.csv"
    output_path = root / "tests" / "fixtures" / "evidence_hints.out.csv"

    try:
        result = extract_detail_hints(input_path, output_path)

        assert result.rows_written == 1
        frame = pd.read_csv(output_path, dtype=str).fillna("")
        row = frame.iloc[0]
        assert "66 individuals" in row["sample_size_hint"]
        assert "12 weeks" in row["duration_hint"]
        assert "3 x 10^10 CFU/day" in row["cfu_hint"]
        assert "2 g/day" in row["dose_hint"]
        assert "BMI >= 25" in row["bmi_hint"]
        assert "p < 0.05" in row["p_value_hint"]
        assert "Body weight" in row["body_weight_effect_hint"]
    finally:
        output_path.unlink(missing_ok=True)
