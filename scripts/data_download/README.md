# 数据获取模块

## 目标

登记和获取公开数据库中的人体肠道微生物组、干预研究、候选菌株基因组、微生物组-代谢组配对数据和文献证据。

## 输入

- 数据库配置：`config/database_config.yaml`
- 研究编号、样本编号、accession 清单
- 文献补充表格或手工登记表

## 输出

- 原始数据下载记录
- 数据来源登记表
- 样本与研究索引表

## 样本级微生物组数据获取（curatedMetagenomicData）

肥胖模型所需的样本级 species 丰度矩阵通过 R + Bioconductor `curatedMetagenomicData` 获取。

### 一次性安装依赖

```powershell
$R = 'C:\Program Files\R\R-4.6.0\bin\Rscript.exe'
& $R --vanilla scripts\data_download\install_r_deps.R   # CRAN + Bioc 依赖
& $R --vanilla scripts\data_download\install_cmd.R       # ExperimentHub + curatedMetagenomicData
```

注：本机无 Rtools，`AnnotationHub`/`ExperimentHub` 为纯 R 包，脚本会从 Bioconductor 源码 tar.gz 直接安装。

### 抓取数据

```powershell
& $R --vanilla scripts\data_download\fetch_curatedMetagenomicData.R "F:\strain screen mix" [max_studies]
```

- 第 2 个参数可限制研究数量（省略=全部 45 个研究 / 约 8308 样本）。
- 筛选条件：有 BMI + 粪便样本 + 肥胖/代谢病相关表型。
- 逐研究下载并重试，缓存于 `data/raw_data/cmd_cache/`，中断可续传。

### 输出

| 文件 | 内容 |
| --- | --- |
| `data/metadata/sample_metadata_raw.csv` | 样本元数据（项目标准 schema） |
| `data/taxonomic_profile/species_abundance_wide.csv` | 宽表（样本 × 物种，供建模） |
| `data/taxonomic_profile/species_abundance_long.csv` | 长表（taxonomic_profile schema） |

### 后续

```powershell
python -m proslim_ai validate-table sample_metadata data\metadata\sample_metadata_raw.csv
python -m proslim_ai clean-sample-metadata data\metadata\sample_metadata_raw.csv data\processed_data\sample_metadata_clean.csv
```

