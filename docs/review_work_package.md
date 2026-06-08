# Review Work Package

Current evidence registry:

- `data/literature_database/evidence_registry.expansion2.csv`
- 1097 deduplicated evidence rows.

Priority prediction files:

- `results/prediction_results/preliminary_evidence_response_prioritization.combined_top659.csv`
- `results/prediction_results/review_priority_top100.csv`
- `results/prediction_results/review_priority_top200.csv`

Manual outcome review files:

- `data/intervention_data/outcome_review_worksheet.combined_high_medium_top930.csv`
- `data/intervention_data/outcome_review_worksheet.review_priority_top100.csv`
- `data/intervention_data/outcome_review_worksheet.review_priority_top200.csv`

Gap reports:

- `results/prediction_results/combined_top659_data_gap_report.csv`
- `results/prediction_results/combined_top659_review_package_summary.csv`

Recommended review order:

1. Review `review_priority_top100.csv` first.
2. Fill extracted rows in `outcome_review_worksheet.review_priority_top100.csv`.
3. Continue to `review_priority_top200.csv` when the top 100 are complete.
4. Use `combined_top659_data_gap_report.csv` to fill missing taxa and intervention type hints.

Current summary:

- Total prediction candidates: 659
- High confidence: 96
- Medium confidence: 240
- Low confidence: 323
- Top 100 outcome review rows: 414
- Top 200 outcome review rows: 694
- Combined high/medium outcome review rows: 930
