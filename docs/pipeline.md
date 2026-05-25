# 建模流程

## 1. 数据获取

输入公开数据库索引、研究编号、样本编号和下载路径，输出原始数据登记表与下载状态表。

优先数据源：

- curatedMetagenomicData
- GMrepo
- Qiita
- SRA / ENA
- MGnify
- NCBI Genome / RefSeq / GenBank
- Metabolomics Workbench / GNPS

## 2. 元数据整理

统一样本、受试者、研究、时间点、BMI、肥胖状态、干预剂量和周期。输出标准化长表。

## 3. 特征构建

构建以下矩阵：

- genus-level abundance matrix
- species-level abundance matrix
- pathway abundance matrix
- diversity features
- key taxa features
- SCFA functional score
- bile-acid functional score
- butyrate-producer score
- enterotype-related features

## 4. 肥胖状态预测

任务包括 BMI 回归、obesity vs lean 二分类、normal / overweight / obesity 多分类。

推荐模型：

- Elastic Net
- Random Forest
- XGBoost
- LightGBM

## 5. 益生菌响应预测

输入基线宿主变量、基线菌群变量、干预变量和队列变量，输出 weight / BMI / lipid / glucose / microbiome / composite response。

## 6. 菌株功能匹配

先执行 safety gate，再对 SCFA、胆汁酸、碳水化合物利用、生态位补充和文献证据进行评分。

## 7. 组合推荐

生成 2 菌、3 菌和 4 菌组合。所有菌株必须通过安全门槛，并至少覆盖两个功能模块。

## 8. 结果解释

输出 SHAP、feature importance、组合功能覆盖矩阵、目标人群匹配图和验证路线图。

