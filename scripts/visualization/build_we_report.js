const fs = require("fs");
const path = require("path");
const { Document, Packer, Paragraph, TextRun, Table, TableRow, TableCell,
        AlignmentType, LevelFormat, HeadingLevel, BorderStyle, WidthType,
        ShadingType, ImageRun, PageNumber, Footer } = require("docx");

const ROOT = "D:/strain screen mix";
const PR = path.join(ROOT, "results/prediction_results/we_healthy");
const OUT = path.join(ROOT, "docs/西欧健康队列_胖瘦差异菌分析报告_20260625.docx");
const SERIF = "SimSun", HEI = "SimHei";
const A4W = 11906, A4H = 16838, MARGIN = 1440, CONTENT = A4W - 2 * MARGIN;

const S = JSON.parse(fs.readFileSync(path.join(PR, "analysis_summary.json"), "utf8"));
function csv(f) {
  const t = fs.readFileSync(path.join(PR, f), "utf8").replace(/^\uFEFF/, "").trim().split(/\r?\n/);
  const h = t[0].split(",");
  return t.slice(1).map(l => {
    const v = l.split(","); const o = {};
    h.forEach((k, i) => o[k] = v[i]); return o;
  });
}
const cohort = csv("cohort_sources.csv");
const da = csv("differential_abundance_adjusted.csv");
const num = (x) => parseFloat(x);
const robust = da.filter(r => String(r.robust).toLowerCase() === "true");
const lean = robust.filter(r => r.direction === "lean_enriched").sort((a,b)=>num(b.meta_g)-num(a.meta_g));
const obese = robust.filter(r => r.direction === "obese_enriched").sort((a,b)=>num(a.meta_g)-num(b.meta_g));

function runs(t, f, s) {
  return t.split(/(\*\*[^*]+\*\*)/g).filter(Boolean).map(p => p.startsWith("**")
    ? new TextRun({ text: p.slice(2,-2), bold: true, font: f, size: s })
    : new TextRun({ text: p, font: f, size: s }));
}
const body = (t, o={}) => new Paragraph({ spacing:{line:340, after:110}, alignment:AlignmentType.JUSTIFIED,
  indent: o.noIndent?undefined:{firstLine:440}, children: runs(t, SERIF, 21) });
const h1 = (t) => new Paragraph({ heading:HeadingLevel.HEADING_1, spacing:{before:300,after:150},
  children:[new TextRun({text:t, font:HEI, size:29, bold:true})] });
const h2 = (t) => new Paragraph({ heading:HeadingLevel.HEADING_2, spacing:{before:200,after:110},
  children:[new TextRun({text:t, font:HEI, size:24, bold:true})] });
const cb = {style:BorderStyle.SINGLE, size:1, color:"BBBBBB"};
const bd = {top:cb,bottom:cb,left:cb,right:cb};
const cell = (t,w,head,ac) => new TableCell({ borders:bd, width:{size:w,type:WidthType.DXA},
  shading:{fill:head?"D9E2F0":"FFFFFF", type:ShadingType.CLEAR},
  margins:{top:50,bottom:50,left:80,right:80},
  children:[new Paragraph({alignment:ac?AlignmentType.CENTER:AlignmentType.LEFT,
    children:[new TextRun({text:String(t), font:SERIF, size:16, bold:head})]})]});
function table(hd, rows, w) {
  const mk=(c,h)=>new TableRow({tableHeader:h, children:c.map((x,i)=>cell(x,w[i],h,i>0))});
  return new Table({width:{size:CONTENT,type:WidthType.DXA}, columnWidths:w,
    rows:[mk(hd,true), ...rows.map(r=>mk(r,false))]});
}
const cap = (t) => new Paragraph({alignment:AlignmentType.CENTER, spacing:{before:70,after:180},
  children:[new TextRun({text:t, font:HEI, size:17, bold:true})]});
function figure(name, capt, ratio, w=580) {
  return [new Paragraph({alignment:AlignmentType.CENTER, spacing:{before:150,after:50},
    children:[new ImageRun({type:"png", data:fs.readFileSync(path.join(ROOT,"results/paper_figures",name)),
      transformation:{width:w, height:Math.round(w*ratio)},
      altText:{title:capt, description:capt, name:name}})]}),
    new Paragraph({alignment:AlignmentType.CENTER, spacing:{after:190},
      children:[new TextRun({text:capt, font:HEI, size:18, bold:true})]})];
}

const C = [];
C.push(new Paragraph({alignment:AlignmentType.CENTER, spacing:{before:520,after:110},
  children:[new TextRun({text:"西欧健康人群肠道菌群胖瘦差异分析", font:HEI, size:38, bold:true})]}));
C.push(new Paragraph({alignment:AlignmentType.CENTER, spacing:{after:70},
  children:[new TextRun({text:"排除 2 型糖尿病 · 研究内年龄性别匹配 · 随机效应 meta 验证", font:HEI, size:24, bold:true})]}));
C.push(new Paragraph({alignment:AlignmentType.CENTER, spacing:{after:320},
  children:[new TextRun({text:"ProSlim-Microbiome-AI 项目组　2026 年 6 月 25 日", font:SERIF, size:20})]}));

// 摘要
C.push(new Paragraph({spacing:{after:90}, children:[new TextRun({text:"摘要", font:HEI, size:23, bold:true})]}));
C.push(body(`**目的：**明确西欧无疾病人群中，肥胖相关的肠道菌群差异是否独立于年龄与性别混杂。**方法：**自 8 304 例公开宏基因组样本逐级筛选，排除 2 型糖尿病、糖耐量异常与高血压，最终纳入 ${S.eligible_studies} 项鸟枪法测序研究（${S.countries.join("/")}），共 ${S.n_lean_total} 例瘦人与 ${S.n_obese_total} 例肥胖者。采用研究内 1:1 年龄（±5 岁）性别匹配（n=${S.matched.n}）并在回归中再次校正，对 ${S.n_species_tested} 个物种行 OLS 差异分析（BH-FDR），以随机效应 meta 分析交叉验证，并用随机森林留一研究交叉验证。**结果：**匹配后仅年龄性别模型 AUC 降至 ${S.ai_demographics_only_auc}（≈随机），而菌群模型仍达 ${S.ai_matched_loso_auc}。共 ${S.n_fdr_significant} 个物种 FDR<0.05，其中 ${S.n_robust} 个通过 meta 验证。产甲烷古菌 Methanobrevibacter smithii 为最稳健瘦人标志（I²=0%），Ruminococcus gnavus 在肥胖者中丰度翻倍（2.05 倍）。丁酸产生菌呈现种间分化：Butyrivibrio crossotus 与 Eubacterium eligens 富集于瘦人，而 Roseburia intestinalis 与 Eubacterium rectale 富集于肥胖。**结论：**严格校正后菌群差异为独立生物学信号；菌株组合设计必须采用种级而非属级分辨率。`, {noIndent:true}));
C.push(new Paragraph({spacing:{before:110,after:200}, children:[
  new TextRun({text:"关键词：", font:HEI, size:19, bold:true}),
  new TextRun({text:"肠道菌群；肥胖；西欧队列；倾向匹配；随机效应 meta 分析；机器学习", font:SERIF, size:19})]}));

// 方法
C.push(h1("1  方法"));
C.push(h2("1.1  队列构建与纳入排除"));
C.push(body("自公开宏基因组队列体系出发，逐级应用纳入排除标准（表 1）。**关键排除**：所有 2 型糖尿病（T2D）、糖耐量异常（IGT）与高血压受试者，以确保观察到的差异归因于肥胖本身而非代谢疾病。"));
C.push(table(["筛选步骤","剩余样本量"], S.cohort_filter_steps.map(s=>[s.step, s.n]), [6026, 3000]));
C.push(cap("表 1  队列筛选流程"));
C.push(body("**纳入标准**：① 西欧国家；② 无疾病（disease_status = healthy）；③ 明确的瘦或肥胖表型（排除超重中间态）；④ 年龄与性别记录完整；⑤ 该研究内两组各不少于 10 例。"));

C.push(h2("1.2  合格数据队列来源"));
C.push(body(`最终纳入 **${S.eligible_studies} 项独立研究**，覆盖 **${S.countries.length} 个国家（${S.countries.join("/")}）**，全部为鸟枪法宏基因组测序（表 2）。原始队列中肥胖组年龄普遍高于瘦人组，故年龄校正为必需。`));
C.push(table(["研究队列","国家","瘦(n)","肥胖(n)","年龄瘦/胖","女性比瘦/胖","BMI瘦/胖"],
  cohort.map(r=>[r.study_id, r.country, r.n_lean, r.n_obese,
    `${r.age_lean}/${r.age_obese}`, `${r.female_lean}/${r.female_obese}`, `${r.bmi_lean}/${r.bmi_obese}`])
    .concat([["合计","—",String(S.n_lean_total),String(S.n_obese_total),"—","—","—"]]),
  [2100,700,700,760,1400,1500,1866]));
C.push(cap("表 2  合格数据队列来源与人口学特征"));

C.push(h2("1.3  年龄性别校正（双重独立处理）"));
C.push(body(`**（1）研究内 1:1 匹配。**对每例肥胖受试者，在**同一研究内**匹配同性别、年龄差不超过 5 岁的瘦人（最近邻，无放回抽样）。匹配后样本量 **n=${S.matched.n}（瘦 ${S.matched.lean} / 肥胖 ${S.matched.obese}）**，两组平均年龄 **${S.matched.age_lean} 岁与 ${S.matched.age_obese} 岁**，女性比例均为 **${S.matched.female_lean}**，达到完全平衡。研究内匹配的额外优势在于同时消除测序中心与批次效应。`));
C.push(body("**（2）回归协变量校正。**差异分析模型中再次纳入年龄、性别与研究固定效应，形成双重保障。"));

C.push(h2("1.4  差异丰度统计"));
C.push(body(`物种筛选：匹配队列内流行率不低于 10%，共 **${S.n_species_tested} 个物种**进入检验。主模型为 OLS 回归：log10(相对丰度 + 0.001) ~ 肥胖 + 年龄 + 性别 + 研究，提取肥胖项系数与 P 值，行 **Benjamini-Hochberg FDR** 多重检验校正。`));
C.push(body("稳健性交叉验证：在各研究内独立计算 **Hedges g**（含小样本偏倚校正因子），再以 **DerSimonian-Laird 随机效应模型**合并，报告 95% 置信区间与异质性指标 I²。**稳健差异菌**须同时满足三项条件：FDR<0.05；meta 合并 95%CI 排除 0；两种方法方向一致。"));

C.push(h2("1.5  AI 验证"));
C.push(body("在匹配队列上训练平衡随机森林（500 树，最大深度 6，最小叶节点 3），采用**留一研究交叉验证**——每次留出一整项研究作为独立测试集，从设计上杜绝批次泄漏。同时以仅年龄与性别为特征训练对照模型，用以检验人口学混杂是否已被彻底消除。"));

// 结果
C.push(h1("2  结果"));
C.push(...figure("fig17_we_healthy_full.png", "图 1  西欧健康队列胖瘦差异菌群总览：(A) 校正后差异丰度火山图；(B) AI 留一研究验证；(C) 稳健瘦人富集菌森林图；(D) 稳健肥胖富集菌森林图", 0.693));

C.push(h2("2.1  混杂消除的关键验证"));
C.push(body(`匹配前，仅使用年龄与性别即可达到 AUC 0.722，高于菌群单独模型；**匹配后，人口学模型 AUC 降至 ${S.ai_demographics_only_auc}，接近随机水平，而菌群模型仍达 ${S.ai_matched_loso_auc}**（表 3、图 1B）。这一对照证明：观察到的菌群差异并非年龄或性别的副产品，而是独立的生物学信号。`));
C.push(table(["模型","留一研究 AUC","解读"],
  [["仅年龄 + 性别", String(S.ai_demographics_only_auc), "接近随机，混杂已消除"],
   ["菌群（199 物种）", String(S.ai_matched_loso_auc), "跨研究可泛化的独立信号"]],
  [2600, 2200, 4226]));
C.push(cap("表 3  匹配队列上的 AI 判别效力对照"));
C.push(body("各研究留出表现存在系统性差异：丹麦三项研究（LeChatelierE、HansenLBS、NielsenHB，源自 MetaHIT 计划）AUC 达 0.89–1.00，而人群队列（AsnicarF 0.67、LifeLinesDeep 0.66、XieH 0.65）明显较低。前者以“胖瘦对比”为设计目标、招募极端表型，故可分性偏高；**人群队列的估计更接近真实世界效力**。KeohaneDM 匹配后样本极少，其 AUC 0.48 不具解释力。"));

C.push(h2("2.2  差异菌群"));
C.push(body(`在 ${S.n_species_tested} 个受检物种中，**${S.n_fdr_significant} 个**达到 FDR<0.05；其中 **${S.n_robust} 个**同时通过随机效应 meta 验证，判定为稳健差异菌（表 4、表 5）。`));
C.push(table(["物种","合并 g","95% CI","倍数变化(胖/瘦)","FDR","I²"],
  lean.slice(0,12).map(r=>[r.species.replace(/_/g," "), (+r.meta_g).toFixed(2),
    `${(+r.ci_low).toFixed(2)} ~ ${(+r.ci_high).toFixed(2)}`, (+r.fold_change_obese_vs_lean).toFixed(2),
    (+r.fdr).toExponential(1), `${Math.round(+r.I2_percent)}%`]),
  [3000,900,1600,1500,1100,926]));
C.push(cap("表 4  稳健瘦人富集菌（按合并效应量排序，前 12）"));
C.push(table(["物种","合并 g","95% CI","倍数变化(胖/瘦)","FDR","I²"],
  obese.slice(0,10).map(r=>[r.species.replace(/_/g," "), (+r.meta_g).toFixed(2),
    `${(+r.ci_low).toFixed(2)} ~ ${(+r.ci_high).toFixed(2)}`, (+r.fold_change_obese_vs_lean).toFixed(2),
    (+r.fdr).toExponential(1), `${Math.round(+r.I2_percent)}%`]),
  [3000,900,1600,1500,1100,926]));
C.push(cap("表 5  稳健肥胖富集菌（全部）"));

C.push(h2("2.3  生物学发现"));
C.push(body("**（1）产甲烷古菌为最稳健瘦人标志。** Methanobrevibacter smithii 合并效应量 +0.37，异质性 I²=0%，肥胖者丰度仅为瘦人的 0.29 倍（FDR=3.4×10⁻⁶），各研究结论高度一致。"));
C.push(body("**（2）多个丁酸产生菌为瘦人富集且异质性为零。** 包括 Butyrivibrio crossotus（0.44 倍，I²=0%）、Eubacterium eligens（0.49 倍，I²=0%）、Intestinimonas butyriciproducens 及 Roseburia 属 CAG_303/309 分支。"));
C.push(body("**（3）反直觉发现：丁酸产生菌存在种间方向分化。** Roseburia intestinalis（1.74 倍）与 Eubacterium rectale（1.81 倍）虽同属经典丁酸产生菌，却在肥胖者中显著富集。这表明“丁酸产生菌等同于瘦表型”的属级叙事过于简化，**菌株组合设计必须下沉到种级分辨率**，否则存在方向性风险。"));
C.push(body("**（4）Ruminococcus gnavus 在肥胖者中丰度翻倍**（2.05 倍，FDR=1.1×10⁻⁴），为最强肥胖标志。该菌是已知的黏液降解与促炎菌，与肥胖低度炎症机制相吻合。"));
C.push(body("**（5）口腔菌易位信号在严格校正后大幅减弱。** 仅 Streptococcus vestibularis 保留统计显著（1.35 倍）。此前在未排除 T2D、未做匹配的分析中观察到的强口腔链球菌信号，主要由疾病状态与人口学差异驱动，本研究予以修正。"));

// ===== 新增：自下而上程序验证 =====
const V = JSON.parse(fs.readFileSync(path.join(ROOT,"results/prediction_results/bottomup_validation/validation_summary.json"),"utf8"));
const BIO = JSON.parse(fs.readFileSync(path.join(ROOT,"results/prediction_results/bottomup_validation/bio_only_features.json"),"utf8"));
const LF = JSON.parse(fs.readFileSync(path.join(ROOT,"results/prediction_results/lean_factors/summary.json"),"utf8"));
const MC = JSON.parse(fs.readFileSync(path.join(ROOT,"results/prediction_results/lean_factors/model_comparison.json"),"utf8"));

C.push(h1("3  自下而上菌株性质程序的对比验证"));
C.push(h2("3.1  验证对象与设计"));
C.push(body("项目内已有一套自下而上程序（build_strain_screening_catalog.py），由菌株性质推测减脂效果：以肥胖分类器 SHAP 信号方向、基因组功能潜能（BSH、丁酸、黏液）与安全分层为输入，对 223 株给出“保护”或“促肥胖”标签。该程序的 SHAP 信号来自全部 8 304 样本的**未校正模型**（未排除 T2D、未校正年龄性别）。本节以第 2 节的严格筛选结果为金标准，检验二者是否匹配。"));
C.push(...figure("fig18_bottomup_validation.png", "图 2  自下而上程序与严格筛选结果的对比验证：(A) 混淆矩阵；(B) 一致性随证据强度变化；(C) 各特征判别力；(D) 丙酸与丁酸对比", 0.717));

C.push(h2("3.2  一致性结果"));
C.push(body("一致性随证据强度显著提升：在全部受检物种上仅 61.6%（κ=0.21，接近随机），而在统计稳健的 37 个差异菌上达到 **81.1%（κ=0.516，中等一致）**（表 6）。"));
C.push(table(["比对范围","物种数","一致率","Cohen's κ","判定"],
  [["全部受检物种", String(V.concordance["全部受检物种"].n), (V.concordance["全部受检物种"].一致率*100).toFixed(1)+"%", String(V.concordance["全部受检物种"].kappa),"弱一致（接近随机）"],
   ["FDR<0.05 显著", String(V.concordance["FDR<0.05 显著"].n), (V.concordance["FDR<0.05 显著"].一致率*100).toFixed(1)+"%", String(V.concordance["FDR<0.05 显著"].kappa),"中等一致"],
   ["稳健差异菌", String(V.concordance["稳健差异菌"].n), (V.concordance["稳健差异菌"].一致率*100).toFixed(1)+"%", String(V.concordance["稳健差异菌"].kappa),"中等一致"]],
  [2200,900,1000,1000,3926]));
C.push(cap("表 6  自下而上程序与严格筛选结果的一致性"));
C.push(body("**程序可靠性高度不对称**：当程序预测某菌为“保护/瘦人富集”时，精确率高达 **24/25 = 96%**，高度可信；但当其预测“促肥胖”时，精确率仅 **6/12 = 50%**，等同随机，不可用于排除菌株。"));
C.push(body("**一个高后果误判**：Ruminococcus gnavus 被程序判为“保护”，实测却是最强肥胖标志（肥胖者丰度翻倍 2.05 倍）。该菌为已知黏液降解促炎菌——若仅依据该程序选菌，会将促炎菌纳入减脂配方。其余 6 例误判均为 SHAP 重要性极低（0.002–0.015）的未培养 CAG 类群。"));

C.push(h1("4  减脂相关特征的进一步筛选"));
C.push(h2("4.1  功能潜能：丙酸有效，丁酸无效"));
C.push(body(`在剔除源自模型自身的循环特征后，对独立生物学特征逐一检验（图 2C、2D）。**丙酸产生潜能是唯一有效的功能特征**：10 个具丙酸潜能的显著物种**全部**为瘦人富集（${(BIO.propionate_pos_lean_rate*100).toFixed(0)}%），高于无丙酸潜能者的 ${(BIO.propionate_neg_lean_rate*100).toFixed(0)}%。**丁酸潜能则无效甚至方向相反**：具丁酸潜能者瘦人富集率 ${(BIO.butyrate_pos_lean_rate*100).toFixed(0)}%，反而低于无丁酸潜能者的 ${(BIO.butyrate_neg_lean_rate*100).toFixed(0)}%（总体基线 83%）。这与第 2.3 节的发现完全吻合。`));
C.push(body(`**诚实的负结果**：仅使用属级功能特征时，留一属交叉验证 AUC 为 ${BIO.bio_only_loso_genus_auc_logreg}（逻辑回归）与 ${BIO.bio_only_loso_genus_auc_rf}（随机森林），均不优于随机。原因在于功能潜能按属赋值、与分类学完全共线，留一属验证恰好剔除了该信息。这说明属级功能先验不足以支撑新菌株的减脂预测，必须下沉到菌株级基因组注释。`));

C.push(h2("4.2  超越丙酸：其它与瘦人菌株相关的因素"));
C.push(body("为寻找功能潜能之外的判别因素，进一步构建两类非循环特征：**生态学特征**（流行率、平均丰度、与菌群多样性的关联、共现网络中心度、与已确认瘦人菌的共现亲和度）与**知识型特征**（口腔来源、严格厌氧、芽孢形成、纤维降解能力），在 41 个显著物种上检验（图 3）。"));
C.push(...figure("fig19_lean_factors.png", "图 3  超越丙酸的减脂相关因素筛选：(A) 各因素判别力；(B) 跨属泛化能力比较；(C) 多样性关联的组间分布；(D) 知识型性质对比", 0.647));
C.push(table(["因素","AUC","方向","瘦人富集菌均值","肥胖富集菌均值","显著性"],
  LF.single_features.slice(0,6).map(r=>{
    const cn={lean_marker_affinity:"与已确认瘦人菌共现亲和度",diversity_association:"与菌群多样性的关联",
      spore_former:"芽孢形成能力",oral_origin:"口腔来源菌",strict_anaerobe:"严格厌氧",
      fiber_degrader:"纤维降解能力",prevalence:"流行率",cooccurrence_degree:"共现网络中心度",
      mean_log_abundance:"平均丰度水平"};
    const p=r.p_mannwhitney;
    return [cn[r.feature]||r.feature, String(r.auc), r.direction, String(r.lean_mean), String(r.obese_mean),
            p<0.001?"P<0.001":(p<0.05?`P=${p.toFixed(3)}`:"不显著")];
  }), [2500,800,1000,1600,1600,1526]));
C.push(cap("表 7  与瘦人菌株相关的候选因素（按判别力排序，前 6）"));
C.push(body(`**核心发现：与菌群多样性的关联是最强的独立判别因素。** 该特征在各组内部单独计算（而非直接比较胖瘦两组），故不构成循环论证。瘦人富集菌的多样性关联均值为 +0.193，而肥胖富集菌仅 +0.025（P<0.001，AUC 0.920，图 3C）。生物学含义为：**瘦人相关菌能与高多样性群落共存，而肥胖相关菌更适应低多样性的失衡群落**。`));
C.push(body(`**跨属泛化能力对比（图 3B）**：仅用多样性关联，留一属交叉验证 AUC 达 **${MC["仅多样性关联"]}**；与丙酸潜能联合可达 **${MC["多样性关联+丙酸"]}**；而仅用丙酸潜能仅 ${MC["仅丙酸"]}、仅用知识型特征仅 ${MC["仅知识特征(口腔/需氧/芽孢/纤维)"]}。**多样性关联不仅判别力最强，且是唯一能跨属泛化的特征**，因而可直接用于筛查目录之外的新候选菌株。`));
C.push(body("**次要因素**：肥胖富集菌中芽孢形成菌比例显著更高（71% 对 32%），口腔来源菌亦更多（14% 对 0%）；而流行率、平均丰度与共现网络中心度均无判别力（AUC≈0.50–0.52），说明“常见”或“高丰度”并不等同于“有益”。"));

// 结论
C.push(h1("5  结论"));
[`在 ${S.eligible_studies} 项西欧研究、${S.n_lean_total + S.n_obese_total} 例无疾病受试者中，经研究内年龄性别 1:1 匹配与回归双重校正后，肠道菌群仍能跨研究区分胖瘦（留一研究 AUC ${S.ai_matched_loso_auc}），而人口学信息已完全失效（${S.ai_demographics_only_auc}）。菌群差异是独立于年龄性别的生物学信号。`,
 `共鉴定 ${S.n_robust} 个稳健差异物种。瘦人以产甲烷古菌与特定丁酸产生菌为特征；肥胖以 Ruminococcus gnavus 丰度翻倍为最强标志。`,
 "种级分辨率不可替代：同为丁酸产生菌，Butyrivibrio crossotus 与 Eubacterium eligens 富集于瘦人，而 Roseburia intestinalis 与 Eubacterium rectale 富集于肥胖，基于功能属的组合设计存在方向性风险。",
 "对菌株组合设计的直接输入：Butyrivibrio crossotus 在本严格分析中获得独立验证；建议将 Eubacterium eligens、Intestinimonas butyriciproducens 与 Methanobrevibacter smithii 纳入候选池，并排除 Roseburia intestinalis 与 Eubacterium rectale。",
 "Ruminococcus gnavus 丰度下降可作为西欧人群减脂干预的候选疗效生物标志物。",
 `自下而上菌株性质程序与本严格筛选中等一致（81.1%，κ=0.52），但可靠性不对称：预测“保护”时精确率 96% 可直接用于初筛，预测“促肥胖”时仅 50% 不可用于排除；且曾将促炎菌 Ruminococcus gnavus 误判为保护菌，必须以实测差异丰度复核。`,
 `功能潜能层面，丙酸产生能力是唯一有效特征（10/10 全部瘦人富集），丁酸产生能力无效且方向相反，应停止将“丁酸产生菌”作为减脂筛选标准。`,
 `与菌群多样性的关联是判别力最强（AUC 0.920）且唯一能跨属泛化（留一属 AUC ${MC["仅多样性关联"]}）的因素，与丙酸联合可达 ${MC["多样性关联+丙酸"]}，建议作为新菌株的首选筛查指标；肥胖富集菌则更多为芽孢形成菌与口腔来源菌。`,
].forEach(t=>C.push(new Paragraph({numbering:{reference:"concl",level:0}, spacing:{line:330,after:60},
  children:[new TextRun({text:t, font:SERIF, size:21})]})));

C.push(h1("6  局限性"));
["横断面关联而非因果：不能据此推断补充上述菌株可致减脂，需干预试验验证。",
 "匹配代价：1:1 匹配使样本量自 2 008 降至 904，统计效能下降、置信区间变宽，未匹配上的极端年龄样本被舍弃。",
 "残余混杂：饮食结构、用药（含抗生素）、体力活动等信息缺失，无法纳入校正。",
 "队列设计异质：丹麦 MetaHIT 系列为极端表型设计，判别效力偏高；人群队列估计更为保守。",
 "地域局限：结论限于西欧人群，前期分层分析显示部分菌种（如 Roseburia intestinalis）在东亚人群中方向相反。",
 "特征筛选样本有限：41 个显著物种中仅 7 个肥胖富集，类别不平衡，判别力估计不稳；丙酸 10/10 的完美关联基于 n=10，需更大样本复核。",
 "与已确认瘦人菌的共现亲和度（AUC 0.96）含部分定义性循环，已在解读中标注，不作为独立结论；多样性关联虽在组内计算，仍属关联证据。",
].forEach(t=>C.push(new Paragraph({numbering:{reference:"lim",level:0}, spacing:{line:330,after:60},
  children:[new TextRun({text:t, font:SERIF, size:21})]})));

C.push(h1("7  数据与代码可用性"));
C.push(body("分析脚本：scripts/obesity_model/we_healthy_full_analysis.py（主分析）、bottomup_vs_screened_validation.py（程序验证）、lean_associated_factors_discovery.py（因素筛选）；结果数据：results/prediction_results/we_healthy/（含队列来源表 cohort_sources.csv、匹配队列 matched_cohort.csv、完整差异分析表 differential_abundance_adjusted.csv、分析摘要 analysis_summary.json）；程序验证与因素筛选结果见 results/prediction_results/bottomup_validation/ 与 lean_factors/；配套 Excel 汇总见 西欧健康队列_完整数据_20260625.xlsx。", {noIndent:true}));

const doc = new Document({
  styles:{ default:{document:{run:{font:SERIF, size:21}}},
    paragraphStyles:[
      {id:"Heading1", name:"Heading 1", basedOn:"Normal", next:"Normal", quickFormat:true,
       run:{size:29,bold:true,font:HEI}, paragraph:{spacing:{before:300,after:150}, outlineLevel:0}},
      {id:"Heading2", name:"Heading 2", basedOn:"Normal", next:"Normal", quickFormat:true,
       run:{size:24,bold:true,font:HEI}, paragraph:{spacing:{before:200,after:110}, outlineLevel:1}}]},
  numbering:{config:[
    {reference:"concl", levels:[{level:0, format:LevelFormat.DECIMAL, text:"%1.", alignment:AlignmentType.LEFT,
      style:{paragraph:{indent:{left:560,hanging:340}}}}]},
    {reference:"lim", levels:[{level:0, format:LevelFormat.DECIMAL, text:"%1.", alignment:AlignmentType.LEFT,
      style:{paragraph:{indent:{left:560,hanging:340}}}}]}]},
  sections:[{ properties:{page:{size:{width:A4W,height:A4H}, margin:{top:MARGIN,right:MARGIN,bottom:MARGIN,left:MARGIN}}},
    footers:{default:new Footer({children:[new Paragraph({alignment:AlignmentType.CENTER,
      children:[new TextRun({text:"第 ", font:SERIF, size:18}),
                new TextRun({children:[PageNumber.CURRENT], font:SERIF, size:18}),
                new TextRun({text:" 页", font:SERIF, size:18})]})]})},
    children:C }]});
Packer.toBuffer(doc).then(b=>{fs.writeFileSync(OUT,b); console.log("wrote", OUT, b.length);});
