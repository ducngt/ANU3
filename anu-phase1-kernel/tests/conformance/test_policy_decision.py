from __future__ import annotations

from datetime import datetime

from anu_kernel.contracts import EffectivePeriod, PolicyContract, PolicyEvaluationRequest
from anu_kernel.repository import add_policy
from anu_kernel.services import evaluate_policy


def dt(s: str) -> datetime:
    return datetime.fromisoformat(s.replace("Z", "+00:00"))


def test_policy_decision_is_effective_time_aware_and_fail_closed(session):
    add_policy(session, PolicyContract(
        policy_id="urn:anu:policy:academic-approval",
        policy_type="ACADEMIC_APPROVAL",
        issuer_ref="urn:anu:org:aru:academic-affairs",
        authority_basis_ref="urn:anu:authority:policy-owner",
        version="1.0.0",
        scope={"action": "academic.programme.approve", "resource": "urn:anu:programme:software-engineering"},
        effects=[{"require": "programme_owner_approval"}],
        effective_period=EffectivePeriod(
            valid_from=dt("2026-01-01T00:00:00Z"),
            valid_until=dt("2027-01-01T00:00:00Z"),
        ),
    ))
    decision = evaluate_policy(session, PolicyEvaluationRequest(
        subject_ref="urn:anu:human:h003",
        action="academic.programme.approve",
        resource="urn:anu:programme:software-engineering",
        at=dt("2026-10-15T00:00:00Z"),
    ))
    assert decision.effect.value == "REQUIRE_REVIEW"
    assert decision.policy_refs == ["urn:anu:policy:academic-approval@1.0.0"]

    no_policy = evaluate_policy(session, PolicyEvaluationRequest(
        subject_ref="urn:anu:human:h003",
        action="academic.programme.approve",
        resource="urn:anu:programme:data-science",
        at=dt("2026-10-15T00:00:00Z"),
    ))
    assert no_policy.effect.value == "DENY"
    assert "NO_APPLICABLE_POLICY" in no_policy.reason_codes
