from __future__ import annotations

from pathlib import Path
from typing import Any


def load_yaml(path: Path) -> dict[str, Any]:
    try:
        import yaml
    except ImportError as exc:
        raise RuntimeError("PyYAML is required to read YAML config files.") from exc

    with path.open("r", encoding="utf-8") as handle:
        value = yaml.safe_load(handle) or {}
    if not isinstance(value, dict):
        raise ValueError(f"Expected YAML mapping in {path}")
    return value


def load_table_schemas(config_dir: Path) -> dict[str, list[str]]:
    raw = load_yaml(config_dir / "table_schemas.yaml")
    schemas: dict[str, list[str]] = {}
    for name, columns in raw.items():
        if not isinstance(columns, list) or not all(isinstance(col, str) for col in columns):
            raise ValueError(f"Schema {name} must be a list of column names.")
        schemas[name] = columns
    return schemas

