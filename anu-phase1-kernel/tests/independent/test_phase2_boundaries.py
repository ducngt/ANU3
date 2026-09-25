from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_phase2_migration_is_additive_and_versioned():
    migration = (ROOT / "migrations/versions/0003_reality_data_memory.py").read_text(encoding="utf-8")
    assert 'revision = "0003"' in migration
    assert 'down_revision = "0002"' in migration
    for table in [
        "source_registry",
        "source_authority_mapping",
        "data_contract_version",
        "data_object_version",
        "knowledge_object_version",
        "university_memory_record",
    ]:
        assert f'"{table}"' in migration


def test_source_authority_and_epistemic_fail_closed_guards_exist():
    repository = (ROOT / "src/anu_kernel/reality_repository.py").read_text(encoding="utf-8")
    contracts = (ROOT / "src/anu_kernel/reality_contracts.py").read_text(encoding="utf-8")
    assert "SOURCE_AUTHORITY_REQUIRED" in repository
    assert "EPISTEMIC_TYPE_MUTATION_FORBIDDEN" in repository
    assert "SYNTHETIC OUTPUT != AUTHORITATIVE EVIDENCE/FACT/DECISION" in contracts


def test_university_memory_is_trace_index_not_shadow_source():
    contracts = (ROOT / "src/anu_kernel/reality_contracts.py").read_text(encoding="utf-8")
    adr = (ROOT / "docs/adr/ADR-0004-reality-source-epistemic.md").read_text(encoding="utf-8")
    assert "source_ref: str" in contracts
    assert "provenance_ref: str" in contracts
    assert "does not become a competing source-of-record" in adr
