from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .schemas import validate_csv_schema
from .standardize import normalize_sex, normalize_time_point, obesity_status_from_bmi


@dataclass(frozen=True)
class CleaningSummary:
    input_path: Path
    output_path: Path
    rows_in: int
    rows_out: int
    missing_required_columns: list[str]
    added_columns: list[str]


def clean_sample_metadata(
    config_dir: Path,
    input_path: Path,
    output_path: Path,
    derive_obesity_status: bool = True,
) -> CleaningSummary:
    import pandas as pd

    schema_result = validate_csv_schema(config_dir, "sample_metadata", input_path)
    if not schema_result.ok:
        return CleaningSummary(
            input_path=input_path,
            output_path=output_path,
            rows_in=0,
            rows_out=0,
            missing_required_columns=schema_result.missing_columns,
            added_columns=[],
        )

    frame = pd.read_csv(input_path)
    rows_in = len(frame)
    added_columns: list[str] = []

    frame["sex"] = frame["sex"].map(normalize_sex)
    frame["time_point"] = frame["time_point"].map(normalize_time_point)

    if "age_missing" not in frame.columns:
        frame["age_missing"] = frame["age"].isna()
        added_columns.append("age_missing")

    if derive_obesity_status:
        missing_or_unknown = frame["obesity_status"].isna() | (
            frame["obesity_status"].astype(str).str.strip().str.lower().isin({"", "na", "nan", "unknown"})
        )
        derived = frame["BMI"].map(obesity_status_from_bmi)
        frame.loc[missing_or_unknown, "obesity_status"] = derived[missing_or_unknown]

    output_path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(output_path, index=False)

    return CleaningSummary(
        input_path=input_path,
        output_path=output_path,
        rows_in=rows_in,
        rows_out=len(frame),
        missing_required_columns=[],
        added_columns=added_columns,
    )

