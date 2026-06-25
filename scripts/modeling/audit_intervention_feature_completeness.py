from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from proslim_ai.arm_effects import _add_interpretable_intervention_features
from proslim_ai.run_stamp import production_run_stamp


ROOT = Path(__file__).resolve().parents[2]


def main() -> None:
    stamp = production_run_stamp()
    arms = pd.read_csv(
        ROOT / f"data/intervention_data/study_arm_registry.upgrade_{stamp}.csv"
    )
    effects = pd.read_csv(
        ROOT / f"results/prediction_results/effect_quality_audit_{stamp}.csv"
    )
    active = arms[arms["arm_role"].eq("intervention")].copy()
    active = _add_interpretable_intervention_features(active)
    eligible_ids = set(
        effects.loc[
            effects["primary_analysis_eligible"].astype(str).str.lower().eq("true"),
            "study_id",
        ].astype(str)
    )
    active["primary_effect_study"] = active["study_id"].astype(str).isin(eligible_ids)
    active["species_known"] = active["species"].fillna("").astype(str).str.strip().ne("")
    active["strain_known"] = active["strain"].fillna("").astype(str).str.strip().ne("")
    active["dose_known"] = active["dose_status"].eq("known")
    active["duration_known"] = active["duration_status"].eq("known")
    active["dosage_form_known"] = active["dosage_form_group"].ne("unknown_or_other")
    active["moderator_complete"] = active[
        ["species_known", "strain_known", "dose_known", "duration_known"]
    ].all(axis=1)

    fields = [
        "species_known",
        "strain_known",
        "dose_known",
        "duration_known",
        "dosage_form_known",
        "moderator_complete",
    ]
    primary = active[active["primary_effect_study"]]
    report = {
        "run_stamp": stamp,
        "intervention_studies": int(active["study_id"].nunique()),
        "primary_effect_studies": int(primary["study_id"].nunique()),
        "coverage_all_intervention_studies": {
            field: float(active[field].mean()) for field in fields
        },
        "coverage_primary_effect_studies": {
            field: float(primary[field].mean()) if len(primary) else 0.0 for field in fields
        },
        "feature_categories_primary": {
            "microbial_family": primary["microbial_family"].value_counts().to_dict(),
            "formulation_complexity": primary["formulation_complexity"].value_counts().to_dict(),
            "dosage_form_group": primary["dosage_form_group"].value_counts().to_dict(),
        },
        "modeling_decision": (
            "use coarse pre-intervention categories; do not fit strain-specific effects "
            "until moderator_complete coverage and per-level study counts improve"
        ),
    }
    result_dir = ROOT / "results/prediction_results"
    table_output = result_dir / f"intervention_feature_completeness_{stamp}.csv"
    report_output = result_dir / f"intervention_feature_completeness_{stamp}.json"
    active.to_csv(table_output, index=False)
    report_output.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(report_output)
    print(table_output)


if __name__ == "__main__":
    main()
