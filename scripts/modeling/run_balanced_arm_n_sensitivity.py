from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from proslim_ai.arm_effects import _canonical_trial_ids, _parse_continuous_effect
from proslim_ai.run_stamp import production_run_stamp


ROOT = Path(__file__).resolve().parents[2]
DIRECT = {"reported_ci", "arm_sd_and_n"}
CORE_STRATA = {"weight|kg", "BMI|kg/m2", "body_fat|kg", "lipid_TG|mg/dL", "waist|cm"}


def _canonical_unit(value: object) -> str:
    text = str(value or "")
    if "kg/m2" in text:
        return "kg/m2"
    if "mg/dL" in text:
        return "mg/dL"
    if text == "cm" or text.startswith("cm "):
        return "cm"
    if text == "kg" or text.startswith("kg "):
        return "kg"
    return text


def main() -> None:
    stamp = production_run_stamp()
    effect_path = ROOT / f"data/intervention_data/continuous_effect_sizes.upgrade_{stamp}.csv"
    candidate_path = (
        ROOT
        / f"data/intervention_data/clinical_outcome.structured_effects.direct_variance_candidates_{stamp}.csv"
    )
    output_path = (
        ROOT / f"results/prediction_results/balanced_arm_n_sensitivity_{stamp}.json"
    )
    effects = pd.read_csv(effect_path)
    if not candidate_path.is_file():
        raise FileNotFoundError(
            f"Run build_direct_variance_candidate_patch.py first: {candidate_path}"
        )
    candidates = pd.read_csv(candidate_path)
    candidates = candidates[
        candidates["candidate_status"].eq("balanced_n_sensitivity_only")
    ].copy()
    if len(candidates) == 0:
        output_path.write_text(
            json.dumps(
                {
                    "run_stamp": stamp,
                    "sensitivity_rows_added": 0,
                    "production_policy": "no balanced-n rows available; production unchanged",
                },
                indent=2,
            ),
            encoding="utf-8",
        )
        print(output_path)
        return

    augmented = effects.copy()
    updates = 0
    for _, row in candidates.iterrows():
        evidence_id = str(row["evidence_id"])
        domain = str(row["outcome_domain"])
        unit = _canonical_unit(row.get("effect_unit"))
        source = str(row.get("source_final_value", "") or "")
        current = augmented[
            augmented["evidence_id"].astype(str).eq(evidence_id)
            & augmented["outcome_domain"].astype(str).eq(domain)
            & augmented["effect_unit"].map(_canonical_unit).eq(unit)
        ]
        if len(current) == 0:
            continue
        target_index = current.index[0]
        total_n = pd.to_numeric(current.iloc[0].get("sample_size_total"), errors="coerce")
        if pd.isna(total_n) or float(total_n) < 2:
            continue
        balanced = f"{source}; n={int(float(total_n) / 2)} per arm"
        parsed = _parse_continuous_effect(balanced, balanced)
        if parsed is None or not parsed.get("standard_error"):
            continue
        augmented.loc[target_index, "standard_error"] = float(parsed["standard_error"])
        augmented.loc[target_index, "variance"] = float(parsed["standard_error"]) ** 2
        augmented.loc[target_index, "ci_lower"] = parsed.get("ci_lower")
        augmented.loc[target_index, "ci_upper"] = parsed.get("ci_upper")
        augmented.loc[target_index, "variance_provenance"] = "balanced_arm_n_inferred"
        updates += 1

    high = augmented[augmented["confidence"].fillna("").str.lower().eq("high")].copy()
    high["canonical_unit"] = high["effect_unit"].map(_canonical_unit)
    high["stratum"] = high["outcome_domain"].astype(str) + "|" + high["canonical_unit"]
    high["analysis_study_id"] = _canonical_trial_ids(high)
    rows = []
    for stratum, group in high[high["stratum"].isin(CORE_STRATA)].groupby("stratum"):
        direct_studies = int(
            group[group["variance_provenance"].isin(DIRECT)]["analysis_study_id"].nunique()
        )
        sensitivity_studies = int(
            group[
                group["variance_provenance"].isin(DIRECT | {"balanced_arm_n_inferred"})
            ]["analysis_study_id"].nunique()
        )
        rows.append(
            {
                "stratum": stratum,
                "high_confidence_studies": int(group["analysis_study_id"].nunique()),
                "direct_variance_studies": direct_studies,
                "direct_plus_balanced_n_studies": sensitivity_studies,
                "balanced_n_increment": sensitivity_studies - direct_studies,
                "meets_10_study_direct_target_in_sensitivity": sensitivity_studies >= 10,
            }
        )
    report = {
        "run_stamp": stamp,
        "sensitivity_rows_added": int(updates),
        "production_policy": (
            "balanced_arm_n_inferred rows are sensitivity-only and are not counted "
            "as reported_ci or arm_sd_and_n direct variance."
        ),
        "strata": sorted(rows, key=lambda item: item["stratum"]),
    }
    output_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(output_path)


if __name__ == "__main__":
    main()
