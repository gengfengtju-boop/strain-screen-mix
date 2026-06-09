# Top100 PDF Augmentation Summary

Generated on 2026-06-09 from local files under:

`F:\workspace\codex\strain mix codex`

## Outputs

- `results/pdf_review_extracts/pdf_source_index.csv`
- `results/prediction_results/review_priority_top100.enriched.pdf_augmented.csv`
- `data/intervention_data/outcome_review_worksheet.review_priority_top100.pdf_augmented.csv`
- `data/intervention_data/intervention_review_worksheet.top100.pdf_augmented.csv`
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
