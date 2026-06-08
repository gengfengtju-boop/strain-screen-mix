from __future__ import annotations

import csv
import re
from dataclasses import dataclass
from pathlib import Path


ENRICHED_FIELDS = [
    "evidence_id",
    "source_database",
    "source_accession",
    "title",
    "intervention_type_hint",
    "taxa_hint",
    "enriched_intervention_type_hint",
    "enriched_taxa_hint",
    "enrichment_source",
    "study_tag",
    "priority",
    "relevance_score",
    "preliminary_response_score",
    "confidence_level",
    "predicted_usefulness",
    "main_positive_signals",
    "main_limitations",
    "source_url",
]


INTERVENTION_PATTERNS = {
    "probiotic": ["probiotic", "probiotics", "lactobacillus", "bifidobacterium", "bacillus coagulans"],
    "prebiotic": ["prebiotic", "prebiotics", "inulin", "fos", "fructo-oligosaccharide", "fiber", "polydextrose"],
    "synbiotic": ["synbiotic", "synbiotics"],
    "postbiotic": ["postbiotic", "postbiotics", "heat-killed", "pasteurized"],
    "dietary_polyphenol": ["green tea", "catechin", "tea", "polyphenol"],
}


TAXA_PATTERNS = [
    "Lactobacillus",
    "Lacticaseibacillus",
    "Lactiplantibacillus",
    "Limosilactobacillus",
    "Bifidobacterium",
    "Akkermansia",
    "Bacillus",
    "Saccharomyces",
    "Streptococcus",
    "Enterococcus",
    "Coprococcus",
]


STRAIN_PATTERNS = [
    r"\b[A-Z]{1,5}[- ]?\d{2,5}[A-Za-z-]*\b",
    r"\bDSM\s*\d+\b",
    r"\bBB\d+\b",
    r"\bBC\d+\b",
    r"\bIDCC\s*\d+\b",
    r"\bBBr\d+\b",
    r"\bKABP\d+\b",
    r"\bUA\d+\b",
]


@dataclass(frozen=True)
class EnrichmentResult:
    prediction_path: Path
    output_path: Path
    rows_read: int
    rows_written: int
    intervention_filled: int
    taxa_filled: int


def enrich_prediction_hints(
    prediction_path: Path,
    details_paths: list[Path],
    output_path: Path,
) -> EnrichmentResult:
    detail_text_by_id = _load_detail_text(details_paths)
    output_rows: list[dict[str, str]] = []
    intervention_filled = 0
    taxa_filled = 0

    with prediction_path.open("r", newline="", encoding="utf-8-sig") as handle:
        rows = list(csv.DictReader(handle))

    for row in rows:
        evidence_id = _text(row.get("evidence_id"))
        detail_text = detail_text_by_id.get(evidence_id, "")
        text = " ".join([_text(row.get("title")), detail_text])
        enriched_intervention = _join_unique(
            [_text(row.get("intervention_type_hint")), *_infer_interventions(text)]
        )
        enriched_taxa = _join_unique([_text(row.get("taxa_hint")), *_infer_taxa(text)])
        if not _text(row.get("intervention_type_hint")) and enriched_intervention:
            intervention_filled += 1
        if not _text(row.get("taxa_hint")) and enriched_taxa:
            taxa_filled += 1
        enrichment_source = []
        if detail_text:
            enrichment_source.append("evidence_details")
        if enriched_intervention != _text(row.get("intervention_type_hint")) or enriched_taxa != _text(row.get("taxa_hint")):
            enrichment_source.append("regex_inference")
        output_rows.append(
            {
                **{field: _text(row.get(field)) for field in ENRICHED_FIELDS if field not in {"enriched_intervention_type_hint", "enriched_taxa_hint", "enrichment_source"}},
                "enriched_intervention_type_hint": enriched_intervention,
                "enriched_taxa_hint": enriched_taxa,
                "enrichment_source": "; ".join(enrichment_source),
            }
        )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=ENRICHED_FIELDS)
        writer.writeheader()
        writer.writerows(output_rows)

    return EnrichmentResult(
        prediction_path=prediction_path,
        output_path=output_path,
        rows_read=len(rows),
        rows_written=len(output_rows),
        intervention_filled=intervention_filled,
        taxa_filled=taxa_filled,
    )


def _load_detail_text(paths: list[Path]) -> dict[str, str]:
    details: dict[str, str] = {}
    for path in paths:
        if not path.exists():
            continue
        with path.open("r", newline="", encoding="utf-8-sig") as handle:
            for row in csv.DictReader(handle):
                evidence_id = _text(row.get("evidence_id"))
                if not evidence_id:
                    continue
                details[evidence_id] = " ".join(
                    [
                        details.get(evidence_id, ""),
                        _text(row.get("title")),
                        _text(row.get("abstract")),
                        _text(row.get("clinical_interventions")),
                        _text(row.get("primary_outcomes")),
                        _text(row.get("secondary_outcomes")),
                        _text(row.get("arms")),
                    ]
                )
    return details


def _infer_interventions(text: str) -> list[str]:
    lowered = text.lower()
    matches: list[str] = []
    for label, terms in INTERVENTION_PATTERNS.items():
        if any(term in lowered for term in terms):
            matches.append(label)
    return matches


def _infer_taxa(text: str) -> list[str]:
    matches: list[str] = []
    for genus in TAXA_PATTERNS:
        species_pattern = re.compile(rf"\b({re.escape(genus)})\s+([a-z][a-z-]+)\b", re.IGNORECASE)
        species_matches = [f"{item[0]} {item[1]}" for item in species_pattern.findall(text)]
        if species_matches:
            matches.extend(species_matches)
        elif re.search(rf"\b{re.escape(genus)}\b", text, re.IGNORECASE):
            matches.append(genus)
    for pattern in STRAIN_PATTERNS:
        matches.extend(re.findall(pattern, text))
    return matches


def _join_unique(values: list[str]) -> str:
    parts: list[str] = []
    for value in values:
        for item in _text(value).split(";"):
            item = item.strip()
            if item:
                parts.append(item)
    return "; ".join(dict.fromkeys(parts))


def _text(value: object) -> str:
    return "" if value is None else " ".join(str(value).split())
