from __future__ import annotations

from datetime import datetime

from anu_kernel.contracts import (
    AuthorityGrantContract, AuthorityScope, CompetenceAssertionContract, DecisionRecordContract,
    EffectivePeriod, KernelEventEnvelope, LifecycleState, LifecycleTransitionContract, PolicyContract,
    ProvenanceRecordContract, ReplayRequestContract, RoleAssignmentContract, SubjectType,
)
from anu_kernel.repository import (
    add_authority, add_competence, add_decision, add_event, add_lifecycle_transition,
    add_policy, add_provenance, add_role,
)
from anu_kernel.services import replay_decision


def dt(s: str) -> datetime:
    return datetime.fromisoformat(s.replace("Z", "+00:00"))


def test_historical_replay_uses_historical_policy_not_current(session):
    human="urn:anu:human:h003"; programme="urn:anu:programme:software-engineering"
    policy="urn:anu:policy:academic-approval"; decision="urn:anu:decision:programme-revision-001"
    add_role(session, RoleAssignmentContract(
        assignment_id="role-1", subject_ref=human, role_ref="urn:anu:role:programme-owner",
        context_ref=programme, assigned_by="urn:anu:human:rector",
        effective_period=EffectivePeriod(valid_from=dt("2026-01-01T00:00:00Z"))
    ))
    add_competence(session, CompetenceAssertionContract(
        assertion_id="comp-1", subject_ref=human, competence_ref="urn:anu:competence:programme-governance",
        level="OWNER", asserted_by="urn:anu:human:rector",
        effective_period=EffectivePeriod(valid_from=dt("2026-01-01T00:00:00Z"))
    ))
    add_authority(session, AuthorityGrantContract(
        authority_id="auth-1", subject_ref=human, subject_type=SubjectType.HUMAN,
        authority_type="academic.programme.approve", basis_ref="basis-1", issuer_ref="urn:anu:org:aru",
        scope=AuthorityScope(resource=programme), consequence_class="ACADEMIC_CONSEQUENCE",
        competence_requirements=["urn:anu:competence:programme-governance"], delegation_allowed=False,
        effective_period=EffectivePeriod(valid_from=dt("2026-01-01T00:00:00Z"))
    ))
    add_policy(session, PolicyContract(
        policy_id=policy, policy_type="ACADEMIC_APPROVAL", issuer_ref="urn:anu:org:aru:academic-affairs",
        authority_basis_ref="urn:anu:authority:policy-owner", version="1.0.0",
        effects=[{"require":"programme_owner_approval"}],
        effective_period=EffectivePeriod(valid_from=dt("2026-01-01T00:00:00Z"), valid_until=dt("2027-01-01T00:00:00Z")),
        lifecycle_state=LifecycleState.SUPERSEDED
    ))
    add_policy(session, PolicyContract(
        policy_id=policy, policy_type="ACADEMIC_APPROVAL", issuer_ref="urn:anu:org:aru:academic-affairs",
        authority_basis_ref="urn:anu:authority:policy-owner", version="2.0.0",
        effects=[{"require":"programme_owner_approval"},{"require":"qa_review"}],
        effective_period=EffectivePeriod(valid_from=dt("2027-01-01T00:00:00Z")), supersedes_ref=f"{policy}@1.0.0"
    ))
    add_provenance(session, ProvenanceRecordContract(
        provenance_id="prov-1", entity_ref=decision, actor_ref=human,
        effective_time=dt("2026-10-15T10:00:00Z"), recorded_time=dt("2026-10-15T10:00:01Z"),
        source_refs=["urn:anu:evidence:ev101","urn:anu:evidence:ev102"]
    ))
    add_decision(session, DecisionRecordContract(
        decision_id=decision, subject_ref=human, role_refs=["urn:anu:role:programme-owner"],
        authority_ref="auth-1", policy_ref=policy,
        evidence_refs=["urn:anu:evidence:ev101","urn:anu:evidence:ev102"],
        artifact_ref="urn:anu:artifact:programme-proposal@1.3", signature_ref="urn:anu:signature:sig001",
        outcome="APPROVED", effective_time=dt("2026-10-15T10:00:00Z"), recorded_time=dt("2026-10-15T10:00:01Z"),
        provenance_ref="prov-1"
    ))
    add_event(session, KernelEventEnvelope(
        event_id="evt-1", event_type="anu.programme.revision.approved.v1",
        source="urn:anu:capability:academic.programme.approve", subject=decision,
        time=dt("2026-10-15T10:00:01Z"), effective_time=dt("2026-10-15T10:00:00Z"),
        recorded_time=dt("2026-10-15T10:00:01Z"), actor_identity=human,
        role="programme-owner", authority_ref="auth-1", policy_version=f"{policy}@1.0.0",
        artifact_ref="urn:anu:artifact:programme-proposal@1.3", signature_ref="urn:anu:signature:sig001",
        provenance_ref="prov-1"
    ))
    result = replay_decision(session, ReplayRequestContract(
        target_ref=decision, perspective="AS_EFFECTIVE_AT", effective_at=dt("2026-10-15T12:00:00Z")
    ))
    assert result.policy_versions == [f"{policy}@1.0.0"]
    assert result.authority_refs == ["auth-1"]
    assert result.evidence_refs == ["urn:anu:evidence:ev101", "urn:anu:evidence:ev102"]
    assert result.completeness_status == "COMPLETE"


def test_retirement_preserves_history(session):
    add_lifecycle_transition(session, LifecycleTransitionContract(
        transition_id="lt-1", object_ref="urn:anu:capability:academic.programme.revise",
        from_state=LifecycleState.ACTIVE, to_state=LifecycleState.RETIRED,
        effective_time=dt("2028-01-01T00:00:00Z"), recorded_time=dt("2028-01-01T00:00:01Z"),
        reason="replaced", actor_ref="urn:anu:human:architect"
    ))
    rows = session.query(type(session.query.__self__) if False else object) if False else None
    from anu_kernel.db import LifecycleTransition
    assert session.get(LifecycleTransition, "lt-1") is not None
