from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from proslim_ai.arm_effects import _parse_continuous_effect, _sample_size
from proslim_ai.input_manifest import load_structured_effect_table
from proslim_ai.run_stamp import production_run_stamp


ROOT = Path(__file__).resolve().parents[2]
FIELDS = [
    "evidence_id",
    "outcome_domain",
    "endpoint_type",
    "analysis_population",
    "comparison",
    "intervention_effect",
    "control_effect",
    "effect_difference",
    "effect_unit",
    "between_group_p",
    "within_group_p",
    "direction",
    "evidence_modifier",
    "positive_efficacy_label",
    "effect_parse_method",
    "p_value_parse_method",
    "structure_warning",
    "source_final_value",
    "source_note",
    "candidate_status",
    "candidate_parse_method",
]


def _load_manifest() -> dict[str, object]:
    return json.loads(
        (ROOT / "config/continuous_effect_upgrade_manifest.json").read_text(
            encoding="utf-8"
        )
    )


def _detail_sample_sizes(paths: list[str]) -> dict[str, float]:
    frames = [pd.read_csv(ROOT / path) for path in paths if (ROOT / path).is_file()]
    if not frames:
        return {}
    table = (
        pd.concat(frames, ignore_index=True, sort=False)
        .drop_duplicates("evidence_id", keep="last")
    )
    lookup: dict[str, float] = {}
    for _, row in table.iterrows():
        evidence_id = str(row.get("evidence_id", "")).strip()
        if not evidence_id:
            continue
        size = pd.to_numeric(row.get("enrollment"), errors="coerce")
        if pd.isna(size):
            size = _sample_size(
                f"{row.get('abstract', '') or ''} {row.get('arms', '') or ''}"
            )
        if pd.notna(size) and float(size) > 0:
            lookup[evidence_id] = float(size)
    return lookup


def main() -> None:
    stamp = production_run_stamp()
    manifest = _load_manifest()
    queue_path = ROOT / f"results/prediction_results/direct_variance_review_queue_{stamp}.csv"
    queue = pd.read_csv(queue_path)
    structured = load_structured_effect_table(
        [ROOT / str(path) for path in manifest["structured_effects"]]
    )
    n_lookup = _detail_sample_sizes([str(path) for path in manifest["evidence_details"]])

    target_keys = {
        (str(row.evidence_id), str(row.outcome_domain), str(row.canonical_unit))
        for _, row in queue[
            queue["queue_type"].eq("included_missing_direct_variance")
        ].iterrows()
    }
    rows: list[dict[str, object]] = []
    blocked: list[dict[str, object]] = []
    for _, row in structured.iterrows():
        evidence_id = str(row.get("evidence_id", "")).strip()
        domain = str(row.get("outcome_domain", "")).strip()
        unit = str(row.get("effect_unit", "")).strip()
        canonical_unit = (
            "kg/m2" if "kg/m2" in unit else
            "mg/dL" if "mg/dL" in unit else
            "cm" if unit == "cm" or unit.startswith("cm ") else
            "kg" if unit == "kg" or unit.startswith("kg ") else unit
        )
        if (evidence_id, domain, canonical_unit) not in target_keys:
            continue
        source = str(row.get("source_final_value", "") or "").strip()
        if not source:
            continue
        parsed = _parse_continuous_effect(source, source)
        if parsed is None:
            blocked.append(
                {
                    "evidence_id": evidence_id,
                    "outcome_domain": domain,
                    "effect_unit": unit,
                    "block_reason": "source_final_value_not_parseable_for_ci_or_arm_sd",
                    "source_final_value": source,
                }
            )
            continue
        method = str(parsed.get("extraction_method", ""))
        if method == "two_arm_mean_sd_and_arm_n":
            status = "ready_for_manual_confirmation"
            note = "Exact arm n found in source text; verify against full text before manifest inclusion."
        elif method == "two_arm_mean_sd_missing_arm_n" and evidence_id in n_lookup:
            status = "balanced_n_sensitivity_only"
            note = (
                f"Arm SDs found, but exact arm n missing; total n={n_lookup[evidence_id]:.0f} "
                "available for balanced-n sensitivity only."
            )
        elif "95ci" in method:
            status = "ready_for_manual_confirmation"
            note = "Reported CI found; verify point estimate and CI before manifest inclusion."
        else:
            status = "needs_full_text_arm_n"
            note = "Effect text parses, but direct validation still needs exact per-arm n."
        out = {field: row.get(field, "") for field in FIELDS if field not in {
            "candidate_status",
            "candidate_parse_method",
        }}
        out["candidate_status"] = status
        out["candidate_parse_method"] = method
        out["source_note"] = f"{row.get('source_note', '') or ''} {note}".strip()
        rows.append(out)

    output_dir = ROOT / "data/intervention_data"
    candidate_output = (
        output_dir / f"clinical_outcome.structured_effects.direct_variance_candidates_{stamp}.csv"
    )
    blocked_output = (
        ROOT
        / f"results/prediction_results/direct_variance_candidate_blocked_{stamp}.csv"
    )
    report_output = (
        ROOT / f"results/prediction_results/direct_variance_candidate_report_{stamp}.json"
    )
    candidates = pd.DataFrame(rows, columns=FIELDS)
    candidates.to_csv(candidate_output, index=False)
    pd.DataFrame(blocked).to_csv(blocked_output, index=False)
    report = {
        "run_stamp": stamp,
        "candidate_rows": int(len(candidates)),
        "ready_for_manual_confirmation": int(
            candidates["candidate_status"].eq("ready_for_manual_confirmation").sum()
        ) if len(candidates) else 0,
        "balanced_n_sensitivity_only": int(
            candidates["candidate_status"].eq("balanced_n_sensitivity_only").sum()
        ) if len(candidates) else 0,
        "needs_full_text_arm_n": int(
            candidates["candidate_status"].eq("needs_full_text_arm_n").sum()
        ) if len(candidates) else 0,
        "blocked_rows": int(len(blocked)),
        "production_manifest_updated": False,
        "candidate_output": str(candidate_output.relative_to(ROOT)).replace("\\", "/"),
        "blocked_output": str(blocked_output.relative_to(ROOT)).replace("\\", "/"),
    }
    report_output.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(candidate_output)
    print(report_output)


if __name__ == "__main__":
    main()
