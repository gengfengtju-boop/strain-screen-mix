"""Phase 4.2 (route 1) — does a population microbiome prior help the effect model?

Adds, per intervention arm, the population-level abundance of the intervened genus in
the obese cohort (curatedMetagenomicData) and its lean/obese depletion, as extra
covariates, then compares leave-one-study-out MAE with vs without them, per stratum.
This is an EXPERIMENT against the locked pipeline (does not modify it). Honest read:
report whether the prior actually lowers MAE / beats the stratum-mean null.

    PYTHONPATH=src python scripts/obesity_model/microbiome_prior_covariate_experiment.py
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

warnings.filterwarnings("ignore", category=UserWarning)  # all-NaN folds in tiny strata

ROOT = Path(__file__).resolve().parents[2]
EFFECTS = ROOT / "data/intervention_data/continuous_effect_sizes.upgrade_20260613.csv"
ARMS = ROOT / "data/intervention_data/study_arm_registry.upgrade_20260613.csv"
META = ROOT / "data/metadata/sample_metadata_raw.csv"
WIDE = ROOT / "data/taxonomic_profile/species_abundance_wide.csv"

# map intervention text -> microbiome genus whose population abundance we look up
GENUS_RULES = [
    ("Akkermansia", ("akkermansia", "muct", "pakk")),
    ("Bifidobacterium", ("bifidobacter", "bb536", "mcc1274", "b420", "idcc", "bbr60", "bbr 60")),
    ("Bacillus", ("bacillus", "coagulans", "bc99")),
    ("Streptococcus", ("streptococcus thermophilus",)),
    ("Lactobacillus", ("lactobacill", "lacticaseibac", "lactiplantibac", "limosilactobac",
                        "paracasei", "rhamnosus", "plantarum", "gasseri", "reuteri", "fermentum",
                        "sakei", "cjls03", "lmt1-48", "k50", "k7", "k8", "k11")),
]


# studies whose genus is not in the comparison/arm text but is known from the
# candidate-strain registry / evidence title (verified by hand).
STUDY_GENUS_OVERRIDE = {
    "PMID:39051504": "Bifidobacterium",   # B. lactis IDCC 4301
    "PMID:37447365": "Lactobacillus",     # L. fermentum K7/K8/K11
    "PMID:40066582": "Lactobacillus",     # E. faecium + L. plantarum (lacto-dominant)
}
# genuinely multi-strain / synbiotic studies: no single genus -> blended prior.
MIXED_STUDIES = {"PMID:32521799", "PMID:40409234", "PMID:41512635", "PMID:40385498"}


def _genus_for(text: str) -> str:
    low = text.lower()
    for genus, terms in GENUS_RULES:
        if any(t in low for t in terms):
            return genus
    return "mixed_or_unknown"


def _genus_priors() -> pd.DataFrame:
    meta = pd.read_csv(META, usecols=["sample_id", "obesity_status"])
    meta = meta[meta["obesity_status"].isin(["lean", "obesity"])]
    header = pd.read_csv(WIDE, nrows=0).columns.tolist()
    genera = sorted({g for g, _ in GENUS_RULES})
    cols = {g: [c for c in header if c.split("_")[0] == g] for g in genera}
    use = ["sample_id"] + sorted({c for v in cols.values() for c in v})
    wide = pd.read_csv(WIDE, usecols=use)
    df = meta.merge(wide, on="sample_id", how="inner")
    rows = []
    for g, members in cols.items():
        if not members:
            continue
        agg = df[members].sum(axis=1)
        obese = agg[df["obesity_status"].to_numpy() == "obesity"]
        lean = agg[df["obesity_status"].to_numpy() == "lean"]
        rows.append({
            "genus": g,
            "genus_obese_abundance": float(obese.mean()),
            "genus_lean_obese_log2ratio": float(np.log2((lean.mean() + 1e-3) / (obese.mean() + 1e-3))),
        })
    return pd.DataFrame(rows)


def _pipeline(extra_numeric: list[str]) -> Pipeline:
    numeric = ["log10_cfu_per_day", "duration_weeks", "sample_size"] + extra_numeric
    pre = ColumnTransformer([
        ("num", Pipeline([("i", SimpleImputer(strategy="median")), ("s", StandardScaler())]), numeric),
        ("cat", Pipeline([("i", SimpleImputer(strategy="most_frequent")),
                          ("e", OneHotEncoder(handle_unknown="ignore"))]), ["intervention_class"]),
    ])
    return Pipeline([("pre", pre), ("ridge", Ridge(alpha=10.0))])


def _loso_mae(group: pd.DataFrame, extra: list[str]) -> tuple[float, float]:
    X = group[["log10_cfu_per_day", "duration_weeks", "sample_size", "intervention_class"] + extra]
    y = group["estimate"].astype(float).to_numpy()
    groups = group["study_id"].astype(str).to_numpy()
    pred = np.zeros(len(group))
    for s in np.unique(groups):
        te = groups == s
        m = _pipeline(extra)
        m.fit(X.loc[~te], y[~te])
        pred[te] = m.predict(X.loc[te])
    null = float(np.mean(np.abs(y - y.mean())))
    return float(mean_absolute_error(y, pred)), null


def main() -> None:
    priors = _genus_priors()
    print("Genus population priors (obese abundance / lean-obese log2 ratio):")
    print(priors.to_string(index=False), "\n")

    effects = pd.read_csv(EFFECTS)
    effects["confidence"] = effects.get("confidence", "high").fillna("high").astype(str)
    arms = pd.read_csv(ARMS)
    active = arms[arms["arm_role"] == "intervention"].copy()
    active["genus"] = (active["species"].fillna("") + " " + active["strain"].fillna("") + " "
                       + active["arm_label"].fillna("") + " " + active["source_title"].fillna("")).map(_genus_for)
    data = effects.merge(
        active[["study_id", "intervention_class", "log10_cfu_per_day", "duration_weeks", "sample_size", "genus"]],
        on="study_id", how="left",
    )
    data = data[data["intervention_class"].isin(["probiotic", "synbiotic"])].copy()
    data = data[pd.to_numeric(data["estimate"], errors="coerce").notna()].copy()
    data = data[data["confidence"].str.lower().eq("high")].copy()
    # fall back genus from comparison text where arm-derived genus was unknown
    miss = data["genus"].isin(["mixed_or_unknown", np.nan]) | data["genus"].isna()
    data.loc[miss, "genus"] = data.loc[miss, "comparison"].fillna("").map(_genus_for)
    # apply hand-verified per-study genus overrides
    for sid, genus in STUDY_GENUS_OVERRIDE.items():
        data.loc[data["study_id"] == sid, "genus"] = genus
    data.loc[data["study_id"].isin(MIXED_STUDIES), "genus"] = "mixed_synbiotic"
    data = data.merge(priors, on="genus", how="left")
    # genuinely multi-strain studies get a blended Lacto+Bifido prior (typical mix)
    blend = priors[priors["genus"].isin(["Lactobacillus", "Bifidobacterium"])]
    if len(blend):
        b_ab = float(blend["genus_obese_abundance"].mean())
        b_lr = float(blend["genus_lean_obese_log2ratio"].mean())
        nan_ab = data["genus_obese_abundance"].isna()
        data.loc[nan_ab, "genus_obese_abundance"] = b_ab
        data.loc[nan_ab, "genus_lean_obese_log2ratio"] = b_lr
    data["canonical_unit"] = data["effect_unit"].map(_canonical_unit)
    data["stratum"] = data["outcome_domain"].astype(str) + "|" + data["canonical_unit"].astype(str)

    print("genus coverage of modeling rows:")
    print(data["genus"].value_counts().to_dict(), "\n")

    extra = ["genus_obese_abundance", "genus_lean_obese_log2ratio"]
    print(f"{'stratum':16} {'studies':>7} {'mae_base':>9} {'mae_micro':>10} {'null':>7}  verdict")
    for stratum, group in data.groupby("stratum"):
        group, _ = _trim_estimate_outliers(group)
        if group["study_id"].nunique() < 4 or len(group) < 4:
            continue
        base, null = _loso_mae(group, [])
        micro, _ = _loso_mae(group, extra)
        verdict = "micro better" if micro < base else "no gain"
        beats = " BEATS_NULL" if micro < null else ""
        print(f"{stratum:16} {group['study_id'].nunique():7d} {base:9.3f} {micro:10.3f} {null:7.3f}  {verdict}{beats}")


if __name__ == "__main__":
    main()
