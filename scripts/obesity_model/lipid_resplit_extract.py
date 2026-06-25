"""Re-extract lipid effects one row per subtype (TC/LDL/HDL/TG), unit-normalized.

The pooled lipid|mg/dL stratum is invalid because each row often mashes several
lipid measures and mixes mg/dL with mmol/L. This parses each curated lipid row's
source_final_value into per-subtype between-group differences, converts mmol/L to
mg/dL, and writes a clean per-subtype effects table plus a modelability report.

    PYTHONPATH=src python scripts/obesity_model/lipid_resplit_extract.py
"""
from __future__ import annotations

import glob
import re
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "data/intervention_data/continuous_effect_sizes.lipid_subtyped_20260613.csv"

MMOL_TO_MGDL = {"TC": 38.67, "LDL": 38.67, "HDL": 38.67, "TG": 88.57}
NUM = r"[-+]?\d+(?:\.\d+)?"


def _subtype(text: str) -> str | None:
    t = text.lower()
    if "triglycer" in t or re.search(r"\btg\b", t):
        return "TG"
    if "ldl" in t:
        return "LDL"
    if "hdl" in t:
        return "HDL"
    if "total cholesterol" in t or re.search(r"\btc\b", t) or "cholesterol" in t:
        return "TC"
    return None


def _clause_difference(clause: str) -> float | None:
    """Between-group difference from a clause: 'A vs B' -> first(A)-first(B); else single number."""
    norm = clause.replace("−", "-").replace("–", "-")
    if " vs" in norm.lower():
        left, right = re.split(r"\bvs\.?\b", norm, maxsplit=1, flags=re.IGNORECASE)
        ln = re.search(NUM, left)
        rn = re.search(NUM, right)
        if ln and rn:
            return float(ln.group()) - float(rn.group())
        return None
    # single explicit difference value (e.g. "LDL-C -10.83 mg/dL")
    n = re.search(NUM, norm)
    return float(n.group()) if n else None


def main() -> None:
    seen = {}
    rows = []
    for f in glob.glob(str(ROOT / "data/intervention_data/clinical_outcome.structured_effects*.csv")):
        if "ascii" in f:
            continue
        try:
            d = pd.read_csv(f, dtype=str)
        except Exception:
            continue
        if "outcome_domain" not in d.columns:
            continue
        for _, r in d[d["outcome_domain"] == "lipid"].iterrows():
            eid = str(r["evidence_id"])
            if eid in seen:
                continue
            seen[eid] = 1
            src = str(r.get("source_final_value", ""))
            unit_field = str(r.get("effect_unit", "")).lower()
            row_is_mmol = "mmol" in unit_field
            for clause in re.split(r"[;]", src):
                sub = _subtype(clause + " " + unit_field)
                if sub is None:
                    continue
                diff = _clause_difference(clause)
                if diff is None:
                    continue
                is_mmol = row_is_mmol or "mmol" in clause.lower()
                diff_mgdl = diff * MMOL_TO_MGDL[sub] if is_mmol else diff
                # plausibility: a between-group lipid change rarely exceeds 100 mg/dL
                if abs(diff_mgdl) > 100:
                    continue
                rows.append({
                    "evidence_id": eid, "lipid_subtype": sub,
                    "effect_difference_mgdl": round(diff_mgdl, 2),
                    "raw_value": round(diff, 3), "source_unit": "mmol/L" if is_mmol else "mg/dL",
                    "between_group_p": str(r.get("between_group_p", "")),
                    "source_clause": clause.strip()[:90],
                })

    out = pd.DataFrame(rows)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(OUT, index=False)
    print(f"Per-subtype lipid effect rows: {len(out)} from {out['evidence_id'].nunique()} studies")
    print(f"Output: {OUT}\n")
    print("Modelability per subtype (>=4 independent studies):")
    for sub, g in out.groupby("lipid_subtype"):
        n = g["evidence_id"].nunique()
        print(f"  {sub:4} studies={n:2d}  diffs(mg/dL)={sorted(g['effect_difference_mgdl'].tolist())}"
              f"  -> {'MODELABLE' if n >= 4 else 'insufficient'}")


if __name__ == "__main__":
    main()
