from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PipelineModule:
    name: str
    title: str
    script_dir: str
    expected_outputs: tuple[str, ...]


MODULES = [
    PipelineModule(
        name="data_download",
        title="数据获取",
        script_dir="scripts/data_download",
        expected_outputs=("data source registry", "download manifest", "sample-study index"),
    ),
    PipelineModule(
        name="metadata_cleaning",
        title="元数据整理",
        script_dir="scripts/metadata_cleaning",
        expected_outputs=("sample_metadata_clean.csv", "standardized intervention metadata"),
    ),
    PipelineModule(
        name="feature_engineering",
        title="微生物组特征构建",
        script_dir="scripts/feature_engineering",
        expected_outputs=("abundance matrices", "diversity matrix", "mechanism-derived matrix"),
    ),
    PipelineModule(
        name="obesity_model",
        title="肥胖菌群状态预测",
        script_dir="scripts/obesity_model",
        expected_outputs=("BMI regressor", "obesity classifier", "obesity microbiome score"),
    ),
    PipelineModule(
        name="responder_model",
        title="益生菌干预响应预测",
        script_dir="scripts/responder_model",
        expected_outputs=("responder classifier", "response probability table"),
    ),
    PipelineModule(
        name="strain_annotation",
        title="候选菌株功能匹配",
        script_dir="scripts/strain_annotation",
        expected_outputs=("strain safety table", "strain function matrix"),
    ),
    PipelineModule(
        name="combination_recommendation",
        title="益生菌组合推荐",
        script_dir="scripts/combination_recommendation",
        expected_outputs=("combination score table", "validation priority list"),
    ),
    PipelineModule(
        name="visualization",
        title="结果解释与可视化",
        script_dir="scripts/visualization",
        expected_outputs=("SHAP plots", "feature rankings", "combination coverage matrix"),
    ),
    PipelineModule(
        name="report_generation",
        title="报告生成",
        script_dir="scripts/report_generation",
        expected_outputs=("obesity report", "response report", "strain report", "combination report"),
    ),
]


def get_module(name: str) -> PipelineModule:
    for module in MODULES:
        if module.name == name:
            return module
    valid_names = ", ".join(module.name for module in MODULES)
    raise KeyError(f"Unknown module '{name}'. Valid modules: {valid_names}")

