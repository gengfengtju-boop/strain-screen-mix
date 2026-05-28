from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class EvidenceLinkValidationResult:
    strain_table_path: Path
    evidence_registry_path: Path
    rows_checked: int
    missing_links: list[str]

    @property
    def ok(self) -> bool:
        return not self.missing_links


def _split_identifiers(value: object) -> list[str]:
    import re

    if value is None:
        return []
    text = str(value).strip()
    if not text or text.lower() in {"na", "nan", "none", "unknown"}:
        return []
    return [item.strip() for item in re.split(r"[;,|]", text) if item.strip()]


def _registry_identifiers(registry_path: Path) -> tuple[set[str], set[str]]:
    import pandas as pd

    frame = pd.read_csv(registry_path).fillna("")
    dois: set[str] = set()
    pmids: set[str] = set()
    for _, row in frame.iterrows():
        dois.update(identifier.lower() for identifier in _split_identifiers(row.get("doi")))
        pmids.update(_split_identifiers(row.get("pmid")))
    return dois, pmids


def validate_strain_evidence_links(
    strain_table_path: Path,
    evidence_registry_path: Path,
) -> EvidenceLinkValidationResult:
    import pandas as pd

    registry_dois, registry_pmids = _registry_identifiers(evidence_registry_path)
    strain_frame = pd.read_csv(strain_table_path).fillna("")
    missing_links: list[str] = []

    for index, row in strain_frame.iterrows():
        row_number = index + 2
        strain_id = str(row.get("strain_id", "")).strip() or f"row {row_number}"
        for doi in _split_identifiers(row.get("evidence_doi")):
            if doi.lower() not in registry_dois:
                missing_links.append(f"row {row_number} ({strain_id}): DOI not in evidence_registry: {doi}")
        for pmid in _split_identifiers(row.get("evidence_pmid")):
            if pmid not in registry_pmids:
                missing_links.append(f"row {row_number} ({strain_id}): PMID not in evidence_registry: {pmid}")

    return EvidenceLinkValidationResult(
        strain_table_path=strain_table_path,
        evidence_registry_path=evidence_registry_path,
        rows_checked=len(strain_frame),
        missing_links=missing_links,
    )

