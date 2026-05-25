from pathlib import Path

from proslim_ai.paths import REQUIRED_CONFIG_FILES, REQUIRED_DIRECTORIES


def test_required_directories_exist():
    root = Path(__file__).resolve().parents[1]
    missing = [item for item in REQUIRED_DIRECTORIES if not (root / item).is_dir()]
    assert not missing


def test_required_config_files_exist():
    root = Path(__file__).resolve().parents[1]
    missing = [item for item in REQUIRED_CONFIG_FILES if not (root / "config" / item).is_file()]
    assert not missing

