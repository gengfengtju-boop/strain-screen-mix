from __future__ import annotations

import argparse
import csv
import hashlib
import re
from difflib import SequenceMatcher
from pathlib import Path

from pypdf import PdfReader


TITLE_STOPWORDS = {
    "a", "an", "and", "of", "on", "in", "the", "to", "with", "for", "by", "from",
    "article", "original", "research", "full", "text", "supplementary", "reference",
}


def clean(value: object) -> str:
    return re.sub(r"\s+", " ", "" if value is None else str(value)).strip()


def normalized_title(value: str) -> str:
    words = re.findall(r"[a-z0-9]+", clean(value).lower())
    return " ".join(word for word in words if word not in TITLE_STOPWORDS)


def title_tokens(value: str) -> set[str]:
    return {word for word in normalized_title(value).split() if len(word) > 2}


def title_score(left: str, right: str) -> float:
    left_norm = normalized_title(left)
    right_norm = normalized_title(right)
    if not left_norm or not right_norm:
        return 0.0
    sequence = SequenceMatcher(None, left_norm, right_norm).ratio()
    left_tokens = title_tokens(left)
    right_tokens = title_tokens(right)
    union = left_tokens | right_tokens
    jaccard = len(left_tokens & right_tokens) / len(union) if union else 0.0
    containment = len(left_tokens & right_tokens) / min(len(left_tokens), len(right_tokens))
    return round(max(sequence, 0.65 * containment + 0.35 * jaccard), 3)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def first_page_text(path: Path) -> tuple[str, str, str]:
    reader = PdfReader(path)
    metadata_title = clean((reader.metadata or {}).get("/Title", ""))
    page_text = reader.pages[0].extract_text() or "" if reader.pages else ""
    return metadata_title, page_text, str(len(reader.pages))


def title_from_page(metadata_title: str, text: str, filename: str) -> str:
    bad_metadata = {"", "untitled", "full text", "article", "microsoft word"}
    if (
        metadata_title.lower() not in bad_metadata
        and len(metadata_title) >= 25
        and len(title_tokens(metadata_title)) >= 5
    ):
        return metadata_title[:500]
    filename_title = clean(Path(filename).stem.replace("_", " "))
    if len(title_tokens(filename_title)) >= 8:
        return filename_title[:500]
    lines = [clean(line) for line in re.split(r"[\r\n]+", text) if clean(line)]
    abstract_index = next((index for index, line in enumerate(lines) if line.lower() == "abstract"), 35)
    title_lines = lines[: min(abstract_index, 35)]
    candidates: list[str] = []
    bad_terms = (
        "copyright", "creative commons", "licence", "license", "department of", "university",
        "correspondence", "received", "accepted", "published", "http", "www.", "doi:", "volume ",
        "author", "affiliation", "email", "@", "springer nature", "rights reserved",
    )
    for start in range(len(title_lines)):
        for width in range(1, 5):
            candidate = clean(" ".join(title_lines[start : start + width]))
            lower = candidate.lower()
            if not 35 <= len(candidate) <= 450 or any(term in lower for term in bad_terms):
                continue
            if len(re.findall(r"[A-Za-z]", candidate)) >= 25 and len(title_tokens(candidate)) >= 5:
                candidates.append(candidate)
    if candidates:
        title_terms = ("effect", "effects", "trial", "study", "microbi", "obesity", "overweight", "probiotic", "prebiotic", "diet")
        return max(
            candidates,
            key=lambda item: (
                sum(term in item.lower() for term in title_terms) * 8
                + min(len(title_tokens(item)), 30)
                - max(0, len(item) - 300) / 20
            ),
        )
    return filename_title


def read_csv_title(path: Path) -> tuple[str, str, str]:
    with path.open(encoding="utf-8-sig", errors="replace", newline="") as handle:
        rows = list(csv.DictReader(handle))
    if not rows:
        return "", "", "csv"
    row = rows[0]
    title = clean(row.get("Study Title") or row.get("Brief Title") or row.get("Official Title"))
    return title, clean(" ".join(str(value) for value in row.values())), "csv"


def load_candidates(paths: list[Path]) -> list[dict[str, str]]:
    candidates: dict[str, dict[str, str]] = {}
    for path in paths:
        if not path.exists():
            continue
        with path.open(encoding="utf-8-sig", newline="") as handle:
            for row in csv.DictReader(handle):
                evidence_id = clean(row.get("evidence_id"))
                title = clean(row.get("title"))
                if evidence_id and title and evidence_id not in candidates:
                    candidates[evidence_id] = {
                        "evidence_id": evidence_id,
                        "source_accession": clean(row.get("source_accession")),
                        "doi": clean(row.get("doi")),
                        "title": title,
                        "table_kind": path.stem,
                    }
    return list(candidates.values())


def identifier_match(text: str, candidates: list[dict[str, str]]) -> dict[str, str] | None:
    nct = re.search(r"\bNCT\d{8}\b", text, re.I)
    pmid = re.search(r"\bPMID\s*[:#]?\s*(\d{7,9})\b", text, re.I)
    doi = re.search(r"\b10\.\d{4,9}/[-._;()/:A-Z0-9]+", text, re.I)
    identifiers = [nct.group(0).upper()] if nct else []
    if pmid:
        identifiers.append(pmid.group(1))
    if doi:
        identifiers.append(doi.group(0).rstrip(".,;)").lower())
    for identifier in identifiers:
        for candidate in candidates:
            haystack = f"{candidate['evidence_id']} {candidate['source_accession']} {candidate['doi']}"
            if identifier.lower() in haystack.lower():
                return candidate
    return None


def best_match(title: str, text: str, candidates: list[dict[str, str]]) -> tuple[dict[str, str], float]:
    exact = identifier_match(text, candidates)
    if exact:
        return exact, 1.0
    scored = [(title_score(title, candidate["title"]), candidate) for candidate in candidates]
    score, candidate = max(scored, key=lambda item: item[0])
    return candidate, score


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-dir", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True, help="Text file with one source filename per line.")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--candidate", action="append", type=Path, default=[])
    args = parser.parse_args()

    names = [line.strip() for line in args.manifest.read_text(encoding="utf-8-sig").splitlines() if line.strip()]
    candidates = load_candidates(args.candidate)
    rows: list[dict[str, str]] = []
    hash_counts: dict[str, int] = {}
    source_rows: list[tuple[Path, str, str, str, str, str]] = []
    for name in names:
        path = args.source_dir / name
        if not path.exists():
            rows.append({"file_name": name, "file_path": str(path), "parse_status": "missing"})
            continue
        file_hash = sha256(path)
        hash_counts[file_hash] = hash_counts.get(file_hash, 0) + 1
        try:
            if path.suffix.lower() == ".pdf":
                metadata_title, text, pages = first_page_text(path)
                title = title_from_page(metadata_title, text, name)
                file_type = "pdf"
            else:
                title, text, pages = read_csv_title(path)
                file_type = "csv"
            source_rows.append((path, file_hash, file_type, title, text, pages))
        except Exception as exc:  # noqa: BLE001
            rows.append({
                "file_name": name, "file_path": str(path), "file_type": path.suffix.lower().lstrip("."),
                "parse_status": "error", "error": str(exc), "sha256": file_hash,
            })

    for path, file_hash, file_type, title, text_value, pages in source_rows:
        candidate, score = best_match(title, f"{path.name} {title} {text_value[:12000]}", candidates)
        rows.append({
            "file_name": path.name,
            "file_path": str(path),
            "file_type": file_type,
            "parse_status": "ok",
            "pages": pages,
            "sha256": file_hash,
            "exact_duplicate_count": str(hash_counts[file_hash]),
            "is_exact_duplicate": "yes" if hash_counts[file_hash] > 1 else "no",
            "extracted_title": title,
            "matched_evidence_id": candidate["evidence_id"],
            "matched_source_accession": candidate["source_accession"],
            "matched_title": candidate["title"],
            "match_score": f"{score:.3f}",
            "matched_table_kind": candidate["table_kind"],
            "text_excerpt": clean(text_value)[:1800],
            "error": "",
        })

    fields: list[str] = []
    for row in rows:
        for field in row:
            if field not in fields:
                fields.append(field)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    print(f"{args.output}\trows={len(rows)}\tunique_hashes={len(hash_counts)}")


if __name__ == "__main__":
    main()
