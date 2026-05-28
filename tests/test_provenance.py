from pathlib import Path

from proslim_ai.provenance import validate_provenance


def test_validate_provenance_passes_when_database_and_publication_ids_exist():
    root = Path(__file__).resolve().parents[1]
    csv_path = root / "tests" / "fixtures" / "strain_function_matrix_with_provenance.csv"

    result = validate_provenance(root / "config", "strain_function_matrix", csv_path)

    assert result.ok
    assert result.rows_checked == 1


def test_validate_provenance_fails_without_publication_identifier():
    root = Path(__file__).resolve().parents[1]
    csv_path = root / "tests" / "fixtures" / "strain_function_matrix_missing_provenance.csv"

    result = validate_provenance(root / "config", "strain_function_matrix", csv_path)

    assert not result.ok
    assert "missing publication identifier" in result.row_errors[0]


def test_validate_provenance_fails_for_unregistered_source_and_bad_identifiers():
    root = Path(__file__).resolve().parents[1]
    csv_path = root / "tests" / "fixtures" / "strain_function_matrix_bad_format.csv"

    result = validate_provenance(root / "config", "strain_function_matrix", csv_path)

    assert not result.ok
    assert any("unregistered source" in error for error in result.row_errors)
    assert any("invalid DOI format" in error for error in result.row_errors)
    assert any("invalid PMID format" in error for error in result.row_errors)
    assert any("invalid URL format" in error for error in result.row_errors)


def test_validate_provenance_accepts_pandas_float_like_pmid():
    root = Path(__file__).resolve().parents[1]
    csv_path = root / "tests" / "fixtures" / "evidence_registry_float_pmid.out.csv"

    try:
        csv_path.write_text(
            "evidence_id,evidence_type,source_database,source_accession,source_url,doi,pmid,"
            "title,year,journal,study_design,data_field_supported,extraction_note,curator,extraction_date\n"
            "EV001,literature,PubMed,12345678,https://pubmed.ncbi.nlm.nih.gov/12345678/,"
            "10.1000/example,12345678.0,Title,2024,Journal,RCT,field,note,curator,2026-05-26\n",
            encoding="utf-8",
        )

        result = validate_provenance(root / "config", "evidence_registry", csv_path)

        assert result.ok
    finally:
        csv_path.unlink(missing_ok=True)
