"""Annotated list of lean-enriched species: in-vivo abundance (lean & obese),
Chinese name, and culturability."""
from __future__ import annotations
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
PR = ROOT / "results/prediction_results"

GENUS_CN = {
    "Akkermansia": "阿克曼氏菌属", "Alistipes": "另枝菌属",
    "Anaeromassilibacillus": "厌氧马赛杆菌属", "Bacteroides": "拟杆菌属",
    "Barnesiella": "巴恩斯氏菌属", "Bifidobacterium": "双歧杆菌属",
    "Bilophila": "嗜胆菌属", "Butyricimonas": "丁酸单胞菌属",
    "Butyrivibrio": "丁酸弧菌属", "Clostridium": "梭菌属",
    "Coprobacter": "粪杆菌属", "Coprococcus": "粪球菌属",
    "Desulfovibrio": "脱硫弧菌属", "Dialister": "戴阿利斯特杆菌属",
    "Dielma": "迪尔玛菌属", "Eubacterium": "真杆菌属",
    "Firmicutes": "厚壁菌门未定属", "Fretibacterium": "弗雷特杆菌属",
    "Gemmiger": "芽生菌属", "Intestinimonas": "肠单胞菌属",
    "Lactobacillus": "乳杆菌属", "Methanobrevibacter": "甲烷短杆菌属",
    "Odoribacter": "臭杆菌属", "Oscillibacter": "颤杆菌属",
    "Parabacteroides": "副拟杆菌属", "Parasutterella": "副萨特氏菌属",
    "Phascolarctobacterium": "考拉杆菌属", "Romboutsia": "伦伯茨氏菌属",
    "Roseburia": "罗斯氏菌属", "Ruminococcaceae": "瘤胃球菌科未定属",
    "Ruminococcus": "瘤胃球菌属", "Ruthenibacterium": "卢森尼杆菌属",
    "Turicibacter": "苏黎世杆菌属", "Victivallis": "食物谷菌属",
}
SPECIES_CN = {
    "Akkermansia_muciniphila": "嗜黏蛋白阿克曼氏菌",
    "Methanobrevibacter_smithii": "史氏甲烷短杆菌",
    "Bacteroides_intestinalis": "肠拟杆菌",
    "Odoribacter_splanchnicus": "内脏臭杆菌",
    "Intestinimonas_butyriciproducens": "产丁酸肠单胞菌",
    "Barnesiella_intestinihominis": "人肠巴恩斯氏菌",
    "Phascolarctobacterium_succinatutens": "食琥珀酸考拉杆菌",
    "Gemmiger_formicilis": "甲酸芽生菌",
    "Bilophila_wadsworthia": "沃兹沃思嗜胆菌",
    "Butyrivibrio_crossotus": "丛毛丁酸弧菌",
}
CULT_CN = {
    "culturable_easy": "易培养（常规厌氧）",
    "culturable_commercial": "可培养·已商业化",
    "culturable_anaerobe": "可培养（严格厌氧）",
    "fastidious_anaerobe": "苛养厌氧（较难培养）",
    "archaea_special_culture": "产甲烷古菌（特殊培养）",
    "uncultured_or_MAG": "尚未培养 / 仅宏基因组拼接(MAG)",
    "named_isolate_likely": "有命名分离株（可培养性待证）",
}


def cn_name(species: str, genus: str) -> str:
    if species in SPECIES_CN:
        return SPECIES_CN[species]
    g = GENUS_CN.get(genus, genus)
    epithet = species.split("_", 1)[1] if "_" in species else ""
    return f"{g} {epithet}".strip()


def axes(row) -> str:
    a = []
    if row["butyrate"]: a.append("丁酸")
    if row["propionate"]: a.append("丙酸")
    if row["mucin"]: a.append("黏液")
    if row["bsh"]: a.append("BSH")
    return "/".join(a) if a else "—"


def main() -> None:
    diff = pd.read_csv(PR / "lean_vs_obese_trusted_differential_20260625.csv")
    scr = pd.read_csv(PR / "lean_enriched_screened_candidates_20260625.csv")
    le = diff[diff["direction"] == "lean_enriched"].merge(
        scr[["species", "butyrate", "propionate", "mucin", "bsh",
             "culturability_class", "composite_screen_score"]],
        on="species", how="left")
    le["genus"] = le["species"].str.split("_").str[0]
    le["中文名称"] = [cn_name(s, g) for s, g in zip(le["species"], le["genus"])]
    le["可培养性"] = le["culturability_class"].map(CULT_CN)
    le["机制轴"] = le.apply(axes, axis=1)
    le = le.sort_values("pooled_cohens_d", ascending=False)

    out = le[["species", "中文名称", "mean_abund_lean_pp", "mean_abund_obese_pp",
              "median_abund_diff_pp", "median_log2fc", "pooled_cohens_d",
              "studies_consistent", "机制轴", "可培养性", "composite_screen_score"]].rename(columns={
        "species": "物种(拉丁名)", "mean_abund_lean_pp": "瘦人丰度_pp",
        "mean_abund_obese_pp": "胖人丰度_pp", "median_abund_diff_pp": "丰度差_pp",
        "median_log2fc": "log2FC", "pooled_cohens_d": "效应d",
        "studies_consistent": "一致研究数", "composite_screen_score": "综合筛选分"})
    fp = PR / "lean_enriched_annotated_list_20260625.csv"
    out.to_csv(fp, index=False, encoding="utf-8-sig")

    print(f"lean-enriched annotated: {len(out)} species")
    print(f"\n{'物种':32}{'中文名':18}{'瘦%':>7}{'胖%':>7}{'d':>7}  {'可培养性'}")
    for _, r in out.head(20).iterrows():
        print(f"{r['物种(拉丁名)'][:31]:32}{r['中文名称'][:16]:18}"
              f"{r['瘦人丰度_pp']:>7.3f}{r['胖人丰度_pp']:>7.3f}{r['效应d']:>7.2f}  {r['可培养性']}")
    print("\nwrote", fp.relative_to(ROOT))


if __name__ == "__main__":
    main()
