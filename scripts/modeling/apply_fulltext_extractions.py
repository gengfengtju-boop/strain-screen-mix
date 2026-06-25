"""Apply hand-verified full-text extractions into the review worksheet.

Each entry below was read directly from the article full text in D:\\Download
(text dumped to .fulltext_extract/). Values are recorded with provenance in
reviewer_note. review_status is set to 'extracted' for direct full-text reads.
Rows not covered here stay pending for continued curation.

    PYTHONPATH=src python scripts/modeling/apply_fulltext_extractions.py
"""
from __future__ import annotations

import glob
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]

# (evidence_id, outcome_domain) -> extracted fields
EXTRACTIONS: dict[tuple[str, str], dict[str, str]] = {
    # PMID:40965226 — SF68/phytosterols/5-MTHF "PrObesity" RCT (n=40). Table reports
    # WITHIN-group changes per arm with within-group p; no between-group test given.
    # effect = probiotic change minus control change (point estimate, no between-group SE).
    ("PMID:40965226", "waist"): {
        "final_value": "intervention -1.8 vs control -1.2",
        "final_unit": "cm", "final_direction": "decrease",
        "comparison": "SF68_probiotic_vs_placebo", "time_point": "12 weeks",
        "p_value_confirmed": "not_reported", "sample_size_confirmed": "n=40",
        "note": "full text: within-group change probiotic -1.8cm (p=0.008) vs control -1.2cm (p=0.039); no between-group test",
    },
    ("PMID:40965226", "body_fat"): {
        "final_value": "intervention -1.8 vs control -1.3",
        "final_unit": "kg", "final_direction": "decrease",
        "comparison": "SF68_probiotic_vs_placebo", "time_point": "12 weeks",
        "p_value_confirmed": "not_reported", "sample_size_confirmed": "n=40",
        "note": "full text: within-group fat mass probiotic -1.8kg (p=0.007) vs control -1.3kg (p=0.020); no between-group test",
    },
    # PMID:32521799 — META-ANALYSIS (pooled mean difference vs control), NOT a single RCT.
    ("PMID:32521799", "BMI"): {
        "final_value": "between-group difference -0.45 (95% CI -0.69 to -0.21)",
        "final_unit": "kg/m2", "final_direction": "decrease",
        "comparison": "probiotic_vs_control_pooled", "time_point": "",
        "p_value_confirmed": "<0.001", "sample_size_confirmed": "16 studies n=1256",
        "note": "META-ANALYSIS pooled DM (not single RCT) - flag before arm-level use",
    },
    ("PMID:32521799", "lipid"): {
        "final_value": "between-group difference -13.27 (95% CI -16.74 to -9.80)",
        "final_unit": "mg/dL", "final_direction": "decrease",
        "comparison": "probiotic_vs_control_pooled", "time_point": "",
        "p_value_confirmed": "<0.05", "sample_size_confirmed": "",
        "note": "META-ANALYSIS pooled total-cholesterol MD (not single RCT) - flag before arm-level use",
    },
    # EUROPEPMC:40218949 — L. plantarum LMT1-48, Nutrients 2025 RCT (n=106, 53/arm).
    # DXA body-fat mass: experimental arm 12-wk change -1.6 +/- 1.9 kg (within p<0.001),
    # between-group p=0.009 vs placebo. Arm-level change with SD (SE-computable).
    ("EUROPEPMC:40218949", "body_fat"): {
        "final_value": "intervention -1.6 +/- 1.9",
        "final_unit": "kg", "final_direction": "decrease",
        "comparison": "LMT1-48_probiotic_vs_placebo", "time_point": "12 weeks",
        "p_value_confirmed": "0.009", "sample_size_confirmed": "n=106; n=53 per arm",
        "note": "full text Table: experimental DXA fat-mass change -1.6+/-1.9 kg (30.0->28.3), between-group p=0.009",
    },
}


def main() -> None:
    drafts = sorted(
        glob.glob(str(ROOT / "data/intervention_data/outcome_review_worksheet.variance_rich_autofilled_*.csv"))
    )
    path = Path(drafts[-1])
    df = pd.read_csv(path, dtype=str).fillna("")

    applied = 0
    for (evid, domain), fields in EXTRACTIONS.items():
        mask = (df["evidence_id"] == evid) & (df["outcome_domain"] == domain)
        if not mask.any():
            print(f"  WARN: no row for {evid} / {domain}")
            continue
        df.loc[mask, "final_value"] = fields["final_value"]
        df.loc[mask, "final_unit"] = fields["final_unit"]
        df.loc[mask, "final_direction"] = fields["final_direction"]
        df.loc[mask, "comparison"] = fields["comparison"]
        df.loc[mask, "time_point"] = fields["time_point"]
        df.loc[mask, "p_value_confirmed"] = fields["p_value_confirmed"]
        if fields["sample_size_confirmed"]:
            df.loc[mask, "sample_size_confirmed"] = fields["sample_size_confirmed"]
        df.loc[mask, "extraction_source"] = "full_text"
        df.loc[mask, "reviewer"] = "claude_fulltext"
        df.loc[mask, "review_status"] = "extracted"
        df.loc[mask, "reviewer_note"] = "FULLTEXT: " + fields["note"]
        applied += int(mask.sum())

    out = path.with_name(path.name.replace("autofilled", "fulltext_curated"))
    df.to_csv(out, index=False, encoding="utf-8")
    print(f"Applied full-text extractions to {applied} rows")
    print(f"Output: {out}")


if __name__ == "__main__":
    main()
