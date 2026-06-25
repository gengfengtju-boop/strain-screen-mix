from __future__ import annotations

from datetime import date
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "results/combination_recommendations/robust_strain_combinations_20260610.csv"
TOPN = 10


def fmt(s: object) -> str:
    return ", ".join(str(s).split("; ")) if pd.notna(s) else ""


def main() -> None:
    df = pd.read_csv(SOURCE).sort_values("robust_rank")
    top = df.head(TOPN).copy()

    keep = [
        "robust_rank", "combination_id", "strains", "total_strain_count",
        "evidence_pmid_list", "functional_modules", "posterior_score_mean",
        "posterior_score_p10", "posterior_score_p90", "upper_confidence_bound",
        "uncertainty_width", "top10_probability", "module_coverage_score",
        "genus_diversity_score", "pareto_front", "active_learning_batch",
        "safety_gate", "recommended_prebiotic", "validation_recommendation",
        "prediction_scope",
    ]
    out_csv = ROOT / "results/combination_recommendations/preclinical_validation_priority_top10_20260625.csv"
    top[keep].to_csv(out_csv, index=False)

    L: list[str] = []
    L.append("# 临床前验证优先级清单 — Top 10 益生菌组合")
    L.append("")
    L.append(
        f"运行日期 {date.today().isoformat()} · 来源 "
        f"`robust_strain_combinations_20260610.csv` · 共 {len(df)} 个候选组合"
    )
    L.append("")
    L.append("> ⚠️ **范围声明（必须保留）**")
    L.append("> 本清单是 **临床前验证优先级**，不是减脂疗效或个体响应概率预测。")
    L.append("> 排序依据 = 证据综合（锚定 PMID）+ 机制互补 + 配方完整性 + 属多样性 + 安全分流。")
    L.append("> `combination_ranking_enabled=false`（疗效门关闭）；所有组合 `safety_gate=pending_genome_safety_gate`")
    L.append("> ——进入任何实验前必须先完成菌株级基因组 AMR/毒力/MGE 筛查。")
    L.append("")
    L.append("## 评分口径")
    L.append("- **posterior_score_mean [p10, p90]**：证据-机制后验综合分及其 bootstrap 不确定区间。")
    L.append("- **UCB**：上置信界，用于主动学习探索排序。**top10_probability**：该组合落入前 10 的后验概率。")
    L.append("- **module_coverage / genus_diversity**：机制模块覆盖、属级多样性（各 0–10）。")
    L.append("- **pareto_front=yes**：在高证据 / 低复杂度 / 广覆盖上为帕累托最优。")
    L.append("")
    L.append("## 组合明细")
    for _, r in top.iterrows():
        L.append("")
        L.append(f"### #{int(r['robust_rank'])} · {r['combination_id']} （{int(r['total_strain_count'])} 株）")
        L.append("")
        L.append("**菌株**：" + "；".join(str(r["strains"]).split("; ")))
        L.append("")
        L.append(
            f"- 后验综合分 **{r['posterior_score_mean']:.2f}** "
            f"[p10 {r['posterior_score_p10']:.2f}, p90 {r['posterior_score_p90']:.2f}] · "
            f"UCB {r['upper_confidence_bound']:.2f} · 不确定宽度 {r['uncertainty_width']:.2f}"
        )
        L.append(
            f"- top10 概率 {r['top10_probability']:.2f} · 机制覆盖 "
            f"{r['module_coverage_score']:.0f}/10 · 属多样性 {r['genus_diversity_score']:.0f}/10 · "
            f"帕累托 {r['pareto_front']}"
        )
        L.append(f"- 锚定证据 PMID：{r['evidence_pmid_list']}")
        L.append(f"- 覆盖机制模块：{fmt(r['functional_modules'])}")
        L.append(f"- 推荐益生元：{r['recommended_prebiotic']}")
        L.append(f"- 安全门：`{r['safety_gate']}` · 验证建议：{r['validation_recommendation']}")
    L.append("")
    L.append("## 下一步硬门控（进入体外/动物/人体验证前）")
    L.append("1. 菌株级基因组下载 + AMR（AMRFinderPlus/CARD）、毒力（VFDB）、可移动元件（MGE）筛查。")
    L.append("2. 通过 EFSA QPS / LBP 前例核对每株安全分层。")
    L.append("3. 体外 SCFA / 胆盐水解酶（BSH）/ 黏附功能确认机制假设。")
    L.append("4. **疗效仍需前瞻 RCT 或个体级 IPD**——本清单只决定先验证谁，不替代疗效证据。")

    out_md = ROOT / "docs/preclinical_combination_validation_priority_20260625.md"
    out_md.write_text("\n".join(L), encoding="utf-8")
    print("wrote", out_md.relative_to(ROOT))
    print("wrote", out_csv.relative_to(ROOT))


if __name__ == "__main__":
    main()
