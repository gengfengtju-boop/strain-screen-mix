from __future__ import annotations

import math
from typing import Any


SEX_MAP = {
    "m": "male",
    "male": "male",
    "man": "male",
    "男": "male",
    "f": "female",
    "female": "female",
    "woman": "female",
    "女": "female",
}

TIME_POINT_MAP = {
    "baseline": "baseline",
    "base": "baseline",
    "pre": "baseline",
    "pre-intervention": "baseline",
    "before": "baseline",
    "post": "post",
    "post-intervention": "post",
    "after": "post",
    "follow-up": "follow-up",
    "followup": "follow-up",
}


def normalize_sex(value: Any) -> str:
    if value is None:
        return "unknown"
    text = str(value).strip().lower()
    if not text or text in {"na", "nan", "none", "unknown"}:
        return "unknown"
    return SEX_MAP.get(text, "unknown")


def normalize_time_point(value: Any) -> str:
    if value is None:
        return "unknown"
    text = str(value).strip().lower()
    return TIME_POINT_MAP.get(text, text if text else "unknown")


def obesity_status_from_bmi(bmi: Any) -> str:
    try:
        number = float(bmi)
    except (TypeError, ValueError):
        return "unknown"
    if math.isnan(number):
        return "unknown"
    if number < 25:
        return "lean"
    if number < 30:
        return "overweight"
    return "obesity"


def log10_cfu_per_day(value: Any) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if number <= 0 or math.isnan(number):
        return None
    return math.log10(number)

