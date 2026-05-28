from pathlib import Path

from proslim_ai.schemas import validate_csv_schema


def test_validate_template_schema():
    root = Path(__file__).resolve().parents[1]
    template = root / "data" / "metadata" / "templates" / "sample_metadata.csv"
    result = validate_csv_schema(root / "config", "sample_metadata", template)
    assert result.ok
    assert not result.missing_columns


def test_validate_schema_reports_missing_columns():
    root = Path(__file__).resolve().parents[1]
    csv_path = root / "tests" / "fixtures" / "bad_sample_metadata.csv"

    result = validate_csv_schema(root / "config", "sample_metadata", csv_path)
    assert not result.ok
    assert "study_id" in result.missing_columns
