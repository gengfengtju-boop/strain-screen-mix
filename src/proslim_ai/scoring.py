from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class StrainScore:
    strain_id: str
    safety_gate: str
    SCFA_functional_fit: float = 0.0
    bile_acid_metabolism_fit: float = 0.0
    carbohydrate_utilization: float = 0.0
    niche_repletion: float = 0.0
    literature_evidence: float = 0.0
    probiotic_use_history: float = 0.0

    @property
    def passes_safety(self) -> bool:
        return self.safety_gate.lower() == "pass"


@dataclass(frozen=True)
class CombinationScore:
    combination_id: str
    strains: tuple[str, ...]
    safety_gate: str
    complementarity_score: float
    microbiome_matching_score: float
    predicted_response_score: float
    literature_evidence_score: float
    validation_feasibility_score: float
    total_score: float


def weighted_sum(values: dict[str, float], weights: dict[str, float]) -> float:
    return sum(float(values.get(name, 0.0)) * float(weight) for name, weight in weights.items())


def score_strain(strain: StrainScore, weights: dict[str, float]) -> float:
    if not strain.passes_safety:
        return 0.0
    return weighted_sum(
        {
            "SCFA_functional_fit": strain.SCFA_functional_fit,
            "bile_acid_metabolism_fit": strain.bile_acid_metabolism_fit,
            "carbohydrate_utilization": strain.carbohydrate_utilization,
            "niche_repletion": strain.niche_repletion,
            "literature_evidence": strain.literature_evidence,
            "probiotic_use_history": strain.probiotic_use_history,
        },
        weights,
    )


def score_combination(
    combination_id: str,
    strains: tuple[str, ...],
    component_scores: dict[str, float],
    weights: dict[str, float],
    safety_passed: bool,
) -> CombinationScore:
    safety_gate = "pass" if safety_passed else "fail"
    total = weighted_sum(component_scores, weights) if safety_passed else 0.0
    return CombinationScore(
        combination_id=combination_id,
        strains=strains,
        safety_gate=safety_gate,
        complementarity_score=component_scores.get("complementarity_score", 0.0),
        microbiome_matching_score=component_scores.get("microbiome_matching_score", 0.0),
        predicted_response_score=component_scores.get("predicted_response_score", 0.0),
        literature_evidence_score=component_scores.get("literature_evidence_score", 0.0),
        validation_feasibility_score=component_scores.get("validation_feasibility_score", 0.0),
        total_score=total,
    )

