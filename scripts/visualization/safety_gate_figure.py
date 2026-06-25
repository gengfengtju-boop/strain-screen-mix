"""Figure: genome safety-gate status matrix for synergistic candidates."""
from __future__ import annotations
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import pandas as pd

plt.rcParams.update({"font.sans-serif": ["Microsoft YaHei", "SimHei"],
                     "axes.unicode_minus": False, "savefig.dpi": 300, "figure.dpi": 300})
ROOT = Path(__file__).resolve().parents[2]
G = "#2E8B57"; Y = "#E08A1E"; R = "#C0392B"; B = "#2C6FB0"; GREY = "#BDC3C7"


def main():
    d = pd.read_csv(ROOT / "results/candidate_strain_scores/synergistic_candidates_safety_gate_20260625.csv")
    order = {"moderate_lbp_precedent": 0, "moderate_novel_commensal": 1, "elevated_pathogen_or_amr_genus": 2}
    d = d.sort_values(["safety_risk_class", "mge_amr_prior"], key=lambda s: s.map(order).fillna(1) if s.name == "safety_risk_class" else s)
    d = d.reset_index(drop=True)[::-1].reset_index(drop=True)
    n = len(d)
    cols = ["安全风险类别", "MGE/可移动AMR", "基因组可得性", "安全门"]
    risk_c = {"moderate_lbp_precedent": G, "moderate_novel_commensal": Y, "elevated_pathogen_or_amr_genus": R}
    risk_t = {"moderate_lbp_precedent": "LBP人体前例", "moderate_novel_commensal": "新型共生·需筛", "elevated_pathogen_or_amr_genus": "致病/AMR属"}
    mge_c = {"low": G, "unknown": GREY, "moderate": Y, "elevated": R}
    mge_t = {"low": "低", "unknown": "未知", "moderate": "中", "elevated": "高(必查)"}

    fig, ax = plt.subplots(figsize=(10.4, 6.2))
    for i, r in d.iterrows():
        cells = [
            (risk_c[r["safety_risk_class"]], risk_t[r["safety_risk_class"]]),
            (mge_c.get(r["mge_amr_prior"], GREY), mge_t.get(r["mge_amr_prior"], r["mge_amr_prior"])),
            (B if r["real_screen_runnable"] else GREY, f"{int(r['ncbi_assemblies'])}+ 基因组" if r["ncbi_assemblies"] > 1 else "有基因组"),
            (G, "可进真版筛查"),
        ]
        for j, (c, t) in enumerate(cells):
            ax.add_patch(mpatches.FancyBboxPatch((j, i), 0.94, 0.86, boxstyle="round,pad=0.01,rounding_size=0.04",
                         fc=c, ec="white", lw=1.4, alpha=0.88))
            ax.text(j + 0.47, i + 0.43, t, ha="center", va="center", fontsize=8,
                    color="white" if c in (R, B, G) else "black")
    ax.set_yticks([i + 0.43 for i in range(n)])
    ax.set_yticklabels([s.replace("_", " ") for s in d["species"]], fontsize=8.8, fontstyle="italic")
    ax.set_xticks([j + 0.47 for j in range(4)]); ax.set_xticklabels(cols, fontsize=10)
    ax.xaxis.set_ticks_position("top"); ax.xaxis.set_label_position("top")
    ax.set_xlim(-0.05, 4); ax.set_ylim(-0.1, n)
    for sp in ax.spines.values(): sp.set_visible(False)
    ax.tick_params(length=0)
    ax.set_title("协同减脂候选菌的基因组安全门分流（知识先验 + 基因组可得性）\n"
                 "诚实：非真版 AMRFinder/VFDB 筛查；用于决定先筛谁与已知风险旗标", fontsize=11.5, fontweight="bold", pad=28)
    fig.savefig(ROOT / "results/paper_figures/fig14_safety_gate.png", bbox_inches="tight", facecolor="white")
    plt.close(fig); print("wrote fig14_safety_gate.png")


if __name__ == "__main__":
    main()
