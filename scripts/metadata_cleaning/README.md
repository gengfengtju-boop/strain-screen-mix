# 元数据整理模块

## 目标

统一不同数据库和文献来源的字段名称、单位、标签、缺失值和批次变量。

## 输入

- 原始样本元数据
- 干预研究元数据
- 临床结局表
- `config/filtering_rules.yaml`

## 输出

- `data/processed_data/sample_metadata_clean.csv`
- 标准化干预信息表
- 标准化临床结局表
- 缺失值和剔除样本日志

