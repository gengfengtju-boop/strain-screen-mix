# Platform V1.0 Completed Results

| 模块 | 已完成数据 | 关键指标 | 当前结果 | 下一步 |
| --- | --- | --- | --- | --- |
| 肥胖微生态数据库 | 78 个检索/抽取队列；1097 条去重证据；659 条预测候选；930 行 high/medium outcome 复核池；样本级 `sample_metadata` 目前为 2 行示例数据 | 证据库规模；high/medium 覆盖；数据完整率；批次控制 | 已形成证据登记表、筛选表、抽取队列、预测候选表和人工复核工作包；样本级微生态矩阵仍处于 schema/template 与示例阶段 | 扩展中国人群样本；接入真实 `sample_metadata`、taxonomic/functional profile；建立批次校正和完整率报告 |
| OMS 模型 | 已定义 obesity microbiome score 所需目录、schema 和建模模块边界；当前无真实样本级训练集/验证集/外部测试集 | AUC、Accuracy、F1、leave-one-study-out validation | 阶段性结果：尚未训练 OMS 分类模型；真实 AUC/Accuracy/F1 暂无；已具备后续训练输入规范 | 接入样本级菌群矩阵；训练肥胖/非肥胖分类器；做外部验证和留一研究验证 |
| BMI 回归模型 | 已定义 BMI 回归模型目录与 `sample_metadata` schema；当前仅有 2 行清洗示例样本，无可训练真实样本集 | R²、MAE、RMSE | 阶段性结果：尚未训练 BMI 回归模型；真实 R²/MAE/RMSE 暂无 | 加入真实 BMI 样本、年龄、性别、地区、饮食、抗生素等临床协变量；训练并外部验证 |
| 响应人群模型 | 46 个结构化 study-endpoint 行；12 个 evidence-level 研究；659 条启发式预测候选；Top100/Top200 人工复核包已生成 | 响应预测 AUC、Average Precision、Brier score、解释特征 | study-endpoint 监督模型阶段性结果：AUC=0.971，Average Precision=0.935，Brier=0.060；模型层级为研究终点，不是个体 baseline microbiome responder | 完成 Top100/Top200 人工 outcome 抽取；扩大 extracted endpoint；加入个体基线菌群数据；前瞻验证 |
| 组合推荐模型 | 7 个候选菌株；7 个 formulation block；50 个 formulation-aware 3-5 菌株组合；50 个 model-response 组合排名 | Top 组合数量；clinical evidence score；combination design score；predicted response score | 已输出 50 个 3-5 菌株组合；已有基于 study-endpoint response probability 的组合重排版本；安全门仍为 pending genome safety gate | 补全菌株基因组安全门；体外功能验证；动物实验验证；根据人工复核结局更新组合评分 |

## Notes

- V1.0 当前强项是公开证据库、文献抽取队列、研究终点层级响应模型和组合推荐工作流。
- OMS 与 BMI 回归仍需要真实样本级 microbiome 矩阵，当前不能报告真实模型性能。
- 响应模型 AUC 来自结构化 study-endpoint rows，不应解读为个体响应预测 AUC。
