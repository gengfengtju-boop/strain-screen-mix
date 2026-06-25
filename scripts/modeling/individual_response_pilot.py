"""Runner for the individual baseline-microbiome -> response LOSO pilot.

Self-test (no real data needed):
    python scripts/modeling/individual_response_pilot.py --self-test

Real run (once a curated IPD cohort exists):
    python scripts/modeling/individual_response_pilot.py \
        --profiles data/ipd_pilot/<cohort>_baseline_taxa.csv \
        --outcomes data/ipd_pilot/<cohort>_subject_outcomes.csv \
        --task regression

`profiles`: first column = subject_id, remaining columns = baseline taxon abundances.
`outcomes`: columns subject_id, outcome (delta BMI / delta weight, or 0/1 responder).
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

from proslim_ai.individual_response import leave_one_subject_out, synthetic_demo

ROOT = Path(__file__).resolve().parents[2]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--profiles")
    ap.add_argument("--outcomes")
    ap.add_argument("--task", choices=["regression", "classification"], default="regression")
    ap.add_argument("--self-test", action="store_true")
    ap.add_argument("--out", default="results/prediction_results/individual_response_pilot.json")
    args = ap.parse_args()

    if args.self_test or not (args.profiles and args.outcomes):
        signal = synthetic_demo(seed=1, signal=True).to_dict()
        noise = synthetic_demo(seed=2, signal=False).to_dict()
        report = {
            "mode": "synthetic_self_test",
            "note": (
                "No real IPD cohort supplied. This only proves the LOSO pipeline "
                "recovers planted signal and correctly rejects noise. Supply "
                "--profiles and --outcomes from a curated cohort for a real run."
            ),
            "planted_signal": signal,
            "pure_noise": noise,
        }
    else:
        profiles = pd.read_csv(ROOT / args.profiles, index_col=0)
        outcomes = pd.read_csv(ROOT / args.outcomes, index_col=0).iloc[:, 0]
        result = leave_one_subject_out(profiles, outcomes, task=args.task)
        report = {"mode": "real_cohort", **result.to_dict()}

    out = ROOT / args.out
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(report, indent=2, ensure_ascii=False))
    print("wrote", out.relative_to(ROOT))


if __name__ == "__main__":
    main()
