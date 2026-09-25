from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy import and_, or_, select
from sqlalchemy.orm import Session

from .contracts import (
    AuthorityEvaluationRequest,
    Effect,
    PolicyDecisionContract,
    PolicyEvaluationRequest,
    ReplayRequestContract,
    ReplayResultContract,
    SubjectType,
)
from .db import (
    AuthorityGrant,
    CompetenceAssertion,
    DecisionRecord,
    DelegationGrant,
    DelegationRevocation,
    KernelEvent,
    LifecycleTransition,
    PolicyVersion,
    ProvenanceRecord,
    RoleAssignment,
)


def _cmp_dt(value: datetime) -> datetime:
    """Normalize DB/runtime datetimes for safe temporal comparison.

    SQLite drops timezone offsets even when SQLAlchemy is configured with
    timezone=True. PostgreSQL preserves them. Comparison therefore uses UTC
    naive values as a storage-neutral canonical representation.
    """
    if value.tzinfo is not None:
        return value.astimezone(timezone.utc).replace(tzinfo=None)
    return value


def _active_period(from_: datetime, to: datetime | None, at: datetime) -> bool:
    f = _cmp_dt(from_)
    a = _cmp_dt(at)
    t = _cmp_dt(to) if to is not None else None
    return f <= a and (t is None or a < t)


def _scope_contains(parent: dict[str, Any], child: dict[str, Any]) -> bool:
    """Conservative hierarchical containment: child may narrow but never broaden."""
    for key, child_value in child.items():
        if child_value in (None, ""):
            continue
        parent_value = parent.get(key)
        if parent_value in (None, "*"):
            continue
        if parent_value != child_value:
            return False
    return True


def active_competences(session: Session, subject_ref: str, at: datetime) -> set[str]:
    rows = session.scalars(select(CompetenceAssertion).where(CompetenceAssertion.subject_ref == subject_ref)).all()
    return {
        r.competence_ref
        for r in rows
        if r.lifecycle_state == "ACTIVE"
        and r.validation_state == "VALIDATED"
        and _active_period(r.effective_from, r.effective_to, at)
    }


def active_roles(session: Session, subject_ref: str, at: datetime) -> list[RoleAssignment]:
    rows = session.scalars(select(RoleAssignment).where(RoleAssignment.subject_ref == subject_ref)).all()
    return [
        r for r in rows
        if r.lifecycle_state == "ACTIVE" and _active_period(r.effective_from, r.effective_to, at)
    ]


def authority_grants(session: Session, subject_ref: str, at: datetime) -> list[AuthorityGrant]:
    rows = session.scalars(select(AuthorityGrant).where(AuthorityGrant.subject_ref == subject_ref)).all()
    return [
        r for r in rows
        if r.lifecycle_state == "ACTIVE" and _active_period(r.effective_from, r.effective_to, at)
    ]


def active_delegations(session: Session, delegatee_ref: str, at: datetime) -> list[DelegationGrant]:
    rows = session.scalars(select(DelegationGrant).where(DelegationGrant.delegatee_ref == delegatee_ref)).all()
    result: list[DelegationGrant] = []
    for r in rows:
        if r.lifecycle_state != "ACTIVE" or not (_cmp_dt(r.valid_from) <= _cmp_dt(at) < _cmp_dt(r.valid_until)):
            continue
        revocations = session.scalars(
            select(DelegationRevocation).where(
                DelegationRevocation.delegation_id == r.delegation_id,
                DelegationRevocation.effective_time <= _cmp_dt(at),
            )
        ).all()
        if not revocations:
            result.append(r)
    return result


def validate_delegation(session: Session, delegation: DelegationGrant) -> tuple[bool, list[str]]:
    reasons: list[str] = []
    parent = session.get(AuthorityGrant, delegation.authority_ref)
    if parent is None:
        return False, ["AUTHORITY_NOT_FOUND"]
    if parent.subject_ref != delegation.delegator_ref:
        reasons.append("DELEGATOR_DOES_NOT_OWN_AUTHORITY")
    if not parent.delegation_allowed:
        reasons.append("AUTHORITY_NOT_DELEGABLE")
    if not _scope_contains(parent.scope or {}, delegation.delegated_scope or {}):
        reasons.append("DELEGATION_SCOPE_EXCEEDS_AUTHORITY")
    if _cmp_dt(delegation.valid_from) < _cmp_dt(parent.effective_from):
        reasons.append("DELEGATION_STARTS_BEFORE_AUTHORITY")
    if parent.effective_to is not None and _cmp_dt(delegation.valid_until) > _cmp_dt(parent.effective_to):
        reasons.append("DELEGATION_OUTLIVES_AUTHORITY")
    return not reasons, reasons


def evaluate_authority(session: Session, request: AuthorityEvaluationRequest) -> dict[str, Any]:
    at = request.at
    available_competences = set(request.competence_refs) | active_competences(session, request.subject_ref, at)
    matched_authority: list[str] = []
    matched_delegation: list[str] = []
    reasons: list[str] = []

    # Standing institutional grants are forbidden for Agent identities by contract.
    if request.subject_type != SubjectType.AGENT:
        for grant in authority_grants(session, request.subject_ref, at):
            if grant.authority_type != request.action:
                continue
            scope = grant.scope or {}
            if request.resource and scope.get("resource") not in (None, "*", request.resource):
                continue
            missing = [c for c in (grant.competence_requirements or []) if c not in available_competences]
            if missing:
                reasons.append("REQUIRED_COMPETENCE_MISSING")
                continue
            matched_authority.append(grant.authority_id)

    for delegation in active_delegations(session, request.subject_ref, at):
        ok, invalid_reasons = validate_delegation(session, delegation)
        if not ok:
            reasons.extend(invalid_reasons)
            continue
        parent = session.get(AuthorityGrant, delegation.authority_ref)
        if parent is None or parent.authority_type != request.action:
            continue
        dscope = delegation.delegated_scope or {}
        if request.resource and dscope.get("resource") not in (None, "*", request.resource):
            continue
        missing = [c for c in (parent.competence_requirements or []) if c not in available_competences]
        if missing:
            reasons.append("REQUIRED_COMPETENCE_MISSING")
            continue
        matched_authority.append(parent.authority_id)
        matched_delegation.append(delegation.delegation_id)

    allowed = bool(matched_authority)
    if not allowed and not reasons:
        reasons.append("AUTHORITY_NOT_PRESENT")
    return {
        "allowed": allowed,
        "authority_refs": sorted(set(matched_authority)),
        "delegation_refs": sorted(set(matched_delegation)),
        "reason_codes": sorted(set(reasons)),
    }


def applicable_policy(session: Session, policy_id: str, at: datetime) -> PolicyVersion | None:
    rows = session.scalars(select(PolicyVersion).where(PolicyVersion.policy_id == policy_id)).all()
    candidates = [
        r for r in rows
        if r.lifecycle_state in ("ACTIVE", "SUPERSEDED", "ARCHIVED")
        and _active_period(r.effective_from, r.effective_to, at)
    ]
    candidates.sort(key=lambda r: (r.effective_from, r.recorded_at), reverse=True)
    return candidates[0] if candidates else None


def replay_decision(session: Session, request: ReplayRequestContract) -> ReplayResultContract:
    decision = session.get(DecisionRecord, request.target_ref)
    if decision is None:
        raise KeyError("decision not found")

    if request.perspective == "AS_EFFECTIVE_AT":
        at = request.effective_at
        assert at is not None
        if _cmp_dt(decision.effective_time) > _cmp_dt(at):
            raise KeyError("decision did not yet exist at requested effective time")
    else:
        at = request.recorded_at
        assert at is not None
        if _cmp_dt(decision.recorded_time) > _cmp_dt(at):
            raise KeyError("decision was not yet known at requested recorded time")

    policy = None
    # policy_ref is stored as canonical policy id; exact historical version is resolved by decision effective time.
    policy = applicable_policy(session, decision.policy_ref, decision.effective_time)

    roles = active_roles(session, decision.subject_ref, decision.effective_time)
    comps = active_competences(session, decision.subject_ref, decision.effective_time)
    grant = session.get(AuthorityGrant, decision.authority_ref)
    delegation = session.get(DelegationGrant, decision.delegation_ref) if decision.delegation_ref else None

    provenance_chain = [decision.provenance_ref]
    p = session.get(ProvenanceRecord, decision.provenance_ref)
    if p:
        provenance_chain.extend(p.previous_provenance_refs or [])

    events = session.scalars(
        select(KernelEvent).where(
            or_(KernelEvent.subject == decision.decision_id, KernelEvent.subject == decision.artifact_ref)
        )
    ).all()

    lifecycle_rows = session.scalars(
        select(LifecycleTransition).where(LifecycleTransition.object_ref == decision.decision_id)
    ).all()
    lifecycle_rows.sort(key=lambda r: (r.effective_time, r.recorded_time))
    lifecycle_state = lifecycle_rows[-1].to_state if lifecycle_rows else "ACTIVE"

    warnings: list[str] = []
    completeness = "COMPLETE"
    if policy is None:
        warnings.append("POLICY_VERSION_NOT_RECONSTRUCTED")
        completeness = "PARTIAL"
    if grant is None:
        warnings.append("AUTHORITY_NOT_RECONSTRUCTED")
        completeness = "PARTIAL"

    return ReplayResultContract(
        target_ref=decision.decision_id,
        perspective=request.perspective,
        reconstructed_state={
            "outcome": decision.outcome,
            "effective_time": decision.effective_time.isoformat(),
            "recorded_time": decision.recorded_time.isoformat(),
            "artifact_ref": decision.artifact_ref,
            "signature_ref": decision.signature_ref,
        },
        role_assignments=[r.assignment_id for r in roles],
        competence_assertions=sorted(comps),
        authority_refs=[grant.authority_id] if grant else [],
        delegation_refs=[delegation.delegation_id] if delegation else [],
        policy_versions=[f"{policy.policy_id}@{policy.version}"] if policy else [],
        evidence_refs=list(decision.evidence_refs or []),
        lifecycle_state=lifecycle_state,
        provenance_chain=provenance_chain,
        source_event_refs=[e.event_id for e in events],
        completeness_status=completeness,
        warnings=warnings,
    )


def _policy_scope_matches(scope: dict[str, Any], request: PolicyEvaluationRequest) -> bool:
    checks = {
        "resource": request.resource,
        "action": request.action,
        "context": request.context,
    }
    for key, requested in checks.items():
        configured = scope.get(key)
        if configured in (None, "*") or requested is None:
            continue
        if configured != requested:
            return False
    return True


def evaluate_policy(session: Session, request: PolicyEvaluationRequest) -> PolicyDecisionContract:
    """Conservative Phase-1 PDP. Unknown or absent policy fails closed.

    This is intentionally a small declarative baseline, not a general-purpose
    business rules engine. Recognized effects are ALLOW/DENY and obligations
    expressed as {"require": ...}.
    """
    rows = session.scalars(select(PolicyVersion)).all()
    applicable = [
        r for r in rows
        if r.lifecycle_state in ("ACTIVE", "SUPERSEDED", "ARCHIVED")
        and _active_period(r.effective_from, r.effective_to, request.at)
        and _policy_scope_matches(r.scope or {}, request)
    ]
    applicable.sort(key=lambda r: (r.effective_from, r.recorded_at), reverse=True)

    policy_refs = [f"{r.policy_id}@{r.version}" for r in applicable]
    obligations: list[str] = []
    reasons: list[str] = []
    effect = Effect.DENY

    if not applicable:
        reasons.append("NO_APPLICABLE_POLICY")
    else:
        saw_allow = False
        require_review = False
        require_signature = False
        for policy in applicable:
            for item in policy.effects or []:
                declared = str(item.get("effect", "")).upper()
                requirement = item.get("require")
                if declared == "DENY":
                    reasons.append("POLICY_DENY")
                    effect = Effect.DENY
                    saw_allow = False
                    require_review = False
                    require_signature = False
                    break
                if declared == "ALLOW":
                    saw_allow = True
                if requirement:
                    obligations.append(str(requirement))
                    if "signature" in str(requirement).lower():
                        require_signature = True
                    else:
                        require_review = True
            if "POLICY_DENY" in reasons:
                break
        if "POLICY_DENY" not in reasons:
            if require_signature:
                effect = Effect.REQUIRE_SIGNATURE
            elif require_review:
                effect = Effect.REQUIRE_REVIEW
            elif saw_allow:
                effect = Effect.ALLOW
            else:
                reasons.append("NO_POSITIVE_POLICY_EFFECT")

    return PolicyDecisionContract(
        decision_id=f"policy-eval:{request.subject_ref}:{request.action}:{int(request.at.timestamp())}",
        policy_refs=policy_refs,
        evaluated_at=request.at,
        subject_ref=request.subject_ref,
        role_context=request.role_context,
        authority_refs=request.authority_refs,
        delegation_refs=request.delegation_refs,
        resource=request.resource,
        action=request.action,
        context=request.context,
        risk=request.risk,
        effect=effect,
        obligations=sorted(set(obligations)),
        reason_codes=sorted(set(reasons)),
    )
