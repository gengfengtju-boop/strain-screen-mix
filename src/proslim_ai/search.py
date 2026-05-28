from __future__ import annotations

import csv
from dataclasses import dataclass
from datetime import date
from html import unescape
from pathlib import Path
from typing import Any

from .config import load_yaml
from .search_clients import (
    ApiClient,
    ClinicalTrialsClient,
    EuropePmcClient,
    HttpConfig,
    NcbiAssemblyClient,
    PubMedClient,
)


@dataclass(frozen=True)
class EvidenceCandidate:
    evidence_id: str
    evidence_type: str
    source_database: str
    source_accession: str
    source_url: str
    doi: str
    pmid: str
    title: str
    year: str
    journal: str
    study_design: str
    data_field_supported: str
    extraction_note: str
    curator: str
    extraction_date: str


@dataclass(frozen=True)
class GenomeCandidate:
    candidate_id: str
    search_query: str
    source_database: str
    source_accession: str
    source_url: str
    organism_name: str
    assembly_name: str
    assembly_level: str
    refseq_category: str
    taxid: str
    submitter: str
    release_date: str
    query_match_score: float
    manual_review_flag: str
    extraction_note: str
    curator: str
    extraction_date: str


def _text(value: Any) -> str:
    if value is None:
        return ""
    return " ".join(unescape(str(value)).split())


def _pubmed_candidates(records: list[dict[str, Any]], curator: str, extraction_date: str) -> list[EvidenceCandidate]:
    candidates: list[EvidenceCandidate] = []
    for record in records:
        pmid = _text(record.get("uid"))
        article_ids = record.get("articleids", [])
        doi = ""
        if isinstance(article_ids, list):
            for article_id in article_ids:
                if article_id.get("idtype") == "doi":
                    doi = _text(article_id.get("value"))
                    break
        candidates.append(
            EvidenceCandidate(
                evidence_id=f"PMID:{pmid}",
                evidence_type="literature",
                source_database="PubMed",
                source_accession=pmid,
                source_url=f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/" if pmid else "",
                doi=doi,
                pmid=pmid,
                title=_text(record.get("title")),
                year=_text(record.get("pubdate")).split(" ")[0],
                journal=_text(record.get("fulljournalname") or record.get("source")),
                study_design="needs_manual_review",
                data_field_supported="evidence_registry",
                extraction_note="Auto-collected from PubMed E-utilities; requires manual review.",
                curator=curator,
                extraction_date=extraction_date,
            )
        )
    return candidates


def _europe_pmc_candidates(
    records: list[dict[str, Any]],
    curator: str,
    extraction_date: str,
) -> list[EvidenceCandidate]:
    candidates: list[EvidenceCandidate] = []
    for record in records:
        pmid = _text(record.get("pmid"))
        doi = _text(record.get("doi"))
        accession = pmid or doi or _text(record.get("id"))
        candidates.append(
            EvidenceCandidate(
                evidence_id=f"EUROPEPMC:{accession}",
                evidence_type="literature",
                source_database="PubMed" if pmid else "publisher supplementary data",
                source_accession=accession,
                source_url=f"https://europepmc.org/article/MED/{pmid}" if pmid else "",
                doi=doi,
                pmid=pmid,
                title=_text(record.get("title")),
                year=_text(record.get("pubYear")),
                journal=_text(record.get("journalTitle")),
                study_design="needs_manual_review",
                data_field_supported="evidence_registry",
                extraction_note="Auto-collected from Europe PMC; requires manual review.",
                curator=curator,
                extraction_date=extraction_date,
            )
        )
    return candidates


def _clinical_trial_candidates(
    studies: list[dict[str, Any]],
    curator: str,
    extraction_date: str,
) -> list[EvidenceCandidate]:
    candidates: list[EvidenceCandidate] = []
    for study in studies:
        protocol = study.get("protocolSection", {})
        identification = protocol.get("identificationModule", {})
        status = protocol.get("statusModule", {})
        nct_id = _text(identification.get("nctId"))
        title = _text(identification.get("briefTitle") or identification.get("officialTitle"))
        candidates.append(
            EvidenceCandidate(
                evidence_id=f"NCT:{nct_id}",
                evidence_type="clinical_trial",
                source_database="ClinicalTrials.gov",
                source_accession=nct_id,
                source_url=f"https://clinicaltrials.gov/study/{nct_id}" if nct_id else "",
                doi="",
                pmid="",
                title=title,
                year=_text(status.get("startDateStruct", {}).get("date", "")).split("-")[0],
                journal="",
                study_design="clinical_trial_registry",
                data_field_supported="intervention_metadata;clinical_outcome",
                extraction_note="Auto-collected from ClinicalTrials.gov API v2; requires manual review.",
                curator=curator,
                extraction_date=extraction_date,
            )
        )
    return candidates


def write_evidence_candidates(candidates: list[EvidenceCandidate], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = list(EvidenceCandidate.__dataclass_fields__)
    with output_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for candidate in candidates:
            writer.writerow(candidate.__dict__)


def _assembly_candidates(
    records: list[dict[str, Any]],
    search_query: str,
    curator: str,
    extraction_date: str,
) -> list[GenomeCandidate]:
    candidates: list[GenomeCandidate] = []
    for record in records:
        accession = _text(record.get("assemblyaccession"))
        searchable_text = " ".join(
            [
                _text(record.get("organism")),
                _text(record.get("assemblyname")),
                accession,
            ]
        ).lower()
        query_tokens = [
            token.lower()
            for token in search_query.replace('"', " ").replace("'", " ").split()
            if token.strip()
        ]
        matched_tokens = [token for token in query_tokens if token in searchable_text]
        query_match_score = round(len(matched_tokens) / len(query_tokens), 3) if query_tokens else 0.0
        manual_review_flag = "needs_strain_confirmation" if query_match_score < 1.0 else "query_terms_matched"
        candidates.append(
            GenomeCandidate(
                candidate_id=f"ASSEMBLY:{accession or _text(record.get('uid'))}",
                search_query=search_query,
                source_database="NCBI Genome",
                source_accession=accession,
                source_url=f"https://www.ncbi.nlm.nih.gov/datasets/genome/{accession}/" if accession else "",
                organism_name=_text(record.get("organism")),
                assembly_name=_text(record.get("assemblyname")),
                assembly_level=_text(record.get("assemblystatus")),
                refseq_category=_text(record.get("refseq_category")),
                taxid=_text(record.get("taxid")),
                submitter=_text(record.get("submitter")),
                release_date=_text(record.get("assemblyreleasedate")),
                query_match_score=query_match_score,
                manual_review_flag=manual_review_flag,
                extraction_note="Auto-collected from NCBI Assembly E-utilities; requires manual review.",
                curator=curator,
                extraction_date=extraction_date,
            )
        )
    return candidates


def write_genome_candidates(candidates: list[GenomeCandidate], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = list(GenomeCandidate.__dataclass_fields__)
    with output_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for candidate in candidates:
            writer.writerow(candidate.__dict__)


def search_evidence(
    config_dir: Path,
    query: str,
    output_path: Path,
    source: str = "pubmed",
    retmax: int | None = None,
    curator: str = "auto_search",
) -> int:
    config = load_yaml(config_dir / "search_config.yaml")
    http_config = HttpConfig(**config.get("http", {}))
    api_client = ApiClient(http_config)
    extraction_date = date.today().isoformat()
    candidates: list[EvidenceCandidate] = []

    if source == "pubmed":
        source_config = config["pubmed"]
        client = PubMedClient(source_config["base_url"], api_client)
        pmids = client.search_pmids(query, retmax or int(source_config["default_retmax"]))
        candidates = _pubmed_candidates(client.summaries(pmids), curator, extraction_date)
    elif source == "europe_pmc":
        source_config = config["europe_pmc"]
        client = EuropePmcClient(source_config["base_url"], api_client)
        records = client.search(query, retmax or int(source_config["default_page_size"]))
        candidates = _europe_pmc_candidates(records, curator, extraction_date)
    elif source == "clinical_trials":
        source_config = config["clinical_trials"]
        client = ClinicalTrialsClient(source_config["base_url"], api_client)
        studies = client.search(query, retmax or int(source_config["default_page_size"]))
        candidates = _clinical_trial_candidates(studies, curator, extraction_date)
    else:
        raise ValueError("source must be one of: pubmed, europe_pmc, clinical_trials")

    write_evidence_candidates(candidates, output_path)
    return len(candidates)


def search_genomes(
    config_dir: Path,
    query: str,
    output_path: Path,
    retmax: int | None = None,
    curator: str = "auto_search",
) -> int:
    config = load_yaml(config_dir / "search_config.yaml")
    http_config = HttpConfig(**config.get("http", {}))
    api_client = ApiClient(http_config)
    extraction_date = date.today().isoformat()
    source_config = config["ncbi_assembly"]
    client = NcbiAssemblyClient(source_config["base_url"], api_client)
    assembly_ids = client.search_ids(query, retmax or int(source_config["default_retmax"]))
    candidates = _assembly_candidates(client.summaries(assembly_ids), query, curator, extraction_date)
    write_genome_candidates(candidates, output_path)
    return len(candidates)
