from __future__ import annotations

import json
from dataclasses import dataclass
from itertools import combinations
from pathlib import Path

import numpy as np
import pandas as pd

from .formulation_recommendation import FORMULATIONS, _candidate_strains


FORMULATION_EVIDENCE_FIELDS = [
    "formulation_id",
    "formulation_name",
    "evidence_id",
    "outcome_rows",
    "positive_rows",
    "limited_rows",
    "negative_rows",
    "endpoint_coverage",
    "evidence_posterior_mean",
    "evidence_posterior_p10",
    "evidence_posterior_p90",
    "evidence_effective_sample_size",
    "evidence_status",
]

ROBUST_COMBINATION_FIELDS = [
    "robust_rank",
    "combination_id",
    "strains",
    "source_strain_ids",
    "total_strain_count",
    "retained_formulations",
    "partial_formulations",
    "evidence_pmid_list",
    "functional_modules",
    "posterior_score_mean",
    "posterior_score_p10",
    "posterior_score_p90",
    "top10_probability",
    "rank_mean",
    "rank_p90",
    "clinical_evidence_mean",
    "clinical_evidence_p10",
    "module_coverage_score",
    "formulation_integrity_score",
    "evidence_independence_score",
    "genus_diversity_score",
    "split_evidence_penalty",
    "complexity_penalty",
    "safety_gate",
    "prediction_scope",
    "recommended_prebiotic",
    "validation_recommendation",
]

ENDPOINT_WEIGHTS = {"adiposity": 1.0, "metabolic": 0.7, "microbiome": 0.35}
LABEL_VALUES = {"yes": 1.0, "limited": 0.5, "no": 0.0}


@dataclass(frozen=True)
class RobustCombinationOptimizationResult:
    formulation_evidence_output: Path
    combination_output: Path
    diagnostics_output: Path
    formulations_scored: int
    combinations_scored: int
    simulations: int


def optimize_strain_combinations(
    structured_outcomes_path: Path,
    formulation_evidence_output: Path,
    combination_output: Path,
    diagnostics_output: Path,
    min_strains: int = 3,
    max_strains: int = 5,
    top_n: int = 50,
    simulations: int = 2000,
    random_seed: int = 17,
    safety_status_path: Path | None = None,
) -> RobustCombinationOptimizationResult:
    if simulations < 100:
        raise ValueError("Robust optimization requires at least 100 simulations.")
    outcomes = pd.read_csv(structured_outcomes_path)
    rng = np.random.default_rng(random_seed)
    safety_statuses = _load_safety_statuses(safety_status_path)
    evidence_rows, evidence_draws = _score_formulation_evidence(outcomes, simulations, rng)
    candidates = _enumerate_candidates(min_strains, max_strains, safety_statuses)
    scored = _simulate_combination_scores(candidates, evidence_draws, rng)
    rows = _rank_combinations(scored, top_n)

    formulation_evidence_output.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(evidence_rows, columns=FORMULATION_EVIDENCE_FIELDS).to_csv(
        formulation_evidence_output, index=False
    )
    combination_output.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows, columns=ROBUST_COMBINATION_FIELDS).to_csv(combination_output, index=False)

    diagnostics = {
        "model_name": "evidence_constrained_bayesian_robust_combination_optimizer",
        "structured_outcome_rows": int(len(outcomes)),
        "formulations_scored": len(evidence_rows),
        "candidate_combinations_scored": len(candidates),
        "simulations": simulations,
        "random_seed": random_seed,
        "combination_size_range": [min_strains, max_strains],
        "endpoint_weights": ENDPOINT_WEIGHTS,
        "score_weight_center": {
            "clinical_evidence": 0.45,
            "module_coverage": 0.20,
            "formulation_integrity": 0.15,
            "evidence_independence": 0.10,
            "genus_diversity": 0.10,
        },
        "validation": "Monte Carlo sensitivity analysis over evidence posteriors and score weights",
        "prediction_scope": "preclinical formulation validation priority, not individual response probability",
        "safety_policy": "failed strains excluded; pending strains remain hypothesis-only",
        "limitation": (
            "Each formulation is supported by few independent trials. Scores estimate robust validation "
            "priority and must not be interpreted as clinical efficacy probabilities."
        ),
    }
    diagnostics_output.parent.mkdir(parents=True, exist_ok=True)
    diagnostics_output.write_text(json.dumps(diagnostics, indent=2), encoding="utf-8")
    return RobustCombinationOptimizationResult(
        formulation_evidence_output=formulation_evidence_output,
        combination_output=combination_output,
        diagnostics_output=diagnostics_output,
        formulations_scored=len(evidence_rows),
        combinations_scored=len(candidates),
        simulations=simulations,
    )


def _score_formulation_evidence(
    outcomes: pd.DataFrame,
    simulations: int,
    rng: np.random.Generator,
) -> tuple[list[dict[str, object]], dict[str, np.ndarray]]:
    rows: list[dict[str, object]] = []
    draws: dict[str, np.ndarray] = {}
    for formulation in FORMULATIONS:
        evidence_id = f"PMID:{formulation['evidence_pmid']}"
        group = outcomes[outcomes["evidence_id"].astype(str) == evidence_id].copy()
        group = group[group["positive_efficacy_label"].isin(LABEL_VALUES)].copy()
        successes = 0.0
        failures = 0.0
        for _, outcome in group.iterrows():
            label = str(outcome["positive_efficacy_label"])
            value = LABEL_VALUES[label]
            endpoint_weight = ENDPOINT_WEIGHTS.get(str(outcome.get("endpoint_type", "")), 0.5)
            quality = _quality_factor(outcome, formulation)
            weight = endpoint_weight * quality
            successes += weight * value
            failures += weight * (1.0 - value)
        alpha = 1.0 + successes
        beta = 1.0 + failures
        posterior = rng.beta(alpha, beta, size=simulations) * 10.0
        draws[str(formulation["formulation_id"])] = posterior
        labels = group["positive_efficacy_label"].value_counts()
        endpoint_types = sorted(set(group.get("endpoint_type", pd.Series(dtype=str)).astype(str)))
        rows.append(
            {
                "formulation_id": formulation["formulation_id"],
                "formulation_name": formulation["formulation_name"],
                "evidence_id": evidence_id,
                "outcome_rows": int(len(group)),
                "positive_rows": int(labels.get("yes", 0)),
                "limited_rows": int(labels.get("limited", 0)),
                "negative_rows": int(labels.get("no", 0)),
                "endpoint_coverage": "; ".join(endpoint_types),
                "evidence_posterior_mean": f"{float(posterior.mean()):.3f}",
                "evidence_posterior_p10": f"{float(np.quantile(posterior, 0.10)):.3f}",
                "evidence_posterior_p90": f"{float(np.quantile(posterior, 0.90)):.3f}",
                "evidence_effective_sample_size": f"{successes + failures:.3f}",
                "evidence_status": "observed_outcomes" if len(group) else "prior_only_no_matching_outcome",
            }
        )
    return rows, draws


def _quality_factor(outcome: pd.Series, formulation: dict[str, object]) -> float:
    text = " ".join(
        [
            str(outcome.get("analysis_population", "")),
            str(outcome.get("evidence_modifier", "")),
            str(formulation.get("analysis_population", "")),
        ]
    ).lower()
    factor = 1.0
    if "subgroup" in text:
        factor *= 0.55
    if "itt_not_significant" in text:
        factor *= 0.60
    elif "pps" in text or "per_protocol" in text or " pp" in f" {text}":
        factor *= 0.80
    if "within_group" in text:
        factor *= 0.70
    if "abstract_only" in text:
        factor *= 0.65
    if "early_termination" in text or "severe_attrition" in text:
        factor *= 0.50
    return max(factor, 0.20)


def _enumerate_candidates(
    min_strains: int,
    max_strains: int,
    safety_statuses: dict[str, str],
) -> list[dict[str, object]]:
    strains = _candidate_strains(safety_statuses)
    candidates: list[dict[str, object]] = []
    for size in range(min_strains, min(max_strains, len(strains)) + 1):
        for selected in combinations(strains, size):
            if any(strain["safety_gate"] == "fail" for strain in selected):
                continue
            if len({str(strain["genus"]) for strain in selected}) < 2:
                continue
            candidates.append(_candidate_features(selected))
    return candidates


def _candidate_features(selected: tuple[dict[str, object], ...]) -> dict[str, object]:
    selected_ids = {str(strain["strain_id"]) for strain in selected}
    retained: list[str] = []
    partial: list[str] = []
    represented: list[tuple[str, float]] = []
    for formulation in FORMULATIONS:
        member_ids = {member[0] for member in formulation["members"]}
        overlap = selected_ids & member_ids
        if not overlap:
            continue
        fraction = len(overlap) / len(member_ids)
        formulation_id = str(formulation["formulation_id"])
        if member_ids.issubset(selected_ids):
            retained.append(formulation_id)
            represented.append((formulation_id, 1.0))
        else:
            partial.append(formulation_id)
            represented.append((formulation_id, 0.25 * fraction))
    modules = set().union(*(set(strain["modules"]) for strain in selected))
    endpoint_modules = {"body_fat", "visceral_fat", "weight", "BMI", "waist", "lipid", "glucose"}
    mechanism_modules = {
        "SCFA_network",
        "bifidobacterium_niche",
        "barrier",
        "carbohydrate_utilization",
        "fiber_response",
        "cross_feeding",
        "amino_acid_metabolism",
        "microbiome_shift",
    }
    endpoint_coverage = min(len(modules & endpoint_modules) / 5.0, 1.0)
    mechanism_coverage = min(len(modules & mechanism_modules) / 5.0, 1.0)
    module_score = 10.0 * (0.6 * endpoint_coverage + 0.4 * mechanism_coverage)
    integrity = 10.0 * sum(weight for _, weight in represented) / len(represented)
    pmids = sorted({str(strain["evidence_pmid"]) for strain in selected})
    genera = {str(strain["genus"]) for strain in selected}
    return {
        "selected": selected,
        "represented": represented,
        "retained": retained,
        "partial": partial,
        "modules": modules,
        "pmids": pmids,
        "module_score": module_score,
        "integrity_score": integrity,
        "independence_score": 10.0 * min(len(pmids), 3) / 3.0,
        "diversity_score": 10.0 * min(len(genera), 4) / 4.0,
        "split_penalty": min(0.8 * len(partial), 2.4),
        "complexity_penalty": 0.35 * max(len(selected) - 3, 0),
    }


def _simulate_combination_scores(
    candidates: list[dict[str, object]],
    evidence_draws: dict[str, np.ndarray],
    rng: np.random.Generator,
) -> list[dict[str, object]]:
    simulations = len(next(iter(evidence_draws.values())))
    weight_center = np.array([0.45, 0.20, 0.15, 0.10, 0.10])
    weights = rng.dirichlet(weight_center * 80.0, size=simulations)
    score_matrix = np.zeros((len(candidates), simulations), dtype=float)
    clinical_matrix = np.zeros_like(score_matrix)
    for index, candidate in enumerate(candidates):
        represented = candidate["represented"]
        weighted_draws = [evidence_draws[formulation_id] * weight for formulation_id, weight in represented]
        represented_weight = sum(weight for _, weight in represented)
        clinical = np.sum(weighted_draws, axis=0) / represented_weight
        clinical_matrix[index] = clinical
        fixed = np.array(
            [
                candidate["module_score"],
                candidate["integrity_score"],
                candidate["independence_score"],
                candidate["diversity_score"],
            ],
            dtype=float,
        )
        score_matrix[index] = (
            weights[:, 0] * clinical
            + np.sum(weights[:, 1:] * fixed, axis=1)
            - float(candidate["split_penalty"])
            - float(candidate["complexity_penalty"])
        )
    order = np.argsort(-score_matrix, axis=0)
    ranks = np.empty_like(order)
    ranks[order, np.arange(simulations)] = np.arange(1, len(candidates) + 1)[:, None]
    scored: list[dict[str, object]] = []
    for index, candidate in enumerate(candidates):
        scored.append(
            {
                **candidate,
                "scores": score_matrix[index],
                "clinical": clinical_matrix[index],
                "ranks": ranks[index],
            }
        )
    return scored


def _rank_combinations(scored: list[dict[str, object]], top_n: int) -> list[dict[str, object]]:
    scored.sort(
        key=lambda candidate: (
            float(np.mean(candidate["ranks"] <= 10)),
            float(np.quantile(candidate["scores"], 0.10)),
        ),
        reverse=True,
    )
    rows: list[dict[str, object]] = []
    for rank, candidate in enumerate(scored[:top_n], start=1):
        selected = candidate["selected"]
        safety_passed = all(str(strain["safety_gate"]) == "pass" for strain in selected)
        strain_count = len(selected)
        rows.append(
            {
                "robust_rank": rank,
                "combination_id": f"ROBUST_{rank:03d}",
                "strains": "; ".join(str(strain["strain_name"]) for strain in selected),
                "source_strain_ids": "; ".join(str(strain["strain_id"]) for strain in selected),
                "total_strain_count": strain_count,
                "retained_formulations": "; ".join(candidate["retained"]),
                "partial_formulations": "; ".join(candidate["partial"]),
                "evidence_pmid_list": "; ".join(candidate["pmids"]),
                "functional_modules": "; ".join(sorted(candidate["modules"])),
                "posterior_score_mean": f"{float(np.mean(candidate['scores'])):.3f}",
                "posterior_score_p10": f"{float(np.quantile(candidate['scores'], 0.10)):.3f}",
                "posterior_score_p90": f"{float(np.quantile(candidate['scores'], 0.90)):.3f}",
                "top10_probability": f"{float(np.mean(candidate['ranks'] <= 10)):.4f}",
                "rank_mean": f"{float(np.mean(candidate['ranks'])):.2f}",
                "rank_p90": f"{float(np.quantile(candidate['ranks'], 0.90)):.2f}",
                "clinical_evidence_mean": f"{float(np.mean(candidate['clinical'])):.3f}",
                "clinical_evidence_p10": f"{float(np.quantile(candidate['clinical'], 0.10)):.3f}",
                "module_coverage_score": f"{float(candidate['module_score']):.3f}",
                "formulation_integrity_score": f"{float(candidate['integrity_score']):.3f}",
                "evidence_independence_score": f"{float(candidate['independence_score']):.3f}",
                "genus_diversity_score": f"{float(candidate['diversity_score']):.3f}",
                "split_evidence_penalty": f"{float(candidate['split_penalty']):.3f}",
                "complexity_penalty": f"{float(candidate['complexity_penalty']):.3f}",
                "safety_gate": "pass" if safety_passed else "pending_genome_safety_gate",
                "prediction_scope": "preclinical_validation_priority_not_response_probability",
                "recommended_prebiotic": "; ".join(
                    sorted({str(strain["prebiotic"]) for strain in selected})
                ),
                "validation_recommendation": _validation_recommendation(
                    rank, strain_count, safety_passed
                ),
            }
        )
    return rows


def _validation_recommendation(rank: int, strain_count: int, safety_passed: bool) -> str:
    if not safety_passed:
        return "complete strain-resolved genome AMR/virulence/MGE screening before validation"
    if rank <= 3:
        return f"priority tier 1: test intact {strain_count}-strain combination and component controls"
    if rank <= 10:
        return "priority tier 2: in-vitro compatibility and dose-response screening"
    return "reserve candidate for sensitivity panel"


def _load_safety_statuses(path: Path | None) -> dict[str, str]:
    if path is None:
        return {}
    table = pd.read_csv(path)
    statuses: dict[str, str] = {}
    for _, row in table.iterrows():
        strain_id = str(row.get("strain_id", "")).strip()
        status = str(row.get("safety_gate", "")).strip().lower()
        if strain_id and status in {"pass", "fail", "pending"}:
            statuses[strain_id] = status
    return statuses
