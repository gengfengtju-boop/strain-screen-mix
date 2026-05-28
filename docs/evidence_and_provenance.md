# 数据来源与证据追溯规则

## 基本原则

菌株数据、功能指标、安全性指标、干预指标、临床结局和组合推荐证据必须来自真实公开数据库、临床研究登记库、论文正文或论文补充材料。不得使用虚构 accession、虚构 DOI、虚构 PMID 或未经标注来源的手工推断值。

允许的数据库来源登记在 `config/source_registry.yaml`。如果新增来源，必须先登记来源名称、类别、主页和 accession 示例，再录入数据表。

## 必填来源

### 候选菌株功能表

`strain_function_matrix` 必须记录：

- `genome_accession`
- `genome_database`
- `genome_url`
- `annotation_database`
- `annotation_accession`
- `evidence_doi` 或 `evidence_pmid` 至少一个

推荐来源：

- NCBI Genome / NCBI Datasets / RefSeq / GenBank
- GTDB
- MGnify Genomes
- CARD / RGI
- VFDB
- ResFinder
- BacMet
- MobileElementFinder
- PubMed / MEDLINE / 期刊补充材料

### 干预信息表

`intervention_metadata` 必须记录至少一个来源标识：

- `source_accession`
- `source_url`
- `publication_doi`
- `publication_pmid`

推荐来源：

- ClinicalTrials.gov
- PubMed / MEDLINE
- 论文补充表格
- SRA / ENA / Qiita 中可追溯研究

### 临床结局表

`clinical_outcome` 必须记录至少一个来源标识：

- `source_accession`
- `source_url`
- `publication_doi`
- `publication_pmid`

结局指标必须能追溯到论文正文、补充材料、ClinicalTrials.gov 结果页或公开数据库字段。

### 组合推荐表

`combination_ranking` 必须记录：

- `source_strain_ids`
- `evidence_summary`
- `evidence_doi_list` 或 `evidence_pmid_list` 至少一个

组合推荐中的每个菌株必须能回溯到 `strain_function_matrix`。

## 证据登记表

所有手工整理的论文证据建议登记到 `evidence_registry`，记录：

- DOI / PMID
- 数据库来源和 accession
- 文献题目、年份、期刊
- 研究设计
- 支持的数据字段
- 提取说明
- 整理人
- 提取日期

推荐录入顺序：

1. 将论文、数据库或临床登记来源先录入 `evidence_registry`。
2. 将菌株功能、安全性和文献证据录入 `strain_function_matrix`。
3. 用 `validate-provenance` 检查两个表各自的来源字段。
4. 用 `validate-evidence-links` 检查菌株表引用的 DOI/PMID 是否已经登记。

## CLI 校验

字段结构校验：

```bash
proslim-ai validate-table strain_function_matrix data/metadata/templates/strain_function_matrix.csv
```

来源追溯校验：

```bash
proslim-ai validate-provenance strain_function_matrix data/strain_genome/strain_function_matrix.csv
```

如果来源字段缺失，表格不能进入菌株评分、组合推荐或报告生成模块。

菌株证据交叉校验：

```bash
proslim-ai validate-evidence-links data/strain_genome/strain_function_matrix.csv data/literature_database/evidence_registry.csv
```

如果 `strain_function_matrix` 中的 `evidence_doi` 或 `evidence_pmid` 未出现在 `evidence_registry` 中，表格不能进入菌株评分模块。

## 自动检索候选表

系统支持通过官方 API 生成候选证据表：

- PubMed E-utilities：`search-evidence --source pubmed`
- Europe PMC REST API：`search-evidence --source europe_pmc`
- ClinicalTrials.gov API v2：`search-evidence --source clinical_trials`
- NCBI Assembly E-utilities：`search-genomes`

自动检索结果只作为候选表，不能直接视为已确认事实。尤其是 NCBI Assembly 检索，关键词可能返回物种级候选而非株级精确记录。`genome_candidates` 中的 `query_match_score` 和 `manual_review_flag` 用于提示是否需要进一步确认株号。

候选证据可以用 `merge-evidence-candidates` 合并为去重草稿。去重优先级为 PMID、DOI、来源数据库和 accession。草稿仍需人工复核后才能作为正式 `evidence_registry` 使用。

```bash
proslim-ai merge-evidence-candidates data/literature_database/evidence_registry.draft.csv data/literature_database/pubmed_candidates.csv data/literature_database/europepmc_candidates.csv data/literature_database/clinicaltrials_candidates.csv
```

草稿证据可用 `screen-evidence` 排序和打标签，再用 `build-extraction-drafts` 生成 `intervention_metadata` 与 `clinical_outcome` 草稿。自动抽取只能填充来源、干预类型提示、候选菌种/株号提示和需要人工抽取的结局占位，剂量、周期、真实数值和 responder 标签必须人工从论文或注册库中复核。

`fetch-evidence-details` 和 `extract-detail-hints` 可进一步生成抽取提示，包括样本量、周期、CFU、剂量、BMI 范围、p 值和相关结局句子。这些提示只能辅助人工复核，不能直接作为最终建模数值。

`build-review-worksheets` 会把提示转换为长表复核任务。只有人工确认并将 `review_status` 标为 `extracted` 的行，才会被 `finalize-clinical-outcomes` 回填到 final preview。这样可以避免自动提示未经复核就进入模型训练数据。

`predict-preliminary` 可在正式训练数据不足时生成启发式证据优先级评分。它不是机器学习预测模型，也不能替代 leave-one-study-out 验证；其用途是排序优先复核、优先抽取和优先实验验证的候选干预。

high/medium 优先级研究应先用 `filter-review-worksheet` 形成单独人工复核表。复核者填入 `final_value`、`final_unit`、`final_direction`、`p_value_confirmed`，并将确认行标记为 `review_status=extracted`。`validate-outcome-review` 用于防止缺字段的 extracted 行进入 final 数值表。

`validate-provenance` 会检查：

- `source_database` / `genome_database` / `annotation_database` 是否登记在 `source_registry.yaml`
- DOI 是否符合 `10.xxxx/xxxxx` 基本格式
- PMID 是否为数字编号
- URL 是否以 `http://` 或 `https://` 开头
- 关键表是否满足最低证据规则

这些检查只能作为入口质量控制，不能替代人工核对论文内容和数据库记录。
