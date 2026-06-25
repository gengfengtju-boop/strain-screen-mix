"""Derive combination SAFETY-GATE eligibility for the expanded screening candidates.

The combination recommender excludes any set containing a `fail` strain and only marks a
set `safety_eligible` when every member passes the genome AMR/virulence gate. This maps the
223-entry screening catalog's safety + functional triage onto that gate, defining WHO may
enter a combination. It is independent of the response-RANKING gate (combination_ranking_enabled
stays false until the effect model shows signal): this answers eligibility, not efficacy.

Hard exclusions: adverse-mechanism producers (H2S sulfate reducers, histamine), pathogen/AMR
genera, and MAG-only taxa (no isolate genome to QC). Everything else is eligible only PENDING
genome-level confirmation (QPS gives a lower barrier but still needs strain QC).

    PYTHONPATH=src python scripts/combination_recommendation/safety_gate_eligibility.py
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
CAT = ROOT / "results/candidate_strain_scores/strain_screening_catalog_functional_20260613.csv"
OUT = ROOT / "results/candidate_strain_scores/combination_safety_gate_eligibility_20260613.csv"

ISOLATE = {"Complete Genome", "Chromosome"}


def _cell(value: object) -> str:
    return "" if pd.isna(value) else str(value).strip()


def _eligibility(row: pd.Series) -> dict[str, str]:
    adverse = _cell(row.get("adverse_mechanism_flag"))
    risk = _cell(row.get("safety_risk_class"))
    level = _cell(row.get("assembly_level"))
    if adverse:
        return {"combination_safety_gate": "fail",
                "eligibility": "excluded_adverse_mechanism",
                "gate_reason": f"pro-inflammatory metabolite ({adverse}) - never combine"}
    if risk == "elevated_pathogen_or_amr_genus":
        return {"combination_safety_gate": "fail",
                "eligibility": "excluded_pathogen_or_amr_genus",
                "gate_reason": "genus carries pathogen/AMR risk - exclude unless documented safe strain"}
    if level not in ISOLATE:
        return {"combination_safety_gate": "pending",
                "eligibility": "ineligible_no_isolate_genome",
                "gate_reason": "MAG-only/unresolved - cannot genome-QC; not a product strain"}
    if risk == "low_qps_history":
        return {"combination_safety_gate": "pending",
                "eligibility": "eligible_qps_lower_barrier_pending_genome_qc",
                "gate_reason": "QPS history; strain-level genome QC still required before pass"}
    return {"combination_safety_gate": "pending",
            "eligibility": "eligible_pending_genome_safety_screen",
            "gate_reason": "needs AMRFinder/abricate genome screen before pass"}


def main() -> None:
    cat = pd.read_csv(CAT)
    elig = cat.apply(_eligibility, axis=1, result_type="expand")
    out = pd.concat([cat, elig], axis=1)
    out.to_csv(OUT, index=False)

    print(f"Combination safety-gate eligibility for {len(out)} candidates -> {OUT.name}\n")
    print("eligibility distribution:")
    print(out["eligibility"].value_counts().to_string())

    eligible = out[out["eligibility"].str.startswith("eligible")]
    print(f"\nCombination-eligible pool (isolate genome, non-adverse, non-pathogen): {len(eligible)}")
    print("  of which QPS lower-barrier:",
          int((eligible["eligibility"].str.contains("qps")).sum()))
    print("  by category:", eligible["category"].value_counts().to_dict())
    print("\nHARD-EXCLUDED from any combination (safety):")
    excl = out[out["combination_safety_gate"] == "fail"]
    print(f"  {len(excl)} total — adverse-mechanism + pathogen/AMR genera")
    print("  e.g.", list(excl["species"].head(8)))
    print("\nNote: eligibility != efficacy. combination_ranking_enabled stays FALSE; this only "
          "defines the safety-admissible pool, pending real genome screening (step-2 SOP).")


if __name__ == "__main__":
    main()
