# Top100 PDF Augmentation Summary

Generated on 2026-06-09 from local files under:

`F:\workspace\codex\strain mix codex`

## Outputs

- `results/pdf_review_extracts/pdf_source_index.csv`
- `results/pdf_review_extracts/pdf_structured_extracts.csv`
- `results/prediction_results/review_priority_top100.enriched.pdf_augmented.csv`
- `results/prediction_results/review_priority_top100.enriched.pdf_deep_augmented.csv`
- `data/intervention_data/outcome_review_worksheet.review_priority_top100.pdf_augmented.csv`
- `data/intervention_data/outcome_review_worksheet.review_priority_top100.pdf_deep_augmented.csv`
- `data/intervention_data/intervention_review_worksheet.top100.pdf_augmented.csv`
- `data/intervention_data/intervention_review_worksheet.top100.pdf_deep_augmented.csv`
- `data/intervention_data/outcome_review_worksheet.top100_batch1.pdf_augmented.csv`
- `data/intervention_data/outcome_review_worksheet.top100_batch2.pdf_augmented.csv`
- `data/intervention_data/outcome_review_worksheet.top100_batch3.pdf_augmented.csv`
- `data/intervention_data/outcome_review_worksheet.top100_batch4.pdf_augmented.csv`
- `results/prediction_results/review_priority_top100_batch1_predictions.pdf_augmented.csv`
- `results/prediction_results/review_priority_top100_batch2_predictions.pdf_augmented.csv`
- `results/prediction_results/review_priority_top100_batch3_predictions.pdf_augmented.csv`
- `results/prediction_results/review_priority_top100_batch4_predictions.pdf_augmented.csv`

## Added Columns

- `pdf_source_file`
- `pdf_match_score`
- `pdf_pages`
- `pdf_intervention_terms`
- `pdf_duration_terms`
- `pdf_cfu_terms`
- `pdf_sample_size_terms`
- `pdf_outcome_terms`
- `pdf_text_excerpt`

## Deep Extraction Columns

- `pdf_deep_species_strain_terms`
- `pdf_deep_strain_codes`
- `pdf_deep_dose_terms`
- `pdf_deep_duration_terms`
- `pdf_deep_sample_size_terms`
- `pdf_deep_design_terms`
- `pdf_deep_dosage_form_terms`
- `pdf_deep_p_value_terms`
- `pdf_deep_numeric_value_terms`
- `pdf_deep_result_snippets`
- `pdf_deep_methods_excerpt`
- `pdf_deep_extraction_status`
- `pdf_deep_error`

## Matching Summary

- Local files parsed: 47
- Parse failures: 0
- Evidence matching threshold used for augmentation: `match_score >= 0.60`
- Unique Top100 evidence IDs matched: 35
- `review_priority_top100.enriched`: 34 / 100 rows matched
- `outcome_review_worksheet.review_priority_top100`: 154 / 414 rows matched
- `intervention_review_worksheet.top100`: 1 / 100 rows matched
- Outcome batch matches: batch1 69, batch2 70, batch3 15, batch4 0
- Prediction batch matches: batch1 15, batch2 15, batch3 4, batch4 0

## Deep Extraction Summary

- Evidence IDs with deep extraction: 35
- Deep extraction failures: 0
- Evidence IDs with species/strain terms: 26
- Evidence IDs with dose terms: 12
- Evidence IDs with P-value terms: 25
- Evidence IDs with result snippets: 32
- `review_priority_top100.enriched.pdf_deep_augmented`: 34 / 100 rows deep matched; 31 rows with result snippets
- `outcome_review_worksheet.review_priority_top100.pdf_deep_augmented`: 154 / 414 rows deep matched; 144 rows with result snippets
- `intervention_review_worksheet.top100.pdf_deep_augmented`: 1 / 100 rows deep matched; 1 row with result snippets
- Outcome deep batch matches: batch1 69, batch2 70, batch3 15, batch4 0
- Prediction deep batch matches: batch1 15, batch2 15, batch3 4, batch4 0

## Files Requiring Manual Confirmation

These parsed successfully but were not automatically merged because the title/file-name match score was below 0.60, or the extracted title was too weak:

- `1123.pdf`
- `3.pdf`
- `7.pdf`
- `bm-article-p121_2 (1).pdf`
- `bm-article-p121_2.pdf`
- `cureus-0017-00000082613.pdf`
- `dmj-2021-0370.pdf`
- `ec-EC-25-0219.pdf`
- `MEHD-27-30312.pdf`
- `nutrients-12-00222-v2.pdf`

Borderline files that were merged but should still be manually checked using `pdf_match_score`:

- `2.pdf`
- `5.pdf`
- `6.pdf`
- `bmfh-37-067.pdf`
