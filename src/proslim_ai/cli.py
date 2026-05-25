from __future__ import annotations

import argparse
from pathlib import Path

from .modules import MODULES
from .paths import ProjectPaths, find_project_root
from .project import check_project, write_template_tables


def _paths(root: str | None) -> ProjectPaths:
    return ProjectPaths(find_project_root(Path(root)) if root else find_project_root())


def cmd_check(args: argparse.Namespace) -> int:
    paths = _paths(args.root)
    result = check_project(paths)
    print(f"Project root: {paths.root}")
    if result.ok:
        print("OK: required directories and config files are present.")
        return 0

    if result.missing_directories:
        print("Missing directories:")
        for item in result.missing_directories:
            print(f"  - {item}")
    if result.missing_config_files:
        print("Missing config files:")
        for item in result.missing_config_files:
            print(f"  - config/{item}")
    return 1


def cmd_modules(args: argparse.Namespace) -> int:
    for index, module in enumerate(MODULES, start=1):
        print(f"{index}. {module.name} - {module.title}")
        print(f"   dir: {module.script_dir}")
        print(f"   outputs: {', '.join(module.expected_outputs)}")
    return 0


def cmd_templates(args: argparse.Namespace) -> int:
    paths = _paths(args.root)
    written = write_template_tables(paths, overwrite=args.overwrite)
    if not written:
        print("No templates written; files already exist.")
        return 0
    print("Written template tables:")
    for path in written:
        print(f"  - {path}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="proslim-ai",
        description="ProSlim-Microbiome-AI project utility CLI.",
    )
    parser.add_argument("--root", help="Project root directory. Defaults to current project.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    check = subparsers.add_parser("check", help="Check required project structure.")
    check.set_defaults(func=cmd_check)

    modules = subparsers.add_parser("modules", help="List pipeline modules.")
    modules.set_defaults(func=cmd_modules)

    templates = subparsers.add_parser("write-templates", help="Write CSV header templates.")
    templates.add_argument("--overwrite", action="store_true", help="Overwrite existing templates.")
    templates.set_defaults(func=cmd_templates)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)

