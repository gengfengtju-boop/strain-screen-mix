"""Test the trained obesity model's signature as a feature for the effect-size model.

Constraint: the intervention RCTs have NO microbiome samples, so a per-study obesity-
microbiome score is not computable. The available microbiome-derived signal is the
intervened taxon's population OBESITY-ASSOCIATION learned by the obesity classifier
(point-biserial corr of each species with obesity, aggregated to genus). A lean-
protective (negative) target taxon is the "restore a depleted commensal" hypothesis.

This is a supervised refinement of the Phase-4.2 abundance prior (which failed). Tested
the same rigorous way: leave-one-study-out MAE with vs without the feature, per stratum.

    PYTHONPATH=src python scripts/obesity_model/obesity_signature_response_feature.py
"""
from __future__ import annotations

import warnings
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.linear_model import Ridge
from sklearn.metrics import mean_absolute_error
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from proslim_ai.arm_effects import _canonical_unit, _trim_estimate_outliers

warnings.filterwarnings("ignore", category=UserWarning)

ROOT = Path(__file__).resolve().parents[2]
META = ROOT / "data/metadata/sample_metadata_raw.csv"
WIDE = ROOT / "data/taxonomic_profile/species_abundance_wide.csv"
EFFECTS = ROOT / "data/intervention_data/continuous_effect_sizes.upgrade_20260613.csv"
ARMS = ROOT / "data/intervention_data/study_arm_registry.upgrade_20260613.csv"

GENUS_RULES = [
    ("Akkermansia", ("akkermansia", "muct")),
    ("Bifidobacterium", ("bifidobacter", "bb536", "mcc1274", "b420", "idcc", "bbr60")),
    ("Bacillus", ("bacillus", "coagulans", "bc99")),
    ("Lactobacillus", ("lactobacill", "lacticaseib", "lactiplantib", "limosilacto", "paracasei",
                       "rhamnosus", "plantarum", "gasseri", "reuteri", "fermentum", "sakei",
                       "cjls03", "lmt1-48")),
]
STUDY_GENUS_OVERRIDE = {"PMID:39051504": "Bifidobacterium", "PMID:37447365": "Lactobacillus",
                        "PMID:40066582": "Lactobacillus"}
MIXED = {"PMID:32521799", "PMID:40409234", "PMID:41512635", "PMID:40385498"}


def _genus_for(text: str) -> str:
    low = text.lower()
    for genus, terms in GENUS_RULES:
        if any(t in low for t in terms):
            return genus
    return "mixed_or_unknown"


def _genus_obesity_association() -> dict[str, float]:
    """Mean point-biserial corr(species, obesity) per genus over the 206-species set."""
    meta = pd.read_csv(META)[["sample_id", "obesity_status"]]
    meta = meta[meta["obesity_status"].isin(["lean", "obesity"])]
    wide = pd.read_csv(WIDE)
    df = meta.merge(wide, on="sample_id", how="inner")
    y = (df["obesity_status"] == "obesity").astype(int).to_numpy()
    species = [c for c in wide.columns if c != "sample_id"]
    prev = (df[species] > 0).mean()
    species = prev[prev >= 0.10].index.tolist()
    out: dict[str, list[float]] = {}
    for s in species:
        x = np.log10(df[s].astype(float) + 1e-4).to_numpy()
        if x.std() == 0:
            continue
        corr = float(np.corrcoef(x, y)[0, 1])
        genus = s.split("_")[0]
        out.setdefault(genus, []).append(corr)
    return {g: float(np.mean(v)) for g, v in out.items()}


def _pipeline(extra: list[str]) -> Pipeline:
    numeric = ["log10_cfu_per_day", "duration_weeks", "sample_size"] + extra
    pre = ColumnTransformer([
        ("num", Pipeline([("i", SimpleImputer(strategy="median")), ("s", StandardScaler())]), numeric),
        ("cat", Pipeline([("i", SimpleImputer(strategy="most_frequent")),
                          ("e", OneHotEncoder(handle_unknown="ignore"))]), ["intervention_class"]),
    ])
    return Pipeline([("pre", pre), ("ridge", Ridge(alpha=10.0))])


def _loso_mae(group: pd.DataFrame, extra: list[str]) -> float:
    cols = ["log10_cfu_per_day", "duration_weeks", "sample_size", "intervention_class"] + extra
    X, y = group[cols], group["estimate"].astype(float).to_numpy()
    g = group["study_id"].astype(str).to_numpy()
    pred = np.zeros(len(group))
    for s in np.unique(g):
        te = g == s
        model = _pipeline(extra)
        model.fit(X.loc[~te], y[~te])
        pred[te] = model.predict(X.loc[te])
    return float(mean_absolute_error(y, pred))


def main() -> None:
    assoc = _genus_obesity_association()
    print("Genus obesity-association (mean corr with obesity; negative=lean-protective):")
    for g in ["Akkermansia", "Bifidobacterium", "Lactobacillus", "Bacillus"]:
        print(f"  {g:16} {assoc.get(g, float('nan')):+.4f}" if g in assoc else f"  {g:16} (not in >=10% set)")
    blended = np.mean([assoc[g] for g in ("Lactobacillus", "Bifidobacterium") if g in assoc])

    effects = pd.read_csv(EFFECTS)
    effects["confidence"] = effects.get("confidence", "high").fillna("high").astype(str)
    arms = pd.read_csv(ARMS)
    active = arms[arms["arm_role"] == "intervention"].copy()
    active["genus"] = (active["species"].fillna("") + " " + active["strain"].fillna("") + " "
                       + active["arm_label"].fillna("") + " " + active["source_title"].fillna("")).map(_genus_for)
    data = effects.merge(active[["study_id", "intervention_class", "log10_cfu_per_day",
                                 "duration_weeks", "sample_size", "genus"]], on="study_id", how="left")
    data = data[data["intervention_class"].isin(["probiotic", "synbiotic"])].copy()
    data = data[pd.to_numeric(data["estimate"], errors="coerce").notna()].copy()
    data = data[data["confidence"].str.lower().eq("high")].copy()
    miss = data["genus"].isna() | data["genus"].eq("mixed_or_unknown")
    data.loc[miss, "genus"] = data.loc[miss, "comparison"].fillna("").map(_genus_for)
    for sid, g in STUDY_GENUS_OVERRIDE.items():
        data.loc[data["study_id"] == sid, "genus"] = g
    data.loc[data["study_id"].isin(MIXED), "genus"] = "mixed"
    data["obesity_assoc"] = data["genus"].map(assoc)
    data.loc[data["obesity_assoc"].isna(), "obesity_assoc"] = blended  # mixed -> blended
    data["canonical_unit"] = data["effect_unit"].map(_canonical_unit)
    data["stratum"] = data["outcome_domain"].astype(str) + "|" + data["canonical_unit"].astype(str)

    print("\n%-16s %7s %9s %10s   verdict" % ("stratum", "studies", "mae_base", "mae_sig"))
    improved = 0
    total = 0
    for stratum, group in data.groupby("stratum"):
        group, _ = _trim_estimate_outliers(group)
        if group["study_id"].nunique() < 4 or len(group) < 4:
            continue
        total += 1
        base = _loso_mae(group, [])
        sig = _loso_mae(group, ["obesity_assoc"])
        verdict = "sig better" if sig < base else "no gain"
        improved += sig < base
        print("%-16s %7d %9.3f %10.3f   %s" % (stratum, group["study_id"].nunique(), base, sig, verdict))
    print(f"\nStrata improved by the obesity-signature feature: {improved}/{total}")


if __name__ == "__main__":
    main()
