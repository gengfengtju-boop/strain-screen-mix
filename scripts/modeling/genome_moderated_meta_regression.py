"""Genome-moderated meta-regression: does a strain functional feature explain heterogeneity?

Maps each SE-bearing intervention study to the genomic functional potential of its
intervened genus (data/strain_genome/strain_genomic_functional_features.csv) and runs a
fixed-effect meta-regression per stratum. Targets weight|kg (I^2=80% in the intercept-only
random-effects meta-analysis) to test whether e.g. mucin-degradation vs BSH/lactate
mechanism explains why Akkermansia and Lactobacillus effects disagree.

    PYTHONPATH=src python scripts/modeling/genome_moderated_meta_regression.py
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from proslim_ai.arm_effects import _canonical_unit, _dersimonian_laird, _meta_regression_moderator, _trim_estimate_outliers

ROOT = Path(__file__).resolve().parents[2]
GENOME = ROOT / "data/strain_genome/strain_genomic_functional_features.csv"

GENUS_RULES = [
    ("Akkermansia", ("akkermansia", "muct")),
    ("Bifidobacterium", ("bifidobacter", "bb536", "mcc1274", "b420", "idcc", "bbr60")),
    ("Bacillus", ("bacillus", "coagulans", "bc99")),
    ("Lactobacillus", ("lactobacill", "lacticaseib", "lactiplantib", "limosilacto", "paracasei",
                       "rhamnosus", "plantarum", "gasseri", "reuteri", "fermentum", "sakei",
                       "cjls03", "lmt1-48")),
]
STUDY_GENUS_OVERRIDE = {"PMID:39051504": "Bifidobacterium", "PMID:37447365": "Lactobacillus",
                        "PMID:40066582": "Lactobacillus", "DOI:10.3803/EnM.2020.35.2.425": "Lactobacillus"}
MODERATORS = ["bsh_potential", "butyrate_scfa_potential", "mucin_interaction", "propionate_potential"]


def _genus_for(text: str) -> str:
    low = text.lower()
    for genus, terms in GENUS_RULES:
        if any(t in low for t in terms):
            return genus
    return "mixed"


def main() -> None:
    feats = pd.read_csv(GENOME).set_index("genus")
    e = pd.read_csv(ROOT / "data/intervention_data/continuous_effect_sizes.upgrade_20260613.csv")
    e["confidence"] = e.get("confidence", "high").fillna("high").astype(str)
    a = pd.read_csv(ROOT / "data/intervention_data/study_arm_registry.upgrade_20260613.csv")
    act = a[a["arm_role"] == "intervention"]
    act = act.assign(genus=(act["species"].fillna("") + " " + act["strain"].fillna("") + " "
                            + act["arm_label"].fillna("") + " " + act["source_title"].fillna("")).map(_genus_for))
    m = e.merge(act[["study_id", "intervention_class", "genus"]], on="study_id", how="left")
    m = m[m["intervention_class"].isin(["probiotic", "synbiotic"])].copy()
    m["estimate"] = pd.to_numeric(m["estimate"], errors="coerce")
    m["se"] = pd.to_numeric(m["standard_error"], errors="coerce")
    m = m[m["estimate"].notna() & (m["se"] > 0) & m["confidence"].str.lower().eq("high")]
    for sid, g in STUDY_GENUS_OVERRIDE.items():
        m.loc[m["study_id"] == sid, "genus"] = g
    m.loc[m["genus"].isna() | m["genus"].eq("mixed"), "genus"] = (
        m.loc[m["genus"].isna() | m["genus"].eq("mixed"), "comparison"].fillna("").map(_genus_for))
    m["canonical_unit"] = m["effect_unit"].map(_canonical_unit)
    m["stratum"] = m["outcome_domain"].astype(str) + "|" + m["canonical_unit"].astype(str)

    for stratum in ["weight|kg", "body_fat|kg"]:
        g = m[m["stratum"] == stratum].copy()
        g, _ = _trim_estimate_outliers(g)
        g = g.sort_values("se").drop_duplicates("study_id", keep="first")
        if g["study_id"].nunique() < 3:
            print(f"\n{stratum}: <3 SE-bearing studies, skipped")
            continue
        for mod in MODERATORS:
            g[mod] = g["genus"].map(feats[mod]).astype(float)
        base = _dersimonian_laird(g["estimate"].to_numpy(), (g["se"] ** 2).to_numpy())
        print(f"\n=== {stratum} (k={base['k_studies']}) ===")
        print(f"  genera: {sorted(g['genus'].unique())}")
        print(f"  intercept-only random-effects: pooled {base['pooled_effect']} I2={base['i2_percent']}%")
        for mod in MODERATORS:
            x = g[mod].to_numpy()
            if np.ptp(x) == 0:
                print(f"  {mod:24} (no variation across these studies)")
                continue
            res = _meta_regression_moderator(g["estimate"].to_numpy(), (g["se"] ** 2).to_numpy(), x)
            drop = base["i2_percent"] - res["residual_i2_percent"]
            flag = "  <-- explains heterogeneity" if drop > 20 and res["slope_p"] < 0.10 else ""
            print(f"  {mod:24} slope={res['moderator_slope']:+.3f} (p={res['slope_p']:.3f}) "
                  f"residual_I2={res['residual_i2_percent']:.0f}% (was {base['i2_percent']:.0f}%){flag}")
    print("\nNote: exploratory at k=3-7 (df=k-2); a moderator that drops residual I^2 with a "
          "directional slope is hypothesis-generating, not confirmatory.")


if __name__ == "__main__":
    main()
