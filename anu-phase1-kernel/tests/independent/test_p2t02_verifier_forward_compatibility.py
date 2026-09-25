from __future__ import annotations

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def _load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_p2t02_schema_export_verifier_allows_additive_schema_growth():
    source = (ROOT / "scripts" / "verify_p2t02_p3.py").read_text(encoding="utf-8")
    assert '"exported 50 schemas" in schemas.stdout' not in source
    assert "exported_count >= 50" in source
    assert "missing_baseline_schemas" in source


def test_p2t02_postgres_evidence_accepts_later_additive_head():
    verifier = _load_module(
        ROOT / "scripts" / "verify_p2t02_p3_postgres_evidence.py",
        "verify_p2t02_p3_postgres_evidence",
    )
    checks = {name: True for name in verifier.REQUIRED}
    payload = {
        "status": "PASS",
        "baseline_revision": "0004",
        "database_revision": "0005",
        "synthetic_data_only": True,
        "checks": checks,
    }
    qualified, missing, failed = verifier.qualify(payload)
    assert qualified is True
    assert missing == []
    assert failed == []


def test_phase2_workflow_tracks_repository_head_instead_of_pinning_0004():
    workflow = (ROOT.parent / ".github" / "workflows" / "phase2-verify.yml").read_text(encoding="utf-8")
    assert 'test "$(alembic current | awk' not in workflow
    assert 'HEAD="$(alembic heads' in workflow
    assert 'test "$CURRENT" = "$HEAD"' in workflow
