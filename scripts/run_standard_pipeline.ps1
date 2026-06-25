<# 
.SYNOPSIS
Run the standard ProSlim-Microbiome-AI evidence-to-ranking workflow.

.DESCRIPTION
This script stitches the existing proslim-ai CLI commands into a reproducible
pipeline. By default it uses already-downloaded *_candidates.csv files and writes
standard-tagged outputs so existing curated/draft files are not overwritten.

Network/API steps are opt-in with -RunSearch and -FetchDetails.
#>

[CmdletBinding()]
param(
    [string]$Root = "",
    [string]$OutputTag = "standard",
    [switch]$RunSearch,
    [switch]$FetchDetails,
    [string]$ExistingEvidenceDetails = "",
    [string]$ExistingDetailHints = "",
    [switch]$StopAfterReviewWorksheets,
    [switch]$UseExistingOutcomeReview,
    [string]$ExistingOutcomeReview = "data/intervention_data/outcome_review_worksheet.high_medium.csv",
    [switch]$TrainResponseModel,
    [switch]$ApplyResponseModel,
    [switch]$ExportAscii
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

if (-not $Root) {
    $scriptDir = if ($PSScriptRoot) { $PSScriptRoot } else { Split-Path -Parent $MyInvocation.MyCommand.Path }
    $Root = (Resolve-Path (Join-Path $scriptDir "..")).Path
}

function Join-RootPath {
    param([Parameter(Mandatory = $true)][string]$RelativePath)
    return Join-Path $Root $RelativePath
}

function Invoke-ProSlim {
    param([Parameter(Mandatory = $true)][string[]]$Arguments)

    $cli = Join-RootPath ".venv/Scripts/proslim-ai.exe"
    if (Test-Path $cli) {
        & $cli --root $Root @Arguments
        if ($LASTEXITCODE -ne 0) {
            throw "proslim-ai failed: $($Arguments -join ' ')"
        }
        return
    }

    $env:PYTHONPATH = Join-RootPath "src"
    & python -m proslim_ai --root $Root @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "python -m proslim_ai failed: $($Arguments -join ' ')"
    }
}

function Assert-FileExists {
    param(
        [Parameter(Mandatory = $true)][string]$Path,
        [Parameter(Mandatory = $true)][string]$Message
    )
    if (-not (Test-Path $Path)) {
        throw "$Message Missing file: $Path"
    }
}

Push-Location $Root
try {
    Write-Host "== ProSlim standard pipeline =="
    Write-Host "Root: $Root"
    Write-Host "Output tag: $OutputTag"

    $literatureDir = Join-RootPath "data/literature_database"
    $interventionDir = Join-RootPath "data/intervention_data"
    $predictionDir = Join-RootPath "results/prediction_results"
    $strainScoreDir = Join-RootPath "results/candidate_strain_scores"
    $combinationDir = Join-RootPath "results/combination_ranking"
    $modelDir = Join-RootPath "models/responder_classifier"

    $evidenceRegistry = Join-RootPath "data/literature_database/evidence_registry.$OutputTag.csv"
    $evidenceScreening = Join-RootPath "data/literature_database/evidence_screening.$OutputTag.csv"
    $evidenceDetails = Join-RootPath "data/literature_database/evidence_details.$OutputTag.csv"
    $detailHints = Join-RootPath "data/literature_database/intervention_outcome_extraction_hints.$OutputTag.csv"
    $interventionDraft = Join-RootPath "data/intervention_data/intervention_metadata.$OutputTag.draft.csv"
    $outcomeDraft = Join-RootPath "data/intervention_data/clinical_outcome.$OutputTag.draft.csv"
    $outcomeReview = Join-RootPath "data/intervention_data/outcome_review_worksheet.$OutputTag.csv"
    $interventionReview = Join-RootPath "data/intervention_data/intervention_review_worksheet.$OutputTag.csv"
    $finalOutcome = Join-RootPath "data/intervention_data/clinical_outcome.$OutputTag.final.preview.csv"
    $preliminary = Join-RootPath "results/prediction_results/preliminary_evidence_response_prioritization.$OutputTag.csv"
    $outcomeAware = Join-RootPath "results/prediction_results/outcome_aware_response_prioritization.$OutputTag.csv"
    $structuredOutcomes = Join-RootPath "data/intervention_data/clinical_outcome.structured_effects.$OutputTag.csv"
    $rowPredictions = Join-RootPath "results/prediction_results/study_endpoint_response_row_predictions.$OutputTag.csv"
    $evidencePredictions = Join-RootPath "results/prediction_results/study_endpoint_response_evidence_predictions.$OutputTag.csv"
    $metrics = Join-RootPath "results/prediction_results/study_endpoint_response_model_metrics.$OutputTag.json"
    $model = Join-RootPath "models/responder_classifier/study_endpoint_evidence_classifier.$OutputTag.pkl"
    $strainOutput = Join-RootPath "results/candidate_strain_scores/formulation_aware_strain_scores.$OutputTag.csv"
    $formulationOutput = Join-RootPath "results/candidate_strain_scores/formulation_blocks.$OutputTag.csv"
    $combinationOutput = Join-RootPath "results/combination_ranking/formulation_aware_3to5_strain_combinations.$OutputTag.csv"
    $modelCombinationOutput = Join-RootPath "results/combination_ranking/model_response_3to5_strain_combinations.$OutputTag.csv"
    $safetyStatus = Join-RootPath "results/candidate_strain_scores/combination_safety_gate_eligibility_20260613.csv"

    foreach ($dir in @($literatureDir, $interventionDir, $predictionDir, $strainScoreDir, $combinationDir, $modelDir)) {
        New-Item -ItemType Directory -Force -Path $dir | Out-Null
    }

    Write-Host "`n[1/12] Audit project"
    Invoke-ProSlim @("audit")

    if ($RunSearch) {
        Write-Host "`n[2/12] Run configured API searches"
        Invoke-ProSlim @(
            "batch-search",
            "--config", "config/search_batch.yaml",
            "--manifest", "results/search_manifest.$OutputTag.csv"
        )
    } else {
        Write-Host "`n[2/12] Skip API search; using existing *_candidates.csv files"
    }

    Write-Host "`n[3/12] Merge evidence candidates"
    $candidateFiles = Get-ChildItem -Path $literatureDir -Filter "*_candidates.csv" -File |
        Sort-Object FullName |
        ForEach-Object { $_.FullName }
    if (-not $candidateFiles -or $candidateFiles.Count -eq 0) {
        throw "No evidence candidate CSV files found in $literatureDir. Run with -RunSearch or add *_candidates.csv files."
    }
    $mergeArgs = @("merge-evidence-candidates", $evidenceRegistry) + $candidateFiles
    Invoke-ProSlim $mergeArgs

    Write-Host "`n[4/12] Screen evidence registry"
    Invoke-ProSlim @("screen-evidence", $evidenceRegistry, $evidenceScreening)

    Write-Host "`n[5/12] Build extraction draft tables"
    Invoke-ProSlim @("build-extraction-drafts", $evidenceScreening, $interventionDraft, $outcomeDraft)

    if ($ExistingDetailHints) {
        Write-Host "`n[6/12] Use existing detail hints"
        $detailHints = Join-RootPath $ExistingDetailHints
        Assert-FileExists $detailHints "The requested existing detail-hints table was not found."
    } else {
        if ($ExistingEvidenceDetails) {
            Write-Host "`n[6/12] Use existing evidence details"
            $evidenceDetails = Join-RootPath $ExistingEvidenceDetails
            Assert-FileExists $evidenceDetails "The requested existing evidence-detail table was not found."
        } elseif ($FetchDetails) {
            Write-Host "`n[6/12] Fetch evidence details from supported APIs"
            Invoke-ProSlim @("fetch-evidence-details", $evidenceScreening, $evidenceDetails)
        } else {
            Write-Host "`n[6/12] Skip detail fetch"
            Assert-FileExists $evidenceDetails "Run with -FetchDetails, -ExistingEvidenceDetails, or -ExistingDetailHints."
        }

        Write-Host "`n[7/12] Extract detail hints"
        Invoke-ProSlim @("extract-detail-hints", $evidenceDetails, $detailHints)
    }

    Write-Host "`n[8/12] Build manual review worksheets"
    Invoke-ProSlim @("build-review-worksheets", $detailHints, $outcomeReview, $interventionReview)

    if ($StopAfterReviewWorksheets) {
        Write-Host "`nStopped after worksheet generation."
        Write-Host "Review and mark extracted rows in: $outcomeReview"
        exit 0
    }

    $reviewForFinalization = $outcomeReview
    if ($UseExistingOutcomeReview) {
        $reviewForFinalization = Join-RootPath $ExistingOutcomeReview
        Assert-FileExists $reviewForFinalization "The requested existing review worksheet was not found."
    }

    Write-Host "`n[9/12] Validate and finalize confirmed clinical outcomes"
    Invoke-ProSlim @("validate-outcome-review", $reviewForFinalization)
    Invoke-ProSlim @("finalize-clinical-outcomes", $outcomeDraft, $reviewForFinalization, $finalOutcome)

    Write-Host "`n[10/12] Build preliminary and outcome-aware prioritization"
    Invoke-ProSlim @("predict-preliminary", $evidenceScreening, $detailHints, $preliminary)
    Invoke-ProSlim @("prioritize-with-outcomes", $preliminary, $reviewForFinalization, $outcomeAware)

    Write-Host "`n[11/12] Generate formulation-aware strain and combination ranking"
    $recommendArgs = @("recommend-formulations", $strainOutput, $formulationOutput, $combinationOutput, "--min-strains", "3", "--max-strains", "5", "--top-n", "50")
    if (Test-Path $safetyStatus) {
        $recommendArgs += @("--safety-status", $safetyStatus)
    } else {
        Write-Warning "Safety-status table not found; all candidate strains remain pending."
    }
    Invoke-ProSlim $recommendArgs

    if ($TrainResponseModel) {
        Write-Host "`n[12/12] Train study-endpoint evidence classifier"
        Invoke-ProSlim @("structure-outcomes", $reviewForFinalization, $structuredOutcomes)
        Invoke-ProSlim @("train-response-model", $structuredOutcomes, $rowPredictions, $evidencePredictions, $metrics, $model)

        if ($ApplyResponseModel) {
            Write-Host "`n[12b] Apply informative evidence classifier to combination ranking"
            Invoke-ProSlim @("apply-response-model", $combinationOutput, $evidencePredictions, $modelCombinationOutput)
        }
    } else {
        Write-Host "`n[12/12] Skip supervised response-model training"
    }

    if ($ExportAscii) {
        Write-Host "`n[extra] Export ASCII-safe review copies"
        foreach ($path in @($evidenceRegistry, $evidenceScreening, $detailHints, $outcomeReview, $preliminary, $outcomeAware, $combinationOutput)) {
            if (Test-Path $path) {
                $asciiPath = [System.IO.Path]::ChangeExtension($path, $null) + ".ascii.csv"
                Invoke-ProSlim @("export-ascii-safe", $path, $asciiPath)
            }
        }
    }

    Write-Host "`nPipeline complete."
    Write-Host "Evidence registry: $evidenceRegistry"
    Write-Host "Outcome review worksheet: $outcomeReview"
    Write-Host "Outcome-aware prioritization: $outcomeAware"
    Write-Host "Combination ranking: $combinationOutput"
    if ($ApplyResponseModel -and (Test-Path $modelCombinationOutput)) {
        Write-Host "Model-applied combination ranking: $modelCombinationOutput"
    }
}
finally {
    Pop-Location
}
