import json
import sys
import types

import pandas as pd
import pytest
from sklearn.linear_model import LogisticRegression

from proslim_ai.tabpfn_benchmark import (
    _parse_cfu_log10,
    _duration_weeks,
    _intervention_class,
    _sample_size,
    benchmark_tabpfn,
    build_response_feature_table,
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


def _paths(tmp_path):
    return (
        tmp_path / "outcomes.csv",
        tmp_path / "model.ckpt",
        tmp_path / "metrics.json",
    )


def test_benchmark_requires_explicit_local_checkpoint(tmp_path) -> None:
    outcomes, checkpoint, output = _paths(tmp_path)
    _rows().to_csv(outcomes, index=False)
    try:
        with pytest.raises(FileNotFoundError, match="checkpoint not found"):
            benchmark_tabpfn(outcomes, checkpoint, output)
    finally:
        outcomes.unlink(missing_ok=True)
        output.unlink(missing_ok=True)


def test_benchmark_uses_grouped_validation_without_network(monkeypatch, tmp_path) -> None:
    outcomes, checkpoint, output = _paths(tmp_path)
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
    assert _parse_cfu_log10("3 x 10^10 CFU/day") == pytest.approx(10.477121)
    assert _parse_cfu_log10("1.5 billion CFU") == pytest.approx(9.176091)


def test_confirmed_intervention_review_features_are_used_but_pending_hints_are_not(tmp_path) -> None:
    confirmed = tmp_path / "intervention_confirmed.csv"
    pending = tmp_path / "intervention_pending.csv"
    outcomes = _rows().iloc[[0, 2]].reset_index(drop=True)
    pd.DataFrame(
        [
            {
                "evidence_id": outcomes.iloc[0]["evidence_id"],
                "review_status": "extracted",
                "final_log10_CFU_per_day": "10.25",
                "final_duration_weeks": "12",
                "final_species": "Bifidobacterium longum",
            }
        ]
    ).to_csv(confirmed, index=False)
    pd.DataFrame(
        [
            {
                "evidence_id": outcomes.iloc[1]["evidence_id"],
                "review_status": "pending",
                "suggested_cfu": "3 x 10^10 CFU/day",
            }
        ]
    ).to_csv(pending, index=False)
    try:
        features, _, numeric, _ = build_response_feature_table(outcomes, [confirmed, pending])

        assert "log10_cfu_day" in numeric
        assert features.iloc[0]["log10_cfu_day"] == pytest.approx(10.25)
        assert features.iloc[0]["duration_weeks"] == pytest.approx(12)
        assert pd.isna(features.iloc[1]["log10_cfu_day"])
    finally:
        confirmed.unlink(missing_ok=True)
        pending.unlink(missing_ok=True)
