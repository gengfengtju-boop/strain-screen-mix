from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path

import pandas as pd

from proslim_ai.arm_effects import (
    _canonical_trial_ids,
    _canonical_unit,
    _microbial_comparison_mask,
    _primary_study_title_mask,
)
from proslim_ai.run_stamp import production_run_stamp


ROOT = Path(__file__).resolve().parents[2]
COINTERVENTION_PATTERN = re.compile(
    r"diet|nutrition|micronutrient|surgery|bypass|exercise|energy[- ]restrict",
    re.I,
)


def _robust_outlier_flags(data: pd.DataFrame) -> pd.Series:
    flags = pd.Series(False, index=data.index)
    for _, group in data.groupby(["outcome_domain", "canonical_unit"]):
        values = pd.to_numeric(group["estimate"], errors="coerce")
        if values.notna().sum() < 4:
            continue
        median = float(values.median())
        mad = float((values - median).abs().median())
        if mad > 1e-9:
            flags.loc[group.index] = 0.6745 * (values - median).abs() / mad > 3.5
    return flags


def main() -> None:
    stamp = production_run_stamp()
    report_date = datetime.strptime(stamp, "%Y%m%d").date().isoformat()
    effects = pd.read_csv(
        ROOT / f"data/intervention_data/continuous_effect_sizes.upgrade_{stamp}.csv"
    )
    arms = pd.read_csv(
        ROOT / f"data/intervention_data/study_arm_registry.upgrade_{stamp}.csv"
    )
    active = arms[arms["arm_role"] == "intervention"][
        ["study_id", "intervention_class", "arm_label", "source_title"]
    ]
    data = effects.merge(active, on="study_id", how="left")
    data["analysis_study_id"] = _canonical_trial_ids(data)
    data["canonical_unit"] = data["effect_unit"].map(_canonical_unit)
    data["is_microbial_arm"] = data["intervention_class"].isin(["probiotic", "synbiotic"])
    data["comparison_matches_microbial_arm"] = _microbial_comparison_mask(data)
    data["is_high_confidence"] = data["confidence"].fillna("").str.lower().eq("high")
    data["has_variance"] = pd.to_numeric(data["standard_error"], errors="coerce").gt(0)
    data["has_direct_variance"] = data.get(
        "variance_provenance", pd.Series(index=data.index, dtype=object)
    ).isin(["reported_ci", "arm_sd_and_n"])
    data["mixed_or_unspecified_unit"] = data["canonical_unit"].isin(
        ["mixed", "unspecified"]
    )
    data["review_like_title"] = ~_primary_study_title_mask(data)
    context = (
        data["comparison"].fillna("")
        + " "
        + data["source_title"].fillna("")
        + " "
        + data["source_final_value"].fillna("")
    )
    data["cointervention_flag"] = context.map(
        lambda value: "; ".join(sorted(set(COINTERVENTION_PATTERN.findall(value))))
    )
    alias_counts = data.groupby("analysis_study_id")["study_id"].transform("nunique")
    data["duplicate_publication_alias"] = alias_counts.gt(1)
    within_trial_counts = data.groupby(
        ["analysis_study_id", "outcome_domain", "canonical_unit"]
    )["effect_id"].transform("size")
    data["multiple_effects_same_trial_stratum"] = within_trial_counts.gt(1)
    pre_outlier_eligible = (
        data["is_microbial_arm"]
        & data["comparison_matches_microbial_arm"]
        & data["is_high_confidence"]
        & ~data["mixed_or_unspecified_unit"]
        & ~data["review_like_title"]
    )
    data["robust_outlier_flag"] = False
    data.loc[pre_outlier_eligible, "robust_outlier_flag"] = _robust_outlier_flags(
        data.loc[pre_outlier_eligible]
    )
    data["primary_analysis_eligible"] = (
        pre_outlier_eligible & ~data["robust_outlier_flag"]
    )

    flag_columns = [
        "is_microbial_arm",
        "comparison_matches_microbial_arm",
        "is_high_confidence",
        "has_variance",
        "has_direct_variance",
        "mixed_or_unspecified_unit",
        "review_like_title",
        "robust_outlier_flag",
        "duplicate_publication_alias",
        "multiple_effects_same_trial_stratum",
        "primary_analysis_eligible",
    ]
    audit_path = ROOT / f"results/prediction_results/effect_quality_audit_{stamp}.csv"
    report_path = ROOT / f"results/prediction_results/effect_quality_report_{stamp}.json"
    audit_path.parent.mkdir(parents=True, exist_ok=True)
    data.to_csv(audit_path, index=False)
    report = {
        "date": report_date,
        "effect_rows": int(len(data)),
        "analysis_trial_ids": int(data["analysis_study_id"].nunique()),
        "primary_analysis_eligible_rows": int(data["primary_analysis_eligible"].sum()),
        "primary_analysis_trials": int(
            data.loc[data["primary_analysis_eligible"], "analysis_study_id"].nunique()
        ),
        "flag_counts": {column: int(data[column].sum()) for column in flag_columns},
        "cointervention_rows": int(data["cointervention_flag"].ne("").sum()),
        "excluded_nonmicrobial_comparisons": sorted(
            data.loc[~data["comparison_matches_microbial_arm"], "study_id"].unique().tolist()
        ),
        "duplicate_alias_groups": {
            trial_id: sorted(set(group["study_id"]))
            for trial_id, group in data[data["duplicate_publication_alias"]].groupby(
                "analysis_study_id"
            )
        },
        "policy": (
            "Primary analysis requires a high-confidence microbial-arm effect, a matching "
            "microbial contrast, a comparable physical unit, a primary-study title, and no "
            "robust within-stratum outlier flag calculated only among otherwise eligible "
            "records. Missing variance and balanced cointerventions are retained but "
            "explicitly audited."
        ),
        "audit_table": str(audit_path.relative_to(ROOT)).replace("\\", "/"),
    }
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(report_path)


if __name__ == "__main__":
    main()
