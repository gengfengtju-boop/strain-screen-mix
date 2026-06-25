"""Publication-quality figures (300 dpi, Chinese labels) for the ProSlim report."""
from __future__ import annotations

from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch
import numpy as np
import pandas as pd

plt.rcParams.update({
    "font.sans-serif": ["Microsoft YaHei", "SimHei"],
    "axes.unicode_minus": False,
    "font.size": 11,
    "axes.titlesize": 13,
    "axes.titleweight": "bold",
    "axes.labelsize": 11,
    "savefig.dpi": 300,
    "figure.dpi": 300,
    "axes.spines.top": False,
    "axes.spines.right": False,
    "axes.linewidth": 0.9,
})
ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "results/paper_figures"
OUT.mkdir(parents=True, exist_ok=True)
C = {"blue": "#2C6FB0", "red": "#C0392B", "green": "#2E8B57", "grey": "#7F8C8D",
     "orange": "#E08A1E", "purple": "#7D5BA6", "light": "#D6E4F0"}


def save(fig, name):
    fig.savefig(OUT / name, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print("wrote", (OUT / name).relative_to(ROOT))


def fig1_pipeline():
    fig, ax = plt.subplots(figsize=(9, 4.6))
    ax.axis("off")
    cols = [
        ("数据层", ["公开菌群数据库", "益生菌 RCT 证据", "候选菌株基因组", "安全性注释"], C["light"]),
        ("模型层", ["肥胖状态模型\n(分组AUC 0.729)", "效应量 meta 综合\n(严格直接方差)", "菌株安全/功能矩阵\n(223 株)"], "#FCE9C8"),
        ("决策层", ["组合排序优先级\n(Top-10)", "诚实验证门控\n(疗效门关闭)", "个体应答 pilot\n(脚手架就绪)"], "#D8EAD8"),
    ]
    x0 = 0.03
    for ci, (title, items, color) in enumerate(cols):
        x = x0 + ci * 0.335
        ax.text(x + 0.14, 0.93, title, ha="center", fontsize=13, fontweight="bold")
        for ii, it in enumerate(items):
            y = 0.78 - ii * 0.205
            box = FancyBboxPatch((x, y - 0.075), 0.28, 0.15,
                                 boxstyle="round,pad=0.01,rounding_size=0.02",
                                 fc=color, ec=C["grey"], lw=1.1)
            ax.add_patch(box)
            ax.text(x + 0.14, y, it, ha="center", va="center", fontsize=9.2)
        if ci < 2:
            ax.add_patch(FancyArrowPatch((x + 0.29, 0.5), (x + 0.335, 0.5),
                         arrowstyle="-|>", mutation_scale=18, color=C["grey"], lw=1.6))
    ax.set_xlim(0, 1); ax.set_ylim(0, 1)
    ax.set_title("图1  ProSlim 微生物组减脂预测系统总体架构", y=1.02)
    save(fig, "fig1_pipeline.png")


def fig2_obesity_model():
    fig, axes = plt.subplots(1, 2, figsize=(8.4, 4))
    # AUC
    ax = axes[0]
    vals = [0.729, 0.825]; labels = ["分组留一验证\n(主要)", "随机拆分\n(乐观)"]
    bars = ax.bar(labels, vals, color=[C["blue"], C["grey"]], width=0.55, edgecolor="black", lw=0.7)
    ax.axhline(0.5, ls="--", color=C["red"], lw=1, label="随机基线 0.5")
    for b, v in zip(bars, vals):
        ax.text(b.get_x()+b.get_width()/2, v+0.012, f"{v:.3f}", ha="center", fontsize=11, fontweight="bold")
    ax.set_ylim(0.4, 0.9); ax.set_ylabel("ROC-AUC")
    ax.set_title("(A) 肥胖分类性能")
    ax.legend(fontsize=8, loc="upper left")
    ax.annotate("乐观偏差\n(批次/地域混杂)", xy=(1,0.825), xytext=(0.35,0.86),
                fontsize=8, color=C["red"], ha="center",
                arrowprops=dict(arrowstyle="->", color=C["red"], lw=1))
    # BMI R2
    ax = axes[1]
    vals = [0.103, 0.225]
    bars = ax.bar(labels, vals, color=[C["blue"], C["grey"]], width=0.55, edgecolor="black", lw=0.7)
    for b, v in zip(bars, vals):
        ax.text(b.get_x()+b.get_width()/2, v+0.004, f"{v:.3f}", ha="center", fontsize=11, fontweight="bold")
    ax.set_ylim(0, 0.28); ax.set_ylabel("R²")
    ax.set_title("(B) BMI 回归 R²")
    fig.suptitle("图2  肥胖状态模型：内部分组验证有信号，但与随机拆分存在乐观差距",
                 y=1.02, fontsize=12.5, fontweight="bold")
    save(fig, "fig2_obesity_model.png")


def fig3_forest():
    data = [
        ("BMI | kg/m²  (k=5)", -0.4384, -0.5326, -0.3441, -0.5464, -0.3303, True),
        ("体重 | kg  (k=7)", -1.3947, -2.1083, -0.681, -2.9726, 0.1833, False),
    ]
    fig, ax = plt.subplots(figsize=(8.6, 3.2))
    ys = [1, 0]
    for (lab, est, lo, hi, pil, pih, ready), y in zip(data, ys):
        col = C["green"] if ready else C["orange"]
        ax.plot([pil, pih], [y, y], color=col, lw=2.4, alpha=0.35, solid_capstyle="round")  # prediction interval
        ax.plot([lo, hi], [y, y], color=col, lw=4, solid_capstyle="round")  # 95% CI
        ax.plot(est, y, "s", color=col, ms=11, mec="black", mew=0.6)
        ax.text(0.27, y, f"{est:.2f} [{lo:.2f}, {hi:.2f}]\n预测区间[{pil:.2f}, {pih:.2f}]",
                va="center", fontsize=9)
        tag = "可复制就绪" if ready else "区间含0·未就绪"
        ax.text(-3.35, y+0.22, lab, va="center", fontsize=10, fontweight="bold")
        ax.text(-3.35, y-0.2, f"I²={'0.0' if ready else '54.8'}%  ·  {tag}", va="center",
                fontsize=8.4, color=col)
    ax.axvline(0, ls="--", color=C["red"], lw=1.1)
    ax.text(0.02, 1.55, "无效应线", color=C["red"], fontsize=8)
    ax.set_ylim(-0.6, 1.7); ax.set_xlim(-3.4, 1.3)
    ax.set_yticks([]); ax.set_xlabel("合并效应量（HKSJ 随机效应，负=下降）")
    ax.spines["left"].set_visible(False)
    ax.set_title("图3  严格直接方差下的小样本 meta 综合：BMI 可复制就绪，体重区间含 0", y=1.06)
    # legend
    ax.plot([],[],color=C["grey"],lw=4,label="95% 置信区间")
    ax.plot([],[],color=C["grey"],lw=2.4,alpha=0.35,label="预测区间")
    ax.legend(fontsize=8, loc="lower right")
    save(fig, "fig3_forest.png")


def fig4_gate_funnel():
    fig, ax = plt.subplots(figsize=(7.6, 4.4))
    stages = [("效应行（全部）", 137), ("高置信行", 68), ("直接方差行", 27),
              ("独立研究", 19), ("越过基线 stratum", 1)]
    n = len(stages); maxw = 1.0
    cols = [C["light"], "#A9C9E8", C["blue"], "#1F4E79", C["red"]]
    for i, (lab, val) in enumerate(stages):
        w = maxw * (val / stages[0][1]) ** 0.5
        y = n - 1 - i
        ax.add_patch(mpatches.FancyBboxPatch((0.5 - w/2, y), w, 0.78,
                     boxstyle="round,pad=0.005", fc=cols[i], ec="black", lw=0.8))
        ax.text(0.5, y + 0.39, f"{lab}：{val}", ha="center", va="center",
                fontsize=10.5, fontweight="bold" if i in (0,4) else "normal",
                color="white" if i in (3,4) else "black")
    ax.text(0.5, -0.7, "组合疗效排序门：关闭（combination_ranking_enabled = false）",
            ha="center", fontsize=10, color=C["red"], fontweight="bold",
            bbox=dict(boxstyle="round", fc="#FBEAEA", ec=C["red"]))
    ax.set_xlim(0, 1); ax.set_ylim(-1.1, n)
    ax.axis("off")
    ax.set_title("图4  证据到疗效门的诚实漏斗：4 个 stratum 中仅 1 个越过均值基线", y=1.0)
    save(fig, "fig4_gate_funnel.png")


def fig5_balanced_sensitivity():
    strata = ["体重|kg", "BMI|kg/m²", "body_fat|kg", "waist|cm", "lipid_TG"]
    direct = [10, 7, 2, 2, 1]; balanced = [13, 11, 4, 2, 1]
    x = np.arange(len(strata)); w = 0.38
    fig, ax = plt.subplots(figsize=(8.4, 4))
    ax.bar(x - w/2, direct, w, label="直接方差研究", color=C["blue"], edgecolor="black", lw=0.6)
    ax.bar(x + w/2, balanced, w, label="+ 平衡n 敏感性", color=C["orange"], edgecolor="black", lw=0.6)
    ax.axhline(10, ls="--", color=C["red"], lw=1.2)
    ax.text(4.3, 10.2, "10 研究目标", color=C["red"], fontsize=8.5, ha="right")
    for i,(d,b) in enumerate(zip(direct,balanced)):
        ax.text(i-w/2, d+0.15, str(d), ha="center", fontsize=9)
        ax.text(i+w/2, b+0.15, str(b), ha="center", fontsize=9, color=C["orange"])
    ax.set_xticks(x); ax.set_xticklabels(strata)
    ax.set_ylabel("独立研究数"); ax.set_ylim(0, 15)
    ax.legend(fontsize=9)
    ax.set_title("图5  补全臂级样本量后：BMI 与体重在敏感性层达到 10 研究目标", y=1.03)
    save(fig, "fig5_balanced_sensitivity.png")


def fig6_combinations():
    df = pd.read_csv(ROOT / "results/combination_recommendations/robust_strain_combinations_20260610.csv").sort_values("robust_rank").head(10)
    y = np.arange(len(df))[::-1]
    est = df["posterior_score_mean"].values
    lo = df["posterior_score_p10"].values; hi = df["posterior_score_p90"].values
    fig, ax = plt.subplots(figsize=(8.6, 4.6))
    ax.barh(y, est, color=C["light"], edgecolor=C["blue"], height=0.6)
    ax.errorbar(est, y, xerr=[est-lo, hi-est], fmt="o", color=C["blue"],
                ms=6, capsize=3, lw=1.2, mec="black", mew=0.5)
    ax.set_yticks(y)
    ax.set_yticklabels([f"#{int(r)} {cid}" for r, cid in zip(df["robust_rank"], df["combination_id"])], fontsize=9)
    for yi, v in zip(y, est):
        ax.text(v+0.06, yi, f"{v:.2f}", va="center", fontsize=8.5)
    ax.set_xlim(5, 8.7); ax.set_xlabel("证据-机制后验综合分（误差棒=p10–p90）")
    ax.set_title("图6  Top-10 益生菌组合的临床前验证优先级及不确定区间", y=1.03)
    ax.text(5.05, -1.0, "范围：临床前验证优先级，非疗效/响应概率预测",
            fontsize=8.5, color=C["red"])
    save(fig, "fig6_combinations.png")


def fig7_mechanism():
    df = pd.read_csv(ROOT / "results/combination_recommendations/preclinical_validation_priority_top10_augmented_20260625.csv")
    axes_lab = ["BSH\n胆盐水解", "lactate\n乳酸乙酸", "butyrate\n丁酸", "propionate\n丙酸", "mucin\n黏液屏障"]
    M = np.zeros((len(df), 5))
    for i, r in df.iterrows():
        cov = str(r["axes_covered"])
        M[i,0] = 1 if "BSH" in cov else 0
        M[i,1] = 1 if "lactate" in cov else 0
        M[i,2] = 1 if "butyrate" in cov else 0
        M[i,3] = 1 if "propionate" in cov else 0
        M[i,4] = 1 if "mucin" in cov else 0
    fig, ax = plt.subplots(figsize=(7.2, 4.8))
    ax.imshow(M, cmap=matplotlib.colors.ListedColormap(["#F2F2F2", C["green"]]), aspect="auto", vmin=0, vmax=1)
    ax.set_xticks(range(5)); ax.set_xticklabels(axes_lab, fontsize=9)
    ax.set_yticks(range(len(df))); ax.set_yticklabels([f"#{int(x)}" for x in df["robust_rank"]], fontsize=9)
    for i in range(len(df)):
        for j in range(5):
            ax.text(j, i, "●" if M[i,j] else "—", ha="center", va="center",
                    color="white" if M[i,j] else C["grey"], fontsize=10)
    ax.set_title("图7  机制覆盖热图：Top 组合集中于 BSH+乳酸轴，普遍缺丁酸/丙酸/黏液", y=1.03)
    ax.text(2, len(df)+0.2, "机制盲区（证据驱动排序的固有偏向）", ha="center", color=C["red"], fontsize=8.5)
    save(fig, "fig7_mechanism.png")


def fig8_ipd_funnel():
    fig, axes = plt.subplots(1, 2, figsize=(9.4, 4))
    # search funnel by round
    ax = axes[0]
    rounds = ["第1轮\n(100)", "第2轮\n(400)", "第3轮过滤\n(666)"]
    screened = [100, 400, 666]; deposit = [7, 25, 5]; ontarget = [3, 14, 152]
    x = np.arange(3); w=0.26
    ax.bar(x-w, screened, w, label="筛查", color=C["light"], edgecolor="black", lw=0.5)
    ax.bar(x, ontarget, w, label="结局对口", color=C["blue"], edgecolor="black", lw=0.5)
    ax.bar(x+w, deposit, w, label="有测序沉积", color=C["orange"], edgecolor="black", lw=0.5)
    ax.set_yscale("log"); ax.set_xticks(x); ax.set_xticklabels(rounds, fontsize=9)
    ax.set_ylabel("研究数（对数轴）"); ax.legend(fontsize=8)
    ax.set_title("(A) 三轮 IPD 搜寻漏斗")
    # verdict outcome
    ax = axes[1]; ax.axis("off")
    rows = [
        ("益生菌+减脂+个体测序", "0", C["red"]),
        ("唯一配对人源队列\n(PRJNA1211859 低卡饮食)", "16S·待个体结局", C["orange"]),
        ("含 shotgun 对口队列\n(PRJEB81868 菊苣纤维)", "减脂结局为零", C["orange"]),
        ("个体应答建模脚手架", "就绪·已测试", C["green"]),
    ]
    for i,(lab,val,col) in enumerate(rows):
        y=0.82-i*0.24
        ax.add_patch(FancyBboxPatch((0.02,y-0.09),0.96,0.18,boxstyle="round,pad=0.01",
                     fc="white", ec=col, lw=1.6))
        ax.text(0.06,y,lab,va="center",fontsize=9.3)
        ax.text(0.94,y,val,va="center",ha="right",fontsize=9.3,color=col,fontweight="bold")
    ax.set_xlim(0,1); ax.set_ylim(0,1)
    ax.set_title("(B) 文献级核验结论")
    fig.suptitle("图8  个体级数据(IPD)搜寻：公开库无「益生菌×减脂×个体测序」队列",
                 y=1.03, fontsize=12.5, fontweight="bold")
    save(fig, "fig8_ipd_funnel.png")


def fig9_strain_membership():
    df = pd.read_csv(ROOT / "results/combination_recommendations/robust_strain_combinations_20260610.csv").sort_values("robust_rank").head(10)
    from collections import Counter
    members = [[x.strip() for x in str(r["strains"]).split(";")] for _, r in df.iterrows()]
    freq = Counter(s for m in members for s in m)
    strains = [s for s, _ in freq.most_common()]
    n_s, n_c = len(strains), len(df)
    sidx = {s: i for i, s in enumerate(strains)}

    def genus_color(s):
        if s.startswith("Lactobacillus"): return C["blue"]
        if s.startswith("Bifidobacterium"): return C["green"]
        if s.startswith("Bacillus"): return C["orange"]
        return C["purple"]

    fig, ax = plt.subplots(figsize=(11, 5.6))
    # score bar across top
    scores = df["posterior_score_mean"].values
    smin, smax = scores.min(), scores.max()
    for j, sc in enumerate(scores):
        hh = 0.55 * (sc - smin + 0.3) / (smax - smin + 0.3)
        ax.add_patch(mpatches.Rectangle((j + 0.18, n_s + 0.15), 0.64, hh,
                     fc=C["light"], ec=C["blue"], lw=0.8))
        ax.text(j + 0.5, n_s + 0.18 + hh + 0.05, f"{sc:.2f}", ha="center", va="bottom", fontsize=7.5)
    ax.text(-0.3, n_s + 0.45, "后验分", ha="right", va="center", fontsize=8.5, color=C["blue"])
    # membership cells
    for j, m in enumerate(members):
        for s in m:
            i = n_s - 1 - sidx[s]
            ax.add_patch(mpatches.FancyBboxPatch((j + 0.12, i + 0.12), 0.76, 0.76,
                         boxstyle="round,pad=0.005,rounding_size=0.06",
                         fc=genus_color(s), ec="white", lw=1.2))
    # grid + labels
    for i, s in enumerate(strains):
        y = n_s - 1 - i
        ax.text(-0.3, y + 0.5, s, ha="right", va="center", fontsize=9)
        ax.text(n_c + 0.25, y + 0.5, f"{freq[s]}/10", ha="left", va="center",
                fontsize=8.5, color=C["grey"])
    for j in range(n_c):
        cid = df.iloc[j]["combination_id"]
        ax.text(j + 0.5, -0.35, f"#{j+1}\n{cid.split('_')[1]}", ha="center", va="top", fontsize=8)
    ax.text(n_c + 0.25, n_s + 0.0, "出现\n频次", ha="left", va="center", fontsize=8, color=C["grey"])
    ax.set_xlim(-3.4, n_c + 1.2); ax.set_ylim(-1.9, n_s + 0.95)
    ax.axis("off")
    # genus legend
    handles = [mpatches.Patch(color=C["blue"], label="Lactobacillus（乳杆菌）"),
               mpatches.Patch(color=C["green"], label="Bifidobacterium（双歧杆菌）"),
               mpatches.Patch(color=C["orange"], label="Bacillus（芽孢杆菌）"),
               mpatches.Patch(color=C["purple"], label="其他乳酸菌属")]
    ax.legend(handles=handles, loc="upper center", bbox_to_anchor=(0.42, -0.04),
              ncol=4, fontsize=8.5, frameon=False)
    ax.set_title("图9  预测的 Top-10 益生菌减脂组合及其菌株构成（行=菌株，列=组合）", y=1.02)
    save(fig, "fig9_strain_membership.png")


if __name__ == "__main__":
    fig1_pipeline(); fig2_obesity_model(); fig3_forest(); fig4_gate_funnel()
    fig5_balanced_sensitivity(); fig6_combinations(); fig7_mechanism(); fig8_ipd_funnel()
    fig9_strain_membership()
    print("all figures done")
