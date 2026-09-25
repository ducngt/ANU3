from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path

from sqlalchemy.orm import sessionmaker

from anu_kernel.contracts import (
    AuthorityEvaluationRequest,
    AuthorityGrantContract,
    AuthorityScope,
    CompetenceAssertionContract,
    DecisionRecordContract,
    DelegationGrantContract,
    DelegationRevocationContract,
    EffectivePeriod,
    IdentityContract,
    KernelEventEnvelope,
    LifecycleState,
    PolicyContract,
    ProvenanceRecordContract,
    ReplayRequestContract,
    RoleAssignmentContract,
    SemanticDefinitionContract,
    SubjectType,
)
from anu_kernel.db import make_engine
from anu_kernel.repository import (
    add_authority,
    add_competence,
    add_decision,
    add_delegation,
    add_event,
    add_identity,
    add_policy,
    add_provenance,
    add_role,
    add_semantic,
    revoke_delegation,
)
from anu_kernel.services import evaluate_authority, replay_decision


def dt(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def run_pilot(database_url: str) -> dict:
    engine = make_engine(database_url)
    Session = sessionmaker(bind=engine, future=True)
    human = "urn:anu:human:h003"
    agent = "urn:anu:agent:qa-01"
    programme = "urn:anu:programme:software-engineering"
    policy_id = "urn:anu:policy:academic-approval"
    decision_id = "urn:anu:decision:programme-revision-001"

    with Session() as session:
        add_identity(session, IdentityContract(
            identity_id="urn:anu:identity:human:h003", subject_id=human, subject_type=SubjectType.HUMAN,
            assurance_level="HIGH", aliases=["Programme Owner SE"],
            effective_period=EffectivePeriod(valid_from=dt("2026-01-01T00:00:00Z")),
        ))
        add_identity(session, IdentityContract(
            identity_id="urn:anu:identity:agent:qa-01", subject_id=agent, subject_type=SubjectType.AGENT,
            assurance_level="SYSTEM", aliases=["QA Analysis Agent"],
            effective_period=EffectivePeriod(valid_from=dt("2026-01-01T00:00:00Z")),
        ))
        add_semantic(session, SemanticDefinitionContract(
            semantic_id="urn:anu:semantic:role:programme-owner", canonical_name="Programme Owner",
            definition="Role responsible for programme governance in a bounded institutional context.",
            semantic_kind="ROLE", owner_ref="urn:anu:org:aru", version="1.0.0",
            effective_period=EffectivePeriod(valid_from=dt("2026-01-01T00:00:00Z")),
        ))
        add_role(session, RoleAssignmentContract(
            assignment_id="aru-role-h003-programme-owner", subject_ref=human,
            role_ref="urn:anu:semantic:role:programme-owner", context_ref=programme,
            assigned_by="urn:anu:human:rector", basis_ref="urn:anu:decision:appointment-h003",
            effective_period=EffectivePeriod(valid_from=dt("2026-01-01T00:00:00Z")),
        ))
        add_competence(session, CompetenceAssertionContract(
            assertion_id="aru-comp-h003-programme-governance", subject_ref=human,
            competence_ref="urn:anu:competence:programme-governance", level="QUALIFIED",
            scope={"programme": programme}, evidence_refs=["urn:anu:evidence:h003-programme-governance"],
            asserted_by="urn:anu:org:aru",
            effective_period=EffectivePeriod(valid_from=dt("2026-01-01T00:00:00Z")),
        ))
        add_authority(session, AuthorityGrantContract(
            authority_id="urn:anu:authority:programme-owner-approve", subject_ref=human,
            subject_type=SubjectType.HUMAN, authority_type="academic.programme.approve",
            basis_ref="urn:anu:policy:academic-approval:v1", issuer_ref="urn:anu:org:aru",
            scope=AuthorityScope(institution="urn:anu:org:aru", domain="academic", resource=programme,
                                 action="academic.programme.approve", context="programme-governance"),
            consequence_class="ACADEMIC_CONSEQUENCE",
            competence_requirements=["urn:anu:competence:programme-governance"],
            delegation_allowed=True,
            delegation_constraints={"max_scope": programme},
            effective_period=EffectivePeriod(valid_from=dt("2026-01-01T00:00:00Z"), valid_until=dt("2027-01-01T00:00:00Z")),
            policy_refs=[f"{policy_id}@1.0.0"],
        ))
        add_policy(session, PolicyContract(
            policy_id=policy_id, policy_type="ACADEMIC_APPROVAL",
            issuer_ref="urn:anu:org:aru:academic-affairs", authority_basis_ref="urn:anu:authority:policy-owner",
            version="1.0.0", scope={"action": "academic.programme.approve", "resource": programme},
            effects=[{"require": "programme_owner_approval"}],
            effective_period=EffectivePeriod(valid_from=dt("2026-01-01T00:00:00Z"), valid_until=dt("2027-01-01T00:00:00Z")),
            lifecycle_state=LifecycleState.SUPERSEDED,
        ))
        add_policy(session, PolicyContract(
            policy_id=policy_id, policy_type="ACADEMIC_APPROVAL",
            issuer_ref="urn:anu:org:aru:academic-affairs", authority_basis_ref="urn:anu:authority:policy-owner",
            version="2.0.0", scope={"action": "academic.programme.approve", "resource": programme},
            effects=[{"require": "programme_owner_approval"}, {"require": "qa_review"}],
            effective_period=EffectivePeriod(valid_from=dt("2027-01-01T00:00:00Z")),
            supersedes_ref=f"{policy_id}@1.0.0",
        ))

        human_allowed = evaluate_authority(session, AuthorityEvaluationRequest(
            subject_ref=human, subject_type=SubjectType.HUMAN, action="academic.programme.approve",
            resource=programme, context_ref="programme-governance", at=dt("2026-10-15T10:00:00Z"),
        ))
        agent_without_delegation = evaluate_authority(session, AuthorityEvaluationRequest(
            subject_ref=agent, subject_type=SubjectType.AGENT, action="academic.programme.approve",
            resource=programme, at=dt("2026-10-15T10:00:00Z"),
            competence_refs=["urn:anu:competence:programme-governance"],
        ))

        add_delegation(session, DelegationGrantContract(
            delegation_id="urn:anu:delegation:qa-precheck-oct2026", delegator_ref=human, delegatee_ref=agent,
            authority_ref="urn:anu:authority:programme-owner-approve",
            delegated_scope=AuthorityScope(resource=programme, action="academic.programme.approve"),
            purpose="Bounded programme precheck", valid_from=dt("2026-10-01T00:00:00Z"),
            valid_until=dt("2026-11-01T00:00:00Z"), issued_under_policy="urn:anu:policy:delegation:v1",
        ))
        agent_with_delegation = evaluate_authority(session, AuthorityEvaluationRequest(
            subject_ref=agent, subject_type=SubjectType.AGENT, action="academic.programme.approve",
            resource=programme, at=dt("2026-10-15T10:00:00Z"),
            competence_refs=["urn:anu:competence:programme-governance"],
        ))
        revoke_delegation(session, DelegationRevocationContract(
            revocation_id="urn:anu:delegation-revocation:qa-precheck-oct2026",
            delegation_id="urn:anu:delegation:qa-precheck-oct2026",
            effective_time=dt("2026-10-20T00:00:00Z"), recorded_at=dt("2026-10-20T00:01:00Z"),
            actor_ref=human, reason="Reference revocation test",
        ))
        agent_after_revoke = evaluate_authority(session, AuthorityEvaluationRequest(
            subject_ref=agent, subject_type=SubjectType.AGENT, action="academic.programme.approve",
            resource=programme, at=dt("2026-10-21T10:00:00Z"),
            competence_refs=["urn:anu:competence:programme-governance"],
        ))

        add_provenance(session, ProvenanceRecordContract(
            provenance_id="urn:anu:provenance:programme-revision-001", entity_ref=decision_id, actor_ref=human,
            work_ref="urn:anu:work:programme-revision-001", capability_ref="urn:anu:capability:academic.programme.approve",
            source_refs=["urn:anu:evidence:ev101", "urn:anu:evidence:ev102"],
            effective_time=dt("2026-10-15T10:00:00Z"), recorded_time=dt("2026-10-15T10:00:01Z"),
        ))
        add_decision(session, DecisionRecordContract(
            decision_id=decision_id, subject_ref=human,
            role_refs=["urn:anu:semantic:role:programme-owner"],
            authority_ref="urn:anu:authority:programme-owner-approve", policy_ref=policy_id,
            evidence_refs=["urn:anu:evidence:ev101", "urn:anu:evidence:ev102"],
            artifact_ref="urn:anu:artifact:programme-proposal@1.3", signature_ref="urn:anu:signature:sig001",
            outcome="APPROVED", effective_time=dt("2026-10-15T10:00:00Z"),
            recorded_time=dt("2026-10-15T10:00:01Z"), provenance_ref="urn:anu:provenance:programme-revision-001",
        ))
        add_event(session, KernelEventEnvelope(
            event_id="urn:anu:event:programme-revision-001-approved", event_type="anu.programme.revision.approved.v1",
            source="urn:anu:capability:academic.programme.approve", subject=decision_id,
            time=dt("2026-10-15T10:00:01Z"), effective_time=dt("2026-10-15T10:00:00Z"),
            recorded_time=dt("2026-10-15T10:00:01Z"), work_id="urn:anu:work:programme-revision-001",
            actor_identity=human, role="programme-owner",
            authority_ref="urn:anu:authority:programme-owner-approve", policy_version=f"{policy_id}@1.0.0",
            artifact_ref="urn:anu:artifact:programme-proposal@1.3", signature_ref="urn:anu:signature:sig001",
            provenance_ref="urn:anu:provenance:programme-revision-001",
        ))
        replay = replay_decision(session, ReplayRequestContract(
            target_ref=decision_id, perspective="AS_EFFECTIVE_AT", effective_at=dt("2026-10-15T12:00:00Z")
        ))

    checks = {
        "human_authority_valid": human_allowed["allowed"] is True,
        "agent_no_standing_authority": agent_without_delegation["allowed"] is False,
        "bounded_delegation_works": agent_with_delegation["allowed"] is True,
        "revocation_stops_future_use": agent_after_revoke["allowed"] is False,
        "historical_replay_uses_policy_v1": replay.policy_versions == [f"{policy_id}@1.0.0"],
        "historical_replay_complete": replay.completeness_status == "COMPLETE",
    }
    return {
        "scenario": "ARU-01 Programme Revision Approval",
        "checks": checks,
        "pass": all(checks.values()),
        "replay": replay.model_dump(mode="json"),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--database-url", required=True)
    parser.add_argument("--output")
    args = parser.parse_args()
    result = run_pilot(args.database_url)
    payload = json.dumps(result, ensure_ascii=False, indent=2)
    if args.output:
        Path(args.output).write_text(payload + "\n", encoding="utf-8")
    print(payload)
    return 0 if result["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
