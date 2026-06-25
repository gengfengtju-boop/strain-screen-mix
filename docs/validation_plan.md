# 验证方案

## 验证层级

1. random split validation
2. stratified cross-validation
3. leave-one-study-out validation
4. external database validation（计划项，尚无独立外部数据集）
5. country / region stratified validation（计划项，需足够地区覆盖）

## 核心要求

`leave-one-study-out validation` 是最重要的泛化测试。模型需要在留出研究队列上保持可接受表现，才能进入后续组合推荐。

当前实现属于内部按研究分组验证。留出研究来自同一汇总数据库，不能表述为独立外部验证。

## BMI 回归指标

- RMSE
- MAE
- R2
- Pearson correlation
- Spearman correlation

## 肥胖分类指标

- AUC
- accuracy
- balanced accuracy
- precision
- recall
- F1-score

## 解释性指标

- feature importance
- SHAP value
- permutation importance

## 判读原则

如果随机拆分表现明显优于留一研究验证，优先检查批次效应、研究来源泄露、国家和测序方法混杂。
