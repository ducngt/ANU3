from __future__ import annotations

import os
from datetime import datetime

import jwt

from anu_kernel.authn import authenticate_bearer_token
from anu_kernel.contracts import (
    AuthorityGrantContract,
    AuthorityScope,
    CompetenceAssertionContract,
    EffectivePeriod,
    GovernedActionRequest,
    IdentityContract,
    PolicyContract,
    SubjectType,
)
from anu_kernel.enforcement import enforce_governed_action
from anu_kernel.repository import add_authority, add_competence, add_identity, add_policy


def dt(s: str) -> datetime:
    return datetime.fromisoformat(s.replace("Z", "+00:00"))


def _token(subject: str, identity_id: str, credential_ref: str) -> str:
    return jwt.encode(
        {
            "sub": subject,
            "identity_id": identity_id,
            "credential_ref": credential_ref,
            "iss": "anu-reference-idp",
            "aud": "anu-kernel",
            "iat": int(dt("2026-01-01T00:00:00Z").timestamp()),
            "exp": int(dt("2030-10-15T09:00:00Z").timestamp()),
        },
        "phase1-test-secret-that-is-long-enough-32b",
        algorithm="HS256",
    )


def test_authentication_does_not_create_authority(session, monkeypatch):
    monkeypatch.setenv("ANU_JWT_SECRET", "phase1-test-secret-that-is-long-enough-32b")
    human = "urn:anu:human:h100"
    identity_id = "urn:anu:identity:human:h100"
    credential = "urn:anu:credential:login:h100"
    add_identity(session, IdentityContract(
        identity_id=identity_id,
        subject_id=human,
        subject_type=SubjectType.HUMAN,
        assurance_level="HIGH",
        credential_refs=[credential],
        effective_period=EffectivePeriod(valid_from=dt("2026-01-01T00:00:00Z")),
    ))
    principal = authenticate_bearer_token(session, _token(human, identity_id, credential))
    decision = enforce_governed_action(session, principal, GovernedActionRequest(
        action="academic.programme.approve",
        resource="urn:anu:programme:se",
        at=dt("2026-10-15T10:00:00Z"),
    ))
    assert decision.authenticated is True
    assert decision.authority_valid is False
    assert decision.allowed_to_proceed is False
    assert "PEP_DENY_AUTHORITY" in decision.reason_codes


def test_pep_allows_only_when_authn_authority_and_policy_all_pass(session, monkeypatch):
    monkeypatch.setenv("ANU_JWT_SECRET", "phase1-test-secret-that-is-long-enough-32b")
    human = "urn:anu:human:h101"
    identity_id = "urn:anu:identity:human:h101"
    credential = "urn:anu:credential:login:h101"
    programme = "urn:anu:programme:se"
    competence = "urn:anu:competence:programme-governance"
    add_identity(session, IdentityContract(
        identity_id=identity_id,
        subject_id=human,
        subject_type=SubjectType.HUMAN,
        assurance_level="HIGH",
        credential_refs=[credential],
        effective_period=EffectivePeriod(valid_from=dt("2026-01-01T00:00:00Z")),
    ))
    add_competence(session, CompetenceAssertionContract(
        assertion_id="comp-h101",
        subject_ref=human,
        competence_ref=competence,
        level="QUALIFIED",
        asserted_by="urn:anu:org:aru",
        effective_period=EffectivePeriod(valid_from=dt("2026-01-01T00:00:00Z")),
    ))
    add_authority(session, AuthorityGrantContract(
        authority_id="auth-h101-programme-approve",
        subject_ref=human,
        subject_type=SubjectType.HUMAN,
        authority_type="academic.programme.approve",
        basis_ref="urn:anu:policy:approval@1.0.0",
        issuer_ref="urn:anu:org:aru",
        scope=AuthorityScope(resource=programme, action="academic.programme.approve"),
        consequence_class="ACADEMIC_CONSEQUENCE",
        competence_requirements=[competence],
        effective_period=EffectivePeriod(valid_from=dt("2026-01-01T00:00:00Z"), valid_until=dt("2027-01-01T00:00:00Z")),
    ))
    add_policy(session, PolicyContract(
        policy_id="urn:anu:policy:approval",
        policy_type="ACADEMIC_APPROVAL",
        issuer_ref="urn:anu:org:aru",
        authority_basis_ref="urn:anu:authority:policy-owner",
        version="1.0.0",
        scope={"action": "academic.programme.approve", "resource": programme},
        effects=[{"effect": "ALLOW"}],
        effective_period=EffectivePeriod(valid_from=dt("2026-01-01T00:00:00Z"), valid_until=dt("2027-01-01T00:00:00Z")),
    ))
    principal = authenticate_bearer_token(session, _token(human, identity_id, credential))
    decision = enforce_governed_action(session, principal, GovernedActionRequest(
        action="academic.programme.approve",
        resource=programme,
        at=dt("2026-10-15T10:00:00Z"),
    ))
    assert decision.authenticated is True
    assert decision.authority_valid is True
    assert decision.policy_effect.value == "ALLOW"
    assert decision.allowed_to_proceed is True
