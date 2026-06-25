"""Figures: (A) full lean-vs-obese differential landscape; (B) screened
lean-enriched candidates by composite (function/complementarity/culturability)."""
from __future__ import annotations
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np
import pandas as pd

plt.rcParams.update({"font.sans-serif": ["Microsoft YaHei", "SimHei"],
                     "axes.unicode_minus": False, "savefig.dpi": 300, "figure.dpi": 300,
                     "axes.spines.top": False, "axes.spines.right": False})
ROOT = Path(__file__).resolve().parents[2]
PR = ROOT / "results/prediction_results"
FIG = ROOT / "results/paper_figures"
GREEN, RED, GREY = "#2E8B57", "#C0392B", "#BDC3C7"


def volcano():
    r = pd.read_csv(PR / "lean_vs_obese_differential_abundance_20260625.csv")
    trusted = r["consistency"] >= 0.70
    fig, ax = plt.subplots(figsize=(9.4, 6.4))
    ax.scatter(r.loc[~trusted, "median_log2fc"], r.loc[~trusted, "pooled_cohens_d"],
               s=14, c=GREY, alpha=0.5, label="未达一致性阈值")
    for direc, col, lab in [("lean_enriched", GREEN, "瘦人富集（一致≥11/15）"),
                            ("obese_enriched", RED, "胖人富集（一致≥11/15）")]:
        m = trusted & (r["direction"] == direc)
        ax.scatter(r.loc[m, "median_log2fc"], r.loc[m, "pooled_cohens_d"],
                   s=34, c=col, edgecolor="black", lw=0.4, label=lab)
    ax.axhline(0, color="black", lw=0.7); ax.axvline(0, color="black", lw=0.7)
    # label notable
    note = ["Akkermansia_muciniphila", "Faecalibacterium_prausnitzii", "Ruminococcus_gnavus",
            "Prevotella_copri", "Bacteroides_intestinalis", "Odoribacter_splanchnicus",
            "Butyrivibrio_crossotus", "Veillonella_atypica", "Eubacterium_siraeum",
            "Barnesiella_intestinihominis"]
    for _, x in r[r["species"].isin(note)].iterrows():
        ax.annotate(x["species"].replace("_", " "), (x["median_log2fc"], x["pooled_cohens_d"]),
                    fontsize=7.5, fontstyle="italic", xytext=(4, 3), textcoords="offset points")
    ax.set_xlabel("中位 log2 倍数变化（瘦/胖，正=瘦人富集）")
    ax.set_ylabel("合并 Cohen's d（标准化效应）")
    ax.set_title("全部差异菌总览：瘦人(无胰岛素抵抗) vs 胖人（194 物种，83 个方向稳健）",
                 fontsize=12.5, fontweight="bold")
    ax.legend(loc="upper left", fontsize=9, frameon=True)
    fig.savefig(FIG / "fig11_diffabund_volcano.png", bbox_inches="tight", facecolor="white")
    plt.close(fig); print("wrote fig11_diffabund_volcano.png")


def screen():
    s = pd.read_csv(PR / "lean_enriched_screened_candidates_20260625.csv").head(12)
    s = s.iloc[::-1]
    y = np.arange(len(s))
    def primary(row):
        if row["butyrate"]: return GREEN          # butyrate producer
        if row["mucin"] >= 2: return "#7D5BA6"    # strong mucin axis (Akkermansia-type)
        if row["propionate"]: return "#2C6FB0"    # propionate producer
        if row["mucin"]: return "#7D5BA6"
        return GREY
    colors = [primary(r) for _, r in s.iterrows()]
    fig, ax = plt.subplots(figsize=(9.8, 6.2))
    ax.barh(y, s["composite_screen_score"], color=colors, edgecolor="black", lw=0.5, height=0.66)
    for yi, (_, r) in zip(y, s.iterrows()):
        flags = "".join(["丁" if r["butyrate"] else "", "黏" if r["mucin"] else "",
                         "丙" if r["propionate"] else ""]) or "—"
        ax.text(r["composite_screen_score"] + 0.008, yi,
                f"{flags} · d={r['cohens_d']:+.2f} · {r['culturability_class']}",
                va="center", fontsize=7.8)
    ax.set_yticks(y)
    ax.set_yticklabels([sp.replace("_", " ") for sp in s["species"]], fontsize=9.2, fontstyle="italic")
    ax.set_xlim(0, 1.0); ax.set_xlabel("综合筛选分（效应 32% + 机制互补 28% + 功能 20% + 可培养性 20%）")
    ax.set_title("瘦人富集菌的功能 / 互补 / 可培养性筛选（Top 12 候选）", fontsize=12.5, fontweight="bold")
    ax.legend(handles=[mpatches.Patch(color=GREEN, label="丁酸产生菌"),
                       mpatches.Patch(color="#7D5BA6", label="黏液轴（Akkermansia 类）"),
                       mpatches.Patch(color="#2C6FB0", label="丙酸产生菌")],
              loc="lower right", fontsize=9, frameon=True)
    fig.savefig(FIG / "fig12_lean_screen.png", bbox_inches="tight", facecolor="white")
    plt.close(fig); print("wrote fig12_lean_screen.png")


if __name__ == "__main__":
    volcano(); screen()
