"""Assess the predictive capability of bile-acid metabolism for lean enrichment.

The combination scorer gives bile salt hydrolase (BSH) a 16% weight as the
"cholesterol-lowering" axis. This script tests whether that is justified.

Axes tested
  1. BSH (deconjugation)      - current annotation, genus-level (8/90 genera)
  2. 7a-dehydroxylation       - secondary bile acid production (DCA/LCA); a
                                distinct pathway absent from the current
                                annotation, restricted to a few Clostridia
  3. bile tolerance / exposure- taxa that thrive under high bile (Bilophila uses
                                taurine from taurocholate; Alistipes is bile
                                resistant)
Benchmarks against propionate and diversity association in the same framework.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import LeaveOneGroupOut
from sklearn.metrics import roc_auc_score
from sklearn.preprocessing import StandardScaler

ROOT = Path(__file__).resolve().parents[2]
PR = ROOT / "results/prediction_results"
OUT = PR / "bile_acid"

# --- 7alpha-dehydroxylating species (secondary bile acid producers) ---
DEHYDROX_SPECIES = {"Clostridium_scindens", "Clostridium_hylemonae", "Clostridium_hiranonis",
                    "Peptacetobacter_hiranonis", "Clostridium_sordellii", "Clostridium_leptum"}
# --- bile-tolerant / bile-exposed taxa ---
BILE_TOLERANT_GENERA = {"Bilophila", "Alistipes", "Bacteroides", "Parabacteroides",
                        "Odoribacter", "Escherichia", "Enterococcus"}
BILE_SENSITIVE_GENERA = {"Faecalibacterium", "Roseburia", "Eubacterium", "Butyrivibrio",
                         "Coprococcus", "Blautia", "Bifidobacterium"}


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    da = pd.read_csv(PR / "we_healthy/differential_abundance_adjusted.csv")
    guild = pd.read_csv(ROOT / "data/strain_genome/genus_functional_guild_reference_20260613.csv").set_index("genus")
    div = pd.read_csv(PR / "lean_factors/diversity_association_all_species.csv")[["species", "diversity_rho"]]

    d = da[da.fdr < 0.05].copy()
    d["genus"] = d.species.str.split("_").str[0]
    d["y"] = (d.direction == "lean_enriched").astype(int)
    d = d.merge(div, on="species", how="left")
    for col, g in [("bsh", "bsh_potential"), ("propionate", "propionate_potential"),
                   ("butyrate", "butyrate_scfa_potential")]:
        d[col] = d.genus.map(lambda x: float(guild.loc[x, g]) if x in guild.index else np.nan)
    d["dehydroxylation"] = d.species.isin(DEHYDROX_SPECIES).astype(int)
    d["bile_tolerant"] = d.genus.isin(BILE_TOLERANT_GENERA).astype(int)
    d["bile_sensitive"] = d.genus.isin(BILE_SENSITIVE_GENERA).astype(int)
    d = d.dropna(subset=["bsh"])

    print(f"=== 评估队列：{len(d)} 个 FDR<0.05 物种（瘦人富集 {int(d.y.sum())} / 肥胖富集 {int((1-d.y).sum())}）===\n")

    # ---------- Part A: BSH discriminative power ----------
    print("【A】BSH（胆盐水解酶）对瘦人富集的判别力")
    rows = []
    for name, col in [("BSH 潜能(0/1/2)", "bsh"), ("BSH 阳性(二值)", None),
                      ("7α-脱羟基(次级胆汁酸)", "dehydroxylation"),
                      ("胆汁耐受属", "bile_tolerant"), ("胆汁敏感属", "bile_sensitive"),
                      ("丙酸潜能(对照)", "propionate"), ("多样性关联(对照)", "diversity_rho")]:
        v = (d.bsh > 0).astype(float).to_numpy() if col is None else d[col].to_numpy(float)
        if np.nanstd(v) == 0:
            continue
        ok = np.isfinite(v)
        a = roc_auc_score(d.y[ok], v[ok])
        lean_v, ob_v = v[ok][d.y[ok] == 1], v[ok][d.y[ok] == 0]
        try:
            _, p = stats.mannwhitneyu(lean_v, ob_v)
        except ValueError:
            p = np.nan
        rows.append({"axis": name, "auc": round(float(max(a, 1 - a)), 3),
                     "direction": "越高越瘦" if a > 0.5 else "越高越胖",
                     "lean_mean": round(float(lean_v.mean()), 3),
                     "obese_mean": round(float(ob_v.mean()), 3), "p": float(p)})
        print(f"  {name:24} AUC={rows[-1]['auc']:.3f}  {rows[-1]['direction']}  "
              f"瘦={rows[-1]['lean_mean']:.3f} 胖={rows[-1]['obese_mean']:.3f}  P={p:.3f}")
    A = pd.DataFrame(rows)

    # ---------- Part B: which BSH+ species, and where do they land ----------
    print("\n【B】BSH 阳性物种的实际归属")
    bsh_pos = d[d.bsh > 0][["species", "genus", "bsh", "direction", "fold_change_obese_vs_lean",
                            "meta_g", "fdr", "diversity_rho"]].sort_values("bsh", ascending=False)
    if len(bsh_pos):
        for r in bsh_pos.itertuples():
            lab = "瘦人富集" if r.direction == "lean_enriched" else "肥胖富集"
            print(f"  {r.species[:34]:34} BSH={int(r.bsh)} {lab:8} FC={r.fold_change_obese_vs_lean:.2f} "
                  f"多样性ρ={r.diversity_rho if pd.notna(r.diversity_rho) else float('nan'):+.2f}")
    print(f"  BSH 阳性物种数: {len(bsh_pos)} / {len(d)}  "
          f"（瘦人富集 {int((bsh_pos.direction=='lean_enriched').sum())}，肥胖富集 {int((bsh_pos.direction=='obese_enriched').sum())}）")
    bsh_pos.to_csv(OUT / "bsh_positive_species.csv", index=False, encoding="utf-8-sig")

    # coverage check on the whole tested set (not just significant)
    all_t = da.copy(); all_t["genus"] = all_t.species.str.split("_").str[0]
    all_t["bsh"] = all_t.genus.map(lambda x: float(guild.loc[x, "bsh_potential"]) if x in guild.index else np.nan)
    cov = {"物种总数": int(len(all_t)), "有BSH注释": int(all_t.bsh.notna().sum()),
           "BSH阳性": int((all_t.bsh > 0).sum()), "强BSH(=2)": int((all_t.bsh == 2).sum())}
    print(f"\n  注释覆盖：{cov}")

    # ---------- Part C: cross-genus generalisation ----------
    print("\n【C】跨属泛化能力（留一属 CV）")
    combos = {"仅 BSH": ["bsh"], "胆汁酸全轴(BSH+脱羟基+耐受)": ["bsh", "dehydroxylation", "bile_tolerant"],
              "仅丙酸(对照)": ["propionate"], "仅多样性关联(对照)": ["diversity_rho"],
              "多样性+BSH": ["diversity_rho", "bsh"]}
    gen = {}
    for name, feats in combos.items():
        sub = d.dropna(subset=feats)
        X = sub[feats].to_numpy(float); y = sub.y.to_numpy(); g = sub.genus.to_numpy()
        if len(np.unique(y)) < 2:
            continue
        oof = np.full(len(y), np.nan)
        for tr, te in LeaveOneGroupOut().split(X, y, g):
            if len(np.unique(y[tr])) < 2:
                continue
            sc = StandardScaler().fit(X[tr])
            oof[te] = LogisticRegression(C=0.5, max_iter=3000).fit(sc.transform(X[tr]), y[tr]).predict_proba(sc.transform(X[te]))[:, 1]
        ok = np.isfinite(oof)
        gen[name] = round(float(roc_auc_score(y[ok], oof[ok])), 3)
        print(f"  {name:28} AUC={gen[name]:.3f}")

    # ---------- Part D: RCT cholesterol evidence availability ----------
    eff = pd.read_csv(ROOT / "data/intervention_data/continuous_effect_sizes.upgrade_20260625.csv")
    lip = eff[eff.outcome_domain.astype(str).str.contains("lipid", na=False)]
    arms = pd.read_csv(ROOT / "data/intervention_data/study_arm_registry.upgrade_20260625.csv")
    linked = lip.merge(arms[["study_id", "species"]].dropna().drop_duplicates("study_id"), on="study_id", how="inner")
    rct = {"血脂结局行": int(len(lip)), "高置信行": int((lip.confidence == "high").sum()),
           "可关联干预菌种的行": int(len(linked)),
           "含乳杆菌(强BSH)的行": int(linked.species.astype(str).str.contains("Lactobacillus|Lactiplantibacillus|Lacticaseibacillus").sum()),
           "可检验": bool(len(linked) >= 10)}
    print(f"\n【D】RCT 胆固醇结局证据：{rct}")

    A.to_csv(OUT / "bile_axis_discriminative_power.csv", index=False, encoding="utf-8-sig")
    (OUT / "assessment.json").write_text(json.dumps(
        {"n_species": int(len(d)), "single_axis": A.to_dict("records"),
         "bsh_positive_n": int(len(bsh_pos)),
         "bsh_positive_lean": int((bsh_pos.direction == "lean_enriched").sum()),
         "bsh_positive_obese": int((bsh_pos.direction == "obese_enriched").sum()),
         "annotation_coverage": cov, "cross_genus_auc": gen,
         "rct_cholesterol_evidence": rct}, indent=2, ensure_ascii=False), encoding="utf-8")
    print("\nwrote", OUT.relative_to(ROOT))


if __name__ == "__main__":
    main()
