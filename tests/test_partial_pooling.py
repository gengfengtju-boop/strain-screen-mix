import pandas as pd

from proslim_ai.partial_pooling import _collapse_study_strata


def test_partial_pooling_collapses_alias_rows_to_one_study_stratum() -> None:
    data = pd.DataFrame(
        {
            "analysis_study_id": ["S1", "S1", "S2"],
            "stratum": ["weight|kg", "weight|kg", "weight|kg"],
            "estimate": [-1.0, -2.0, -0.5],
            "variance": [0.4, 0.1, None],
            "variance_provenance": ["pvalue_backcalculated", "reported_ci", "missing"],
        }
    )
    result = _collapse_study_strata(data)
    assert len(result) == 2
    assert result.loc[result["analysis_study_id"] == "S1", "estimate"].iloc[0] == -2.0
