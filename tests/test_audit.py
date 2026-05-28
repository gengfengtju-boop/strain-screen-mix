from pathlib import Path

from proslim_ai.audit import audit_project


def test_audit_project_passes_for_current_repository():
    root = Path(__file__).resolve().parents[1]

    result = audit_project(root)

    assert result.ok
    assert not result.template_errors
    assert not result.source_registry_errors

