from __future__ import annotations

from pathlib import Path

import pandas as pd

from proslim_ai.arm_effects import (
    _dersimonian_laird,
    _canonical_unit,
    _canonical_trial_ids,
    _leave_one_out_meta_influence,
    _layered_evidence_sensitivity,
    _microbial_comparison_mask,
    _primary_study_title_mask,
    _missing_variance_sensitivity,
    _meta_regression_moderator,
    _paule_mandel_hartung_knapp,
    _effects_from_structured,
    _fit_strata,
    _add_interpretable_intervention_features,
    _intervention_class,
    _microbial_mask,
    _two_arm_endpoint_difference,
    build_arm_level_dataset,
    build_continuous_effects,
    mine_abstract_effects,
    train_continuous_effect_models,
)


def test_dersimonian_laird_pooled_effect_and_heterogeneity() -> None:
    import numpy as np

    # three concordant negative effects with small SE -> pooled CI should exclude zero
    res = _dersimonian_laird(np.array([-2.0, -2.5, -1.8]), np.array([0.25, 0.25, 0.25]))
    assert res["k_studies"] == 3
    assert res["pooled_effect"] < 0
    assert res["ci_excludes_zero"] is True
    assert 0.0 <= res["i2_percent"] <= 100.0
    # widely discordant effects -> heterogeneity high, pooled CI should include zero
    res2 = _dersimonian_laird(np.array([-5.0, 5.0, -4.0, 4.0]), np.array([0.25, 0.25, 0.25, 0.25]))
    assert res2["i2_percent"] > 50.0
    assert res2["ci_excludes_zero"] is False


def test_paule_mandel_hksj_is_more_cautious_for_small_k() -> None:
    import numpy as np

    effects = np.array([-0.7, -0.5, -0.4, -0.2])
    variances = np.array([0.04, 0.05, 0.03, 0.06])
    robust = _paule_mandel_hartung_knapp(effects, variances)
    dl = _dersimonian_laird(effects, variances)
    assert robust["pooled_effect"] < 0
    assert robust["tau2_method"] == "Paule-Mandel"
    assert robust["interval_method"].startswith("modified Hartung-Knapp")
    robust_width = robust["ci95_high"] - robust["ci95_low"]
    dl_width = dl["ci95_high"] - dl["ci95_low"]
    assert robust_width >= dl_width


def test_paule_mandel_hksj_rejects_invalid_variances() -> None:
    import numpy as np
    import pytest

    with pytest.raises(ValueError, match="positive variances"):
        _paule_mandel_hartung_knapp(np.array([-1.0, -2.0]), np.array([0.1, 0.0]))


def test_missing_variance_sensitivity_keeps_imputation_explicit() -> None:
    import numpy as np

    result = _missing_variance_sensitivity(
        np.array([-1.0, -0.8, -0.5, -0.2, 0.1]),
        np.array([0.10, 0.15, np.nan, np.nan, np.nan]),
        bootstrap_iterations=500,
    )
    assert result["observed_variance_studies"] == 2
    assert result["missing_variance_studies"] == 3
    assert result["imputation_is_sensitivity_only"] is True
    assert "observed_variance_only" in result["variance_scenarios"]
    assert "impute_stratum_upper_quartile_variance" in result["variance_scenarios"]
    assert result["nonparametric_sensitivity"]["median_effect"] < 0


def test_missing_variance_sensitivity_flags_weak_variance_basis() -> None:
    import numpy as np

    result = _missing_variance_sensitivity(
        np.array([-1.0, -0.5, 0.2]),
        np.array([0.1, np.nan, np.nan]),
        bootstrap_iterations=500,
    )
    assert result["evidence_state"] == "sensitivity_only_insufficient_observed_variances"


def test_mixed_percent_and_kg_unit_does_not_enter_kg_stratum() -> None:
    assert _canonical_unit("percentage-point and kg fat mass change") == "mixed"
    assert _canonical_unit("relative body fat mass change; kg difference") == "mixed"
    assert _canonical_unit("kg total fat mass change") == "kg"


def test_leave_one_out_meta_influence_identifies_extreme_study() -> None:
    import numpy as np

    result = _leave_one_out_meta_influence(
        np.array([-0.5, -0.6, -0.4, 2.0]),
        np.array([0.1, 0.1, 0.1, 0.1]),
        ["A", "B", "C", "extreme"],
    )
    assert result["most_influential_study"] == "extreme"
    assert result["maximum_absolute_pooled_shift"] > 0
    assert len(result["leave_one_out"]) == 4


def test_canonical_trial_ids_merge_database_aliases_and_matching_titles() -> None:
    data = pd.DataFrame(
        {
            "study_id": [
                "EUROPEPMC:41512635",
                "PMID:41512635",
                "PMID:32615727",
                "DOI:10.3803/EnM.2020.35.2.425",
                "NCT:1",
                "PMID:9",
            ],
            "source_title": [
                "A sufficiently specific randomized probiotic trial title in adults",
                "A sufficiently specific randomized probiotic trial title in adults",
                "Effect of Lactobacillus sakei on body fat",
                "Effect of Lactobacillus sakei on body fat",
                "Another sufficiently specific synbiotic randomized trial title",
                "Another sufficiently specific synbiotic randomized trial title",
            ],
        }
    )
    ids = _canonical_trial_ids(data).tolist()
    assert ids[0] == ids[1] == "PMID:41512635"
    assert ids[2] == ids[3] == "DOI:10.3803/EnM.2020.35.2.425"
    assert ids[4] == ids[5] == "PMID:9"


def test_microbial_comparison_mask_rejects_nonmicrobial_contrast() -> None:
    data = pd.DataFrame(
        {
            "comparison": [
                "whey_vs_control_change",
                "energy_restriction_plus_exercise_vs_usual_lifestyle",
                "probiotic_plus_energy_restriction_vs_energy_restriction_control",
                "probiotic_vs_placebo",
                "",
            ]
        }
    )
    assert _microbial_comparison_mask(data).tolist() == [False, False, True, True, True]


def test_primary_study_title_mask_excludes_reviews() -> None:
    data = pd.DataFrame(
        {
            "source_title": [
                "A randomized controlled probiotic trial",
                "A systematic review and meta-analysis of probiotic trials",
                "",
            ]
        }
    )
    assert _primary_study_title_mask(data).tolist() == [True, False, True]


def test_layered_evidence_sensitivity_detects_direction_change() -> None:
    import numpy as np

    result = _layered_evidence_sensitivity(
        estimates=np.array([-1.0, -0.8, 0.6, 0.7]),
        variances=np.array([0.1, 0.1, 0.1, 0.1]),
        cointervention=np.array([False, False, True, True]),
        stronger_precision=np.array([False, False, True, True]),
        bootstrap_iterations=500,
    )
    assert result["conclusion"] == "direction_changes_across_evidence_layers"
    assert result["layers"]["exclude_flagged_cointerventions"][
        "nonparametric_sensitivity"
    ]["median_effect"] < 0
    assert result["layers"]["stronger_precision_only"][
        "nonparametric_sensitivity"
    ]["median_effect"] > 0


def test_layered_evidence_sensitivity_flags_subset_only_interval_support() -> None:
    import numpy as np

    result = _layered_evidence_sensitivity(
        estimates=np.array([-3.0, -2.0, -1.0, 2.0, 3.0]),
        variances=np.array([0.1, 0.1, 0.1, np.nan, np.nan]),
        cointervention=np.array([False, False, False, False, False]),
        stronger_precision=np.array([True, True, True, False, False]),
        bootstrap_iterations=500,
    )
    assert result["conclusion"] == "interval_support_is_subset_dependent"
    assert result["layers_with_interval_support"] >= 1


def test_meta_regression_moderator_absorbs_grouped_heterogeneity() -> None:
    import numpy as np

    # two groups (moderator 0 vs 1) with different effect levels -> moderator absorbs it
    y = np.array([-1.0, -1.2, -3.0, -3.2])
    v = np.array([0.1, 0.1, 0.1, 0.1])
    mod = np.array([0.0, 0.0, 1.0, 1.0])
    res = _meta_regression_moderator(y, v, mod)
    assert res["moderator_varies"] is True
    assert abs(res["moderator_slope"] - (-2.0)) < 0.5  # ~ -2 level shift
    assert res["residual_i2_percent"] < 50.0


def test_endpoint_effect_difference_recomputed_from_source(tmp_path) -> None:
    # a corrupted curated effect_difference (-69.51) on an 'endpoint' row must be
    # overridden by the between-arm endpoint difference parsed from the source.
    assert _two_arm_endpoint_difference("BC99 80.39 +/- 12.74 vs placebo 78.51 +/- 10.89") == 80.39 - 78.51
    path = tmp_path / "clinical_outcome.structured_effects.csv"
    pd.DataFrame(
        [{
            "evidence_id": "PMID:40416368", "outcome_domain": "weight",
            "comparison": "probiotic_BC99_vs_placebo", "effect_unit": "kg endpoint",
            "intervention_effect": "", "control_effect": "", "effect_difference": -69.51,
            "between_group_p": "", "within_group_p": "",
            "source_final_value": "BC99 80.39 +/- 12.74 vs placebo 78.51 +/- 10.89 at week 8",
            "source_note": "",
        }]
    ).to_csv(path, index=False)
    rows = _effects_from_structured([path], n_lookup={})
    assert len(rows) == 1
    assert abs(float(rows[0]["estimate"]) - (80.39 - 78.51)) < 1e-6


def test_human_derived_ngp_species_are_recognized() -> None:
    # human-derived next-generation probiotics must be classed as a microbial arm
    for label in (
        "Akkermansia muciniphila vs placebo",
        "Faecalibacterium prausnitzii",
        "Hafnia alvei supplementation",
        "Clostridium butyricum",
    ):
        assert _intervention_class(label) == "probiotic", label
    # and detected by the microbial mask used to build the arm registry
    frame = pd.DataFrame(
        {
            "title": [
                "Pasteurized Akkermansia muciniphila in overweight adults",
                "Faecalibacterium prausnitzii live biotherapeutic trial",
                "Statin therapy in adults",
            ]
        }
    )
    mask = _microbial_mask(frame)
    assert mask.tolist() == [True, True, False]


def test_arm_dataset_and_ci_effect_extraction(tmp_path: Path) -> None:
    review = tmp_path / "review.csv"
    intervention = tmp_path / "intervention.csv"
    arms = tmp_path / "arms.csv"
    effects = tmp_path / "effects.csv"
    pd.DataFrame(
        [
            {
                "evidence_id": "PMID:1",
                "title": "Probiotic randomized placebo controlled trial",
                "outcome_domain": "weight",
                "comparison": "probiotic_vs_placebo_adjusted",
                "final_value": "adjusted difference -1.2 (95% CI -2.0 to -0.4)",
                "final_unit": "kg",
                "time_point": "12 weeks",
                "sample_size_confirmed": "n=60 randomized",
                "review_status": "extracted",
            },
            {
                "evidence_id": "PMID:2",
                "title": "Synbiotic intervention in adults with obesity",
                "outcome_domain": "BMI",
                "comparison": "synbiotic_vs_control",
                "final_value": "synbiotic -0.5 +/- 1.0 vs control +0.1 +/- 1.2",
                "final_unit": "kg/m2",
                "time_point": "3 months",
                "sample_size_confirmed": "n=22 synbiotic; n=22 control",
                "review_status": "extracted",
            },
        ]
    ).to_csv(review, index=False)
    pd.DataFrame(
        [
            {
                "evidence_id": "PMID:1",
                "final_species": "Lacticaseibacillus rhamnosus",
                "final_strain": "GG",
                "final_total_CFU_per_day": 1e10,
                "final_log10_CFU_per_day": 10.0,
                "final_duration_weeks": 12,
                "review_status": "extracted",
            }
        ]
    ).to_csv(intervention, index=False)

    arm_result = build_arm_level_dataset([review], [intervention], arms, target_studies=2)
    assert arm_result.studies == 2
    assert arm_result.arms == 4
    arm_table = pd.read_csv(arms)
    assert arm_table.loc[arm_table["evidence_id"] == "PMID:1", "log10_cfu_per_day"].notna().sum() == 1

    effect_result = build_continuous_effects([review], arms, effects)
    assert effect_result.effects == 2
    assert effect_result.validation_ready_effects == 2
    table = pd.read_csv(effects)
    row = table[table["evidence_id"] == "PMID:1"].iloc[0]
    assert row["estimate"] == -1.2
    assert row["ci_lower"] == -2.0
    assert row["ci_upper"] == -0.4
    arm_row = table[table["evidence_id"] == "PMID:2"].iloc[0]
    assert arm_row["estimate"] == -0.6
    assert arm_row["intervention_n"] == 22


def test_continuous_model_uses_leave_one_study_out(tmp_path: Path) -> None:
    effects = tmp_path / "effects.csv"
    arms = tmp_path / "arms.csv"
    metrics = tmp_path / "metrics.json"
    predictions = tmp_path / "predictions.csv"
    model = tmp_path / "model.pkl"
    pd.DataFrame(
        [
            {
                "effect_id": f"E{i}",
                "study_id": f"S{i}",
                "evidence_id": f"S{i}",
                "outcome_domain": "weight",
                "effect_unit": "kg",
                "estimate": -0.2 * i,
                "variance": 0.25,
                "validation_ready": True,
            }
            for i in range(1, 6)
        ]
    ).to_csv(effects, index=False)
    pd.DataFrame(
        [
            {
                "study_id": f"S{i}",
                "arm_role": "intervention",
                "intervention_class": "probiotic",
                "log10_cfu_per_day": 9.0 + i / 10,
                "duration_weeks": 8 + i,
                "sample_size": 40 + i,
            }
            for i in range(1, 6)
        ]
    ).to_csv(arms, index=False)

    result = train_continuous_effect_models(
        effects, arms, metrics, predictions, model, minimum_studies=5
    )
    assert result.modeled_strata == 1
    assert len(pd.read_csv(predictions)) == 5
    assert metrics.is_file()
    assert model.is_file()


def test_structured_effects_ingestion_and_p_value_se(tmp_path: Path) -> None:
    review = tmp_path / "review.csv"
    structured = tmp_path / "structured.csv"
    arms = tmp_path / "arms.csv"
    effects = tmp_path / "effects.csv"
    # one structured row carries n via the worksheet sample size; SE comes from p + n
    pd.DataFrame(
        [
            {
                "evidence_id": "PMID:10",
                "outcome_domain": "weight",
                "comparison": "probiotic_vs_placebo_change",
                "sample_size_confirmed": "n=80 randomized",
                "review_status": "queued",
            }
        ]
    ).to_csv(review, index=False)
    pd.DataFrame(
        [
            {
                "evidence_id": "PMID:10",
                "outcome_domain": "weight",
                "comparison": "probiotic_vs_placebo_change",
                "intervention_effect": "",
                "control_effect": "",
                "effect_difference": -1.5,
                "effect_unit": "kg change",
                "between_group_p": "<0.05",
                "source_final_value": "between-group difference -1.5 kg",
            }
        ]
    ).to_csv(structured, index=False)

    build_arm_level_dataset([review], [], arms, target_studies=1, structured_paths=[structured])
    arm_table = pd.read_csv(arms)
    assert "PMID:10" in set(arm_table["study_id"])  # structured study covered by registry

    result = build_continuous_effects(
        [review], arms, effects, structured_paths=[structured]
    )
    assert result.effects == 1
    row = pd.read_csv(effects).iloc[0]
    assert row["estimate"] == -1.5
    assert row["confidence"] == "high"
    assert bool(row["validation_ready"]) is False
    assert row["variance_provenance"] == "pvalue_backcalculated"
    # SE = |estimate| / z, z = inv_cdf(1 - 0.05/2) ~= 1.96  -> SE ~= 0.765
    assert abs(float(row["standard_error"]) - 1.5 / 1.959963985) < 1e-3
    assert "pbound" in str(row["extraction_method"])


def test_loso_keeps_held_out_extreme_and_uses_fold_local_null() -> None:
    estimates = [-1.0, -1.1, -0.9, -1.05, 25.0]
    data = pd.DataFrame(
        {
            "effect_id": [f"E{i}" for i in range(5)],
            "study_id": [f"S{i}" for i in range(5)],
            "analysis_study_id": [f"S{i}" for i in range(5)],
            "stratum": "weight|kg",
            "estimate": estimates,
            "variance": 0.25,
            "variance_provenance": "reported_ci",
            "intervention_class": "probiotic",
            "log10_cfu_per_day": 9.0,
            "duration_weeks": 12.0,
            "sample_size": 50.0,
        }
    )
    predictions, _, metrics = _fit_strata(data, minimum_studies=5)
    result = predictions[0]
    extreme = result.loc[result["study_id"] == "S4"].iloc[0]
    assert len(result) == 5
    assert abs(float(extreme["null_predicted_effect"]) - (-1.0125)) < 1e-9
    assert metrics[0]["rows"] == 5
    assert metrics[0]["null_mae"] == metrics[0]["weighted_null_mae"]


def test_interpretable_intervention_features_are_low_cardinality() -> None:
    data = pd.DataFrame(
        {
            "species": ["Akkermansia muciniphila", "Lactobacillus; Bifidobacterium", ""],
            "strain": ["MucT", "multi-strain mixture", ""],
            "log10_cfu_per_day": [10.0, None, None],
            "duration_weeks": [12.0, 8.0, None],
            "dosage_form": ["capsule", "powder sachet", ""],
        }
    )
    result = _add_interpretable_intervention_features(data)
    assert result.loc[0, "microbial_family"] == "next_generation"
    assert result.loc[1, "microbial_family"] == "mixed_family"
    assert result.loc[1, "formulation_complexity"] == "multi_component"
    assert result.loc[2, "dose_status"] == "missing"
    assert result.loc[0, "dosage_form_group"] == "capsule_or_tablet"


def test_structured_two_arm_sd_uses_n_embedded_in_source(tmp_path: Path) -> None:
    structured = tmp_path / "structured.csv"
    pd.DataFrame(
        [
            {
                "evidence_id": "PMID:11",
                "outcome_domain": "glucose",
                "comparison": "probiotic_vs_placebo_endpoint",
                "effect_difference": -0.8,
                "effect_unit": "mmol/mol HbA1c endpoint",
                "between_group_p": "",
                "source_final_value": (
                    "probiotic 45.9 +/- 4.4 vs placebo 46.7 +/- 4.3; "
                    "n=66 probiotic; n=63 placebo"
                ),
                "source_note": "",
            }
        ]
    ).to_csv(structured, index=False)
    rows = _effects_from_structured([structured], n_lookup={})
    assert len(rows) == 1
    expected = ((4.4**2 / 66) + (4.3**2 / 63)) ** 0.5
    assert abs(float(rows[0]["standard_error"]) - expected) < 1e-9
    assert rows[0]["validation_ready"] is True


def test_single_lipid_subtype_keeps_its_confidence_interval(tmp_path: Path) -> None:
    structured = tmp_path / "structured.csv"
    pd.DataFrame(
        [
            {
                "evidence_id": "PMID:12",
                "outcome_domain": "lipid",
                "comparison": "probiotic_vs_control_change",
                "effect_difference": -22.8,
                "effect_unit": "mg/dL triglyceride change",
                "between_group_p": "0.049",
                "source_final_value": (
                    "triglycerides difference -22.8 mg/dL "
                    "(95% CI -45.6 to -0.1)"
                ),
                "source_note": "",
            }
        ]
    ).to_csv(structured, index=False)
    rows = _effects_from_structured([structured], n_lookup={})
    assert len(rows) == 1
    assert rows[0]["outcome_domain"] == "lipid_TG"
    assert rows[0]["validation_ready"] is True
    assert abs(float(rows[0]["standard_error"]) - (45.5 / 3.92)) < 1e-9


def test_abstract_mining_is_low_confidence_and_excluded_from_primary(tmp_path: Path) -> None:
    details = tmp_path / "details.csv"
    pd.DataFrame(
        [
            {
                "evidence_id": "PMID:20",
                "abstract": (
                    "Randomized trial in adults with obesity. Body weight mean "
                    "difference -2.0 (95% CI -3.0 to -1.0) favoured probiotic."
                ),
                "primary_outcomes": "",
                "secondary_outcomes": "",
            }
        ]
    ).to_csv(details, index=False)
    mined = mine_abstract_effects([details], {"PMID:20": 100.0})
    assert len(mined) == 1
    assert mined[0]["confidence"] == "low"
    assert mined[0]["extraction_method"] == "abstract_mined"
    assert mined[0]["outcome_domain"] == "weight"
    assert mined[0]["validation_ready"] is True
