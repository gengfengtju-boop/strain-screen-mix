from __future__ import annotations

import os
import re
from datetime import date


def production_run_stamp() -> str:
    stamp = os.environ.get("PROSLIM_RUN_STAMP", date.today().strftime("%Y%m%d"))
    if not re.fullmatch(r"\d{8}", stamp):
        raise ValueError("PROSLIM_RUN_STAMP must use YYYYMMDD format")
    return stamp
