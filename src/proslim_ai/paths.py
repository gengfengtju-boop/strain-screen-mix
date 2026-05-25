from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class ProjectPaths:
    root: Path

    @property
    def config(self) -> Path:
        return self.root / "config"

    @property
    def data(self) -> Path:
        return self.root / "data"

    @property
    def docs(self) -> Path:
        return self.root / "docs"

    @property
    def models(self) -> Path:
        return self.root / "models"

    @property
    def results(self) -> Path:
        return self.root / "results"

    @property
    def scripts(self) -> Path:
        return self.root / "scripts"


REQUIRED_DIRECTORIES = [
    "config",
    "data/raw_data",
    "data/metadata",
    "data/taxonomic_profile",
    "data/functional_profile",
    "data/intervention_data",
    "data/strain_genome",
    "data/literature_database",
    "data/processed_data",
    "scripts/data_download",
    "scripts/metadata_cleaning",
    "scripts/feature_engineering",
    "scripts/obesity_model",
    "scripts/responder_model",
    "scripts/strain_annotation",
    "scripts/combination_recommendation",
    "scripts/visualization",
    "scripts/report_generation",
    "models/obesity_classifier",
    "models/BMI_regressor",
    "models/responder_classifier",
    "models/combination_ranker",
    "results/feature_importance",
    "results/prediction_results",
    "results/SHAP_results",
    "results/candidate_strain_scores",
    "results/combination_ranking",
    "results/validation_reports",
    "docs",
]

REQUIRED_CONFIG_FILES = [
    "database_config.yaml",
    "filtering_rules.yaml",
    "feature_config.yaml",
    "model_config.yaml",
    "validation_config.yaml",
    "scoring_weights.yaml",
    "table_schemas.yaml",
]


def find_project_root(start: Path | None = None) -> Path:
    current = (start or Path.cwd()).resolve()
    for candidate in [current, *current.parents]:
        if (candidate / "README.md").exists() and (candidate / "config").exists():
            return candidate
    return current

