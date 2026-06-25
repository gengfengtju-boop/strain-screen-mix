"""Figure: lean(no-IR) vs obese differential gut abundance (study-aware)."""
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
GREEN, RED = "#2E8B57", "#C0392B"


def main():
    r = pd.read_csv(ROOT / "results/prediction_results/lean_vs_obese_differential_abundance_20260625.csv")
    r = r[r["consistency"] >= 0.70]
    top = r.reindex(r["abs_median_diff_pp"].sort_values(ascending=False).index).head(14).copy()
    top = top.sort_values("median_abund_diff_pp")
    y = np.arange(len(top))
    colors = [GREEN if d > 0 else RED for d in top["median_abund_diff_pp"]]

    import matplotlib.patches as mpatches
    fig, ax = plt.subplots(figsize=(9.6, 6.4))
    ax.barh(y, top["median_abund_diff_pp"], color=colors, edgecolor="black", lw=0.5, height=0.66)
    ax.axvline(0, color="black", lw=0.9)
    for yi, (_, row) in zip(y, top.iterrows()):
        d = row["median_abund_diff_pp"]
        txt = f"{d:+.2f}pp (d={row['pooled_cohens_d']:+.2f}, {row['studies_consistent']}/15)"
        ax.text(d + (0.05 if d > 0 else -0.05), yi, txt,
                va="center", ha="left" if d > 0 else "right", fontsize=7.8)
    ax.set_yticks(y)
    ax.set_yticklabels([s.replace("_", " ") for s in top["species"]], fontsize=9.4,
                       fontstyle="italic")
    ax.set_xlim(-4.0, 1.6)
    ax.set_xlabel("瘦人(无胰岛素抵抗) − 胖人  中位相对丰度差（百分点）")
    ax.set_title("瘦人(无胰岛素抵抗) vs 胖人 肠道菌差异丰度 Top 物种\n"
                 "（15 研究内求差 → 跨研究中位聚合，方向一致 ≥11/15）",
                 fontsize=12.5, fontweight="bold")
    ax.legend(handles=[mpatches.Patch(color=GREEN, label="瘦人富集（减脂恢复候选）"),
                       mpatches.Patch(color=RED, label="胖人富集（应抑制）")],
              loc="upper left", fontsize=9.5, frameon=True)
    out = ROOT / "results/paper_figures/fig10_lean_vs_obese_diffabund.png"
    fig.savefig(out, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print("wrote", out.relative_to(ROOT))


if __name__ == "__main__":
    main()
