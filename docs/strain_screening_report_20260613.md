# 减重候选菌株筛选报告

**项目**：ProSlim-Microbiome-AI　**日期**：2026-06-13　**版本**：v1（筛选库扩充 + 三步标注）

---

## 一、执行摘要

将候选菌株从 **~10 个临床验证菌** 扩充为 **223 个筛选候选**（益生菌 + 人源非致病菌），经基因组映射、安全分流、功能注释三步标注，蒸馏出 **79 个可落地优先候选**。其中首批 **26 个**（QPS/LBP 前例 + 完整基因组）可立即进入真实验室/生信筛查。

> **重要声明**：本报告的安全与功能标注为**分类学/比较基因组知识先验**，用于**分流与优先级排序**，**不替代**基因组级 AMR/毒力筛查与 de-novo 功能注释（见第七节边界）。除 5 个临床证据菌外，其余均为**筛选假设**，需实验验证。

---

## 二、背景与依据

旧候选库仅含在策展肥胖 RCT 中被测过的菌株（临床证据驱动），故数量少。本次构建**筛选库**（基因组/信号驱动）：
- 基础来源：肥胖分类模型（内部按研究分组 ROC-AUC 0.73）的 SHAP 物种签名——206 个 ≥10% 流行率的人源肠道菌，用于描述与肥胖状态的关联方向，尚未完成独立外部验证。
- 加入食品级益生菌（EFSA QPS 名单）。
- 优先保护型菌（肥胖中耗竭、SHAP 判为降低肥胖风险）——"恢复耗竭保护菌"假设。

---

## 三、方法（三步标注流水线）

| 步骤 | 工具/依据 | 输出 | provenance |
|---|---|---|---|
| 1 基因组映射 | NCBI Datasets API v2 | accession + assembly 级别 | 实测查询 |
| 2 安全分流 | EFSA QPS 名单 + 临床微生物学 | safety_risk_class + flags | **知识先验** |
| 3 功能注释 | 90 属代谢 guild 比较基因组 | SCFA/胆汁酸潜力 + 机制 + 不利标记 | **知识先验** |

脚本：`scripts/strain_annotation/{build_strain_screening_catalog,map_genomes_step1,safety_triage_step2,functional_annotation_step3}.py`

---

## 四、结果

### 4.1 筛选库构成（223）
| 类别 | 数量 |
|---|---|
| 人源共生菌 | 109 |
| 人源 NGP | 76 |
| 食品级益生菌 | 38 |

### 4.2 基因组覆盖
180/223 映射成功，**124 个 isolate 质量**（Complete/Chromosome）；41 个 MAG-only（未培养，不可作产品）；2 个网络失败可重试。

### 4.3 安全分层
| 风险类 | 数量 | 处置 |
|---|---|---|
| low_qps_history | 28 | 门槛低 |
| moderate_lbp_precedent | 5 | 有人体试验前例 |
| moderate_novel_commensal | 165 | 需基因组筛查 |
| elevated_pathogen_or_amr_genus | 25 | **排除/菌株级审查** |

### 4.4 功能（代谢 guild，223）
丙酸 58 · 乳酸 49 · 丁酸 35 · 黏液 31 · 多酚/equol 6 · 产甲烷 1 · 未表征 68。
**不利机制标记 4 个**（排除补充）：Desulfovibrio piger、Desulfovibrionaceae、Bilophila wadsworthia（H₂S 促炎）、Allisonella histaminiformans（组胺促炎——且为 SHAP 最肥胖相关物种，双重证据一致）。

### 4.5 整合优先清单（79）
满足：isolate 基因组 + 安全（非病原）+ 有利机制 + 非不利机制。
分层：B 保护型 35 · C 假设 25 · B 食品级 13 · A 临床 5 · C 病原审 1。
机制：乳酸 30 · 丙酸 30 · 黏液 16 · 丁酸 13。

---

## 五、首批筛查名单（26：QPS/LBP 前例 + 完整基因组）

### 5.1 LBP 前例人源菌（有人体试验先例，最优先）
| 菌种 | 基因组 | 机制 |
|---|---|---|
| Akkermansia muciniphila | GCF_009731575.1 | 黏液降解 + 丙酸 |
| Parabacteroides distasonis | GCF_018279895.1 | 丙酸 |
| Roseburia intestinalis | GCF_900537995.1 | 丁酸 |

### 5.2 食品级 QPS 益生菌（23）
Bifidobacterium longum/breve/animalis/adolescentis、Lactobacillus acidophilus/gasseri/helveticus/johnsonii/crispatus、Lacticaseibacillus rhamnosus/casei/paracasei、Lactiplantibacillus plantarum、Limosilactobacillus fermentum、Lactococcus lactis、Pediococcus acidilactici/pentosaceus、Bacillus subtilis/coagulans、Saccharomyces boulardii 等。

### 5.3 次批 NEW 人源候选（保护型 + 有利机制 + 完整基因组，需基因组安全确认）
Anaerostipes hadrus（丁酸）· Phascolarctobacterium faecium（丙酸）· Intestinimonas butyriciproducens（丁酸）· Parabacteroides goldsteinii（丙酸）· Bacteroides ovatus/thetaiotaomicron/xylanisolvens（丙酸+黏液）· Alistipes shahii · Blautia obeum/wexlerae。

---

## 六、产出文件索引

| 文件 | 内容 |
|---|---|
| `strain_screening_catalog_functional_20260613.csv` | **主表**（223 × 全部三步标注）|
| `screening_shortlist_ranked_20260613.csv` | 79 优先候选（排序）|
| `genus_functional_guild_reference_20260613.csv` | 90 属功能 guild 参考 |
| `strain_screening_catalog_{genomes,safety}_20260613.csv` | 步骤 1/2 中间产物 |

---

## 七、边界与局限（务必阅读）

1. **安全标注是 QPS/分类学先验**，无法检测菌株特异的 AMR 基因、可移动元件、毒力因子。所有非 QPS 类群标 `needs_genome_confirmation=True`。
2. **功能标注是属级比较基因组先验**，非 de-novo 基因组注释；同属不同菌株功能可异。
3. **41 个 MAG-only** 类群有基因组信息但无法作菌株产品。
4. 除 5 个临床证据菌外，**其余为筛选假设**——"肥胖中耗竭"是关联非因果，不证明补充有效。

---

## 八、下一步真实筛查 SOP（落地真版）

> 需一台可运行 conda/nextflow 生信流程的机器 + 联网下载基因组。

1. **下载基因组**：对 79 候选（或首批 26）按 accession 用 `datasets download genome accession <ACC>`。
2. **安全筛查（真版）**：
   - AMR：`AMRFinderPlus`（NCBI）或 `abricate --db card/resfinder`
   - 毒力：`abricate --db vfdb`
   - 可移动元件/质粒：`mobsuite` / `plasmidfinder`
   - 判据：无获得性 AMR、无质粒携带的可转移耐药、无毒力岛 → 通过安全门。
3. **功能注释（真版）**：
   - 基础注释：`prokka` / `bakta`
   - BSH：HMM/同源搜索 BSH（choloylglycine hydrolase）
   - SCFA 通路：KEGG 模块（butyryl-CoA:acetate CoA-transferase 等）
   - 次级胆汁酸：`bai` 操纵子检测
   - 次生代谢/细菌素：`antiSMASH` / `BAGEL`
4. **体外验证**：可培养性、产 SCFA 量、胆汁/酸耐受、黏附。
5. **进入推荐**：通过安全门 + 功能确认者，方可进入组合推荐（当前 `combination_ranking_enabled=false`，待应答模型信号或体外证据解锁）。

---

*本报告基于 2026-06-13 数据与模型。标注先验需基因组级确认后方可用于产品决策。*
