// Build the ProSlim-Microbiome-AI deliverable report as a .docx (Chinese, Microsoft YaHei).
const path = require("path");
const { execSync } = require("child_process");
const G = execSync("npm root -g").toString().trim();
const { Document, Packer, Paragraph, TextRun, Table, TableRow, TableCell, AlignmentType,
        HeadingLevel, BorderStyle, WidthType, ShadingType, LevelFormat, TableOfContents,
        Header, Footer, PageNumber, PageBreak } = require(path.join(G, "docx"));
const fs = require("fs");

const FONT = "Microsoft YaHei";
const CW = 9360; // content width (US Letter, 1" margins)
const border = { style: BorderStyle.SINGLE, size: 1, color: "BBBBBB" };
const borders = { top: border, bottom: border, left: border, right: border };

function P(text, opts = {}) {
  return new Paragraph({ spacing: { after: 120 }, ...opts,
    children: Array.isArray(text) ? text : [new TextRun({ text, ...(opts.run || {}) })] });
}
function H(text, level) { return new Paragraph({ heading: level, children: [new TextRun(text)] }); }
function bullet(text) { return new Paragraph({ numbering: { reference: "b", level: 0 }, spacing: { after: 60 }, children: [new TextRun(text)] }); }

function table(headers, rows, widths) {
  const w = widths || headers.map(() => Math.floor(CW / headers.length));
  const hrow = new TableRow({ tableHeader: true, children: headers.map((h, i) =>
    new TableCell({ borders, width: { size: w[i], type: WidthType.DXA },
      shading: { fill: "2E5A88", type: ShadingType.CLEAR },
      margins: { top: 60, bottom: 60, left: 100, right: 100 },
      children: [P("", { children: [new TextRun({ text: h, bold: true, color: "FFFFFF", size: 18 })] })] })) });
  const drows = rows.map(r => new TableRow({ children: r.map((c, i) =>
    new TableCell({ borders, width: { size: w[i], type: WidthType.DXA },
      margins: { top: 50, bottom: 50, left: 100, right: 100 },
      children: [P("", { children: [new TextRun({ text: String(c), size: 18 })], spacing: { after: 0 } })] })) }));
  return new Table({ width: { size: CW, type: WidthType.DXA }, columnWidths: w, rows: [hrow, ...drows] });
}

const heading = (id, name, size, lvl) => ({ id, name, basedOn: "Normal", next: "Normal", quickFormat: true,
  run: { size, bold: true, font: FONT, color: "1F3864" },
  paragraph: { spacing: { before: 220, after: 120 }, outlineLevel: lvl } });

const doc = new Document({
  styles: {
    default: { document: { run: { font: FONT, size: 20 } } },
    paragraphStyles: [ heading("Heading1", "Heading 1", 30, 0), heading("Heading2", "Heading 2", 24, 1) ],
  },
  numbering: { config: [{ reference: "b", levels: [{ level: 0, format: LevelFormat.BULLET, text: "•",
    alignment: AlignmentType.LEFT, style: { paragraph: { indent: { left: 480, hanging: 240 } } } }] }] },
  sections: [{
    properties: { page: { size: { width: 12240, height: 15840 }, margin: { top: 1440, right: 1440, bottom: 1440, left: 1440 } } },
    footers: { default: new Footer({ children: [ new Paragraph({ alignment: AlignmentType.CENTER,
      children: [ new TextRun({ text: "ProSlim-Microbiome-AI 可交付报告 v1.0  ·  ", size: 16, color: "888888" }),
        new TextRun({ children: ["第 ", PageNumber.CURRENT, " 页"], size: 16, color: "888888" }) ] }) ] }) },
    children: [
      // ---- title ----
      new Paragraph({ spacing: { before: 1800, after: 200 }, alignment: AlignmentType.CENTER,
        children: [new TextRun({ text: "ProSlim-Microbiome-AI", bold: true, size: 52, color: "1F3864" })] }),
      new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 120 },
        children: [new TextRun({ text: "完整可交付报告", bold: true, size: 36, color: "2E5A88" })] }),
      new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 600 },
        children: [new TextRun({ text: "减重相关肠道微生物：肥胖状态预测 · 干预应答评估 · 候选菌筛选与组合设计", size: 22, color: "555555" })] }),
      new Paragraph({ alignment: AlignmentType.CENTER, children: [new TextRun({ text: "版本 v1.1　|　日期 2026-06-14", size: 20 })] }),
      new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 200 },
        children: [new TextRun({ text: "范围：全链路（数据 → 双模型 → 223 菌筛选 → 组合假设）", size: 18, color: "888888" })] }),
      new Paragraph({ children: [new PageBreak()] }),

      // ---- TOC ----
      H("目录", HeadingLevel.HEADING_1),
      new TableOfContents("Table of Contents", { hyperlink: true, headingStyleRange: "1-2" }),
      new Paragraph({ children: [new PageBreak()] }),

      // ---- 0 ----
      H("0. 阅读须知（诚实声明）", HeadingLevel.HEADING_1),
      P("本报告区分三类结论，请勿混淆："),
      bullet("已验证信号：经跨队列/留出验证、优于基线的结果（仅肥胖状态模型）。"),
      bullet("诚实否定：经正确方法验证后不成立的结果（干预效应量不优于均值）。"),
      bullet("知识先验 / 设计假设：基于分类学/比较基因组的标注与机制设计——用于分流和优先级，不替代基因组级实测，不冒充疗效。"),
      P("两道门控贯穿全程：安全门（谁能进，需基因组确认）与疗效门（combination_ranking_enabled=false，效应量无信号则不发疗效排序）。二者独立。"),

      // ---- 1 ----
      H("1. 执行摘要", HeadingLevel.HEADING_1),
      table(["维度", "成果", "状态"],
        [["数据基础", "8304 样本×1405 物种 + 659 文献证据库", "完成"],
         ["肥胖状态模型", "瘦 vs 肥胖跨队列 ROC-AUC 0.729；BMI R² 0.103", "有信号"],
         ["可解释性", "SHAP 物种签名，三方互证", "完成"],
         ["干预效应量模型", "严格 meta（HKSJ/PM，仅直接方差）：仅 weight 可合并 −1.62kg 但非复制就绪；body_fat 不可合并", "无可复制信号"],
         ["菌株筛选库", "10 → 223（益生菌 + 人源非致病）；三步标注", "完成"],
         ["安全/机制候选", "79 机制候选 / 105 安全可入池 / 28 硬排除", "完成"],
         ["组合设计假设", "201 机制互补假设（设计轴，非疗效）", "假设"],
         ["疗效预测", "效应量不可预测 → 组合疗效未解锁", "数据受限"]],
        [2400, 5160, 1800]),
      P("一句话：建成了一个有信号的肥胖状态模型和一条安全分层、机制合理、可送验证的候选菌→组合设计链；但干预疗效在当前数据下不可预测，组合的“有效性”诚实地保持未解锁。"),

      // ---- 2,3 ----
      H("2. 目标与范围", HeadingLevel.HEADING_1),
      P("预测三件事：① 人群肥胖状态（微生物组→BMI/分类）；② 干预应答（菌株/配方的减重效应量）；③ 候选菌与组合（基于证据+机制+安全的筛选与设计）。"),
      H("3. 数据基础", HeadingLevel.HEADING_1),
      bullet("样本级微生物组：curatedMetagenomicData，8304 样本（瘦 4432/超重 2310/肥胖 1562）× 1405 物种，45 研究，BMI 全覆盖（11–66）。"),
      bullet("文献证据：659 去重 RCT/试验候选；83 研究进入效应量数据集，高置信含 SE 约 20-34 行。"),
      bullet("基因组：候选菌 NCBI assembly + 本报告新增 223 物种基因组映射。"),

      // ---- 4 ----
      H("4. 模型线 A — 肥胖状态模型（已验证信号）", HeadingLevel.HEADING_1),
      P("方法：HistGradientBoosting，206 物种特征（≥10% 流行率，log10 丰度）。按研究分组 10 折 CV（留出整个研究=新队列）为主，随机 CV 仅暴露混杂乐观偏差。"),
      table(["模型", "分组 CV（诚实）", "随机 CV", "基线", "优于基线"],
        [["肥胖分类器（瘦 vs 肥胖）", "ROC-AUC 0.729", "0.825", "0.5", "是"],
         ["BMI 回归", "R² 0.103, MAE 3.87", "R² 0.225", "MAE 4.15", "是"]],
        [2600, 2400, 1400, 1360, 1600]),
      P("可解释（SHAP）：保护型（Bifidobacterium longum、Phascolarctobacterium faecium、Turicibacter）；肥胖型（Allisonella histaminiformans 居首）。SHAP × 点二列相关 × 研究内分层一致性三方互证。"),
      P("意义：项目首个跨留出队列优于基线的模型。乐观偏差（0.73 vs 0.83）被如实暴露——约一半表面信号来自批次混杂，剩余 0.73 是真生物学。"),

      // ---- 5 ----
      H("5. 模型线 B — 干预效应量模型（诚实否定 + 方法学纠正）", HeadingLevel.HEADING_1),
      P("问题诊断：原 ML 留一验证在每 stratum 仅 5–12 研究上拟合 3–4 特征——统计方法错配，结果“0 stratum 优于均值基线”。"),
      P("方法学纠正（v1.1 严格版）：改用 Paule-Mandel τ² + 修正 HKSJ 区间（小样本正确方法），仅纳入直接方差（reported CI 或臂级 SD+n），p 值反算 SE 降级为敏感性；配合别名去重、共干预标记、缺失方差 bootstrap 三角验证、证据层敏感性。"),
      table(["Stratum", "直接方差 k", "合并效应(HKSJ)", "95%CI", "I²", "复制就绪"],
        [["weight|kg", "4", "−1.62 kg", "[−3.24,−0.006]", "76%", "否（区间/敏感性跨 0）"],
         ["body_fat|kg", "1", "—", "—", "—", "不可合并→复制假设(双向)"],
         ["BMI/lipid/waist/glucose", "<3", "—", "—", "—", "直接方差不足"]],
        [2100, 1100, 1500, 1700, 660, 2300]),
      P("关键修正：v1.0 基于较弱的 DL 方法 + p 值反算方差，曾报 body_fat −0.44 [−0.74,−0.13] CI 排除 0。严格 HKSJ + 直接方差下此结论不成立——body_fat 直接方差仅 k=1，效应双向（4 负 2 正），降级为优先复制假设。"),
      bullet("基因组 moderator / 人群特征桥接：均为小样本假象或过拟合，无稳健增益。两条线不能用人群特征桥接，需个体级 IPD。"),
      P("结论：严格小样本方法下，0 个 stratum 复制就绪、0 优于均值基线。weight 边际合并降低（−1.62 kg）但 I²=76%、预测区间与敏感性均跨 0，不可作疗效信号。这是正确方法得出的诚实零结果；约束被定位为直接方差研究太少（仅 13 研究/39 行）。combination_ranking_enabled 保持 false。"),

      // ---- 6 ----
      H("6. 菌株筛选库（10 → 223）与三步标注", HeadingLevel.HEADING_1),
      P("为何扩库：旧候选仅含临床测过的菌（数量少）；筛选库改为基因组/信号驱动——肥胖签名的人源菌 + 食品级益生菌。构成：109 人源共生 + 76 NGP + 38 食品级 = 223。"),
      table(["步骤", "依据（provenance）", "结果"],
        [["1 基因组映射", "NCBI Datasets API（实测）", "181/223 映射，125 isolate 质量；42 MAG/未解析"],
         ["2 安全分流", "EFSA QPS + 临床微生物学（知识先验）", "QPS 28 / LBP 5 / 新型需筛 165 / 病原·AMR 属 25"],
         ["3 功能注释", "90 属代谢 guild（知识先验）", "丙酸 58/乳酸 49/丁酸 35/黏液 31；4 个不利机制硬排除"]],
        [1700, 3600, 4060]),
      P("整合优先清单：79 机制候选（isolate 基因组 + 安全 + 有利机制）。不利机制硬排除（Desulfovibrio/Bilophila 产 H₂S、Allisonella 产组胺——与 SHAP 双重一致）。"),

      // ---- 7 ----
      H("7. 组合安全门与机制设计假设", HeadingLevel.HEADING_1),
      P("安全门资格（223 → 准入分流）：105 安全可入池（40 NGP + 39 共生 + 26 食品级），全标 pending（需真筛查）；28 硬排除（病原/AMR 属 + 不利机制）；90 无 isolate 基因组不可 QC。"),
      P("机制互补组合假设（201）：覆盖互补 SCFA/胆汁酸 niche + 交叉喂养。头号设计："),
      P("", { children: [new TextRun({ text: "Bifidobacterium longum + Anaerostipes hadrus + Phascolarctobacterium faecium + Akkermansia muciniphila", bold: true, size: 20 })] }),
      bullet("完整 SCFA 谱（乙酸→丁酸→丙酸）+ BSH 降脂 + 黏液屏障；含乳酸→丁酸交叉喂养；含 QPS 可交付锚 + 恢复耗竭保护菌。"),
      P("门控：predicted_response 全空，combination_ranking_enabled=false。这是临床前机制设计假设，非疗效。"),

      // ---- 8 ----
      H("8. 局限与门控（务必阅读）", HeadingLevel.HEADING_1),
      bullet("安全/功能标注为知识先验，无法检测菌株特异 AMR/毒力/可移动元件 → 需基因组级实测。"),
      bullet("除 5 个临床证据菌外，其余为筛选假设；“肥胖中耗竭”是关联非因果。"),
      bullet("41 个 MAG 有基因组信息但不可作产品。"),
      bullet("疗效未解锁：效应量不可预测，组合不发疗效排序。"),
      bullet("肥胖模型有混杂乐观偏差（已暴露），且为状态预测，非个体应答。"),

      // ---- 9 ----
      H("9. 下一步路线（按杠杆）", HeadingLevel.HEADING_1),
      table(["优先级", "行动", "杠杆"],
        [["1", "定向策展直接方差研究（报告臂级 SD/CI 的 weight/body_fat RCT，k 4→≥10）", "唯一能让 HKSJ 区间收窄"],
         ["2", "个体级 IPD（基线菌群+各自应答的 RCT）→ 真正的应答模型", "唯一能解锁个体疗效"],
         ["3", "真基因组筛查（下载 79/105 基因组 + AMRFinder/abricate/prokka/antiSMASH）", "把先验升级为实测"],
         ["4", "强化肥胖模型（功能通路+多样性、序数、校准、外部验证）", "唯一有信号的资产"]],
        [900, 5660, 2800]),
      P("真筛查 SOP（落地步骤 2/3）：datasets download → AMRFinderPlus/abricate(CARD/VFDB/ResFinder) 安全 → prokka/bakta + antiSMASH + BSH/bai 检测功能 → 体外验证 → 通过安全门方进推荐。"),

      // ---- 10 ----
      H("10. 主要产出文件索引", HeadingLevel.HEADING_1),
      bullet("模型：models/obesity_classifier/、models/BMI_regressor/；obesity_model_metrics_20260613.json"),
      bullet("可解释：results/SHAP_results/obesity_shap_{beeswarm,bar}_20260613.png + shap_importance CSV"),
      bullet("效应量：effect_meta_analysis_20260613.json"),
      bullet("菌株筛选主表：strain_screening_catalog_functional_20260613.csv；79 候选 shortlist；105 安全可入池"),
      bullet("组合：mechanism_complementary_hypotheses_20260613.csv（201 设计假设）"),
      bullet("文档：strain_screening_report、research_plan_next、session_summary（均 _20260613.md）"),

      P("", { spacing: { before: 300 }, children: [new TextRun({ text: "本报告所有“知识先验/设计假设”类结论需基因组级实测与临床验证后方可用于产品决策。秉持：不调参凑基线、不注入脏数据、不保留好看版本、关联不冒充因果、安全门不可绕过。", italics: true, size: 18, color: "666666" })] }),
    ],
  }],
});

Packer.toBuffer(doc).then(buf => {
  fs.writeFileSync(path.join("docs", "ProSlim_Microbiome_AI_可交付报告_v1.1_20260614.docx"), buf);
  console.log("docx written:", buf.length, "bytes");
});
