const fs = require("fs");
const path = require("path");
const { Document, Packer, Paragraph, TextRun, Table, TableRow, TableCell,
        AlignmentType, LevelFormat, HeadingLevel, BorderStyle, WidthType,
        ShadingType, ImageRun, PageBreak, PageNumber, Footer } = require("docx");

const ROOT = "D:/strain screen mix";
const FIG = path.join(ROOT, "results/paper_figures");
const OUT = path.join(ROOT, "docs/ProSlim_减脂菌株组合研发框架_论文_20260625.docx");
const SERIF = "SimSun", HEI = "SimHei";
const A4W = 11906, A4H = 16838, MARGIN = 1440, CONTENT = A4W - 2 * MARGIN;

const RATIO = { fig0_framework: 0.528, fig2_obesity_model: 0.476, fig11_diffabund_volcano: 0.681,
  fig12_lean_screen: 0.633, fig13_synergistic_combos: 0.588, fig14_safety_gate: 0.596,
  fig4_gate_funnel: 0.579, fig8_ipd_funnel: 0.426, fig10_lean_vs_obese_diffabund: 0.667 };

function parseRuns(text, f, s) {
  return text.split(/(\*\*[^*]+\*\*)/g).filter(Boolean).map(p => p.startsWith("**")
    ? new TextRun({ text: p.slice(2, -2), bold: true, font: f, size: s })
    : new TextRun({ text: p, font: f, size: s }));
}
const body = (t, o = {}) => new Paragraph({ spacing: { line: 360, after: 120 },
  alignment: AlignmentType.JUSTIFIED, indent: o.noIndent ? undefined : { firstLine: 480 },
  children: parseRuns(t, SERIF, 21) });
const h1 = (t) => new Paragraph({ heading: HeadingLevel.HEADING_1, spacing: { before: 320, after: 160 },
  children: [new TextRun({ text: t, font: HEI, size: 30, bold: true })] });
const h2 = (t) => new Paragraph({ heading: HeadingLevel.HEADING_2, spacing: { before: 220, after: 120 },
  children: [new TextRun({ text: t, font: HEI, size: 25, bold: true })] });
function figure(name, cap, w = 560) {
  const h = Math.round(w * RATIO[name]);
  return [new Paragraph({ alignment: AlignmentType.CENTER, spacing: { before: 160, after: 60 },
      children: [new ImageRun({ type: "png", data: fs.readFileSync(path.join(FIG, name + ".png")),
        transformation: { width: w, height: h }, altText: { title: cap, description: cap, name } })] }),
    new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 200 },
      children: [new TextRun({ text: cap, font: HEI, size: 19, bold: true })] })];
}
const cb = { style: BorderStyle.SINGLE, size: 1, color: "BBBBBB" };
const bd = { top: cb, bottom: cb, left: cb, right: cb };
const tcell = (t, w, head, ac) => new TableCell({ borders: bd, width: { size: w, type: WidthType.DXA },
  shading: { fill: head ? "D9E2F0" : "FFFFFF", type: ShadingType.CLEAR },
  margins: { top: 60, bottom: 60, left: 90, right: 90 },
  children: [new Paragraph({ alignment: ac ? AlignmentType.CENTER : AlignmentType.LEFT,
    children: [new TextRun({ text: t, font: SERIF, size: 17, bold: head })] })] });
function table(hd, rows, w) {
  const mk = (c, h) => new TableRow({ tableHeader: h, children: c.map((x, i) => tcell(x, w[i], h, i > 0)) });
  return new Table({ width: { size: CONTENT, type: WidthType.DXA }, columnWidths: w,
    rows: [mk(hd, true), ...rows.map(r => mk(r, false))] });
}
const cap = (t) => new Paragraph({ alignment: AlignmentType.CENTER, spacing: { before: 80, after: 200 },
  children: [new TextRun({ text: t, font: HEI, size: 18, bold: true })] });

const C = [];
// Title
C.push(new Paragraph({ alignment: AlignmentType.CENTER, spacing: { before: 600, after: 120 },
  children: [new TextRun({ text: "数据驱动的益生菌减脂菌株组合研发框架", font: HEI, size: 40, bold: true })] }));
C.push(new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 80 },
  children: [new TextRun({ text: "AI 临床数据筛选 — 菌株机制细筛 — 菌株效果验证", font: HEI, size: 26, bold: true })] }));
C.push(new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 60 },
  children: [new TextRun({ text: "ProSlim-Microbiome-AI 项目组", font: SERIF, size: 22 })] }));
C.push(new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 360 },
  children: [new TextRun({ text: "2026 年 6 月 25 日", font: SERIF, size: 20 })] }));

// Abstract
C.push(new Paragraph({ spacing: { before: 120, after: 100 }, children: [new TextRun({ text: "摘要", font: HEI, size: 24, bold: true })] }));
C.push(body("**背景：**益生菌减脂的临床证据高度异质，既往以“已测配方证据”为骨架的组合推荐存在两个根本缺陷：组合常由单一产品的捆绑证据驱动（而非数据支持的协同），且所用菌属在瘦/胖人群间几乎无差异。本研究重构为一个数据驱动、机制接地、可诚实验证的三阶段框架。", { noIndent: true }));
C.push(body("**方法：**(一) AI 临床数据筛选——以 8 304 样本 / 45 研究训练肥胖状态 AI 模型，并在 15 项同时含瘦(无胰岛素抵抗)与肥胖人群的研究内求差、跨研究聚合，得到方向稳健的差异菌；(二) 菌株机制细筛——对瘦人富集菌按功能、机制互补与可培养性打分，组合以覆盖丁酸/丙酸/黏液/BSH 多轴为协同标准，并过基因组安全门（AMR/毒力/MGE 知识先验 + 基因组可得性）；(三) 菌株效果验证——以留一研究/留一受试者验证与越基线门控为证据标准，建立个体应答模型脚手架与验证数据获取路径。", { noIndent: true }));
C.push(body("**结果：**肥胖分类分组 AUC 0.729；瘦人富集得 53 个方向稳健物种（≥11/15 研究一致），稳健信号集中于丁酸产生菌与 Akkermansia（黏液轴）。机制细筛得到协同组合，首选为肠拟杆菌 + 嗜黏蛋白阿克曼氏菌 + 人肠巴恩斯氏菌 + 丛毛丁酸弧菌（覆盖全部四条机制轴，综合分 0.821），全部可培养。安全门：候选均无致病属、均有分离基因组（真版筛查可后续运行），其中拟杆菌属被标记 MGE 高、须重点筛移动 AMR。", { noIndent: true }));
C.push(body("**结论：**本框架以数据驱动定标取代证据捆绑，以机制互补定义协同，以诚实门控约束疗效断言。组合推荐以候选定标交付，疗效仍需个体级数据或前瞻 RCT 验证。", { noIndent: true }));
C.push(new Paragraph({ spacing: { before: 120, after: 240 }, children: [
  new TextRun({ text: "关键词：", font: HEI, size: 20, bold: true }),
  new TextRun({ text: "肠道菌群；益生菌减脂；差异丰度；机制互补；短链脂肪酸；基因组安全门；诚实验证", font: SERIF, size: 20 })] }));
C.push(new Paragraph({ children: [new PageBreak()] }));

// 1 引言
C.push(h1("1  引言"));
C.push(body("肥胖与肠道菌群密切相关，益生菌、合生元与膳食纤维被寄望于辅助减脂，但已发表 RCT 在菌株、剂量、人群与结局上高度异质。既往“菌株组合推荐”常直接断言疗效，且其组合往往来自单一临床产品的捆绑证据（例如把一篇试验所测的固定多株配方整体纳入排序），这既非数据证明的协同，所用菌属在瘦/胖人群菌群差异上也并不突出。本研究将思路重构为三阶段、数据驱动的研发框架：以 AI 临床数据筛选确定有人群差异依据的候选菌，以菌株机制细筛设计机制互补且安全的协同组合，以诚实验证门控约束效果断言。"));

// 2 框架
C.push(h1("2  总体框架"));
C.push(body("框架由三个阶段顺序构成（图 1）：阶段一以公开临床菌群数据筛出瘦人富集候选菌；阶段二对候选菌做功能/互补/可培养与安全筛选，产出机制互补的安全组合；阶段三以严格验证标准与个体应答模型约束并指引效果验证。贯穿原则是：数据驱动定标、机制互补、诚实门控（疗效门未过即关闭）。"));
C.push(...figure("fig0_framework", "图 1  数据驱动三阶段研发框架"));

// 3 Stage 1
C.push(h1("3  阶段一：AI 临床数据筛选"));
C.push(h2("3.1  肥胖状态 AI 模型"));
C.push(body("以 8 304 个样本、45 项研究、206 个物种相对丰度训练肥胖分类与 BMI 回归，按研究分组留一验证为主。肥胖分类分组 AUC 0.729（随机拆分 0.825，差距揭示批次/地域混杂的乐观偏差，图 2），表明菌群组成对肥胖状态有可泛化信号，可用于人群分层与候选优先级。"));
C.push(...figure("fig2_obesity_model", "图 2  肥胖状态 AI 模型：分组验证有信号且乐观差距可控"));
C.push(h2("3.2  瘦(无胰岛素抵抗) vs 胖 差异丰度筛选"));
C.push(body("将瘦人(无胰岛素抵抗)定义为 lean 且 healthy（排除 T2D/IGT），与 obesity 对比。为避免 45 研究的批次混杂，仅用同时含 ≥10 例两组的 15 项研究，在研究内求差、跨研究取中位聚合，仅信任方向 ≥11/15 一致者，得 83 个稳健差异菌（瘦人富集 53、胖人富集 30，图 3）。稳健的瘦人富集信号集中于丁酸产生菌（如 *Butyrivibrio*、*Odoribacter*）与 *Akkermansia muciniphila*（黏液轴）；稳健胖人富集为 *Ruminococcus gnavus*、*Veillonella atypica* 等。值得注意的是，既往组合所用乳杆菌属在此对比中差异极小，印证证据捆绑路线与人群信号的脱节。"));
C.push(...figure("fig11_diffabund_volcano", "图 3  瘦 vs 胖 全部差异菌总览（火山图）"));

// 4 Stage 2
C.push(h1("4  阶段二：菌株机制细筛"));
C.push(h2("4.1  功能 / 互补 / 可培养性筛选"));
C.push(body("对 53 个瘦人富集菌按三维度打分：功能相关（属级 SCFA/黏液/BSH 与减脂机制，扣减促炎菌）、机制互补（奖励覆盖丁酸/丙酸/黏液——既往乳杆菌/双歧组合仅覆盖 BSH+乳酸的盲区）、可培养性（命名分离株先验）。促炎菌 *Bilophila*、*Desulfovibrio* 与仅 MAG 物种被排除（图 4）。"));
C.push(...figure("fig12_lean_screen", "图 4  瘦人富集菌的功能/互补/可培养性筛选"));
C.push(h2("4.2  协同组合打分"));
C.push(body("协同被操作化为机制轴互补——组合按覆盖的不同功能轴（丁酸·丙酸·黏液·BSH）计分，要求 ≥3 轴，并综合减脂潜力、降胆固醇能力与菌株性质。首选组合覆盖全部四轴，综合分 0.821（图 5、表 1）。"));
C.push(...figure("fig13_synergistic_combos", "图 5  数据驱动的协同减脂组合（Top 6，维度分解）"));
C.push(table(["排名", "组合成员", "机制轴", "综合分"], [
  ["1", "肠拟杆菌 + 嗜黏蛋白阿克曼氏菌 + 人肠巴恩斯氏菌 + 丛毛丁酸弧菌", "丁+丙+黏+BSH", "0.821"],
  ["7", "肠拟杆菌 + 人肠巴恩斯氏菌 + 丛毛丁酸弧菌", "丁+丙+黏+BSH", "0.815"],
  ["8", "肠拟杆菌 + 嗜黏蛋白阿克曼氏菌 + 丛毛丁酸弧菌", "丁+丙+黏+BSH", "0.815"],
], [800, 5800, 1626, 800]));
C.push(cap("表 1  代表性协同组合（覆盖四条机制轴）"));
C.push(h2("4.3  基因组安全门（AMR / 毒力 / MGE）"));
C.push(body("对组合候选过基因组安全门：以 EFSA QPS + 临床微生物学知识先验给出风险类别，并查 NCBI 基因组可得性（决定真版筛查是否可运行）。14 株候选均无致病属、均有分离基因组（真版筛查可后续运行）；*Akkermansia*、*Odoribacter* 具 LBP 人体前例（最低门槛），而拟杆菌属（含降胆固醇株肠拟杆菌）被标记 MGE 高、须重点筛查可移动 tetQ/ermF/cfxA（图 6）。"));
C.push(...figure("fig14_safety_gate", "图 6  协同候选菌的基因组安全门分流状态矩阵"));
C.push(body("**注：** 本环境不运行真版 AMRFinderPlus/abricate-CARD-VFDB；此为知识先验 + 基因组可得性分流，用于决定先筛谁并标注已知风险，不替代菌株级真版筛查。", { noIndent: true }));

// 5 Stage 3
C.push(h1("5  阶段三：菌株效果验证"));
C.push(h2("5.1  诚实验证门控"));
C.push(body("效果断言受统一门控约束：连续效应模型须在留一研究下越过均值基线方可启用组合疗效排序。从 137 条效应行经层层筛选仅得 19 项独立研究，4 个可建模 stratum 中仅 1 个越基线，故组合疗效排序门保持关闭（图 7）。这是数据约束下的正确表述，而非缺陷——本框架的组合以候选定标交付，不作疗效概率断言。"));
C.push(...figure("fig4_gate_funnel", "图 7  证据到疗效门的诚实漏斗"));
C.push(h2("5.2  个体应答模型"));
C.push(body("个体减脂应答的真正预测需个体级数据（同一批人的基线菌群 + 各自结局）。本研究构建了留一受试者验证的个体应答建模脚手架，并以合成自检证明其能识别真信号、拒绝纯噪声，待对口数据即可运行。"));
C.push(h2("5.3  验证数据获取（IPD）"));
C.push(body("以 EuropePMC + ENA + 数据链 API 三轮（含结局过滤）搜寻沉积了每受试者测序的减脂干预 RCT（图 8）。结论：公开库中尚无同时具备每受试者测序与减脂结局的益生菌 RCT；唯一群体对口且配对的沉积为低卡饮食队列。这把验证瓶颈精确定位为个体级数据的缺失，指明经作者协作或前瞻试验创造 IPD 的路径。效果验证的整体顺序为：基因组安全筛查 → 体外 SCFA/BSH/黏附功能确认 → 动物模型 → 个体级 IPD / 前瞻 RCT。"));
C.push(...figure("fig8_ipd_funnel", "图 8  验证数据获取（IPD）三轮搜寻与文献级核验"));

// 6 讨论
C.push(h1("6  讨论"));
C.push(body("本框架相对既往路线的根本转变在于：以**数据驱动定标**取代**证据捆绑**。我们删除了以单一产品固定配方为骨架的组合方向——该方向产生的乳杆菌三联实为单篇试验的产品绑定，并非数据证明的协同，且其菌属在瘦/胖差异上近乎为零。取而代之，候选菌来自有人群差异依据的瘦人富集信号，组合以机制互补（丁酸/丙酸/黏液/BSH）定义协同。"));
C.push(body("数据驱动的瘦人富集菌恰好落在丁酸与黏液轴，正是既往乳杆菌/双歧组合的机制盲区，这从机制上解释了证据捆绑路线的局限。安全门进一步揭示数据驱动候选的现实约束：多为新型益生菌/严格厌氧，须先过真版基因组筛查，且拟杆菌属携带可移动 AMR 的风险需重点排查。诚实门控与 IPD 缺失分析则把效果验证从“调模型”锁定到“采数据”。"));

// 7 结论
C.push(h1("7  结论"));
C.push(body("数据驱动的三阶段框架以人群差异定标候选、以机制互补设计协同、以诚实门控约束断言，给出可落地的安全协同组合候选与清晰的验证路线。下一步为：在生信环境运行真版基因组安全筛查，开展体外与动物验证，并经作者协作/前瞻试验获取个体级数据以最终验证减脂效果。"));

// 8 局限
C.push(h1("8  局限性与诚实声明"));
["差异丰度为横断面关联，非因果；菌株补充能否致减重需 IPD/前瞻 RCT。",
 "菌株功能为属级先验（如真杆菌属异质，部分丁酸功能可能被低估），需菌株级基因组注释确认。",
 "安全门为知识先验 + 基因组可得性，未运行真版 AMRFinder/VFDB；真版筛查须在生信环境完成。",
 "肥胖状态模型仅内部分组验证，存在乐观偏差；尚无独立外部数据集。",
 "组合为候选定标，非疗效/响应概率；疗效门保持关闭。",
].forEach(t => C.push(new Paragraph({ numbering: { reference: "lim", level: 0 },
  spacing: { line: 340, after: 60 }, children: [new TextRun({ text: t, font: SERIF, size: 21 })] })));

// 9 数据
C.push(h1("9  数据与代码可用性"));
C.push(body("代码、数据产出与图表生成脚本纳入项目仓库（分支 codex/archive-supplement-pipeline）。差异丰度与瘦人富集筛选见 results/prediction_results/ 下 lean_vs_obese 与 lean_enriched 系列；协同组合与安全门见 synergistic 与 safety_gate 系列；图表生成见 scripts/visualization/。", { noIndent: true }));

const doc = new Document({
  styles: { default: { document: { run: { font: SERIF, size: 21 } } },
    paragraphStyles: [
      { id: "Heading1", name: "Heading 1", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { size: 30, bold: true, font: HEI }, paragraph: { spacing: { before: 320, after: 160 }, outlineLevel: 0 } },
      { id: "Heading2", name: "Heading 2", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { size: 25, bold: true, font: HEI }, paragraph: { spacing: { before: 220, after: 120 }, outlineLevel: 1 } }] },
  numbering: { config: [{ reference: "lim", levels: [{ level: 0, format: LevelFormat.DECIMAL, text: "%1.",
    alignment: AlignmentType.LEFT, style: { paragraph: { indent: { left: 600, hanging: 360 } } } }] }] },
  sections: [{ properties: { page: { size: { width: A4W, height: A4H }, margin: { top: MARGIN, right: MARGIN, bottom: MARGIN, left: MARGIN } } },
    footers: { default: new Footer({ children: [new Paragraph({ alignment: AlignmentType.CENTER,
      children: [new TextRun({ text: "第 ", font: SERIF, size: 18 }), new TextRun({ children: [PageNumber.CURRENT], font: SERIF, size: 18 }), new TextRun({ text: " 页", font: SERIF, size: 18 })] })] }) },
    children: C }] });
Packer.toBuffer(doc).then(b => { fs.writeFileSync(OUT, b); console.log("wrote", OUT, b.length); });
