# 数据字典

## sample_metadata

| 字段 | 含义 |
| --- | --- |
| sample_id | 样本编号 |
| subject_id | 受试者编号 |
| study_id | 研究编号 |
| database_source | 数据库来源 |
| sequencing_type | 16S 或 shotgun |
| body_site | 样本来源，优先 feces |
| time_point | baseline / post / follow-up |
| age | 年龄 |
| sex | male / female / unknown |
| BMI | kg/m2 |
| obesity_status | lean / overweight / obesity |
| disease_status | healthy / obesity / T2D / NAFLD / metabolic syndrome |
| country | 国家 |
| region | 地区 |
| antibiotic_use | 是否近期使用抗生素 |
| diet_info_available | 是否有饮食信息 |
| intervention_available | 是否为干预研究样本 |

## taxonomic_profile

| 字段 | 含义 |
| --- | --- |
| sample_id | 样本编号 |
| taxon_level | genus / species |
| taxon_name | 菌属或菌种名称 |
| relative_abundance | 相对丰度 |
| database_source | 数据来源 |
| profiling_method | MetaPhlAn / QIIME2 / DADA2 / Kraken2 等 |

## functional_profile

| 字段 | 含义 |
| --- | --- |
| sample_id | 样本编号 |
| pathway_id | 通路编号 |
| pathway_name | 通路名称 |
| pathway_database | MetaCyc / KEGG / eggNOG |
| abundance | 通路丰度 |
| coverage | 通路覆盖度 |
| annotation_method | HUMAnN / MGnify / eggNOG-mapper |

## intervention_metadata

| 字段 | 含义 |
| --- | --- |
| study_id | 研究编号 |
| subject_id | 受试者编号 |
| intervention_type | probiotic / prebiotic / synbiotic / diet |
| probiotic_species | 益生菌种名 |
| probiotic_strain | 益生菌株号 |
| number_of_strains | 菌株数量 |
| total_CFU_per_day | 总活菌数 |
| log10_CFU_per_day | log10 转换剂量 |
| strain_specific_CFU | 单株剂量 |
| prebiotic_type | 益生元类型 |
| prebiotic_dose_g_day | 益生元剂量 |
| duration_weeks | 干预周期 |
| dosage_form | 胶囊、粉剂、酸奶、发酵乳等 |
| placebo_type | 安慰剂类型 |

## clinical_outcome

| 字段 | 含义 |
| --- | --- |
| subject_id | 受试者编号 |
| study_id | 研究编号 |
| weight_change | 体重变化 |
| weight_change_percent | 体重变化百分比 |
| BMI_change | BMI 变化 |
| waist_change | 腰围变化 |
| TG_change | 甘油三酯变化 |
| TC_change | 总胆固醇变化 |
| LDL_change | LDL-C 变化 |
| HDL_change | HDL-C 变化 |
| FBG_change | 空腹血糖变化 |
| FINS_change | 空腹胰岛素变化 |
| HOMA_IR_change | HOMA-IR 变化 |
| inflammatory_marker_change | 炎症指标变化 |
| responder_label | 响应者标签 |

## strain_function_matrix

| 字段 | 含义 |
| --- | --- |
| strain_id | 菌株编号 |
| genus | 属 |
| species | 种 |
| strain_name | 株名 |
| genome_accession | 基因组编号 |
| safety_gate | pass / fail |
| AMR_risk | 耐药风险 |
| virulence_risk | 毒力风险 |
| BSH_potential | 胆盐水解相关功能 |
| SCFA_potential | SCFA 相关功能 |
| carbohydrate_utilization | 碳水化合物利用能力 |
| mucin_adhesion_potential | 黏液层黏附潜力 |
| EPS_potential | 胞外多糖潜力 |
| anti_inflammatory_evidence | 抗炎证据 |
| literature_weight_loss_evidence | 减脂文献证据 |
| probiotic_use_history | 益生菌使用历史 |

