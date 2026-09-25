from __future__ import annotations

from sqlalchemy.orm import Session

from .contracts import (
    AuthenticationContext,
    Effect,
    EnforcementDecisionContract,
    GovernedActionRequest,
    PolicyEvaluationRequest,
)
from .services import evaluate_authority, evaluate_policy
from .contracts import AuthorityEvaluationRequest


def enforce_governed_action(
    session: Session,
    principal: AuthenticationContext,
    request: GovernedActionRequest,
) -> EnforcementDecisionContract:
    """Policy Enforcement Point for consequential Kernel operations.

    Authentication proves who is interacting. It never creates Authority.
    Authority/Delegation and Policy are evaluated independently and fail closed.
    """
    authority = evaluate_authority(
        session,
        AuthorityEvaluationRequest(
            subject_ref=principal.subject_ref,
            subject_type=principal.subject_type,
            action=request.action,
            resource=request.resource,
            context_ref=request.context,
            at=request.at,
            competence_refs=request.competence_refs,
        ),
    )
    policy = evaluate_policy(
        session,
        PolicyEvaluationRequest(
            subject_ref=principal.subject_ref,
            authority_refs=authority["authority_refs"],
            delegation_refs=authority["delegation_refs"],
            resource=request.resource,
            action=request.action,
            context=request.context,
            risk=request.risk,
            at=request.at,
        ),
    )
    reasons = list(authority["reason_codes"]) + list(policy.reason_codes)
    authorized = authority["allowed"]
    allowed = authorized and policy.effect == Effect.ALLOW
    if not authorized:
        reasons.append("PEP_DENY_AUTHORITY")
    if policy.effect != Effect.ALLOW:
        reasons.append(f"PEP_POLICY_{policy.effect.value}")
    return EnforcementDecisionContract(
        subject_ref=principal.subject_ref,
        authenticated=True,
        authorized=authorized,
        authority_valid=authorized,
        policy_effect=policy.effect,
        allowed_to_proceed=allowed,
        authority_refs=authority["authority_refs"],
        delegation_refs=authority["delegation_refs"],
        policy_refs=policy.policy_refs,
        obligations=policy.obligations,
        reason_codes=sorted(set(reasons)),
    )
