# lipid stratum 诊断与修复结论（2026-06-13）

脚本 `scripts/obesity_model/lipid_substratify_experiment.py`。

## 问题
连续模型的 `lipid|mg/dL` stratum 留一验证 MAE≈41，远差于均值基线 MAE≈7.4 —— 过拟合假象，源于**把不可比的量混入同一 stratum**：

1. **单位混合**：mg/dL（7 研究）与 mmol/L（3 研究）被规范化函数错误合并（胆固醇差 38.7×、TG 差 88.6×）。
2. **脂质类型混合**：TC / LDL / HDL / TG 方向与量级各异（HDL 升为好，余降为好）同池。
3. **终点 vs 变化混合**：部分行是 week-8 绝对值（如 80.39 kg），被当作"变化量"。
4. **多脂质塞进一行**：抽取把一句多脂质（"TC… LDL… TG…"）压成单个 estimate。

## 按亚型拆分后的结果（单位归一到 mg/dL）

| 亚型 | 研究数 | 可建模? |
|---|---|---|
| TG | 7 | 名义可建模，但被污染 |
| LDL | 2 | 不足 |
| TC/unspecified | 1-2 | 不足 |

TG 的 estimates = [−28, −10.6, 0, **674**, −5, −18.6, 32.8] —— 含一个 **674 mg/dL** 的离群值（来自 PMID:40416368 把 7.61 mmol/L 终点又乘换算因子的连环误抽），且多脂质行被误归类。

## 确认的数据质量缺陷（待重抽）
- **PMID:40416368**：weight 行 estimate=−69.51 kg 实为 week-8 终点绝对值（80.39 vs 78.51 kg），非变化量；其 TG 行同样是终点误当变化。
- 系统性：`effect_unit` 含 "endpoint" 的行普遍把绝对终点当效应量；MAD 截断只挡掉部分。

## 诚实结论
**仅靠重新分层无法挽救 lipid。** 即使拆亚型，只有 TG 勉强达 n≥4，且被误抽污染；其余亚型样本不足。正确做法：
1. **lipid 标为 insufficient_data（按亚型）**，不再以单一 stratum 输出误导性模型。
2. **按脂质亚型逐一重抽**（每行一个 TC/LDL/HDL/TG，统一单位、区分变化 vs 终点）。
3. 修复确认的终点-当-变化误抽（PMID:40416368 等）。

→ 这是一次有价值的否定/纠错：暴露了抽取层的终点/单位/多脂质缺陷，优先级应高于继续堆数据。

## 已修复（2026-06-13）

### 1. endpoint-当-change 误抽（代码层，已修）
`arm_effects._effects_from_structured` 新增守卫：effect_unit 含 "endpoint" 时，从 source 两臂均值重算组间差（`_two_arm_endpoint_difference`）。修正 14 行（PMID:37111082 BMI 23.94→−0.61、weight 59.25→−1.72；PMID:40416368 weight −69.51→+1.88、lipid 674→0.07）。weight|kg MAE 1.742→1.527。测试 `test_endpoint_effect_difference_recomputed_from_source`。

### 2. 逐脂质亚型重抽（数据层，已做）
`scripts/obesity_model/lipid_resplit_extract.py` 把每行 source 按亚型拆成独立效应，mmol/L→mg/dL 归一，输出
`data/intervention_data/continuous_effect_sizes.lipid_subtyped_20260613.csv`（21 行 / 10 研究）。

| 亚型 | 研究数 | 组间差 (mg/dL) | 可建模 |
|---|---|---|---|
| TG | 7 | −28…+21.5（多数降）| ✅ |
| TC | 5 | −23.6,−17.2,−11.8,−10.6,+15.5 | ✅ |
| LDL | 5 | −18.2,−10.8,+0.1,+0.16,+14.3 | ✅ |
| HDL | 1 | −5.0 | 不足 |

**结果**：从 1 个无效的 pooled lipid|mg/dL（MAE 41）变成 **3 个尺度一致、物理可比的可建模亚型（TG/TC/LDL）**。数据现在有效。

**待办**：把 `lipid_subtype` 接入管线 stratum 键（让模型按 TG|mg/dL、TC|mg/dL、LDL|mg/dL 分别拟合），并为每个亚型行补 SE（多数 source 含 ±SD 或 p+n）。
