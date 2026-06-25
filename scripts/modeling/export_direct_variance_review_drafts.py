from __future__ import annotations

import json
import re
from pathlib import Path

import pandas as pd

from proslim_ai.run_stamp import production_run_stamp


ROOT = Path(__file__).resolve().parents[2]
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


def _best_stat_sentence(text: str, domain: str) -> str:
    patterns = {
        "weight": r"body weight|weight loss|weight change",
        "BMI": r"\bbmi\b|body mass index",
        "body_fat": r"body fat|fat mass|visceral fat|adiposity",
        "lipid_TG": r"triglycerid|\btg\b",
        "waist": r"waist circumference|\bwaist\b",
    }
    sentences = re.split(r"(?<=[.;])\s+", text)
    candidates = [
        sentence.strip()
        for sentence in sentences
        if re.search(patterns[domain], sentence, re.I)
        and re.search(r"95\s*%?\s*ci|\+/-|\+-|±|\bsd\b|standard deviation", sentence, re.I)
    ]
    return max(candidates, key=len)[:600] if candidates else ""


def main() -> None:
    stamp = production_run_stamp()
    queue = pd.read_csv(
        ROOT / f"results/prediction_results/direct_variance_review_queue_{stamp}.csv"
    )
    manifest = json.loads(
        (ROOT / "config/continuous_effect_upgrade_manifest.json").read_text(
            encoding="utf-8"
        )
    )
    details = pd.concat(
        [pd.read_csv(ROOT / path) for path in manifest["evidence_details"]],
        ignore_index=True,
        sort=False,
    ).drop_duplicates("evidence_id", keep="last").set_index("evidence_id")

    outcome_rows: list[dict[str, object]] = []
    intervention_rows: dict[str, dict[str, object]] = {}
    for _, item in queue.iterrows():
        evidence_id = str(item["evidence_id"])
        detail = details.loc[evidence_id] if evidence_id in details.index else pd.Series()
        text = " ".join(
            str(detail.get(field, "") or "")
            for field in ("abstract", "primary_outcomes", "secondary_outcomes", "arms")
        )
        prefix, _, accession = evidence_id.partition(":")
        sentence = _best_stat_sentence(text, str(item["outcome_domain"]))
        p_match = re.search(r"p\s*[<=>]\s*0?\.\d+", sentence, re.I)
        enrollment = detail.get("enrollment", "")
        sample_size = (
            f"n={int(float(enrollment))} enrolled"
            if pd.notna(enrollment) and str(enrollment).strip()
            else ""
        )
        outcome_rows.append(
            {
                "evidence_id": evidence_id,
                "source_database": prefix,
                "source_accession": accession,
                "title": item.get("title", ""),
                "outcome_domain": item["outcome_domain"],
                "suggested_text": sentence,
                "suggested_p_value": p_match.group(0) if p_match else "",
                "final_value": "",
                "final_unit": item["canonical_unit"],
                "final_direction": "",
                "comparison": "",
                "time_point": "",
                "p_value_confirmed": "",
                "sample_size_confirmed": sample_size,
                "extraction_source": "direct_variance_targeted_draft",
                "reviewer": "",
                "review_status": "pending",
                "reviewer_note": (
                    f"{item['queue_type']}; {item['recommended_action']}; "
                    "required: effect estimate plus reported CI/SE or both-arm SD and n"
                ),
            }
        )
        intervention_rows[evidence_id] = {
            "evidence_id": evidence_id,
            "source_database": prefix,
            "source_accession": accession,
            "title": item.get("title", ""),
            "intervention_component": "",
            "suggested_intervention": detail.get("clinical_interventions", ""),
            "suggested_duration": "",
            "suggested_cfu": "",
            "suggested_dose": "",
            "final_species": "",
            "final_strain": "",
            "final_total_CFU_per_day": "",
            "final_log10_CFU_per_day": "",
            "final_prebiotic_type": "",
            "final_prebiotic_dose_g_day": "",
            "final_duration_weeks": "",
            "final_dosage_form": "",
            "reviewer": "",
            "review_status": "pending",
            "reviewer_note": "required for interpretable moderator modeling",
        }

    output_dir = ROOT / "data/intervention_data"
    outcome_output = output_dir / f"outcome_review_worksheet.direct_variance_{stamp}.csv"
    intervention_output = (
        output_dir / f"intervention_review_worksheet.direct_variance_{stamp}.csv"
    )
    pd.DataFrame(outcome_rows, columns=OUTCOME_FIELDS).to_csv(outcome_output, index=False)
    pd.DataFrame(intervention_rows.values(), columns=INTERVENTION_FIELDS).to_csv(
        intervention_output, index=False
    )
    print(outcome_output)
    print(intervention_output)


if __name__ == "__main__":
    main()
