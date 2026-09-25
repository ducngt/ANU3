from __future__ import annotations

from datetime import datetime, timezone
import pytest

from anu_kernel.contracts import AuthorityGrantContract, AuthorityScope, EffectivePeriod, SubjectType


def dt(s: str) -> datetime:
    return datetime.fromisoformat(s.replace("Z", "+00:00"))


def test_agent_identity_cannot_receive_standing_authority():
    with pytest.raises(ValueError, match="AGENT IDENTITY"):
        AuthorityGrantContract(
            authority_id="urn:anu:authority:a1",
            subject_ref="urn:anu:agent:x",
            subject_type=SubjectType.AGENT,
            authority_type="academic.programme.approve",
            basis_ref="urn:anu:basis:x",
            issuer_ref="urn:anu:org:aru",
            scope=AuthorityScope(resource="urn:anu:programme:software-engineering", action="academic.programme.approve"),
            consequence_class="ACADEMIC_CONSEQUENCE",
            effective_period=EffectivePeriod(valid_from=dt("2026-01-01T00:00:00Z")),
        )
