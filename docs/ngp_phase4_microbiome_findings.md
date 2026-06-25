# NGP 研究计划 — 阶段 4 微生物组整合发现（2026-06-13）

数据：curatedMetagenomicData 8304 样本（瘦 4432 / 超重 2310 / 肥胖 1562），45 研究。

## 4.1 NGP 基线丰度（肥胖 vs 瘦，研究内分层一致性）

脚本 `scripts/obesity_model/ngp_baseline_abundance.py`；输出
`results/prediction_results/ngp_baseline_abundance_by_obesity_20260613.csv`。

pooled 检验受研究/国别混杂污染，故以**研究内"瘦>胖"一致性**（25 个研究）为准：

| 在肥胖中稳健耗竭（一致性≥0.72） | 一致性 |
|---|---|
| Phascolarctobacterium faecium | 0.80 |
| Roseburia hominis | 0.80 |
| Roseburia CAG_303 / CAG_182 | 0.76 |
| Faecalibacterium prausnitzii | 0.72（pooled NS，但跨研究一致）|
| Parabacteroides distasonis | 0.72 |

**不支持人群耗竭**：Akkermansia muciniphila（0.64，弱）、Christensenella minuta（0.52，无信号）。
→ Akkermansia 的价值在干预应答（RCT），非人群差异，与文献一致。

## 4.2（路线1）人群微生物组先验作为效应量协变量

实验脚本 `scripts/obesity_model/microbiome_prior_covariate_experiment.py`：把"被干预菌属在
肥胖人群的基线丰度 + 瘦/胖 log2 比"作为额外特征，留一研究验证对比 MAE。

| stratum | 研究 | MAE 基线 | MAE +微生物组 | null 基线 |
|---|---|---|---|---|
| **weight\|kg** | 11 | 1.742 | **1.471** (-16%) | 1.300 |
| body_fat\|kg | 5 | 0.364 | 0.357 | 0.295 |
| BMI\|kg/m2 | 10 | 0.887 | 0.887 | 0.325 |
| waist\|cm | 4 | 1.000 | 1.000 | 0.740 |
| lipid\|mg/dL | 6 | 41.3 | 41.3（过拟合）| 7.4 |

### 两轮结果（关键：增益不稳健）

| stratum | MAE 基线 | +微生物组(部分覆盖 21/48) | +微生物组(完整覆盖 48/48) | null |
|---|---|---|---|---|
| weight\|kg | 1.742 | 1.471 | **1.929** | 1.300 |
| body_fat\|kg | 0.364 | 0.357 | **0.523** | 0.295 |
| BMI\|kg/m2 | 0.887 | 0.887 | **1.054** | 0.325 |
| waist\|cm | 1.000 | 1.000 | **1.136** | 0.740 |
| lipid\|mg/dL | 41.3 | 41.3 | 29.9 | 7.4 |

完整覆盖后菌属分布：mixed_synbiotic 16、Bifidobacterium 14、Lactobacillus 8、Bacillus 7、Akkermansia 3。

**结论（诚实，已自我纠正）**：
- 第一轮"weight 降 16%"是**不完整覆盖的假象**（靠 NaN 中位数填补的偶然模式），**经正确补全菌属映射后增益消失甚至反转**（weight 1.471→1.929）。
- 在当前样本量（每 stratum 5-11 研究）下，加入人群微生物组先验特征**只会让岭回归过拟合**，留一误差上升。**该特征不能稳健提升预测**。
- 这是一次重要的反例：把"看起来更好"的部分覆盖版本留下来就是 cherry-picking；严格补全后真相是**无稳健信号**。

**根本结论**：人群层面的微生物组先验**不足以**破局。真正需要的是个体级"基线丰度→应答"数据（IPD）——即 RCT 报告每个受试者的基线菌群与各自应答，而非臂级汇总 + 人群近似。这类数据稀少，是后续主攻方向。
