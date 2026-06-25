"""Study-aware differential abundance: lean (no insulin resistance) vs obese.

Goal: identify the gut species whose relative abundance differs most between
metabolically-healthy lean people and obese people, as data-driven targets for
weight-loss strain-combination design (replacing evidence-provenance artifacts
like a single product's fixed 3-strain block).

Honest method:
  - lean-no-IR  = obesity_status == lean AND disease_status == healthy
                  (excludes T2D / IGT, i.e. insulin-resistance / glucose disorders)
  - obese       = obesity_status == obesity
  - The 8k samples span 45 studies; pooled tests are confounded by batch/country/
    sequencing. So differences are computed WITHIN each study (only studies with
    >=10 per group), then aggregated across studies by the MEDIAN effect, and a
    species is only trusted when its direction is consistent across most studies.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
EPS = 1e-3          # 0.001% pseudocount on the percent scale
MIN_PER_GROUP = 10
MIN_PREVALENCE = 0.10   # species present in >=10% of analysed samples
OUT_DIR = ROOT / "results/prediction_results"


def main() -> None:
    meta = pd.read_csv(ROOT / "data/metadata/sample_metadata_raw.csv")
    meta["group"] = np.where(
        (meta["obesity_status"] == "lean") & (meta["disease_status"] == "healthy"),
        "lean_healthy",
        np.where(meta["obesity_status"] == "obesity", "obese", "other"))
    meta = meta[meta["group"].isin(["lean_healthy", "obese"])][["sample_id", "study_id", "group"]]

    abund = pd.read_csv(ROOT / "data/taxonomic_profile/species_abundance_wide.csv").set_index("sample_id")
    df = meta.join(abund, on="sample_id").dropna(subset=[abund.columns[0]])
    species = list(abund.columns)

    # keep studies with >=10 per group
    counts = df.groupby(["study_id", "group"]).size().unstack(fill_value=0)
    good = counts[(counts.get("lean_healthy", 0) >= MIN_PER_GROUP) &
                  (counts.get("obese", 0) >= MIN_PER_GROUP)].index.tolist()
    df = df[df["study_id"].isin(good)]
    n_studies = len(good)

    # prevalence filter
    prev = (df[species] > 0).mean()
    species = [s for s in species if prev[s] >= MIN_PREVALENCE]

    # per-study group means
    per = {}   # species -> list of (delta_pp, log2fc, d) across studies
    rows_studymean = []
    for st in good:
        sub = df[df["study_id"] == st]
        L = sub[sub["group"] == "lean_healthy"][species]
        O = sub[sub["group"] == "obese"][species]
        mL, mO = L.mean(), O.mean()
        sL, sO = L.std(ddof=1), O.std(ddof=1)
        nL, nO = len(L), len(O)
        psd = np.sqrt(((nL - 1) * sL**2 + (nO - 1) * sO**2) / (nL + nO - 2)).replace(0, np.nan)
        delta = mL - mO
        log2fc = np.log2((mL + EPS) / (mO + EPS))
        d = (mL - mO) / psd
        for g in species:
            per.setdefault(g, []).append((delta[g], log2fc[g], d[g]))

    recs = []
    for g, vals in per.items():
        deltas = np.array([v[0] for v in vals])
        l2 = np.array([v[1] for v in vals])
        ds = np.array([v[2] for v in vals if np.isfinite(v[2])])
        med_delta = float(np.median(deltas))
        n_lean_higher = int((deltas > 0).sum())
        consistency = max(n_lean_higher, n_studies - n_lean_higher) / n_studies
        recs.append({
            "species": g,
            "direction": "lean_enriched" if med_delta > 0 else "obese_enriched",
            "median_abund_diff_pp": round(med_delta, 4),
            "abs_median_diff_pp": round(abs(med_delta), 4),
            "median_log2fc": round(float(np.median(l2)), 3),
            "pooled_cohens_d": round(float(np.median(ds)) if len(ds) else np.nan, 3),
            "studies_consistent": max(n_lean_higher, n_studies - n_lean_higher),
            "n_studies": n_studies,
            "consistency": round(consistency, 2),
            "mean_abund_lean_pp": round(float(df[df.group=="lean_healthy"][g].mean()), 4),
            "mean_abund_obese_pp": round(float(df[df.group=="obese"][g].mean()), 4),
        })
    res = pd.DataFrame(recs)
    # trusted = consistent direction across most studies
    res["trusted"] = res["consistency"] >= 0.70
    res = res.sort_values("abs_median_diff_pp", ascending=False)
    full = OUT_DIR / "lean_vs_obese_differential_abundance_20260625.csv"
    res.to_csv(full, index=False)

    top5 = res[res["trusted"]].head(5)
    top5.to_csv(OUT_DIR / "lean_vs_obese_top5_species_20260625.csv", index=False)

    print(f"analysed studies={n_studies} | species after prevalence filter={len(species)}")
    print(f"lean-healthy samples={int((df.group=='lean_healthy').sum())} | obese={int((df.group=='obese').sum())}")
    print("\n=== TOP 5 species by |cross-study abundance difference| (trusted) ===")
    for _, r in top5.iterrows():
        print(f"  {r['species'][:42]:42} {r['direction']:14} "
              f"Δ={r['median_abund_diff_pp']:+.3f}pp  log2FC={r['median_log2fc']:+.2f}  "
              f"d={r['pooled_cohens_d']:+.2f}  一致 {r['studies_consistent']}/{r['n_studies']}")
    print("\nwrote", full.relative_to(ROOT))
    print("wrote", (OUT_DIR / 'lean_vs_obese_top5_species_20260625.csv').relative_to(ROOT))


if __name__ == "__main__":
    main()
