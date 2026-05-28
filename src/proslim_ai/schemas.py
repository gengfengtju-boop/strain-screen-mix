from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .config import load_table_schemas


@dataclass(frozen=True)
class SchemaValidationResult:
    table_name: str
    path: Path
    missing_columns: list[str]
    extra_columns: list[str]

    @property
    def ok(self) -> bool:
        return not self.missing_columns


def read_csv_header(path: Path) -> list[str]:
    import csv

    with path.open("r", newline="", encoding="utf-8-sig") as handle:
        reader = csv.reader(handle)
        try:
            return next(reader)
        except StopIteration:
            return []


def validate_csv_schema(
    config_dir: Path,
    table_name: str,
    csv_path: Path,
    allow_extra_columns: bool = True,
) -> SchemaValidationResult:
    schemas = load_table_schemas(config_dir)
    if table_name not in schemas:
        valid = ", ".join(sorted(schemas))
        raise KeyError(f"Unknown table schema '{table_name}'. Valid schemas: {valid}")

    expected = schemas[table_name]
    actual = read_csv_header(csv_path)
    actual_set = set(actual)
    expected_set = set(expected)
    missing = [column for column in expected if column not in actual_set]
    extra = [column for column in actual if column not in expected_set]
    if not allow_extra_columns and extra:
        missing = [*missing, *[f"unexpected:{column}" for column in extra]]

    return SchemaValidationResult(
        table_name=table_name,
        path=csv_path,
        missing_columns=missing,
        extra_columns=extra,
    )

