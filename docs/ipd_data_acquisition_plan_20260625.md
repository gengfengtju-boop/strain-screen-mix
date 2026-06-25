# 个体级数据（IPD）获取计划与首轮搜寻结果（2026-06-25）

## 为什么是 IPD

聚合 RCT 数据在严格方法下无可复制疗效信号，且臂级均值丢失"谁应答"的个体异质性。
要做**真正的个体减脂应答模型**，唯一公开路径是：**做过测序沉积的干预 RCT**——
即每位受试者有「基线菌群 + 个体结局（ΔBMI/Δ体重/Δ体脂）」配对。这是当前项目最高杠杆、
也是最大瓶颈的一步。

## 搜寻方法（可复现）

脚本 `scripts/data_download/search_ipd_candidates.py`：

1. EuropePMC 检索干预型「益生菌/合生元 × 肥胖/超重 × 16S/宏基因组」试验（排除综述）。
2. 对每篇命中调用 EuropePMC **datalinks API**，提取沉积的测序登记号
   （BioProject `PRJNA/PRJEB/PRJDB`、SRA `SRP`、ENA `ERP`、GEO `GSE`）。
3. 仅保留有测序沉积的研究，输出三态分诊队列。

> **关键限制（诚实）**：有测序沉积 ≠ 每受试者基线+随访配对设计。每个候选仍需人工确认：
> （a）样本能按受试者配对基线与随访；（b）可恢复个体级肥胖结局。无沉积的研究无法从公开数据做 IPD。

## 首轮结果（screened=100）

- 有测序沉积候选：**7**；可解析登记号：**4**。
- 分诊：`human_candidate_review` 3 ｜ `animal_exclude` 3（家禽/啮齿）｜ `likely_preclinical_check` 1。

### 待人工复核的人源候选

| PMID | 年 | 登记号 | 说明 |
|------|----|--------|------|
| 41599863 | 2026 | （16S 已沉积，OA，登记号待全文取） | CKDB-322 = *L. plantarum* Q180 组合人体 RCT —— **最相关** |
| 42015200 | 2026 | PRJNA1416471 | *L. plantarum* 缓释肠溶配方研究 |
| 41377121 | 2025 | PRJNA1211859 | 低卡饮食肥胖人群（非益生菌，但人源配对菌群，可作方法学对照）|

产出：
- `data/ipd_search/ipd_candidate_studies_20260625.csv`
- `data/ipd_search/ipd_candidate_search_summary_20260625.json`

## 诚实结论

100 篇里仅 ~2-3 个真正可用的人源益生菌-肥胖 IPD 候选——**IPD 数据本身稀缺**，
这正是个体应答模型迟迟无法建立的根因，不是搜寻不力。

## ENA 配对核验结果（3 个人源候选，2026-06-25）

用 ENA Portal API 拉 run/sample 元数据后，3 个候选全部判明：

| 候选 | ENA 判定 | IPD 可用 |
|------|---------|----------|
| **PRJNA1211859**（PMID 41377121，人源低卡饮食）| `human gut metagenome`；**20 受试者中 19 个 w0+w6+w12 完整配对**；15 干预 / 5 对照 | ✅ **IPD 就绪**——但为**饮食非益生菌** → 作方法学 pilot |
| PRJNA1416471（PMID 42015200）| `mouse gut metagenome` | ❌ 鼠源，排除 |
| PMID 41599863（CKDB-322 益生菌 RCT）| 仅沉积菌株基因组 `CP073753`，无 per-subject reads | ❌ 无个体测序 |

**净结论**：首轮 **0 个益生菌 IPD 队列**，但拿到 **1 个完全配对的人源饮食-应答队列**（PRJNA1211859，
基线+2 随访、双臂）。它不能直接训益生菌应答模型，但可作**个体「基线菌群→ΔBMI/Δ体重」建模管线的 pilot**
（跑通预处理→留一受试者 CV→标志物），等真正的益生菌 IPD 到位即可复用。这再次量化了瓶颈：
**益生菌 RCT 极少沉积每受试者测序**。

## Pilot 可行性核验（PRJNA1211859）与建模脚手架

对这个唯一配对的人源队列做了硬核可行性核验：

| 维度 | 实情 | 影响 |
|------|------|------|
| 测序类型 | **16S 扩增子**（非 shotgun），59 run 合计 **~1.23 GB** | 可下载；但需 DADA2/QIIME2 出 ASV/属表，**不能用 MetaPhlAn** |
| 预处理工具 | 本机 **无** metaphlan/bowtie2/dada2/qiime2 | 16S→丰度表这一步当前环境跑不了 |
| MGnify 预分析 | **0** 条 | 无法绕过本地处理直接取丰度表 |
| 个体结局（ΔBMI/Δ体重）| **不在** ENA/BioSample 属性里（仅有 subject_id+timepoint+采样日期）| 标签需从论文补充材料取（OA，PMID 41377121），多半仅组级 |

**诚实结论**：当前环境**无法**端到端训练真 pilot——卡在「16S 无本地处理链」+「个体结局标签不在公开元数据」。
这与项目既有的"本环境做不了真版生信"边界一致。**未伪造任何模型结果。**

### 已交付的真实产物
- **样本清单**（可行、已存）：`data/ipd_search/PRJNA1211859_sample_manifest_20260625.csv`
  —— 59 run × (subject_id, arm, week, 采样日, fastq_ftp)，含 19 个 w0+w6+w12 配对受试者。
- **建模脚手架**（已测试）：`src/proslim_ai/individual_response.py` + `scripts/modeling/individual_response_pilot.py`
  —— 留一受试者 CV（回归/分类），诚实门控（min 12 受试者 + 越过均值/AUC≥0.65）。
  合成自检证明它**能识别植入信号、能拒绝纯噪声**（`results/prediction_results/individual_response_pilot.json`）。
  真实数据（丰度表 + 个体结局）一就位即可直接跑。

## 下一步

1. **扩大搜寻**：把 `MAX_PMIDS` 提到 300–500（后台跑），并对窄化的干预查询全量翻页。
2. **确认配对**：对 3 个人源候选，用 ENA Portal API 拉 `sample`/`run` 元数据，
   核验是否有 per-subject、baseline+post 两个时间点。
3. **结局恢复**：从全文/补充材料抽个体级 ΔBMI/Δ体重；缺则联系作者要补充个体数据。
4. **建模启动条件**：≥1 个确认的配对 IPD 队列即可起 pilot（基线菌群 → 个体应答，留一研究 CV）。
   在此之前，组合推荐继续以「临床前验证优先级」交付，疗效门保持关闭。
