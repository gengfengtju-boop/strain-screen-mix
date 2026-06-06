# 标准运行流程脚本

脚本位置：

```powershell
scripts\run_standard_pipeline.ps1
```

该脚本把现有 `proslim-ai` CLI 串成一条可复现流程。默认行为是：

- 不联网搜索；
- 使用 `data/literature_database/*_candidates.csv` 作为候选证据输入；
- 输出文件名带 `.standard` 标记，避免覆盖已有 `draft`、`top100`、`expanded` 结果；
- 默认不训练监督模型，除非显式传入 `-TrainResponseModel`。

## 推荐用法

只跑到人工复核表生成，需要联网抓取 PubMed / ClinicalTrials.gov 详情：

```powershell
powershell -ExecutionPolicy Bypass -File scripts\run_standard_pipeline.ps1 `
  -OutputTag standard `
  -FetchDetails `
  -StopAfterReviewWorksheets
```

从已有候选 CSV 开始，但重新执行 API 搜索：

```powershell
powershell -ExecutionPolicy Bypass -File scripts\run_standard_pipeline.ps1 `
  -OutputTag standard `
  -RunSearch `
  -FetchDetails `
  -StopAfterReviewWorksheets
```

人工复核完成后，用复核表继续生成优先级和组合推荐：

```powershell
powershell -ExecutionPolicy Bypass -File scripts\run_standard_pipeline.ps1 `
  -OutputTag standard `
  -ExistingDetailHints data/literature_database/intervention_outcome_extraction_hints.top100.csv `
  -UseExistingOutcomeReview `
  -ExistingOutcomeReview data/intervention_data/outcome_review_worksheet.high_medium.csv
```

训练研究终点层级的响应模型，并把模型概率应用到组合排名：

```powershell
powershell -ExecutionPolicy Bypass -File scripts\run_standard_pipeline.ps1 `
  -OutputTag standard `
  -ExistingDetailHints data/literature_database/intervention_outcome_extraction_hints.top100.csv `
  -UseExistingOutcomeReview `
  -ExistingOutcomeReview data/intervention_data/outcome_review_worksheet.high_medium.csv `
  -TrainResponseModel `
  -ApplyResponseModel
```

## 主要输出

- `data/literature_database/evidence_registry.<tag>.csv`
- `data/literature_database/evidence_screening.<tag>.csv`
- `data/literature_database/evidence_extraction_queue.<tag>.csv`
- `data/literature_database/intervention_outcome_extraction_hints.<tag>.csv`
- `data/intervention_data/outcome_review_worksheet.<tag>.csv`
- `results/prediction_results/preliminary_evidence_response_prioritization.<tag>.csv`
- `results/prediction_results/outcome_aware_response_prioritization.<tag>.csv`
- `results/combination_ranking/formulation_aware_3to5_strain_combinations.<tag>.csv`
- `results/combination_ranking/model_response_3to5_strain_combinations.<tag>.csv`，仅在 `-ApplyResponseModel` 时生成。

## 注意

`-FetchDetails` 和 `-RunSearch` 会访问外部 API。无网络或 API 限流时，脚本会停在对应步骤。

监督响应模型的层级是研究终点层级，不是个体 baseline microbiome responder 模型。

## 补充抽取队列

可用 `build-extraction-queue` 从筛选表生成 top-N 文献抽取队列：

```powershell
.venv\Scripts\proslim-ai.exe build-extraction-queue `
  data/literature_database/evidence_screening.supplement.csv `
  data/literature_database/evidence_extraction_queue.supplement_new_top160.csv `
  --top-n 160 `
  --min-relevance-score 1 `
  --priority high `
  --priority medium `
  --exclude-evidence-ids-from data/intervention_data/outcome_review_worksheet.high_medium.csv
```

队列会按 `priority`、`relevance_score`、`year` 排序，并附加 `queue_rank` 与 `queue_reason`，可直接用于 `fetch-evidence-details`、`extract-detail-hints` 和 `build-review-worksheets`。
