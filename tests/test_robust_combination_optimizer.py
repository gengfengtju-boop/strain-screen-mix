import json

import pandas as pd

from proslim_ai.robust_combination_optimizer import optimize_strain_combinations


def _outcomes() -> pd.DataFrame:
    rows = []
    evidence = {
        "37447365": ["yes", "yes", "yes", "yes"],
        "39051504": ["no", "yes", "yes"],
        "38542727": ["no", "yes", "yes", "yes"],
        "27810310": ["no", "yes", "yes"],
        "39456659": ["yes", "no", "yes"],
        "38999741": ["no", "no", "yes", "no"],
        "40416368": ["no", "no", "yes"],
    }
    endpoint_types = ["adiposity", "adiposity", "metabolic", "microbiome"]
    for pmid, labels in evidence.items():
        for index, label in enumerate(labels):
            rows.append(
                {
                    "evidence_id": f"PMID:{pmid}",
                    "positive_efficacy_label": label,
                    "endpoint_type": endpoint_types[index],
                    "analysis_population": "aggregate_trial",
                    "evidence_modifier": "",
                }
            )
    return pd.DataFrame(rows)


def test_optimizer_is_deterministic_and_preserves_tested_formulations(tmp_path) -> None:
    paths = [
        tmp_path / "outcomes.csv",
        tmp_path / "evidence.csv",
        tmp_path / "combinations.csv",
        tmp_path / "diagnostics.json",
    ]
    _outcomes().to_csv(paths[0], index=False)
    try:
        result = optimize_strain_combinations(
            paths[0], paths[1], paths[2], paths[3], top_n=10, simulations=200
        )
        combinations = pd.read_csv(paths[2])
        diagnostics = json.loads(paths[3].read_text(encoding="utf-8"))

        assert result.formulations_scored == 7
        assert result.combinations_scored > 100
        assert len(combinations) == 10
        assert combinations.iloc[0]["retained_formulations"]
        assert combinations.iloc[0]["prediction_scope"].endswith("not_response_probability")
        assert combinations["top10_probability"].between(0, 1).all()
        assert diagnostics["simulations"] == 200
        evidence = pd.read_csv(paths[1])
        assert evidence["independent_studies"].max() == 1
        assert evidence["evidence_effective_sample_size"].astype(float).max() <= 1.0
    finally:
        for path in paths:
            path.unlink(missing_ok=True)


def test_failed_strain_is_excluded_from_robust_results(tmp_path) -> None:
    paths = [
        tmp_path / "outcomes.csv",
        tmp_path / "evidence.csv",
        tmp_path / "combinations.csv",
        tmp_path / "diagnostics.json",
        tmp_path / "safety.csv",
    ]
    _outcomes().to_csv(paths[0], index=False)
    pd.DataFrame([{"strain_id": "LF_K7", "safety_gate": "fail"}]).to_csv(paths[4], index=False)
    try:
        optimize_strain_combinations(
            paths[0],
            paths[1],
            paths[2],
            paths[3],
            top_n=50,
            simulations=100,
            safety_status_path=paths[4],
        )
        combinations = pd.read_csv(paths[2])
        assert not combinations["source_strain_ids"].str.contains("LF_K7").any()
    finally:
        for path in paths:
            path.unlink(missing_ok=True)


def test_species_level_safety_catalog_maps_to_known_strains(tmp_path) -> None:
    outcomes = tmp_path / "outcomes.csv"
    evidence = tmp_path / "evidence.csv"
    combinations = tmp_path / "combinations.csv"
    diagnostics = tmp_path / "diagnostics.json"
    safety = tmp_path / "safety.csv"
    _outcomes().to_csv(outcomes, index=False)
    pd.DataFrame(
        [{"species": "Lactobacillus_fermentum", "combination_safety_gate": "fail"}]
    ).to_csv(safety, index=False)

    optimize_strain_combinations(
        outcomes,
        evidence,
        combinations,
        diagnostics,
        top_n=50,
        simulations=100,
        safety_status_path=safety,
    )

    result = pd.read_csv(combinations)
    assert not result["source_strain_ids"].str.contains("LF_K7|LF_K8|LF_K11").any()
