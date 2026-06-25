# Run the arm-level + continuous effect-size upgrade end to end.
#
#   powershell -File scripts\modeling\run_continuous_effect_upgrade.ps1
#
# Produces dated artifacts under data/intervention_data/ and results/prediction_results/.
# Curated structured effects are the primary source; abstract-mined rows (low confidence)
# are added only to reach the 60-80 study target and are excluded from the primary model.

$ErrorActionPreference = "Stop"
$env:PYTHONPATH = "src"
$stamp = Get-Date -Format "yyyyMMdd"
$env:PROSLIM_RUN_STAMP = $stamp
$python = Join-Path $PSScriptRoot "..\..\.venv\Scripts\python.exe"
if (-not (Test-Path $python)) {
    throw "Project virtual-environment Python not found: $python"
}

function Assert-LastCommand([string]$step) {
    if ($LASTEXITCODE -ne 0) {
        throw "$step failed with exit code $LASTEXITCODE"
    }
}

$arms      = "data/intervention_data/study_arm_registry.upgrade_$stamp.csv"
$effects   = "data/intervention_data/continuous_effect_sizes.upgrade_$stamp.csv"
$metrics   = "results/prediction_results/continuous_effect_model_metrics_$stamp.json"
$preds     = "results/prediction_results/continuous_effect_predictions_$stamp.csv"
$model     = "models/continuous_effect_model_$stamp.pkl"
$meta      = "results/prediction_results/effect_meta_analysis_hksj_$stamp.json"
$robust    = "results/prediction_results/missing_variance_robustness_$stamp.json"
$quality   = "results/prediction_results/effect_quality_report_$stamp.json"
$manifestPath = "config/continuous_effect_upgrade_manifest.json"
$manifest = Get-Content $manifestPath -Raw | ConvertFrom-Json

$structured = $manifest.structured_effects | ForEach-Object {
    "--structured"; (Resolve-Path $_).Path
}

$reviews = $manifest.outcome_reviews | ForEach-Object {
    "--review"; (Resolve-Path $_).Path
}

$interventions = $manifest.intervention_reviews | ForEach-Object {
    "--intervention-review"; (Resolve-Path $_).Path
}

$details = $manifest.evidence_details | ForEach-Object {
    "--details"; (Resolve-Path $_).Path
}

Write-Host "[0/16] Validating pinned production inputs ..."
& $python -m proslim_ai validate-continuous-manifest $manifestPath
Assert-LastCommand "Input manifest validation"

Write-Host "[1/16] Building intervention-arm registry ..."
& $python -m proslim_ai build-arm-dataset $arms @reviews @interventions @structured --target-studies 80
Assert-LastCommand "Arm registry construction"

Write-Host "[2/16] Building continuous effect sizes (curated + abstract supplement) ..."
& $python -m proslim_ai build-continuous-effects $arms $effects @reviews @structured @details --include-abstract-mined
Assert-LastCommand "Continuous effect construction"

Write-Host "[3/16] Training continuous effect models (high-confidence primary) ..."
& $python -m proslim_ai train-continuous-effect-model $effects $arms $metrics $preds $model `
    --minimum-studies 5 --confidence-policy high_confidence_only
Assert-LastCommand "Continuous model training"

Write-Host "[4/16] Running small-sample robust meta-analysis ..."
& $python -m proslim_ai meta-analyze-effects $effects $arms $meta --minimum-studies 3
Assert-LastCommand "Random-effects meta-analysis"

Write-Host "[5/16] Triangulating evidence with incomplete study variances ..."
& $python -m proslim_ai analyze-missing-variance $effects $arms $robust `
    --minimum-studies 3 --bootstrap-iterations 10000
Assert-LastCommand "Missing-variance robustness analysis"

Write-Host "[6/16] Auditing effect quality and duplicate trial aliases ..."
& $python scripts/modeling/audit_continuous_effect_quality.py
Assert-LastCommand "Effect quality audit"

Write-Host "[7/16] Auditing intervention feature completeness ..."
& $python scripts/modeling/audit_intervention_feature_completeness.py
Assert-LastCommand "Intervention feature completeness audit"

Write-Host "[8/16] Auditing evidence layers and cointerventions ..."
& $python scripts/modeling/analyze_evidence_robustness_layers.py
Assert-LastCommand "Evidence layer audit"

Write-Host "[9/16] Auditing the body-fat replication hypothesis ..."
& $python scripts/modeling/audit_body_fat_hypothesis.py
Assert-LastCommand "Body-fat hypothesis audit"

Write-Host "[10/16] Building the direct-variance review queue ..."
& $python scripts/modeling/build_direct_variance_review_queue.py
Assert-LastCommand "Direct-variance review queue"

Write-Host "[11/16] Exporting direct-variance review drafts ..."
& $python scripts/modeling/export_direct_variance_review_drafts.py
Assert-LastCommand "Direct-variance review drafts"

Write-Host "[12/16] Building the direct-variance candidate patch ..."
& $python scripts/modeling/build_direct_variance_candidate_patch.py
Assert-LastCommand "Direct-variance candidate patch"

Write-Host "[13/16] Running balanced-arm-n sensitivity ..."
& $python scripts/modeling/run_balanced_arm_n_sensitivity.py
Assert-LastCommand "Balanced-arm-n sensitivity"

Write-Host "[14/16] Evaluating the cross-outcome partial-pooling baseline ..."
& $python scripts/modeling/run_partial_pooling_baseline.py
Assert-LastCommand "Partial-pooling baseline"

Write-Host "[15/16] Auditing external-validation readiness ..."
& $python scripts/modeling/audit_external_validation_readiness.py
Assert-LastCommand "External-validation readiness audit"

Write-Host "[16/16] Refreshing the research status summary ..."
& $python scripts/modeling/summarize_continuous_effect_upgrade.py
Assert-LastCommand "Research status summary"

Write-Host "Done. Artifacts:"
Write-Host "  arms     $arms"
Write-Host "  effects  $effects"
Write-Host "  metrics  $metrics"
Write-Host "  preds    $preds"
Write-Host "  model    $model"
Write-Host "  meta     $meta"
Write-Host "  robust   $robust"
Write-Host "  quality  $quality"
