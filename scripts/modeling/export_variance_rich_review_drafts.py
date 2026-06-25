"""Export top variance-rich curation candidates into review-worksheet drafts.

Takes the prioritized queue from build_variance_rich_curation_queue.py and emits
outcome- and intervention-review worksheet drafts matching the project schema
(config/review_fields.yaml). Each outcome row is pre-filled with the abstract
sentence that carries the statistic (mean +/- SD, 95% CI, or p-value) and the
detected p-value, so a curator only has to confirm final_value/unit/direction.

    PYTHONPATH=src python scripts/modeling/export_variance_rich_review_drafts.py [TOP_N]

Defaults to the 77 highest-yield studies (RCT + microbial intervention + CI/SD).
"""
from __future__ import annotations

import re
import sys
from datetime import date
from pathlib import Path

import pandas as pd
import glob

ROOT = Path(__file__).resolve().parents[2]

OUTCOME_PATTERNS = {
    "weight": r"body weight|weight loss|weight change|\bweight\b",
    "BMI": r"\bbmi\b|body mass index",
    "body_fat": r"body fat|fat mass|visceral fat|adiposity|fat percentage",
    "waist": r"waist circumference|waist-to-hip|\bwaist\b",
    "glucose": r"fasting glucose|insulin|hba1c|homa-?ir|glyca?emic|glucose",
    "lipid": r"triglycerid|cholesterol|\bldl\b|\bhdl\b|lipid",
}
STAT_PATTERN = re.compile(
    r"(?:±|\+/-|\bsd\b|95\s*%?\s*ci|\bp\s*[<=>]\s*0?\.\d|\d\s*\()", re.IGNORECASE
)
P_PATTERN = re.compile(r"p\s*[<=>]\s*0?\.\d+", re.IGNORECASE)

OUTCOME_FIELDS = [
    "evidence_id", "source_database", "source_accession", "title", "outcome_domain",
    "suggested_text", "suggested_p_value", "final_value", "final_unit",
    "final_direction", "comparison", "time_point", "p_value_confirmed",
    "sample_size_confirmed", "extraction_source", "reviewer", "review_status",
    "reviewer_note",
]
INTERVENTION_FIELDS = [
    "evidence_id", "source_database", "source_accession", "title",
    "intervention_component", "suggested_intervention", "suggested_duration",
    "suggested_cfu", "suggested_dose", "final_species", "final_strain",
    "final_total_CFU_per_day", "final_log10_CFU_per_day", "final_prebiotic_type",
    "final_prebiotic_dose_g_day", "final_duration_weeks", "final_dosage_form",
    "reviewer", "review_status", "reviewer_note",
]


def _sentences(text: str) -> list[str]:
    return [s.strip() for s in re.split(r"(?<=[.;])\s+", text) if s.strip()]


def _best_sentence(text: str, pattern: str) -> str:
    candidates = [
        s for s in _sentences(text)
        if re.search(pattern, s, re.IGNORECASE) and STAT_PATTERN.search(s)
    ]
    candidates.sort(key=lambda s: (P_PATTERN.search(s) is None, -len(s)))
    return candidates[0][:400] if candidates else ""


def main() -> None:
    top_n = int(sys.argv[1]) if len(sys.argv) > 1 else 77
    queue_files = sorted(
        glob.glob(str(ROOT / "results/prediction_results/variance_rich_curation_queue_*.csv"))
    )
    if not queue_files:
        raise SystemExit("Run build_variance_rich_curation_queue.py first.")
    queue = pd.read_csv(queue_files[-1])
    # highest-yield first: RCT + microbial + directly computable SE (CI or SD)
    queue = queue[queue["is_rct"] & queue["is_microbial_intervention"] & (queue["has_ci"] | queue["has_sd"])]
    queue = queue.drop_duplicates("evidence_id").head(top_n)

    detail_files = [
        f for f in glob.glob(str(ROOT / "data/literature_database/evidence_details*.csv"))
        if "ascii" not in f
    ]
    details = pd.concat(
        [pd.read_csv(f) for f in detail_files], ignore_index=True, sort=False
    ).drop_duplicates("evidence_id", keep="last").set_index("evidence_id")

    outcome_rows: list[dict[str, object]] = []
    intervention_rows: list[dict[str, object]] = []
    for _, q in queue.iterrows():
        evidence_id = str(q["evidence_id"])
        prefix = evidence_id.split(":")[0]
        accession = evidence_id.split(":", 1)[1] if ":" in evidence_id else evidence_id
        detail = details.loc[evidence_id] if evidence_id in details.index else {}
        text = " ".join(
            str(detail.get(f, "") or "")
            for f in ("abstract", "primary_outcomes", "secondary_outcomes", "arms")
        )
        title = str(q.get("title", "") or "")
        enrollment = q.get("enrollment", "")
        if str(enrollment).strip() not in ("", "nan"):
            sample_size = f"n={int(float(enrollment))} enrolled"
        else:
            n_match = re.search(r"\b[nN]\s*=\s*\d+", text)
            sample_size = n_match.group(0) if n_match else ""
        signals = ", ".join(
            s for s, flag in [("CI", q["has_ci"]), ("SD", q["has_sd"]), ("p", q["has_p_value"])] if flag
        )

        for domain in str(q["outcome_domains"]).split("; "):
            domain = domain.strip()
            if domain not in OUTCOME_PATTERNS:
                continue
            sentence = _best_sentence(text, OUTCOME_PATTERNS[domain])
            if not sentence:
                continue
            p_match = P_PATTERN.search(sentence)
            outcome_rows.append({
                "evidence_id": evidence_id, "source_database": prefix,
                "source_accession": accession, "title": title, "outcome_domain": domain,
                "suggested_text": sentence,
                "suggested_p_value": p_match.group(0) if p_match else "",
                "final_value": "", "final_unit": "", "final_direction": "",
                "comparison": "", "time_point": "", "p_value_confirmed": "",
                "sample_size_confirmed": sample_size,
                "extraction_source": "abstract_auto_draft", "reviewer": "",
                "review_status": "pending",
                "reviewer_note": f"variance signals: {signals}",
            })

        intervention_rows.append({
            "evidence_id": evidence_id, "source_database": prefix,
            "source_accession": accession, "title": title,
            "intervention_component": "", "suggested_intervention": "",
            "suggested_duration": "", "suggested_cfu": "", "suggested_dose": "",
            "final_species": "", "final_strain": "", "final_total_CFU_per_day": "",
            "final_log10_CFU_per_day": "", "final_prebiotic_type": "",
            "final_prebiotic_dose_g_day": "", "final_duration_weeks": "",
            "final_dosage_form": "", "reviewer": "", "review_status": "pending",
            "reviewer_note": "variance-rich curation candidate",
        })

    stamp = date.today().strftime("%Y%m%d")
    out_dir = ROOT / "data/intervention_data"
    outcome_out = out_dir / f"outcome_review_worksheet.variance_rich_draft_{stamp}.csv"
    interv_out = out_dir / f"intervention_review_worksheet.variance_rich_draft_{stamp}.csv"
    pd.DataFrame(outcome_rows, columns=OUTCOME_FIELDS).to_csv(outcome_out, index=False, encoding="utf-8")
    pd.DataFrame(intervention_rows, columns=INTERVENTION_FIELDS).to_csv(interv_out, index=False, encoding="utf-8")

    print(f"Studies exported: {len(intervention_rows)}")
    print(f"Outcome rows (study x domain) with a statistic sentence: {len(outcome_rows)}")
    print(f"Outcome draft:      {outcome_out}")
    print(f"Intervention draft: {interv_out}")


if __name__ == "__main__":
    main()
