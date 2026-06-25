from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from proslim_ai.run_stamp import production_run_stamp


ROOT = Path(__file__).resolve().parents[2]


def main() -> None:
    stamp = production_run_stamp()
    policy = json.loads(
        (ROOT / "config/continuous_effect_validation_policy.json").read_text(
            encoding="utf-8"
        )
    )
    quality = pd.read_csv(
        ROOT / f"results/prediction_results/effect_quality_audit_{stamp}.csv"
    )
    eligible = quality[
        quality["primary_analysis_eligible"].astype(str).str.lower().eq("true")
    ].drop_duplicates("analysis_study_id")
    identifiers = eligible["study_id"].fillna("").astype(str)
    sources = identifiers.str.split(":", n=1).str[0].replace({"EUROPEPMC": "PMID"})
    years = eligible["source_title"].fillna("").astype(str).str.extract(
        r"((?:19|20)\d{2})"
    )[0]
    source_counts = sources.value_counts().to_dict()
    usable_sources = sum(count >= policy["minimum_external_studies"] for count in source_counts.values())
    temporal_ready = int(years.notna().sum()) >= policy["minimum_external_studies"] * 2
    source_holdout_ready = usable_sources >= 2
    report = {
        "run_stamp": stamp,
        "policy": policy,
        "eligible_independent_studies": int(len(eligible)),
        "identifier_source_counts": source_counts,
        "studies_with_parseable_publication_year": int(years.notna().sum()),
        "temporal_holdout_ready": temporal_ready,
        "source_holdout_ready": source_holdout_ready,
        "prospective_external_cohort_available": False,
        "external_validation_gate_passed": False,
        "blocking_reasons": [
            reason
            for condition, reason in (
                (not temporal_ready, "publication year is unavailable for a reliable temporal split"),
                (not source_holdout_ready, "no second source contains enough independent studies"),
                (True, "no prospective external cohort has been supplied"),
            )
            if condition
        ],
        "required_next_data": (
            "Add publication_date and enrollment_source fields to the study registry, then "
            "reserve at least five wholly unseen canonical trials or a prospective cohort."
        ),
        "combination_ranking_enabled": False,
    }
    output = ROOT / f"results/prediction_results/external_validation_readiness_{stamp}.json"
    output.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(output)


if __name__ == "__main__":
    main()
