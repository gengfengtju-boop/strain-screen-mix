"""Figure: lean vs obese gut metabolic-potential differences (Western Europe)."""
from __future__ import annotations
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy import stats

plt.rcParams.update({"font.sans-serif": ["Microsoft YaHei", "SimHei"], "axes.unicode_minus": False,
                     "savefig.dpi": 300, "figure.dpi": 300,
                     "axes.spines.top": False, "axes.spines.right": False})
ROOT = Path(__file__).resolve().parents[2]
PR = ROOT / "results/prediction_results"
G, R, GY, B, O = "#2E8B57", "#C0392B", "#BDC3C7", "#2C6FB0", "#E08A1E"


def main():
    r = pd.read_csv(PR / "we_metabolic/pathway_differential_all.csv")
    r1 = r[r.analysis == "matched_144v144"].copy()
    cls = pd.read_csv(PR / "we_metabolic/metabolite_class_summary.csv")

    fig = plt.figure(figsize=(13.8, 9.4))
    gs = fig.add_gridspec(2, 2, hspace=0.44, wspace=0.30, height_ratios=[1, 1.05])

    # A volcano
    ax = fig.add_subplot(gs[0, 0])
    r1["nlp"] = -np.log10(r1.fdr.clip(lower=1e-6))
    ns = r1[r1.fdr >= 0.05]; le = r1[(r1.fdr < 0.05) & (r1.coef_obese_log10 < 0)]
    oe = r1[(r1.fdr < 0.05) & (r1.coef_obese_log10 > 0)]
    ax.scatter(ns.coef_obese_log10, ns.nlp, s=12, c=GY, alpha=.5, label=f"不显著 (n={len(ns)})")
    ax.scatter(le.coef_obese_log10, le.nlp, s=32, c=G, edgecolor="black", lw=.4, label=f"瘦人富集 (n={len(le)})")
    ax.scatter(oe.coef_obese_log10, oe.nlp, s=32, c=R, edgecolor="black", lw=.4, label=f"肥胖富集 (n={len(oe)})")
    ax.axhline(-np.log10(0.05), ls="--", color="grey", lw=1); ax.axvline(0, color="black", lw=.7)
    for _, x in pd.concat([le.nlargest(3, "nlp"), oe.nlargest(3, "nlp")]).iterrows():
        ax.annotate(x.pathway[:22], (x.coef_obese_log10, x.nlp), fontsize=6.0,
                    xytext=(5, 3), textcoords="offset points")
    ax.set_xlabel("肥胖项系数（log10 丰度差；负=瘦人富集）"); ax.set_ylabel("−log10 FDR")
    ax.set_title("(A) 代谢通路差异（匹配队列 144 vs 144）\n395 条通路中仅 34 条显著，效应普遍很小",
                 fontsize=10.8, fontweight="bold")
    ax.legend(fontsize=7.6, loc="upper left")

    # B class summary
    ax = fig.add_subplot(gs[0, 1])
    c = cls[cls.n_pathways >= 4].sort_values("n_sig")
    y = np.arange(len(c)); w = 0.4
    ax.barh(y - w/2, c.n_obese_enriched, w, color=R, edgecolor="black", lw=.4, label="肥胖富集")
    ax.barh(y + w/2, c.n_lean_enriched, w, color=G, edgecolor="black", lw=.4, label="瘦人富集")
    xmax = max(c.n_obese_enriched.max(), c.n_lean_enriched.max())
    for yi, row in zip(y, c.itertuples()):
        ax.text(xmax * 1.06, yi, f"共{int(row.n_pathways)}条", va="center", fontsize=6.8, color="#555")
    ax.set_yticks(y); ax.set_yticklabels(c.metabolite_class, fontsize=8)
    ax.set_xlim(0, xmax * 1.28)
    ax.set_xlabel("FDR<0.05 的通路数"); ax.legend(fontsize=8, loc="lower right", framealpha=0.95)
    ax.set_title("(B) 按代谢物类别汇总\n短链脂肪酸类几乎无差异（功能冗余）", fontsize=10.8, fontweight="bold")

    # C archaeal pathways + correlation
    ax = fig.add_subplot(gs[1, 0])
    arch = r1[r1.pathway.str.contains("archae|methanogen|factor 420|CDP archaeol", case=False, na=False)].copy()
    arch = arch.sort_values("coef_obese_log10")
    y = np.arange(len(arch))
    cols = [G if v < 0 else R for v in arch.coef_obese_log10]
    ax.barh(y, arch.cliffs_delta_lean_vs_obese, color=cols, edgecolor="black", lw=.4, height=.66)
    ax.axvline(0, color="black", lw=.8)
    for yi, x in zip(y, arch.itertuples()):
        s = "*" if x.fdr < 0.05 else ""
        ax.text(x.cliffs_delta_lean_vs_obese + (0.008 if x.cliffs_delta_lean_vs_obese > 0 else -0.008), yi,
                f"FC={x.fold_change_obese_vs_lean:.3f}{s}", va="center",
                ha="left" if x.cliffs_delta_lean_vs_obese > 0 else "right", fontsize=7)
    ax.set_yticks(y); ax.set_yticklabels([p[:34] for p in arch.pathway], fontsize=7.6)
    ax.set_xlim(-0.30, 0.34); ax.set_xlabel("Cliff's δ（正=瘦人富集）")
    ax.set_title("(C) 古菌/产甲烷通路：氢营养型富集于瘦人\n乙酸营养型反而富集于肥胖（*=FDR<0.05）",
                 fontsize=10.6, fontweight="bold")

    # D SCFA null result
    ax = fig.add_subplot(gs[1, 1])
    s = r1[r1.metabolite_class.str.contains("短链脂肪酸")].copy()
    s["cls"] = s.metabolite_class.str.replace("短链脂肪酸-", "", regex=False)
    order = {"丁酸": 0, "丙酸": 1, "乙酸/发酵": 2}
    s["ord"] = s.cls.map(order)
    colors = {"丁酸": G, "丙酸": B, "乙酸/发酵": O}
    for k, grp in s.groupby("cls"):
        ax.scatter(grp.fold_change_obese_vs_lean, np.random.default_rng(0).normal(order[k], 0.09, len(grp)),
                   s=[46 if f < 0.05 else 26 for f in grp.fdr],
                   c=colors[k], edgecolor="black", lw=.4,
                   alpha=[1.0 if f < 0.05 else 0.55 for f in grp.fdr])
    ax.axvline(1.0, ls="--", color="black", lw=1.1)
    ax.set_yticks([0, 1, 2]); ax.set_yticklabels(["丁酸通路\n(6条)", "丙酸通路\n(5条)", "乙酸/发酵\n(12条)"], fontsize=9)
    ax.set_xlim(0.95, 1.08); ax.set_xlabel("倍数变化（胖/瘦）；虚线=无差异")
    ax.set_title("(D) 短链脂肪酸产生能力：无实质差异\n丁酸与丙酸通路全部接近 1.0（大点=FDR<0.05）",
                 fontsize=10.6, fontweight="bold")

    fig.suptitle("西欧健康人群胖瘦肠道代谢潜能差异（宏基因组通路，非实测代谢组）",
                 fontsize=13.6, fontweight="bold", y=0.975)
    fig.savefig(ROOT / "results/paper_figures/fig23_metabolic_pathways.png",
                bbox_inches="tight", facecolor="white")
    print("wrote fig23_metabolic_pathways.png")


if __name__ == "__main__":
    main()
