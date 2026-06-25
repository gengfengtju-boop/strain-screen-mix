from pathlib import Path

import pandas as pd
import pytest

from proslim_ai.input_manifest import load_structured_effect_table


def _write(path: Path, estimate: float) -> None:
    pd.DataFrame(
        [
            {
                "evidence_id": "PMID:1",
                "outcome_domain": "weight",
                "comparison": "probiotic_vs_placebo",
                "effect_unit": "kg",
                "effect_difference": estimate,
            }
        ]
    ).to_csv(path, index=False)


def test_structured_loader_is_order_independent(tmp_path: Path) -> None:
    first = tmp_path / "a.csv"
    second = tmp_path / "b.csv"
    _write(first, -1.0)
    _write(second, -1.0)
    left = load_structured_effect_table([first, second])
    right = load_structured_effect_table([second, first])
    pd.testing.assert_frame_equal(left, right)
    assert len(left) == 1


def test_structured_loader_rejects_numeric_conflicts(tmp_path: Path) -> None:
    first = tmp_path / "a.csv"
    second = tmp_path / "b.csv"
    _write(first, -1.0)
    _write(second, -2.0)
    with pytest.raises(ValueError, match="Conflicting structured effects"):
        load_structured_effect_table([first, second])
