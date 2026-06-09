# Third-Pass Gap Audit Summary

Generated on 2026-06-09.

This pass quantified residual missingness after the first two PDF extraction batches and re-mined only records that had a local source file but still lacked key review fields.

## Outputs

- `results/pdf_review_extracts/review_gap_audit_summary.csv`
- `results/pdf_review_extracts/third_pass_gap_extracts.csv`
- `results/prediction_results/review_priority_top100.enriched.pdf_deep_augmented.download_augmented.second_pass_augmented.download_second_pass_augmented.third_pass_gap_augmented.csv`
- `data/intervention_data/outcome_review_worksheet.review_priority_top100.pdf_deep_augmented.download_augmented.second_pass_augmented.download_second_pass_augmented.third_pass_gap_augmented.csv`
- `data/intervention_data/intervention_review_worksheet.top100.pdf_deep_augmented.download_augmented.second_pass_augmented.download_second_pass_augmented.third_pass_gap_augmented.csv`

## Residual Missingness Before Third Pass

- Top100 priority table: 100 rows
  - Rows with local source files: 44
  - Rows missing local source files: 56
  - Rows missing second-pass result snippets: 59
  - Rows missing second-pass value/P-value candidates: 61
  - Rows missing second-pass dose terms: 64
  - Rows missing second-pass sample terms: 63
- Outcome review table: 414 rows
  - Rows with local source files: 194
  - Rows missing local source files: 220
  - Rows missing second-pass result snippets: 230
  - Rows missing second-pass value/P-value candidates: 244
  - Rows missing second-pass dose terms: 263
  - Rows missing second-pass sample terms: 256
- Intervention review table: 100 rows
  - Rows with local source files: 1
  - Rows missing local source files: 99

## Third-Pass Targeted Fill

- Evidence IDs with local source but remaining priority-table gaps: 10
- Third-pass extraction failures: 0
- Image/scanned PDFs requiring OCR or manual review: 3
- Priority Top100 rows third-pass matched: 9
- Outcome review rows third-pass matched: 49
- Intervention review rows third-pass matched: 1

## Fields Added

- `priority_gaps_before_third_pass`
- `third_pass_source_status`
- `third_pass_fill_note`
- `third_pass_result_snippets`
- `third_pass_p_values`
- `third_pass_numeric_values`
- `third_pass_dose_terms`
- `third_pass_duration_terms`
- `third_pass_sample_terms`
- `third_pass_nct_enrollment`
- `third_pass_nct_study_design`
- `third_pass_nct_interventions`
- `third_pass_nct_primary_outcomes`
- `third_pass_nct_secondary_outcomes`
- `third_pass_nct_brief_summary`

## Still Requiring OCR Or Manual Review

These files are local but contain almost no machine-readable text with the current PDF parser:

- `2.pdf` mapped to `EUROPEPMC:41126806`
- `4.pdf` mapped to `EUROPEPMC:35126309`
- `5.pdf` mapped to `EUROPEPMC:40416368`

## Main Remaining Cause Of Missingness

Most remaining gaps are not extractable from the currently available local files because the corresponding Top100 records do not yet have a matched local PDF/CSV source. The next highest-yield action is to add full-text PDFs or trial records for the 56 Top100 priority records without local sources, then rerun `scripts/audit_and_fill_review_gaps.py`.
