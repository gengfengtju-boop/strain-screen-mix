"""Train the canonical population obesity models and research report artifacts.

The implementation lives in ``proslim_ai.obesity_model`` so the CLI, tests, and
research script cannot silently drift to different algorithms.
"""

from __future__ import annotations

from pathlib import Path

from proslim_ai.obesity_model import train_obesity_models


ROOT = Path(__file__).resolve().parents[2]


def main() -> None:
    result = train_obesity_models(
        metadata_path=ROOT / "data/metadata/sample_metadata_raw.csv",
        feature_matrix_path=ROOT / "data/taxonomic_profile/species_abundance_wide.csv",
        metrics_output=ROOT / "results/prediction_results/obesity_model_metrics_20260613.json",
        classifier_output=ROOT / "models/obesity_classifier/obesity_classifier_20260613.pkl",
        bmi_regressor_output=ROOT / "models/BMI_regressor/bmi_regressor_20260613.pkl",
        signature_output=(
            ROOT / "results/prediction_results/obesity_microbiome_signature_20260613.csv"
        ),
        sample_score_output=(
            ROOT / "results/prediction_results/obesity_microbiome_score_20260613.csv"
        ),
    )
    print(f"Samples: {result.samples_used} | studies: {result.studies_used}")
    print(f"Metrics: {result.metrics_output}")


if __name__ == "__main__":
    main()
