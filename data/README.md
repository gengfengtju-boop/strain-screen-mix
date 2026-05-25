# Data Layout

本目录保存原始数据、中间数据和建模输入表。大型原始测序文件不建议直接提交到 Git。

## 子目录

| 目录 | 内容 |
| --- | --- |
| `raw_data` | 原始下载数据、数据库导出文件和补充表格 |
| `metadata` | 样本、受试者、研究和临床元数据 |
| `taxonomic_profile` | genus/species 分类丰度表 |
| `functional_profile` | MetaCyc、KEGG、eggNOG 等功能通路表 |
| `intervention_data` | 益生菌、益生元、合生元或饮食干预信息 |
| `strain_genome` | 候选菌株基因组、注释和安全性结果 |
| `literature_database` | 文献证据表 |
| `processed_data` | 清洗后可建模矩阵和标签表 |

## 阶段一推荐产出

- `processed_data/sample_metadata_clean.csv`
- `processed_data/genus_abundance_matrix.csv`
- `processed_data/species_abundance_matrix.csv`
- `processed_data/pathway_abundance_matrix.csv`
- `processed_data/obesity_label_table.csv`

## 阶段三推荐产出

- `intervention_data/intervention_metadata.csv`
- `processed_data/baseline_microbiome_matrix.csv`
- `processed_data/outcome_change_table.csv`
- `processed_data/responder_label_table.csv`

