# 人源微生物（下一代益生菌）纳入研究计划

> 目标：把人源肠道共生菌 / 下一代益生菌（NGP）发展为**证据支撑、基因组安全筛查、机制可解释**的减重配方候选，与现有食品级益生菌并列进入预测与推荐系统。
>
> 立项日期 2026-06-13。本计划承接已完成的菌种范围扩展（`config/species_universe.yaml`、`[[species-universe-ngp]]`）与 NGP 证据筛选（`results/prediction_results/ngp_curation_queue_20260613.csv`，24 篇待策展）。

---

## 0. 范围与候选菌（已定义）

按抗肥胖/代谢证据强度分三档（详见 `config/species_universe.yaml`）：

| 档 | 菌种 | 现有证据 |
|----|------|---------|
| **A 临床已验证** | *Akkermansia muciniphila*（巴氏灭活）、*Hafnia alvei* HA4597 | 人体 RCT（Depommier 2019、MucT 2025 已入库）|
| **B 临床早期** | *Clostridium butyricum*、*Bacteroides uniformis* CECT 7771、*Christensenella minuta* | 少量小样本 RCT / Ph1-2 |
| **C 临床前为主** | *Faecalibacterium prausnitzii*、*Dysosmobacter welbionis*、*Roseburia*、*Parabacteroides distasonis*、*Phascolarctobacterium* | 动物 + 关联性研究 |

**原则**：A/B 档进入效应量建模；C 档仅作机制注释与"假设候选"，不进推荐，直到出现人体证据。

---

## 阶段 1 — 证据库扩充（文献，4 周）

**1.1 定向检索**
- 新建 `config/search_batch_ngp.yaml`，按属逐个建查询（沿用现有 PubMed/EuropePMC/ClinicalTrials 三源批量框架）。
- 每属查询关键词：`<genus> + (obesity|overweight|body weight|fat mass|metabolic|insulin) + (randomized|trial|supplementation)`。
- 同步抓 NCBI/GTDB 基因组候选（沿用 `data/strain_genome` 模式）。

**1.2 全文臂级效应量提取**
- 优先策展 `ngp_curation_queue_20260613.csv` 现有 24 篇中**摘要已含数值**的（已完成 Akkermansia ×2）。
- 其余（仅报 p 值者）走全文/补充表提取（沿用 `.fulltext_extract` + `apply_fulltext_extractions.py` 流程）。
- 产出并入 `clinical_outcome.structured_effects.fulltext_new_*.csv`。

**交付**：NGP 证据登记表；新增 ≥10 个 A/B 档 NGP 臂级 SE-bearing 数据点。

---

## 阶段 2 — 基因组与安全门（关键，与阶段 1 并行，6 周）

> **NGP 不是食品补充剂——是活体生物治疗产品（LBP）**。这是与传统益生菌最大的区别，安全门必须前置。

**2.1 参考基因组获取**：每个 A/B 档候选从 NCBI RefSeq/GTDB 取菌株级基因组。

**2.2 安全筛查**（填充 `strain_function_matrix` 的安全字段）：
- AMR 基因（CARD/ResFinder）→ `AMR_risk`
- 毒力因子（VFDB）→ `virulence_risk`
- 产毒/溶血、可转移元件
- 厌氧菌可培养性 / 工业可行性备注

**2.3 监管分级**：标注 LBP/QPS 状态，写入 `safety_categories`。

**交付**：NGP 安全卡；`safety_gate` 状态从 `pending_genome_safety` 更新为通过/排除。**未通过者不得进入推荐。**

---

## 阶段 3 — 机制与功能注释（3 周）

- 把 NGP 的功能模块映射到肥胖通路：丁酸/SCFA 产生、黏液降解（Akkermansia）、胆汁酸代谢、屏障完整性、ClpB-食欲信号（Hafnia）、琥珀酸→丙酸（Phascolarctobacterium）。
- 填 `strain_function_matrix`：`SCFA_potential`、`BSH_potential`、`mucin_adhesion_potential`、`anti_inflammatory_evidence`。
- 用于组合互补性评分（与现有食品级菌的 cross-feeding）。

**交付**：NGP 功能矩阵；NGP×益生菌互补组合的机制假设。

---

## 阶段 4 — 微生物组状态整合（4 周，高杠杆）

> 这是 NGP 最独特的价值点，也是连接已下载的 8304 样本级微生物组数据的地方。

**4.1 基线丰度刻画**：用 `curatedMetagenomicData` 数据计算 NGP（尤其 Akkermansia、Faecalibacterium、Christensenella）在肥胖 vs 瘦人群的基线丰度差异。

**4.2 应答者假设建模**：Depommier/MucT 都提示**基线 Akkermansia 丰度与应答相关**。建"基线微生物组状态 → 干预应答"特征，给连续效应量模型加入**人群微生物组协变量**——这正是目前模型缺的高信息量特征。

**交付**：NGP 基线丰度图谱；应答者特征；为效应量模型补充微生物组协变量。

---

## 阶段 5 — 建模与配方推荐（3 周）

- A/B 档 NGP 臂级效应量并入连续模型，按 stratum 重新评估是否优于基线。
- NGP-aware 配方推荐：**安全门通过**才纳入；标注 LBP 监管状态与给药形式（多为活菌/巴氏灭活）。
- 诚实验证：维持 `combination_ranking_enabled` 门控策略，不优于基线则不推。

**交付**：含 NGP 的候选菌评分与组合推荐；honest 验证报告。

---

## 关键风险与对策

| 风险 | 对策 |
|------|------|
| NGP 人体 RCT 稀少，多数仅临床前 | 严格分档；C 档不进推荐，只标假设 |
| 全文/补充表付费墙 | 用户提供 PDF（已验证可行）+ OA 优先 |
| 摘要只报 p 值无效应量 | 全文取数值，否则标 point-estimate |
| 安全/监管门槛高（LBP） | 安全门前置（阶段 2），未过不推 |
| 加数据仍不改"无信号"结论 | 微生物组协变量（阶段 4）是主要破局点，非单纯加样本 |

## 成功判据

1. ≥10 个 A/B 档 NGP 臂级 SE-bearing 数据点入库
2. 所有进入推荐的 NGP 通过基因组安全门
3. 基线微生物组协变量接入效应量模型并评估其增益
4. 至少 1 个 stratum 在加入 NGP + 微生物组特征后**真实**优于基线（若达不到，如实报告，不调参强凑）

---

## 与现有资产的衔接

- 菌种识别/特征：`enrichment.py TAXA_PATTERNS`、`tabpfn_benchmark.py _strain_family`（已扩）
- 证据筛选：`build_variance_rich_curation_queue.py`、NGP 队列已生成
- 全文策展：`.fulltext_extract/`、`apply_fulltext_extractions.py`、`build_fulltext_new_studies.py`
- 安全门：`strain_function_matrix`、`safety_gate`
- 微生物组数据：`scripts/data_download/fetch_curatedMetagenomicData.R`、`[[r-env-curatedmetagenomicdata]]`
- 连续模型：`run_continuous_effect_upgrade.ps1`、`[[continuous-effect-model]]`
