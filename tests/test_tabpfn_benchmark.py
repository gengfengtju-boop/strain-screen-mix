import json
import sys
import types
from pathlib import Path
from uuid import uuid4

import pandas as pd
import pytest
from sklearn.linear_model import LogisticRegression

from proslim_ai.tabpfn_benchmark import (
    _duration_weeks,
    _intervention_class,
    _sample_size,
    benchmark_tabpfn,
)


class _FakeTabPFNClassifier:
    def __init__(self, **kwargs) -> None:
        self.model = LogisticRegression(max_iter=500)

    def fit(self, X, y):
        self.model.fit(X, y)
        return self

    def predict_proba(self, X):
        return self.model.predict_proba(X)


def _rows() -> pd.DataFrame:
    rows = []
    for study in range(10):
        for endpoint, domain in enumerate(("weight", "glucose")):
            rows.append(
                {
                    "evidence_id": f"PMID:{study}",
                    "outcome_domain": domain,
                    "endpoint_type": "adiposity" if endpoint == 0 else "metabolic",
                    "analysis_population": "aggregate_trial",
                    "comparison": "intervention_vs_control",
                    "positive_efficacy_label": "yes" if (study + endpoint) % 3 == 0 else "no",
                }
            )
    return pd.DataFrame(rows)


def _paths() -> tuple[Path, Path, Path]:
    directory = Path(__file__).resolve().parent / "fixtures"
    token = uuid4().hex
    return (
        directory / f"tabpfn_{token}_outcomes.csv",
        directory / f"tabpfn_{token}_model.ckpt",
        directory / f"tabpfn_{token}_metrics.json",
    )


def test_benchmark_requires_explicit_local_checkpoint() -> None:
    outcomes, checkpoint, output = _paths()
    _rows().to_csv(outcomes, index=False)
    try:
        with pytest.raises(FileNotFoundError, match="checkpoint not found"):
            benchmark_tabpfn(outcomes, checkpoint, output)
    finally:
        outcomes.unlink(missing_ok=True)
        output.unlink(missing_ok=True)


def test_benchmark_uses_grouped_validation_without_network(monkeypatch) -> None:
    outcomes, checkpoint, output = _paths()
    _rows().to_csv(outcomes, index=False)
    checkpoint.write_bytes(b"test-only")
    fake_module = types.ModuleType("tabpfn")
    fake_module.TabPFNClassifier = _FakeTabPFNClassifier
    monkeypatch.setitem(sys.modules, "tabpfn", fake_module)

    try:
        metrics = benchmark_tabpfn(outcomes, checkpoint, output, cv_repeats=2)

        assert metrics["validation"].endswith("group_cross_validation_by_evidence_id")
        assert metrics["cv_repeats"] == 2
        assert len(metrics["repeat_metrics"]) == 2
        assert metrics["repeat_metrics"][1]["seed"] == 118
        assert metrics["roc_auc_std"] >= 0
        assert metrics["evidence_groups"] == 10
        assert json.loads(output.read_text(encoding="utf-8"))["model"] == "TabPFNClassifier"
    finally:
        outcomes.unlink(missing_ok=True)
        checkpoint.unlink(missing_ok=True)
        output.unlink(missing_ok=True)


def test_review_numeric_feature_parsers() -> None:
    assert _sample_size("n=96 randomized; n=85 completed") == 96
    assert _duration_weeks("4 months") == pytest.approx(17.38)
    assert _intervention_class("inulin prebiotic trial with probiotic discussion") == "prebiotic"
