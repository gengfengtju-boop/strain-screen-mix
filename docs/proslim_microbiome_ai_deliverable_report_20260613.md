# ProSlim-Microbiome-AI 完整可交付报告

**减重相关肠道微生物：肥胖状态预测 · 干预应答评估 · 候选菌筛选与组合设计**

**版本** v1.1　**日期** 2026-06-14　**范围** 全链路（数据 → 双模型 → 223 菌筛选 → 组合假设）

> **v1.1 更新**：效应量综合改用更严格的小样本方法（Paule-Mandel τ² + Hartung-Knapp-Sidik-Jonkman 区间，仅直接方差，p 值反算降级为敏感性）。**v1.0 的"body_fat −0.44 kg CI 排除 0"在严格方法下不成立**（直接方差仅 k=1，效应双向），已修正为复制假设。详见 `model_replan_20260614.md`。

---

## 0. 阅读须知（诚实声明）

本报告区分三类结论，请勿混淆：
- **内部验证信号**：经按研究分组交叉验证、优于基线的结果（仅肥胖状态模型）；尚未完成独立外部验证。
- **诚实否定**：经正确方法验证后不成立的结果（干预效应量不优于均值）。
- **知识先验 / 设计假设**：基于分类学/比较基因组的标注与机制设计——用于**分流和优先级**，**不替代**基因组级实测，**不冒充疗效**。

两道门控贯穿全程：**安全门**（谁能进，需基因组确认）与**疗效门**（`combination_ranking_enabled=false`，效应量无信号则不发疗效排序）。二者独立。

---

## 1. 执行摘要

| 维度 | 成果 | 状态 |
|---|---|---|
| 数据基础 | 8304 样本×1405 物种微生物组 + 659 文献证据库 | 🟢 |
| **肥胖状态模型** | 瘦 vs 肥胖内部按研究分组 ROC-AUC **0.729**；BMI R² 0.103 | 🟢 **内部验证有信号** |
| 可解释性 | SHAP 物种签名，三方互证 | 🟢 |
| **干预效应量模型** | 严格 meta（HKSJ/PM，仅直接方差）：仅 weight\|kg 可合并（−1.62 kg，CI 勉强排除 0，但 I²=76%、非复制就绪）；body_fat 不可合并 | 🔴 无可复制信号 |
| 菌株筛选库 | **10 → 223**（益生菌 + 人源非致病）；三步标注 | 🟢 |
| 安全/机制候选 | **79** 机制候选 / **105** 安全可入池 / 28 硬排除 | 🟢 |
| 组合设计假设 | **201** 机制互补假设（设计轴，非疗效）| 🟡 假设 |
| 疗效预测 | 效应量不可预测 → 组合疗效未解锁 | 🔴 数据受限 |

**一句话**：建成了一个**有信号的肥胖状态模型**和一条**安全分层、机制合理、可送验证的候选菌→组合设计链**；但**干预疗效在当前数据下不可预测**，组合的"有效性"诚实地保持未解锁。

---

## 2. 目标与范围

预测三件事：① 人群肥胖状态（微生物组→BMI/分类）；② 干预应答（菌株/配方的减重效应量）；③ 候选菌与组合（基于证据+机制+安全的筛选与设计）。

---

## 3. 数据基础

- **样本级微生物组**：curatedMetagenomicData，8304 样本（瘦 4432/超重 2310/肥胖 1562）× 1405 物种，45 研究，BMI 全覆盖（11–66）。
- **文献证据**：659 去重 RCT/试验候选；83 研究进入效应量数据集，其中高置信策展含 SE 的约 20-34 行。
- **基因组**：候选菌 NCBI assembly + 本报告新增 223 物种的基因组映射。

---

## 4. 模型线 A — 肥胖状态模型（已验证信号）

**方法**：HistGradientBoosting，206 物种特征（≥10% 流行率，log10 丰度）。**按研究分组 10 折 CV**（留出整个研究=新队列）为主，随机 CV 仅暴露混杂乐观偏差。

**结果**：
| 模型 | 分组 CV（诚实）| 随机 CV | 基线 | 优于基线 |
|---|---|---|---|---|
| 肥胖分类器（瘦 vs 肥胖）| **ROC-AUC 0.729** | 0.825 | 0.5 | ✅ |
| BMI 回归 | R² 0.103, MAE 3.87 | R² 0.225 | MAE 4.15 | ✅ |

**可解释（SHAP）**：保护型（Bifidobacterium longum、Phascolarctobacterium faecium、Turicibacter）；肥胖型（Allisonella histaminiformans 居首）。SHAP × 点二列相关 × 研究内分层一致性**三方互证**。

**意义**：项目首个在内部按研究分组验证中优于基线的模型。随机拆分与分组验证的差距（0.73 vs 0.83）提示明显的研究批次混杂；剩余性能仍可能包含数据库和队列层面的混杂，需独立外部数据确认。

---

## 5. 模型线 B — 干预效应量模型（诚实否定 + 方法学纠正）

**问题诊断**：原 ML 留一验证在每 stratum 仅 5–12 研究上拟合 3–4 特征——**统计方法错配**，结果"0 stratum 优于均值基线"。

**方法学纠正（v1.1 严格版）**：改用 **Paule-Mandel τ² + 修正 HKSJ 区间**（小样本正确方法），**仅纳入直接方差**（reported CI 或臂级 SD+n），p 值反算 SE 降级为敏感性。配合 11 组别名去重、18 行共干预标记、缺失方差 bootstrap 三角验证、证据层敏感性。

| Stratum | 直接方差 k | 合并效应（HKSJ）| 95%CI | I² | 复制就绪 |
|---|---|---|---|---|---|
| weight\|kg | 4 | −1.62 kg | [−3.24, −0.006] | 76% | ❌ 否（预测区间跨 0、敏感性含 0）|
| **body_fat\|kg** | 1 | — | — | — | 不可合并 → 复制假设（效应双向）|
| BMI / lipid / waist / glucose | <3 | — | — | — | 直接方差不足 |

**关键修正**：v1.0 基于较弱的 DL 方法 + p 值反算方差，曾报 body_fat −0.44 [−0.74,−0.13] CI 排除 0。**严格 HKSJ + 直接方差下此结论不成立**——body_fat 直接方差仅 k=1，效应双向（4 负 2 正），降级为优先复制假设。

**基因组 moderator / 人群特征桥接**：均为小样本假象或过拟合，无稳健增益。两条线不能用人群特征桥接，需个体级 IPD。

**结论**：严格小样本方法下，**0 个 stratum 达到复制就绪、0 优于均值基线**。weight 显示边际合并降低（−1.62 kg）但异质性高（I²=76%）、预测区间与敏感性均跨 0，不可作为疗效信号。`combination_ranking_enabled` 保持 false。这是**正确方法得出的诚实零结果**，约束被定位为：直接方差研究太少（仅 13 研究 / 39 行有 reported SD/CI）。

---

## 6. 菌株筛选库（10 → 223）与三步标注

**为何扩库**：旧候选仅含临床测过的菌（数量少）；筛选库改为基因组/信号驱动——肥胖签名的人源菌 + 食品级益生菌。

**构成**：109 人源共生 + 76 NGP + 38 食品级 = 223。

**三步标注**（每步标 provenance）：
1. **基因组映射**（NCBI Datasets API，实测）：181/223 映射，125 isolate 质量；42 MAG/未解析（含 1 个拒绝错配赋值的 R. bicirculans）。
2. **安全分流**（EFSA QPS + 临床微生物学，**知识先验**）：QPS 28 / LBP 前例 5 / 新型需筛 165 / 病原·AMR 属 25。
3. **功能注释**（90 属代谢 guild，**知识先验**）：丙酸 58/乳酸 49/丁酸 35/黏液 31；**4 个不利机制硬排除**（Desulfovibrio/Bilophila H₂S、Allisonella 组胺——与 SHAP 双重一致）。

**整合优先清单**：**79** 机制候选（isolate 基因组 + 安全 + 有利机制）。

---

## 7. 组合安全门与机制设计假设

**安全门资格**（223 → 准入分流）：
- **105 安全可入池**（40 NGP + 39 共生 + 26 食品级），全标 `pending`（需真筛查）。
- **28 硬排除**（病原/AMR 属 + 不利机制）；90 无 isolate 基因组不可 QC。

**机制互补组合假设（201）**：覆盖互补 SCFA/胆汁酸 niche + 交叉喂养。头号设计：
> **Bifidobacterium longum + Anaerostipes hadrus + Phascolarctobacterium faecium + Akkermansia muciniphila**
> —— 完整 SCFA 谱（乙酸→丁酸→丙酸）+ BSH 降脂 + 黏液屏障；含乳酸→丁酸交叉喂养；含 QPS 可交付锚 + 恢复耗竭保护菌。

**门控**：`predicted_response` 全空，`combination_ranking_enabled=false`。这是**临床前机制设计假设，非疗效**。

---

## 8. 局限与门控（务必阅读）

1. 安全/功能标注为**知识先验**，无法检测菌株特异 AMR/毒力/可移动元件 → 需基因组级实测。
2. 除 5 个临床证据菌外，**其余为筛选假设**；"肥胖中耗竭"是关联非因果。
3. **41 个 MAG** 有基因组信息但不可作产品。
4. **疗效未解锁**：效应量不可预测，组合不发疗效排序。
5. 肥胖模型有混杂乐观偏差（已暴露），且为状态预测，非个体应答。

---

## 9. 下一步路线（按杠杆）

| 优先级 | 行动 | 杠杆 |
|---|---|---|
| 1 | **定向策展直接方差研究**（报告臂级 SD/CI 的 weight/body_fat RCT，k 4→≥10）| 唯一能让 HKSJ 区间收窄的统计途径 |
| 2 | **个体级 IPD**（基线菌群+各自应答的 RCT）→ 真正的应答模型 | 最高，唯一能解锁个体疗效 |
| 3 | **真基因组筛查**（下载 79/105 基因组 + AMRFinder/abricate/prokka/antiSMASH）| 把先验升级为实测 |
| 4 | 强化肥胖模型（功能通路+多样性、序数、校准、**外部验证**）| 唯一有信号的资产 |

**真筛查 SOP**（落地步骤 2/3）：`datasets download` → AMRFinderPlus/abricate(CARD/VFDB/ResFinder) 安全 → prokka/bakta + antiSMASH + BSH/bai 检测功能 → 体外验证 → 通过安全门方进推荐。

---

## 10. 产出文件索引

**模型**
- `models/obesity_classifier/`, `models/BMI_regressor/` — 肥胖状态模型
- `results/prediction_results/obesity_model_metrics_20260613.json` — 指标
- `results/SHAP_results/obesity_shap_{beeswarm,bar}_20260613.png` + `..._shap_importance_*.csv` — 可解释
- `results/prediction_results/effect_meta_analysis_20260613.json` — 效应量 meta 回归

**菌株筛选**
- `results/candidate_strain_scores/strain_screening_catalog_functional_20260613.csv` — **主表**（223 × 全标注）
- `..._screening_shortlist_ranked_20260613.csv` — 79 机制候选
- `..._combination_safety_gate_eligibility_20260613.csv` — 105 安全可入池
- `data/strain_genome/genus_functional_guild_reference_20260613.csv` — 90 属功能参考

**组合**
- `results/combination_recommendations/mechanism_complementary_hypotheses_20260613.csv` — 201 设计假设

**文档**
- `docs/strain_screening_report_20260613.md` — 筛选专项报告
- `docs/research_plan_next_20260613.md` — 研究计划 + 进展
- `docs/{ngp_phase4_microbiome_findings,lipid_stratum_diagnosis,session_summary}_20260613.md`

---

## 附录 A — 方法可复现命令

```powershell
$env:PYTHONPATH='src'
# 肥胖模型 + SHAP
python scripts/obesity_model/train_obesity_model.py
python scripts/visualization/obesity_model_shap.py
# 效应量 meta 回归
python -m proslim_ai meta-analyze-effects <effects> <arms> <out.json>
# 菌株筛选三步
python scripts/strain_annotation/build_strain_screening_catalog.py
python scripts/strain_annotation/map_genomes_step1.py
python scripts/strain_annotation/safety_triage_step2.py
python scripts/strain_annotation/functional_annotation_step3.py
# 安全门 + 组合假设
python scripts/combination_recommendation/safety_gate_eligibility.py
python scripts/combination_recommendation/mechanism_complementary_hypotheses.py
```

测试：`python -m pytest tests/`（81 通过）。

---

*本报告所有"知识先验/设计假设"类结论需基因组级实测与临床验证后方可用于产品决策。报告秉持：不调参凑基线、不注入脏数据、不保留好看版本、关联不冒充因果、安全门不可绕过。*
