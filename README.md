# ProSlim-Microbiome-AI

基于公开数据库的益生菌减脂组合智能预测系统。

本项目的目标不是直接断言某个益生菌组合一定能减脂，而是建立一个分阶段、可扩展、可验证的 AI 建模系统，用于整合公开肠道微生物组、益生菌干预、候选菌株基因组、安全性注释和文献证据。

## 系统目标

1. 基于公开肠道微生物组数据库，识别肥胖相关菌群组成和功能通路特征。
2. 基于公开益生菌、合生元或饮食干预数据，预测不同人群对益生菌干预的响应概率。
3. 结合候选菌株基因组功能、安全性信息和目标人群菌群缺失特征，推荐具有减脂潜力的益生菌组合。

## 模块结构

| 模块 | 目录 | 目标 |
| --- | --- | --- |
| 数据获取 | `scripts/data_download` | 下载或登记公开数据库来源 |
| 元数据整理 | `scripts/metadata_cleaning` | 统一字段、单位、标签和缺失值规则 |
| 特征构建 | `scripts/feature_engineering` | 构建分类丰度、多样性、功能通路和机制派生特征 |
| 肥胖模型 | `scripts/obesity_model` | 训练 BMI 回归和肥胖状态分类模型 |
| 响应模型 | `scripts/responder_model` | 预测益生菌或合生元干预响应概率 |
| 菌株注释 | `scripts/strain_annotation` | 建立候选菌株安全性和功能矩阵 |
| 组合推荐 | `scripts/combination_recommendation` | 生成并排序 3-5 株益生菌组合 |
| 可视化 | `scripts/visualization` | 输出 SHAP、特征排名、功能覆盖和组合排序图 |
| 报告生成 | `scripts/report_generation` | 生成肥胖菌群状态、响应预测、菌株评分和组合推荐报告 |

## 推荐执行阶段

1. 基础数据库构建：形成 `sample_metadata_clean.csv`、丰度矩阵和标签表。
2. 肥胖状态预测：建立 BMI 预测、肥胖分类和 obesity microbiome score。
3. 干预数据整理：形成干预信息、临床结局变化和 responder 标签。
4. 响应预测建模：输出响应概率和响应人群特征。
5. 候选菌株矩阵：整合安全性、功能和文献证据。
6. 益生菌组合推荐：输出组合排序和验证优先级。
7. 实验验证设计：形成体外、细胞、动物和人体试验的数据反馈闭环。

## 核心验证原则

模型验证必须包含 `leave-one-study-out validation`。如果随机拆分表现良好但留一研究验证表现差，模型不能直接用于菌株组合推荐。

## 主要输出

- 肥胖菌群状态报告
- 益生菌响应预测报告
- 候选菌株评分报告
- 益生菌组合推荐报告

## 当前可执行入口

本仓库已经包含轻量级 Python CLI，用于检查项目结构、查看模块和生成标准 CSV 表头模板。

在未安装包的情况下，可从项目根目录运行：

```bash
PYTHONPATH=src python -m proslim_ai check
PYTHONPATH=src python -m proslim_ai audit
PYTHONPATH=src python -m proslim_ai modules
PYTHONPATH=src python -m proslim_ai write-templates
PYTHONPATH=src python -m proslim_ai show-schema sample_metadata
PYTHONPATH=src python -m proslim_ai validate-table sample_metadata data/metadata/templates/sample_metadata.csv
PYTHONPATH=src python -m proslim_ai clean-sample-metadata tests/fixtures/sample_metadata_dirty.csv data/processed_data/sample_metadata_clean.example.csv
```

在 Windows PowerShell 中运行：

```powershell
$env:PYTHONPATH='src'
python -m proslim_ai check
python -m proslim_ai audit
python -m proslim_ai modules
python -m proslim_ai write-templates
python -m proslim_ai show-schema sample_metadata
python -m proslim_ai validate-table sample_metadata data\metadata\templates\sample_metadata.csv
python -m proslim_ai clean-sample-metadata tests\fixtures\sample_metadata_dirty.csv data\processed_data\sample_metadata_clean.example.csv
```

如果后续安装为本地开发包，可运行：

```bash
pip install -e .
proslim-ai check
```

## 表头模板

标准化表头模板由 `config/table_schemas.yaml` 定义，可通过 CLI 写入：

```bash
python -m proslim_ai write-templates
```

默认输出到：

`data/metadata/templates/`

## 数据表校验

每次导入真实数据前，建议先运行整体审计：

```bash
python -m proslim_ai audit
```

导入公开数据库整理表后，先用 `validate-table` 检查字段是否满足标准数据字典。例如：

```bash
python -m proslim_ai validate-table sample_metadata data/metadata/sample_metadata_clean.csv
```

如需把额外字段也视为错误，可增加 `--strict`。

## 真实来源与论文证据

菌株数据、功能指标、安全性指标、干预指标和临床结局必须来自真实公开数据库、临床研究登记库、SCI/同行评议论文正文或补充材料。相关表格需要记录数据库 accession、URL、DOI 或 PMID。

可用命令检查来源追溯字段：

```bash
python -m proslim_ai validate-provenance strain_function_matrix data/strain_genome/strain_function_matrix.csv
```

允许来源登记在 `config/source_registry.yaml`。`validate-provenance` 会检查数据库名称、DOI、PMID 和 URL 的基础格式。

菌株证据建议先登记到 `evidence_registry`，再录入 `strain_function_matrix`，最后运行交叉校验：

```bash
python -m proslim_ai validate-evidence-links data/strain_genome/strain_function_matrix.csv data/literature_database/evidence_registry.csv
```

可用官方 API 自动生成候选证据表，生成后必须人工复核：

```bash
python -m proslim_ai search-evidence "probiotic obesity weight loss" data/literature_database/pubmed_candidates.csv --source pubmed --retmax 20
python -m proslim_ai search-evidence "probiotic obesity" data/literature_database/clinicaltrials_candidates.csv --source clinical_trials --retmax 20
python -m proslim_ai search-genomes "Lactobacillus gasseri SBT2055" data/strain_genome/ncbi_assembly_candidates.csv --retmax 20
```

候选文献和临床登记可合并为去重后的证据库草稿：

```bash
python -m proslim_ai merge-evidence-candidates data/literature_database/evidence_registry.draft.csv data/literature_database/pubmed_candidates.csv data/literature_database/clinicaltrials_candidates.csv
```

如需在 Windows 控制台或纯 ASCII 环境中审阅非 ASCII 标题，可导出 review 版本：

```bash
python -m proslim_ai export-ascii-safe data/literature_database/evidence_registry.draft.csv data/literature_database/evidence_registry.draft.ascii.csv
```

证据草稿可进一步筛选成抽取队列，并生成干预信息和临床结局草稿：

```bash
python -m proslim_ai screen-evidence data/literature_database/evidence_registry.draft.csv data/literature_database/evidence_screening.csv
python -m proslim_ai build-extraction-drafts data/literature_database/evidence_extraction_queue.top100.csv data/intervention_data/intervention_metadata.draft.csv data/intervention_data/clinical_outcome.draft.csv
```

可继续抓取摘要/临床登记详情，并抽取剂量、周期、样本量和结局提示：

```bash
python -m proslim_ai fetch-evidence-details data/literature_database/evidence_extraction_queue.top100.csv data/literature_database/evidence_details.top100.csv
python -m proslim_ai extract-detail-hints data/literature_database/evidence_details.top100.csv data/literature_database/intervention_outcome_extraction_hints.top100.csv
```

抽取提示可以转成长表复核工作表；人工将确认行的 `review_status` 改为 `extracted` 后，可回填 final preview：

```bash
python -m proslim_ai build-review-worksheets data/literature_database/intervention_outcome_extraction_hints.top100.csv data/intervention_data/outcome_review_worksheet.top100.csv data/intervention_data/intervention_review_worksheet.top100.csv
python -m proslim_ai finalize-clinical-outcomes data/intervention_data/clinical_outcome.draft.csv data/intervention_data/outcome_review_worksheet.top100.csv data/intervention_data/clinical_outcome.final.preview.csv
```

在没有正式样本级训练矩阵前，可以生成启发式预备预测排序，用于决定优先复核和实验验证对象：

```bash
python -m proslim_ai predict-preliminary data/literature_database/evidence_screening.csv data/literature_database/intervention_outcome_extraction_hints.top100.csv results/prediction_results/preliminary_evidence_response_prioritization.csv
```

该输出不是训练好的微生物组响应模型，只是基于证据类型、相关性、样本量、剂量/周期提示、p 值和结局句子的优先级评分。

对 high/medium 证据进行人工确认时，先筛选复核工作表，再校验 extracted 行：

```bash
python -m proslim_ai filter-review-worksheet results/prediction_results/preliminary_evidence_response_prioritization.csv data/intervention_data/outcome_review_worksheet.top100.csv data/intervention_data/outcome_review_worksheet.high_medium.csv
python -m proslim_ai validate-outcome-review data/intervention_data/outcome_review_worksheet.high_medium.csv
python -m proslim_ai finalize-clinical-outcomes data/intervention_data/clinical_outcome.draft.csv data/intervention_data/outcome_review_worksheet.high_medium.csv data/intervention_data/clinical_outcome.final.high_medium.preview.csv
```

只有 `review_status=extracted` 且 `final_value / final_unit / final_direction / p_value_confirmed` 完整的行才应进入 final 数值表。

详细规则见 [docs/evidence_and_provenance.md](docs/evidence_and_provenance.md)。

## 样本元数据清洗

`clean-sample-metadata` 会读取符合 `sample_metadata` schema 的 CSV，并执行基础标准化：

- `sex` 统一为 `male / female / unknown`
- `time_point` 统一为 `baseline / post / follow-up`
- 增加 `age_missing`
- 当 `obesity_status` 缺失或 unknown 时，根据 BMI 推导 `lean / overweight / obesity`

示例：

```bash
python -m proslim_ai clean-sample-metadata data/metadata/sample_metadata.csv data/processed_data/sample_metadata_clean.csv
```
