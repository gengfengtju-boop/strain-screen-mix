# Second-Pass Deep Mining Summary

Generated on 2026-06-09.

This pass re-mined both prior PDF/CSV batches using more pages per document and focused extraction around intervention, result, anthropometric, metabolic, microbiome, safety, numeric value, P-value, and table-like snippets.

## Inputs

- First batch index: `results/pdf_review_extracts/pdf_source_index.csv`
- Download batch index: `results/pdf_review_extracts/download_pdf_source_index.csv`

## Extraction Outputs

- `results/pdf_review_extracts/pdf_second_pass_extracts.csv`
- `results/pdf_review_extracts/download_pdf_second_pass_extracts.csv`

## Final Augmented Review Tables

- `results/prediction_results/review_priority_top100.enriched.pdf_deep_augmented.download_augmented.second_pass_augmented.download_second_pass_augmented.csv`
- `data/intervention_data/outcome_review_worksheet.review_priority_top100.pdf_deep_augmented.download_augmented.second_pass_augmented.download_second_pass_augmented.csv`
- `data/intervention_data/intervention_review_worksheet.top100.pdf_deep_augmented.download_augmented.second_pass_augmented.download_second_pass_augmented.csv`
- `data/intervention_data/outcome_review_worksheet.top100_batch1.pdf_deep_augmented.download_augmented.second_pass_augmented.download_second_pass_augmented.csv`
- `data/intervention_data/outcome_review_worksheet.top100_batch2.pdf_deep_augmented.download_augmented.second_pass_augmented.download_second_pass_augmented.csv`
- `data/intervention_data/outcome_review_worksheet.top100_batch3.pdf_deep_augmented.download_augmented.second_pass_augmented.download_second_pass_augmented.csv`
- `data/intervention_data/outcome_review_worksheet.top100_batch4.pdf_deep_augmented.download_augmented.second_pass_augmented.download_second_pass_augmented.csv`
- `results/prediction_results/review_priority_top100_batch1_predictions.pdf_deep_augmented.download_augmented.second_pass_augmented.download_second_pass_augmented.csv`
- `results/prediction_results/review_priority_top100_batch2_predictions.pdf_deep_augmented.download_augmented.second_pass_augmented.download_second_pass_augmented.csv`
- `results/prediction_results/review_priority_top100_batch3_predictions.pdf_deep_augmented.download_augmented.second_pass_augmented.download_second_pass_augmented.csv`
- `results/prediction_results/review_priority_top100_batch4_predictions.pdf_deep_augmented.download_augmented.second_pass_augmented.download_second_pass_augmented.csv`

## Added Second-Pass Columns

- `second_pass_source_file`
- `second_pass_match_score`
- `second_pass_pages_total`
- `second_pass_intervention_snippets`
- `second_pass_results_snippets`
- `second_pass_anthropometric_snippets`
- `second_pass_metabolic_snippets`
- `second_pass_microbiome_snippets`
- `second_pass_safety_snippets`
- `second_pass_value_pvalue_candidates`
- `second_pass_table_like_lines`
- `second_pass_arm_terms`
- `second_pass_dose_terms`
- `second_pass_duration_terms`
- `second_pass_sample_terms`
- `second_pass_extraction_status`
- `second_pass_error`

## First Batch Results

- Evidence IDs mined: 35
- Extraction failures: 0
- Evidence IDs with result snippets: 32
- Evidence IDs with value/P-value candidates: 30
- Evidence IDs with table-like lines: 31
- Top100 priority rows second-pass matched: 34 / 100
- Outcome review rows second-pass matched: 154 / 414
- Intervention review rows second-pass matched: 1 / 100

## Download Batch Results

- Evidence IDs mined: 12
- Extraction failures: 0
- Evidence IDs with result snippets: 12
- Evidence IDs with value/P-value candidates: 12
- Evidence IDs with table-like lines: 12
- Additional Top100 priority rows second-pass matched: 12 / 100
- Additional outcome review rows second-pass matched: 49 / 414
- Additional intervention review rows second-pass matched: 0 / 100

## Notes For Manual Review

- The final `download_second_pass_augmented.csv` tables retain previous PDF/deep/download fields and add the latest `second_pass_*` fields.
- `second_pass_value_pvalue_candidates` and `second_pass_table_like_lines` are candidate evidence snippets, not final curated values.
- Human reviewers should still confirm direction, units, time point, comparator, and whether P-values are within-group or between-group.
