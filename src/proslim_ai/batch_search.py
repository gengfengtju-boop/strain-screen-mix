from __future__ import annotations

import csv
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from .config import load_yaml
from .search import search_evidence, search_genomes
from .search_clients import ApiRequestError


@dataclass(frozen=True)
class BatchJobResult:
    name: str
    command: str
    query: str
    output: str
    status: str
    records_written: int
    error: str


def _run_job(root: Path, config_dir: Path, job: dict[str, Any], curator: str) -> BatchJobResult:
    name = str(job["name"])
    command = str(job["command"])
    query = str(job["query"])
    output = str(job["output"])
    output_path = root / output
    retmax = int(job.get("retmax", 20))
    try:
        if command == "search_evidence":
            count = search_evidence(
                config_dir=config_dir,
                query=query,
                output_path=output_path,
                source=str(job["source"]),
                retmax=retmax,
                curator=curator,
            )
        elif command == "search_genomes":
            count = search_genomes(
                config_dir=config_dir,
                query=query,
                output_path=output_path,
                retmax=retmax,
                curator=curator,
            )
        else:
            raise ValueError(f"Unknown batch command: {command}")
        return BatchJobResult(name, command, query, output, "ok", count, "")
    except (ApiRequestError, ValueError, KeyError) as exc:
        return BatchJobResult(name, command, query, output, "failed", 0, str(exc))


def run_batch_search(
    root: Path,
    config_path: Path,
    manifest_path: Path,
    curator: str = "auto_search",
) -> list[BatchJobResult]:
    batch_config = load_yaml(config_path)
    jobs = batch_config.get("jobs", [])
    if not isinstance(jobs, list):
        raise ValueError("search batch config must contain a list named 'jobs'.")

    results = [_run_job(root, root / "config", job, curator) for job in jobs]

    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    with manifest_path.open("w", newline="", encoding="utf-8") as handle:
        fieldnames = [
            "run_timestamp",
            "name",
            "command",
            "query",
            "output",
            "status",
            "records_written",
            "error",
        ]
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        timestamp = datetime.now().isoformat(timespec="seconds")
        for result in results:
            writer.writerow({"run_timestamp": timestamp, **result.__dict__})
    return results

