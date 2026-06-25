from __future__ import annotations

from pathlib import Path

from proslim_ai.partial_pooling import evaluate_partial_pooling_baseline
from proslim_ai.run_stamp import production_run_stamp


ROOT = Path(__file__).resolve().parents[2]


def main() -> None:
    stamp = production_run_stamp()
    result_dir = ROOT / "results/prediction_results"
    report = evaluate_partial_pooling_baseline(
        result_dir / f"effect_quality_audit_{stamp}.csv",
        ROOT / f"data/intervention_data/study_arm_registry.upgrade_{stamp}.csv",
        result_dir / f"partial_pooling_effect_metrics_{stamp}.json",
        result_dir / f"partial_pooling_effect_predictions_{stamp}.csv",
    )
    print(f"Strata evaluated: {report['strata_evaluated']}")
    print(f"Strata passing: {report['strata_passing_improvement_gate']}")


if __name__ == "__main__":
    main()
