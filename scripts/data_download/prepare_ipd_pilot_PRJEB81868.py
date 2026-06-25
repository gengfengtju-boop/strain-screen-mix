"""Prepare the individual-response pilot inputs for PRJEB81868 (Whole Fiber study,
PMID 40669445): a chicory-fiber RCT in T2D/obesity with 293 deposited samples,
including 105 shotgun WGS runs that can be profiled with MetaPhlAn (no DADA2).

What is feasible from public data (this script):
  - the WGS download manifest (run -> fastq URLs + sizes), reproducibly.
  - an outcome/pairing template keyed by run, because the ENA/BioSample records do
    NOT carry subject id, timepoint, arm or anthropometrics (verified: only generic
    environment fields). Those MUST be filled from the paper supplement.

What still requires the paper supplement / authors (template columns left blank):
  - sample serial -> subject id -> timepoint -> arm mapping
  - per-subject baseline + follow-up weight / BMI / body fat (the model label)

Run:
    python scripts/data_download/prepare_ipd_pilot_PRJEB81868.py
"""
from __future__ import annotations

import csv
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = ROOT / "data/ipd_pilot"
STUDY = "PRJEB81868"
UA = {"User-Agent": "proslim-ai/1.0 (research)"}


def get(url: str, timeout: int = 60) -> str:
    return urllib.request.urlopen(
        urllib.request.Request(url, headers=UA), timeout=timeout
    ).read().decode("utf-8", "replace")


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    fields = ("run_accession,sample_accession,sample_alias,library_strategy,"
              "fastq_ftp,fastq_bytes,collection_date")
    url = (
        "https://www.ebi.ac.uk/ena/portal/api/filereport?accession="
        + STUDY + "&result=read_run&fields=" + urllib.parse.quote(fields)
        + "&format=tsv&limit=0"
    )
    lines = get(url).strip().split("\n")
    hdr = lines[0].split("\t")
    recs = [dict(zip(hdr, ln.split("\t"))) for ln in lines[1:]]
    wgs = [r for r in recs if r.get("library_strategy") == "WGS"]

    # 1) download manifest (real, actionable)
    manifest = OUT_DIR / f"{STUDY}_wgs_download_manifest.csv"
    mfields = ["run_accession", "sample_accession", "sample_alias", "sample_serial",
               "fastq_ftp", "fastq_bytes", "collection_date"]
    with manifest.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=mfields)
        w.writeheader()
        for r in sorted(wgs, key=lambda x: x.get("sample_alias", "")):
            serial = (r.get("sample_alias", "").split("_") or [""])[-1]
            w.writerow({
                "run_accession": r["run_accession"],
                "sample_accession": r["sample_accession"],
                "sample_alias": r["sample_alias"],
                "sample_serial": serial,
                "fastq_ftp": r["fastq_ftp"],
                "fastq_bytes": r["fastq_bytes"],
                "collection_date": r["collection_date"],
            })

    # 2) outcome / pairing template (to fill from the paper supplement)
    template = OUT_DIR / f"{STUDY}_subject_outcome_template.csv"
    tfields = ["run_accession", "sample_alias", "sample_serial",
               "subject_id", "arm", "timepoint",
               "weight_kg", "bmi", "body_fat_pct",
               "delta_weight_kg", "delta_bmi", "is_baseline", "source_ref"]
    with template.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=tfields)
        w.writeheader()
        for r in sorted(wgs, key=lambda x: x.get("sample_alias", "")):
            serial = (r.get("sample_alias", "").split("_") or [""])[-1]
            w.writerow({
                "run_accession": r["run_accession"],
                "sample_alias": r["sample_alias"],
                "sample_serial": serial,
                "subject_id": "", "arm": "", "timepoint": "",
                "weight_kg": "", "bmi": "", "body_fat_pct": "",
                "delta_weight_kg": "", "delta_bmi": "", "is_baseline": "",
                "source_ref": "FILL from PMID 40669445 supplement",
            })

    total_gb = sum(
        int(p) for r in wgs for p in (r.get("fastq_bytes", "") or "0").split(";")
        if p.isdigit()
    ) / 1e9
    print(f"WGS runs: {len(wgs)} | total ~{total_gb:.2f} GB")
    print("wrote", manifest.relative_to(ROOT))
    print("wrote", template.relative_to(ROOT))


if __name__ == "__main__":
    main()
