from __future__ import annotations

import json
from pathlib import Path


def require_combination_ranking_gate(
    status_path: Path | None, *, hypothesis_only: bool = False
) -> dict[str, object]:
    if status_path is None:
        raise ValueError(
            "A research status JSON is required for combination ranking. "
            "Use --hypothesis-only to generate explicitly non-clinical hypotheses."
        )
    status = json.loads(status_path.read_text(encoding="utf-8"))
    predictive = status.get("predictive_model", status)
    enabled = bool(predictive.get("combination_ranking_enabled", False))
    if not enabled and not hypothesis_only:
        model_status = predictive.get("model_status", "unknown")
        raise ValueError(
            "Combination ranking is disabled by the research status "
            f"({model_status}). Re-run with --hypothesis-only only for validation-priority "
            "hypothesis generation."
        )
    return {
        "combination_ranking_enabled": enabled,
        "hypothesis_only": bool(hypothesis_only or not enabled),
        "research_status_path": str(status_path),
    }
