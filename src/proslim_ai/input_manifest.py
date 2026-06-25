from __future__ import annotations

import json
from pathlib import Path

import pandas as pd


STRUCTURED_KEY = ["evidence_id", "outcome_domain", "comparison", "effect_unit"]
STRUCTURED_VALUES = ["effect_difference", "intervention_effect", "control_effect"]
MANIFEST_SECTIONS = (
    "structured_effects",
    "outcome_reviews",
    "intervention_reviews",
    "evidence_details",
)


def load_input_manifest(manifest_path: Path) -> dict[str, object]:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    root = manifest_path.resolve().parents[1]
    resolved: dict[str, object] = {
        "schema_version": manifest.get("schema_version"),
        "manifest_path": str(manifest_path.resolve()),
    }
    for section in MANIFEST_SECTIONS:
        entries = manifest.get(section)
        if not isinstance(entries, list) or not entries:
            raise ValueError(f"Manifest section '{section}' must be a non-empty list")
        paths = [(root / str(entry)).resolve() for entry in entries]
        missing = [str(path) for path in paths if not path.is_file()]
        if missing:
            raise FileNotFoundError(f"Missing manifest inputs in '{section}': {missing}")
        if len(paths) != len(set(paths)):
            raise ValueError(f"Manifest section '{section}' contains duplicate paths")
        resolved[section] = paths

    structured = load_structured_effect_table(resolved["structured_effects"])
    resolved["structured_rows"] = int(len(structured))
    resolved["structured_studies"] = int(structured["evidence_id"].nunique())
    return resolved


def load_structured_effect_table(paths: list[Path]) -> pd.DataFrame:
    frames: list[pd.DataFrame] = []
    for path in sorted((Path(path).resolve() for path in paths), key=str):
        frame = pd.read_csv(path)
        missing = [column for column in STRUCTURED_KEY if column not in frame]
        if missing:
            raise ValueError(f"Structured effect file {path} is missing columns: {missing}")
        frame = frame.copy()
        frame["_source_path"] = str(path)
        frames.append(frame)
    if not frames:
        return pd.DataFrame()

    table = pd.concat(frames, ignore_index=True, sort=False)
    for column in STRUCTURED_VALUES:
        if column not in table:
            table[column] = pd.NA
    numeric = table[STRUCTURED_VALUES].apply(pd.to_numeric, errors="coerce")
    table["_numeric_signature"] = numeric.apply(
        lambda row: tuple(None if pd.isna(value) else float(value) for value in row), axis=1
    )

    conflicts: list[str] = []
    for key, group in table.groupby(STRUCTURED_KEY, dropna=False, sort=True):
        signatures = set(group["_numeric_signature"])
        if len(signatures) > 1:
            sources = sorted(Path(value).name for value in group["_source_path"].unique())
            conflicts.append(f"{key}: values={sorted(signatures, key=str)} sources={sources}")
    if conflicts:
        preview = "\n".join(conflicts[:20])
        raise ValueError(
            f"Conflicting structured effects for {len(conflicts)} analysis keys:\n{preview}"
        )

    table["_completeness"] = table.notna().sum(axis=1)
    table = (
        table.sort_values(
            STRUCTURED_KEY + ["_completeness", "_source_path"],
            ascending=[True] * len(STRUCTURED_KEY) + [False, True],
            kind="stable",
        )
        .drop_duplicates(STRUCTURED_KEY, keep="first")
        .drop(columns=["_source_path", "_numeric_signature", "_completeness"])
        .reset_index(drop=True)
    )
    return table
