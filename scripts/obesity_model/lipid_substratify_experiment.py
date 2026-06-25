"""Diagnose/repair the lipid stratum by splitting into TC/LDL/HDL/TG and normalizing units.

The pooled `lipid|mg/dL` stratum mixes incomparable quantities (mg/dL vs mmol/L, and
total cholesterol vs LDL vs HDL vs triglycerides), which is why its leave-one-study-out
MAE (~41) blows past the stratum-mean null (~7). This splits by lipid subtype, converts
mmol/L to mg/dL with subtype-specific factors, and reports how many studies each subtype
has and whether it is independently modelable.

    PYTHONPATH=src python scripts/obesity_model/lipid_substratify_experiment.py
"""
from __future__ import annotations

import re
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
EFFECTS = ROOT / "data/intervention_data/continuous_effect_sizes.upgrade_20260613.csv"

# mmol/L -> mg/dL conversion factors (molar mass based)
MMOL_TO_MGDL = {"TC": 38.67, "LDL": 38.67, "HDL": 38.67, "TG": 88.57}


def _subtype(text: str) -> str:
    t = text.lower()
    # order matters: HDL/LDL before generic cholesterol
    if "triglycer" in t or re.search(r"\btg\b", t):
        return "TG"
    if "ldl" in t:
        return "LDL"
    if "hdl" in t:
        return "HDL"
    if "total cholesterol" in t or re.search(r"\btc\b", t) or "cholesterol" in t:
        return "TC"
    return "unspecified"


def _is_mmol(text: str) -> bool:
    return "mmol" in text.lower()


def main() -> None:
    e = pd.read_csv(EFFECTS)
    lip = e[e["outcome_domain"] == "lipid"].copy()
    lip = lip[lip.get("confidence", "high").fillna("high").str.lower().eq("high")].copy()

    def _col(name: str) -> pd.Series:
        return lip[name].fillna("") if name in lip.columns else pd.Series([""] * len(lip), index=lip.index)

    txt = _col("effect_unit") + " | " + _col("source_final_value") + " | " + _col("source_note")
    lip["subtype"] = txt.map(_subtype)
    lip["was_mmol"] = lip["effect_unit"].fillna("").map(_is_mmol)
    # normalize mmol/L -> mg/dL on the estimate so subtype strata share one scale
    factor = lip["subtype"].map(MMOL_TO_MGDL).fillna(38.67)
    lip["estimate_mgdl"] = np.where(lip["was_mmol"],
                                    pd.to_numeric(lip["estimate"], errors="coerce") * factor,
                                    pd.to_numeric(lip["estimate"], errors="coerce"))

    print("Lipid rows by subtype (after unit normalization to mg/dL):\n")
    for sub, g in lip.groupby("subtype"):
        ests = g["estimate_mgdl"].round(1).tolist()
        print(f"  {sub:12} studies={g['study_id'].nunique():2d}  estimates(mg/dL)={ests}")

    print("\nModelability (minimum 4 independent studies per subtype):")
    modelable = []
    for sub, g in lip.groupby("subtype"):
        n = g["study_id"].nunique()
        verdict = "MODELABLE" if n >= 4 else "insufficient (<4 studies)"
        if n >= 4:
            modelable.append(sub)
        print(f"  {sub:12} {n} studies -> {verdict}")

    print("\nHonest read:")
    if not modelable:
        print("  No lipid subtype reaches 4 independent studies. The pooled lipid|mg/dL")
        print("  model (MAE~41) was an artifact of mixing incomparable measures/units.")
        print("  Correct action: report lipid as insufficient_data per-subtype, not a")
        print("  single misleading stratum. Needs more curated per-subtype studies.")
    else:
        print(f"  Modelable subtypes: {modelable} — refit these separately.")


if __name__ == "__main__":
    main()
