"""E1a — add leakage-safe ecological features (alpha diversity, phylum, F/B) to the obesity model.

All added features are per-sample (no cross-sample leakage): Shannon, observed richness,
Simpson, Pielou evenness, phylum-level relative abundances, and log Firmicutes/Bacteroidetes.
Honest prior: a tree already sees all 206 species, so explicit diversity may be redundant;
phylum aggregation could denoise. Evaluated vs species-only under grouped CV + LOSO external.

(E1b — HUMAnN functional pathways — is the orthogonal-information test and needs a new
curatedMetagenomicData fetch; not included here.)

    PYTHONPATH=src python scripts/obesity_model/e1a_diversity_features.py
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import GroupKFold

ROOT = Path(__file__).resolve().parents[2]
META = ROOT / "data/metadata/sample_metadata_raw.csv"
WIDE = ROOT / "data/taxonomic_profile/species_abundance_wide.csv"
OUT = ROOT / "results/prediction_results/e1a_diversity_features_20260614.json"
EPS = 1e-4
MIN_PER_CLASS = 8

GENUS_PHYLUM = {
    # Firmicutes
    "Lactobacillus": "Firmicutes", "Lacticaseibacillus": "Firmicutes", "Lactiplantibacillus": "Firmicutes",
    "Limosilactobacillus": "Firmicutes", "Roseburia": "Firmicutes", "Faecalibacterium": "Firmicutes",
    "Anaerostipes": "Firmicutes", "Blautia": "Firmicutes", "Clostridium": "Firmicutes",
    "Eubacterium": "Firmicutes", "Ruminococcus": "Firmicutes", "Coprococcus": "Firmicutes",
    "Streptococcus": "Firmicutes", "Enterococcus": "Firmicutes", "Intestinimonas": "Firmicutes",
    "Anaerobutyricum": "Firmicutes", "Dialister": "Firmicutes", "Phascolarctobacterium": "Firmicutes",
    "Veillonella": "Firmicutes", "Lactococcus": "Firmicutes", "Turicibacter": "Firmicutes",
    "Oscillibacter": "Firmicutes", "Subdoligranulum": "Firmicutes", "Dorea": "Firmicutes",
    "Lachnospira": "Firmicutes", "Butyrivibrio": "Firmicutes", "Megamonas": "Firmicutes",
    "Megasphaera": "Firmicutes", "Acidaminococcus": "Firmicutes",
    # Bacteroidetes
    "Bacteroides": "Bacteroidetes", "Parabacteroides": "Bacteroidetes", "Alistipes": "Bacteroidetes",
    "Prevotella": "Bacteroidetes", "Odoribacter": "Bacteroidetes", "Barnesiella": "Bacteroidetes",
    "Butyricimonas": "Bacteroidetes", "Paraprevotella": "Bacteroidetes",
    # Actinobacteria
    "Bifidobacterium": "Actinobacteria", "Collinsella": "Actinobacteria", "Eggerthella": "Actinobacteria",
    "Adlercreutzia": "Actinobacteria", "Gordonibacter": "Actinobacteria", "Slackia": "Actinobacteria",
    "Actinomyces": "Actinobacteria", "Senegalimassilia": "Actinobacteria",
    # Verrucomicrobia / Proteobacteria / Euryarchaeota
    "Akkermansia": "Verrucomicrobia",
    "Escherichia": "Proteobacteria", "Klebsiella": "Proteobacteria", "Haemophilus": "Proteobacteria",
    "Bilophila": "Proteobacteria", "Desulfovibrio": "Proteobacteria", "Sutterella": "Proteobacteria",
    "Methanobrevibacter": "Euryarchaeota",
}


def _model():
    return HistGradientBoostingClassifier(max_depth=3, learning_rate=0.05, max_iter=400,
                                          l2_regularization=1.0, random_state=17)


def _grouped(X, y, groups):
    gkf = GroupKFold(n_splits=10); p = np.zeros(len(y))
    for tr, te in gkf.split(X, y, groups):
        m = _model(); m.fit(X[tr], y[tr]); p[te] = m.predict_proba(X[te])[:, 1]
    return float(roc_auc_score(y, p))


def _loso(X, y, studies):
    oof = np.full(len(y), np.nan)
    for s in np.unique(studies):
        te = studies == s
        if y[te].sum() < MIN_PER_CLASS or (~y[te].astype(bool)).sum() < MIN_PER_CLASS:
            continue
        m = _model(); m.fit(X[~te], y[~te]); oof[te] = m.predict_proba(X[te])[:, 1]
    mask = ~np.isnan(oof)
    return float(roc_auc_score(y[mask], oof[mask]))


def main() -> None:
    meta = pd.read_csv(META)[["sample_id", "study_id", "obesity_status"]]
    meta = meta[meta["obesity_status"].isin(["lean", "obesity"])]
    wide = pd.read_csv(WIDE)
    df = meta.merge(wide, on="sample_id", how="inner")
    species = [c for c in wide.columns if c != "sample_id"]
    prev = (df[species] > 0).mean()
    keep = prev[prev >= 0.10].index.tolist()
    rel = df[keep].astype(float).to_numpy()
    relfull = df[species].astype(float).to_numpy()  # all species for diversity
    y = (df["obesity_status"] == "obesity").astype(int).to_numpy()
    groups = df["study_id"].to_numpy()

    # alpha diversity (from full species profile, per-sample)
    p = relfull / np.clip(relfull.sum(axis=1, keepdims=True), EPS, None)
    with np.errstate(divide="ignore", invalid="ignore"):
        shannon = -np.nansum(np.where(p > 0, p * np.log(p), 0.0), axis=1)
    richness = (relfull > 0).sum(axis=1).astype(float)
    simpson = 1.0 - np.nansum(p**2, axis=1)
    evenness = np.where(richness > 1, shannon / np.log(richness), 0.0)

    # phylum aggregation (from full species profile)
    phyla = ["Firmicutes", "Bacteroidetes", "Actinobacteria", "Proteobacteria",
             "Verrucomicrobia", "Euryarchaeota"]
    genus = [s.split("_")[0] for s in species]
    phyl_of = np.array([GENUS_PHYLUM.get(g, "other") for g in genus])
    phy_abund = {ph: relfull[:, phyl_of == ph].sum(axis=1) for ph in phyla}
    fb_log = np.log((phy_abund["Firmicutes"] + EPS) / (phy_abund["Bacteroidetes"] + EPS))

    eco = np.column_stack([shannon, richness, simpson, evenness, fb_log] +
                          [phy_abund[ph] for ph in phyla])
    X_species = np.log10(rel + EPS)
    X_aug = np.column_stack([X_species, eco])

    res = {}
    for name, X in (("species_only", X_species), ("species_plus_ecology", X_aug)):
        g = _grouped(X, y, groups); e = _loso(X, y, groups)
        res[name] = {"n_features": X.shape[1], "grouped_cv_auc": round(g, 4), "loso_external_auc": round(e, 4)}
        print(f"{name:24} feats={X.shape[1]:4d} grouped={g:.4f} external_LOSO={e:.4f}")

    base, aug = res["species_only"], res["species_plus_ecology"]
    report = {
        "experiment": "E1a_ecological_features",
        "added_features": ["shannon", "observed_richness", "simpson", "pielou_evenness",
                           "log_firmicutes_bacteroidetes", *[f"phylum_{p}" for p in phyla]],
        "results": res,
        "grouped_delta": round(aug["grouped_cv_auc"] - base["grouped_cv_auc"], 4),
        "external_delta": round(aug["loso_external_auc"] - base["loso_external_auc"], 4),
        "preregistered_success": "grouped or external AUC +>=0.02",
        "verdict": "helps" if (aug["loso_external_auc"] - base["loso_external_auc"] >= 0.02
                               or aug["grouped_cv_auc"] - base["grouped_cv_auc"] >= 0.02) else "no_meaningful_gain",
        "note": "E1b (HUMAnN functional pathways = orthogonal information) still pending a new fetch.",
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"\ngrouped delta {report['grouped_delta']:+.4f}  external delta {report['external_delta']:+.4f}  -> {report['verdict']}")
    print(f"Report: {OUT}")


if __name__ == "__main__":
    main()
