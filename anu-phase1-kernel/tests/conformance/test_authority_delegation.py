from __future__ import annotations

from datetime import datetime
import pytest

from anu_kernel.contracts import (
    AuthorityEvaluationRequest,
    AuthorityGrantContract,
    AuthorityScope,
    CompetenceAssertionContract,
    DelegationGrantContract,
    EffectivePeriod,
    SubjectType,
)
from anu_kernel.db import DelegationRevocation
from anu_kernel.repository import add_authority, add_competence, add_delegation
from anu_kernel.services import evaluate_authority


def dt(s: str) -> datetime:
    return datetime.fromisoformat(s.replace("Z", "+00:00"))


def seed_authority(session, delegation_allowed=True):
    add_competence(session, CompetenceAssertionContract(
        assertion_id="comp-1", subject_ref="urn:anu:human:h003",
        competence_ref="urn:anu:competence:programme-governance", level="OWNER",
        asserted_by="urn:anu:human:rector",
        effective_period=EffectivePeriod(valid_from=dt("2026-01-01T00:00:00Z")),
    ))
    return add_authority(session, AuthorityGrantContract(
        authority_id="auth-1", subject_ref="urn:anu:human:h003", subject_type=SubjectType.HUMAN,
        authority_type="academic.programme.approve", basis_ref="basis-1", issuer_ref="urn:anu:org:aru",
        scope=AuthorityScope(resource="urn:anu:programme:software-engineering", action="academic.programme.approve"),
        consequence_class="ACADEMIC_CONSEQUENCE",
        competence_requirements=["urn:anu:competence:programme-governance"],
        delegation_allowed=delegation_allowed,
        effective_period=EffectivePeriod(valid_from=dt("2026-01-01T00:00:00Z"), valid_until=dt("2027-01-01T00:00:00Z")),
    ))


def test_capability_does_not_create_authority(session):
    result = evaluate_authority(session, AuthorityEvaluationRequest(
        subject_ref="urn:anu:agent:qa-01", subject_type=SubjectType.AGENT,
        action="academic.programme.approve", resource="urn:anu:programme:software-engineering",
        at=dt("2026-10-15T00:00:00Z"), competence_refs=["urn:anu:competence:programme-governance"]
    ))
    assert result["allowed"] is False
    assert "AUTHORITY_NOT_PRESENT" in result["reason_codes"]


def test_authority_requires_competence(session):
    add_authority(session, AuthorityGrantContract(
        authority_id="auth-2", subject_ref="urn:anu:human:h004", subject_type=SubjectType.HUMAN,
        authority_type="academic.programme.approve", basis_ref="basis-1", issuer_ref="urn:anu:org:aru",
        scope=AuthorityScope(resource="urn:anu:programme:software-engineering"),
        consequence_class="ACADEMIC_CONSEQUENCE",
        competence_requirements=["urn:anu:competence:programme-governance"], delegation_allowed=False,
        effective_period=EffectivePeriod(valid_from=dt("2026-01-01T00:00:00Z"))
    ))
    result = evaluate_authority(session, AuthorityEvaluationRequest(
        subject_ref="urn:anu:human:h004", subject_type=SubjectType.HUMAN,
        action="academic.programme.approve", resource="urn:anu:programme:software-engineering",
        at=dt("2026-10-15T00:00:00Z")
    ))
    assert result["allowed"] is False
    assert "REQUIRED_COMPETENCE_MISSING" in result["reason_codes"]


def test_delegation_is_bounded_and_revocable(session):
    seed_authority(session, delegation_allowed=True)
    add_delegation(session, DelegationGrantContract(
        delegation_id="del-1", delegator_ref="urn:anu:human:h003", delegatee_ref="urn:anu:agent:qa-01",
        authority_ref="auth-1", delegated_scope=AuthorityScope(resource="urn:anu:programme:software-engineering"),
        purpose="Programme precheck", valid_from=dt("2026-10-01T00:00:00Z"), valid_until=dt("2026-11-01T00:00:00Z"),
        issued_under_policy="urn:anu:policy:delegation:v1"
    ))
    allowed = evaluate_authority(session, AuthorityEvaluationRequest(
        subject_ref="urn:anu:agent:qa-01", subject_type=SubjectType.AGENT,
        action="academic.programme.approve", resource="urn:anu:programme:software-engineering",
        at=dt("2026-10-15T00:00:00Z"), competence_refs=["urn:anu:competence:programme-governance"]
    ))
    assert allowed["allowed"] is True
    session.add(DelegationRevocation(
        revocation_id="rev-1", delegation_id="del-1", effective_time=dt("2026-10-20T00:00:00Z"),
        recorded_at=dt("2026-10-20T00:01:00Z"), actor_ref="urn:anu:human:h003", reason="revoked"
    )); session.commit()
    denied = evaluate_authority(session, AuthorityEvaluationRequest(
        subject_ref="urn:anu:agent:qa-01", subject_type=SubjectType.AGENT,
        action="academic.programme.approve", resource="urn:anu:programme:software-engineering",
        at=dt("2026-10-21T00:00:00Z"), competence_refs=["urn:anu:competence:programme-governance"]
    ))
    assert denied["allowed"] is False


def test_delegation_cannot_broaden_scope(session):
    seed_authority(session, delegation_allowed=True)
    with pytest.raises(ValueError, match="DELEGATION_SCOPE_EXCEEDS_AUTHORITY"):
        add_delegation(session, DelegationGrantContract(
            delegation_id="del-2", delegator_ref="urn:anu:human:h003", delegatee_ref="urn:anu:agent:qa-01",
            authority_ref="auth-1", delegated_scope=AuthorityScope(resource="urn:anu:programme:data-science"),
            purpose="Invalid broad delegation", valid_from=dt("2026-10-01T00:00:00Z"), valid_until=dt("2026-11-01T00:00:00Z"),
            issued_under_policy="urn:anu:policy:delegation:v1"
        ))
