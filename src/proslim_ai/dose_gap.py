from __future__ import annotations

from pathlib import Path

import pandas as pd

from .tabpfn_benchmark import build_response_feature_table


def build_dose_gap_queue(
    structured_outcomes_path: Path,
    review_paths: list[Path],
    output_path: Path,
) -> pd.DataFrame:
    outcomes = pd.read_csv(structured_outcomes_path)
    features, _, _, _ = build_response_feature_table(outcomes, review_paths)
    gap = features[
        features["intervention_class"].isin(["probiotic", "synbiotic"])
        & features["log10_cfu_day"].isna()
    ].copy()
    source = _review_sources(review_paths)
    rows: list[dict[str, object]] = []
    for evidence_id, group in gap.groupby("evidence_id", sort=False):
        evidence_source = source[source["evidence_id"].astype(str) == str(evidence_id)]
        first = evidence_source.iloc[0] if len(evidence_source) else pd.Series(dtype=object)
        endpoint_count = int(group["outcome_domain"].nunique())
        positive_count = int((group["positive_efficacy_label"] == "yes").sum())
        rows.append(
            {
                "priority_score": endpoint_count * 10 + positive_count,
                "evidence_id": evidence_id,
                "title": first.get("title", ""),
                "intervention_class": group["intervention_class"].iloc[0],
                "endpoint_count": endpoint_count,
                "positive_endpoint_count": positive_count,
                "outcome_domains": "; ".join(sorted(set(group["outcome_domain"].astype(str)))),
                "current_labels": "; ".join(
                    sorted(set(group["positive_efficacy_label"].astype(str)))
                ),
                "source_file": _first_nonempty(
                    evidence_source, ["second_pass_source_file", "pdf_source_file"]
                ),
                "existing_dose_text": _joined_nonempty(
                    evidence_source,
                    [
                        "second_pass_dose_terms",
                        "download_deep_dose_terms",
                        "pdf_deep_dose_terms",
                        "pdf_cfu_terms",
                    ],
                ),
                "review_required": (
                    "total CFU/day; per-strain CFU/day; number of strains; dosing frequency; "
                    "dosage form; intervention-arm mapping"
                ),
                "completion_rule": (
                    "record numeric total daily CFU and distinguish per-dose, per-serving, "
                    "per-strain, and total formulation dose"
                ),
                "review_status": "pending_manual_dose_review",
            }
        )
    queue = pd.DataFrame(rows).sort_values(
        ["priority_score", "evidence_id"], ascending=[False, True]
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    queue.to_csv(output_path, index=False)
    return queue


def _review_sources(review_paths: list[Path]) -> pd.DataFrame:
    frames = [pd.read_csv(path) for path in review_paths]
    return pd.concat(frames, ignore_index=True, sort=False) if frames else pd.DataFrame()


def _first_nonempty(data: pd.DataFrame, columns: list[str]) -> str:
    for column in columns:
        if column not in data:
            continue
        for value in data[column].dropna().astype(str):
            if value.strip():
                return value.strip()
    return ""


def _joined_nonempty(data: pd.DataFrame, columns: list[str]) -> str:
    values: list[str] = []
    for column in columns:
        if column not in data:
            continue
        values.extend(value.strip() for value in data[column].dropna().astype(str) if value.strip())
    return " | ".join(dict.fromkeys(values))
