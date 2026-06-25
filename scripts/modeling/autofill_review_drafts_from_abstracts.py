"""Pre-fill the variance-rich review drafts from LOCAL abstract text.

Parses the statistic sentence already attached to each (study, outcome_domain)
row and fills final_value / final_unit / final_direction / p_value_confirmed /
sample_size_confirmed / comparison where a numeric effect can be read. Nothing is
marked `extracted`: every auto-filled row stays `review_status=pending` with a
reviewer_note flagging it for human verification (auto-extraction is error-prone).

Only local evidence_details abstracts are used — no external fetch.

    PYTHONPATH=src python scripts/modeling/autofill_review_drafts_from_abstracts.py
"""
from __future__ import annotations

import glob
import re
from datetime import date
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]

NUM = r"[-+]?\d+(?:\.\d+)?"
UNIT = r"kg/m\^?2|kg/m2|kg|cm|mg/dl|mmol/l|mcu/ml|%"

# plausibility caps on a between-group CHANGE/difference (drop endpoint means/garbage)
DOMAIN_ABS_CAP = {
    "weight": 25.0, "BMI": 12.0, "body_fat": 25.0,
    "waist": 25.0, "glucose": 60.0, "lipid": 120.0,
}
INTERVENTION_TOKENS = [
    ("synbiotic", "synbiotic"), ("postbiotic", "postbiotic"), ("prebiotic", "prebiotic"),
    ("probiotic", "probiotic"), ("lactobacill", "probiotic"), ("bifidobacter", "probiotic"),
    ("akkermansia", "probiotic"), ("inulin", "prebiotic"), ("fructan", "prebiotic"),
]


def _norm(text: str) -> str:
    return (
        text.replace("−", "-").replace("–", "-").replace("—", "-")
        .replace("±", "+/-")
    )


def _unit(raw: str) -> str:
    r = raw.lower().replace("^", "")
    return {"kg/m2": "kg/m2", "mcu/ml": "mcU/ml", "mmol/l": "mmol/L", "mg/dl": "mg/dL"}.get(r, r)


def _p_value(text: str) -> str:
    m = re.search(r"[pP]\s*([<=>])\s*(0?\.\d+|\d+\.\d+)", text)
    return f"{m.group(1)}{m.group(2)}".replace("=", "") if m else ""


def _ci(text: str) -> tuple[float, float] | None:
    m = re.search(rf"95\s*%?\s*CI[:\s]*\(?\s*({NUM})\s*(?:,|to|;|\s)\s*({NUM})", text, re.I)
    if not m:
        return None
    lo, hi = sorted((float(m.group(1)), float(m.group(2))))
    return lo, hi


def _comparison(text: str) -> str:
    low = text.lower()
    for token, label in INTERVENTION_TOKENS:
        if token in low:
            return f"{label}_vs_placebo"
    return ""


def extract(sentence: str, domain: str) -> dict[str, str] | None:
    text = _norm(sentence)

    # (1) two-arm mean (SD) vs mean (SD):  45.9 (4.4) ... vs ... 46.7 (4.3)
    two = re.search(
        rf"({NUM})\s*\(\s*({NUM})\s*\)[^;]*?\bvs\b[^;]*?({NUM})\s*\(\s*({NUM})\s*\)",
        text, re.I,
    )
    if two:
        im, isd, cm, csd = map(float, two.groups())
        est = im - cm
        if abs(est) <= DOMAIN_ABS_CAP.get(domain, 1e9):
            unit_m = re.search(UNIT, text, re.I)
            return {
                "final_value": f"intervention {im} +/- {isd} vs control {cm} +/- {csd}",
                "final_unit": _unit(unit_m.group(0)) if unit_m else "",
                "final_direction": "decrease" if est < 0 else "increase" if est > 0 else "no_change",
                "p_value_confirmed": _p_value(text),
                "method": "two_arm_mean_sd",
            }

    # (2) (weighted-)mean difference / MD / difference : NUM [unit]
    md = re.search(
        rf"(?:weighted[-\s]*mean\s+difference|mean\s+difference|\bWMD\b|\bMD\b|difference)\s*[:,]?\s*({NUM})\s*({UNIT})?",
        text, re.I,
    )
    if md:
        est = float(md.group(1))
        if abs(est) <= DOMAIN_ABS_CAP.get(domain, 1e9):
            # only look for a CI/unit in the clause that follows THIS estimate
            # (stop at the next ';', ']' or ' and ') to avoid mixing outcomes
            tail = re.split(r"[;\]]|\sand\s", text[md.end():], maxsplit=1)[0]
            unit = _unit(md.group(2)) if md.group(2) else (
                _unit(re.search(UNIT, tail, re.I).group(0)) if re.search(UNIT, tail, re.I) else ""
            )
            ci = _ci(tail)
            direction = "decrease" if est < 0 else "increase" if est > 0 else "no_change"
            if ci is not None:
                final_value = f"between-group difference {est} (95% CI {ci[0]} to {ci[1]})"
                method = "difference_with_ci"
            else:
                final_value = f"between-group difference {est}"
                method = "difference_point_estimate"
            return {
                "final_value": final_value,
                "final_unit": unit,
                "final_direction": direction,
                "p_value_confirmed": _p_value(tail) or _p_value(text),
                "method": method,
            }
    return None


def main() -> None:
    drafts = sorted(
        glob.glob(str(ROOT / "data/intervention_data/outcome_review_worksheet.variance_rich_draft_*.csv"))
    )
    if not drafts:
        raise SystemExit("Run export_variance_rich_review_drafts.py first.")
    df = pd.read_csv(drafts[-1], dtype=str).fillna("")

    filled = 0
    with_se = 0
    for idx, row in df.iterrows():
        sentence = row["suggested_text"]
        if not sentence:
            continue
        parsed = extract(sentence, row["outcome_domain"])
        if parsed is None:
            df.at[idx, "reviewer_note"] = row["reviewer_note"] + " | AUTO: no numeric effect parsed - needs full text"
            continue
        df.at[idx, "final_value"] = parsed["final_value"]
        df.at[idx, "final_unit"] = parsed["final_unit"]
        df.at[idx, "final_direction"] = parsed["final_direction"]
        if parsed["p_value_confirmed"]:
            df.at[idx, "p_value_confirmed"] = parsed["p_value_confirmed"]
        if not row["comparison"]:
            df.at[idx, "comparison"] = _comparison(sentence)
        n_match = re.search(r"\b[nN]\s*=\s*\d+", sentence)
        if n_match and not row["sample_size_confirmed"]:
            df.at[idx, "sample_size_confirmed"] = n_match.group(0)
        df.at[idx, "extraction_source"] = "abstract_auto"
        df.at[idx, "reviewer_note"] = (
            f"{row['reviewer_note']} | AUTO[{parsed['method']}]: VERIFY value/unit/direction/p against source"
        )
        # review_status intentionally left 'pending' — requires human confirmation
        filled += 1
        if "95% CI" in parsed["final_value"] or "+/-" in parsed["final_value"]:
            with_se += 1

    # guard: the same final_value assigned to >=3 domains of one study means the
    # source sentence packed multiple outcomes and was mis-split. Blank those.
    reverted = 0
    for evid, grp in df[df["final_value"] != ""].groupby("evidence_id"):
        counts = grp["final_value"].value_counts()
        for value, count in counts.items():
            if count >= 3:
                mask = (df["evidence_id"] == evid) & (df["final_value"] == value)
                df.loc[mask, ["final_value", "final_unit", "final_direction"]] = ""
                df.loc[mask, "reviewer_note"] = (
                    df.loc[mask, "reviewer_note"]
                    + " | AUTO REVERTED: value repeated across outcomes - extract from full text"
                )
                reverted += int(mask.sum())
                filled -= int(mask.sum())

    stamp = date.today().strftime("%Y%m%d")
    out = ROOT / f"data/intervention_data/outcome_review_worksheet.variance_rich_autofilled_{stamp}.csv"
    df.to_csv(out, index=False, encoding="utf-8")
    print(f"Rows total: {len(df)}")
    print(f"Auto-filled with a numeric effect: {filled}")
    print(f"  reverted (value repeated across >=3 outcomes): {reverted}")
    print(f"Left for full-text curation: {len(df) - filled}")
    print(f"Output (all rows still review_status=pending for verification): {out}")


if __name__ == "__main__":
    main()
