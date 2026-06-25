# PRJEB81868 个体应答 pilot — 数据准备说明

**研究**：Whole Fiber study（PMID 40669445），菊苣纤维 RCT，T2D/肥胖人群，荷兰。
**为什么选它**：当前唯一"结局对口（减脂/代谢）+ 配对设计 + 含 shotgun WGS"的公开队列。
shotgun 可直接 **MetaPhlAn**，绕过 16S 的 DADA2/QIIME2 瓶颈。

## 本目录产物（脚本 `scripts/data_download/prepare_ipd_pilot_PRJEB81868.py` 生成）

- `PRJEB81868_wgs_download_manifest.csv` — **105 个 WGS run** 的 fastq 下载地址 + 大小（真实可用）。
- `PRJEB81868_subject_outcome_template.csv` — 按 run 列出的**配对+结局模板**，待从论文补充材料填。

## 两个硬前置（诚实）

1. **算力 / 体量**：105 个 WGS 合计 **~392 GB**。下载 + 每样本 MetaPhlAn + 合并物种表
   需要一台能跑生信流程的服务器（conda + bowtie2 + MetaPhlAn DB），**本机做不了**。
2. **配对与结局只在论文里**：已核验 ENA/BioSample **不含** subject id / timepoint / arm / 体重 / BMI
   （别名 `2023_0027_####` 仅是 年_批次_样本序号，不自带受试者或访视）。
   sample→subject→timepoint→arm 映射与个体减脂结局**必须从 PMID 40669445 补充材料取**，填进模板。

## 端到端流程（算力到位后）

```
# 1. 下载（用 enaBrowserTools 或 aria2，按 manifest 的 fastq_ftp）
#    enaDataGet -f fastq <run_accession>   # 105 个 run, ~392 GB

# 2. 每样本物种谱
#    metaphlan <run>_1.fastq.gz,<run>_2.fastq.gz --input_type fastq -o <run>.profile.tsv
#    merge_metaphlan_tables.py *.profile.tsv > PRJEB81868_species_table.tsv

# 3. 填结局模板（从 PMID 40669445 补充材料）：subject_id / arm / timepoint / weight / bmi

# 4. 构造建模输入并跑已就绪的 LOSO 脚手架：
#    - profiles = 各受试者【基线时间点】的物种丰度（subjects x species）
#    - outcomes = 各受试者 Δweight 或 ΔBMI（baseline→endpoint）
#    python scripts/modeling/individual_response_pilot.py \
#        --profiles data/ipd_pilot/PRJEB81868_baseline_species.csv \
#        --outcomes data/ipd_pilot/PRJEB81868_subject_outcomes.csv --task regression
```

## 诚实定位

这是**减脂益生菌 IPD 到位前的方法学 pilot**（菊苣纤维≠益生菌）。
它验证"个体基线菌群 → 个体减脂应答"的建模管线本身能否工作（留一受试者 CV、越过均值基线）。
管线（`src/proslim_ai/individual_response.py`）已写好并通过合成自检；缺的只是上面两个前置。
组合推荐在此期间继续以「临床前验证优先级」交付，疗效门保持关闭。
