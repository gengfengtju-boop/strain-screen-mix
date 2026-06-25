# 临床前验证优先级清单 — Top 10 益生菌组合

运行日期 2026-06-25 · 来源 `robust_strain_combinations_20260610.csv` · 共 50 个候选组合

> ⚠️ **范围声明（必须保留）**
> 本清单是 **临床前验证优先级**，不是减脂疗效或个体响应概率预测。
> 排序依据 = 证据综合（锚定 PMID）+ 机制互补 + 配方完整性 + 属多样性 + 安全分流。
> `combination_ranking_enabled=false`（疗效门关闭）；所有组合 `safety_gate=pending_genome_safety_gate`
> ——进入任何实验前必须先完成菌株级基因组 AMR/毒力/MGE 筛查。

## 评分口径
- **posterior_score_mean [p10, p90]**：证据-机制后验综合分及其 bootstrap 不确定区间。
- **UCB**：上置信界，用于主动学习探索排序。**top10_probability**：该组合落入前 10 的后验概率。
- **module_coverage / genus_diversity**：机制模块覆盖、属级多样性（各 0–10）。
- **pareto_front=yes**：在高证据 / 低复杂度 / 广覆盖上为帕累托最优。

## 组合明细

### #1 · ROBUST_001 （5 株）

**菌株**：Lactobacillus fermentum K7；Lactobacillus fermentum K8；Lactobacillus fermentum K11；Bifidobacterium lactis IDCC 4301；Bifidobacterium animalis subsp. lactis B420

- 后验综合分 **7.35** [p10 6.62, p90 8.05] · UCB 7.85 · 不确定宽度 1.42
- top10 概率 0.62 · 机制覆盖 10/10 · 属多样性 5/10 · 帕累托 yes
- 锚定证据 PMID：27810310; 37447365; 39051504
- 覆盖机制模块：BMI, SCFA_network, barrier, bifidobacterium_niche, body_fat, carbohydrate_utilization, fiber_response, lipid, waist, weight
- 推荐益生元：acacia gum optional; probiotic arm strongest without synbiotic advantage; inulin/FOS optional; polydextrose/Litesse Ultra
- 安全门：`pending_genome_safety_gate` · 验证建议：complete strain-resolved genome AMR/virulence/MGE screening before validation

### #2 · ROBUST_002 （4 株）

**菌株**：Lactobacillus fermentum K7；Lactobacillus fermentum K8；Lactobacillus fermentum K11；Bifidobacterium breve BBr60

- 后验综合分 **7.30** [p10 6.54, p90 8.06] · UCB 7.84 · 不确定宽度 1.52
- top10 概率 0.55 · 机制覆盖 9/10 · 属多样性 5/10 · 帕累托 yes
- 锚定证据 PMID：37447365; 39456659
- 覆盖机制模块：BMI, SCFA_network, amino_acid_metabolism, bifidobacterium_niche, body_fat, carbohydrate_utilization, glucose, waist, weight
- 推荐益生元：acacia gum optional; probiotic arm strongest without synbiotic advantage; inulin/FOS optional
- 安全门：`pending_genome_safety_gate` · 验证建议：complete strain-resolved genome AMR/virulence/MGE screening before validation

### #3 · ROBUST_003 （5 株）

**菌株**：Lactobacillus fermentum K7；Lactobacillus fermentum K8；Lactobacillus fermentum K11；Bifidobacterium animalis subsp. lactis B420；Bifidobacterium breve BBr60

- 后验综合分 **7.27** [p10 6.54, p90 7.97] · UCB 7.77 · 不确定宽度 1.43
- top10 概率 0.54 · 机制覆盖 10/10 · 属多样性 5/10 · 帕累托 yes
- 锚定证据 PMID：27810310; 37447365; 39456659
- 覆盖机制模块：BMI, SCFA_network, amino_acid_metabolism, barrier, bifidobacterium_niche, body_fat, carbohydrate_utilization, fiber_response, glucose, waist, weight
- 推荐益生元：acacia gum optional; probiotic arm strongest without synbiotic advantage; inulin/FOS optional; polydextrose/Litesse Ultra
- 安全门：`pending_genome_safety_gate` · 验证建议：complete strain-resolved genome AMR/virulence/MGE screening before validation

### #4 · ROBUST_004 （4 株）

**菌株**：Lactobacillus fermentum K7；Lactobacillus fermentum K8；Lactobacillus fermentum K11；Bifidobacterium lactis IDCC 4301

- 后验综合分 **7.27** [p10 6.48, p90 8.01] · UCB 7.80 · 不确定宽度 1.53
- top10 概率 0.53 · 机制覆盖 8/10 · 属多样性 5/10 · 帕累托 yes
- 锚定证据 PMID：37447365; 39051504
- 覆盖机制模块：BMI, SCFA_network, bifidobacterium_niche, body_fat, carbohydrate_utilization, lipid, waist, weight
- 推荐益生元：acacia gum optional; probiotic arm strongest without synbiotic advantage; inulin/FOS optional
- 安全门：`pending_genome_safety_gate` · 验证建议：complete strain-resolved genome AMR/virulence/MGE screening before validation

### #5 · ROBUST_005 （5 株）

**菌株**：Lactobacillus fermentum K7；Lactobacillus fermentum K8；Lactobacillus fermentum K11；Bifidobacterium breve BBr60；Bacillus coagulans BC99

- 后验综合分 **7.23** [p10 6.48, p90 7.97] · UCB 7.75 · 不确定宽度 1.49
- top10 概率 0.51 · 机制覆盖 10/10 · 属多样性 8/10 · 帕累托 yes
- 锚定证据 PMID：37447365; 39456659; 40416368
- 覆盖机制模块：BMI, SCFA_network, amino_acid_metabolism, bifidobacterium_niche, body_fat, carbohydrate_utilization, glucose, microbiome_shift, spore_former, waist, weight, weight_subgroup
- 推荐益生元：acacia gum optional; probiotic arm strongest without synbiotic advantage; inulin/FOS optional; none specified
- 安全门：`pending_genome_safety_gate` · 验证建议：complete strain-resolved genome AMR/virulence/MGE screening before validation

### #6 · ROBUST_006 （5 株）

**菌株**：Lactobacillus fermentum K7；Lactobacillus fermentum K8；Lactobacillus fermentum K11；Bifidobacterium longum BB536；Bifidobacterium breve MCC1274

- 后验综合分 **7.13** [p10 6.37, p90 7.83] · UCB 7.64 · 不确定宽度 1.46
- top10 概率 0.43 · 机制覆盖 9/10 · 属多样性 5/10 · 帕累托 no
- 锚定证据 PMID：37447365; 38542727
- 覆盖机制模块：BMI, SCFA_network, barrier, bifidobacterium_niche, body_fat, carbohydrate_utilization, lipid, visceral_fat, waist, weight
- 推荐益生元：acacia gum optional; probiotic arm strongest without synbiotic advantage; inulin/FOS optional
- 安全门：`pending_genome_safety_gate` · 验证建议：complete strain-resolved genome AMR/virulence/MGE screening before validation

### #7 · ROBUST_007 （5 株）

**菌株**：Lactobacillus fermentum K7；Lactobacillus fermentum K8；Lactobacillus fermentum K11；Bifidobacterium lactis IDCC 4301；Bifidobacterium breve BBr60

- 后验综合分 **7.17** [p10 6.47, p90 7.82] · UCB 7.64 · 不确定宽度 1.34
- top10 概率 0.42 · 机制覆盖 9/10 · 属多样性 5/10 · 帕累托 no
- 锚定证据 PMID：37447365; 39051504; 39456659
- 覆盖机制模块：BMI, SCFA_network, amino_acid_metabolism, bifidobacterium_niche, body_fat, carbohydrate_utilization, glucose, lipid, waist, weight
- 推荐益生元：acacia gum optional; probiotic arm strongest without synbiotic advantage; inulin/FOS optional
- 安全门：`pending_genome_safety_gate` · 验证建议：complete strain-resolved genome AMR/virulence/MGE screening before validation

### #8 · ROBUST_008 （5 株）

**菌株**：Lactobacillus fermentum K7；Lactobacillus fermentum K8；Lactobacillus fermentum K11；Bifidobacterium lactis IDCC 4301；Bacillus coagulans BC99

- 后验综合分 **7.16** [p10 6.43, p90 7.88] · UCB 7.66 · 不确定宽度 1.45
- top10 概率 0.42 · 机制覆盖 9/10 · 属多样性 8/10 · 帕累托 no
- 锚定证据 PMID：37447365; 39051504; 40416368
- 覆盖机制模块：BMI, SCFA_network, bifidobacterium_niche, body_fat, carbohydrate_utilization, lipid, microbiome_shift, spore_former, waist, weight, weight_subgroup
- 推荐益生元：acacia gum optional; probiotic arm strongest without synbiotic advantage; inulin/FOS optional; none specified
- 安全门：`pending_genome_safety_gate` · 验证建议：complete strain-resolved genome AMR/virulence/MGE screening before validation

### #9 · ROBUST_009 （4 株）

**菌株**：Lactobacillus fermentum K7；Lactobacillus fermentum K8；Lactobacillus fermentum K11；Bifidobacterium animalis subsp. lactis B420

- 后验综合分 **7.10** [p10 6.28, p90 7.89] · UCB 7.67 · 不确定宽度 1.61
- top10 概率 0.40 · 机制覆盖 8/10 · 属多样性 5/10 · 帕累托 yes
- 锚定证据 PMID：27810310; 37447365
- 覆盖机制模块：BMI, SCFA_network, barrier, body_fat, carbohydrate_utilization, fiber_response, waist, weight
- 推荐益生元：acacia gum optional; probiotic arm strongest without synbiotic advantage; polydextrose/Litesse Ultra
- 安全门：`pending_genome_safety_gate` · 验证建议：complete strain-resolved genome AMR/virulence/MGE screening before validation

### #10 · ROBUST_010 （4 株）

**菌株**：Bifidobacterium lactis IDCC 4301；Bifidobacterium breve BBr60；Lacticaseibacillus paracasei BEPC22；Lactiplantibacillus plantarum BELP53

- 后验综合分 **7.08** [p10 6.31, p90 7.84] · UCB 7.61 · 不确定宽度 1.53
- top10 概率 0.36 · 机制覆盖 9/10 · 属多样性 8/10 · 帕累托 yes
- 锚定证据 PMID：38999741; 39051504; 39456659
- 覆盖机制模块：SCFA_network, amino_acid_metabolism, bifidobacterium_niche, body_fat, carbohydrate_utilization, cross_feeding, glucose, lipid, lipid_metabolism, weight
- 推荐益生元：FOS/GOS optional; inulin/FOS optional
- 安全门：`pending_genome_safety_gate` · 验证建议：complete strain-resolved genome AMR/virulence/MGE screening before validation

## 下一步硬门控（进入体外/动物/人体验证前）
1. 菌株级基因组下载 + AMR（AMRFinderPlus/CARD）、毒力（VFDB）、可移动元件（MGE）筛查。
2. 通过 EFSA QPS / LBP 前例核对每株安全分层。
3. 体外 SCFA / 胆盐水解酶（BSH）/ 黏附功能确认机制假设。
4. **疗效仍需前瞻 RCT 或个体级 IPD**——本清单只决定先验证谁，不替代疗效证据。
## 机制 / 安全维度增补（属级先验）

> 机制与安全均为 **属级先验**（90 属 guild 参考 + EFSA QPS 分流）；菌株级真值仍需基因组注释。这一节用于让优先级评分更扎实，并暴露机制盲区。

| # | 组合 | 属数 | 机制轴覆盖 | 缺失机制轴 | 安全分层 | 安全门 |
|---|------|------|-----------|-----------|---------|--------|
| 1 | ROBUST_001 | 2 | 2/5：BSH(胆盐水解/降脂); lactate/acetate(乳酸/乙酸) | butyrate(丁酸); propionate(丙酸); mucin(黏液屏障) | low_qps_history | pending |
| 2 | ROBUST_002 | 2 | 2/5：BSH(胆盐水解/降脂); lactate/acetate(乳酸/乙酸) | butyrate(丁酸); propionate(丙酸); mucin(黏液屏障) | low_qps_history | pending |
| 3 | ROBUST_003 | 2 | 2/5：BSH(胆盐水解/降脂); lactate/acetate(乳酸/乙酸) | butyrate(丁酸); propionate(丙酸); mucin(黏液屏障) | low_qps_history | pending |
| 4 | ROBUST_004 | 2 | 2/5：BSH(胆盐水解/降脂); lactate/acetate(乳酸/乙酸) | butyrate(丁酸); propionate(丙酸); mucin(黏液屏障) | low_qps_history | pending |
| 5 | ROBUST_005 | 3 | 2/5：BSH(胆盐水解/降脂); lactate/acetate(乳酸/乙酸) | butyrate(丁酸); propionate(丙酸); mucin(黏液屏障) | low_qps_history | pending |
| 6 | ROBUST_006 | 2 | 2/5：BSH(胆盐水解/降脂); lactate/acetate(乳酸/乙酸) | butyrate(丁酸); propionate(丙酸); mucin(黏液屏障) | low_qps_history | pending |
| 7 | ROBUST_007 | 2 | 2/5：BSH(胆盐水解/降脂); lactate/acetate(乳酸/乙酸) | butyrate(丁酸); propionate(丙酸); mucin(黏液屏障) | low_qps_history | pending |
| 8 | ROBUST_008 | 3 | 2/5：BSH(胆盐水解/降脂); lactate/acetate(乳酸/乙酸) | butyrate(丁酸); propionate(丙酸); mucin(黏液屏障) | low_qps_history | pending |
| 9 | ROBUST_009 | 2 | 2/5：BSH(胆盐水解/降脂); lactate/acetate(乳酸/乙酸) | butyrate(丁酸); propionate(丙酸); mucin(黏液屏障) | low_qps_history | pending |
| 10 | ROBUST_010 | 3 | 2/5：BSH(胆盐水解/降脂); lactate/acetate(乳酸/乙酸) | butyrate(丁酸); propionate(丙酸); mucin(黏液屏障) | low_qps_history | pending |

### 关键发现（诚实）
- **机制盲区**：当前全部 Top 组合集中在 **BSH（胆盐水解→降脂）+ lactate/acetate** 轴，**普遍缺失 butyrate（丁酸）、propionate（丙酸）、mucin（黏液屏障）** 三条机制——因为高证据菌株几乎都是 Lactobacillus/Bifidobacterium。这是证据驱动排序的固有偏向。
- **可行动建议**：若要机制互补，应主动纳入丁酸/黏液轴候选（如 Faecalibacterium、Akkermansia 类——但这些 NGP 尚未过基因组安全门，见 NGP 计划），作为机制对照臂。
- **安全**：所有涉及属为 `qps_gras_lower_barrier / low_qps_history`，无 adverse 机制旗标；但 `combination_safety_gate=pending`——QPS 仅降低门槛，**菌株级基因组 QC（AMR/毒力/MGE）仍是硬前置**。