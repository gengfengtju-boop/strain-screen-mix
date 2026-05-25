# 益生菌组合推荐模块

## 目标

生成 2 菌、3 菌和 4 菌组合，并依据安全性、功能互补、目标人群匹配、响应预测、文献证据和可验证性进行排序。

## 输入

- 候选菌株评分表
- 安全性准入表
- 响应预测模型输出
- 目标人群菌群缺失特征
- `config/scoring_weights.yaml`

## 输出

- `candidate_combination_table.csv`
- `combination_score_table.csv`
- `top_combination_recommendation.csv`
- `validation_priority_list.csv`

