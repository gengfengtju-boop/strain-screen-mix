# Manual Review SOP

Use this SOP for outcome review worksheet rows.

Start here:

1. `results/prediction_results/review_priority_top10_quick_start.csv`
2. `results/prediction_results/review_priority_top100_batch1_predictions.csv`
3. `data/intervention_data/outcome_review_worksheet.top100_batch1.csv`

## Required Fields

For each confirmed outcome row, fill:

- `final_value`: numeric effect or concise extracted value. Prefer between-group change/difference when available.
- `final_unit`: unit from source, for example `kg`, `kg/m2`, `cm`, `%`, `mg/dL`, `mmol/L`, `cm2`, or `relative_abundance`.
- `final_direction`: use controlled language such as `decrease_beneficial`, `increase_beneficial`, `improved`, `no_significant_effect`, or `unfavorable`.
- `comparison`: describe the statistical contrast, for example `intervention_change_vs_placebo_change`, `between_group_post`, `within_group_baseline_to_post`, `subgroup_only`, or `not_reported`.
- `time_point`: intervention duration or assessment point, for example `12 weeks`.
- `p_value_confirmed`: exact p value text when available. Include `between-group` or `within-group` when needed.
- `sample_size_confirmed`: analyzed N for the endpoint, preferably by arm when available.
- `review_status`: set to `extracted` only when `final_value`, `final_unit`, `final_direction`, and `p_value_confirmed` are complete.
- `reviewer_note`: record caveats, including PP-only, ITT not significant, subgroup-only, exploratory microbiome, protocol-only, or abstract-only extraction.

## Review Rules

- Prefer randomized between-group evidence over within-group changes.
- Mark `final_direction` as `no_significant_effect` when the between-group result is not significant, even if within-group change is significant.
- If the paper reports PP benefit but ITT is not significant, put `PP_only; ITT_not_significant` in `reviewer_note`.
- If the row is only a protocol/trial registration with no result, keep `review_status=pending` and note `protocol_no_results`.
- If the intervention is not probiotic/prebiotic/synbiotic/postbiotic but is still microbiome-relevant, note the intervention type explicitly.
- Do not set `review_status=extracted` from title-only evidence.

## Batch Files

Prediction batches:

- `results/prediction_results/review_priority_top100_batch1_predictions.csv`
- `results/prediction_results/review_priority_top100_batch2_predictions.csv`
- `results/prediction_results/review_priority_top100_batch3_predictions.csv`
- `results/prediction_results/review_priority_top100_batch4_predictions.csv`

Outcome review batches:

- `data/intervention_data/outcome_review_worksheet.top100_batch1.csv`
- `data/intervention_data/outcome_review_worksheet.top100_batch2.csv`
- `data/intervention_data/outcome_review_worksheet.top100_batch3.csv`
- `data/intervention_data/outcome_review_worksheet.top100_batch4.csv`

After each batch, run:

```powershell
.venv\Scripts\proslim-ai.exe validate-outcome-review data\intervention_data\outcome_review_worksheet.top100_batch1.csv
```
