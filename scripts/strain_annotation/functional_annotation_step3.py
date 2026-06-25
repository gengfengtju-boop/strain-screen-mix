"""Step 3 — genus-level functional annotation of the screening catalog (comparative-genomics priors).

NOT de-novo genome annotation (which needs prokka/antiSMASH/HMM searches on each genome).
This assigns each genus to its established metabolic guild (butyrate / propionate / lactate /
mucin / BSH / polyphenol / methanogen / sulfate-reducer / amine) from gut-microbiome comparative
genomics, giving 0-2 functional-potential scores plus an obesity-relevant mechanism label and an
adverse-mechanism flag (H2S sulfate reducers, histamine/amine producers). Strain-level
confirmation still requires genome annotation.

    PYTHONPATH=src python scripts/strain_annotation/functional_annotation_step3.py
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
CAT = ROOT / "results/candidate_strain_scores/strain_screening_catalog_safety_20260613.csv"
OUT = ROOT / "results/candidate_strain_scores/strain_screening_catalog_functional_20260613.csv"
REF = ROOT / "data/strain_genome/genus_functional_guild_reference_20260613.csv"

# metabolic guilds (gut-microbiome comparative genomics)
BUTYRATE = {  # butyrate producers (anti-inflammatory, barrier, anti-obesity)
    "Faecalibacterium", "Roseburia", "Anaerostipes", "Anaerotruncus", "Butyrivibrio",
    "Coprococcus", "Intestinimonas", "Oscillibacter", "Flavonifractor", "Pseudoflavonifractor",
    "Agathobaculum", "Butyricimonas", "Gemmiger", "Lachnospira", "Fusicatenibacter",
    "Ruthenibacterium", "Lawsonibacter", "Monoglobus", "Eisenbergiella", "Anaeromassilibacillus",
    "Faecalitalea", "Coprobacillus", "Subdoligranulum", "Anaerobutyricum",
}
PROPIONATE = {  # propionate / succinate producers
    "Bacteroides", "Parabacteroides", "Phascolarctobacterium", "Veillonella", "Dialister",
    "Akkermansia", "Alistipes", "Odoribacter", "Prevotella", "Paraprevotella", "Megamonas",
    "Acidaminococcus", "Barnesiella", "Coprobacter", "Parasutterella", "Turicimonas",
}
LACTATE = {  # lactate/acetate, no butyrate (food-grade + Actinobacteria/Bacilli)
    "Lactobacillus", "Lacticaseibacillus", "Lactiplantibacillus", "Limosilactobacillus",
    "Bifidobacterium", "Streptococcus", "Lactococcus", "Pediococcus", "Collinsella",
    "Catenibacterium", "Holdemanella", "Enorma", "Aeriscardovia", "Olsenella", "Dorea", "Blautia",
}
MUCIN = {"Akkermansia": 2, "Ruminococcus": 1, "Bacteroides": 1, "Barnesiella": 1}
BSH = {  # bile salt hydrolase (cholesterol/lipid)
    "Lactobacillus": 2, "Lacticaseibacillus": 2, "Lactiplantibacillus": 2, "Limosilactobacillus": 2,
    "Bifidobacterium": 1, "Enterococcus": 1, "Clostridium": 1, "Bacteroides": 1, "Lactococcus": 1,
}
POLYPHENOL = {"Adlercreutzia", "Slackia", "Gordonibacter", "Asaccharobacter", "Enterorhabdus", "Eggerthella"}
METHANOGEN = {"Methanobrevibacter"}
SULFATE_REDUCER = {"Bilophila", "Desulfovibrio", "Desulfovibrionaceae"}  # H2S, pro-inflammatory
AMINE_PRODUCER = {"Allisonella", "Morganella"}  # histamine/amine, pro-inflammatory


def _annotate(genus: str) -> dict[str, object]:
    butyrate = 2 if genus in BUTYRATE else 0
    propionate = 2 if genus in PROPIONATE else 0
    lactate = 2 if genus in LACTATE else 0
    mucin = MUCIN.get(genus, 0)
    bsh = BSH.get(genus, 0)
    guilds, adverse = [], []
    if butyrate:
        guilds.append("butyrate_producer")
    if propionate:
        guilds.append("propionate_producer")
    if lactate:
        guilds.append("lactate_acetate")
    if mucin:
        guilds.append("mucin_interaction")
    if genus in POLYPHENOL:
        guilds.append("polyphenol_equol_metabolism")
    if genus in METHANOGEN:
        guilds.append("methanogen_h2_sink")
    if genus in SULFATE_REDUCER:
        adverse.append("sulfate_reducer_H2S_proinflammatory")
    if genus in AMINE_PRODUCER:
        adverse.append("amine_histamine_proinflammatory")

    # obesity-relevant mechanism summary
    if butyrate:
        mech = "SCFA/butyrate -> barrier, GLP-1, energy regulation (favorable)"
    elif mucin == 2:
        mech = "mucin-degradation -> propionate, barrier (Akkermansia-type, favorable)"
    elif propionate:
        mech = "propionate -> satiety/lipogenesis modulation (favorable)"
    elif bsh:
        mech = "bile salt hydrolase -> cholesterol/lipid lowering (favorable)"
    elif adverse:
        mech = "PRO-INFLAMMATORY metabolite producer (unfavorable - do not supplement)"
    else:
        mech = "no characterized obesity-relevant SCFA/bile mechanism"
    return {
        "bsh_potential": bsh, "butyrate_scfa_potential": butyrate,
        "propionate_potential": propionate, "mucin_interaction": mucin, "lactate_acetate": lactate,
        "metabolic_guild": "; ".join(guilds) if guilds else "uncharacterized",
        "adverse_mechanism_flag": "; ".join(adverse),
        "obesity_mechanism": mech,
        "functional_provenance": "genus-level comparative-genomics prior (NOT de-novo annotation)",
    }


def main() -> None:
    cat = pd.read_csv(CAT)
    # drop the genus-level columns from the earlier 17-genus merge, re-annotate all 90 genera
    drop = ["bsh_potential", "butyrate_scfa_potential", "mucin_interaction"]
    cat = cat.drop(columns=[c for c in drop if c in cat.columns])
    ann = cat["genus"].astype(str).map(lambda g: _annotate(g)).apply(pd.Series)
    out = pd.concat([cat, ann], axis=1)
    out.to_csv(OUT, index=False)

    # genus reference table
    genera = sorted(cat["genus"].astype(str).unique())
    ref = pd.DataFrame([{**{"genus": g}, **_annotate(g)} for g in genera])
    ref.to_csv(REF, index=False)

    print(f"Functionally annotated {len(out)} entries ({len(genera)} genera) -> {OUT.name}")
    print(f"Genus guild reference -> {REF.name}\n")
    print("metabolic guild coverage (entries):")
    print(out["metabolic_guild"].str.split("; ").explode().value_counts().to_string())
    adverse = out[out["adverse_mechanism_flag"] != ""]
    print(f"\nAdverse-mechanism flagged (exclude from supplementation): {len(adverse)}")
    print(adverse[["species", "adverse_mechanism_flag"]].to_string(index=False))
    print("\nFavorable + actionable (isolate genome, non-adverse, has SCFA/bile mechanism):")
    good = out[(out["assembly_level"].isin(["Complete Genome", "Chromosome"]))
              & (out["adverse_mechanism_flag"] == "")
              & (out["metabolic_guild"] != "uncharacterized")
              & (out["safety_risk_class"] != "elevated_pathogen_or_amr_genus")]
    print(f"  count: {len(good)}")
    print(good[["species", "metabolic_guild", "safety_risk_class"]].head(15).to_string(index=False))


if __name__ == "__main__":
    main()
