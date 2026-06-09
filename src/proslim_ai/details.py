from __future__ import annotations

import csv
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .config import load_yaml
from .search_clients import ApiClient, ApiRequestError, HttpConfig


DETAIL_FIELDS = [
    "evidence_id",
    "source_database",
    "source_accession",
    "source_url",
    "title",
    "abstract",
    "publication_types",
    "clinical_interventions",
    "enrollment",
    "phase",
    "primary_outcomes",
    "secondary_outcomes",
    "arms",
    "detail_status",
]


@dataclass(frozen=True)
class DetailBuildResult:
    input_path: Path
    output_path: Path
    rows_read: int
    rows_written: int
    failed_rows: int


def _text(value: Any) -> str:
    if value is None:
        return ""
    return " ".join(str(value).split())


def _join(items: list[str]) -> str:
    return "; ".join(item for item in items if item)


def _parse_pubmed_xml(xml_text: str) -> dict[str, dict[str, str]]:
    root = ET.fromstring(xml_text)
    records: dict[str, dict[str, str]] = {}
    for article in root.findall(".//PubmedArticle"):
        pmid = _text(article.findtext(".//PMID"))
        title = _text(article.findtext(".//ArticleTitle"))
        abstract_parts = [
            _text("".join(node.itertext())) for node in article.findall(".//Abstract/AbstractText")
        ]
        publication_types = [
            _text(node.text) for node in article.findall(".//PublicationTypeList/PublicationType")
        ]
        if pmid:
            records[pmid] = {
                "title": title,
                "abstract": _join(abstract_parts),
                "publication_types": _join(publication_types),
            }
    return records


def _clinical_trials_detail(study: dict[str, Any]) -> dict[str, str]:
    protocol = study.get("protocolSection", {})
    identification = protocol.get("identificationModule", {})
    design = protocol.get("designModule", {})
    arms = protocol.get("armsInterventionsModule", {})
    outcomes = protocol.get("outcomesModule", {})

    interventions = [
        _text(item.get("name"))
        for item in arms.get("interventions", [])
        if isinstance(item, dict)
    ]
    arm_groups = [
        _text(item.get("label"))
        for item in arms.get("armGroups", [])
        if isinstance(item, dict)
    ]
    primary_outcomes = [
        _text(item.get("measure"))
        for item in outcomes.get("primaryOutcomes", [])
        if isinstance(item, dict)
    ]
    secondary_outcomes = [
        _text(item.get("measure"))
        for item in outcomes.get("secondaryOutcomes", [])
        if isinstance(item, dict)
    ]

    enrollment_info = design.get("enrollmentInfo", {})
    return {
        "title": _text(identification.get("briefTitle") or identification.get("officialTitle")),
        "clinical_interventions": _join(interventions),
        "enrollment": _text(enrollment_info.get("count")),
        "phase": _join(design.get("phases", [])) if isinstance(design.get("phases"), list) else "",
        "primary_outcomes": _join(primary_outcomes),
        "secondary_outcomes": _join(secondary_outcomes),
        "arms": _join(arm_groups),
    }


def _pubmed_details(config: dict, api_client: ApiClient, pmids: list[str]) -> dict[str, dict[str, str]]:
    if not pmids:
        return {}
    base_url = config["pubmed"]["base_url"].rstrip("/")
    records: dict[str, dict[str, str]] = {}
    chunk_size = 80
    for start in range(0, len(pmids), chunk_size):
        chunk = pmids[start : start + chunk_size]
        xml_text = api_client.get_text(
            f"{base_url}/efetch.fcgi",
            {"db": "pubmed", "id": ",".join(chunk), "retmode": "xml"},
        )
        records.update(_parse_pubmed_xml(xml_text))
    return records


def _clinical_trial_detail(config: dict, api_client: ApiClient, nct_id: str) -> dict[str, str]:
    base_url = config["clinical_trials"]["base_url"].rstrip("/")
    payload = api_client.get_json(f"{base_url}/{nct_id}", {})
    return _clinical_trials_detail(payload)


def build_evidence_details(
    config_dir: Path,
    screening_path: Path,
    output_path: Path,
) -> DetailBuildResult:
    config = load_yaml(config_dir / "search_config.yaml")
    api_client = ApiClient(HttpConfig(**config.get("http", {})))

    with screening_path.open("r", newline="", encoding="utf-8-sig") as handle:
        rows = list(csv.DictReader(handle))

    pmids = [
        str(row.get("pmid", "")).removesuffix(".0")
        for row in rows
        if str(row.get("source_database", "")) == "PubMed" and str(row.get("pmid", "")).strip()
    ]
    pubmed_records = _pubmed_details(config, api_client, list(dict.fromkeys(pmids)))

    detail_rows: list[dict[str, str]] = []
    failed_rows = 0
    for row in rows:
        source_database = _text(row.get("source_database"))
        accession = _text(row.get("source_accession")).removesuffix(".0")
        pmid = _text(row.get("pmid")).removesuffix(".0")
        detail = {field: "" for field in DETAIL_FIELDS}
        detail.update(
            {
                "evidence_id": _text(row.get("evidence_id")),
                "source_database": source_database,
                "source_accession": accession,
                "source_url": _text(row.get("source_url")),
                "title": _text(row.get("title")),
                "detail_status": "no_detail_fetch_attempted",
            }
        )
        try:
            if source_database == "PubMed" and pmid in pubmed_records:
                detail.update(pubmed_records[pmid])
                detail["detail_status"] = "ok"
            elif source_database == "ClinicalTrials.gov" and accession.startswith("NCT"):
                detail.update(_clinical_trial_detail(config, api_client, accession))
                detail["detail_status"] = "ok"
            else:
                detail["detail_status"] = "unsupported_source"
        except ApiRequestError as exc:
            failed_rows += 1
            detail["detail_status"] = f"failed: {exc}"
        detail_rows.append(detail)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=DETAIL_FIELDS)
        writer.writeheader()
        writer.writerows(detail_rows)

    return DetailBuildResult(
        input_path=screening_path,
        output_path=output_path,
        rows_read=len(rows),
        rows_written=len(detail_rows),
        failed_rows=failed_rows,
    )
