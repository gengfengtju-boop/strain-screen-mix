const fs = require("fs");
const path = require("path");
const { Document, Packer, Paragraph, TextRun, Table, TableRow, TableCell,
        AlignmentType, LevelFormat, HeadingLevel, BorderStyle, WidthType,
        ShadingType, ImageRun, PageBreak, PageNumber, Footer } = require("docx");

const ROOT = "D:/strain screen mix";
const CR = path.join(ROOT, "results/combination_recommendations");
const OUT = path.join(ROOT, "docs/食源性益生菌减脂潜力预测_研究论文_20260625.docx");
const SERIF = "SimSun", HEI = "SimHei";
const A4W = 11906, A4H = 16838, MARGIN = 1418, CONTENT = A4W - 2 * MARGIN;

const J = (p) => JSON.parse(fs.readFileSync(p, "utf8"));
function csv(p) {
  const t = fs.readFileSync(p, "utf8").replace(/^\uFEFF/, "").trim().split(/\r?\n/);
  const h = t[0].split(",");
  return t.slice(1).map(l => {
    // naive split is fine: no embedded commas in these files except cohort_detail
    const v = l.split(","); const o = {};
    h.forEach((k, i) => o[k] = v[i]); return o;
  });
}
const S3 = J(path.join(CR, "foodgrade_v3_summary_20260625.json"));
const SR = J(path.join(CR, "foodgrade_single_strain_ranking_summary_20260625.json"));
const RANK = csv(path.join(CR, "foodgrade_single_strain_ranking_20260625.csv"));
const COMB = csv(path.join(CR, "foodgrade_v3_combinations_20260625.csv"));

function runs(t, f, s) {
  return t.split(/(\*\*[^*]+\*\*)/g).filter(Boolean).map(p => p.startsWith("**")
    ? new TextRun({ text: p.slice(2, -2), bold: true, font: f, size: s })
    : new TextRun({ text: p, font: f, size: s }));
}
const body = (t, o = {}) => new Paragraph({ spacing: { line: 340, after: 100 },
  alignment: AlignmentType.JUSTIFIED, indent: o.noIndent ? undefined : { firstLine: 440 },
  children: runs(t, SERIF, 21) });
const h1 = (t) => new Paragraph({ heading: HeadingLevel.HEADING_1, spacing: { before: 300, after: 140 },
  children: [new TextRun({ text: t, font: HEI, size: 28, bold: true })] });
const h2 = (t) => new Paragraph({ heading: HeadingLevel.HEADING_2, spacing: { before: 190, after: 100 },
  children: [new TextRun({ text: t, font: HEI, size: 23, bold: true })] });
const cb = { style: BorderStyle.SINGLE, size: 1, color: "BBBBBB" };
const bd = { top: cb, bottom: cb, left: cb, right: cb };
const cell = (t, w, head, ac, fill) => new TableCell({ borders: bd, width: { size: w, type: WidthType.DXA },
  shading: { fill: head ? "D9E2F0" : (fill || "FFFFFF"), type: ShadingType.CLEAR },
  margins: { top: 44, bottom: 44, left: 66, right: 66 },
  children: [new Paragraph({ alignment: ac ? AlignmentType.CENTER : AlignmentType.LEFT,
    children: [new TextRun({ text: String(t), font: SERIF, size: 15, bold: head })] })] });
function table(hd, rows, w, fills) {
  const mk = (c, h, fill) => new TableRow({ tableHeader: h,
    children: c.map((x, i) => cell(x, w[i], h, i > 0, fill)) });
  return new Table({ width: { size: CONTENT, type: WidthType.DXA }, columnWidths: w,
    rows: [mk(hd, true), ...rows.map((r, i) => mk(r, false, fills ? fills[i] : null))] });
}
const cap = (t) => new Paragraph({ alignment: AlignmentType.CENTER, spacing: { before: 60, after: 170 },
  children: [new TextRun({ text: t, font: HEI, size: 16, bold: true })] });
function figure(name, capt, ratio, w = 590) {
  return [new Paragraph({ alignment: AlignmentType.CENTER, spacing: { before: 140, after: 45 },
    children: [new ImageRun({ type: "png", data: fs.readFileSync(path.join(ROOT, "results/paper_figures", name)),
      transformation: { width: w, height: Math.round(w * ratio) },
      altText: { title: capt, description: capt, name } })] }),
    new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 180 },
      children: [new TextRun({ text: capt, font: HEI, size: 16, bold: true })] })];
}
const C = [];

// ===== 封面 =====
C.push(new Paragraph({ alignment: AlignmentType.CENTER, spacing: { before: 1000, after: 130 },
  children: [new TextRun({ text: "食源性益生菌减脂潜力的预测方法与菌株排序", font: HEI, size: 38, bold: true })] }));
C.push(new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 200 },
  children: [new TextRun({ text: "一套不依赖肠道队列丰度的菌株性质评分体系", font: HEI, size: 24, bold: true })] }));
C.push(new Paragraph({ alignment: AlignmentType.CENTER, spacing: { before: 300, after: 60 },
  children: [new TextRun({ text: "ProSlim-Microbiome-AI 项目组", font: SERIF, size: 22 })] }));
C.push(new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 1000 },
  children: [new TextRun({ text: "2026 年 6 月 25 日", font: SERIF, size: 20 })] }));
C.push(new Paragraph({ children: [new PageBreak()] }));

// ===== 摘要 =====
C.push(new Paragraph({ spacing: { after: 100 }, children: [new TextRun({ text: "摘要", font: HEI, size: 26, bold: true })] }));
C.push(body("**背景与问题：**食源性益生菌是唯一可直接用于食品与膳食补充剂的菌株类别，但对其减脂潜力的排序长期依赖零散的临床报道或机制推测。基于人群队列差异丰度的评价体系无法适用于这一类别，原因有两点：其一，多数乳杆菌类为肠道过路菌而非常驻菌，在公开宏基因组队列中流行率低于检出阈值；其二，全部食源菌在区分瘦人相关菌群的关键功能轴（丁酸、丙酸、黏液相互作用）上取值完全相同，该类指标无法产生排序区分度。", { noIndent: true }));
C.push(body(`**方法：**本研究建立一套仅使用菌株固有性质的评分体系（v3）。六个维度及权重为：交叉喂养供能 0.22、胆盐水解酶（BSH）介导的胆汁酸调节 0.15、安全等级 0.22、临床证据 0.15、工业可行性 0.14，以及肥胖特征惩罚 −0.12。各维度的判据分别来自本项目前期在西欧健康人群队列中获得的验证结果（协作型生态、口腔来源菌的肥胖富集、糖降解通路的肥胖富集）与自下而上菌株目录（EFSA QPS 安全分层、人体试验先例、可培养性）。队列证据按设计不进入评分，仅作为独立旗标报告，并在同分内用于排序。`, { noIndent: true }));
C.push(body(`**结果：**对 ${SR.n_strains} 株食源益生菌完成排序，形成 ${SR.n_score_tiers} 个分数档。副干酪乳酪杆菌与植物乳植杆菌性质分最高（0.866），但二者在队列中完全无数据。真正兼具"性质优、临床先例、队列支持"三重条件的仅动物双歧杆菌与长双歧杆菌（性质分 0.749；西欧队列显著瘦人富集，倍数变化分别为 0.62 与 0.65），其评分劣势全部来自工业可行性与 BSH 强度而非证据强度。链状双歧杆菌拥有全部食源菌中最强的队列信号（中东倍数变化 0.48）但缺临床先例。四株常用商业双歧杆菌（短、青春、两歧、假链状）在北美队列显著肥胖富集（倍数变化 3.15–7.39），列为慎用；链球菌属 11 株因属内含病原种而不予推荐。`, { noIndent: true }));
C.push(body("**结论：**以减脂效果预测为目标时，应以动物双歧杆菌与长双歧杆菌为首选，而非性质分最高的乳杆菌类。本方法的主要局限在于属级注释造成大规模并列（最大并列 11 株），且两个权重较大的维度属机制与工程先验、未经减脂结局验证；真正的菌株级排序需补充实际酶活、产酸量与耐受性等表型数据。", { noIndent: true }));
C.push(new Paragraph({ spacing: { before: 110, after: 200 }, children: [
  new TextRun({ text: "关键词：", font: HEI, size: 20, bold: true }),
  new TextRun({ text: "食源性益生菌；减脂；菌株筛选；交叉喂养；胆盐水解酶；EFSA QPS；预测排序", font: SERIF, size: 20 })] }));
C.push(new Paragraph({ children: [new PageBreak()] }));

// ===== 1 引言 =====
C.push(h1("1　引言"));
C.push(body("益生菌辅助减脂是近年功能食品领域的重要方向，市售产品多以乳杆菌属与双歧杆菌属为主。然而，产品配方的菌株选择往往依据单一临床报道、供应链可得性或既有工艺经验，缺乏统一、可追溯的排序依据。"));
C.push(body("与此同时，基于公开肠道宏基因组队列的菌群分析已能较可靠地识别与瘦体型相关的常驻菌。一个自然的想法是把该分析结果直接用于食源菌筛选，但这条路径存在结构性障碍：**食源性益生菌在很大程度上并非肠道常驻菌**。这决定了必须为食源菌单独建立评价体系，而不是套用常驻菌的方法。本文报告该体系的设计、依据与全部 38 株食源菌的排序结果。"));

// ===== 2 方法 =====
C.push(h1("2　材料与方法"));
C.push(h2("2.1　菌株来源"));
C.push(body("菌株来自本项目构建的筛选目录中标注为食品级益生菌（food_grade_probiotic）的全部条目，共 38 株，覆盖乳杆菌属及其重分类属（Lactobacillus、Lacticaseibacillus、Lactiplantibacillus、Limosilactobacillus）、双歧杆菌属、乳球菌属、片球菌属、芽孢杆菌属、酵母属与链球菌属。每株附带 EFSA QPS 安全分层、人体试验先例标注与属级代谢功能注释。"));

C.push(h2("2.2　为何不能沿用队列差异丰度方法"));
C.push(body("本项目针对肠道常驻菌的评价体系以人群队列的胖瘦差异丰度为核心依据。将其应用于食源菌时遇到两条硬约束（表 1）。"));
C.push(table(["约束", "具体事实", "后果"],
  [["多数食源菌不在肠道队列中",
    "38 株中 15 株在西欧队列的流行率低于 10% 检出阈值，未进入统计；乳杆菌类为过路菌而非常驻菌",
    "无差异丰度数据可用，非数据缺陷而是生物学事实"],
   ["食源菌在关键判别轴上完全同质",
    "全部 38 株的丁酸潜能、丙酸潜能与黏液相互作用均为 0，皆为乳酸-乙酸产生菌",
    "前期最有效的指标（丙酸潜能、群落多样性关联）无法产生排序区分度"]],
  [1900, 4600, 2570]));
C.push(cap("表 1　队列方法不适用于食源菌的两条硬约束"));

C.push(h2("2.3　v3 评分体系"));
C.push(body("评分公式为六个维度的加权和，各维度取值归一化至 0–1 区间："));
C.push(new Paragraph({ alignment: AlignmentType.CENTER, spacing: { before: 60, after: 60 },
  children: [new TextRun({ text: "v3 = 0.22×交叉喂养 + 0.15×BSH + 0.22×安全 + 0.15×临床 + 0.14×工业 − 0.12×肥胖特征",
    font: SERIF, size: 20, italics: true })] }));
C.push(body("各维度的判据来源与证据强度列于表 2。设计上刻意区分两类信息：**具有队列验证支撑的判据**（肥胖特征惩罚）与**属于机制或工程先验的判据**（交叉喂养、工业可行性），后者在结论中被明确标注为未经减脂结局验证。"));
C.push(table(["维度", "权重", "判据来源", "证据强度"],
  [["交叉喂养供能", "0.22",
    "前期发现瘦人菌群呈协作型生态（与群落多样性关联的判别 AUC 0.920，跨属泛化 0.878）。食源菌产乳酸与乙酸，可作为常驻丁酸/丙酸产生菌的底物，间接支持该生态",
    "机制假设，未验证"],
   ["BSH 胆汁酸调节", "0.15",
    "BSH 已被本项目证明不能预测常驻菌的瘦人富集（AUC 0.517，P=0.85；跨属 0.027），但对外源补充乳杆菌的降胆固醇作用有既有文献支持，此为其唯一合理适用范式",
    "文献支持；本项目血脂数据不足以自证"],
   ["安全等级", "0.22", "EFSA QPS/GRAS 低门槛记 1.0；需菌株级安全审查记 0.25", "监管框架，明确"],
   ["临床证据", "0.15", "目录标注的人体试验先例记 1.0；仅筛选级记 0.35", "目录标注，明确"],
   ["工业可行性", "0.14",
    "发酵与稳定性先验：芽孢杆菌 1.00、酵母 0.95、乳杆菌类 0.85–0.90、链球菌 0.75、双歧杆菌 0.60（需厌氧、难稳定）",
    "工程先验，非减脂证据"],
   ["肥胖特征惩罚", "−0.12",
    "口腔来源属权重 0.6（前期在西欧验证口腔链球菌属肥胖富集）；糖降解主导型权重 0.4（前期通路分析显示半乳糖、水苏糖、肌醇降解在肥胖者增强）",
    "有队列验证支撑"]],
  [1500, 700, 5100, 1770]));
C.push(cap("表 2　六个维度的权重、判据来源与证据强度"));

C.push(h2("2.4　队列证据的处理与两级排序"));
C.push(body("按设计要求，队列差异丰度**不进入评分**。但完全忽略「某菌在人群队列中显著肥胖富集」这一事实并不稳妥，故将其作为**独立旗标**报告，取值为：队列支持（瘦人富集）、队列受检但不显著、队列无数据（不可得）、队列反证（肥胖富集）。"));
C.push(body(`排序采用两级规则：**第一级**以 v3 性质分决定所属分数档；**第二级**仅在同分内以队列证据层级排序（支持 > 不显著／无数据 > 反证），不跨档移动菌株。第二级为必要设计——属级注释使整组菌完全同分（9 株乳杆菌均为 0.7615，11 株链球菌均为 0.3125），若无第二级，排序将退化为大规模并列。该规则以独立列透明呈现，性质分本身仍可单独审阅。`));

C.push(h2("2.5　组合评分"));
C.push(body("在单菌评分基础上，对 2–4 株的全部组合穷举打分：综合分 = 0.72×成员平均 v3 分 + 0.18×性质互补度 + 0.10×属多样性。互补度奖励同时包含强 BSH 成员与强交叉喂养成员、且跨越两个以上属的组合。需菌株级安全审查者与存在队列反证者不进入组合池。"));

// ===== 3 结果 =====
C.push(h1("3　结果"));
C.push(h2("3.1　单菌排序总览"));
C.push(body(`38 株形成 ${SR.n_score_tiers} 个分数档，最大并列组 ${SR.largest_tie_group} 株（图 1A、1B）。推荐意见分布为：首选 2 株、推荐 2 株、值得关注 1 株、备选 11 株、低优先 7 株、慎用 4 株、不推荐 11 株。`));
C.push(...figure("fig27_foodgrade_ranking.png", "图 1　38 株食源益生菌减脂潜力单菌排序：(A) 全部菌株按 v3 性质分排序，颜色表示推荐意见，标注表示队列证据方向；(B) 分档结构与关键结论", 0.809));

C.push(h2("3.2　排序前 21 位明细"));
const fills = RANK.slice(0, 21).map(r => {
  const k = r["推荐意见"] || "";
  if (k.startsWith("首选")) return "E3F1E8";
  if (k.startsWith("推荐")) return "E6EEF7";
  if (k.startsWith("值得关注")) return "F0EAF6";
  if (k.startsWith("慎用")) return "FBEEE2";
  return "FFFFFF";
});
C.push(table(["排名", "中文名", "v3分", "交叉喂养", "BSH", "安全", "临床", "工业", "队列证据", "推荐意见"],
  RANK.slice(0, 21).map(r => [r["排名"], r["中文名"], (+r["v3性质分"]).toFixed(3),
    (+r["交叉喂养"]).toFixed(1), (+r["BSH胆汁酸"]).toFixed(1), (+r["安全等级"]).toFixed(2),
    (+r["临床证据"]).toFixed(2), (+r["工业可行"]).toFixed(2),
    (r["队列证据"] || "").replace("队列", "").replace("：瘦人富集", "(瘦)").replace("：肥胖富集", "(胖)"),
    (r["推荐意见"] || "").split("：")[0]]),
  [560, 1700, 700, 800, 560, 560, 560, 560, 1200, 1870], fills));
C.push(cap("表 3　单菌排序前 21 位（余下 17 位见配套数据表）"));

C.push(h2("3.3　关键结果"));
C.push(body("**（1）排名第一并非最优选择。** 副干酪乳酪杆菌与植物乳植杆菌性质分并列最高（0.866），在强 BSH、强交叉喂养、QPS 安全与临床先例四项上全部占优。但二者在队列中完全无数据——乳杆菌不是肠道常驻菌，其减脂潜力只能依靠机制推断。"));
C.push(body("**（2）真正的首选是动物双歧杆菌与长双歧杆菌。** 二者是 38 株中唯一同时具备性质优、临床先例与队列证据支持三重条件者：动物双歧杆菌在西欧队列显著瘦人富集（倍数变化 0.62，即肥胖者丰度为瘦人的 62%，FDR=0.004），长双歧杆菌同样显著（倍数变化 0.65，FDR=0.042）。其性质分（0.749）低于第一档，差距全部来自工业可行性（双歧杆菌 0.60 对乳杆菌 0.90，因需厌氧且难稳定）与 BSH 强度（0.5 对 1.0）。**即评分劣势属工程与机制层面，而证据优势是真实的人群数据；以预测减脂效果为目标时应以此二株为首选。**"));
C.push(body("**（3）链状双歧杆菌值得单独关注。** 它拥有全部食源菌中最强的队列支持信号——中东队列显著瘦人富集，倍数变化 0.48，即肥胖者丰度不足瘦人一半，强于动物双歧杆菌的 0.62。但因缺乏临床先例，性质分仅 0.652。建议将其列为需补做临床验证的高潜力候选，而非直接排除。"));
C.push(body("**（4）四株常用商业双歧杆菌存在队列反证。** 短双歧杆菌、青春双歧杆菌、两歧双歧杆菌与假链状双歧杆菌在北美队列显著肥胖富集（倍数变化 3.15–7.39）。虽然主评分不含队列项，该旗标提示其在北美人群中的减脂定位存疑，建议该市场慎用或先行人群验证。需强调的是，同属菌在西欧与中东方向相反，说明该结论具有地区特异性。"));
C.push(body("**（5）芽孢杆菌与酵母排名靠后源于机制而非安全。** 凝结芽孢杆菌与枯草芽孢杆菌的工业可行性最高（1.00），但交叉喂养与 BSH 均为 0——它们不产乳酸/乙酸，缺少本方法认定的核心机制；布拉氏酵母同理（真核生物，机制路径不同）。这不否定其在腹泻等其他适应症中的价值，仅说明按减脂机制排序时不占优。"));
C.push(body("**（6）链球菌属 11 株不予推荐的原因是安全等级。** 其安全分为 0.25（属内含病原种，需菌株级审查），而非减脂性质不佳——其交叉喂养能力实为 1.0。若某特定商业株已通过菌株级安全评估，可单独重新评价。"));

C.push(h2("3.4　组合评分结果"));
C.push(body(`在排除需安全审查者与队列反证者后，可建组合池为 ${S3.buildable_pool} 株，共产生 ${S3.n_combinations.toLocaleString()} 个候选组合。`));
C.push(table(["方案", "组成", "综合分", "特点"],
  [["A（全局最优）", "副干酪乳酪杆菌 + 植物乳植杆菌", "0.9035", "性质最优，但两株均无队列证据"],
   ["B（推荐）", "副干酪乳酪杆菌 + 植物乳植杆菌 + 动物双歧杆菌", "0.8754", "在 A 基础上加入唯一具队列支持且有临床先例的成员"]],
  [1500, 4200, 900, 2470]));
C.push(cap("表 4　组合评分的两个代表方案"));
C.push(body("方案 A 的评分优势来自工业可行性（属工程属性）；方案 B 以 0.028 的评分代价换取一项真实的人群证据，三株均有临床先例。以预测减脂为目标时推荐方案 B。"));
C.push(...figure("fig26_foodgrade_v3.png", "图 2　v3 方法总览：(A) 评分构成；(B) 38 株的队列证据状况；(C) 推荐组合；(D) 被排除的 15 株及原因", 0.719));

// ===== 4 讨论 =====
C.push(h1("4　讨论"));
C.push(body("本研究的核心判断是：**食源性益生菌需要与肠道常驻菌不同的评价逻辑**。常驻菌可以直接用人群队列的胖瘦差异丰度来定标，而食源菌多为过路菌，队列中往往不可见；若强行套用队列方法，结果不是「证据不足」而是「根本无法排序」。本文的解决方式是把从队列分析中**学到的判据**（协作型生态、口腔来源与糖降解的肥胖倾向）迁移为可对食源菌计算的性质维度，同时保留自下而上目录中的安全与临床信息。"));
C.push(body("一个值得强调的结果是**性质分最高者并非推荐首选**。这一反差揭示了评分体系的一个内在张力：工业可行性等工程维度会系统性地抬高乳杆菌类的排名，而它们恰恰是队列证据最匮乏的类别；双歧杆菌工艺更难，却是唯一拥有人群证据的类别。本文的处理方式是保持评分透明、把队列证据独立成列，并在推荐意见中优先采纳有证据支撑者——而非通过调整权重把结论「做」出来。"));
C.push(body("另一个具有直接产业含义的发现是**四株常用商业双歧杆菌在北美队列显著肥胖富集**。结合前期跨地区分析中同属菌在西欧、中东方向相反的观察，合理解释是这类菌的胖瘦关联具有强地区依赖性，可能与人群年龄结构、饮食模式与基线菌群构成有关。因此，全球统一配方在部分市场可能失效甚至方向相反，地区化配方策略更为稳妥。"));
C.push(body("最后需要正视方法本身的证据层级。相比针对常驻菌的方法（其最大权重维度具备队列验证支撑），本方法权重最大的两个维度——交叉喂养 0.22 与工业可行性 0.14——分别是机制假设与工程先验，均未针对减脂结局验证。因此本排序应被理解为**候选定标与优先级工具**，而非疗效预测。"));

// ===== 5 结论 =====
C.push(h1("5　结论"));
[`对 38 株食源性益生菌建立了不依赖肠道队列丰度的六维评分体系，形成 ${SR.n_score_tiers} 个分数档的完整排序。`,
 "以减脂效果预测为目标时，首选为动物双歧杆菌与长双歧杆菌——二者是唯一同时具备性质优、临床先例与队列支持三重条件者；其评分劣势仅源于工业可行性与 BSH 强度，而非证据强度。",
 "副干酪乳酪杆菌与植物乳植杆菌性质分最高，可作为工艺优先方案，但需补充人群菌群关联或小样本试验以填补队列证据空缺。",
 "链状双歧杆菌拥有全部食源菌中最强的队列信号（中东倍数变化 0.48），应列为需补临床验证的高潜力候选。",
 "短、青春、两歧、假链状双歧杆菌在北美队列显著肥胖富集（倍数变化 3.15–7.39），该市场应慎用；此类关联具有地区特异性，支持地区化配方策略。",
 "链球菌属 11 株因属内含病原种而不予推荐，原因在安全而非减脂性质。",
].forEach(t => C.push(new Paragraph({ numbering: { reference: "concl", level: 0 },
  spacing: { line: 330, after: 60 }, children: [new TextRun({ text: t, font: SERIF, size: 21 })] })));

// ===== 6 局限 =====
C.push(h1("6　局限性"));
[`最主要局限是属级注释造成大规模并列：9 株乳杆菌性质分完全相同（0.7615），11 株链球菌完全相同（0.3125），方法无法在属内区分菌株。真正的菌株级排序须补充实际 BSH 酶活、产酸量与速率、耐胆盐与耐酸性、黏附能力等表型数据以及菌株级基因组注释。`,
 "权重最大的两个维度证据最弱：交叉喂养（0.22）为机制假设，工业可行性（0.14）为工程先验，均未针对减脂结局验证；本方法的整体证据强度弱于针对常驻菌的方法。",
 "BSH 权重（0.15）来自既有文献而非本项目数据——本项目可关联干预菌种的血脂结局仅 6 行，不足以检验 BSH 与降胆固醇的关系。",
 "交叉喂养假设需体外验证：应通过共培养实验证明该食源菌确能提升常驻丁酸/丙酸产生菌的产酸量。",
 "队列证据存在地区异质性：同一菌属在不同地区方向可相反，故队列支持标签不可全球通用。",
 "本排序为候选定标而非疗效预测，不能据此断言某菌可减脂或减重幅度；落地须经体外功能验证、动物模型与人体随机对照试验。",
].forEach(t => C.push(new Paragraph({ numbering: { reference: "lim", level: 0 },
  spacing: { line: 330, after: 60 }, children: [new TextRun({ text: t, font: SERIF, size: 21 })] })));

// ===== 7 行动建议 =====
C.push(h1("7　行动建议"));
C.push(table(["优先级", "菌株", "下一步"],
  [["1", "动物双歧杆菌、长双歧杆菌", "直接进入体外与动物减脂验证（性质、临床、队列三重支持齐备）"],
   ["2", "副干酪乳酪杆菌、植物乳植杆菌", "补做人群菌群关联或小样本随机对照试验，填补队列证据空缺"],
   ["3", "链状双歧杆菌", "补临床先例；其队列信号为食源菌中最强"],
   ["4", "9 株乳杆菌（同分组 3）", "先做菌株级表型测定破除并列，再行排序"],
   ["—", "4 株北美反证双歧杆菌", "该市场慎用；如需使用先做人群验证"],
   ["—", "链球菌属 11 株", "除已通过菌株级安全评估者外，不进入减脂配方"]],
  [900, 2900, 5270]));
C.push(cap("表 5　按优先级的后续行动建议"));

// ===== 8 数据可用性 =====
C.push(h1("8　数据与代码可用性"));
C.push(body("评分与排序脚本：scripts/combination_recommendation/foodgrade_prediction_v3.py（六维评分与组合打分）、foodgrade_single_strain_ranking.py（两级排序与推荐意见）；作图脚本：scripts/visualization/foodgrade_ranking_figure.py。结果数据：results/combination_recommendations/ 下 foodgrade_v3_strain_scores、foodgrade_single_strain_ranking、foodgrade_v3_combinations 三个系列文件。配套数据表：食源性益生菌预测_完整数据_20260625.xlsx。", { noIndent: true }));

const doc = new Document({
  styles: { default: { document: { run: { font: SERIF, size: 21 } } },
    paragraphStyles: [
      { id: "Heading1", name: "Heading 1", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { size: 28, bold: true, font: HEI }, paragraph: { spacing: { before: 300, after: 140 }, outlineLevel: 0 } },
      { id: "Heading2", name: "Heading 2", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { size: 23, bold: true, font: HEI }, paragraph: { spacing: { before: 190, after: 100 }, outlineLevel: 1 } }] },
  numbering: { config: [
    { reference: "concl", levels: [{ level: 0, format: LevelFormat.DECIMAL, text: "%1.", alignment: AlignmentType.LEFT,
      style: { paragraph: { indent: { left: 560, hanging: 340 } } } }] },
    { reference: "lim", levels: [{ level: 0, format: LevelFormat.DECIMAL, text: "%1.", alignment: AlignmentType.LEFT,
      style: { paragraph: { indent: { left: 560, hanging: 340 } } } }] }] },
  sections: [{ properties: { page: { size: { width: A4W, height: A4H },
      margin: { top: MARGIN, right: MARGIN, bottom: MARGIN, left: MARGIN } } },
    footers: { default: new Footer({ children: [new Paragraph({ alignment: AlignmentType.CENTER,
      children: [new TextRun({ text: "— ", font: SERIF, size: 18 }),
                 new TextRun({ children: [PageNumber.CURRENT], font: SERIF, size: 18 }),
                 new TextRun({ text: " —", font: SERIF, size: 18 })] })] }) },
    children: C }] });
Packer.toBuffer(doc).then(b => { fs.writeFileSync(OUT, b); console.log("wrote", OUT, b.length); });
