"""Figure: food-grade single-strain fat-loss ranking (tiers + recommendations)."""
from __future__ import annotations
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mp
import numpy as np
import pandas as pd

plt.rcParams.update({"font.sans-serif": ["Microsoft YaHei", "SimHei"], "axes.unicode_minus": False,
                     "savefig.dpi": 300, "figure.dpi": 300,
                     "axes.spines.top": False, "axes.spines.right": False})
ROOT = Path(__file__).resolve().parents[2]
CR = ROOT / "results/combination_recommendations"
G, R, B, O, GY, PU = "#2E8B57", "#C0392B", "#2C6FB0", "#E08A1E", "#BDC3C7", "#7D5BA6"
REC_COL = {"首选": G, "推荐": B, "备选": O, "值得关注": PU, "慎用": "#E67E22", "低优先": GY, "不推荐": R}


def rec_key(s):
    for k in REC_COL:
        if s.startswith(k):
            return k
    return "低优先"


def main():
    R_ = pd.read_csv(CR / "foodgrade_single_strain_ranking_20260625.csv")
    R_["rec"] = R_["推荐意见"].map(rec_key)

    fig = plt.figure(figsize=(14.4, 10.6))
    gs = fig.add_gridspec(1, 2, wspace=0.06, width_ratios=[1.35, 1])

    # ---- left: full ranking bars ----
    ax = fig.add_subplot(gs[0, 0])
    d = R_.iloc[::-1].reset_index(drop=True)
    y = np.arange(len(d))
    ax.barh(y, d["v3性质分"], color=[REC_COL[k] for k in d.rec], edgecolor="black", lw=.4, height=.72)
    for yi, r in zip(y, d.itertuples()):
        mk = {"队列支持：瘦人富集": " ←队列支持", "队列反证：肥胖富集": " ←队列反证"}.get(r.队列证据, "")
        ax.text(r.v3性质分 + 0.006, yi, f"{r.v3性质分:.3f}{mk}", va="center", fontsize=6.6,
                fontweight="bold" if mk else "normal",
                color=(G if "支持" in mk else (R if "反证" in mk else "#333")))
    ax.set_yticks(y)
    ax.set_yticklabels([f"{int(r.排名):>2}. {r.中文名}" for r in d.itertuples()], fontsize=7.2)
    ax.set_xlim(0, 1.02); ax.set_xlabel("v3 性质分（六轴加权，不含队列数据）")
    # tier separators
    for g_ in sorted(d["同分组"].unique())[:-1]:
        idx = d.index[d["同分组"] == g_].max()
        ax.axhline(idx + 0.5, color="#CCC", lw=.7, ls=":")
    ax.set_title("(A) 38 株食源益生菌减脂潜力排序\n颜色=推荐意见；标注=队列证据方向",
                 fontsize=11.4, fontweight="bold")
    ax.legend(handles=[mp.Patch(color=v, label=k) for k, v in REC_COL.items()],
              fontsize=7.6, loc="lower right", ncol=2, framealpha=.95)

    # ---- right top: tier structure ----
    ax = fig.add_subplot(gs[0, 1])
    ax.axis("off")
    t = R_.groupby("同分组").agg(分数=("v3性质分", "first"), 株数=("species" if "species" in R_.columns else "物种(拉丁名)", "size")).reset_index()
    ax.text(0.5, 0.985, "(B) 分档结构与关键结论", ha="center", fontsize=11.4, fontweight="bold")
    yy = 0.945
    ax.text(0.03, yy, "10 个分数档，最大并列 11 株（属级注释所致）", fontsize=8.4, color="#444")
    yy -= 0.028
    for r in t.itertuples():
        w = 0.62 * r.株数 / t.株数.max()
        ax.add_patch(mp.Rectangle((0.20, yy - 0.016), w, 0.019, fc=B, alpha=.75, ec="black", lw=.4))
        ax.text(0.18, yy - 0.007, f"组{int(r.同分组)} {r.分数:.3f}", ha="right", fontsize=7, color="#333")
        ax.text(0.20 + w + 0.012, yy - 0.007, f"{int(r.株数)}株", fontsize=7, color="#333")
        yy -= 0.027

    yy -= 0.02
    blocks = [
        ("【首选】2 株", G,
         ["动物双歧杆菌  西欧 FC=0.62 (FDR 0.004)",
          "长双歧杆菌    西欧 FC=0.65 (FDR 0.042)",
          "唯一同时具备：性质优 + 临床先例 + 队列支持",
          "评分劣势仅来自工业可行性与 BSH 强度"]),
        ("推荐（2 株）", B,
         ["副干酪乳酪杆菌 / 植物乳植杆菌  v3=0.866 最高",
          "性质全面占优，但队列中完全无数据",
          "（乳杆菌为过路菌，非肠道常驻菌）"]),
        ("值得关注（1 株）", PU,
         ["链状双歧杆菌  中东 FC=0.48",
          "全部食源菌中最强队列信号，但缺临床先例"]),
        ("慎用（4 株）", "#E67E22",
         ["短 / 青春 / 两歧 / 假链状双歧杆菌",
          "北美队列显著肥胖富集 FC 3.15–7.39",
          "均为常用商业菌，该市场需先做人群验证"]),
        ("不推荐（11 株）", R,
         ["链球菌属：安全等级 0.25（属内含病原种）",
          "非减脂性质问题——其交叉喂养能力实为 1.0"]),
    ]
    for title, col, lines in blocks:
        h = 0.030 + 0.0225 * len(lines)
        ax.add_patch(mp.FancyBboxPatch((0.02, yy - h), 0.96, h,
                                       boxstyle="round,pad=0.008", fc="white", ec=col, lw=1.6))
        ax.text(0.05, yy - 0.018, title, fontsize=8.8, fontweight="bold", color=col)
        for k, ln in enumerate(lines):
            ax.text(0.06, yy - 0.040 - k * 0.0225, ln, fontsize=7.3, color="#333")
        yy -= h + 0.014
    ax.set_xlim(0, 1); ax.set_ylim(0, 1)

    fig.suptitle("食源性益生菌减脂潜力单菌排序（v3 方法）", fontsize=14, fontweight="bold", y=0.998)
    fig.savefig(ROOT / "results/paper_figures/fig27_foodgrade_ranking.png",
                bbox_inches="tight", facecolor="white")
    print("wrote fig27_foodgrade_ranking.png")


if __name__ == "__main__":
    main()
