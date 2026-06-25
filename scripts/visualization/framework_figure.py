"""Three-stage framework figure: AI clinical screening -> mechanism fine-screen
-> effect validation."""
from __future__ import annotations
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch

plt.rcParams.update({"font.sans-serif": ["Microsoft YaHei", "SimHei"],
                     "axes.unicode_minus": False, "savefig.dpi": 300, "figure.dpi": 300})
ROOT = Path(__file__).resolve().parents[2]


def main():
    fig, ax = plt.subplots(figsize=(10.6, 5.6))
    ax.axis("off"); ax.set_xlim(0, 1); ax.set_ylim(0, 1)
    stages = [
        ("阶段一  AI 临床数据筛选", "#2C6FB0", "#E8F0F8",
         ["8 304 样本 / 45 研究", "肥胖状态 AI 模型", "（分组 AUC 0.729）",
          "瘦(无胰岛素抵抗) vs 胖", "差异丰度筛选"],
         "→ 53 个瘦人富集候选菌"),
        ("阶段二  菌株机制细筛", "#2E8B57", "#E6F2EA",
         ["功能 / 互补 / 可培养筛选", "协同组合打分", "（丁酸·丙酸·黏液·BSH）",
          "基因组安全门", "（AMR · 毒力 · MGE）"],
         "→ 安全·机制互补组合"),
        ("阶段三  菌株效果验证", "#E08A1E", "#FBF0DD",
         ["诚实验证门控", "个体应答模型", "（留一受试者 CV）",
          "验证数据获取 (IPD)", "体外→动物→RCT"],
         "→ 数据驱动验证路线"),
    ]
    x0, w, gap = 0.02, 0.30, 0.02
    for i, (title, ec, fc, items, out) in enumerate(stages):
        x = x0 + i * (w + gap + 0.005)
        ax.add_patch(FancyBboxPatch((x, 0.12), w, 0.74, boxstyle="round,pad=0.01,rounding_size=0.02",
                     fc=fc, ec=ec, lw=2.0))
        ax.text(x + w / 2, 0.805, title, ha="center", va="center", fontsize=12, fontweight="bold", color=ec)
        for j, it in enumerate(items):
            yy = 0.70 - j * 0.105
            bold = it and not it.startswith("（")
            ax.text(x + w / 2, yy, it, ha="center", va="center",
                    fontsize=9.2 if bold else 8.2,
                    color="black" if bold else "#555555")
        ax.add_patch(FancyBboxPatch((x + 0.015, 0.135), w - 0.03, 0.055,
                     boxstyle="round,pad=0.005", fc=ec, ec="none"))
        ax.text(x + w / 2, 0.1625, out, ha="center", va="center", fontsize=9, color="white", fontweight="bold")
        if i < 2:
            ax.add_patch(FancyArrowPatch((x + w + 0.002, 0.49), (x + w + gap + 0.007, 0.49),
                         arrowstyle="-|>", mutation_scale=20, color="#555555", lw=2))
    ax.text(0.5, 0.04, "贯穿原则：数据驱动定标 · 机制互补 · 诚实验证门控（疗效门未过即关闭）",
            ha="center", fontsize=9.5, color="#C0392B", style="italic")
    ax.set_title("益生菌减脂菌株组合研发框架：AI 临床数据筛选 → 菌株机制细筛 → 菌株效果验证",
                 fontsize=13, fontweight="bold", y=1.0)
    fig.savefig(ROOT / "results/paper_figures/fig0_framework.png", bbox_inches="tight", facecolor="white")
    plt.close(fig); print("wrote fig0_framework.png")


if __name__ == "__main__":
    main()
