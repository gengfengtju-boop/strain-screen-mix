const fs = require("fs");
const path = require("path");
const { Document, Packer, Paragraph, TextRun, Table, TableRow, TableCell,
        AlignmentType, LevelFormat, HeadingLevel, BorderStyle, WidthType,
        ShadingType, ImageRun, PageBreak, PageNumber, Footer } = require("docx");

const ROOT = "D:/strain screen mix";
const PR = path.join(ROOT, "results/prediction_results");
const CR = path.join(ROOT, "results/combination_recommendations");
const OUT = path.join(ROOT, "docs/西欧队列与机制分析_综合研究论文_20260625.docx");
const SERIF = "SimSun", HEI = "SimHei";
const A4W = 11906, A4H = 16838, MARGIN = 1418, CONTENT = A4W - 2 * MARGIN;

const J = (p) => JSON.parse(fs.readFileSync(p, "utf8"));
function csv(p) {
  const t = fs.readFileSync(p, "utf8").replace(/^\uFEFF/, "").trim().split(/\r?\n/);
  const h = t[0].split(",");
  return t.slice(1).map(l => { const v = l.split(","); const o = {}; h.forEach((k, i) => o[k] = v[i]); return o; });
}
const S   = J(path.join(PR, "we_healthy/analysis_summary.json"));
const V   = J(path.join(PR, "bottomup_validation/validation_summary.json"));
const BIO = J(path.join(PR, "bottomup_validation/bio_only_features.json"));
const LF  = J(path.join(PR, "lean_factors/summary.json"));
const MC  = J(path.join(PR, "lean_factors/model_comparison.json"));
const BA  = J(path.join(PR, "bile_acid/assessment.json"));
const V2  = J(path.join(CR, "synergistic_v2_robust_summary_20260625.json"));
const cohort = csv(path.join(PR, "we_healthy/cohort_sources.csv"));
const da = csv(path.join(PR, "we_healthy/differential_abundance_adjusted.csv"));
const pool = csv(path.join(CR, "synergistic_pool_v2_robust_20260625.csv"));
const comb = csv(path.join(CR, "synergistic_lean_combinations_v2_robust_20260625.csv"));
const n = (x) => parseFloat(x);
const robust = da.filter(r => String(r.robust).toLowerCase() === "true");
const lean = robust.filter(r => r.direction === "lean_enriched").sort((a, b) => n(b.meta_g) - n(a.meta_g));
const obese = robust.filter(r => r.direction === "obese_enriched").sort((a, b) => n(a.meta_g) - n(b.meta_g));

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
const h3 = (t) => new Paragraph({ heading: HeadingLevel.HEADING_3, spacing: { before: 150, after: 80 },
  children: [new TextRun({ text: t, font: HEI, size: 21, bold: true })] });
const cb = { style: BorderStyle.SINGLE, size: 1, color: "BBBBBB" };
const bd = { top: cb, bottom: cb, left: cb, right: cb };
const cell = (t, w, head, ac) => new TableCell({ borders: bd, width: { size: w, type: WidthType.DXA },
  shading: { fill: head ? "D9E2F0" : "FFFFFF", type: ShadingType.CLEAR },
  margins: { top: 46, bottom: 46, left: 70, right: 70 },
  children: [new Paragraph({ alignment: ac ? AlignmentType.CENTER : AlignmentType.LEFT,
    children: [new TextRun({ text: String(t), font: SERIF, size: 15, bold: head })] })] });
function table(hd, rows, w) {
  const mk = (c, h) => new TableRow({ tableHeader: h, children: c.map((x, i) => cell(x, w[i], h, i > 0)) });
  return new Table({ width: { size: CONTENT, type: WidthType.DXA }, columnWidths: w,
    rows: [mk(hd, true), ...rows.map(r => mk(r, false))] });
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
const CN = { Barnesiella_intestinihominis: "人肠巴恩斯氏菌", Odoribacter_splanchnicus: "内脏臭杆菌",
  Alistipes_putredinis: "腐败另枝菌", Bacteroides_cellulosilyticus: "解纤维素拟杆菌",
  Intestinimonas_butyriciproducens: "产丁酸肠单胞菌", Butyrivibrio_crossotus: "丛毛丁酸弧菌",
  Bacteroides_intestinalis: "肠拟杆菌", Akkermansia_muciniphila: "嗜黏蛋白阿克曼氏菌",
  Eubacterium_eligens: "优选真杆菌", Methanobrevibacter_smithii: "史氏甲烷短杆菌",
  Ruminococcus_gnavus: "鼠李糖瘤胃球菌" };
const cn = (s) => CN[s] || s.replace(/_/g, " ");

const C = [];
// ============ 封面 ============
C.push(new Paragraph({ alignment: AlignmentType.CENTER, spacing: { before: 900, after: 130 },
  children: [new TextRun({ text: "西欧健康人群肠道菌群肥胖差异及其", font: HEI, size: 38, bold: true })] }));
C.push(new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 200 },
  children: [new TextRun({ text: "减脂机制特征的系统性评估", font: HEI, size: 38, bold: true })] }));
C.push(new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 90 },
  children: [new TextRun({ text: "从队列差异分析到机制特征验证与菌株组合定标", font: HEI, size: 23, bold: true })] }));
C.push(new Paragraph({ alignment: AlignmentType.CENTER, spacing: { before: 300, after: 60 },
  children: [new TextRun({ text: "ProSlim-Microbiome-AI 项目组", font: SERIF, size: 22 })] }));
C.push(new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 900 },
  children: [new TextRun({ text: "2026 年 6 月 25 日", font: SERIF, size: 20 })] }));
C.push(new Paragraph({ children: [new PageBreak()] }));

// ============ 摘要 ============
C.push(new Paragraph({ spacing: { after: 100 }, children: [new TextRun({ text: "摘要", font: HEI, size: 26, bold: true })] }));
C.push(body(`**背景与目的：**肠道菌群与肥胖的关联广受关注，但既有报道普遍未控制年龄、性别与代谢疾病等混杂，且菌株筛选多依赖未经验证的机制先验。本研究旨在：(1) 在严格控制混杂的条件下确定西欧健康人群的肥胖相关菌群差异；(2) 系统评估各类机制特征对"瘦人相关菌"的预测能力；(3) 据此重构菌株组合的定标依据。`, { noIndent: true }));
C.push(body(`**材料与方法：**自 8 304 例公开鸟枪法宏基因组样本逐级筛选，排除 2 型糖尿病、糖耐量异常与高血压，纳入 ${S.eligible_studies} 项独立研究（${S.countries.join("、")}）共 ${S.n_lean_total} 例瘦人与 ${S.n_obese_total} 例肥胖者。采用**研究内 1:1 年龄（±5 岁）性别匹配**（n=${S.matched.n}）联合回归协变量校正的双重混杂控制策略。对 ${S.n_species_tested} 个物种行 OLS 差异分析（Benjamini-Hochberg FDR），并以 DerSimonian-Laird 随机效应 meta 分析交叉验证；以留一研究交叉验证的随机森林检验判别效力。进一步构建功能潜能、生态学与知识型三类特征，采用**留一属交叉验证**评估其跨类群泛化能力。`, { noIndent: true }));
C.push(body(`**结果：**匹配后仅年龄性别模型 AUC 降至 ${S.ai_demographics_only_auc}（近随机），而菌群模型仍达 ${S.ai_matched_loso_auc}，证实菌群差异独立于人口学。${S.n_fdr_significant} 个物种达 FDR<0.05，其中 ${S.n_robust} 个通过 meta 验证。产甲烷古菌 Methanobrevibacter smithii 为最稳健瘦人标志（I²=0%，胖/瘦 0.29 倍），Ruminococcus gnavus 在肥胖者中丰度翻倍（2.05 倍）。丁酸产生菌呈现种间方向分化。机制特征评估显示：**与群落多样性的关联**判别力最高（AUC ${LF.single_features.find(x=>x.feature==="diversity_association").auc}）且为唯一可跨属泛化者（留一属 AUC ${MC["仅多样性关联"]}）；丙酸潜能样本内有效（10/10）但不能跨属泛化（${MC["仅丙酸"]}）；**胆盐水解酶（BSH）无任何预测能力**（AUC ${BA.single_axis.find(x=>x.axis==="BSH 潜能(0/1/2)").auc}，P=0.85），跨属为 ${BA.cross_genus_auc["仅 BSH"]}，纳入后反使最佳模型由 0.878 降至 0.798。据此重新加权的组合定标（v2）首选为人肠巴恩斯氏菌、内脏臭杆菌与腐败另枝菌，且在放宽纳入标准的敏感性分析中排序不变。`, { noIndent: true }));
C.push(body(`**结论：**严格校正后肠道菌群的肥胖相关差异真实存在且独立于年龄性别。菌株筛选应以**群落多样性关联**为首要指标，辅以实测效应与丙酸潜能；**应停止以 BSH 与"丁酸产生菌"作为减脂筛选标准**。菌株组合仍为候选定标，其疗效须经前瞻试验验证。`, { noIndent: true }));
C.push(new Paragraph({ spacing: { before: 110, after: 200 }, children: [
  new TextRun({ text: "关键词：", font: HEI, size: 20, bold: true }),
  new TextRun({ text: "肠道菌群；肥胖；宏基因组学；倾向性匹配；随机效应 meta 分析；α 多样性；短链脂肪酸；胆盐水解酶；机器学习", font: SERIF, size: 20 })] }));
C.push(new Paragraph({ children: [new PageBreak()] }));

// ============ 1 引言 ============
C.push(h1("1　引言"));
C.push(body("肥胖已成为全球性公共卫生负担，肠道菌群被认为通过能量收获、短链脂肪酸信号、胆汁酸代谢与肠屏障功能参与其发生发展。然而，已发表的“肥胖菌群特征”在不同研究间重复性有限，其原因至少有三：其一，肥胖人群往往年龄更大、代谢疾病更多，多数研究未对这些混杂因素作充分控制；其二，跨研究的批次与测序差异易被误读为生物学信号；其三，基于“功能属”的机制先验（如认定丁酸产生菌或含胆盐水解酶的菌必然有益）缺乏在严格数据上的检验。"));
C.push(body("本研究以西欧公开鸟枪法宏基因组队列为对象，采取三项设计以回应上述问题：**排除全部代谢疾病个体**以剥离疾病混杂；**在研究内部作 1:1 年龄性别匹配**，从而同时消除人口学与批次混杂；**以留一研究与留一属两级交叉验证**分别检验模型的跨队列与跨类群泛化能力。在此基础上，本文进一步系统评估功能潜能、生态学与知识型三类机制特征的预测能力，并据实测结果重构菌株组合的定标依据。"));

// ============ 2 材料与方法 ============
C.push(h1("2　材料与方法"));
C.push(h2("2.1　数据来源与物种定量"));
C.push(body("本研究使用公开人体肠道宏基因组数据集体系（curatedMetagenomicData 汇编），所有纳入样本均为**鸟枪法全宏基因组测序**（非 16S 扩增子），物种水平相对丰度由 MetaPhlAn 系列标记基因方法统一定量，单位为百分比（%），每样本各物种丰度之和为 100%。样本元数据包含研究编号、国家、年龄、性别、体质指数（BMI）、肥胖分型与疾病状态。"));
C.push(h3("2.1.1　伴随表型定义"));
C.push(body("肥胖分型（lean / overweight / obesity）沿用原始队列的策展标注（以 BMI 为主要依据）；疾病状态包含 healthy、T2D（2 型糖尿病）、IGT（糖耐量异常）与 hypertension（高血压）。"));

C.push(h2("2.2　纳入与排除标准"));
C.push(body("逐级应用以下标准（表 1）：(1) 国家属于西欧（荷兰、英国、丹麦、法国、德国、意大利、西班牙、瑞典、奥地利、爱尔兰、卢森堡）；(2) **疾病状态为 healthy**，即排除全部 T2D、IGT 与高血压个体，以确保观察到的差异归因于肥胖本身而非代谢疾病；(3) 肥胖分型为 lean 或 obesity，排除 overweight 中间态以增强对比度；(4) 年龄与性别记录完整；(5) 该研究内瘦人与肥胖两组各不少于 10 例，以保证研究内可比性与匹配可行性。"));
C.push(table(["筛选步骤", "剩余样本量", "排除数"], S.cohort_filter_steps.map((s, i) => [s.step, s.n,
  i === 0 ? "—" : String(S.cohort_filter_steps[i - 1].n - s.n)]), [5300, 2000, 1726]));
C.push(cap("表 1　队列筛选流程"));

C.push(h2("2.3　混杂控制：双重独立策略"));
C.push(h3("2.3.1　研究内 1:1 年龄性别匹配"));
C.push(body(`原始队列中肥胖组年龄系统性高于瘦人组（如 AsnicarF_2021 为 49.2 对 42.7 岁；KeohaneDM_2020 为 44.5 对 27.8 岁），性别构成亦存在差异。为此，对每一例肥胖受试者，在**同一研究内部**检索性别相同、年龄差不超过 5 岁的瘦人对照，采用**最近邻无放回**抽样（若存在多个候选，取年龄差最小者；已被匹配的个体不再进入候选池）。研究内匹配的额外优势在于同时消除测序中心、建库方案与地域带来的批次效应。匹配后样本量为 **n=${S.matched.n}**（瘦人 ${S.matched.lean} 例、肥胖 ${S.matched.obese} 例），两组平均年龄分别为 ${S.matched.age_lean} 与 ${S.matched.age_obese} 岁，女性比例均为 ${S.matched.female_lean}，达到完全平衡。`));
C.push(h3("2.3.2　回归协变量校正"));
C.push(body("在差异丰度模型中再次纳入年龄、性别与研究作为协变量，形成与匹配相互独立的第二重保障，以校正匹配容差（±5 岁）内的残余差异。"));

C.push(h2("2.4　差异丰度分析"));
C.push(body(`物种筛选：仅保留在匹配队列中**流行率不低于 10%**（即至少 10% 样本可检出）的物种，共 ${S.n_species_tested} 个，以避免零膨胀导致的统计不稳。`));
C.push(body("**主模型**：对每个物种，以 log10(相对丰度 + 0.001) 为因变量（伪计数 0.001% 用于处理零值），拟合普通最小二乘回归："));
C.push(new Paragraph({ alignment: AlignmentType.CENTER, spacing: { before: 60, after: 60 },
  children: [new TextRun({ text: "log10(丰度 + 0.001) ~ 肥胖 + 年龄 + 性别 + 研究", font: SERIF, size: 21, italics: true })] }));
C.push(body("其中研究以哑变量形式作为固定效应纳入。提取肥胖项的回归系数与 P 值，并采用 **Benjamini-Hochberg 法**控制错误发现率（FDR）。倍数变化由回归系数换算：FC = 10^β（β 为肥胖项系数，FC<1 表示肥胖者较低）。", { noIndent: true }));

C.push(h2("2.5　随机效应 meta 分析（稳健性交叉验证）"));
C.push(body("为避免单一模型设定带来的偏倚，对每个物种独立执行第二套分析：在**各研究内部**分别计算瘦人与肥胖组 log10 丰度的标准化均数差，并施加 Hedges 小样本偏倚校正因子 J = 1 − 3/[4(n₁+n₂) − 9] 得到 Hedges g；随后以 **DerSimonian-Laird 随机效应模型**合并各研究效应量，报告合并 g、95% 置信区间与异质性指标 I²。仅纳入两组各不少于 5 例的研究，且要求至少 3 项研究方可合并。"));
C.push(body("**稳健差异菌判定**：须同时满足三项条件——(i) 主模型 FDR<0.05；(ii) meta 合并 95%CI 排除 0；(iii) 两种方法给出的效应方向一致。三重判定旨在剔除仅因单一模型设定或个别研究驱动而显著的物种。"));

C.push(h2("2.6　机器学习判别与验证"));
C.push(body("采用**平衡随机森林**（500 棵树，最大深度 6，最小叶节点样本数 3，类别权重按频数倒数平衡）以物种相对丰度为输入判别瘦/胖。验证采用**留一研究交叉验证**：每次留出一整项研究作为独立测试集，其余研究用于训练，从设计上杜绝批次泄漏。作为混杂消除的对照，另以仅年龄与性别为输入训练同构模型；若匹配充分，该对照模型的 AUC 应接近 0.5。"));

C.push(h2("2.7　机制特征构建"));
C.push(h3("2.7.1　功能潜能特征（属级）"));
C.push(body("依据 90 个属的代谢 guild 参考表，为每个物种赋予其所属属的丁酸、丙酸、黏液相互作用与胆盐水解酶（BSH）潜能评分（0/1/2）。该注释为**属级知识先验**，非菌株级基因组实测。"));
C.push(h3("2.7.2　生态学特征（数据推导）"));
C.push(body("(1) **流行率**与**平均丰度**：在匹配队列中计算。(2) **与多样性的关联**：先按 Shannon 指数 H = −Σpᵢln pᵢ 计算每例样本的 α 多样性，再**在瘦人组与肥胖组内部分别**计算该物种 log10 丰度与 Shannon 指数的 Spearman 相关系数，取两组平均。**组内计算是关键设计**：它检验的是“在胖瘦相同的人群中，菌群越多样者该菌是否越多”，因而不构成对胖瘦标签的重述，避免了循环论证。(3) **共现网络中心度**：以 Spearman |ρ|>0.30 为阈值统计该物种的共现伙伴数。(4) **瘦人菌共现亲和度**：与已确认稳健瘦人标志的平均相关系数（留自身法）；因该指标与标签部分定义性重叠，仅作展示、不纳入结论。"));
C.push(h3("2.7.3　知识型特征"));
C.push(body("依据分类学与微生物学文献标注：口腔来源菌（Streptococcus、Actinomyces、Veillonella、Gemella、Rothia、Haemophilus、Fusobacterium 等）、严格厌氧、芽孢形成能力、纤维降解能力。另补充胆汁酸相关的两条通路：7α-脱羟基（次级胆汁酸产生，限于 Clostridium scindens、C. hylemonae、C. hiranonis 等少数梭菌）与胆汁耐受/敏感属。"));

C.push(h2("2.8　特征评估：留一属交叉验证"));
C.push(body("特征的判别力以单变量 AUC 与 Mann-Whitney U 检验评估。**跨类群泛化能力**以**留一属交叉验证**评估：每次留出一个属的全部物种作为测试集，其余属用于训练逻辑回归（L2 正则，C=0.5，标准化后）。该设计的必要性在于——属级功能注释与分类学完全共线，若采用常规随机拆分，模型可通过记忆属的身份而非学习机制获得虚高性能；留一属验证恰好剔除该信息，因而是检验“该特征能否用于预测新类群”的正确方式。"));

C.push(h2("2.9　自下而上程序的对比验证"));
C.push(body("项目既有的自下而上程序（由肥胖分类器 SHAP 信号方向、基因组功能潜能与安全分层推测菌株减脂效果，输出 223 株目录）以**全部 8 304 样本的未校正模型**为基础。本研究以 2.4–2.5 节的严格结果为金标准，在三个证据层级（全部受检物种、FDR<0.05 显著、稳健差异菌）比较两者的一致率与 Cohen's κ，并分别计算“预测保护”与“预测促肥胖”两个方向的精确率。"));

C.push(h2("2.10　菌株组合定标与重新加权"));
C.push(body(`组合评分对 3–5 株的全部组合穷举打分。**版本 1**的权重基于机制假设；**版本 2**（本研究）的每一项权重均由 2.8 节的验证结果确定：与多样性关联 0.30、实测 meta 效应 0.24、机制互补 0.16、丙酸潜能 0.12、可培养性 0.10、属多样性 0.08，并对芽孢形成（−0.05）与口腔来源（−0.10）成员施加惩罚；**BSH 项由 0.16 归零**。候选池亦由全局未校正分析的 53 株升级为本研究稳健验证的 ${V2.pool_size} 株，并排除硫化氢产生菌（Bilophila、Desulfovibrionaceae）、仅宏基因组拼接（MAG）物种与产甲烷古菌。**敏感性分析**：将纳入标准放宽为仅要求 FDR<0.05（不强制 meta 95%CI 排除 0），候选池扩至 20 株，重复全部打分。`));

C.push(h2("2.11　统计环境"));
C.push(body("全部分析在 Python 3.13 环境完成，主要依赖 pandas 2.3、numpy 2.3、scikit-learn（随机森林与逻辑回归）、statsmodels 0.14（OLS）与 scipy（Spearman 相关、Mann-Whitney U 检验）。随机数种子固定为 0 以保证可重复。双侧检验，显著性水平取 0.05。"));
C.push(new Paragraph({ children: [new PageBreak()] }));

// ============ 3 结果 ============
C.push(h1("3　结果"));
C.push(h2("3.1　队列构成"));
C.push(body(`经逐级筛选，最终纳入 **${S.eligible_studies} 项独立研究**，覆盖 ${S.countries.length} 个国家（${S.countries.join("、")}），全部为鸟枪法宏基因组测序，共 ${S.n_lean_total} 例瘦人与 ${S.n_obese_total} 例肥胖者（表 2）。各研究的两组年龄差异不一，其中人群队列（AsnicarF_2021、LifeLinesDeep_2016）与爱尔兰队列（KeohaneDM_2020）差异尤为明显，进一步印证了年龄校正的必要性。`));
C.push(table(["研究队列", "国家", "瘦(n)", "肥胖(n)", "年龄瘦/胖", "女性比瘦/胖", "BMI瘦/胖"],
  cohort.map(r => [r.study_id, r.country, r.n_lean, r.n_obese, `${r.age_lean}/${r.age_obese}`,
    `${r.female_lean}/${r.female_obese}`, `${r.bmi_lean}/${r.bmi_obese}`])
    .concat([["合计", "—", String(S.n_lean_total), String(S.n_obese_total), "—", "—", "—"]]),
  [2000, 660, 660, 720, 1350, 1400, 1280]));
C.push(cap("表 2　合格数据队列来源与人口学特征"));

C.push(h2("3.2　混杂消除的验证"));
C.push(body(`匹配前，仅以年龄与性别为输入的模型即可达到 AUC 0.722，高于菌群单独模型的 0.695，提示未校正的比较存在实质性人口学混杂。**匹配后，该对照模型 AUC 降至 ${S.ai_demographics_only_auc}，接近随机水平，而菌群模型仍达 ${S.ai_matched_loso_auc}**（表 3，图 1B），证实观察到的菌群差异并非年龄或性别的副产品。`));
C.push(table(["模型", "留一研究 AUC", "解读"],
  [["仅年龄 + 性别（对照）", String(S.ai_demographics_only_auc), "接近随机，混杂已消除"],
   ["菌群（199 物种）", String(S.ai_matched_loso_auc), "跨研究可泛化的独立信号"]],
  [2800, 2200, 5070]));
C.push(cap("表 3　匹配队列上的判别效力对照"));
C.push(body("各研究留出表现存在系统性差异：丹麦三项研究（LeChatelierE_2013、HansenLBS_2018、NielsenHB_2014，源自 MetaHIT 计划）AUC 达 0.89–1.00，而人群队列（AsnicarF_2021 为 0.67、LifeLinesDeep_2016 为 0.66、XieH_2016 为 0.65）明显较低。前者以“极端表型对比”为招募设计，故判别性偏高；**人群队列的估计更接近真实世界效力**。"));
C.push(...figure("fig17_we_healthy_full.png", "图 1　西欧健康队列胖瘦差异菌群总览：(A) 校正后差异丰度火山图；(B) 留一研究交叉验证；(C) 稳健瘦人富集菌森林图；(D) 稳健肥胖富集菌森林图", 0.693));

C.push(h2("3.3　差异丰度结果"));
C.push(body(`在 ${S.n_species_tested} 个受检物种中，${S.n_fdr_significant} 个达 FDR<0.05；其中 **${S.n_robust} 个**同时通过随机效应 meta 验证，判定为稳健差异菌（表 4、表 5）。`));
C.push(table(["物种", "合并 g", "95% CI", "倍数(胖/瘦)", "FDR", "I²"],
  lean.slice(0, 12).map(r => [r.species.replace(/_/g, " "), (+r.meta_g).toFixed(2),
    `${(+r.ci_low).toFixed(2)} ~ ${(+r.ci_high).toFixed(2)}`, (+r.fold_change_obese_vs_lean).toFixed(2),
    (+r.fdr).toExponential(1), `${Math.round(+r.I2_percent)}%`]), [2900, 850, 1600, 1400, 1200, 1120]));
C.push(cap("表 4　稳健瘦人富集菌（按合并效应量排序，前 12）"));
C.push(table(["物种", "合并 g", "95% CI", "倍数(胖/瘦)", "FDR", "I²"],
  obese.slice(0, 10).map(r => [r.species.replace(/_/g, " "), (+r.meta_g).toFixed(2),
    `${(+r.ci_low).toFixed(2)} ~ ${(+r.ci_high).toFixed(2)}`, (+r.fold_change_obese_vs_lean).toFixed(2),
    (+r.fdr).toExponential(1), `${Math.round(+r.I2_percent)}%`]), [2900, 850, 1600, 1400, 1200, 1120]));
C.push(cap("表 5　稳健肥胖富集菌（全部）"));
C.push(body("**产甲烷古菌 Methanobrevibacter smithii 为最稳健的瘦人标志**（g=+0.37，I²=0%，肥胖者丰度仅为瘦人的 0.29 倍，FDR=3.4×10⁻⁶）。**Ruminococcus gnavus 在肥胖者中丰度翻倍**（2.05 倍，FDR=1.1×10⁻⁴），该菌为已知黏液降解与促炎菌。"));
C.push(body("值得注意的是，**丁酸产生菌呈现种间方向分化**：Butyrivibrio crossotus（0.44 倍，I²=0%）与 Eubacterium eligens（0.49 倍，I²=0%）富集于瘦人，而同为经典丁酸产生菌的 Roseburia intestinalis（1.74 倍）与 Eubacterium rectale（1.81 倍）却富集于肥胖。这提示以“功能属”为单位的机制推断存在方向性风险。"));

C.push(h2("3.4　自下而上程序的对比验证"));
C.push(body(`一致性随证据强度提升：全部受检物种仅 ${(V.concordance["全部受检物种"].一致率*100).toFixed(1)}%（κ=${V.concordance["全部受检物种"].kappa}，接近随机），稳健差异菌上达 **${(V.concordance["稳健差异菌"].一致率*100).toFixed(1)}%（κ=${V.concordance["稳健差异菌"].kappa}）**（表 6）。更重要的是，**程序的可靠性高度不对称**：预测“保护/瘦人富集”时精确率为 24/25=96%，而预测“促肥胖”时仅 6/12=50%。程序并将促炎菌 Ruminococcus gnavus 误判为保护菌，构成有实际后果的错误。`));
C.push(table(["比对范围", "物种数", "一致率", "Cohen's κ", "判定"],
  [["全部受检物种", String(V.concordance["全部受检物种"].n), (V.concordance["全部受检物种"].一致率*100).toFixed(1)+"%", String(V.concordance["全部受检物种"].kappa), "弱一致"],
   ["FDR<0.05 显著", String(V.concordance["FDR<0.05 显著"].n), (V.concordance["FDR<0.05 显著"].一致率*100).toFixed(1)+"%", String(V.concordance["FDR<0.05 显著"].kappa), "中等一致"],
   ["稳健差异菌", String(V.concordance["稳健差异菌"].n), (V.concordance["稳健差异菌"].一致率*100).toFixed(1)+"%", String(V.concordance["稳健差异菌"].kappa), "中等一致"]],
  [2200, 900, 1000, 1100, 3870]));
C.push(cap("表 6　自下而上程序与严格筛选结果的一致性"));
C.push(...figure("fig18_bottomup_validation.png", "图 2　自下而上程序对比验证：(A) 混淆矩阵；(B) 一致性随证据强度变化；(C) 各特征判别力；(D) 丙酸与丁酸对比", 0.717));

C.push(h2("3.5　机制特征的预测能力"));
C.push(h3("3.5.1　功能潜能：丙酸有效，丁酸无效"));
C.push(body(`剔除源自模型自身的循环特征后，**丙酸产生潜能是唯一有效的功能特征**：10 个具丙酸潜能的显著物种全部为瘦人富集（${(BIO.propionate_pos_lean_rate*100).toFixed(0)}%），高于无丙酸潜能者的 ${(BIO.propionate_neg_lean_rate*100).toFixed(0)}%。**丁酸潜能无效且方向相反**：具丁酸潜能者瘦人富集率 ${(BIO.butyrate_pos_lean_rate*100).toFixed(0)}%，低于无丁酸潜能者的 ${(BIO.butyrate_neg_lean_rate*100).toFixed(0)}%（总体基线 83%）。然而，**仅用属级功能特征时留一属交叉验证 AUC 仅 ${BIO.bio_only_loso_genus_auc_logreg}–${BIO.bio_only_loso_genus_auc_rf}**，不优于随机——功能潜能与分类学共线，无法用于预测新类群。`));
C.push(h3("3.5.2　群落多样性关联：判别力最高且唯一可跨属泛化"));
C.push(body(`在生态学与知识型特征中，**与群落多样性的关联判别力最高**（AUC ${LF.single_features.find(x=>x.feature==="diversity_association").auc}，P<0.001）：瘦人富集菌的组内多样性关联均值为 +0.193，而肥胖富集菌仅 +0.025（表 7、图 3C）。更关键的是，**该特征是唯一能跨属泛化者**：仅用多样性关联的留一属 AUC 达 ${MC["仅多样性关联"]}，与丙酸联合可达 ${MC["多样性关联+丙酸"]}，而仅用丙酸为 ${MC["仅丙酸"]}、仅用知识型特征为 ${MC["仅知识特征(口腔/需氧/芽孢/纤维)"]}（图 3B）。`));
C.push(table(["因素", "AUC", "方向", "瘦人富集菌均值", "肥胖富集菌均值", "显著性"],
  LF.single_features.slice(0, 6).map(r => {
    const map = { lean_marker_affinity: "与已确认瘦人菌共现亲和度", diversity_association: "与群落多样性的关联",
      spore_former: "芽孢形成能力", oral_origin: "口腔来源菌", strict_anaerobe: "严格厌氧",
      fiber_degrader: "纤维降解能力", prevalence: "流行率", cooccurrence_degree: "共现网络中心度",
      mean_log_abundance: "平均丰度水平" };
    const p = r.p_mannwhitney;
    return [map[r.feature] || r.feature, String(r.auc), r.direction, String(r.lean_mean), String(r.obese_mean),
      p < 0.001 ? "P<0.001" : (p < 0.05 ? `P=${p.toFixed(3)}` : "不显著")];
  }), [2600, 800, 1000, 1600, 1600, 1470]));
C.push(cap("表 7　与瘦人菌株相关的候选因素（按判别力排序，前 6）"));
C.push(...figure("fig19_lean_factors.png", "图 3　减脂相关因素筛选：(A) 各因素判别力；(B) 跨属泛化能力比较；(C) 多样性关联的组间分布；(D) 知识型性质对比", 0.647));
C.push(body("生物学层面，该结果可归纳为两种生态策略：**协作型**菌（Alistipes、Oscillibacter、Odoribacter、Barnesiella、Coprococcus）能与高多样性群落共存，随群落多样化而增多；**垄断型**菌（Prevotella copri、Ruminococcus gnavus、Collinsella、Eggerthella）则在单一化群落中爆发。以 Prevotella copri 为例，其在低多样性人群中平均丰度达 15.87%，而在高多样性人群中仅 1.58%，此种“占位垄断”模式恰可解释其百分点差极大（−2.62）而标准化效应很小（d=−0.16）的表观矛盾。"));
C.push(...figure("fig20_diversity_detail.png", "图 4　多样性关联详解：(A) 队列 α 多样性指标；(B) 多样性伴随菌与低多样性伴随菌排序；(C) 高/低多样性人群中的实际丰度；(D) 属级规律", 0.686));

C.push(h2("3.6　胆汁酸（BSH）预测能力评估"));
C.push(body(`鉴于胆盐水解酶（BSH）在既有组合评分中被赋予 16% 的“降胆固醇”权重，本研究对其作专门评估。结果显示：**BSH 对瘦人富集无任何预测能力**（AUC ${BA.single_axis.find(x=>x.axis==="BSH 潜能(0/1/2)").auc}，P=0.852），远低于丙酸（0.647）与多样性关联（0.920）；**跨属泛化 AUC 仅 ${BA.cross_genus_auc["仅 BSH"]}**，即系统性反向；**纳入 BSH 反使最佳模型由 ${MC["仅多样性关联"]} 降至 ${BA.cross_genus_auc["多样性+BSH"]}**（表 8）。`));
C.push(table(["特征组合", "留一属 CV AUC", "判定"],
  Object.keys(BA.cross_genus_auc).sort((a, b) => BA.cross_genus_auc[b] - BA.cross_genus_auc[a])
    .map(k => [k, String(BA.cross_genus_auc[k]), BA.cross_genus_auc[k] >= 0.8 ? "可泛化" : (BA.cross_genus_auc[k] >= 0.5 ? "弱" : "远低于随机")]),
  [4200, 2000, 2870]));
C.push(cap("表 8　胆汁酸相关特征的跨属泛化能力"));
C.push(body(`进一步分析表明，41 个显著物种中仅 7 个 BSH 阳性，其中 6 个瘦人富集者有 5 个属拟杆菌属——而拟杆菌属本身即为丙酸产生菌且多样性关联为正（ρ 为 +0.15 至 +0.21），**BSH 的表观关联可由丙酸与多样性充分解释**。此外存在两项硬约束：其一，具强 BSH 的乳杆菌类在 199 个受检物种中仅 ${BA.annotation_coverage["强BSH(=2)"]} 个，说明 BSH 属于“外源补充益生菌”范式而非肠道常驻生态；其二，可关联到干预菌种的血脂结局仅 ${BA.rct_cholesterol_evidence["可关联干预菌种的行"]} 行，**远不足以检验“BSH→降胆固醇”假说本身**。`));
C.push(...figure("fig21_bile_acid_assessment.png", "图 5　胆汁酸（BSH）预测能力评估：(A) 各轴判别力；(B) 跨属泛化；(C) BSH 阳性物种归属；(D) 注释覆盖与 RCT 证据约束", 0.683));

C.push(h2("3.7　菌株组合定标的重新加权与敏感性分析"));
C.push(body(`依据上述验证结果重构组合评分（版本 2）：与多样性关联升为首要权重（0.30），实测 meta 效应次之（0.24），**BSH 项归零**，丁酸不再作为正向项，并对芽孢形成与口腔来源成员施加惩罚。候选池由全局未校正分析的 53 株升级为本研究稳健验证的 ${V2.pool_size} 株。`));
C.push(table(["评分项", "版本 1", "版本 2", "调整依据"],
  [["与多样性关联", "—", "0.30", "AUC 0.920，唯一可跨属泛化（0.878）"],
   ["实测胖瘦效应", "0.10", "0.24", "本研究 meta 合并效应量"],
   ["机制互补", "0.28", "0.16", "仍为设计原则，不再主导"],
   ["丙酸潜能", "隐含", "0.12", "AUC 0.647，但不可跨属泛化"],
   ["菌株性质（可培养）", "0.14", "0.10", "基本不变"],
   ["属多样性", "0.06", "0.08", "组合层面"],
   ["BSH 降胆固醇", "0.16", "0.00", "AUC 0.517；跨属 0.027；纳入后性能下降"],
   ["丁酸（正向项）", "隐含", "不计", "AUC 0.540 且方向相反"],
   ["惩罚：芽孢/口腔来源", "—", "−0.05 / −0.10", "均为肥胖富集倾向"]],
  [2400, 1200, 1200, 4270]));
C.push(cap("表 9　组合评分权重的调整及其依据"));
C.push(body(`重新加权后，**首选组合为人肠巴恩斯氏菌（Barnesiella intestinihominis）、内脏臭杆菌（Odoribacter splanchnicus）与腐败另枝菌（Alistipes putredinis）**（综合分 ${V2.top1.composite_v2.toFixed(4)}），三者恰为候选池中多样性关联最高的前三名（ρ 分别为 +0.36、+0.35、+0.33）。若需覆盖全部三条机制轴，可采用第 4 位的五株方案（增加解纤维素拟杆菌与产丁酸肠单胞菌）。`));
C.push(table(["排名", "组合成员", "株数", "机制轴", "多样性ρ均值", "综合分"],
  comb.slice(0, 6).map(r => [r.rank, r.members.split("; ").map(cn).join(" + "), r.n_strains,
    `${r.n_axes}/3`, (+r.diversity_mean).toFixed(2), (+r.composite_v2).toFixed(4)]),
  [600, 4600, 620, 800, 1300, 1150]));
C.push(cap("表 10　版本 2 重新加权后的前 6 位组合"));
C.push(body("**敏感性分析**：将纳入标准放宽为仅要求 FDR<0.05（不强制 meta 95%CI 排除 0），候选池由 16 株扩至 20 株（含嗜黏蛋白阿克曼氏菌），组合数由 6 519 增至 20 196。结果显示**首选组合完全不变**（同为上述三株，综合分 0.7631），表明结论对纳入标准稳健。嗜黏蛋白阿克曼氏菌所在的最佳组合位列第 9（综合分 0.7471，与首位差 0.016），其未能进入前列的原因是多样性关联较低（ρ=+0.23）而非被排除；考虑到该菌文献证据充分且已商业化，可将其作为第四或第五成员的备选方案。"));
C.push(...figure("fig22_combination_v2.png", "图 6　组合定标的重新加权：(A) 权重调整对比；(B) 版本 2 候选池；(C) 前 8 位组合；(D) 首选组合的变化", 0.593));
C.push(new Paragraph({ children: [new PageBreak()] }));

// ============ 4 讨论 ============
C.push(h1("4　讨论"));
C.push(body("本研究的首要发现是：**在严格控制年龄、性别、批次与代谢疾病之后，肠道菌群与肥胖的关联依然稳健存在**。这一点的确立并不平凡——在未匹配的原始数据中，仅年龄与性别即可达到 AUC 0.722，高于菌群本身，说明文献中相当一部分“肥胖菌群特征”可能包含了未被识别的人口学成分。本研究通过研究内匹配使该对照模型降至 0.527，从而将菌群信号与混杂彻底分离。"));
C.push(body("第二项发现涉及机制推断的方法学。既有的菌株筛选实践广泛采用“功能属”先验，即认定丁酸产生菌或含 BSH 的菌具有代谢获益。本研究以数据检验了这一假设，结果并不支持：**丁酸潜能的判别力仅 0.540 且方向相反**，同属的 Butyrivibrio crossotus 与 Roseburia intestinalis 在胖瘦方向上截然相反；**BSH 更是完全无预测力**（0.517），其跨属表现甚至系统性反向。二者共同说明，**属级功能注释不足以支撑菌株层面的机制推断**，正确的做法是下沉到种或菌株级证据。"));
C.push(body("第三项发现具有直接的应用价值：**与群落多样性的关联是判别瘦人相关菌的最强指标，且是唯一能跨类群泛化者**。其生物学意涵在于区分两种生态策略——协作型菌与多样群落共存，垄断型菌在失衡群落中占位扩张。由于该指标可对任何在公开队列中出现的物种直接计算，无需基因组注释或临床试验，因而可作为新候选菌株的快速初筛工具。需要强调的是，该指标反映的是生态兼容性而非因果效力，其高判别力不等同于补充该菌即可致减脂。"));
C.push(body("在应用层面，本研究据实测结果重构了组合定标：移除 BSH 权重、提升多样性关联与实测效应权重后，首选组合发生实质变化，且该结论在放宽纳入标准的敏感性分析中保持不变。这体现了一种可推广的工作方式——**以验证结果而非机制直觉决定权重**。"));

// ============ 5 结论 ============
C.push(h1("5　结论"));
[`在 ${S.eligible_studies} 项西欧研究、${S.n_lean_total + S.n_obese_total} 例无代谢疾病受试者中，经研究内年龄性别 1:1 匹配与回归双重校正后，肠道菌群仍能跨研究区分胖瘦（留一研究 AUC ${S.ai_matched_loso_auc}），而人口学信息已完全失效（${S.ai_demographics_only_auc}）。`,
 `共鉴定 ${S.n_robust} 个稳健差异物种；产甲烷古菌 Methanobrevibacter smithii 为最稳健瘦人标志，Ruminococcus gnavus 在肥胖者中丰度翻倍。`,
 "丁酸产生菌存在种间方向分化，菌株筛选必须采用种级而非属级分辨率。",
 `与群落多样性的关联是判别力最高（AUC 0.920）且唯一可跨属泛化（留一属 ${MC["仅多样性关联"]}）的特征，建议作为新菌株的首选初筛指标。`,
 `胆盐水解酶（BSH）对减脂无预测能力（AUC 0.517），跨属系统性反向，且纳入后损害模型性能；现有 16% 的“降胆固醇”权重缺乏数据支持，应予移除。`,
 `据验证结果重新加权后，首选组合为人肠巴恩斯氏菌、内脏臭杆菌与腐败另枝菌，并在放宽纳入标准的敏感性分析中保持不变。`,
].forEach(t => C.push(new Paragraph({ numbering: { reference: "concl", level: 0 },
  spacing: { line: 330, after: 60 }, children: [new TextRun({ text: t, font: SERIF, size: 21 })] })));

// ============ 6 局限 ============
C.push(h1("6　局限性"));
["本研究为横断面关联分析，不能推断因果；补充上述菌株能否致减脂，须经干预试验验证。",
 "1:1 匹配使样本量由 2 008 降至 904，统计效能下降、置信区间变宽，且年龄极端的个体被舍弃。",
 "饮食结构、用药（尤其抗生素）、体力活动等潜在混杂因素在原始数据中缺失，无法纳入校正。",
 "队列设计异质：丹麦 MetaHIT 系列为极端表型招募，判别效力偏高；人群队列的估计更为保守。",
 "机制特征评估中显著物种仅 41 个（其中肥胖富集 7 个），类别不平衡，低 AUC 的估计不稳定；丙酸 10/10 的完美关联基于 n=10，需更大样本复核。",
 "功能潜能为属级知识先验而非菌株级基因组实测，可能低估菌株间差异。",
 "“与已确认瘦人菌的共现亲和度”含部分定义性循环，已在文中标注并排除于结论之外。",
 "结论限于西欧人群；前期分层分析显示部分物种（如 Roseburia intestinalis）在东亚人群中方向相反。",
 "组合评分权重虽有验证依据，仍为专家设定而非由结局数据拟合；组合结果为候选定标，非疗效预测。",
].forEach(t => C.push(new Paragraph({ numbering: { reference: "lim", level: 0 },
  spacing: { line: 330, after: 60 }, children: [new TextRun({ text: t, font: SERIF, size: 21 })] })));

// ============ 7 数据可用性 ============
C.push(h1("7　数据与代码可用性"));
C.push(body("**分析脚本**：we_healthy_full_analysis.py（队列构建、匹配、差异分析、meta 分析与机器学习验证）、bottomup_vs_screened_validation.py（程序对比验证）、lean_associated_factors_discovery.py（机制特征筛选）、bile_acid_prediction_assessment.py（胆汁酸评估）、synergistic_lean_combinations_v2.py（组合重新加权，支持 robust/relaxed 两种纳入模式）。", { noIndent: true }));
C.push(body("**结果数据**：results/prediction_results/we_healthy/（队列来源、匹配队列、完整差异分析、分析摘要）、bottomup_validation/、lean_factors/、bile_acid/，以及 results/combination_recommendations/（候选池、组合评分、敏感性分析）。", { noIndent: true }));
C.push(body("**配套数据表**：西欧队列与机制分析_完整数据_20260625.xlsx，含全部原始统计结果与方法参数。", { noIndent: true }));

const doc = new Document({
  styles: { default: { document: { run: { font: SERIF, size: 21 } } },
    paragraphStyles: [
      { id: "Heading1", name: "Heading 1", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { size: 28, bold: true, font: HEI }, paragraph: { spacing: { before: 300, after: 140 }, outlineLevel: 0 } },
      { id: "Heading2", name: "Heading 2", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { size: 23, bold: true, font: HEI }, paragraph: { spacing: { before: 190, after: 100 }, outlineLevel: 1 } },
      { id: "Heading3", name: "Heading 3", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { size: 21, bold: true, font: HEI }, paragraph: { spacing: { before: 150, after: 80 }, outlineLevel: 2 } }] },
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
