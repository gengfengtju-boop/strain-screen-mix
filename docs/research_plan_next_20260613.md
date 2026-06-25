# 下一阶段研究计划：模型问题诊断 + 修改方案（2026-06-13）

承接本会话成果（见 `session_summary_20260613.md`）。本文档分三部分：模型问题诊断、研究计划、具体修改方案。

---

## 执行进展（截至 2026-06-13，滚动更新）

| 计划项 | 状态 | 产出/备注 |
|--------|------|-----------|
| 阶段 2 · 随机效应 meta 回归 | ✅ **已完成** | `arm_effects.random_effects_meta_analysis`（DL）+ CLI `meta-analyze-effects` + 测试。结果：**body_fat\|kg 合并 −0.44 kg [−0.74,−0.13] I²=12%（一致减脂，CI 排除 0）**；BMI 提示性；weight I²=80% 不可合并。报告 `effect_meta_analysis_20260613.json` |
| 阶段 3 · 基因组功能 moderator | 🟡 **框架完成** | `data/strain_genome/strain_genomic_functional_features.csv`（属级 BSH/丁酸/黏液/丙酸先验）+ `_meta_regression_moderator` + 测试。weight 的"mucin 解释 I² 80→0% p=0.002"经诊断为 **k=3 与菌属共线的假象**（4 个 moderator 同值即铁证）——是机制假设（Akkermansia 黏液降解 vs Lactobacillus BSH），非确立结论 |
| 菌株筛选库扩充 | ✅ **已完成（物种级）** | 10 → **223 条** `strain_screening_catalog_20260613.csv`：109 人源共生 + 76 NGP + 38 食品级；分层 A 临床5/B 保护92/B 食品18/C 假设82/C 病原属审26 |
| 步骤 1 · 物种→基因组 accession | ✅ **已完成** | `map_genomes_step1.py` 跑完：**180/223 映射成功，124 个高质量 isolate（Complete/Chromosome）**，41 个 MAG-only（CAG 未培养，不可作菌株产品），2 个网络失败可重试。输出 `strain_screening_catalog_genomes_20260613.csv`。可进入步骤 2 的 actionable 候选 ≈ 70（49 保护型 + 16 食品级 + 5 临床，均有 isolate 基因组）|
| 步骤 2 · 基因组安全筛查 | 🟡 **知识先验已完成** | `safety_triage_step2.py`（EFSA QPS + 临床微生物学）分流 223 条：低风险 QPS 28 / LBP 前例 5 / 新型共生需筛 165 / 病原·AMR 属应排除 25。**首批可筛 30 个**（isolate 基因组 + QPS/LBP）。输出 `strain_screening_catalog_safety_20260613.csv`。⚠️真版 AMR/毒力（AMRFinder/abricate/CARD/VFDB）仍需下载基因组+工具，本机不可行 |
| 步骤 3 · 功能注释 | 🟡 **属级先验已完成** | `functional_annotation_step3.py`：90 属代谢 guild 标注（丁酸 35/丙酸 58/乳酸 49/黏液 31）+ 不利机制标注（4 个：Desulfovibrio/Bilophila H₂S、Allisonella 胺）。**有利+可落地候选 79 个**。输出 `strain_screening_catalog_functional_20260613.csv`（三步主表）+ `genus_functional_guild_reference_20260613.csv`。⚠️真版需 prokka/antiSMASH de-novo 注释 |

### 重要可行性说明（诚实边界）
- **可在本环境真实做**：NCBI accession 映射（步骤 1，联网查询）。
- **本环境做不了"真"版**：步骤 2/3 需下载 223 个基因组（GB 级）+ 安装生信工具链（AMRFinderPlus、abricate、prokka、antiSMASH）。当前只能给**知识/分类学先验**版本，作为分流，**不能替代**真正的基因组级 AMR/毒力筛查与功能注释。
- 落地真版需要：① 一台能跑 nextflow/conda 生信流程的机器；② 批量下载基因组；③ 跑标准工具。这是独立的生信工程，建议作为单独阶段。

---

## 第一部分：当前模型问题诊断

### 模型 A — 干预效应量模型（连续，`arm_effects.py`）
**现状**：83 研究 / 5 可建模 stratum / **0 个优于均值基线**。

| 问题 | 根因 | 严重度 |
|------|------|--------|
| P1 留一验证 MAE 不优于均值 | 每 stratum 仅 4-12 研究，用 ML（岭回归）拟合 3-4 特征——**n 远不够** | 🔴 致命 |
| P2 特征信息量低 | 仅 cfu/周期/样本量/干预类，**不含菌株功能基因组、人群基线菌群** | 🔴 高 |
| P3 臂级聚合丢失个体异质性 | 用臂均值，无法建模"谁应答" | 🔴 高 |
| P4 SE 缺失广泛 | 多数研究无 n → 无法逆方差加权 → 退化 OLS | 🟡 中 |
| P5 方法学错配 | 在 n=5-12 上做 ML 留一验证，**统计上不合适**（应用随机效应 meta 回归）| 🔴 高 |

**核心诊断**：这是**方法学问题 + 数据粒度问题**，不是调参能解决的。在 5-12 个研究上用 ML 学 3-4 个特征注定失败；正确做法是随机效应 meta 回归（建模研究间异质性 τ²），或下沉到个体级数据。

### 模型 B — 肥胖状态模型（`train_obesity_model.py`）
**现状**：分类器 AUC 0.729（内部按研究分组交叉验证），BMI R² 0.103 —— **内部验证有信号，但外部效度未知**。

| 问题 | 根因 | 严重度 |
|------|------|--------|
| P6 BMI 回归弱（R²0.10）| 仅用物种丰度，无功能通路/多样性特征 | 🟡 中 |
| P7 混杂乐观偏差大（0.73 vs 0.83）| 45 研究批次/地域/测序差异 | 🟡 中 |
| P8 二分类丢弃 overweight | lean-vs-obesity 损失中间梯度 | 🟢 低 |
| P9 无校准 | 概率未校准，分层阈值不可靠 | 🟢 低 |

### 模型 C — 二分类应答模型（`response_model.py`）
**现状**：logistic_l2 留一 AUC ~0.60 —— **是研究-终点描述分类器，非个体应答模型**。
- P10：用描述字段预测"该研究是否报告显著"，**不是预测个体减重**——名不副实。

### 跨模型结构问题
- P11：肥胖状态线与干预应答线**无法用人群微生物组特征桥接**（已证两次失败：Phase 4.2 原始丰度、SHAP 签名关联）。桥接需个体级 IPD。

---

## 第二部分：研究计划（按杠杆×可行性排序）

### 阶段 1 ⭐ 个体级微生物组-应答数据（IPD）——根本破局
**目标**：拿到"同一批人的基线菌群 + 各自减重应答"，建真正的个体应答模型。
- **1.1 数据源**：① 已沉积测序的益生菌 RCT（SRA/ENA/Qiita，按 BioProject 配对 per-subject 基线+结局）；② curatedMetagenomicData 里含时间点的干预研究（本次 obesity 过滤集是横断面，但 CMD 有 dietary intervention 子集）；③ 联系作者要补充个体数据。
- **1.2 建模**：基线菌群（+宿主协变量）→ 个体 ΔBMI/Δweight，留一研究 CV。
- **交付**：个体应答模型；基线菌群应答标志物。**这是唯一能让"应答预测"真正工作的路径**。
- **风险**：配对数据稀少、异构测序需统一处理（MetaPhlAn 重跑）。

### 阶段 2 效应量模型方法学重构（不需新数据，立即可做）
**目标**：用统计上正确的方法替代 ML 留一。
- **2.1 随机效应 meta 回归**：每 stratum 用 DerSimonian-Laird/REML，建模 τ²，预设 1-2 个 moderator（如 log10CFU、菌株家族）。给诚实的合并效应 + 95%CI + 异质性，而非强行预测。
- **2.2 跨 stratum 部分汇集**（贝叶斯分层模型）：在 BMI/weight/waist 间借力，缓解单 stratum n 不足。
- **交付**：诚实的 meta 分析报告（哪些干预有合并效应、异质性多大），替代"0 越过基线"的 ML 失败。
- **风险**：可能结论仍是"异质性大、合并效应不显著"——但那是**正确的科学表述**。

### 阶段 3 效应量模型加功能基因组特征
**目标**：把 P2（特征弱）补上。
- 用候选菌基因组注释（BSH、SCFA/丁酸、黏液黏附、EPS）作为臂特征，替代/补充粗糙的"干预类"。
- 与阶段 2 结合：meta 回归的 moderator 用功能特征。
- **交付**：功能特征是否解释部分异质性的检验。

### 阶段 4 强化肥胖状态模型（已有信号，提升价值）
- **4.1 加功能特征**：MetaPhlAn 通路丰度 + α/β 多样性 → 改善 BMI R²（P6）。
- **4.2 序数/三分类**：lean<overweight<obesity 序数回归（P8）。
- **4.3 校准 + 研究随机效应**：概率校准，分层阈值可靠（P9）。
- **交付**：更强的肥胖分层器，用于人群分层与候选优先级。

### 阶段 5 扩充变方差 RCT 策展（喂阶段 2/3）
- 策展 232 候选队列，让更多 stratum 达到 meta 回归可用的研究数。
- 脂质按 TC/LDL/HDL/TG 逐亚型策展（补足 P 见 lipid 诊断文档）。

### 阶段 6 NGP 基因组安全 + 功能（承接 NGP 计划）
- 35 个 SHAP-保护型 NGP 恢复靶点过基因组安全门 + 功能注释，才能进推荐。

---

## 第三部分：具体模型修改方案

### 修改 1：效应量模型 — 从 ML 留一改为随机效应 meta 回归（针对 P1/P5）
```
现状：train_continuous_effect_models() 每 stratum 跑 Ridge LOSO
改为：每 stratum 跑 REML 随机效应模型（statsmodels / metafor 风格）
      输出：合并效应 θ、τ²（异质性）、I²、95%CI、moderator 系数
门控：以"合并效应 95%CI 是否排除 0 + I² 是否可控"替代"MAE 是否优于 null"
```
理由：n=5-12 + 已知 SE 的数据，meta 回归是教科书正确方法；ML 留一是误用。

### 修改 2：效应量模型 — 功能基因组 moderator（针对 P2）
```
build_arm_level_dataset() 已有 species/strain → 关联 strain_function_matrix
新增 moderator：BSH_potential, SCFA_potential, mucin_adhesion（数值/分类）
```

### 修改 3：肥胖模型 — 功能特征 + 序数（针对 P6/P8）
```
train_obesity_model.py：
  + 拉取 functional_profile（MetaPhlAn pathways）合并入 X
  + α多样性(Shannon)、β多样性主坐标 作为特征
  + 三分类改用 OrderedModel / 或 BMI 连续回归为主
  + CalibratedClassifierCV 包装，输出校准概率
```

### 修改 4：应答模型正名（针对 P10）
```
response_model.py 重命名/重定位为 "study_endpoint_evidence_classifier"
个体应答模型另起（阶段 1 IPD 数据驱动），不再混淆两者
```

### 修改 5：桥接策略修正（针对 P11）
```
放弃"人群微生物组特征→效应量"的桥接（已证失败两次）
改为：肥胖模型仅服务 (a) 人群分层 (b) 候选优先级（已实现）
      个体应答用 IPD 单独建（阶段 1）
```

---

## 诚实的成功判据与预期

| 阶段 | 成功判据 | 现实预期 |
|------|---------|---------|
| 1 IPD | 个体应答模型跨队列 AUC>0.65 | 数据若到位，最可能真正破局 |
| 2 meta 回归 | 给出诚实合并效应+异质性 | **结论可能仍是"异质性大、效应不确定"——但这是正确科学** |
| 3 功能特征 | 功能 moderator 解释部分 τ² | 不确定 |
| 4 肥胖强化 | BMI R²>0.15，三分类 AUC>0.73 | 可达 |
| 5 策展 | ≥3 stratum 达 meta 回归 n | 可达 |

**优先级建议**：阶段 2（方法学重构，立即可做、纠正根本错误）+ 阶段 4（肥胖强化，已有信号）并行；阶段 1（IPD）启动数据搜寻（最高杠杆但周期长）。

**纪律**：不调参凑基线；meta 回归如实报异质性；个体模型严格留一研究 CV；NGP 不绕安全门；关联不冒充因果。
