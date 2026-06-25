"""Discover candidate studies for individual-level (IPD) response modeling.

Strategy: an individual probiotic-response model needs per-subject baseline
microbiome + per-subject outcome. The only public path is intervention RCTs that
deposited per-sample sequencing (16S / shotgun) under a BioProject / ENA / SRA
study. This script searches EuropePMC for interventional probiotic+obesity
microbiota trials, then queries the EuropePMC datalinks API per article to find
deposited sequencing accessions. Output is a triage queue, NOT a finished IPD set:
each hit still needs manual confirmation that baseline and follow-up samples are
paired per subject and that individual weight/adiposity outcomes are recoverable.
"""
from __future__ import annotations

import json
import re
import time
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = ROOT / "data/ipd_search"
UA = {"User-Agent": "proslim-ai/1.0 (research)"}

QUERY = (
    "(probiotic OR synbiotic OR Lactobacillus OR Bifidobacterium OR Lactiplantibacillus) "
    'AND (obesity OR overweight OR "body weight" OR BMI OR "body fat" OR adiposity) '
    "AND (16S OR metagenom* OR shotgun OR microbiota OR microbiome) "
    "AND (randomi* OR placebo OR intervention OR trial) "
    'AND NOT (PUB_TYPE:"review-article" OR PUB_TYPE:"review")'
)
MAX_PMIDS = 100
SEQ_HINTS = ("bioproject", "nucleotide", "sequence read", "european nucleotide",
             "ena", "sra", "gene expression omnibus", "biostudies", "metagenom")
ACC = re.compile(r"\b(PRJNA\d+|PRJEB\d+|PRJDB\d+|SRP\d{5,}|ERP\d{5,}|DRP\d{5,}|GSE\d{4,})\b")


def get(url: str, timeout: int = 50) -> str:
    return urllib.request.urlopen(
        urllib.request.Request(url, headers=UA), timeout=timeout
    ).read().decode("utf-8", "replace")


def search_pmids() -> list[dict]:
    out: list[dict] = []
    cursor = "*"
    while len(out) < MAX_PMIDS:
        url = (
            "https://www.ebi.ac.uk/europepmc/webservices/rest/search?query="
            + urllib.parse.quote(QUERY)
            + "&format=json&pageSize=100&resultType=lite&cursorMark="
            + urllib.parse.quote(cursor)
        )
        j = json.loads(get(url))
        res = j.get("resultList", {}).get("result", [])
        if not res:
            break
        for r in res:
            if r.get("pmid"):
                out.append({
                    "pmid": r["pmid"], "year": r.get("pubYear", ""),
                    "title": (r.get("title", "") or "").replace("\n", " "),
                    "is_open_access": r.get("isOpenAccess", ""),
                })
        nxt = j.get("nextCursorMark")
        if not nxt or nxt == cursor:
            break
        cursor = nxt
        time.sleep(0.2)
    return out[:MAX_PMIDS]


def datalinks(pmid: str) -> tuple[list[str], list[str]]:
    """Return (sequencing_accessions, repository_names) for a PMID."""
    url = f"https://www.ebi.ac.uk/europepmc/webservices/rest/MED/{pmid}/datalinks?format=json"
    try:
        j = json.loads(get(url, timeout=40))
    except Exception:
        return [], []
    accs: set[str] = set()
    repos: set[str] = set()
    for cat in j.get("dataLinkList", {}).get("Category", []):
        name = str(cat.get("Name", ""))
        low = name.lower()
        is_seq = any(h in low for h in SEQ_HINTS)
        for sec in cat.get("Section", []):
            for ln in sec.get("Linklist", {}).get("Link", []):
                tgt = ln.get("Target", {})
                ident = str(tgt.get("Identifier", {}).get("ID", "") or "")
                title = str(tgt.get("Title", "") or "")
                found = ACC.findall(ident + " " + title)
                if found:
                    accs.update(found)
                    repos.add(name)
                elif is_seq and ("bioproject" in low or "nucleotide" in low
                                 or "sequence read" in low):
                    repos.add(name)
    return sorted(accs), sorted(repos)


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    studies = search_pmids()
    candidates = []
    for i, s in enumerate(studies):
        accs, repos = datalinks(s["pmid"])
        if accs or any("bioproject" in r.lower() or "nucleotide" in r.lower()
                       or "sequence read" in r.lower() for r in repos):
            s["sequencing_accessions"] = "; ".join(accs)
            s["repositories"] = "; ".join(repos)
            s["triage_status"] = "needs_manual_pairing_check"
            s["ipd_requirement"] = (
                "confirm per-subject baseline+followup sample pairing and recoverable "
                "individual adiposity outcome before use"
            )
            candidates.append(s)
        time.sleep(0.12)

    fields = ["pmid", "year", "title", "is_open_access", "sequencing_accessions",
              "repositories", "triage_status", "ipd_requirement"]
    out_csv = OUT_DIR / "ipd_candidate_studies_20260625.csv"
    import csv
    with out_csv.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for c in sorted(candidates, key=lambda x: str(x["year"]), reverse=True):
            w.writerow({k: c.get(k, "") for k in fields})

    summary = {
        "run_stamp": "20260625",
        "query": QUERY,
        "pmids_screened": len(studies),
        "candidates_with_sequencing_deposit": len(candidates),
        "with_extractable_accession": sum(1 for c in candidates if c["sequencing_accessions"]),
        "method": "EuropePMC search + per-article datalinks API (BioProject/ENA/SRA)",
        "limitation": (
            "Datalinks presence does not guarantee per-subject paired baseline+outcome "
            "design; each candidate requires manual confirmation. Studies without a "
            "deposit are not IPD-usable from public data."
        ),
        "output": str(out_csv.relative_to(ROOT)).replace("\\", "/"),
    }
    out_json = OUT_DIR / "ipd_candidate_search_summary_20260625.json"
    out_json.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    print("screened:", len(studies), "candidates:", len(candidates),
          "with_accession:", summary["with_extractable_accession"])
    print("wrote", out_csv.relative_to(ROOT))
    print("wrote", out_json.relative_to(ROOT))


if __name__ == "__main__":
    main()
