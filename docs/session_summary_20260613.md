# 会话总结：NGP 扩展 + 微生物组整合 + 数据质量修复（2026-06-12/13）

## 总体目标
把连续效应量模型从数据稀缺推向可用，并把预测菌种范围扩到人源微生物（NGP）。

## 一、数据采集
- **样本级微生物组**：R/Bioconductor `curatedMetagenomicData` 全量抓取 **8304 样本 × 1405 物种**（45 研究，逐研究重试+断点续传）。脚本 `scripts/data_download/fetch_curatedMetagenomicData.R`。
- **变方差策展队列**：扫 892 摘要，得 **232 个未策展、含 SD/CI/p 的肥胖结局 RCT 候选**（146 个益生菌 RCT）。`build_variance_rich_curation_queue.py`。
- **复核工作表草稿**：top-77 自动生成 + 摘要自动填值（24 行），全部 pending 待人工核。

## 二、全文策展（用户提供 PDF）
29 个 PDF 转文本映射。新增 3 个 RCT 进模型，含 **2 个人源 NGP Akkermansia 试验**：
| 研究 | 效应量 | SE |
|---|---|---|
| L. sakei CJLS03 | body_fat −0.8kg / waist −0.8cm | p+n |
| Akkermansia Depommier 2019 | weight −2.27kg / body_fat −1.37kg | CI |
| Akkermansia MucT 2025 | weight −3.1kg | CI |

## 三、菌种范围扩到人源微生物（NGP）
- `config/species_universe.yaml`：食品级益生菌 vs 人源 NGP 两类，附安全分级（NGP 需 LBP 监管 + 基因组安全）。
- 代码：`enrichment.TAXA_PATTERNS`、`tabpfn_benchmark._strain_family`(+human_derived_ngp)、`arm_effects._microbial_mask`/`_intervention_class`。
- 覆盖：语料 **176 篇**涉及 NGP（之前仅识别 Akkermansia）。NGP 队列 24 篇待策展。

## 四、微生物组整合（Phase 4）
- **4.1 基线丰度**（研究内分层一致性，剔除混杂）：稳健在肥胖中耗竭的是 **Phascolarctobacterium、F. prausnitzii、Roseburia hominis**；**Akkermansia/Christensenella 不是**（其价值在干预应答，非人群差异）。
- **4.2 微生物组先验协变量**：**否定结果**。表面 weight −16% 在补全菌属映射后反转（过拟合）；人群先验不能破局，需个体级 IPD。

## 五、数据质量修复（lipid + endpoint）
1. **endpoint-当-change 误抽**：14 行被均值/SD 错位污染（如 BMI 23.94→−0.61），加 `_two_arm_endpoint_difference` 守卫自愈。
2. **lipid 去混叠**：pooled `lipid|mg/dL`（混 mg/dL+mmol/L+TC/LDL/HDL/TG，MAE 41 的垃圾比较）拆成 `lipid_TG/TC/LDL/HDL`，单位归一。lipid_TG 成为物理有效 stratum（17.7 vs 14.0）。
3. **SE 接入 + 拒绝假阳性**：补 SE 后为凑逆方差注入粗糙 n，得 weight"越过"基线 0.013 但 BMI 恶化 2×——判定噪声，**撤销**。

## 六、肥胖状态模型（首个有诚实信号的模型）
`scripts/obesity_model/train_obesity_model.py`，8304 样本 / 206 物种（≥10% 流行率，log10）。**按研究分组 10 折 CV**（留出整个研究=新队列）为主，随机 CV 仅用于暴露混杂乐观偏差：
- **肥胖分类器（瘦 vs 肥胖）：内部按研究分组 ROC-AUC 0.729**（随机 0.825），prevalence 0.261 — **内部泛化信号，待独立外部验证**
- **BMI 回归：分组 R² 0.103，MAE 3.87 < null 4.15** — 温和但优于基线
- 签名生物学合理且自洽：Phascolarctobacterium faecium、Bifidobacterium longum 保护；Allisonella histaminiformans 最肥胖相关
- **这是项目首个在留出队列上真实优于基线的模型**（对比效应量模型 0 越过基线）
- 模型存 `models/BMI_regressor/`、`models/obesity_classifier/`

## 七、SHAP 可解释（模块 8）
`scripts/visualization/obesity_model_shap.py` → `results/SHAP_results/`（蜂群图 + 条形图 + 全 206 物种重要性 CSV）。
- 修正了方向计算（改用丰度↔SHAP 相关，而非 signed mean SHAP）
- 三方互证：SHAP × 点二列相关 × Phase 4.1 一致（Bifido longum 保护、Phascolarctobacterium 失调）

## 八、SHAP 信号接入候选优先级（模块 6/7）
`scripts/combination_recommendation/microbiome_informed_priority.py`：用肥胖模型信号做**候选优先级**（其擅长场景），非效应量预测（已证失败）。
- 现有 10 候选中 3 株有人群信号：**Bifido longum BB536 最强**（恢复耗竭保护菌）；Lactobacillus/Bacillus 诚实标"无信号"（外源/低丰度）
- surface **35 个 SHAP-保护型 NGP 恢复靶点**（Phascolarctobacterium、Parabacteroides distasonis、Anaerostipes hadrus…），全标 `pending_genome_safety`
- 三约束：关联≠因果（假设生成）、独立轴不并入临床分、NGP 需安全门

---

## 最终诚实状态（两条模型线分明）

| 模型线 | 状态 | 证据 |
|--------|------|------|
| **肥胖状态线** | 🟢 **内部验证有信号 + 可解释 + 接入候选** | 分类器 AUC 0.729（按研究分组交叉验证）；SHAP；候选优先级 |
| **干预应答线** | 🔴 无信号（数据受限）| 连续效应量 0 越过基线；二分类 AUC~0.60 |
| **组合推荐** | 🟡 门控关闭 | 候选评分+微生物组轴就绪；排序待应答信号 |

- 测试：79 全过 | 连续效应量：83 研究 / 5 stratum / 0 越过基线

## 核心结论
1. **肥胖状态模型在内部按研究分组验证中优于基线**（AUC 0.73）——可用于假设生成、人群分层探索和候选优先级，独立外部效度尚未建立。
2. **干预效应量当前不可预测**（不优于均值）——修复了数据污染、拒绝了假阳性、排除了人群先验死路后，这是干净诚实的结论。
3. **两条线不能桥接**（用人群微生物组特征预测效应量已证失败两次）——桥接需个体级 IPD。

三个真实瓶颈（均为数据问题，非代码）：
- 带方差的益生菌 RCT 太少 → 232 候选队列
- 预测特征信息量不足 → 需个体级基线菌群→应答
- 脂质亚型各自 RCT 不足

**全程坚守**：不调参凑基线、不注入脏数据、不保留好看版本、关联不冒充因果、NGP 不绕安全门。

---

## 九、效应量模型方法学重构（阶段 2/3）
- **随机效应 meta 回归**（DerSimonian-Laird）替代 ML 留一：`arm_effects.random_effects_meta_analysis` + CLI `meta-analyze-effects`。**body_fat\|kg 合并 −0.44 kg [−0.74,−0.13] I²=12% — 一致减脂信号**（ML 完全错过）；weight I²=80% 诚实判"不可合并"。
- **基因组功能 moderator**：建属级功能特征层（BSH/丁酸/黏液/丙酸）+ `_meta_regression_moderator`。weight 的"mucin 解释异质性 p=0.002"识别为 **k=3 共线假象**（生物学假设，非确立）。

## 十、菌株筛选库扩充（10 → 223）
- `strain_screening_catalog_20260613.csv`：109 人源共生 + 76 NGP + 38 食品级，按优先级×安全分层。
- 含你要的两类：益生菌 + 人源非致病菌。Tier B 保护型 92 个（Phascolarctobacterium、Anaerostipes、Parabacteroides 等）。
- 步骤 1（NCBI 基因组映射）脚本就绪；步骤 2/3（安全/功能）真版受本机工具约束，现为分类学先验。

## 模型现状（最新）
| 模型线 | 状态 |
|--------|------|
| 肥胖状态 | 🟢 AUC 0.73 + SHAP + 候选优先级 |
| 干预应答（meta 回归）| 🟡 body_fat 有一致合并效应；weight 异质性大 |
| 菌株筛选库 | 🟢 223 物种（含安全分层），待落基因组级 |
| 测试 | 81 全过 |
