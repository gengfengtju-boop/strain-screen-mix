"""Genome safety-gate triage (AMR / virulence / MGE) for the synergistic
fat-loss combination candidates.

IMPORTANT — honest scope: this environment cannot run real genome screening
(AMRFinderPlus / abricate-CARD-VFDB / ResFinder need the genome FASTAs + the
bioinformatics toolchain). This produces:
  (1) a TAXONOMY/QPS knowledge-prior risk class (reusing the project triage),
  (2) NCBI genome AVAILABILITY (so the real screen can be run later), and
  (3) genus-level MGE / mobile-AMR knowledge flags.
It is a triage that decides WHICH strains to screen first and flags known
concerns; it does NOT replace strain-level genome AMR/virulence/MGE screening.
"""
from __future__ import annotations

import json
import time
import urllib.parse
import urllib.request
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
PR = ROOT / "results/prediction_results"
OUT = ROOT / "results/candidate_strain_scores"

QPS_GENERA = {"Lactobacillus", "Lacticaseibacillus", "Lactiplantibacillus", "Limosilactobacillus",
              "Bifidobacterium", "Lactococcus", "Leuconostoc", "Pediococcus", "Propionibacterium"}
ELEVATED_GENERA = {"Escherichia", "Klebsiella", "Enterococcus", "Staphylococcus", "Streptococcus",
                   "Veillonella", "Bilophila", "Clostridioides", "Fusobacterium"}
ELEVATED_SPECIES = {"Bacteroides_fragilis", "Eggerthella_lenta", "Ruminococcus_gnavus"}
LBP_PRECEDENT = {"Akkermansia_muciniphila", "Faecalibacterium_prausnitzii", "Anaerobutyricum_hallii",
                 "Roseburia_intestinalis", "Parabacteroides_distasonis", "Odoribacter_splanchnicus"}
AMBIGUOUS_GENERA = {"Clostridium"}
# genus-level mobile-element / horizontal AMR knowledge priors
MGE_PRIOR = {
    "Bacteroides": ("elevated", "Bacteroidetes 携带可移动 tetQ/ermF/cfxA、CTn 接合转座子 → MGE/AMR 必查"),
    "Parabacteroides": ("elevated", "拟杆菌门 MGE/可移动 AMR 风险，需查"),
    "Clostridium": ("moderate", "梭菌属部分携带毒素/可移动元件，species 级核查"),
    "Akkermansia": ("low", "MGE 负载低，LBP 前例"),
}


def triage(species: str, genus: str):
    flags = []
    if genus in AMBIGUOUS_GENERA:
        flags.append("genus_contains_pathogens_species_level_care")
    if species in ELEVATED_SPECIES:
        flags.append("species_opportunist_concern")
    if species in QPS_GENERA or genus in QPS_GENERA:
        risk, action = "low_qps_history", "lower_barrier; strain-level genome QC still recommended"
    elif species in ELEVATED_SPECIES or genus in ELEVATED_GENERA:
        risk, action = "elevated_pathogen_or_amr_genus", "strain-level review MANDATORY; exclude unless documented safe strain"
    elif species in LBP_PRECEDENT:
        risk, action = "moderate_lbp_precedent", "human-trial precedent; requires genome AMR/virulence confirmation"
    else:
        risk, action = "moderate_novel_commensal", "novel human commensal; genome-level AMR/virulence screening required"
    mge_level, mge_note = MGE_PRIOR.get(genus, ("unknown", "MGE 负载未知，需基因组核查"))
    flags.append(f"mge_{mge_level}")
    return risk, action, "; ".join(flags), mge_level, mge_note


def genome_avail(species: str):
    def get(url, m=40):
        return urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "proslim-ai/1.0"}), timeout=m).read().decode("utf-8", "replace")
    try:
        term = urllib.parse.quote(f'"{species}"[Organism] AND latest[filter]')
        j = json.loads(get(f"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi?db=assembly&term={term}&retmax=50&retmode=json"))
        ids = j.get("esearchresult", {}).get("idlist", [])
        if not ids:
            return 0, "", "none"
        js = json.loads(get(f"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi?db=assembly&id={','.join(ids[:25])}&retmode=json"))
        res = js.get("result", {})
        rank = {"Complete Genome": 3, "Chromosome": 2, "Scaffold": 1, "Contig": 0}
        best_acc, best_lvl, bn = "", "none", -1
        for i in ids[:25]:
            r = res.get(i, {})
            lvl = r.get("assemblystatus") or r.get("AssemblyStatus") or ""
            acc = r.get("assemblyaccession") or r.get("AssemblyAccession") or ""
            if rank.get(lvl, -1) > bn:
                bn, best_acc, best_lvl = rank.get(lvl, -1), acc, lvl
        return len(ids), best_acc, best_lvl
    except Exception:
        return -1, "", "lookup_failed"


def gate(risk, n_assemblies, cult_mag):
    if cult_mag:
        return "blocked_no_isolate_genome"
    if risk == "elevated_pathogen_or_amr_genus":
        return "flagged_exclude_or_documented_safe_strain_only"
    if n_assemblies and n_assemblies > 0:
        return "eligible_pending_real_genome_screen"
    return "needs_genome_then_screen"


def main() -> None:
    pool = pd.read_csv(PR / "synergistic_combination_pool_20260625.csv")
    rows = []
    for r in pool.itertuples():
        sp, genus = r.species, r.genus
        risk, action, flags, mge_level, mge_note = triage(sp, genus)
        cult_mag = "MAG" in str(r.culturability_class) or "uncultured" in str(r.culturability_class)
        n, acc, lvl = genome_avail(sp.replace("_", " "))
        time.sleep(0.34)
        rows.append({
            "species": sp, "genus": genus,
            "safety_risk_class": risk, "mge_amr_prior": mge_level, "mge_note": mge_note,
            "safety_flags": flags, "recommended_action": action,
            "ncbi_assemblies": n, "best_assembly": acc, "best_assembly_level": lvl,
            "real_screen_runnable": (n is not None and n > 0 and not cult_mag),
            "safety_gate": gate(risk, n, cult_mag),
        })
    out = pd.DataFrame(rows).sort_values(["safety_gate", "safety_risk_class"])
    out.to_csv(OUT / "synergistic_candidates_safety_gate_20260625.csv", index=False)

    print(f"safety-gated {len(out)} synergistic-pool strains (knowledge prior + genome availability)\n")
    for r in out.itertuples():
        print(f"  {r.species[:30]:30} {r.safety_risk_class:28} MGE:{r.mge_amr_prior:8} "
              f"assemblies={r.ncbi_assemblies:>4} -> {r.safety_gate}")
    print("\ngate distribution:", out["safety_gate"].value_counts().to_dict())
    print("wrote", (OUT / "synergistic_candidates_safety_gate_20260625.csv").relative_to(ROOT))


if __name__ == "__main__":
    main()
