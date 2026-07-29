"""Figure: extrapolating the Western-Europe pipeline to other regional cohorts."""
from __future__ import annotations
from pathlib import Path
import json, io
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
PR = ROOT / "results/prediction_results"
G, R, GY, B, O = "#2E8B57", "#C0392B", "#BDC3C7", "#2C6FB0", "#E08A1E"
REGS = ["西欧", "北美", "中东", "中亚", "东亚", "非洲"]


def main():
    J = json.load(io.open(PR / "multiregion/regional_summary.json", encoding="utf-8"))
    s = pd.read_csv(PR / "multiregion/cross_region_lean_enriched.csv", index_col=0)
    info = {d["region"]: d for d in J["regions"]}

    fig = plt.figure(figsize=(14, 9.8))
    gs = fig.add_gridspec(2, 2, hspace=0.46, wspace=0.46, height_ratios=[1, 1.18])

    # A regional power / tier
    ax = fig.add_subplot(gs[0, 0])
    regs = [r for r in REGS if r in info]
    y = np.arange(len(regs))[::-1]
    sig = [info[r]["n_lean_enriched_sig"] for r in regs]
    cols = [G if info[r]["tier"] == "robust_capable" else (O if info[r]["n_lean_enriched_sig"] > 0 else R) for r in regs]
    ax.barh(y, sig, color=cols, edgecolor="black", lw=.5, height=.6)
    for yi, r in zip(y, regs):
        d = info[r]
        ax.text(d["n_lean_enriched_sig"] + 0.5, yi, f"{d['n_lean_enriched_sig']}", va="center", fontsize=9, fontweight="bold")
        ax.text(-13, yi, f"{d['studies']}项 · n={d['matched_n']}\n({d['lean']}/{d['obese']}) {d['age_lean']}岁",
                va="center", ha="left", fontsize=7, color="#444")
    ax.set_yticks(y); ax.set_yticklabels(regs, fontsize=10)
    ax.set_xlim(-14, max(sig) * 1.25); ax.set_xlabel("显著瘦人富集物种数（FDR<0.05）")
    ax.set_title("(A) 方法外推的实际效力差异\n绿=可做跨研究meta；橙=单研究；红=效力不足（0结果）",
                 fontsize=10.8, fontweight="bold")

    # B replication counts
    ax = fig.add_subplot(gs[0, 1])
    cnt = s["在几个地区显著瘦人富集"].value_counts().sort_index()
    cnt = cnt[cnt.index >= 1]
    cols2 = [GY, O, G][:len(cnt)]
    ax.bar([str(int(i)) for i in cnt.index], cnt.values, color=cols2, edgecolor="black", lw=.5)
    for i, v in enumerate(cnt.values):
        ax.text(i, v + 0.6, str(int(v)), ha="center", fontsize=10, fontweight="bold")
    ax.set_xlabel("在几个地区达到显著瘦人富集"); ax.set_ylabel("物种数")
    ax.set_title("(B) 跨地区可复现性很低\n仅 1 个物种在 3 个地区复现（E. siraeum）",
                 fontsize=10.8, fontweight="bold")

    # C heatmap of top cross-region species
    ax = fig.add_subplot(gs[1, 0])
    top = s[s["在几个地区显著瘦人富集"] >= 2].head(14)
    cols_c = [f"{r}_系数" for r in REGS if f"{r}_系数" in s.columns]
    M = top[cols_c].to_numpy(float)
    im = ax.imshow(-M, cmap="RdYlGn", vmin=-0.8, vmax=0.8, aspect="auto")
    ax.set_xticks(range(len(cols_c))); ax.set_xticklabels([c.replace("_系数", "") for c in cols_c], fontsize=9)
    ax.set_yticks(range(len(top))); ax.set_yticklabels([i.replace("_", " ")[:30] for i in top.index],
                                                        fontsize=7.4, fontstyle="italic")
    for i, sp in enumerate(top.index):
        for j, c in enumerate(cols_c):
            r = c.replace("_系数", ""); v = top.loc[sp, c]; f = top.loc[sp, f"{r}_FDR"]
            if pd.isna(v):
                ax.text(j, i, "—", ha="center", va="center", fontsize=7, color="#888"); continue
            star = "*" if f < 0.05 else ""
            ax.text(j, i, f"{-v:+.2f}{star}", ha="center", va="center", fontsize=6.2)
    ax.set_title("(C) 在≥2地区复现的瘦人富集菌（数值=瘦人富集强度，*=FDR<0.05）\n绿=瘦人富集，红=肥胖富集",
                 fontsize=10.4, fontweight="bold")
    fig.colorbar(im, ax=ax, fraction=0.022, pad=0.015)

    # D v2 members cross-region
    ax = fig.add_subplot(gs[1, 1])
    V2 = ["Barnesiella_intestinihominis", "Odoribacter_splanchnicus", "Alistipes_putredinis",
          "Bacteroides_cellulosilyticus", "Intestinimonas_butyriciproducens",
          "Eubacterium_siraeum", "Akkermansia_muciniphila"]
    V2 = [v for v in V2 if v in s.index]
    y = np.arange(len(V2))[::-1]
    for yi, sp in zip(y, V2):
        for j, r in enumerate([r for r in REGS if f"{r}_系数" in s.columns]):
            v = s.loc[sp, f"{r}_系数"]; f = s.loc[sp, f"{r}_FDR"]
            if pd.isna(v):
                ax.scatter(j, yi, s=26, marker="x", c="#999"); continue
            lean = v < 0
            ax.scatter(j, yi, s=170 if f < 0.05 else 62, c=(G if lean else R),
                       edgecolor="black", lw=.6, alpha=1.0 if f < 0.05 else 0.42)
    ax.set_xticks(range(len([r for r in REGS if f"{r}_系数" in s.columns])))
    ax.set_xticklabels([r for r in REGS if f"{r}_系数" in s.columns], fontsize=9)
    ax.set_yticks(y); ax.set_yticklabels([v.replace("_", " ") for v in V2], fontsize=8, fontstyle="italic")
    ax.yaxis.tick_right(); ax.yaxis.set_label_position("right")
    ax.set_xlim(-0.6, len(REGS) - 0.4); ax.set_ylim(-0.7, len(V2) - 0.3)
    ax.grid(axis="y", ls=":", color="#DDD")
    ax.legend(handles=[mp.Patch(color=G, label="瘦人富集方向"), mp.Patch(color=R, label="肥胖富集方向"),
                       plt.Line2D([], [], marker="o", ls="", ms=10, mfc="grey", mec="black", label="大点=FDR<0.05")],
              fontsize=7.6, loc="lower left", ncol=1, framealpha=.95)
    ax.set_title("(D) v2 首选组合成员的跨地区表现\n多数仅在西欧显著；Akkermansia 在北美方向相反",
                 fontsize=10.4, fontweight="bold")

    fig.suptitle("将西欧方法外推至其它地区队列：瘦人富集菌群的可复现性检验",
                 fontsize=13.8, fontweight="bold", y=0.975)
    fig.savefig(ROOT / "results/paper_figures/fig24_multiregion.png", bbox_inches="tight", facecolor="white")
    print("wrote fig24_multiregion.png")


if __name__ == "__main__":
    main()
