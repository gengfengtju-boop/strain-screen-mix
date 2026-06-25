"""Find variance-bearing, not-yet-curated studies to expand the continuous-effect dataset.

The continuous effect-size model is data-limited because only ~20 curated studies
report an extractable variance (SD / 95% CI / p-value + n). This scanner ranks the
evidence_details abstract corpus for studies that DO report such statistics on an
obesity outcome and are not yet in the curated structured_effects tables, so they
can be prioritized for manual curation.

    PYTHONPATH=src python scripts/modeling/build_variance_rich_curation_queue.py

Output: results/prediction_results/variance_rich_curation_queue_<stamp>.csv
"""
from __future__ import annotations

import glob
import re
from datetime import date
from pathlib import Path

import pandas as pd

from proslim_ai.arm_effects import _structured_study_meta

ROOT = Path(__file__).resolve().parents[2]

OUTCOME_PATTERNS = {
    "weight": r"body weight|weight loss|weight change",
    "BMI": r"\bbmi\b|body mass index",
    "body_fat": r"body fat|fat mass|visceral fat|adiposity|fat percentage",
    "waist": r"waist circumference|waist-to-hip|\bwaist\b",
    "glucose": r"fasting glucose|insulin|hba1c|homa-?ir|glyca?emic",
    "lipid": r"triglycerid|cholesterol|\bldl\b|\bhdl\b|lipid",
}
RCT_PATTERN = r"randomi[sz]ed|randomi[sz]ation|double-blind|placebo-controlled|crossover|parallel-group"
REVIEW_PATTERN = r"systematic review|meta-analysis|meta analysis|scoping review|umbrella review"
PROBIOTIC_PATTERN = (
    r"probiotic|synbiotic|prebiotic|postbiotic|paraprobiotic|lactobacill|"
    r"bifidobacter|lacticaseibac|limosilactobac|akkermansia|bacillus coagulans|"
    r"enterococcus|streptococcus thermophilus"
)


def _has(pattern: str, text: str) -> bool:
    return bool(re.search(pattern, text, flags=re.IGNORECASE))


def main() -> None:
    structured = [
        Path(p)
        for p in glob.glob(str(ROOT / "data/intervention_data/clinical_outcome.structured_effects*.csv"))
        if "ascii" not in p
    ]
    curated = set(_structured_study_meta(structured))

    detail_files = [
        f
        for f in glob.glob(str(ROOT / "data/literature_database/evidence_details*.csv"))
        if "ascii" not in f
    ]
    details = pd.concat(
        [pd.read_csv(f) for f in detail_files], ignore_index=True, sort=False
    ).drop_duplicates("evidence_id", keep="last")

    rows: list[dict[str, object]] = []
    for _, row in details.iterrows():
        evidence_id = str(row.get("evidence_id", "")).strip()
        if not evidence_id or evidence_id in curated:
            continue
        text = " ".join(
            str(row.get(field, "") or "")
            for field in ("abstract", "primary_outcomes", "secondary_outcomes", "arms")
        )
        title = str(row.get("title", "") or "")
        publication_types = str(row.get("publication_types", "") or "")
        intervention_text = " ".join(
            str(row.get(field, "") or "")
            for field in ("title", "clinical_interventions", "arms")
        )
        if not text.strip():
            continue
        if _has(REVIEW_PATTERN, f"{title} {publication_types}"):
            continue

        domains = [name for name, pat in OUTCOME_PATTERNS.items() if _has(pat, text)]
        if not domains:
            continue

        has_ci = _has(r"95\s*%?\s*ci", text)
        has_sd = _has(r"\d\s*(?:±|\+/-|\+-)|\bsd\b|standard deviation", text)
        has_p = _has(r"\bp\s*[<=>]\s*0?\.\d", text)
        if not (has_ci or has_sd or has_p):
            continue

        is_rct = _has(RCT_PATTERN, f"{title} {publication_types} {text}")
        is_probiotic = _has(PROBIOTIC_PATTERN, intervention_text)
        if not (is_rct and is_probiotic):
            continue

        # extraction-yield score: CI gives SE directly, SD gives SE with n,
        # p-only needs a paired estimate. Weight RCT + microbial relevance higher.
        score = (
            3 * has_ci
            + 2 * has_sd
            + 1 * has_p
            + 2 * is_rct
            + 2 * is_probiotic
            + 1 * ("body_fat" in domains)
            + 1 * ("BMI" in domains)
            + 1 * ("weight" in domains)
            + min(len(domains), 3)
        )
        rows.append(
            {
                "evidence_id": evidence_id,
                "curation_priority": score,
                "has_ci": has_ci,
                "has_sd": has_sd,
                "has_p_value": has_p,
                "is_rct": is_rct,
                "is_microbial_intervention": is_probiotic,
                "outcome_domains": "; ".join(domains),
                "n_outcome_domains": len(domains),
                "title": title[:200],
                "source_url": str(row.get("source_url", "") or ""),
                "enrollment": row.get("enrollment", ""),
                "publication_types": publication_types,
            }
        )

    queue = pd.DataFrame(rows).sort_values(
        ["curation_priority", "is_rct", "is_microbial_intervention"],
        ascending=[False, False, False],
    )
    stamp = date.today().strftime("%Y%m%d")
    out = ROOT / f"results/prediction_results/variance_rich_curation_queue_{stamp}.csv"
    out.parent.mkdir(parents=True, exist_ok=True)
    queue.to_csv(out, index=False)

    print(f"Uncurated variance-bearing obesity studies: {len(queue)}")
    print(f"  with CI: {int(queue['has_ci'].sum())}  SD: {int(queue['has_sd'].sum())}  p-value: {int(queue['has_p_value'].sum())}")
    print(f"  primary RCT + microbial intervention: {len(queue)}")
    print(f"Output: {out}")


if __name__ == "__main__":
    main()
