"""Step 1 — map each screening-catalog species to an NCBI reference/representative genome.

Queries the NCBI Datasets API v2 for a reference genome (falls back to the best available
assembly). MAG-only taxa (e.g. '..._sp_CAG_303') usually have no isolate genome and are
flagged. Writes the catalog with genome_accession + assembly_level columns.

    PYTHONPATH=src python scripts/strain_annotation/map_genomes_step1.py
"""
from __future__ import annotations

import json
import ssl
import time
import urllib.parse
import urllib.request
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
CAT = ROOT / "results/candidate_strain_scores/strain_screening_catalog_20260613.csv"
OUT = ROOT / "results/candidate_strain_scores/strain_screening_catalog_genomes_20260613.csv"

CTX = ssl.create_default_context()
CTX.check_hostname = False
CTX.verify_mode = ssl.CERT_NONE
API = "https://api.ncbi.nlm.nih.gov/datasets/v2/genome/taxon/{}/dataset_report?{}"


def _query(taxon: str, reference_only: bool) -> dict | None:
    params = {"page_size": "1"}
    if reference_only:
        params["filters.reference_only"] = "true"
    url = API.format(urllib.parse.quote(taxon), urllib.parse.urlencode(params))
    for attempt in range(3):
        try:
            with urllib.request.urlopen(url, timeout=30, context=CTX) as resp:
                reports = json.load(resp).get("reports") or []
                return reports[0] if reports else None
        except Exception:
            time.sleep(1 + attempt)
    return "ERROR"  # network failure sentinel


def _species_query(name: str) -> str | None:
    # 'Akkermansia_muciniphila' -> 'Akkermansia muciniphila'; skip MAG placeholders
    parts = name.split("_")
    if len(parts) < 2 or parts[1] in {"sp", "bacterium"} or "CAG" in name:
        return None
    return f"{parts[0]} {parts[1]}"


def main() -> None:
    cat = pd.read_csv(CAT)
    acc, lvl, src = [], [], []
    n = len(cat)
    for i, name in enumerate(cat["species"], 1):
        q = _species_query(str(name))
        if q is None:
            acc.append("")
            lvl.append("no_isolate_genome_MAG_or_unresolved")
            src.append("")
            continue
        rep = _query(q, reference_only=True)
        if rep in (None,):  # no reference -> any assembly
            rep = _query(q, reference_only=False)
        if rep == "ERROR" or rep is None:
            acc.append("")
            lvl.append("not_found_or_network")
            src.append(q)
        else:
            acc.append(rep.get("accession", ""))
            lvl.append(rep.get("assembly_info", {}).get("assembly_level", ""))
            src.append(rep.get("organism", {}).get("organism_name", ""))
        if i % 25 == 0:
            print(f"  {i}/{n} queried...")
        time.sleep(0.34)  # ~3 req/s (NCBI no-key limit)

    cat["genome_accession"] = acc
    cat["assembly_level"] = lvl
    cat["resolved_organism"] = src
    cat.to_csv(OUT, index=False)
    got = sum(bool(a) for a in acc)
    print(f"\nGenomes mapped: {got}/{n}")
    print("assembly levels:", cat["assembly_level"].value_counts().to_dict())
    print(f"Output: {OUT}")


if __name__ == "__main__":
    main()
