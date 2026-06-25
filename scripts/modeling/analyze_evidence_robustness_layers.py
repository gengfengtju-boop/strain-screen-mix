from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

import pandas as pd

from proslim_ai.arm_effects import _layered_evidence_sensitivity
from proslim_ai.run_stamp import production_run_stamp


ROOT = Path(__file__).resolve().parents[2]


def main() -> None:
    stamp = production_run_stamp()
    report_date = datetime.strptime(stamp, "%Y%m%d").date().isoformat()
    audit_path = ROOT / f"results/prediction_results/effect_quality_audit_{stamp}.csv"
    output_path = (
        ROOT / f"results/prediction_results/evidence_layer_sensitivity_{stamp}.json"
    )
    table_path = (
        ROOT / f"results/prediction_results/evidence_layer_sensitivity_{stamp}.csv"
    )
    data = pd.read_csv(audit_path)
    data = data[data["primary_analysis_eligible"]].copy()
    data["stratum"] = data["outcome_domain"].astype(str) + "|" + data[
        "canonical_unit"
    ].astype(str)
    data["estimate"] = pd.to_numeric(data["estimate"], errors="coerce")
    data["variance"] = pd.to_numeric(data["variance"], errors="coerce")
    data["has_cointervention"] = data["cointervention_flag"].fillna("").ne("")
    data["stronger_precision"] = data["variance_provenance"].isin(
        ["reported_ci", "arm_sd_and_n"]
    )
    data.loc[~data["stronger_precision"], "variance"] = float("nan")

    reports: list[dict[str, object]] = []
    flat_rows: list[dict[str, object]] = []
    for index, (stratum, raw_group) in enumerate(data.groupby("stratum")):
        group = raw_group.sort_values("standard_error", na_position="last").drop_duplicates(
            "analysis_study_id", keep="first"
        )
        if len(group) < 3:
            continue
        result = _layered_evidence_sensitivity(
            group["estimate"].to_numpy(),
            group["variance"].to_numpy(),
            group["has_cointervention"].to_numpy(),
            group["stronger_precision"].to_numpy(),
            bootstrap_iterations=5000,
            random_seed=20260614 + index * 10,
        )
        result.update(
            {
                "stratum": stratum,
                "k_studies": int(len(group)),
                "cointervention_studies": int(group["has_cointervention"].sum()),
                "variance_studies": int(group["variance"].gt(0).sum()),
                "stronger_precision_studies": int(group["stronger_precision"].sum()),
            }
        )
        reports.append(result)
        for layer_name, layer in result["layers"].items():
            nonparametric = layer.get("nonparametric_sensitivity", {})
            flat_rows.append(
                {
                    "stratum": stratum,
                    "layer": layer_name,
                    "status": layer.get("status"),
                    "k_studies": layer.get("k_studies"),
                    "median_effect": nonparametric.get("median_effect"),
                    "bootstrap_ci95_low": nonparametric.get("bootstrap_ci95_low"),
                    "bootstrap_ci95_high": nonparametric.get("bootstrap_ci95_high"),
                    "probability_below_zero": nonparametric.get(
                        "bootstrap_probability_below_zero"
                    ),
                    "layer_conclusion": result["conclusion"],
                }
            )

    conclusion_counts = {
        conclusion: sum(row["conclusion"] == conclusion for row in reports)
        for conclusion in sorted({row["conclusion"] for row in reports})
    }
    report = {
        "date": report_date,
        "method": (
            "Study-level median/bootstrap and missing-variance sensitivity compared across "
            "all eligible studies, exclusion of flagged cointerventions, observed-variance "
            "studies, and stronger precision sources (reported CI or arm-level SD+n)."
        ),
        "strata_analyzed": len(reports),
        "conclusion_counts": conclusion_counts,
        "strata": reports,
        "decision_rule": (
            "A signal is not actionable when its direction changes across layers or when "
            "interval support disappears after stricter evidence filtering."
        ),
        "combination_ranking_enabled": False,
        "table": str(table_path.relative_to(ROOT)).replace("\\", "/"),
    }
    output_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    pd.DataFrame(flat_rows).to_csv(table_path, index=False)
    print(output_path)


if __name__ == "__main__":
    main()
