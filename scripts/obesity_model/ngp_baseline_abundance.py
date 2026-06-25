"""Phase 4.1 — baseline abundance of human-derived NGPs in obese vs lean.

Joins curatedMetagenomicData sample metadata (obesity_status/BMI) to the species
abundance matrix and, for each next-generation-probiotic species, reports prevalence
and abundance by weight group plus a lean-vs-obese Mann-Whitney test. This is the
microbiome-state evidence that motivates NGP candidates and feeds the responder
covariate (Phase 4.2).

    PYTHONPATH=src python scripts/obesity_model/ngp_baseline_abundance.py
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import mannwhitneyu

ROOT = Path(__file__).resolve().parents[2]
META = ROOT / "data/metadata/sample_metadata_raw.csv"
WIDE = ROOT / "data/taxonomic_profile/species_abundance_wide.csv"
OUT = ROOT / "results/prediction_results/ngp_baseline_abundance_by_obesity_20260613.csv"

# NGP genera/species of interest (match column names case-insensitively)
NGP_KEYS = [
    "Akkermansia", "Faecalibacterium_prausnitzii", "Christensenella_minuta",
    "Bacteroides_uniformis", "Clostridium_butyricum", "Hafnia_alvei",
    "Roseburia", "Dysosmobacter", "Phascolarctobacterium", "Anaerobutyricum",
    "Parabacteroides_distasonis",
]


def main() -> None:
    meta = pd.read_csv(META, usecols=["sample_id", "obesity_status", "BMI", "study_id"])
    # collapse to lean vs obese poles; keep overweight separate for the table
    meta = meta[meta["obesity_status"].isin(["lean", "overweight", "obesity"])]

    header = pd.read_csv(WIDE, nrows=0).columns.tolist()
    ngp_cols = [c for c in header if any(k.lower() in c.lower() for k in NGP_KEYS)]
    wide = pd.read_csv(WIDE, usecols=["sample_id"] + ngp_cols)

    df = meta.merge(wide, on="sample_id", how="inner")
    print(f"Samples joined: {len(df)} | NGP species columns: {len(ngp_cols)}")
    print("Group sizes:", df["obesity_status"].value_counts().to_dict())

    rows = []
    lean = df[df["obesity_status"] == "lean"]
    obese = df[df["obesity_status"] == "obesity"]
    for col in ngp_cols:
        rec = {"species": col}
        for grp_name, grp in [("lean", lean), ("overweight", df[df["obesity_status"] == "overweight"]), ("obesity", obese)]:
            vals = grp[col].astype(float)
            rec[f"{grp_name}_prevalence"] = round((vals > 0).mean(), 4)
            rec[f"{grp_name}_mean_abund"] = round(vals.mean(), 6)
        # pooled lean vs obese test (CONFOUNDED by study — see consistency below)
        lv, ov = lean[col].astype(float), obese[col].astype(float)
        if (lv > 0).sum() + (ov > 0).sum() >= 10:
            try:
                u, p = mannwhitneyu(lv, ov, alternative="two-sided")
                rec["pooled_lean_vs_obese_p"] = round(p, 5)
            except ValueError:
                rec["pooled_lean_vs_obese_p"] = np.nan
        else:
            rec["pooled_lean_vs_obese_p"] = np.nan
        rec["pooled_lean_higher"] = bool(lv.mean() > ov.mean())

        # study-stratified consistency: within each study that has both poles,
        # is lean-mean > obese-mean? Removes between-study confounding.
        n_eval = n_lean_higher = 0
        for _, g in df.groupby("study_id"):
            gl = g[g["obesity_status"] == "lean"][col].astype(float)
            go = g[g["obesity_status"] == "obesity"][col].astype(float)
            if len(gl) >= 5 and len(go) >= 5:
                n_eval += 1
                if gl.mean() > go.mean():
                    n_lean_higher += 1
        rec["studies_evaluated"] = n_eval
        rec["studies_lean_higher"] = n_lean_higher
        rec["consistency"] = round(n_lean_higher / n_eval, 2) if n_eval else np.nan
        rows.append(rec)

    out = pd.DataFrame(rows).sort_values("pooled_lean_vs_obese_p", na_position="last")
    OUT.parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(OUT, index=False)
    print(f"\nWrote {len(out)} NGP species rows -> {OUT}\n")
    show = ["species", "lean_prevalence", "obesity_prevalence", "pooled_lean_vs_obese_p",
            "pooled_lean_higher", "studies_evaluated", "studies_lean_higher", "consistency"]
    with pd.option_context("display.width", 220, "display.max_columns", None):
        print(out[show].head(21).to_string(index=False))


if __name__ == "__main__":
    main()
