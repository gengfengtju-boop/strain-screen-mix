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

// 结论
C.push(h1("3  结论"));
[`在 ${S.eligible_studies} 项西欧研究、${S.n_lean_total + S.n_obese_total} 例无疾病受试者中，经研究内年龄性别 1:1 匹配与回归双重校正后，肠道菌群仍能跨研究区分胖瘦（留一研究 AUC ${S.ai_matched_loso_auc}），而人口学信息已完全失效（${S.ai_demographics_only_auc}）。菌群差异是独立于年龄性别的生物学信号。`,
 `共鉴定 ${S.n_robust} 个稳健差异物种。瘦人以产甲烷古菌与特定丁酸产生菌为特征；肥胖以 Ruminococcus gnavus 丰度翻倍为最强标志。`,
 "种级分辨率不可替代：同为丁酸产生菌，Butyrivibrio crossotus 与 Eubacterium eligens 富集于瘦人，而 Roseburia intestinalis 与 Eubacterium rectale 富集于肥胖，基于功能属的组合设计存在方向性风险。",
 "对菌株组合设计的直接输入：Butyrivibrio crossotus 在本严格分析中获得独立验证；建议将 Eubacterium eligens、Intestinimonas butyriciproducens 与 Methanobrevibacter smithii 纳入候选池，并排除 Roseburia intestinalis 与 Eubacterium rectale。",
 "Ruminococcus gnavus 丰度下降可作为西欧人群减脂干预的候选疗效生物标志物。",
].forEach(t=>C.push(new Paragraph({numbering:{reference:"concl",level:0}, spacing:{line:330,after:60},
  children:[new TextRun({text:t, font:SERIF, size:21})]})));

C.push(h1("4  局限性"));
["横断面关联而非因果：不能据此推断补充上述菌株可致减脂，需干预试验验证。",
 "匹配代价：1:1 匹配使样本量自 2 008 降至 904，统计效能下降、置信区间变宽，未匹配上的极端年龄样本被舍弃。",
 "残余混杂：饮食结构、用药（含抗生素）、体力活动等信息缺失，无法纳入校正。",
 "队列设计异质：丹麦 MetaHIT 系列为极端表型设计，判别效力偏高；人群队列估计更为保守。",
 "地域局限：结论限于西欧人群，前期分层分析显示部分菌种（如 Roseburia intestinalis）在东亚人群中方向相反。",
].forEach(t=>C.push(new Paragraph({numbering:{reference:"lim",level:0}, spacing:{line:330,after:60},
  children:[new TextRun({text:t, font:SERIF, size:21})]})));

C.push(h1("5  数据与代码可用性"));
C.push(body("分析脚本：scripts/obesity_model/we_healthy_full_analysis.py；结果数据：results/prediction_results/we_healthy/（含队列来源表 cohort_sources.csv、匹配队列 matched_cohort.csv、完整差异分析表 differential_abundance_adjusted.csv、分析摘要 analysis_summary.json）；配套 Excel 汇总见 西欧健康队列_完整数据_20260625.xlsx。", {noIndent:true}));

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
