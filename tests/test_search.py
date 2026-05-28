import pandas as pd
import pytest
import requests

from proslim_ai.search_clients import ApiClient, ApiRequestError, HttpConfig
from proslim_ai.search import (
    _assembly_candidates,
    _clinical_trial_candidates,
    _europe_pmc_candidates,
    _pubmed_candidates,
    write_evidence_candidates,
    write_genome_candidates,
)


def test_pubmed_candidates_extract_doi_and_pmid():
    records = [
        {
            "uid": "12345678",
            "title": "Probiotic weight loss trial",
            "pubdate": "2024 Jan",
            "fulljournalname": "Example Journal",
            "articleids": [{"idtype": "doi", "value": "10.1000/example"}],
        }
    ]

    candidates = _pubmed_candidates(records, "tester", "2026-05-26")

    assert candidates[0].source_database == "PubMed"
    assert candidates[0].doi == "10.1000/example"
    assert candidates[0].pmid == "12345678"


def test_europe_pmc_candidates_extract_metadata():
    records = [
        {
            "pmid": "12345678",
            "doi": "10.1000/example",
            "title": "Europe PMC evidence",
            "pubYear": "2024",
            "journalTitle": "Example Journal",
        }
    ]

    candidates = _europe_pmc_candidates(records, "tester", "2026-05-26")

    assert candidates[0].evidence_id == "EUROPEPMC:12345678"
    assert candidates[0].source_database == "PubMed"


def test_clinical_trial_candidates_extract_nct_id():
    studies = [
        {
            "protocolSection": {
                "identificationModule": {
                    "nctId": "NCT00000000",
                    "briefTitle": "Probiotic obesity study",
                },
                "statusModule": {"startDateStruct": {"date": "2024-01-01"}},
            }
        }
    ]

    candidates = _clinical_trial_candidates(studies, "tester", "2026-05-26")

    assert candidates[0].source_database == "ClinicalTrials.gov"
    assert candidates[0].source_accession == "NCT00000000"
    assert candidates[0].year == "2024"


def test_assembly_candidates_extract_genome_metadata():
    records = [
        {
            "uid": "100",
            "assemblyaccession": "GCF_000000000.1",
            "organism": "Lactobacillus gasseri",
            "assemblyname": "ASM000000v1",
            "assemblystatus": "Complete Genome",
            "refseq_category": "representative genome",
            "taxid": 1596,
            "submitter": "Example Submitter",
            "assemblyreleasedate": "2024/01/01",
        }
    ]

    candidates = _assembly_candidates(records, "Lactobacillus gasseri", "tester", "2026-05-26")

    assert candidates[0].source_database == "NCBI Genome"
    assert candidates[0].source_accession == "GCF_000000000.1"
    assert candidates[0].organism_name == "Lactobacillus gasseri"
    assert candidates[0].assembly_level == "Complete Genome"
    assert candidates[0].manual_review_flag == "query_terms_matched"


def test_write_evidence_candidates():
    candidates = _pubmed_candidates(
        [
            {
                "uid": "12345678",
                "title": "Probiotic weight loss trial",
                "pubdate": "2024 Jan",
                "fulljournalname": "Example Journal",
                "articleids": [{"idtype": "doi", "value": "10.1000/example"}],
            }
        ],
        "tester",
        "2026-05-26",
    )
    from pathlib import Path

    output_path = Path(__file__).resolve().parent / "fixtures" / "evidence_candidates.out.csv"

    try:
        write_evidence_candidates(candidates, output_path)

        frame = pd.read_csv(output_path)
        assert frame.loc[0, "pmid"] == 12345678
        assert frame.loc[0, "doi"] == "10.1000/example"
    finally:
        output_path.unlink(missing_ok=True)


def test_write_genome_candidates():
    from pathlib import Path

    candidates = _assembly_candidates(
        [
            {
                "uid": "100",
                "assemblyaccession": "GCF_000000000.1",
                "organism": "Lactobacillus gasseri",
            }
        ],
        "Lactobacillus gasseri SBT2055",
        "tester",
        "2026-05-26",
    )
    output_path = Path(__file__).resolve().parent / "fixtures" / "genome_candidates.out.csv"

    try:
        write_genome_candidates(candidates, output_path)

        frame = pd.read_csv(output_path)
        assert frame.loc[0, "source_accession"] == "GCF_000000000.1"
        assert frame.loc[0, "manual_review_flag"] == "needs_strain_confirmation"
    finally:
        output_path.unlink(missing_ok=True)


def test_api_client_wraps_request_errors(monkeypatch):
    def fake_get(*args, **kwargs):
        raise requests.exceptions.SSLError("ssl failed")

    monkeypatch.setattr("requests.get", fake_get)
    client = ApiClient(HttpConfig(retry_count=0))

    with pytest.raises(ApiRequestError):
        client.get_json("https://example.org/api", {})
