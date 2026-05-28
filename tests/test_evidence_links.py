from pathlib import Path

from proslim_ai.evidence_links import validate_strain_evidence_links
from proslim_ai.provenance import validate_provenance


def test_evidence_registry_provenance_passes():
    root = Path(__file__).resolve().parents[1]
    registry = root / "tests" / "fixtures" / "evidence_registry_with_strain_evidence.csv"

    result = validate_provenance(root / "config", "evidence_registry", registry)

    assert result.ok


def test_validate_strain_evidence_links_passes_when_identifiers_are_registered():
    root = Path(__file__).resolve().parents[1]
    strain_table = root / "tests" / "fixtures" / "strain_function_matrix_with_provenance.csv"
    registry = root / "tests" / "fixtures" / "evidence_registry_with_strain_evidence.csv"

    result = validate_strain_evidence_links(strain_table, registry)

    assert result.ok
    assert result.rows_checked == 1


def test_validate_strain_evidence_links_fails_when_identifiers_are_missing():
    root = Path(__file__).resolve().parents[1]
    strain_table = root / "tests" / "fixtures" / "strain_function_matrix_with_provenance.csv"
    registry = root / "tests" / "fixtures" / "evidence_registry_missing_strain_evidence.csv"

    result = validate_strain_evidence_links(strain_table, registry)

    assert not result.ok
    assert any("DOI not in evidence_registry" in item for item in result.missing_links)
    assert any("PMID not in evidence_registry" in item for item in result.missing_links)

