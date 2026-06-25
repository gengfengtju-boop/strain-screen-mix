from proslim_ai.individual_response import (
    leave_one_subject_out,
    synthetic_demo,
)

import numpy as np
import pandas as pd


def test_synthetic_signal_beats_null():
    res = synthetic_demo(seed=1, signal=True)
    assert res.task == "regression"
    assert res.n_subjects == 40
    # with planted signal and enough subjects, LOSO should beat the mean null
    assert res.beats_null
    assert res.enabled_for_use


def test_synthetic_noise_does_not_beat_null():
    res = synthetic_demo(seed=2, signal=False)
    # pure noise must NOT be declared a usable individual model
    assert not res.enabled_for_use


def test_underpowered_is_gated_off():
    rng = np.random.default_rng(0)
    idx = [f"s{i}" for i in range(6)]
    profiles = pd.DataFrame(rng.random((6, 5)), index=idx)
    outcomes = pd.Series(rng.random(6), index=idx)
    res = leave_one_subject_out(profiles, outcomes, task="regression")
    assert res.n_subjects == 6
    assert not res.enabled_for_use
    assert any("underpowered" in n for n in res.notes)


def test_classification_runs_and_reports_auc():
    rng = np.random.default_rng(3)
    n, p = 30, 8
    X = rng.random((n, p))
    y = (X[:, 0] + rng.normal(0, 0.1, n) > 0.5).astype(int)
    idx = [f"subj{i}" for i in range(n)]
    res = leave_one_subject_out(
        pd.DataFrame(X, index=idx), pd.Series(y, index=idx), task="classification"
    )
    assert res.metric_name == "roc_auc"
    assert 0.0 <= res.metric_value <= 1.0
