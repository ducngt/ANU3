from pathlib import Path

import pytest

from anu_kernel.contracts import AuthorityGrantContract, AuthorityScope, EffectivePeriod, SubjectType


def test_agent_standing_authority_guard_exists_at_contract_boundary():
    with pytest.raises(ValueError, match="AGENT IDENTITY"):
        AuthorityGrantContract(
            authority_id="urn:anu:authority:forbidden",
            subject_ref="urn:anu:agent:qa-01",
            subject_type=SubjectType.AGENT,
            authority_type="academic.programme.approve",
            basis_ref="urn:anu:basis:test",
            issuer_ref="urn:anu:org:aru",
            scope=AuthorityScope(resource="urn:anu:programme:software-engineering"),
            consequence_class="ACADEMIC_CONSEQUENCE",
            effective_period=EffectivePeriod(valid_from="2026-01-01T00:00:00Z"),
        )


def test_runtime_does_not_silently_create_schema():
    api_text = Path("src/anu_kernel/api.py").read_text()
    assert "Base.metadata.create_all" not in api_text


def test_repository_does_not_ship_runtime_sqlite_database():
    assert not Path("anu_kernel.db").exists()
