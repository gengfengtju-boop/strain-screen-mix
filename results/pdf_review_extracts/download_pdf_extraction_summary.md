# Download PDF Extraction Summary

Generated on 2026-06-09 from local files under:

`D:\Download`

## Outputs

- `results/pdf_review_extracts/download_pdf_source_index.csv`
- `results/pdf_review_extracts/download_pdf_structured_extracts.csv`
- `results/prediction_results/review_priority_top100.enriched.pdf_deep_augmented.download_augmented.csv`
- `data/intervention_data/outcome_review_worksheet.review_priority_top100.pdf_deep_augmented.download_augmented.csv`
- `data/intervention_data/intervention_review_worksheet.top100.pdf_deep_augmented.download_augmented.csv`
- `data/intervention_data/outcome_review_worksheet.top100_batch1.pdf_deep_augmented.download_augmented.csv`
- `data/intervention_data/outcome_review_worksheet.top100_batch2.pdf_deep_augmented.download_augmented.csv`
- `data/intervention_data/outcome_review_worksheet.top100_batch3.pdf_deep_augmented.download_augmented.csv`
- `data/intervention_data/outcome_review_worksheet.top100_batch4.pdf_deep_augmented.download_augmented.csv`
- `results/prediction_results/review_priority_top100_batch1_predictions.pdf_deep_augmented.download_augmented.csv`
- `results/prediction_results/review_priority_top100_batch2_predictions.pdf_deep_augmented.download_augmented.csv`
- `results/prediction_results/review_priority_top100_batch3_predictions.pdf_deep_augmented.download_augmented.csv`
- `results/prediction_results/review_priority_top100_batch4_predictions.pdf_deep_augmented.download_augmented.csv`

## Added Columns

- `download_deep_species_strain_terms`
- `download_deep_strain_codes`
- `download_deep_dose_terms`
- `download_deep_duration_terms`
- `download_deep_sample_size_terms`
- `download_deep_design_terms`
- `download_deep_dosage_form_terms`
- `download_deep_p_value_terms`
- `download_deep_numeric_value_terms`
- `download_deep_result_snippets`
- `download_deep_methods_excerpt`
- `download_deep_extraction_status`
- `download_deep_error`

## Matching Summary

- Local files parsed: 18
- Parse failures: 0
- Files with match score >= 0.60: 14
- Unique evidence IDs deep extracted: 12
- Evidence IDs with species/strain terms: 10
- Evidence IDs with dose terms: 4
- Evidence IDs with P-value terms: 10
- Evidence IDs with result snippets: 12
- `review_priority_top100.enriched`: 12 / 100 rows download-deep matched
- `outcome_review_worksheet.review_priority_top100`: 49 / 414 rows download-deep matched
- `intervention_review_worksheet.top100`: 0 / 100 rows download-deep matched
- Outcome batch matches: batch1 5, batch2 4, batch3 36, batch4 4
- Prediction batch matches: batch1 1, batch2 1, batch3 9, batch4 1

## Files Requiring Manual Confirmation

These parsed successfully but were not automatically merged because the match score was below 0.60:

- `DMSO-558226-investigating-the-microbiota-gut-brain-axis-mechanisms-of-tr.pdf`
- `9.pdf`
- `mmc1.pdf`
- `s12967-025-06927-z.pdf`

Notes:

- Two local copies of the combined probiotics plus calorie restriction paper were indexed. They map to the same evidence ID and were deduplicated during table merging.
- `NCT05114018.csv` and `NCT05114018 (1).csv` map to the same evidence ID and were deduplicated during table merging.
