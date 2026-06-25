from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd

from proslim_ai.arm_effects import (
    _leave_one_out_meta_influence,
)
from proslim_ai.input_manifest import load_input_manifest, load_structured_effect_table
from proslim_ai.run_stamp import production_run_stamp


ROOT = Path(__file__).resolve().parents[2]
COINTERVENTION_PATTERN = re.compile(
    r"diet|nutrition|micronutrient|surgery|bypass|exercise|energy[- ]restrict",
    flags=re.IGNORECASE,
)


def main() -> None:
    stamp = production_run_stamp()
    report_date = datetime.strptime(stamp, "%Y%m%d").date().isoformat()
    effect_path = ROOT / f"data/intervention_data/continuous_effect_sizes.upgrade_{stamp}.csv"
    arm_path = ROOT / f"data/intervention_data/study_arm_registry.upgrade_{stamp}.csv"
    quality_path = ROOT / f"results/prediction_results/effect_quality_audit_{stamp}.csv"
    if not effect_path.is_file() or not quality_path.is_file():
        raise FileNotFoundError("Run effect construction and the quality audit first")
    quality = pd.read_csv(quality_path)
    arms = pd.read_csv(arm_path)
    manifest = load_input_manifest(ROOT / "config/continuous_effect_upgrade_manifest.json")
    structured = load_structured_effect_table(manifest["structured_effects"])
    source_notes: dict[str, str] = {}
    if len(structured):
        structured["source_note"] = structured.get("source_note", "").fillna("").astype(str)
        source_notes = (
            structured.groupby("evidence_id")["source_note"]
            .agg(lambda values: " ".join(dict.fromkeys(value for value in values if value)))
            .to_dict()
        )
    active = arms[arms["arm_role"] == "intervention"].copy()
    selected = quality[
        quality["primary_analysis_eligible"].astype(str).str.lower().eq("true")
        & quality["outcome_domain"].eq("body_fat")
        & quality["canonical_unit"].eq("kg")
    ].copy()
    data = selected.drop(
        columns=[
            "intervention_class",
            "arm_label",
            "source_title",
        ],
        errors="ignore",
    ).merge(
        active[
            [
                "study_id",
                "intervention_class",
                "arm_label",
                "species",
                "strain",
                "duration_weeks",
                "sample_size",
                "source_title",
            ]
        ],
        on="study_id",
        how="left",
    )
    data["standard_error"] = pd.to_numeric(data["standard_error"], errors="coerce")
    data["estimate"] = pd.to_numeric(data["estimate"], errors="coerce")
    data = data.sort_values("standard_error", na_position="last").drop_duplicates(
        "analysis_study_id", keep="first"
    )

    data["source_note"] = data["study_id"].map(source_notes).fillna("")
    context = (
        data["comparison"].fillna("")
        + " "
        + data["source_title"].fillna("")
        + " "
        + data["source_final_value"].fillna("")
        + " "
        + data["source_note"]
    )
    data["cointervention_flag"] = context.map(
        lambda text: "; ".join(sorted(set(COINTERVENTION_PATTERN.findall(text))))
    )
    direct_variance = data["variance_provenance"].isin(
        ["reported_ci", "arm_sd_and_n"]
    )
    data["variance_status"] = np.where(direct_variance, "direct", "missing_or_pbound")
    identity = (
        data["arm_label"].fillna("")
        + " "
        + data["species"].fillna("")
        + " "
        + data["strain"].fillna("")
    ).str.lower()
    identity_is_specific = identity.str.contains(
        r"akkermansia|lactobacill|lacticaseib|lactiplantib|bifidobacter|"
        r"bacillus|cjls\d|b420|bb536|mcc\d",
        regex=True,
    ) & ~identity.str.contains(r"require full methods|multi-strain probiotic", regex=True)
    data["metadata_status"] = np.where(
        identity_is_specific & data["duration_weeks"].notna(),
        "moderator_ready",
        "sparse_intervention_metadata",
    )

    observed = data[direct_variance & data["standard_error"].gt(0)].copy()
    influence = (
        _leave_one_out_meta_influence(
            observed["estimate"].to_numpy(),
            observed["standard_error"].pow(2).to_numpy(),
            observed["study_id"].astype(str).tolist(),
        )
        if len(observed) >= 3
        else None
    )
    study_output = (
        ROOT / f"results/prediction_results/body_fat_hypothesis_studies_{stamp}.csv"
    )
    report_output = ROOT / f"results/prediction_results/body_fat_hypothesis_audit_{stamp}.json"
    study_output.parent.mkdir(parents=True, exist_ok=True)
    data[
        [
            "study_id",
            "estimate",
            "standard_error",
            "effect_unit",
            "comparison",
            "arm_label",
            "species",
            "strain",
            "duration_weeks",
            "sample_size",
            "cointervention_flag",
            "variance_status",
            "metadata_status",
            "source_note",
            "source_title",
        ]
    ].to_csv(study_output, index=False)

    report = {
        "date": report_date,
        "target_stratum": "body_fat|kg",
        "studies": int(len(data)),
        "observed_variance_studies": int(len(observed)),
        "negative_effect_studies": int(data["estimate"].lt(0).sum()),
        "positive_effect_studies": int(data["estimate"].gt(0).sum()),
        "studies_with_cointervention_flags": int(data["cointervention_flag"].ne("").sum()),
        "moderator_ready_studies": int(data["metadata_status"].eq("moderator_ready").sum()),
        "outlier_rows_trimmed": int(
            quality.loc[
                quality["outcome_domain"].eq("body_fat")
                & quality["canonical_unit"].eq("kg"),
                "robust_outlier_flag",
            ].astype(bool).sum()
        ),
        "influence_analysis": influence,
        "decision": "priority_replication_hypothesis_not_efficacy_signal",
        "reason": (
            "The corrected kg-scale evidence contains effects in both directions, sparse "
            "strain/dose metadata, and a small observed-variance subset. Influence results "
            "are hypothesis-generating only."
        ),
        "study_table": str(study_output.relative_to(ROOT)).replace("\\", "/"),
    }
    report_output.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(report_output)


if __name__ == "__main__":
    main()
