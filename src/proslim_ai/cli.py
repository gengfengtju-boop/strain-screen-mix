from __future__ import annotations

import argparse
from pathlib import Path

from .modules import MODULES
from .paths import ProjectPaths, find_project_root
from .project import check_project, write_template_tables
from .config import load_table_schemas
from .audit import audit_project
from .batch_search import run_batch_search
from .details import build_evidence_details
from .dose_gap import build_dose_gap_queue
from .cleaning import clean_sample_metadata
from .evidence_links import validate_strain_evidence_links
from .evidence_merge import merge_evidence_candidates
from .enrichment import enrich_prediction_hints
from .export import export_ascii_safe_csv
from .extraction import build_extraction_drafts
from .extraction_queue import build_extraction_queue
from .finalize import finalize_clinical_outcomes
from .formulation_recommendation import build_formulation_recommendations
from .hints import extract_detail_hints
from .provenance import validate_provenance
from .preliminary_prediction import build_preliminary_predictions
from .outcome_prioritization import build_outcome_prioritized_predictions
from .outcome_structuring import structure_outcome_review
from .obesity_model import train_obesity_models
from .review import build_review_worksheets
from .review_filter import filter_review_worksheet
from .review_validation import validate_outcome_review
from .robust_combination_optimizer import optimize_strain_combinations
from .response_model import apply_response_model_to_combinations, train_response_model
from .schemas import validate_csv_schema
from .search import search_evidence, search_genomes
from .search_clients import ApiRequestError
from .screening import screen_evidence_registry
from .tabpfn_benchmark import benchmark_tabpfn


def _paths(root: str | None) -> ProjectPaths:
    return ProjectPaths(find_project_root(Path(root)) if root else find_project_root())


def cmd_check(args: argparse.Namespace) -> int:
    paths = _paths(args.root)
    result = check_project(paths)
    print(f"Project root: {paths.root}")
    if result.ok:
        print("OK: required directories and config files are present.")
        return 0

    if result.missing_directories:
        print("Missing directories:")
        for item in result.missing_directories:
            print(f"  - {item}")
    if result.missing_config_files:
        print("Missing config files:")
        for item in result.missing_config_files:
            print(f"  - config/{item}")
    return 1


def cmd_modules(args: argparse.Namespace) -> int:
    for index, module in enumerate(MODULES, start=1):
        print(f"{index}. {module.name} - {module.title}")
        print(f"   dir: {module.script_dir}")
        print(f"   outputs: {', '.join(module.expected_outputs)}")
    return 0


def cmd_audit(args: argparse.Namespace) -> int:
    paths = _paths(args.root)
    result = audit_project(paths.root)
    print(f"Project root: {paths.root}")
    if result.project_check.missing_directories:
        print("Missing directories:")
        for item in result.project_check.missing_directories:
            print(f"  - {item}")
    if result.project_check.missing_config_files:
        print("Missing config files:")
        for item in result.project_check.missing_config_files:
            print(f"  - config/{item}")
    if result.template_errors:
        print("Template errors:")
        for item in result.template_errors:
            print(f"  - {item}")
    if result.source_registry_errors:
        print("Source registry errors:")
        for item in result.source_registry_errors:
            print(f"  - {item}")
    if result.ok:
        print("OK: project structure, templates, and source registry are consistent.")
        return 0
    return 1


def cmd_templates(args: argparse.Namespace) -> int:
    paths = _paths(args.root)
    written = write_template_tables(paths, overwrite=args.overwrite)
    if not written:
        print("No templates written; files already exist.")
        return 0
    print("Written template tables:")
    for path in written:
        print(f"  - {path}")
    return 0


def cmd_show_schema(args: argparse.Namespace) -> int:
    paths = _paths(args.root)
    schemas = load_table_schemas(paths.config)
    if args.table not in schemas:
        print(f"Unknown table schema: {args.table}")
        print("Valid schemas:")
        for name in sorted(schemas):
            print(f"  - {name}")
        return 1
    print(args.table)
    for column in schemas[args.table]:
        print(f"  - {column}")
    return 0


def cmd_validate_table(args: argparse.Namespace) -> int:
    paths = _paths(args.root)
    result = validate_csv_schema(
        config_dir=paths.config,
        table_name=args.table,
        csv_path=Path(args.csv),
        allow_extra_columns=not args.strict,
    )
    print(f"Table: {result.table_name}")
    print(f"File: {result.path}")
    if result.ok:
        print("OK: required columns are present.")
    else:
        print("Missing columns:")
        for column in result.missing_columns:
            print(f"  - {column}")
    if result.extra_columns:
        print("Extra columns:")
        for column in result.extra_columns:
            print(f"  - {column}")
    return 0 if result.ok else 1


def cmd_clean_sample_metadata(args: argparse.Namespace) -> int:
    paths = _paths(args.root)
    summary = clean_sample_metadata(
        config_dir=paths.config,
        input_path=Path(args.input),
        output_path=Path(args.output),
        derive_obesity_status=not args.no_derive_obesity_status,
    )
    print(f"Input: {summary.input_path}")
    print(f"Output: {summary.output_path}")
    if summary.missing_required_columns:
        print("Missing required columns:")
        for column in summary.missing_required_columns:
            print(f"  - {column}")
        return 1
    print(f"Rows: {summary.rows_in} -> {summary.rows_out}")
    if summary.added_columns:
        print("Added columns:")
        for column in summary.added_columns:
            print(f"  - {column}")
    return 0


def cmd_validate_provenance(args: argparse.Namespace) -> int:
    paths = _paths(args.root)
    result = validate_provenance(paths.config, args.table, Path(args.csv))
    print(f"Table: {result.table_name}")
    print(f"File: {result.path}")
    if result.schema_missing_columns:
        print("Missing schema columns:")
        for column in result.schema_missing_columns:
            print(f"  - {column}")
        return 1
    print(f"Rows checked: {result.rows_checked}")
    if result.row_errors:
        print("Provenance errors:")
        for error in result.row_errors:
            print(f"  - {error}")
        return 1
    print("OK: provenance requirements are satisfied.")
    return 0


def cmd_validate_evidence_links(args: argparse.Namespace) -> int:
    result = validate_strain_evidence_links(
        strain_table_path=Path(args.strain_table),
        evidence_registry_path=Path(args.evidence_registry),
    )
    print(f"Strain table: {result.strain_table_path}")
    print(f"Evidence registry: {result.evidence_registry_path}")
    print(f"Rows checked: {result.rows_checked}")
    if result.missing_links:
        print("Missing evidence links:")
        for item in result.missing_links:
            print(f"  - {item}")
        return 1
    print("OK: all strain evidence identifiers are registered.")
    return 0


def cmd_merge_evidence(args: argparse.Namespace) -> int:
    paths = _paths(args.root)
    result = merge_evidence_candidates(
        config_dir=paths.config,
        input_paths=[Path(item) for item in args.inputs],
        output_path=Path(args.output),
    )
    print("Evidence candidates merged.")
    print(f"Output: {result.output_path}")
    print(f"Rows read: {result.rows_read}")
    print(f"Rows written: {result.rows_written}")
    print(f"Duplicates removed: {result.duplicates_removed}")
    return 0


def cmd_export_ascii(args: argparse.Namespace) -> int:
    rows = export_ascii_safe_csv(Path(args.input), Path(args.output))
    print(f"Input: {args.input}")
    print(f"Output: {args.output}")
    print(f"Rows written: {rows}")
    return 0


def cmd_enrich_prediction_hints(args: argparse.Namespace) -> int:
    result = enrich_prediction_hints(
        prediction_path=Path(args.predictions),
        details_paths=[Path(item) for item in args.details],
        output_path=Path(args.output),
    )
    print(f"Input predictions: {result.prediction_path}")
    print(f"Output: {result.output_path}")
    print(f"Rows: {result.rows_read} -> {result.rows_written}")
    print(f"Intervention hints filled: {result.intervention_filled}")
    print(f"Taxa hints filled: {result.taxa_filled}")
    return 0


def cmd_search_evidence(args: argparse.Namespace) -> int:
    paths = _paths(args.root)
    try:
        count = search_evidence(
            config_dir=paths.config,
            query=args.query,
            output_path=Path(args.output),
            source=args.source,
            retmax=args.retmax,
            curator=args.curator,
        )
    except ApiRequestError as exc:
        print(f"Search failed: {exc}")
        return 1
    print(f"Source: {args.source}")
    print(f"Query: {args.query}")
    print(f"Output: {args.output}")
    print(f"Candidates written: {count}")
    return 0


def cmd_search_genomes(args: argparse.Namespace) -> int:
    paths = _paths(args.root)
    try:
        count = search_genomes(
            config_dir=paths.config,
            query=args.query,
            output_path=Path(args.output),
            retmax=args.retmax,
            curator=args.curator,
        )
    except ApiRequestError as exc:
        print(f"Search failed: {exc}")
        return 1
    print("Source: ncbi_assembly")
    print(f"Query: {args.query}")
    print(f"Output: {args.output}")
    print(f"Candidates written: {count}")
    return 0


def cmd_batch_search(args: argparse.Namespace) -> int:
    paths = _paths(args.root)
    results = run_batch_search(
        root=paths.root,
        config_path=Path(args.config),
        manifest_path=Path(args.manifest),
        curator=args.curator,
    )
    ok_count = sum(1 for result in results if result.status == "ok")
    failed = [result for result in results if result.status != "ok"]
    print(f"Batch jobs: {len(results)}")
    print(f"Succeeded: {ok_count}")
    print(f"Failed: {len(failed)}")
    print(f"Manifest: {args.manifest}")
    for result in results:
        print(f"- {result.status}: {result.name} -> {result.records_written} rows")
        if result.error:
            print(f"  error: {result.error}")
    return 0 if not failed else 1


def cmd_screen_evidence(args: argparse.Namespace) -> int:
    paths = _paths(args.root)
    result = screen_evidence_registry(
        config_dir=paths.config,
        input_path=Path(args.input),
        output_path=Path(args.output),
    )
    print(f"Input: {result.input_path}")
    print(f"Output: {result.output_path}")
    print(f"Rows: {result.rows_read} -> {result.rows_written}")
    return 0


def cmd_build_extraction_drafts(args: argparse.Namespace) -> int:
    paths = _paths(args.root)
    result = build_extraction_drafts(
        config_dir=paths.config,
        screening_path=Path(args.screening),
        intervention_output=Path(args.intervention_output),
        outcome_output=Path(args.outcome_output),
    )
    print(f"Input: {result.input_path}")
    print(f"Intervention draft: {result.intervention_output} ({result.intervention_rows} rows)")
    print(f"Outcome draft: {result.outcome_output} ({result.outcome_rows} rows)")
    return 0


def cmd_build_extraction_queue(args: argparse.Namespace) -> int:
    result = build_extraction_queue(
        screening_path=Path(args.screening),
        output_path=Path(args.output),
        priority_levels=set(args.priority),
        top_n=args.top_n,
        min_relevance_score=args.min_relevance_score,
        exclude_paths=[Path(item) for item in args.exclude_evidence_ids_from],
    )
    print(f"Input: {result.input_path}")
    print(f"Output: {result.output_path}")
    print(f"Rows read: {result.rows_read}")
    print(f"Excluded evidence ids: {result.excluded_evidence}")
    print(f"Queue rows written: {result.rows_written}")
    return 0


def cmd_fetch_evidence_details(args: argparse.Namespace) -> int:
    paths = _paths(args.root)
    result = build_evidence_details(
        config_dir=paths.config,
        screening_path=Path(args.screening),
        output_path=Path(args.output),
    )
    print(f"Input: {result.input_path}")
    print(f"Output: {result.output_path}")
    print(f"Rows: {result.rows_read} -> {result.rows_written}")
    print(f"Failed rows: {result.failed_rows}")
    return 0 if result.failed_rows == 0 else 1


def cmd_extract_hints(args: argparse.Namespace) -> int:
    result = extract_detail_hints(Path(args.details), Path(args.output))
    print(f"Input: {result.input_path}")
    print(f"Output: {result.output_path}")
    print(f"Rows: {result.rows_read} -> {result.rows_written}")
    return 0


def cmd_build_review_worksheets(args: argparse.Namespace) -> int:
    paths = _paths(args.root)
    result = build_review_worksheets(
        config_dir=paths.config,
        hints_path=Path(args.hints),
        outcome_output=Path(args.outcome_output),
        intervention_output=Path(args.intervention_output),
        reviewer=args.reviewer,
    )
    print(f"Input hints: {result.hints_path}")
    print(f"Evidence rows: {result.evidence_rows}")
    print(f"Outcome review rows: {result.outcome_rows} -> {result.outcome_output}")
    print(f"Intervention review rows: {result.intervention_rows} -> {result.intervention_output}")
    return 0


def cmd_finalize_clinical_outcomes(args: argparse.Namespace) -> int:
    paths = _paths(args.root)
    result = finalize_clinical_outcomes(
        config_dir=paths.config,
        draft_path=Path(args.draft),
        review_path=Path(args.review),
        output_path=Path(args.output),
    )
    print(f"Output: {result.output_path}")
    print(f"Rows written: {result.rows_written}")
    print(f"Extracted review rows used: {result.extracted_review_rows}")
    return 0


def cmd_predict_preliminary(args: argparse.Namespace) -> int:
    paths = _paths(args.root)
    result = build_preliminary_predictions(
        config_dir=paths.config,
        screening_path=Path(args.screening),
        hints_path=Path(args.hints),
        output_path=Path(args.output),
    )
    print(f"Output: {result.output_path}")
    print(f"Rows written: {result.rows_written}")
    print("Note: preliminary heuristic ranking only; not a trained microbiome response model.")
    return 0


def cmd_prioritize_with_outcomes(args: argparse.Namespace) -> int:
    result = build_outcome_prioritized_predictions(
        preliminary_path=Path(args.preliminary),
        outcome_review_path=Path(args.outcome_review),
        output_path=Path(args.output),
    )
    print(f"Output: {result.output_path}")
    print(f"Rows written: {result.rows_written}")
    print(f"Extracted outcome rows used: {result.extracted_review_rows}")
    print("Note: outcome-aware heuristic ranking; not a trained microbiome response model.")
    return 0


def cmd_recommend_formulations(args: argparse.Namespace) -> int:
    result = build_formulation_recommendations(
        strain_output=Path(args.strain_output),
        formulation_output=Path(args.formulation_output),
        combination_output=Path(args.combination_output),
        min_strains=args.min_strains,
        max_strains=args.max_strains,
        top_n=args.top_n,
        safety_status_path=Path(args.safety_status) if args.safety_status else None,
    )
    print(f"Strains: {result.strain_output} ({result.strains_written} rows)")
    print(f"Formulations: {result.formulation_output} ({result.formulations_written} rows)")
    print(f"Combinations: {result.combination_output} ({result.combinations_written} rows)")
    print("Note: pending-safety combinations are hypothesis-ranked but not validation-eligible.")
    return 0


def cmd_optimize_combinations(args: argparse.Namespace) -> int:
    result = optimize_strain_combinations(
        structured_outcomes_path=Path(args.structured_outcomes),
        formulation_evidence_output=Path(args.formulation_evidence_output),
        combination_output=Path(args.combination_output),
        diagnostics_output=Path(args.diagnostics_output),
        min_strains=args.min_strains,
        max_strains=args.max_strains,
        top_n=args.top_n,
        simulations=args.simulations,
        random_seed=args.random_seed,
        safety_status_path=Path(args.safety_status) if args.safety_status else None,
    )
    print(
        f"Formulation evidence: {result.formulation_evidence_output} "
        f"({result.formulations_scored} rows)"
    )
    print(f"Robust combinations: {result.combination_output} ({result.combinations_scored} scored)")
    print(f"Diagnostics: {result.diagnostics_output}; simulations={result.simulations}")
    print("Note: output is validation priority, not clinical or individual response probability.")
    return 0


def cmd_benchmark_tabpfn(args: argparse.Namespace) -> int:
    metrics = benchmark_tabpfn(
        structured_outcomes_path=Path(args.structured_outcomes),
        model_path=Path(args.model_path),
        output_path=Path(args.output),
        n_estimators=args.n_estimators,
        random_seed=args.random_seed,
        cv_repeats=args.cv_repeats,
        review_paths=[Path(path) for path in args.review],
    )
    print(f"Output: {args.output}")
    print(
        f"AUC={metrics['roc_auc_mean']:.3f}+/-{metrics['roc_auc_std']:.3f}; "
        f"AP={metrics['average_precision_mean']:.3f}; "
        f"eligible_for_combination_fusion={metrics['eligible_for_combination_fusion']}"
    )
    return 0


def cmd_structure_outcomes(args: argparse.Namespace) -> int:
    result = structure_outcome_review(
        review_path=Path(args.review),
        output_path=Path(args.output),
    )
    print(f"Output: {result.output_path}")
    print(f"Rows written: {result.rows_written}")
    print("Note: structured fields are heuristic parses; manually review before meta-analysis.")
    return 0


def cmd_filter_review_worksheet(args: argparse.Namespace) -> int:
    levels = set(args.confidence_level)
    result = filter_review_worksheet(
        prediction_path=Path(args.predictions),
        review_path=Path(args.review),
        output_path=Path(args.output),
        confidence_levels=levels,
    )
    print(f"Output: {result.output_path}")
    print(f"Selected evidence ids: {result.selected_evidence}")
    print(f"Review rows written: {result.rows_written}")
    return 0


def cmd_validate_outcome_review(args: argparse.Namespace) -> int:
    result = validate_outcome_review(Path(args.review))
    print(f"Review worksheet: {result.path}")
    print(f"Rows checked: {result.rows_checked}")
    if result.ok:
        print("OK: extracted rows contain required final fields.")
        return 0
    print("Review validation errors:")
    for error in result.errors:
        print(f"  - {error}")
    return 1


def cmd_train_response_model(args: argparse.Namespace) -> int:
    result = train_response_model(
        structured_outcome_path=Path(args.structured_outcomes),
        row_predictions_output=Path(args.row_predictions),
        evidence_predictions_output=Path(args.evidence_predictions),
        metrics_output=Path(args.metrics),
        model_output=Path(args.model),
        review_paths=[Path(path) for path in args.review],
        cv_repeats=args.cv_repeats,
        random_seed=args.random_seed,
        locked_model=args.locked_model,
        feature_profile=args.feature_profile,
    )
    print(f"Rows used: {result.rows_used}")
    print(f"Evidence ids: {result.evidence_count}")
    print(f"Row predictions: {result.row_predictions_output}")
    print(f"Evidence predictions: {result.evidence_predictions_output}")
    print(f"Metrics: {result.metrics_output}")
    print(f"Model: {result.model_output}")
    print("Note: leakage-safe study-endpoint evidence classifier; not an individual responder model.")
    return 0


def cmd_build_dose_gap_queue(args: argparse.Namespace) -> int:
    queue = build_dose_gap_queue(
        Path(args.structured_outcomes),
        [Path(path) for path in args.review],
        Path(args.output),
    )
    print(f"Dose-gap studies: {len(queue)}")
    print(f"Output: {args.output}")
    return 0


def cmd_train_obesity_models(args: argparse.Namespace) -> int:
    result = train_obesity_models(
        metadata_path=Path(args.metadata),
        feature_matrix_path=Path(args.features),
        metrics_output=Path(args.metrics),
        classifier_output=Path(args.classifier),
        bmi_regressor_output=Path(args.bmi_regressor),
    )
    print(f"Samples used: {result.samples_used}")
    print(f"Studies used: {result.studies_used}")
    print(f"Metrics: {result.metrics_output}")
    print(f"OMS classifier: {result.classifier_output}")
    print(f"BMI regressor: {result.bmi_regressor_output}")
    print("Note: grouped internal validation only; an external cohort is still required.")
    return 0


def cmd_apply_response_model(args: argparse.Namespace) -> int:
    result = apply_response_model_to_combinations(
        combination_input=Path(args.combination_input),
        evidence_predictions_path=Path(args.evidence_predictions),
        output_path=Path(args.output),
    )
    print(f"Output: {result.output_path}")
    print(f"Rows written: {result.rows_written}")
    print(f"Rows with model probability: {result.combinations_with_model_probability}")
    print("Note: probabilities are applied only when the evidence classifier passes its informativeness gate.")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="proslim-ai",
        description="ProSlim-Microbiome-AI project utility CLI.",
    )
    parser.add_argument("--root", help="Project root directory. Defaults to current project.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    check = subparsers.add_parser("check", help="Check required project structure.")
    check.set_defaults(func=cmd_check)

    modules = subparsers.add_parser("modules", help="List pipeline modules.")
    modules.set_defaults(func=cmd_modules)

    audit = subparsers.add_parser(
        "audit",
        help="Run project, schema-template, and source-registry checks.",
    )
    audit.set_defaults(func=cmd_audit)

    templates = subparsers.add_parser("write-templates", help="Write CSV header templates.")
    templates.add_argument("--overwrite", action="store_true", help="Overwrite existing templates.")
    templates.set_defaults(func=cmd_templates)

    show_schema = subparsers.add_parser("show-schema", help="Show columns for a table schema.")
    show_schema.add_argument("table", help="Schema name in config/table_schemas.yaml.")
    show_schema.set_defaults(func=cmd_show_schema)

    validate_table = subparsers.add_parser("validate-table", help="Validate a CSV header.")
    validate_table.add_argument("table", help="Schema name in config/table_schemas.yaml.")
    validate_table.add_argument("csv", help="CSV file to validate.")
    validate_table.add_argument(
        "--strict",
        action="store_true",
        help="Treat extra columns as errors as well as reporting them.",
    )
    validate_table.set_defaults(func=cmd_validate_table)

    clean_sample = subparsers.add_parser(
        "clean-sample-metadata",
        help="Standardize sample metadata and write a cleaned CSV.",
    )
    clean_sample.add_argument("input", help="Input sample_metadata CSV.")
    clean_sample.add_argument("output", help="Output cleaned CSV.")
    clean_sample.add_argument(
        "--no-derive-obesity-status",
        action="store_true",
        help="Do not fill missing obesity_status from BMI.",
    )
    clean_sample.set_defaults(func=cmd_clean_sample_metadata)

    provenance = subparsers.add_parser(
        "validate-provenance",
        help="Validate that a table has database and literature provenance.",
    )
    provenance.add_argument("table", help="Schema name with evidence rules.")
    provenance.add_argument("csv", help="CSV file to validate.")
    provenance.set_defaults(func=cmd_validate_provenance)

    evidence_links = subparsers.add_parser(
        "validate-evidence-links",
        help="Validate that strain DOI/PMID identifiers exist in evidence_registry.",
    )
    evidence_links.add_argument("strain_table", help="strain_function_matrix CSV.")
    evidence_links.add_argument("evidence_registry", help="evidence_registry CSV.")
    evidence_links.set_defaults(func=cmd_validate_evidence_links)

    merge_evidence = subparsers.add_parser(
        "merge-evidence-candidates",
        help="Merge and deduplicate evidence candidate CSV files into an evidence_registry draft.",
    )
    merge_evidence.add_argument("output", help="Output evidence_registry draft CSV.")
    merge_evidence.add_argument("inputs", nargs="+", help="Input evidence candidate CSV files.")
    merge_evidence.set_defaults(func=cmd_merge_evidence)

    export_ascii = subparsers.add_parser(
        "export-ascii-safe",
        help="Export a UTF-8 CSV with non-ASCII characters escaped for console-safe review.",
    )
    export_ascii.add_argument("input", help="Input CSV.")
    export_ascii.add_argument("output", help="Output ASCII-safe CSV.")
    export_ascii.set_defaults(func=cmd_export_ascii)

    enrich_predictions = subparsers.add_parser(
        "enrich-prediction-hints",
        help="Infer missing prediction intervention/taxa hints from evidence details.",
    )
    enrich_predictions.add_argument("predictions", help="Input preliminary prediction CSV.")
    enrich_predictions.add_argument("output", help="Output enriched prediction CSV.")
    enrich_predictions.add_argument(
        "--details",
        action="append",
        default=[],
        help="Evidence detail CSV to use for enrichment. Can be repeated.",
    )
    enrich_predictions.set_defaults(func=cmd_enrich_prediction_hints)

    search_cmd = subparsers.add_parser(
        "search-evidence",
        help="Search official literature or trial APIs and write evidence candidates.",
    )
    search_cmd.add_argument("query", help="Search query.")
    search_cmd.add_argument("output", help="Output evidence candidate CSV.")
    search_cmd.add_argument(
        "--source",
        choices=["pubmed", "europe_pmc", "clinical_trials"],
        default="pubmed",
        help="Official API source to query.",
    )
    search_cmd.add_argument("--retmax", type=int, help="Maximum number of records to request.")
    search_cmd.add_argument("--curator", default="auto_search", help="Curator label for output rows.")
    search_cmd.set_defaults(func=cmd_search_evidence)

    genome_search = subparsers.add_parser(
        "search-genomes",
        help="Search NCBI Assembly for candidate strain genomes.",
    )
    genome_search.add_argument("query", help="NCBI Assembly search query.")
    genome_search.add_argument("output", help="Output genome candidate CSV.")
    genome_search.add_argument("--retmax", type=int, help="Maximum number of records to request.")
    genome_search.add_argument("--curator", default="auto_search", help="Curator label for output rows.")
    genome_search.set_defaults(func=cmd_search_genomes)

    batch_search = subparsers.add_parser(
        "batch-search",
        help="Run configured evidence and genome searches sequentially.",
    )
    batch_search.add_argument(
        "--config",
        default="config/search_batch.yaml",
        help="Batch search YAML config.",
    )
    batch_search.add_argument(
        "--manifest",
        default="results/search_manifest.csv",
        help="Output manifest CSV.",
    )
    batch_search.add_argument("--curator", default="auto_search", help="Curator label for output rows.")
    batch_search.set_defaults(func=cmd_batch_search)

    screen_evidence = subparsers.add_parser(
        "screen-evidence",
        help="Rank and tag evidence_registry rows for manual extraction.",
    )
    screen_evidence.add_argument("input", help="Input evidence_registry CSV.")
    screen_evidence.add_argument("output", help="Output evidence screening CSV.")
    screen_evidence.set_defaults(func=cmd_screen_evidence)

    extraction_drafts = subparsers.add_parser(
        "build-extraction-drafts",
        help="Create intervention_metadata and clinical_outcome draft tables from screened evidence.",
    )
    extraction_drafts.add_argument("screening", help="Input evidence screening CSV.")
    extraction_drafts.add_argument("intervention_output", help="Output intervention_metadata draft CSV.")
    extraction_drafts.add_argument("outcome_output", help="Output clinical_outcome draft CSV.")
    extraction_drafts.set_defaults(func=cmd_build_extraction_drafts)

    extraction_queue = subparsers.add_parser(
        "build-extraction-queue",
        help="Build a prioritized top-N screening queue for detail fetch and manual extraction.",
    )
    extraction_queue.add_argument("screening", help="Input evidence screening CSV.")
    extraction_queue.add_argument("output", help="Output prioritized extraction queue CSV.")
    extraction_queue.add_argument(
        "--priority",
        action="append",
        default=["high", "medium"],
        help="Priority level to include. Can be repeated.",
    )
    extraction_queue.add_argument("--top-n", type=int, default=160)
    extraction_queue.add_argument("--min-relevance-score", type=int, default=1)
    extraction_queue.add_argument(
        "--exclude-evidence-ids-from",
        action="append",
        default=[],
        help="CSV file containing evidence_id values to exclude. Can be repeated.",
    )
    extraction_queue.set_defaults(func=cmd_build_extraction_queue)

    evidence_details = subparsers.add_parser(
        "fetch-evidence-details",
        help="Fetch PubMed abstracts and ClinicalTrials.gov details for screened evidence.",
    )
    evidence_details.add_argument("screening", help="Input evidence screening CSV.")
    evidence_details.add_argument("output", help="Output evidence detail CSV.")
    evidence_details.set_defaults(func=cmd_fetch_evidence_details)

    extract_hints = subparsers.add_parser(
        "extract-detail-hints",
        help="Extract dose, duration, sample-size, p-value, and outcome hints from evidence details.",
    )
    extract_hints.add_argument("details", help="Input evidence detail CSV.")
    extract_hints.add_argument("output", help="Output extraction hints CSV.")
    extract_hints.set_defaults(func=cmd_extract_hints)

    review_worksheets = subparsers.add_parser(
        "build-review-worksheets",
        help="Convert extraction hints into long-form manual review worksheets.",
    )
    review_worksheets.add_argument("hints", help="Input extraction hints CSV.")
    review_worksheets.add_argument("outcome_output", help="Output outcome review worksheet CSV.")
    review_worksheets.add_argument("intervention_output", help="Output intervention review worksheet CSV.")
    review_worksheets.add_argument("--reviewer", default="", help="Reviewer name or initials.")
    review_worksheets.set_defaults(func=cmd_build_review_worksheets)

    finalize_outcomes = subparsers.add_parser(
        "finalize-clinical-outcomes",
        help="Apply extracted outcome review rows to a clinical_outcome draft table.",
    )
    finalize_outcomes.add_argument("draft", help="Input clinical_outcome draft CSV.")
    finalize_outcomes.add_argument("review", help="Input outcome review worksheet CSV.")
    finalize_outcomes.add_argument("output", help="Output finalized clinical_outcome CSV.")
    finalize_outcomes.set_defaults(func=cmd_finalize_clinical_outcomes)

    preliminary = subparsers.add_parser(
        "predict-preliminary",
        help="Build a preliminary evidence-based prioritization score from screened evidence and hints.",
    )
    preliminary.add_argument("screening", help="Input evidence screening CSV.")
    preliminary.add_argument("hints", help="Input extraction hints CSV.")
    preliminary.add_argument("output", help="Output preliminary prediction CSV.")
    preliminary.set_defaults(func=cmd_predict_preliminary)

    outcome_priority = subparsers.add_parser(
        "prioritize-with-outcomes",
        help="Re-rank preliminary predictions using manually confirmed final outcome rows.",
    )
    outcome_priority.add_argument("preliminary", help="Input preliminary prediction CSV.")
    outcome_priority.add_argument("outcome_review", help="Input outcome review worksheet CSV.")
    outcome_priority.add_argument("output", help="Output outcome-aware prioritization CSV.")
    outcome_priority.set_defaults(func=cmd_prioritize_with_outcomes)

    recommend_formulations = subparsers.add_parser(
        "recommend-formulations",
        help="Generate formulation-aware 3-5 strain combination recommendations.",
    )
    recommend_formulations.add_argument("strain_output", help="Output candidate strain CSV.")
    recommend_formulations.add_argument("formulation_output", help="Output formulation block CSV.")
    recommend_formulations.add_argument("combination_output", help="Output formulation-aware combination CSV.")
    recommend_formulations.add_argument("--min-strains", type=int, default=3)
    recommend_formulations.add_argument("--max-strains", type=int, default=5)
    recommend_formulations.add_argument("--top-n", type=int, default=50)
    recommend_formulations.add_argument(
        "--safety-status",
        help="Optional CSV with strain_id and safety_gate (pass/fail/pending).",
    )
    recommend_formulations.set_defaults(func=cmd_recommend_formulations)

    optimize_combinations = subparsers.add_parser(
        "optimize-combinations",
        help="Robustly rank 3-5 strain hypotheses from confirmed outcome evidence.",
    )
    optimize_combinations.add_argument("structured_outcomes", help="Structured outcome CSV.")
    optimize_combinations.add_argument(
        "formulation_evidence_output", help="Output formulation evidence posterior CSV."
    )
    optimize_combinations.add_argument("combination_output", help="Output robust combination CSV.")
    optimize_combinations.add_argument("diagnostics_output", help="Output model diagnostics JSON.")
    optimize_combinations.add_argument("--min-strains", type=int, default=3)
    optimize_combinations.add_argument("--max-strains", type=int, default=5)
    optimize_combinations.add_argument("--top-n", type=int, default=50)
    optimize_combinations.add_argument("--simulations", type=int, default=2000)
    optimize_combinations.add_argument("--random-seed", type=int, default=17)
    optimize_combinations.add_argument(
        "--safety-status",
        help="Optional CSV with strain_id and safety_gate (pass/fail/pending).",
    )
    optimize_combinations.set_defaults(func=cmd_optimize_combinations)

    tabpfn_benchmark = subparsers.add_parser(
        "benchmark-tabpfn",
        help="Benchmark a local TabPFN checkpoint with leakage-safe grouped validation.",
    )
    tabpfn_benchmark.add_argument("structured_outcomes", help="Structured outcome CSV.")
    tabpfn_benchmark.add_argument("model_path", help="Local official TabPFN classifier checkpoint.")
    tabpfn_benchmark.add_argument("output", help="Output benchmark metrics JSON.")
    tabpfn_benchmark.add_argument("--n-estimators", type=int, default=2)
    tabpfn_benchmark.add_argument("--random-seed", type=int, default=17)
    tabpfn_benchmark.add_argument("--cv-repeats", type=int, default=1)
    tabpfn_benchmark.add_argument(
        "--review",
        action="append",
        default=[],
        help="Extracted outcome review CSV used for leakage-safe intervention features; repeatable.",
    )
    tabpfn_benchmark.set_defaults(func=cmd_benchmark_tabpfn)

    structure_outcomes = subparsers.add_parser(
        "structure-outcomes",
        help="Parse extracted outcome review rows into structured effect/p-value fields.",
    )
    structure_outcomes.add_argument("review", help="Input outcome review worksheet CSV.")
    structure_outcomes.add_argument("output", help="Output structured outcome CSV.")
    structure_outcomes.set_defaults(func=cmd_structure_outcomes)

    filter_review = subparsers.add_parser(
        "filter-review-worksheet",
        help="Filter a manual review worksheet by preliminary prediction confidence levels.",
    )
    filter_review.add_argument("predictions", help="Input preliminary prediction CSV.")
    filter_review.add_argument("review", help="Input review worksheet CSV.")
    filter_review.add_argument("output", help="Output filtered review worksheet CSV.")
    filter_review.add_argument(
        "--confidence-level",
        action="append",
        default=["high_for_manual_review", "medium_for_manual_review"],
        help="Confidence level to include. Can be repeated.",
    )
    filter_review.set_defaults(func=cmd_filter_review_worksheet)

    validate_review = subparsers.add_parser(
        "validate-outcome-review",
        help="Validate extracted rows in an outcome review worksheet before finalization.",
    )
    validate_review.add_argument("review", help="Input outcome review worksheet CSV.")
    validate_review.set_defaults(func=cmd_validate_outcome_review)

    train_obesity = subparsers.add_parser(
        "train-obesity-models",
        help="Train leakage-safe sample-level OMS classification and BMI regression baselines.",
    )
    train_obesity.add_argument("metadata", help="Sample metadata CSV.")
    train_obesity.add_argument("features", help="Wide numeric feature matrix with sample_id.")
    train_obesity.add_argument("metrics", help="Output grouped-validation metrics JSON.")
    train_obesity.add_argument("classifier", help="Output pickled OMS classifier.")
    train_obesity.add_argument("bmi_regressor", help="Output pickled BMI regressor.")
    train_obesity.set_defaults(func=cmd_train_obesity_models)

    train_response = subparsers.add_parser(
        "train-response-model",
        help="Train a leakage-safe study-endpoint evidence classifier.",
    )
    train_response.add_argument("structured_outcomes", help="Input structured outcome CSV.")
    train_response.add_argument("row_predictions", help="Output row-level model prediction CSV.")
    train_response.add_argument("evidence_predictions", help="Output evidence-level classifier score CSV.")
    train_response.add_argument("metrics", help="Output model metrics JSON.")
    train_response.add_argument("model", help="Output pickled sklearn model.")
    train_response.add_argument(
        "--review",
        action="append",
        default=[],
        help="Extracted outcome review CSV used for leakage-safe intervention features; repeatable.",
    )
    train_response.add_argument("--cv-repeats", type=int, default=1)
    train_response.add_argument("--random-seed", type=int, default=17)
    train_response.add_argument(
        "--locked-model",
        help="Evaluate one prespecified candidate across grouped repeats without fold-wise selection.",
    )
    train_response.add_argument(
        "--feature-profile",
        choices=["all", "numeric_only", "size_duration"],
        default="all",
    )
    train_response.set_defaults(func=cmd_train_response_model)

    dose_gap = subparsers.add_parser(
        "build-dose-gap-queue",
        help="Build a study-level manual queue for missing microbial CFU doses.",
    )
    dose_gap.add_argument("structured_outcomes")
    dose_gap.add_argument("output")
    dose_gap.add_argument("--review", action="append", default=[], required=True)
    dose_gap.set_defaults(func=cmd_build_dose_gap_queue)

    apply_response = subparsers.add_parser(
        "apply-response-model",
        help="Apply informative evidence-classifier scores to combination rankings.",
    )
    apply_response.add_argument("combination_input", help="Input combination ranking CSV.")
    apply_response.add_argument("evidence_predictions", help="Evidence-level classifier score CSV.")
    apply_response.add_argument("output", help="Output combination ranking CSV with model probabilities.")
    apply_response.set_defaults(func=cmd_apply_response_model)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)
