from __future__ import annotations

import json
import re
from pathlib import Path

import pandas as pd

from proslim_ai.run_stamp import production_run_stamp


ROOT = Path(__file__).resolve().parents[2]
CORE_STRATA = {
    ("weight", "kg"),
    ("BMI", "kg/m2"),
    ("body_fat", "kg"),
    ("lipid_TG", "mg/dL"),
    ("waist", "cm"),
}
TARGET_DIRECT_STUDIES = 10
OUTCOME_PATTERNS = {
    "weight": r"body weight|weight loss|weight change",
    "BMI": r"\bbmi\b|body mass index",
    "body_fat": r"body fat|fat mass|visceral fat|adiposity",
    "lipid_TG": r"triglycerid|\btg\b",
    "waist": r"waist circumference|\bwaist\b",
}
DIRECT_CI = re.compile(r"95\s*%?\s*ci", re.I)
DIRECT_SD = re.compile(r"(?:\+/-|\+-|±|\bsd\b|standard deviation)", re.I)
RCT = re.compile(r"randomi[sz]ed|double-blind|placebo-controlled|parallel-group", re.I)
MICROBIAL = re.compile(
    r"probiotic|synbiotic|postbiotic|paraprobiotic|lactobacill|bifidobacter|"
    r"lacticaseibac|akkermansia|bacillus coagulans",
    re.I,
)
REVIEW = re.compile(r"systematic review|meta-analysis|meta analysis|protocol", re.I)


def _load_details() -> pd.DataFrame:
    manifest = json.loads(
        (ROOT / "config/continuous_effect_upgrade_manifest.json").read_text(
            encoding="utf-8"
        )
    )
    frames = [pd.read_csv(ROOT / path) for path in manifest["evidence_details"]]
    details = pd.concat(frames, ignore_index=True, sort=False)
    completeness = details.notna().sum(axis=1)
    return (
        details.assign(_completeness=completeness)
        .sort_values(["evidence_id", "_completeness"], ascending=[True, False])
        .drop_duplicates("evidence_id", keep="first")
        .drop(columns="_completeness")
    )


def _text(row: pd.Series) -> str:
    return " ".join(
        str(row.get(field, "") or "")
        for field in (
            "title",
            "abstract",
            "primary_outcomes",
            "secondary_outcomes",
            "arms",
            "clinical_interventions",
        )
    )


def main() -> None:
    stamp = production_run_stamp()
    result_dir = ROOT / "results/prediction_results"
    quality = pd.read_csv(result_dir / f"effect_quality_audit_{stamp}.csv")
    details = _load_details()
    detail_lookup = details.set_index("evidence_id", drop=False)
    eligible = quality[
        quality["primary_analysis_eligible"].astype(str).str.lower().eq("true")
    ].copy()
    eligible["is_direct"] = eligible["variance_provenance"].isin(
        ["reported_ci", "arm_sd_and_n"]
    )

    direct_counts = {
        key: int(
            group.loc[group["is_direct"], "analysis_study_id"].nunique()
        )
        for key, group in eligible.groupby(["outcome_domain", "canonical_unit"])
        if key in CORE_STRATA
    }
    rows: list[dict[str, object]] = []
    queued: set[tuple[str, str, str]] = set()

    missing_direct = eligible[
        ~eligible["is_direct"]
        & eligible.apply(
            lambda row: (row["outcome_domain"], row["canonical_unit"]) in CORE_STRATA,
            axis=1,
        )
    ]
    for _, effect in missing_direct.iterrows():
        evidence_id = str(effect["evidence_id"])
        domain = str(effect["outcome_domain"])
        unit = str(effect["canonical_unit"])
        key = (evidence_id, domain, unit)
        if key in queued:
            continue
        queued.add(key)
        detail = detail_lookup.loc[evidence_id] if evidence_id in detail_lookup.index else pd.Series()
        source_text = _text(detail) if len(detail) else ""
        has_ci = bool(DIRECT_CI.search(source_text))
        has_sd = bool(DIRECT_SD.search(source_text))
        deficit = max(0, TARGET_DIRECT_STUDIES - direct_counts.get((domain, unit), 0))
        rows.append(
            {
                "evidence_id": evidence_id,
                "analysis_study_id": effect["analysis_study_id"],
                "outcome_domain": domain,
                "canonical_unit": unit,
                "queue_type": "included_missing_direct_variance",
                "priority_score": 100 + deficit * 5 + has_ci * 8 + has_sd * 6,
                "direct_studies_current": direct_counts.get((domain, unit), 0),
                "direct_studies_target": TARGET_DIRECT_STUDIES,
                "direct_study_deficit": deficit,
                "abstract_has_ci": has_ci,
                "abstract_has_sd": has_sd,
                "current_variance_provenance": effect["variance_provenance"],
                "current_estimate": effect["estimate"],
                "current_unit": effect["effect_unit"],
                "title": effect.get("source_title", "") or detail.get("title", ""),
                "source_url": detail.get("source_url", ""),
                "enrollment": detail.get("enrollment", ""),
                "recommended_action": (
                    "verify reported CI" if has_ci else "verify arm SD and per-arm n"
                    if has_sd
                    else "retrieve full text or supplement for CI/SE/SD and per-arm n"
                ),
            }
        )

    included_ids = set(quality["evidence_id"].astype(str))
    for _, detail in details.iterrows():
        evidence_id = str(detail.get("evidence_id", "")).strip()
        if not evidence_id or evidence_id in included_ids:
            continue
        source_text = _text(detail)
        if REVIEW.search(source_text) or not RCT.search(source_text) or not MICROBIAL.search(source_text):
            continue
        has_ci = bool(DIRECT_CI.search(source_text))
        has_sd = bool(DIRECT_SD.search(source_text))
        if not (has_ci or has_sd):
            continue
        for domain, pattern in OUTCOME_PATTERNS.items():
            unit = next(unit for candidate, unit in CORE_STRATA if candidate == domain)
            if not re.search(pattern, source_text, re.I):
                continue
            deficit = max(0, TARGET_DIRECT_STUDIES - direct_counts.get((domain, unit), 0))
            rows.append(
                {
                    "evidence_id": evidence_id,
                    "analysis_study_id": evidence_id,
                    "outcome_domain": domain,
                    "canonical_unit": unit,
                    "queue_type": "new_direct_variance_candidate",
                    "priority_score": 50 + deficit * 5 + has_ci * 8 + has_sd * 6,
                    "direct_studies_current": direct_counts.get((domain, unit), 0),
                    "direct_studies_target": TARGET_DIRECT_STUDIES,
                    "direct_study_deficit": deficit,
                    "abstract_has_ci": has_ci,
                    "abstract_has_sd": has_sd,
                    "current_variance_provenance": "not_curated",
                    "current_estimate": "",
                    "current_unit": "",
                    "title": detail.get("title", ""),
                    "source_url": detail.get("source_url", ""),
                    "enrollment": detail.get("enrollment", ""),
                    "recommended_action": "screen full text and extract effect plus direct variance",
                }
            )

    queue = pd.DataFrame(rows).sort_values(
        ["priority_score", "queue_type", "evidence_id"], ascending=[False, True, True]
    )
    output = result_dir / f"direct_variance_review_queue_{stamp}.csv"
    queue.to_csv(output, index=False)
    summary = {
        "run_stamp": stamp,
        "target_direct_studies_per_core_stratum": TARGET_DIRECT_STUDIES,
        "current_direct_studies": {
            f"{domain}|{unit}": direct_counts.get((domain, unit), 0)
            for domain, unit in sorted(CORE_STRATA)
        },
        "queue_rows": int(len(queue)),
        "included_missing_direct_rows": int(
            queue["queue_type"].eq("included_missing_direct_variance").sum()
        ),
        "new_direct_variance_candidate_rows": int(
            queue["queue_type"].eq("new_direct_variance_candidate").sum()
        ),
        "output": str(output.relative_to(ROOT)).replace("\\", "/"),
    }
    summary_output = result_dir / f"direct_variance_gap_report_{stamp}.json"
    summary_output.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(summary_output)
    print(output)


if __name__ == "__main__":
    main()
