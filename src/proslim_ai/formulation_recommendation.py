from __future__ import annotations

import csv
from dataclasses import dataclass
from itertools import combinations
from pathlib import Path


STRAIN_FIELDS = [
    "strain_id",
    "formulation_id",
    "genus",
    "species",
    "strain_name",
    "evidence_pmid",
    "evidence_unit",
    "inherited_from_combination",
    "confirmed_outcome_score",
    "functional_modules",
    "suggested_prebiotic",
    "safety_gate",
    "notes",
]

FORMULATION_FIELDS = [
    "formulation_id",
    "formulation_name",
    "member_strain_ids",
    "member_strain_names",
    "strain_count",
    "evidence_pmid",
    "analysis_population",
    "evidence_scope",
    "clinical_evidence_score",
    "functional_modules",
    "recommended_prebiotic",
    "can_split_members",
    "notes",
]

COMBINATION_FIELDS = [
    "combination_id",
    "formulation_blocks",
    "strains",
    "total_strain_count",
    "target_population",
    "source_strain_ids",
    "evidence_summary",
    "evidence_doi_list",
    "evidence_pmid_list",
    "safety_gate",
    "functional_modules",
    "clinical_evidence_score",
    "combination_design_score",
    "synergy_score",
    "split_evidence_penalty",
    "original_formulation_recovery_score",
    "complementarity_score",
    "microbiome_matching_score",
    "predicted_response_score",
    "literature_evidence_score",
    "validation_priority",
    "recommended_prebiotic",
    "notes",
]


@dataclass(frozen=True)
class FormulationRecommendationResult:
    strain_output: Path
    formulation_output: Path
    combination_output: Path
    strains_written: int
    formulations_written: int
    combinations_written: int


FORMULATIONS = [
    {
        "formulation_id": "FORM_LF_K7_K8_K11",
        "formulation_name": "Lactobacillus fermentum K7/K8/K11",
        "members": [
            ("LF_K7", "Lactobacillus", "fermentum", "Lactobacillus fermentum K7"),
            ("LF_K8", "Lactobacillus", "fermentum", "Lactobacillus fermentum K8"),
            ("LF_K11", "Lactobacillus", "fermentum", "Lactobacillus fermentum K11"),
        ],
        "evidence_pmid": "37447365",
        "analysis_population": "FAS",
        "evidence_scope": "fixed_3_strain_formulation",
        "clinical_evidence_score": 10.0,
        "modules": {"body_fat", "weight", "BMI", "waist", "carbohydrate_utilization", "SCFA_network"},
        "prebiotic": "acacia gum optional; probiotic arm strongest without synbiotic advantage",
        "can_split_members": "yes_with_evidence_discount",
        "notes": "Members can be recombined, but the strongest clinical signal belongs to the tested K7/K8/K11 formulation.",
    },
    {
        "formulation_id": "FORM_IDCC4301",
        "formulation_name": "Bifidobacterium lactis IDCC 4301",
        "members": [
            ("BL_IDCC4301", "Bifidobacterium", "animalis subsp. lactis", "Bifidobacterium lactis IDCC 4301"),
        ],
        "evidence_pmid": "39051504",
        "analysis_population": "full_trial",
        "evidence_scope": "single_strain",
        "clinical_evidence_score": 5.12,
        "modules": {"body_fat", "lipid", "bifidobacterium_niche", "SCFA_network"},
        "prebiotic": "inulin/FOS optional",
        "can_split_members": "yes",
        "notes": "Single-strain clinical evidence; BMI between-group change was not significant.",
    },
    {
        "formulation_id": "FORM_BB536_MCC1274",
        "formulation_name": "Bifidobacterium longum BB536 + Bifidobacterium breve MCC1274",
        "members": [
            ("BL_BB536", "Bifidobacterium", "longum", "Bifidobacterium longum BB536"),
            ("BB_MCC1274", "Bifidobacterium", "breve", "Bifidobacterium breve MCC1274"),
        ],
        "evidence_pmid": "38542727",
        "analysis_population": "PPS",
        "evidence_scope": "fixed_2_strain_formulation",
        "clinical_evidence_score": 4.51,
        "modules": {"visceral_fat", "lipid", "bifidobacterium_niche", "barrier"},
        "prebiotic": "inulin/FOS optional",
        "can_split_members": "yes_with_evidence_discount",
        "notes": "Members can be recombined; full clinical support applies only when BB536 and MCC1274 are retained together.",
    },
    {
        "formulation_id": "FORM_B420_LU",
        "formulation_name": "Bifidobacterium animalis subsp. lactis B420 + polydextrose",
        "members": [
            ("BL_B420", "Bifidobacterium", "animalis subsp. lactis", "Bifidobacterium animalis subsp. lactis B420"),
        ],
        "evidence_pmid": "27810310",
        "analysis_population": "PP_positive_ITT_not_significant",
        "evidence_scope": "single_strain_with_required_fiber_context",
        "clinical_evidence_score": 3.20,
        "modules": {"body_fat", "waist", "barrier", "SCFA_network", "fiber_response"},
        "prebiotic": "polydextrose/Litesse Ultra",
        "can_split_members": "yes",
        "notes": "PP signal; ITT body-fat difference not significant. Treat fiber context as required for strongest evidence.",
    },
    {
        "formulation_id": "FORM_BBR60",
        "formulation_name": "Bifidobacterium breve BBr60",
        "members": [
            ("BB_BBr60", "Bifidobacterium", "breve", "Bifidobacterium breve BBr60"),
        ],
        "evidence_pmid": "39456659",
        "analysis_population": "full_trial",
        "evidence_scope": "single_strain",
        "clinical_evidence_score": 3.88,
        "modules": {"weight", "glucose", "bifidobacterium_niche", "amino_acid_metabolism"},
        "prebiotic": "inulin/FOS optional",
        "can_split_members": "yes",
        "notes": "Weight signal; BMI between-group change not significant.",
    },
    {
        "formulation_id": "FORM_BN202M",
        "formulation_name": "Lacticaseibacillus paracasei BEPC22 + Lactiplantibacillus plantarum BELP53",
        "members": [
            ("LP_BEPC22", "Lacticaseibacillus", "paracasei", "Lacticaseibacillus paracasei BEPC22"),
            ("LPL_BELP53", "Lactiplantibacillus", "plantarum", "Lactiplantibacillus plantarum BELP53"),
        ],
        "evidence_pmid": "38999741",
        "analysis_population": "PP",
        "evidence_scope": "fixed_2_strain_formulation",
        "clinical_evidence_score": 3.65,
        "modules": {"body_fat", "lipid_metabolism", "cross_feeding", "carbohydrate_utilization"},
        "prebiotic": "FOS/GOS optional",
        "can_split_members": "yes_with_evidence_discount",
        "notes": "Members can be recombined; full clinical support applies only when BEPC22 and BELP53 are retained together.",
    },
    {
        "formulation_id": "FORM_BC99",
        "formulation_name": "Bacillus coagulans BC99",
        "members": [
            ("BC_BC99", "Bacillus", "coagulans", "Bacillus coagulans BC99"),
        ],
        "evidence_pmid": "40416368",
        "analysis_population": "subgroup_overweight_signal",
        "evidence_scope": "single_strain_subgroup",
        "clinical_evidence_score": 1.50,
        "modules": {"weight_subgroup", "microbiome_shift", "spore_former"},
        "prebiotic": "none specified",
        "can_split_members": "yes",
        "notes": "Use only as exploratory/subgroup candidate; lipid endpoint not significant.",
    },
]


def build_formulation_recommendations(
    strain_output: Path,
    formulation_output: Path,
    combination_output: Path,
    min_strains: int = 3,
    max_strains: int = 5,
    top_n: int = 50,
) -> FormulationRecommendationResult:
    strains = _build_strain_rows()
    formulations = _build_formulation_rows()
    combinations_rows = _build_combination_rows(min_strains=min_strains, max_strains=max_strains, top_n=top_n)

    _write_rows(strain_output, STRAIN_FIELDS, strains)
    _write_rows(formulation_output, FORMULATION_FIELDS, formulations)
    _write_rows(combination_output, COMBINATION_FIELDS, combinations_rows)
    return FormulationRecommendationResult(
        strain_output=strain_output,
        formulation_output=formulation_output,
        combination_output=combination_output,
        strains_written=len(strains),
        formulations_written=len(formulations),
        combinations_written=len(combinations_rows),
    )


def _build_strain_rows() -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for formulation in FORMULATIONS:
        inherited = "yes" if len(formulation["members"]) > 1 else "no"
        inherited_score = _member_evidence_score(formulation)
        for strain_id, genus, species, strain_name in formulation["members"]:
            rows.append(
                {
                    "strain_id": strain_id,
                    "formulation_id": formulation["formulation_id"],
                    "genus": genus,
                    "species": species,
                    "strain_name": strain_name,
                    "evidence_pmid": formulation["evidence_pmid"],
                    "evidence_unit": formulation["evidence_scope"],
                    "inherited_from_combination": inherited,
                    "confirmed_outcome_score": f"{inherited_score:.2f}",
                    "functional_modules": "; ".join(sorted(formulation["modules"])),
                    "suggested_prebiotic": formulation["prebiotic"],
                    "safety_gate": "literature_use_only_pending_genome_safety",
                    "notes": formulation["notes"],
                }
            )
    return rows


def _build_formulation_rows() -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for formulation in FORMULATIONS:
        rows.append(
            {
                "formulation_id": formulation["formulation_id"],
                "formulation_name": formulation["formulation_name"],
                "member_strain_ids": "; ".join(member[0] for member in formulation["members"]),
                "member_strain_names": "; ".join(member[3] for member in formulation["members"]),
                "strain_count": str(len(formulation["members"])),
                "evidence_pmid": formulation["evidence_pmid"],
                "analysis_population": formulation["analysis_population"],
                "evidence_scope": formulation["evidence_scope"],
                "clinical_evidence_score": f"{float(formulation['clinical_evidence_score']):.2f}",
                "functional_modules": "; ".join(sorted(formulation["modules"])),
                "recommended_prebiotic": formulation["prebiotic"],
                "can_split_members": formulation["can_split_members"],
                "notes": formulation["notes"],
            }
        )
    return rows


def _build_combination_rows(min_strains: int, max_strains: int, top_n: int) -> list[dict[str, str]]:
    strains = _candidate_strains()
    rows: list[dict[str, str]] = []
    for size in range(min_strains, min(max_strains, len(strains)) + 1):
        for strain_set in combinations(strains, size):
            if len({strain["genus"] for strain in strain_set}) < 2:
                continue
            row = _score_strains(strain_set, len(rows) + 1)
            rows.append(row)
    rows.sort(key=lambda row: float(row["validation_priority"]), reverse=True)
    for index, row in enumerate(rows[:top_n], start=1):
        row["combination_id"] = f"FMB3TO5_{index:03d}"
    return rows[:top_n]


def _score_strains(strains: tuple[dict, ...], index: int) -> dict[str, str]:
    modules = set().union(*(strain["modules"] for strain in strains))
    strain_ids = [str(strain["strain_id"]) for strain in strains]
    strain_names = [str(strain["strain_name"]) for strain in strains]
    formulation_ids = sorted(set(str(strain["formulation_id"]) for strain in strains))
    pmids = sorted(set(str(strain["evidence_pmid"]) for strain in strains))
    strain_count = len(strain_ids)
    clinical = _clinical_score(strains)
    complementarity = _complementarity_score(modules, strains)
    synergy = _synergy_score(modules, strains)
    recovery = _original_formulation_recovery_score(strains)
    split_penalty = _split_evidence_penalty(strains)
    genera = {str(strain["genus"]) for strain in strains}
    microbiome_match = min(7.0 + len(genera) + ("bifidobacterium_niche" in modules) + ("body_fat" in modules), 10.0)
    pp_penalty = sum(0.2 for strain in strains if "ITT_not_significant" in str(strain["analysis_population"]))
    combination_design = max(
        0.0,
        0.35 * complementarity
        + 0.30 * synergy
        + 0.20 * microbiome_match
        + 0.15 * recovery
        - split_penalty
        - pp_penalty,
    )
    validation_priority = 0.45 * clinical + 0.55 * combination_design
    return {
        "combination_id": f"FMB3TO5_{index:03d}",
        "formulation_blocks": "; ".join(formulation_ids),
        "strains": "; ".join(strain_names),
        "total_strain_count": str(strain_count),
        "target_population": _target_population(modules),
        "source_strain_ids": "; ".join(strain_ids),
        "evidence_summary": f"{strain_count}-strain recombined candidate; combination evidence is discounted unless original tested companions are retained; PMIDs {'; '.join(pmids)}",
        "evidence_doi_list": "",
        "evidence_pmid_list": "; ".join(pmids),
        "safety_gate": "pending_genome_safety_gate",
        "functional_modules": "; ".join(sorted(modules)),
        "clinical_evidence_score": f"{clinical:.2f}",
        "combination_design_score": f"{combination_design:.2f}",
        "synergy_score": f"{synergy:.2f}",
        "split_evidence_penalty": f"{split_penalty:.2f}",
        "original_formulation_recovery_score": f"{recovery:.2f}",
        "complementarity_score": f"{complementarity:.2f}",
        "microbiome_matching_score": f"{microbiome_match:.2f}",
        "predicted_response_score": f"{microbiome_match:.2f}",
        "literature_evidence_score": f"{clinical:.2f}",
        "validation_priority": f"{validation_priority:.2f}",
        "recommended_prebiotic": "; ".join(sorted(set(str(strain["prebiotic"]) for strain in strains))),
        "notes": "Recombination allowed: split members carry discounted evidence; synergy favors complementary functions, cross-feeding, fiber response, and retained tested companions. Genome AMR/virulence/MGE safety gate still required.",
    }


def _candidate_strains() -> list[dict[str, object]]:
    strains: list[dict[str, object]] = []
    for formulation in FORMULATIONS:
        for strain_id, genus, species, strain_name in formulation["members"]:
            strains.append(
                {
                    "strain_id": strain_id,
                    "genus": genus,
                    "species": species,
                    "strain_name": strain_name,
                    "formulation_id": formulation["formulation_id"],
                    "formulation_members": {member[0] for member in formulation["members"]},
                    "evidence_pmid": formulation["evidence_pmid"],
                    "analysis_population": formulation["analysis_population"],
                    "evidence_scope": formulation["evidence_scope"],
                    "clinical_evidence_score": _member_evidence_score(formulation),
                    "modules": set(formulation["modules"]),
                    "prebiotic": formulation["prebiotic"],
                }
            )
    return strains


def _member_evidence_score(formulation: dict) -> float:
    score = float(formulation["clinical_evidence_score"])
    members = len(formulation["members"])
    if members == 1:
        return score
    return (score / members) * 0.65


def _clinical_score(strains: tuple[dict, ...]) -> float:
    member_scores = [float(strain["clinical_evidence_score"]) for strain in strains]
    retained_scores = _retained_formulation_scores(strains)
    base = sum(member_scores) / len(member_scores)
    retained_bonus = 0.0
    selected = {str(strain["strain_id"]) for strain in strains}
    for formulation, retained_score in retained_scores:
        retained_members = {member[0] for member in formulation["members"]}
        retained_fraction = len(retained_members) / len(selected)
        retained_bonus += retained_score * retained_fraction * 0.45
    return min(base + retained_bonus, 10.0)


def _retained_formulation_scores(strains: tuple[dict, ...]) -> list[tuple[dict, float]]:
    selected = {str(strain["strain_id"]) for strain in strains}
    retained: list[tuple[dict, float]] = []
    for formulation in FORMULATIONS:
        member_ids = {member[0] for member in formulation["members"]}
        if len(member_ids) > 1 and member_ids.issubset(selected):
            retained.append((formulation, float(formulation["clinical_evidence_score"])))
    return retained


def _split_evidence_penalty(strains: tuple[dict, ...]) -> float:
    selected = {str(strain["strain_id"]) for strain in strains}
    penalty = 0.0
    for formulation in FORMULATIONS:
        member_ids = {member[0] for member in formulation["members"]}
        if len(member_ids) < 2:
            continue
        selected_members = member_ids & selected
        if selected_members and not member_ids.issubset(selected):
            penalty += 0.45
    return min(penalty, 2.0)


def _original_formulation_recovery_score(strains: tuple[dict, ...]) -> float:
    retained_count = len(_retained_formulation_scores(strains))
    return min(5.0 + retained_count * 2.5, 10.0)


def _complementarity_score(modules: set[str], strains: tuple[dict, ...]) -> float:
    genera = {str(strain["genus"]) for strain in strains}
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
    module_balance = min(len(modules & endpoint_modules), 3) + min(len(modules & mechanism_modules), 5)
    genus_bonus = min(len(genera), 4) * 0.5
    return min(module_balance + genus_bonus, 10.0)


def _synergy_score(modules: set[str], strains: tuple[dict, ...]) -> float:
    score = 4.0
    if "bifidobacterium_niche" in modules and ("carbohydrate_utilization" in modules or "fiber_response" in modules):
        score += 1.8
    if "SCFA_network" in modules and ("cross_feeding" in modules or "barrier" in modules):
        score += 1.5
    if "lipid" in modules and ("SCFA_network" in modules or "bifidobacterium_niche" in modules):
        score += 1.0
    if "glucose" in modules and ("amino_acid_metabolism" in modules or "SCFA_network" in modules):
        score += 0.8
    score += 0.7 * len(_retained_formulation_scores(strains))
    return min(score, 10.0)


def _target_population(modules: set[str]) -> str:
    targets = ["overweight/obesity"]
    if "visceral_fat" in modules:
        targets.append("visceral fat accumulation")
    if "lipid" in modules or "lipid_metabolism" in modules:
        targets.append("lipid-risk subgroup")
    if "glucose" in modules:
        targets.append("glucose-risk subgroup")
    return "; ".join(targets)


def _write_rows(path: Path, fields: list[str], rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
