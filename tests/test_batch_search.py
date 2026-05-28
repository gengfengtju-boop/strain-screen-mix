from pathlib import Path

import pandas as pd

from proslim_ai.batch_search import run_batch_search


def test_run_batch_search_writes_manifest(monkeypatch):
    root = Path(__file__).resolve().parents[1]
    manifest = root / "tests" / "fixtures" / "search_manifest.out.csv"

    def fake_search_evidence(**kwargs):
        return 2

    def fake_search_genomes(**kwargs):
        return 3

    monkeypatch.setattr("proslim_ai.batch_search.search_evidence", fake_search_evidence)
    monkeypatch.setattr("proslim_ai.batch_search.search_genomes", fake_search_genomes)

    try:
        results = run_batch_search(
            root=root,
            config_path=root / "tests" / "fixtures" / "search_batch_test.yaml",
            manifest_path=manifest,
            curator="tester",
        )

        assert [result.status for result in results] == ["ok", "ok"]
        assert [result.records_written for result in results] == [2, 3]

        frame = pd.read_csv(manifest)
        assert len(frame) == 2
        assert set(frame["status"]) == {"ok"}
    finally:
        manifest.unlink(missing_ok=True)

