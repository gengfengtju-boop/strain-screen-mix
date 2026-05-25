from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path

from .config import load_table_schemas
from .paths import REQUIRED_CONFIG_FILES, REQUIRED_DIRECTORIES, ProjectPaths


@dataclass(frozen=True)
class CheckResult:
    missing_directories: list[str]
    missing_config_files: list[str]

    @property
    def ok(self) -> bool:
        return not self.missing_directories and not self.missing_config_files


def check_project(paths: ProjectPaths) -> CheckResult:
    missing_dirs = [
        rel_path for rel_path in REQUIRED_DIRECTORIES if not (paths.root / rel_path).is_dir()
    ]
    missing_configs = [
        rel_path for rel_path in REQUIRED_CONFIG_FILES if not (paths.config / rel_path).is_file()
    ]
    return CheckResult(missing_dirs, missing_configs)


def write_template_tables(paths: ProjectPaths, overwrite: bool = False) -> list[Path]:
    schemas = load_table_schemas(paths.config)
    template_dir = paths.data / "metadata" / "templates"
    template_dir.mkdir(parents=True, exist_ok=True)

    written: list[Path] = []
    for table_name, columns in schemas.items():
        output_path = template_dir / f"{table_name}.csv"
        if output_path.exists() and not overwrite:
            continue
        with output_path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.writer(handle)
            writer.writerow(columns)
        written.append(output_path)
    return written

