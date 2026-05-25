# ProSlim-Microbiome-AI

基于公开数据库的益生菌减脂组合智能预测系统。

本项目的目标不是直接断言某个益生菌组合一定能减脂，而是建立一个分阶段、可扩展、可验证的 AI 建模系统，用于整合公开肠道微生物组、益生菌干预、候选菌株基因组、安全性注释和文献证据。

## 系统目标

1. 基于公开肠道微生物组数据库，识别肥胖相关菌群组成和功能通路特征。
2. 基于公开益生菌、合生元或饮食干预数据，预测不同人群对益生菌干预的响应概率。
3. 结合候选菌株基因组功能、安全性信息和目标人群菌群缺失特征，推荐具有减脂潜力的益生菌组合。

## 模块结构

| 模块 | 目录 | 目标 |
| --- | --- | --- |
| 数据获取 | `scripts/data_download` | 下载或登记公开数据库来源 |
| 元数据整理 | `scripts/metadata_cleaning` | 统一字段、单位、标签和缺失值规则 |
| 特征构建 | `scripts/feature_engineering` | 构建分类丰度、多样性、功能通路和机制派生特征 |
| 肥胖模型 | `scripts/obesity_model` | 训练 BMI 回归和肥胖状态分类模型 |
| 响应模型 | `scripts/responder_model` | 预测益生菌或合生元干预响应概率 |
| 菌株注释 | `scripts/strain_annotation` | 建立候选菌株安全性和功能矩阵 |
| 组合推荐 | `scripts/combination_recommendation` | 生成并排序 2-4 株益生菌组合 |
| 可视化 | `scripts/visualization` | 输出 SHAP、特征排名、功能覆盖和组合排序图 |
| 报告生成 | `scripts/report_generation` | 生成肥胖菌群状态、响应预测、菌株评分和组合推荐报告 |

## 推荐执行阶段

1. 基础数据库构建：形成 `sample_metadata_clean.csv`、丰度矩阵和标签表。
2. 肥胖状态预测：建立 BMI 预测、肥胖分类和 obesity microbiome score。
3. 干预数据整理：形成干预信息、临床结局变化和 responder 标签。
4. 响应预测建模：输出响应概率和响应人群特征。
5. 候选菌株矩阵：整合安全性、功能和文献证据。
6. 益生菌组合推荐：输出组合排序和验证优先级。
7. 实验验证设计：形成体外、细胞、动物和人体试验的数据反馈闭环。

## 核心验证原则

模型验证必须包含 `leave-one-study-out validation`。如果随机拆分表现良好但留一研究验证表现差，模型不能直接用于菌株组合推荐。

## 主要输出

- 肥胖菌群状态报告
- 益生菌响应预测报告
- 候选菌株评分报告
- 益生菌组合推荐报告

## 当前可执行入口

本仓库已经包含轻量级 Python CLI，用于检查项目结构、查看模块和生成标准 CSV 表头模板。

在未安装包的情况下，可从项目根目录运行：

```bash
PYTHONPATH=src python -m proslim_ai check
PYTHONPATH=src python -m proslim_ai modules
PYTHONPATH=src python -m proslim_ai write-templates
```

在 Windows PowerShell 中运行：

```powershell
$env:PYTHONPATH='src'
python -m proslim_ai check
python -m proslim_ai modules
python -m proslim_ai write-templates
```

如果后续安装为本地开发包，可运行：

```bash
pip install -e .
proslim-ai check
```

## 表头模板

标准化表头模板由 `config/table_schemas.yaml` 定义，可通过 CLI 写入：

```bash
python -m proslim_ai write-templates
```

默认输出到：

`data/metadata/templates/`
