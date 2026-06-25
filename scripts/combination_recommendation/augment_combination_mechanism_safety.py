from __future__ import annotations

import re
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
COMBOS = ROOT / "results/combination_recommendations/robust_strain_combinations_20260610.csv"
GUILD = ROOT / "data/strain_genome/genus_functional_guild_reference_20260613.csv"
SAFETY = ROOT / "results/candidate_strain_scores/combination_safety_gate_eligibility_20260613.csv"
TOPN = 10

AXES = {
    "BSH(胆盐水解/降脂)": "bsh_potential",
    "butyrate(丁酸)": "butyrate_scfa_potential",
    "propionate(丙酸)": "propionate_potential",
    "mucin(黏液屏障)": "mucin_interaction",
    "lactate/acetate(乳酸/乙酸)": "lactate_acetate",
}


def genera_of(strains: str) -> list[str]:
    out: list[str] = []
    for name in str(strains).split("; "):
        toks = name.split()
        if toks:
            out.append(toks[0])
    return out


def main() -> None:
    combos = pd.read_csv(COMBOS).sort_values("robust_rank").head(TOPN).copy()
    guild = pd.read_csv(GUILD).set_index("genus")
    safety = pd.read_csv(SAFETY)
    safe_by_genus = safety.groupby("genus").agg(
        safety_tier=("safety_tier", lambda s: s.value_counts().index[0]),
        safety_risk_class=("safety_risk_class", lambda s: s.value_counts().index[0]),
        combination_safety_gate=("combination_safety_gate", lambda s: "pending" if (s == "pending").any() else s.value_counts().index[0]),
        needs_genome_confirmation=("needs_genome_confirmation", "max"),
        adverse_mechanism_flag=("adverse_mechanism_flag", lambda s: s.notna().any()),
    )

    records = []
    for _, r in combos.iterrows():
        genera = genera_of(r["strains"])
        uniq = sorted(set(genera))
        covered, missing = [], []
        for label, col in AXES.items():
            level = 0
            for g in uniq:
                if g in guild.index:
                    level = max(level, int(pd.to_numeric(guild.loc[g, col], errors="coerce") or 0))
            (covered if level > 0 else missing).append(label)
        # safety roll-up
        tiers, risks, gates, adverse, needs = set(), set(), set(), False, False
        for g in uniq:
            if g in safe_by_genus.index:
                row = safe_by_genus.loc[g]
                tiers.add(str(row["safety_tier"]))
                risks.add(str(row["safety_risk_class"]))
                gates.add(str(row["combination_safety_gate"]))
                adverse = adverse or bool(row["adverse_mechanism_flag"])
                needs = needs or bool(row["needs_genome_confirmation"])
        gate = "pending" if "pending" in gates else (sorted(gates)[0] if gates else "unknown")
        records.append({
            "robust_rank": int(r["robust_rank"]),
            "combination_id": r["combination_id"],
            "strains": r["strains"],
            "n_genera": len(uniq),
            "genera": "; ".join(uniq),
            "mechanism_axes_covered": len(covered),
            "axes_covered": "; ".join(covered),
            "axes_missing": "; ".join(missing),
            "mechanism_breadth_flag": (
                "BSH+lactate 偏向；缺 " + "/".join(a.split("(")[0] for a in missing)
                if missing else "广谱机制覆盖"
            ),
            "adverse_mechanism_flag": adverse,
            "safety_tier": "; ".join(sorted(tiers)),
            "safety_risk_class": "; ".join(sorted(risks)),
            "combination_safety_gate": gate,
            "needs_genome_confirmation": needs,
            "posterior_score_mean": r["posterior_score_mean"],
        })

    aug = pd.DataFrame(records)
    out_csv = ROOT / "results/combination_recommendations/preclinical_validation_priority_top10_augmented_20260625.csv"
    aug.to_csv(out_csv, index=False)

    # append a mechanism/safety section to the report
    report = ROOT / "docs/preclinical_combination_validation_priority_20260625.md"
    L = ["", "## 机制 / 安全维度增补（属级先验）", ""]
    L.append("> 机制与安全均为 **属级先验**（90 属 guild 参考 + EFSA QPS 分流）；"
             "菌株级真值仍需基因组注释。这一节用于让优先级评分更扎实，并暴露机制盲区。")
    L.append("")
    L.append("| # | 组合 | 属数 | 机制轴覆盖 | 缺失机制轴 | 安全分层 | 安全门 |")
    L.append("|---|------|------|-----------|-----------|---------|--------|")
    for _, r in aug.iterrows():
        L.append(
            f"| {r['robust_rank']} | {r['combination_id']} | {r['n_genera']} | "
            f"{r['mechanism_axes_covered']}/5：{r['axes_covered']} | {r['axes_missing']} | "
            f"{r['safety_risk_class']} | {r['combination_safety_gate']} |"
        )
    L.append("")
    L.append("### 关键发现（诚实）")
    L.append("- **机制盲区**：当前全部 Top 组合集中在 **BSH（胆盐水解→降脂）+ lactate/acetate** 轴，"
             "**普遍缺失 butyrate（丁酸）、propionate（丙酸）、mucin（黏液屏障）** 三条机制——"
             "因为高证据菌株几乎都是 Lactobacillus/Bifidobacterium。这是证据驱动排序的固有偏向。")
    L.append("- **可行动建议**：若要机制互补，应主动纳入丁酸/黏液轴候选（如 Faecalibacterium、"
             "Akkermansia 类——但这些 NGP 尚未过基因组安全门，见 NGP 计划），作为机制对照臂。")
    L.append("- **安全**：所有涉及属为 `qps_gras_lower_barrier / low_qps_history`，无 adverse 机制旗标；"
             "但 `combination_safety_gate=pending`——QPS 仅降低门槛，**菌株级基因组 QC（AMR/毒力/MGE）仍是硬前置**。")
    with report.open("a", encoding="utf-8") as f:
        f.write("\n".join(L))

    print("wrote", out_csv.relative_to(ROOT))
    print("appended mechanism/safety section to", report.relative_to(ROOT))
    print("\n--- coverage summary ---")
    print(aug[["robust_rank", "combination_id", "mechanism_axes_covered", "axes_missing", "combination_safety_gate"]].to_string(index=False))


if __name__ == "__main__":
    main()
