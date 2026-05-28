from pathlib import Path

from proslim_ai.export import export_ascii_safe_csv


def test_export_ascii_safe_csv_escapes_non_ascii():
    root = Path(__file__).resolve().parents[1]
    input_path = root / "tests" / "fixtures" / "non_ascii.csv"
    output_path = root / "tests" / "fixtures" / "non_ascii.out.csv"

    try:
        rows = export_ascii_safe_csv(input_path, output_path)
        content = output_path.read_text(encoding="utf-8")

        assert rows == 1
        assert "SF68&#174; probiotic" in content
    finally:
        output_path.unlink(missing_ok=True)

