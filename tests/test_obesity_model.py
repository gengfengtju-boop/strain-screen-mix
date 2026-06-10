import json
from pathlib import Path
from uuid import uuid4

import pandas as pd
import pytest

from proslim_ai.obesity_model import train_obesity_models


def _paths() -> list[Path]:
    directory = Path(__file__).resolve().parent / "fixtures"
    token = uuid4().hex
    return [directory / f"obesity_{token}_{name}" for name in (
        "metadata.csv", "features.csv", "metrics.json", "classifier.pkl", "regressor.pkl"
    )]


def test_obesity_models_reject_example_sized_data() -> None:
    metadata_path, features_path, metrics_path, classifier_path, regressor_path = _paths()
    metadata = pd.DataFrame(
        [
            {"sample_id": "S1", "study_id": "A", "BMI": 31, "obesity_status": "obese"},
            {"sample_id": "S2", "study_id": "A", "BMI": 22, "obesity_status": "normal"},
        ]
    )
    features = pd.DataFrame([{"sample_id": "S1", "taxon_a": 0.8}, {"sample_id": "S2", "taxon_a": 0.2}])
    try:
        metadata.to_csv(metadata_path, index=False)
        features.to_csv(features_path, index=False)
        with pytest.raises(ValueError, match="At least 30 matched samples"):
            train_obesity_models(
                metadata_path, features_path, metrics_path, classifier_path, regressor_path
            )
    finally:
        for path in [metadata_path, features_path, metrics_path, classifier_path, regressor_path]:
            path.unlink(missing_ok=True)


def test_obesity_models_train_with_grouped_validation() -> None:
    metadata_path, features_path, metrics_path, classifier_path, regressor_path = _paths()
    metadata_rows = []
    feature_rows = []
    for index in range(36):
        obese = index % 2 == 0
        metadata_rows.append(
            {
                "sample_id": f"S{index}",
                "study_id": f"STUDY{index % 3}",
                "BMI": 31 + (index % 3) if obese else 22 + (index % 3),
                "obesity_status": "obese" if obese else "normal",
            }
        )
        feature_rows.append(
            {
                "sample_id": f"S{index}",
                "taxon_a": 0.8 + index / 1000 if obese else 0.2 + index / 1000,
                "pathway_b": 0.7 if obese else 0.3,
            }
        )
    try:
        pd.DataFrame(metadata_rows).to_csv(metadata_path, index=False)
        pd.DataFrame(feature_rows).to_csv(features_path, index=False)
        result = train_obesity_models(
            metadata_path, features_path, metrics_path, classifier_path, regressor_path
        )
        metrics = json.loads(metrics_path.read_text(encoding="utf-8"))
        assert result.samples_used == 36
        assert result.studies_used == 3
        assert metrics["validation"] == "grouped_cross_validation_by_study_id"
        assert metrics["obesity_classification"]["auc"] > 0.9
        assert classifier_path.exists()
        assert regressor_path.exists()
    finally:
        for path in [metadata_path, features_path, metrics_path, classifier_path, regressor_path]:
            path.unlink(missing_ok=True)
