const fs = require("fs");
const path = require("path");
const { Document, Packer, Paragraph, TextRun, Table, TableRow, TableCell,
        AlignmentType, LevelFormat, HeadingLevel, BorderStyle, WidthType,
        ShadingType, ImageRun, PageBreak, PageNumber, Header, Footer } = require("docx");

const ROOT = "D:/strain screen mix";
const FIG = path.join(ROOT, "results/paper_figures");
const OUT = path.join(ROOT, "docs/ProSlim_减脂菌株组合预测_论文_20260625.docx");

const SERIF = "SimSun";      // 宋体 正文
const HEI = "SimHei";        // 黑体 标题
const A4W = 11906, A4H = 16838, MARGIN = 1440;
const CONTENT = A4W - 2 * MARGIN; // 9026 DXA

// ---- helpers ----
const body = (text, opts = {}) => new Paragraph({
  spacing: { line: 360, after: 120 },
  alignment: AlignmentType.JUSTIFIED,
  indent: opts.noIndent ? undefined : { firstLine: 480 },
  children: parseRuns(text, { font: SERIF, size: 21 }),
});
// supports **bold** inline
function parseRuns(text, base) {
  const parts = text.split(/(\*\*[^*]+\*\*)/g).filter(Boolean);
  return parts.map(p => p.startsWith("**")
    ? new TextRun({ text: p.slice(2, -2), bold: true, font: base.font, size: base.size })
    : new TextRun({ text: p, font: base.font, size: base.size }));
}
const h1 = (text) => new Paragraph({ heading: HeadingLevel.HEADING_1,
  spacing: { before: 320, after: 160 },
  children: [new TextRun({ text, font: HEI, size: 30, bold: true })] });
const h2 = (text) => new Paragraph({ heading: HeadingLevel.HEADING_2,
  spacing: { before: 220, after: 120 },
  children: [new TextRun({ text, font: HEI, size: 25, bold: true })] });

function figRatio(name) {
  // figsize ratios (height/width) from the generator
  const r = { fig1_pipeline: 0.511, fig2_obesity_model: 0.476, fig3_forest: 0.372,
              fig4_gate_funnel: 0.579, fig5_balanced_sensitivity: 0.476,
              fig6_combinations: 0.535, fig7_mechanism: 0.667, fig8_ipd_funnel: 0.426,
              fig9_strain_membership: 0.509 };
  return r[name];
}
function figure(name, caption) {
  const w = 560; // px ~ fits A4 content
  const h = Math.round(w * figRatio(name));
  return [
    new Paragraph({ alignment: AlignmentType.CENTER, spacing: { before: 160, after: 60 },
      children: [new ImageRun({ type: "png", data: fs.readFileSync(path.join(FIG, name + ".png")),
        transformation: { width: w, height: h },
        altText: { title: caption, description: caption, name: name } })] }),
    new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 200 },
      children: [new TextRun({ text: caption, font: HEI, size: 19, bold: true })] }),
  ];
}
// table builder
const cellBorder = { style: BorderStyle.SINGLE, size: 1, color: "BBBBBB" };
const borders = { top: cellBorder, bottom: cellBorder, left: cellBorder, right: cellBorder };
function tcell(text, w, { head = false, alignCenter = false } = {}) {
  return new TableCell({ borders, width: { size: w, type: WidthType.DXA },
    shading: { fill: head ? "D9E2F0" : "FFFFFF", type: ShadingType.CLEAR },
    margins: { top: 60, bottom: 60, left: 100, right: 100 },
    children: [new Paragraph({ alignment: alignCenter ? AlignmentType.CENTER : AlignmentType.LEFT,
      children: [new TextRun({ text, font: SERIF, size: 18, bold: head })] })] });
}
function table(headers, rows, widths) {
  const mk = (cells, head) => new TableRow({ tableHeader: head,
    children: cells.map((c, i) => tcell(c, widths[i], { head, alignCenter: i > 0 })) });
  return new Table({ width: { size: CONTENT, type: WidthType.DXA }, columnWidths: widths,
    rows: [mk(headers, true), ...rows.map(r => mk(r, false))] });
}
const caption = (t) => new Paragraph({ alignment: AlignmentType.CENTER,
  spacing: { before: 80, after: 200 }, children: [new TextRun({ text: t, font: HEI, size: 18, bold: true })] });

// ================= CONTENT =================
const children = [];

// Title block
children.push(new Paragraph({ alignment: AlignmentType.CENTER, spacing: { before: 600, after: 120 },
  children: [new TextRun({ text: "基于公开数据库的益生菌减脂组合智能预测系统", font: HEI, size: 40, bold: true })] }));
children.push(new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 80 },
  children: [new TextRun({ text: "分阶段建模、诚实验证门控与个体级数据瓶颈分析", font: HEI, size: 26, bold: true })] }));
children.push(new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 60 },
  children: [new TextRun({ text: "ProSlim-Microbiome-AI 项目组", font: SERIF, size: 22 })] }));
children.push(new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 360 },
  children: [new TextRun({ text: "2026 年 6 月 25 日", font: SERIF, size: 20 })] }));

// Abstract
children.push(new Paragraph({ spacing: { before: 120, after: 100 },
  children: [new TextRun({ text: "摘要", font: HEI, size: 24, bold: true })] }));
children.push(body("**背景：**肥胖与肠道菌群密切相关，但益生菌减脂的临床证据高度异质，现有预测工具常对疗效过度承诺。本项目旨在建立一个分阶段、可扩展、可诚实验证的人工智能建模系统，整合公开肠道微生物组、益生菌干预 RCT、候选菌株基因组与安全性注释。", { noIndent: true }));
children.push(body("**方法：**系统包含肥胖状态模型（8 304 样本 / 45 研究 / 206 物种，按研究分组留一验证）、臂级连续效应量综合（Paule–Mandel τ² + HKSJ 区间，仅采用直接方差）、223 株候选菌的安全/功能分流与鲁棒组合优化，以及统一的验证门控（留一研究、越过均值基线、外部验证就绪）。进一步用 EuropePMC + ENA + 数据链 API 系统搜寻可建个体应答模型的公开测序队列。", { noIndent: true }));
children.push(body("**结果：**肥胖分类分组留一 AUC 为 0.729（随机拆分 0.825，存在乐观差距）。严格直接方差下，仅 BMI（−0.44 kg/m²，95%CI [−0.53, −0.34]，I²=0%）达到可复制就绪；体重合并 −1.39 kg 但预测区间含 0、未就绪。4 个可建模 stratum 中仅 1 个越过均值基线，组合疗效排序门据此关闭。补全臂级样本量后，BMI 与体重在敏感性层达到 10 研究目标。Top-10 组合以临床前验证优先级交付，但机制覆盖集中于 BSH+乳酸轴，普遍缺失丁酸/丙酸/黏液机制。三轮（100→400→666 篇）结局过滤搜寻证明：公开库中不存在同时具备每受试者测序与减脂结局的益生菌 RCT 队列。", { noIndent: true }));
children.push(body("**结论：**本系统的核心价值在于诚实——它以正确的小样本方法证明聚合 RCT 在当前数据下无可复制疗效信号，并将瓶颈精确定位为个体级数据（IPD）的缺失而非模型不足。组合推荐以临床前验证优先级交付，疗效门保持关闭；个体应答建模管线已就绪，只待对口 IPD 队列到位。", { noIndent: true }));
children.push(new Paragraph({ spacing: { before: 120, after: 240 },
  children: [new TextRun({ text: "关键词：", font: HEI, size: 20, bold: true }),
            new TextRun({ text: "肠道菌群；益生菌；减脂；机器学习；随机效应 meta 分析；留一研究验证；个体级数据", font: SERIF, size: 20 })] }));
children.push(new Paragraph({ children: [new PageBreak()] }));

// 1 引言
children.push(h1("1  引言"));
children.push(body("肥胖已成为全球性公共卫生问题，越来越多证据提示肠道菌群在能量吸收、胆汁酸代谢、短链脂肪酸（SCFA）信号与肠屏障功能中发挥作用，从而影响体重与体脂。益生菌、合生元与膳食纤维干预因此被寄望于辅助减脂。然而，已发表的随机对照试验（RCT）在菌株、剂量、周期、人群与结局指标上高度异质，合并效应往往不稳定。"));
children.push(body("在此背景下，许多商业化或学术性的“菌株组合推荐”工具倾向于直接断言某组合可减脂，却缺乏对泛化性与因果性的严格检验。本项目采取相反的立场：**不直接断言疗效，而是建立一个分阶段、可扩展、可诚实验证的建模系统**。其设计原则是——当数据不足以支撑疗效结论时，系统应明确关闭疗效门，而非用调参制造虚假信号。本文报告该系统的架构、各模块的诚实验证结果，以及通往真正个体化预测的关键瓶颈分析。"));

// 2 方法
children.push(h1("2  数据与方法"));
children.push(h2("2.1  数据来源"));
children.push(body("系统整合四类公开数据：(1) 肠道微生物组丰度与表型（用于肥胖状态建模）；(2) 益生菌/合生元/膳食干预 RCT 的证据与臂级结局（来自 PubMed、ClinicalTrials.gov、EuropePMC，锚定 PMID/DOI/登记号）；(3) 候选菌株基因组 accession（NCBI）；(4) 安全性注释（EFSA QPS 资格、临床微生物学先验）。所有菌株指标、功能与临床结局均要求可追溯到真实数据库、登记库或同行评议论文正文/补充材料。"));
children.push(h2("2.2  肥胖状态模型"));
children.push(body("以 8 304 个样本、45 项研究、206 个物种相对丰度为特征，训练肥胖分类（lean vs obesity）与 BMI 回归。验证以**按研究分组的留一/十折交叉验证**为主，并报告随机拆分以暴露批次/地域混杂带来的乐观偏差。"));
children.push(h2("2.3  连续效应量综合"));
children.push(body("将 RCT 抽取为臂级连续效应量。方差政策仅采用**直接方差**（报告的置信区间，或臂级 SD 与样本量），p 值反算降级为敏感性分析。合并采用 **Paule–Mandel τ² 估计 + 修正 HKSJ 区间**（小样本正确方法），并报告 I²、预测区间、共干预排除与缺失方差三角稳健性。"));
children.push(h2("2.4  菌株筛选与组合优化"));
children.push(body("候选菌库由 10 株扩展至 223 株，按 EFSA QPS 与临床先验分为低风险、LBP 前例、需筛新型共生与应排除病原属。组合优化器在证据后验、机制模块覆盖、配方完整性、属多样性与复杂度惩罚下，对 3–5 株组合做带不确定性的鲁棒排序，并输出主动学习批次与帕累托前沿。"));
children.push(h2("2.5  验证门控"));
children.push(body("核心原则为：随机拆分表现良好但留一研究验证差的模型，不得用于组合推荐。连续效应模型须在留一研究下越过均值基线（相对 MAE 改善 ≥10%）方可启用组合疗效排序；外部验证须具备时间或来源留出，乃至前瞻外部队列。任一门未过，`combination_ranking_enabled` 保持为假。"));
children.push(h2("2.6  个体级数据（IPD）搜寻"));
children.push(body("为突破聚合数据的固有局限，用 EuropePMC 检索 + 逐篇 datalinks API 系统搜寻沉积了每受试者测序的干预 RCT，并对候选用 ENA Portal API 核验样本是否按受试者配对、是否含基线与随访时间点。第三轮在搜索中加入摘要级结局门控（要求减脂结局与干预设计，排除横断面与婴儿/动物）。"));

// 3 结果
children.push(h1("3  结果"));
children.push(h2("3.1  系统总体架构"));
children.push(body("系统由数据层、模型层与决策层构成（图 1）。数据层汇聚公开菌群、RCT 证据、菌株基因组与安全注释；模型层产出肥胖状态模型、严格效应量综合与菌株安全/功能矩阵；决策层输出组合排序优先级、诚实验证门控与个体应答 pilot 脚手架。"));
children.push(...figure("fig1_pipeline", "图 1  ProSlim 微生物组减脂预测系统总体架构"));

children.push(h2("3.2  肥胖状态模型：有内部信号但存在乐观差距"));
children.push(body("肥胖分类按研究分组留一 AUC 为 0.729，明显高于随机基线 0.5，表明菌群组成对肥胖状态有可泛化信号；但随机拆分 AUC 达 0.825，二者差距揭示了批次/地域/测序方法的混杂导致的乐观偏差（图 2A）。BMI 回归分组 R² 为 0.103，优于均值基线但绝对解释力有限（图 2B）。该模型是本系统唯一具内部信号的预测资产，适用于人群分层与候选优先级，而非个体疗效预测。"));
children.push(...figure("fig2_obesity_model", "图 2  肥胖状态模型的分组留一验证与随机拆分对比"));

children.push(h2("3.3  严格 meta 综合：BMI 可复制就绪，体重未就绪"));
children.push(body("在仅直接方差 + HKSJ 的严格政策下（图 3），BMI（k=5）合并效应 −0.44 kg/m²（95%CI [−0.53, −0.34]，I²=0%，预测区间 [−0.55, −0.33]）排除 0 且异质性极低，被判定为可复制就绪的统计信号；体重（k=7）合并 −1.39 kg（95%CI [−2.11, −0.68]）虽排除 0，但 I²=54.8% 且预测区间 [−2.97, +0.18] 跨 0，故标记为未就绪。这一结果以正确的小样本方法，诚实地刻画了证据的强弱边界。"));
children.push(...figure("fig3_forest", "图 3  BMI 与体重的小样本随机效应 meta 综合（HKSJ）"));

children.push(h2("3.4  诚实疗效门控：仅 1/4 stratum 越过基线"));
children.push(body("从 137 条效应行经高置信、直接方差、独立研究层层筛选，仅得 19 项独立研究；在留一研究验证下，4 个可建模 stratum 中仅 1 个越过均值基线（图 4）。据此，组合疗效排序门控保持关闭（`combination_ranking_enabled = false`）。这并非缺陷，而是数据约束下的正确科学表述。"));
children.push(...figure("fig4_gate_funnel", "图 4  从证据到疗效门的诚实漏斗"));

children.push(h2("3.5  补全臂级样本量提升敏感性覆盖"));
children.push(body("个体结局核验中，对两项报告了臂级 SD 但缺每臂样本量的研究，经摘要确认总样本量后纳入平衡 n 敏感性层（仅作敏感性，不计入生产直接方差）。补全后，BMI 与体重在敏感性层达到 10 研究目标（图 5），但生产层门控仍按直接方差从严执行。"));
children.push(...figure("fig5_balanced_sensitivity", "图 5  补全臂级样本量后各结局的直接方差与敏感性研究数"));

children.push(h2("3.6  组合优先级与不确定性"));
children.push(body("在疗效门关闭的前提下，系统以**临床前验证优先级**（而非疗效/响应概率）交付 Top-10 益生菌组合（图 6、表 1）。排名首位为乳杆菌 K7/K8/K11 三株配伍双歧杆菌的骨架，后验综合分 7.35（p10–p90 区间 6.62–8.05）。所有组合的安全门为 pending，须先完成菌株级基因组 AMR/毒力/可移动元件筛查。"));
children.push(...figure("fig6_combinations", "图 6  Top-10 益生菌组合的临床前验证优先级及不确定区间"));
const combos = [
  ["1", "L. fermentum K7/K8/K11 + B. lactis IDCC4301 + B. animalis lactis B420", "5", "7.35", "0.62"],
  ["2", "L. fermentum K7/K8/K11 + B. breve BBr60", "4", "7.30", "0.55"],
  ["3", "L. fermentum K7/K8/K11 + B. animalis lactis B420 + B. breve BBr60", "5", "7.27", "0.54"],
  ["4", "L. fermentum K7/K8/K11 + B. lactis IDCC4301", "4", "7.27", "0.53"],
  ["5", "L. fermentum K7/K8/K11 + B. breve BBr60 + Bacillus coagulans BC99", "5", "7.23", "0.51"],
];
children.push(table(["#", "组合（菌株）", "株数", "后验综合分", "Top10 概率"], combos, [560, 6066, 700, 850, 850]));
children.push(caption("表 1  Top-5 益生菌组合（临床前验证优先级，非疗效预测）"));
children.push(body("为直观呈现全部预测组合的菌株构成，图 9 以菌株×组合成员矩阵列出 Top-10 组合：乳杆菌 K7/K8/K11 三联出现在 9/10 个组合中，构成核心骨架，双歧杆菌（IDCC4301、BBr60、B420 等）与少量芽孢杆菌作机制与生态位互补。"));
children.push(...figure("fig9_strain_membership", "图 9  预测的 Top-10 益生菌减脂组合及其菌株构成"));

children.push(h2("3.7  机制盲区"));
children.push(body("按属级功能 guild 解析（图 7），全部 Top 组合仅覆盖 5 条机制轴中的 BSH（胆盐水解→降脂）与乳酸/乙酸两条，普遍缺失丁酸、丙酸与黏液屏障三条——因为高证据菌株几乎都是乳杆菌与双歧杆菌。这是证据驱动排序的固有偏向，提示应主动纳入丁酸/黏液轴候选作为机制对照臂。"));
children.push(...figure("fig7_mechanism", "图 7  Top-10 组合的机制覆盖热图与盲区"));

children.push(h2("3.8  个体级数据搜寻：公开库无对口队列"));
children.push(body("三轮搜寻（100→400→666 篇，第三轮加结局过滤）的漏斗见图 8A。第二轮按样本量看似最强的益生菌测序队列，经逐篇全文核验后全部跑偏（婴儿菌群定植、睡眠质量、健康人群、横断面）。最终结论（图 8B、表 2）：公开库中**不存在**同时具备每受试者测序与减脂结局的益生菌 RCT；唯一群体对口且配对的沉积为低卡饮食队列（PRJNA1211859，16S），而含 shotgun 的对口队列（PRJEB81868 菊苣纤维）经全文核验其组间体重/体脂无显著变化。个体应答建模脚手架已就绪并通过合成自检，只待对口数据。"));
children.push(...figure("fig8_ipd_funnel", "图 8  个体级数据（IPD）三轮搜寻漏斗与文献级核验结论"));
const ipd = [
  ["PRJNA1211859", "低卡饮食（人）", "16S，19/20 配对", "较好（真实 ΔBMI）", "方法学 pilot"],
  ["PRJEB81868", "菊苣纤维（人）", "shotgun，293 样本", "近零（无显著变化）", "仅跑通管线"],
  ["PRJNA1188647", "B. infantis（婴儿）", "16S，314 样本", "非减脂（定植）", "结局跑偏"],
  ["—", "益生菌×减脂×个体测序", "—", "—", "公开库为零"],
];
children.push(table(["登记号/类别", "干预（人群）", "测序/配对", "减脂结局", "判定"], ipd, [1900, 2100, 2026, 1700, 1300]));
children.push(caption("表 2  代表性 IPD 候选的文献级核验结论"));

// 4 讨论
children.push(h1("4  讨论"));
children.push(body("本研究最重要的贡献不是某个高性能预测器，而是**一套在数据不足时拒绝过度承诺的诚实建模框架**。严格的小样本方法（PM τ² + HKSJ + 仅直接方差）推翻了较弱方法下的体脂信号，并将体重、BMI 之外的多数结局正确判为证据不足。这表明，聚合 RCT 在当前公开数据下，无法支撑稳健的个体疗效预测——瓶颈在数据粒度，而非算法。"));
children.push(body("肥胖状态模型的乐观差距（0.729 对 0.825）提示跨研究混杂的现实风险，强调留一研究验证不可或缺。机制盲区分析进一步揭示，纯证据驱动的组合排序会系统性偏向乳杆菌/双歧杆菌的 BSH–乳酸轴，而忽略丁酸与黏液屏障轴，这对机制互补的配方设计具有直接指导意义。"));
children.push(body("IPD 搜寻把“数据稀缺”精确为“减脂益生菌的个体测序队列在公开库中不存在”。这一文献级结论指明了唯一可行的解锁路径：向已完成减脂益生菌 RCT 且测序的团队争取个体数据共享，或在前瞻试验中预先约定 IPD 共享，并辅以可运行 16S/宏基因组流程的算力。"));

// 5 结论
children.push(h1("5  结论与展望"));
children.push(body("本系统能交付有据可依的益生菌组合临床前验证优先级，并以诚实门控避免疗效过度承诺。个体减脂应答的真正预测取决于个体级数据的获取——其建模管线已就绪、通过测试，只待对口 IPD 队列。下一步将聚焦：(1) 通过作者协作或前瞻试验获取个体结局；(2) 在生信环境处理已识别队列的测序数据；(3) 强化肥胖状态模型并争取真正的外部验证。"));

// 局限
children.push(h1("6  局限性与诚实声明"));
[
  "效应量综合受限于直接方差研究稀少（仅 13 研究 / 27 行），合并区间偏宽。",
  "肥胖状态模型仅含内部分组验证，尚无独立外部数据集；存在批次/地域乐观偏差。",
  "菌株安全/功能为属级知识先验，菌株级真实基因组 AMR/毒力筛查仍需生信流程。",
  "组合排序为临床前验证优先级，非疗效或个体响应概率；疗效门控保持关闭。",
  "个体应答模型尚无真实数据训练；所有相关结论均为搜寻与可行性核验，未伪造模型结果。",
].forEach(t => children.push(new Paragraph({ numbering: { reference: "limits", level: 0 },
  spacing: { line: 340, after: 60 }, children: [new TextRun({ text: t, font: SERIF, size: 21 })] })));

// 数据可用性
children.push(h1("7  数据与代码可用性"));
children.push(body("全部代码、配置、结果产出与本报告图表的生成脚本均纳入项目仓库（分支 codex/archive-supplement-pipeline）。关键登记号：肥胖状态模型特征与效应量综合见 results/ 下带日期戳的产出；IPD 候选与核验见 data/ipd_search/ 与 data/ipd_pilot/；图表生成见 scripts/visualization/paper_figures.py。引用的公开队列包括 PRJNA1211859、PRJEB81868 等（详见正文）。", { noIndent: true }));

// ---- build ----
const doc = new Document({
  styles: { default: { document: { run: { font: SERIF, size: 21 } } },
    paragraphStyles: [
      { id: "Heading1", name: "Heading 1", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { size: 30, bold: true, font: HEI }, paragraph: { spacing: { before: 320, after: 160 }, outlineLevel: 0 } },
      { id: "Heading2", name: "Heading 2", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { size: 25, bold: true, font: HEI }, paragraph: { spacing: { before: 220, after: 120 }, outlineLevel: 1 } },
    ] },
  numbering: { config: [
    { reference: "limits", levels: [{ level: 0, format: LevelFormat.DECIMAL, text: "%1.",
      alignment: AlignmentType.LEFT, style: { paragraph: { indent: { left: 600, hanging: 360 } } } }] },
  ] },
  sections: [{
    properties: { page: { size: { width: A4W, height: A4H }, margin: { top: MARGIN, right: MARGIN, bottom: MARGIN, left: MARGIN } } },
    footers: { default: new Footer({ children: [new Paragraph({ alignment: AlignmentType.CENTER,
      children: [new TextRun({ text: "第 ", font: SERIF, size: 18 }), new TextRun({ children: [PageNumber.CURRENT], font: SERIF, size: 18 }), new TextRun({ text: " 页", font: SERIF, size: 18 })] })] }) },
    children,
  }],
});
Packer.toBuffer(doc).then(buf => { fs.writeFileSync(OUT, buf); console.log("wrote", OUT, buf.length, "bytes"); });
