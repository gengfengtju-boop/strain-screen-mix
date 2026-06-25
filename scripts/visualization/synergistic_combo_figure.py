"""Figure: top synergistic lean-enriched fat-loss combinations (dimension breakdown)."""
from __future__ import annotations
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

plt.rcParams.update({"font.sans-serif": ["Microsoft YaHei", "SimHei"],
                     "axes.unicode_minus": False, "savefig.dpi": 300, "figure.dpi": 300,
                     "axes.spines.top": False, "axes.spines.right": False})
ROOT = Path(__file__).resolve().parents[2]
PR = ROOT / "results/prediction_results"


def short(members):
    abbr = []
    for m in members.split("; "):
        g, *rest = m.split("_")
        abbr.append(f"{g[0]}. {rest[0] if rest else ''}")
    return " + ".join(abbr)


def main():
    df = pd.read_csv(PR / "synergistic_lean_combinations_20260625.csv").head(6).iloc[::-1]
    dims = ["synergy", "fat_loss", "cholesterol", "strain_quality"]
    labels = ["协同(机制互补)", "减脂潜力", "降胆固醇(BSH)", "菌株性质(可培养)"]
    colors = ["#7D5BA6", "#2E8B57", "#E08A1E", "#2C6FB0"]
    y = np.arange(len(df)); h = 0.18
    fig, ax = plt.subplots(figsize=(10.2, 6.0))
    for k, (d, lab, c) in enumerate(zip(dims, labels, colors)):
        ax.barh(y + (k - 1.5) * h, df[d], height=h, color=c, edgecolor="black", lw=0.3, label=lab)
    ax.set_yticks(y)
    ax.set_yticklabels([f"#{int(r['rank'])}（{int(r['n_strains'])}株, 轴{int(r['n_axes_covered'])}/4）\n{short(r['members'])}"
                        for _, r in df.iterrows()], fontsize=8.2)
    for yi, (_, r) in zip(y, df.iterrows()):
        ax.text(1.005, yi, f"综合 {r['composite']:.3f}", va="center", fontsize=9, fontweight="bold")
    ax.set_xlim(0, 1.0); ax.set_xlabel("各维度得分（0–1）")
    ax.set_title("具有协同减脂潜力的菌株组合（数据驱动·Top 6）\n"
                 "预测依据：成员均为瘦人(无胰岛素抵抗)富集菌（≥11/15 研究方向一致）",
                 fontsize=12.5, fontweight="bold")
    ax.legend(loc="lower right", fontsize=8.6, ncol=2, frameon=True)
    ax.margins(y=0.04)
    fig.savefig(PR.parent / "paper_figures/fig13_synergistic_combos.png",
                bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print("wrote results/paper_figures/fig13_synergistic_combos.png")


if __name__ == "__main__":
    main()
