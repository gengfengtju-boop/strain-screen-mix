"""Standalone Excel workbook for the food-grade probiotic prediction study."""
from __future__ import annotations

import io
import json
from pathlib import Path

import pandas as pd
from openpyxl.styles import Alignment, Font, PatternFill

ROOT = Path(__file__).resolve().parents[2]
CR = ROOT / "results/combination_recommendations"
OUT = ROOT / "docs/食源性益生菌预测_完整数据_20260625.xlsx"

J = lambda p: json.load(io.open(p, encoding="utf-8"))
S3 = J(CR / "foodgrade_v3_summary_20260625.json")
SR = J(CR / "foodgrade_single_strain_ranking_summary_20260625.json")

FILL = {"首选": "C6E7D0", "推荐": "CFDEF3", "值得关注": "E2D5EF",
        "备选": "FDE9D0", "低优先": "EDEDED", "慎用": "F8D9C0", "不推荐": "F5C6C6"}


def main():
    sh: dict[str, pd.DataFrame] = {}

    sh["00_说明"] = pd.DataFrame({
        "工作表": ["01_研究摘要", "02_方法与权重依据", "03_单菌排序总表", "04_分档结构",
                "05_推荐分类", "06_队列证据明细", "07_组合评分", "08_被排除菌株", "09_局限与行动建议"],
        "内容": ["核心指标一览", "六维评分公式、判据来源与证据强度", "38 株完整排序（含各维度分值）",
               "10 个分数档与并列情况", "按推荐意见分组的菌株清单", "有队列证据的菌株及倍数变化",
               "2–4 株组合评分（前 200）", "15 株排除名单及原因", "方法局限与优先级建议"]})

    sh["01_研究摘要"] = pd.DataFrame({
        "指标": ["评价对象", "菌株总数", "分数档数", "最大并列组", "可建组合池", "被排除株数",
               "候选组合总数", "—— 关键结果 ——", "性质分最高", "推荐首选",
               "最强队列信号", "队列反证菌株", "不推荐菌株",
               "—— 组合 ——", "全局最优组合", "推荐组合"],
        "内容": ["食源性益生菌（食品级，可直接用于产品）", SR["n_strains"], SR["n_score_tiers"],
               f'{SR["largest_tie_group"]} 株（链球菌属）', S3["buildable_pool"], S3["excluded"],
               f'{S3["n_combinations"]:,}', "",
               "副干酪乳酪杆菌 / 植物乳植杆菌（v3=0.866，但队列无数据）",
               "动物双歧杆菌 / 长双歧杆菌（v3=0.749，西欧 FC 0.62 / 0.65）",
               "链状双歧杆菌（中东 FC=0.48，全部食源菌最强）",
               "短/青春/两歧/假链状双歧杆菌（北美 FC 3.15–7.39）",
               "链球菌属 11 株（安全等级 0.25）", "",
               "副干酪乳酪杆菌 + 植物乳植杆菌（0.9035）",
               "副干酪乳酪杆菌 + 植物乳植杆菌 + 动物双歧杆菌（0.8754）"]})

    sh["02_方法与权重依据"] = pd.DataFrame({
        "维度": ["交叉喂养供能", "BSH 胆汁酸调节", "安全等级", "临床证据", "工业可行性",
               "肥胖特征惩罚", "—— 排序规则 ——", "第一级（主）", "第二级（仅打破同分）",
               "—— 组合评分 ——", "综合分公式", "组合池限制"],
        "权重": [0.22, 0.15, 0.22, 0.15, 0.14, -0.12, "", "v3 性质分", "队列证据层级", "",
               "0.72×平均v3 + 0.18×互补度 + 0.10×属多样性", "排除需安全审查者与队列反证者"],
        "取值方式": ["乳酸/乙酸产生潜能 ÷ 2", "BSH 潜能 ÷ 2（0/1/2 → 0/0.5/1.0）",
                 "QPS/GRAS=1.0；需菌株级审查=0.25", "有人体试验先例=1.0；仅筛选级=0.35",
                 "芽孢杆菌1.00/酵母0.95/乳杆菌0.85–0.90/链球菌0.75/双歧杆菌0.60",
                 "0.6×口腔来源 + 0.4×糖降解主导", "", "决定所属分数档",
                 "支持 > 不显著/无数据 > 反证；不跨档移动", "",
                 "互补度奖励：含强BSH + 含强交叉喂养 + 跨≥2属", "—"],
        "判据来源": ["瘦人菌群为协作型生态（多样性关联 AUC 0.920，跨属泛化 0.878）；食源菌产酸可喂养常驻丁酸/丙酸菌",
                 "BSH 不能预测常驻菌瘦人富集（AUC 0.517, P=0.85, 跨属 0.027），但对外源补充乳杆菌降胆固醇有文献支持",
                 "EFSA QPS 名录 + 临床微生物学", "自下而上筛选目录标注",
                 "发酵与冻干稳定性工程先验",
                 "西欧队列验证：口腔链球菌属肥胖富集；肥胖者半乳糖/水苏糖/肌醇降解通路增强",
                 "", "六维加权和", "队列数据不进入评分，仅作旗标", "", "—", "—"],
        "证据强度": ["⚠ 机制假设，未针对减脂结局验证", "文献支持；本项目血脂数据仅6行不足以自证",
                 "监管框架，明确", "目录标注，明确", "⚠ 工程先验，非减脂证据",
                 "有队列验证支撑", "", "—", "—", "", "—", "—"]})

    R = pd.read_csv(CR / "foodgrade_single_strain_ranking_20260625.csv")
    R["推荐类别"] = R["推荐意见"].str.split("：").str[0]
    sh["03_单菌排序总表"] = R
    sh["04_分档结构"] = R.groupby("同分组").agg(
        v3分=("v3性质分", "first"), 株数=("物种(拉丁名)", "size"),
        菌株=("中文名", lambda s: "、".join(s))).reset_index()
    rows = []
    for k in ["首选", "推荐", "值得关注", "备选", "低优先", "慎用", "不推荐"]:
        sub = R[R.推荐类别 == k]
        if len(sub):
            rows.append({"推荐类别": k, "株数": len(sub),
                         "菌株": "、".join(sub.中文名),
                         "说明": sub.推荐意见.iloc[0]})
    sh["05_推荐分类"] = pd.DataFrame(rows)
    ev = R[R.队列证据.isin(["队列支持：瘦人富集", "队列反证：肥胖富集"])][
        ["排名", "中文名", "物种(拉丁名)", "v3性质分", "队列证据", "队列详情", "推荐意见"]]
    sh["06_队列证据明细"] = ev.sort_values("队列证据")
    Cb = pd.read_csv(CR / "foodgrade_v3_combinations_20260625.csv").head(200)
    Cb.columns = ["排名", "组合成员", "株数", "平均v3", "含强BSH", "含强交叉喂养",
                  "属数", "临床证据成员", "队列支持成员", "组合综合分"]
    sh["07_组合评分"] = Cb
    F = pd.read_csv(CR / "foodgrade_v3_strain_scores_20260625.csv")
    ex = F[(F.safety < 0.5) | (F.cohort_flag == "队列反证：肥胖富集")].copy()
    ex["排除原因"] = ex.apply(lambda r: " / ".join(
        ([f"需菌株级安全审查（{r.genus} 属含病原种）"] if r.safety < 0.5 else [])
        + ([f"队列反证：{r.cohort_detail}"] if r.cohort_flag == "队列反证：肥胖富集" else [])), axis=1)
    sh["08_被排除菌株"] = ex[["species", "genus", "v3_score", "safety", "cohort_flag",
                          "cohort_detail", "排除原因"]].rename(columns={
        "species": "物种(拉丁名)", "genus": "属", "v3_score": "v3性质分",
        "safety": "安全等级", "cohort_flag": "队列证据", "cohort_detail": "队列详情"})
    sh["09_局限与行动建议"] = pd.DataFrame({
        "类别": ["局限"] * 6 + ["行动建议"] * 6,
        "序号": [1, 2, 3, 4, 5, 6, 1, 2, 3, 4, "—", "—"],
        "内容": [
            "属级注释造成大规模并列：9 株乳杆菌同分 0.7615，11 株链球菌同分 0.3125，无法在属内区分",
            "权重最大的两维度证据最弱：交叉喂养 0.22 为机制假设，工业可行 0.14 为工程先验，均未验证减脂结局",
            "BSH 权重来自文献而非本项目数据（可关联血脂结局仅 6 行）",
            "交叉喂养假设需体外共培养实验验证（能否提升常驻产酸菌产酸量）",
            "队列证据有地区异质性：同属菌在不同地区方向可相反，标签不可全球通用",
            "本排序为候选定标而非疗效预测，落地须经体外→动物→人体 RCT",
            "动物双歧杆菌、长双歧杆菌：直接进入体外与动物减脂验证（三重支持齐备）",
            "副干酪乳酪杆菌、植物乳植杆菌：补人群菌群关联或小样本 RCT，填补队列证据空缺",
            "链状双歧杆菌：补临床先例；其队列信号为食源菌中最强",
            "9 株乳杆菌：先做菌株级表型测定（BSH活性、产酸量、耐受性）破除并列",
            "4 株北美反证双歧杆菌：该市场慎用，如需使用先做人群验证",
            "链球菌属 11 株：除已通过菌株级安全评估者外，不进入减脂配方"]})

    with pd.ExcelWriter(OUT, engine="openpyxl") as w:
        for name, df in sh.items():
            df.to_excel(w, sheet_name=name, index=False)
        hf = Font(bold=True, color="FFFFFF"); hfill = PatternFill("solid", fgColor="2C6FB0")
        for ws in w.book.worksheets:
            for cc in ws[1]:
                cc.font = hf; cc.fill = hfill
                cc.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
            ws.freeze_panes = "A2"
            for col in ws.columns:
                ln = max((len(str(x.value)) if x.value is not None else 0) for x in col)
                ws.column_dimensions[col[0].column_letter].width = min(max(ln + 2, 10), 56)
        # colour-code the ranking sheet by recommendation
        ws = w.book["03_单菌排序总表"]
        hdr = [c.value for c in ws[1]]
        ci = hdr.index("推荐类别") + 1
        for r in range(2, ws.max_row + 1):
            k = ws.cell(r, ci).value
            if k in FILL:
                f = PatternFill("solid", fgColor=FILL[k])
                for c in range(1, ws.max_column + 1):
                    ws.cell(r, c).fill = f
    print("wrote", OUT)
    for name, df in sh.items():
        print(f"  {name}: {len(df)} 行")


if __name__ == "__main__":
    main()
