from proslim_ai.standardize import (
    log10_cfu_per_day,
    normalize_sex,
    normalize_time_point,
    obesity_status_from_bmi,
)


def test_normalize_sex():
    assert normalize_sex("M") == "male"
    assert normalize_sex("female") == "female"
    assert normalize_sex("") == "unknown"


def test_normalize_time_point():
    assert normalize_time_point("pre") == "baseline"
    assert normalize_time_point("post-intervention") == "post"
    assert normalize_time_point("followup") == "follow-up"


def test_obesity_status_from_bmi():
    assert obesity_status_from_bmi(22) == "lean"
    assert obesity_status_from_bmi(27) == "overweight"
    assert obesity_status_from_bmi(31) == "obesity"
    assert obesity_status_from_bmi(None) == "unknown"


def test_log10_cfu_per_day():
    assert log10_cfu_per_day(1_000_000_000) == 9
    assert log10_cfu_per_day(0) is None

