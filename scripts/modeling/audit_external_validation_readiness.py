from __future__ import annotations

import json
import re
from pathlib import Path

import pandas as pd

from proslim_ai.run_stamp import production_run_stamp


ROOT = Path(__file__).resolve().parents[2]
REGISTRY_PATH = ROOT / "data/intervention_data/study_publication_registry.csv"


def _load_registry() -> pd.DataFrame:
    if not REGISTRY_PATH.is_file():
        return pd.DataFrame(
            columns=["study_id", "publication_date", "enrollment_source"]
        )
    return pd.read_csv(REGISTRY_PATH, dtype=str).fillna("")


def _year(value: str) -> str | None:
    match = re.search(r"(?:19|20)\d{2}", str(value or ""))
    return match.group(0) if match else None


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

    registry = _load_registry()
    pub_date = dict(zip(registry["study_id"], registry.get("publication_date", "")))
    enroll_src = dict(zip(registry["study_id"], registry.get("enrollment_source", "")))

    # Prefer the structured publication_date from the study registry; fall back to a
    # year mined from the source title only when the registry has no record.
    study_ids = eligible["analysis_study_id"].fillna("").astype(str)
    titles = eligible["source_title"].fillna("").astype(str)
    years = []
    sources_for_holdout = []
    for sid, title in zip(study_ids, titles):
        year = _year(pub_date.get(sid, "")) or _year(title)
        years.append(year)
        sources_for_holdout.append(str(enroll_src.get(sid, "")).strip())
    years = pd.Series(years)
    enrollment_source_counts = (
        pd.Series([s for s in sources_for_holdout if s]).value_counts().to_dict()
    )

    identifiers = eligible["study_id"].fillna("").astype(str)
    identifier_sources = identifiers.str.split(":", n=1).str[0].replace(
        {"EUROPEPMC": "PMID"}
    )
    identifier_source_counts = identifier_sources.value_counts().to_dict()

    min_external = policy["minimum_external_studies"]
    studies_with_date = int(years.notna().sum())
    parsed_years = sorted({int(y) for y in years.dropna()})
    temporal_ready = studies_with_date >= min_external * 2
    # A usable holdout source is an independent enrollment registry (not the literature
    # identifier scheme) that on its own covers enough independent studies.
    usable_enrollment_sources = sum(
        count >= min_external for count in enrollment_source_counts.values()
    )
    source_holdout_ready = usable_enrollment_sources >= 2

    report = {
        "run_stamp": stamp,
        "policy": policy,
        "eligible_independent_studies": int(len(eligible)),
        "identifier_source_counts": identifier_source_counts,
        "study_registry": str(REGISTRY_PATH.relative_to(ROOT)).replace("\\", "/"),
        "studies_with_structured_publication_date": int(
            sum(bool(_year(pub_date.get(sid, ""))) for sid in study_ids)
        ),
        "studies_with_parseable_publication_year": studies_with_date,
        "publication_year_min": parsed_years[0] if parsed_years else None,
        "publication_year_max": parsed_years[-1] if parsed_years else None,
        "enrollment_source_counts": enrollment_source_counts,
        "studies_with_known_enrollment_source": int(
            sum(1 for s in sources_for_holdout if s)
        ),
        "temporal_holdout_ready": temporal_ready,
        "source_holdout_ready": source_holdout_ready,
        "prospective_external_cohort_available": False,
        "external_validation_gate_passed": False,
        "blocking_reasons": [
            reason
            for condition, reason in (
                (
                    not temporal_ready,
                    "fewer than 2x the minimum number of studies carry a parseable "
                    "publication date for a reliable temporal split",
                ),
                (
                    not source_holdout_ready,
                    "no second enrollment source (trial registry) covers enough "
                    "independent studies for a source-stratified holdout",
                ),
                (True, "no prospective external cohort has been supplied"),
            )
            if condition
        ],
        "temporal_split_feasible": temporal_ready,
        "required_next_data": (
            "Publication dates are now recorded in the study registry, so a temporal "
            "holdout is feasible. Still required before the gate can pass: a second "
            "enrollment source with >=5 independent studies, or at least five wholly "
            "unseen canonical trials or a prospective external cohort."
        ),
        "combination_ranking_enabled": False,
    }
    output = (
        ROOT / f"results/prediction_results/external_validation_readiness_{stamp}.json"
    )
    output.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(output)


if __name__ == "__main__":
    main()
