"""Definitive SINGLE-STRAIN fat-loss ranking for food-grade probiotics.

Consolidates the v3 method into a usable per-strain ranking. Two-level ordering:

  Level 1 (primary)   : v3 property score (six axes, no cohort data)
  Level 2 (tie-break) : cohort evidence tier, used only to order strains that are
                        tied on level 1 - it never moves a strain across score
                        tiers. 队列支持 > 受检但不显著 / 无数据 > 队列反证

The tie-break is necessary because the genus-level annotation gives identical v3
scores to whole groups (e.g. nine lactobacilli all score 0.7615); without it the
"ranking" would be nine-way ties. It is applied transparently and reported as a
separate column so the property score remains inspectable on its own.

Outputs a ranked table with an action recommendation per strain.
"""
from __future__ import annotations

import io
import json
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "results/combination_recommendations"

CN = {
    "Lacticaseibacillus_paracasei": "副干酪乳酪杆菌", "Lactiplantibacillus_plantarum": "植物乳植杆菌",
    "Lacticaseibacillus_rhamnosus": "鼠李糖乳酪杆菌", "Lacticaseibacillus_casei": "干酪乳酪杆菌",
    "Lactobacillus_acidophilus": "嗜酸乳杆菌", "Lactobacillus_gasseri": "格氏乳杆菌",
    "Lactobacillus_rogosae": "罗戈萨乳杆菌", "Lactobacillus_ruminis": "瘤胃乳杆菌",
    "Limosilactobacillus_reuteri": "罗伊氏黏液乳杆菌", "Lactobacillus_helveticus": "瑞士乳杆菌",
    "Lactobacillus_crispatus": "卷曲乳杆菌", "Lactobacillus_johnsonii": "约氏乳杆菌",
    "Limosilactobacillus_fermentum": "发酵黏液乳杆菌", "Bifidobacterium_breve": "短双歧杆菌",
    "Bifidobacterium_animalis": "动物双歧杆菌", "Bifidobacterium_longum": "长双歧杆菌",
    "Bifidobacterium_catenulatum": "链状双歧杆菌", "Bifidobacterium_adolescentis": "青春双歧杆菌",
    "Bifidobacterium_bifidum": "两歧双歧杆菌", "Bifidobacterium_pseudocatenulatum": "假链状双歧杆菌",
    "Bifidobacterium_dentium": "齿双歧杆菌", "Lactococcus_lactis": "乳酸乳球菌",
    "Pediococcus_acidilactici": "乳酸片球菌", "Pediococcus_pentosaceus": "戊糖片球菌",
    "Bacillus_coagulans": "凝结芽孢杆菌", "Bacillus_subtilis": "枯草芽孢杆菌",
    "Saccharomyces_boulardii": "布拉氏酵母", "Streptococcus_salivarius": "唾液链球菌",
    "Streptococcus_parasanguinis": "副血链球菌", "Streptococcus_australis": "澳大利亚链球菌",
    "Streptococcus_vestibularis": "前庭链球菌", "Streptococcus_gordonii": "戈氏链球菌",
    "Streptococcus_thermophilus": "嗜热链球菌", "Streptococcus_mitis": "缓症链球菌",
    "Streptococcus_oralis": "口腔链球菌", "Streptococcus_anginosus_group": "咽峡炎链球菌群",
    "Streptococcus_sanguinis": "血链球菌", "Streptococcus_sp_A12": "链球菌 sp. A12",
}
EVID_RANK = {"队列支持：瘦人富集": 0, "队列受检但不显著": 1, "队列无数据（不可得）": 1,
             "队列反证：肥胖富集": 2}


def recommend(r):
    if r.safety < 0.5:
        return "不推荐：需菌株级安全审查（病原属）"
    if r.cohort_flag == "队列反证：肥胖富集":
        return "慎用：队列反证，需人群验证后再定位"
    if r.cohort_flag == "队列支持：瘦人富集" and r.clinical >= 1.0:
        return "首选：性质优 + 临床先例 + 队列支持"
    if r.cohort_flag == "队列支持：瘦人富集":
        return "值得关注：队列支持强，但缺临床先例"
    if r.clinical >= 1.0:
        return "推荐：性质优 + 临床先例（缺队列证据）"
    if r.v3_score >= 0.70:
        return "备选：性质优，但仅筛选级证据"
    return "低优先：关键性质缺失"


def main():
    F = pd.read_csv(OUT / "foodgrade_v3_strain_scores_20260625.csv")
    F["中文名"] = F.species.map(CN).fillna(F.species.str.replace("_", " "))
    F["证据层级"] = F.cohort_flag.map(EVID_RANK).fillna(1).astype(int)
    F["推荐意见"] = F.apply(recommend, axis=1)

    # level-1 tier by score, level-2 ordering by evidence
    F = F.sort_values(["v3_score", "证据层级", "species"], ascending=[False, True, True]).reset_index(drop=True)
    F["同分组"] = (F.v3_score != F.v3_score.shift()).cumsum()
    F["排名"] = range(1, len(F) + 1)

    keep = ["排名", "同分组", "species", "中文名", "v3_score", "cross_feeding", "bile_acid",
            "safety", "clinical", "industrial", "obesity_signature",
            "cohort_flag", "cohort_detail", "推荐意见", "genus", "priority_tier"]
    R = F[keep].rename(columns={
        "species": "物种(拉丁名)", "v3_score": "v3性质分", "cross_feeding": "交叉喂养",
        "bile_acid": "BSH胆汁酸", "safety": "安全等级", "clinical": "临床证据",
        "industrial": "工业可行", "obesity_signature": "肥胖特征惩罚",
        "cohort_flag": "队列证据", "cohort_detail": "队列详情", "genus": "属",
        "priority_tier": "目录优先层级"})
    R.to_csv(OUT / "foodgrade_single_strain_ranking_20260625.csv", index=False, encoding="utf-8-sig")

    print(f"=== 食源菌单菌减脂预测排序（{len(R)} 株）===\n")
    print(f"{'排名':>3} {'组':>3} {'菌种':22}{'v3分':>7} {'队列证据':16} 推荐意见")
    for r in R.itertuples():
        print(f"{r.排名:>3} {r.同分组:>3} {r.中文名[:21]:22}{r.v3性质分:>7.3f} {r.队列证据:16} {r.推荐意见}")

    tiers = F.groupby("同分组").agg(分数=("v3_score", "first"), 株数=("species", "size")).reset_index()
    print("\n=== 同分组结构（属级注释导致的并列） ===")
    for r in tiers.itertuples():
        print(f"  组{int(r.同分组)}: {r.分数:.4f} — {int(r.株数)} 株")

    print("\n=== 推荐意见分布 ===")
    print(F["推荐意见"].value_counts().to_string())

    io.open(OUT / "foodgrade_single_strain_ranking_summary_20260625.json", "w", encoding="utf-8").write(
        json.dumps({
            "method": "v3 property score (primary) + cohort evidence tier (tie-break only)",
            "n_strains": int(len(F)),
            "n_score_tiers": int(F.同分组.nunique()),
            "largest_tie_group": int(F.groupby("同分组").size().max()),
            "top5": R.head(5)[["排名", "中文名", "v3性质分", "队列证据", "推荐意见"]].to_dict("records"),
            "recommendation_counts": F["推荐意见"].value_counts().to_dict(),
            "limitation": "genus-level annotation creates large ties; strain-level genomes and in vitro phenotypes are required for a true per-strain ranking",
        }, indent=2, ensure_ascii=False))
    print("\nwrote", (OUT / "foodgrade_single_strain_ranking_20260625.csv").relative_to(ROOT))


if __name__ == "__main__":
    main()
