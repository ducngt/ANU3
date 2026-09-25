from __future__ import annotations

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from .contracts import (
    AuditEventContract,
    AuthorityGrantContract,
    CompetenceAssertionContract,
    DecisionRecordContract,
    DelegationGrantContract,
    DelegationRevocationContract,
    IdentityContract,
    KernelEventEnvelope,
    LifecycleTransitionContract,
    PolicyContract,
    ProvenanceRecordContract,
    RoleAssignmentContract,
    SemanticDefinitionContract,
    TrustCredentialContract,
    SignatureRecordContract,
    AgentAttestationContract,
)
from .db import (
    AuditEvent,
    AuthorityGrant,
    CompetenceAssertion,
    DecisionRecord,
    DelegationGrant,
    DelegationRevocation,
    IdentityRecord,
    KernelEvent,
    LifecycleTransition,
    PolicyVersion,
    ProvenanceRecord,
    RoleAssignment,
    SemanticDefinition,
    TrustCredential,
    SignatureRecord,
    AgentAttestation,
)
from .errors import DomainValidationError, RepositoryConflict
from .services import validate_delegation
from .trust import public_key_fingerprint_sha256


def _commit(session: Session, row, resource_type: str, resource_id: str):
    session.add(row)
    try:
        session.commit()
    except IntegrityError as exc:
        session.rollback()
        raise RepositoryConflict(resource_type, resource_id) from exc
    return row


def add_identity(session: Session, c: IdentityContract) -> IdentityRecord:
    row = IdentityRecord(
        identity_id=c.identity_id,
        subject_id=c.subject_id,
        subject_type=c.subject_type.value,
        assurance_level=c.assurance_level,
        status=c.status,
        credential_refs=c.credential_refs,
        aliases=c.aliases,
        effective_from=c.effective_period.valid_from,
        effective_to=c.effective_period.valid_until,
        lifecycle_state=c.lifecycle_state.value,
        provenance_ref=c.provenance_ref,
    )
    return _commit(session, row, "identity", c.identity_id)


def add_semantic(session: Session, c: SemanticDefinitionContract) -> SemanticDefinition:
    row = SemanticDefinition(
        semantic_id=c.semantic_id,
        canonical_name=c.canonical_name,
        definition=c.definition,
        namespace=c.namespace,
        semantic_kind=c.semantic_kind,
        owner_ref=c.owner_ref,
        context_ref=c.context_ref,
        relations=c.relations,
        mappings=c.mappings,
        version=c.version,
        effective_from=c.effective_period.valid_from,
        effective_to=c.effective_period.valid_until,
        lifecycle_state=c.lifecycle_state.value,
        provenance_ref=c.provenance_ref,
    )
    # semantic identity is versioned; duplicate semantic_id+version is currently
    # protected by service-level idempotence in the seed pipeline rather than a DB constraint.
    session.add(row)
    session.commit()
    return row


def add_role(session: Session, c: RoleAssignmentContract) -> RoleAssignment:
    row = RoleAssignment(
        assignment_id=c.assignment_id,
        subject_ref=c.subject_ref,
        role_ref=c.role_ref,
        context_ref=c.context_ref,
        assigned_by=c.assigned_by,
        basis_ref=c.basis_ref,
        effective_from=c.effective_period.valid_from,
        effective_to=c.effective_period.valid_until,
        lifecycle_state=c.lifecycle_state.value,
        provenance_ref=c.provenance_ref,
    )
    return _commit(session, row, "role_assignment", c.assignment_id)


def add_competence(session: Session, c: CompetenceAssertionContract) -> CompetenceAssertion:
    row = CompetenceAssertion(
        assertion_id=c.assertion_id,
        subject_ref=c.subject_ref,
        competence_ref=c.competence_ref,
        level=c.level,
        scope=c.scope,
        evidence_refs=c.evidence_refs,
        asserted_by=c.asserted_by,
        validation_state=c.validation_state,
        effective_from=c.effective_period.valid_from,
        effective_to=c.effective_period.valid_until,
        lifecycle_state=c.lifecycle_state.value,
        provenance_ref=c.provenance_ref,
    )
    return _commit(session, row, "competence_assertion", c.assertion_id)


def add_authority(session: Session, c: AuthorityGrantContract) -> AuthorityGrant:
    row = AuthorityGrant(
        authority_id=c.authority_id,
        subject_ref=c.subject_ref,
        subject_type=c.subject_type.value,
        authority_type=c.authority_type,
        basis_ref=c.basis_ref,
        issuer_ref=c.issuer_ref,
        scope=c.scope.model_dump(),
        consequence_class=c.consequence_class,
        competence_requirements=c.competence_requirements,
        delegation_allowed=c.delegation_allowed,
        delegation_constraints=c.delegation_constraints,
        effective_from=c.effective_period.valid_from,
        effective_to=c.effective_period.valid_until,
        policy_refs=c.policy_refs,
        lifecycle_state=c.lifecycle_state.value,
        provenance_ref=c.provenance_ref,
    )
    return _commit(session, row, "authority_grant", c.authority_id)


def add_delegation(session: Session, c: DelegationGrantContract) -> DelegationGrant:
    row = DelegationGrant(
        delegation_id=c.delegation_id,
        delegator_ref=c.delegator_ref,
        delegatee_ref=c.delegatee_ref,
        authority_ref=c.authority_ref,
        delegated_scope=c.delegated_scope.model_dump(),
        purpose=c.purpose,
        conditions=c.conditions,
        valid_from=c.valid_from,
        valid_until=c.valid_until,
        redelegation_allowed=c.redelegation_allowed,
        revocation_policy_ref=c.revocation_policy_ref,
        issued_under_policy=c.issued_under_policy,
        lifecycle_state=c.lifecycle_state.value,
        provenance_ref=c.provenance_ref,
    )
    session.add(row)
    try:
        session.flush()
    except IntegrityError as exc:
        session.rollback()
        raise RepositoryConflict("delegation", c.delegation_id) from exc
    ok, reasons = validate_delegation(session, row)
    if not ok:
        session.rollback()
        raise DomainValidationError("invalid delegation", reasons)
    session.commit()
    return row


def revoke_delegation(session: Session, c: DelegationRevocationContract) -> DelegationRevocation:
    if session.get(DelegationGrant, c.delegation_id) is None:
        raise DomainValidationError("delegation not found", ["DELEGATION_NOT_FOUND"])
    row = DelegationRevocation(**c.model_dump())
    return _commit(session, row, "delegation_revocation", c.revocation_id)


def add_policy(session: Session, c: PolicyContract) -> PolicyVersion:
    row = PolicyVersion(
        policy_id=c.policy_id,
        policy_type=c.policy_type,
        issuer_ref=c.issuer_ref,
        authority_basis_ref=c.authority_basis_ref,
        version=c.version,
        scope=c.scope,
        conditions=c.conditions,
        effects=c.effects,
        effective_from=c.effective_period.valid_from,
        effective_to=c.effective_period.valid_until,
        supersedes_ref=c.supersedes_ref,
        exception_rules=c.exception_rules,
        lifecycle_state=c.lifecycle_state.value,
        provenance_ref=c.provenance_ref,
    )
    return _commit(session, row, "policy_version", f"{c.policy_id}@{c.version}")


def add_provenance(session: Session, c: ProvenanceRecordContract) -> ProvenanceRecord:
    return _commit(session, ProvenanceRecord(**c.model_dump()), "provenance", c.provenance_id)


def add_audit(session: Session, c: AuditEventContract) -> AuditEvent:
    return _commit(session, AuditEvent(**c.model_dump()), "audit_event", c.audit_id)


def add_event(session: Session, c: KernelEventEnvelope) -> KernelEvent:
    return _commit(session, KernelEvent(**c.model_dump()), "kernel_event", c.event_id)


def add_decision(session: Session, c: DecisionRecordContract) -> DecisionRecord:
    return _commit(session, DecisionRecord(**c.model_dump()), "decision_record", c.decision_id)


def add_lifecycle_transition(session: Session, c: LifecycleTransitionContract) -> LifecycleTransition:
    row = LifecycleTransition(
        **{**c.model_dump(), "from_state": c.from_state.value, "to_state": c.to_state.value}
    )
    return _commit(session, row, "lifecycle_transition", c.transition_id)


def add_trust_credential(session: Session, c: TrustCredentialContract) -> TrustCredential:
    expected = public_key_fingerprint_sha256(c.public_key_pem)
    if expected != c.fingerprint_sha256:
        raise DomainValidationError("credential fingerprint mismatch", ["CREDENTIAL_FINGERPRINT_MISMATCH"])
    row = TrustCredential(
        credential_id=c.credential_id,
        subject_ref=c.subject_ref,
        credential_type=c.credential_type,
        public_key_pem=c.public_key_pem,
        fingerprint_sha256=c.fingerprint_sha256,
        issuer_ref=c.issuer_ref,
        valid_from=c.valid_from,
        valid_until=c.valid_until,
        status=c.status,
        revoked_at=c.revoked_at,
        provenance_ref=c.provenance_ref,
    )
    return _commit(session, row, "trust_credential", c.credential_id)


def add_signature_record(session: Session, c: SignatureRecordContract) -> SignatureRecord:
    if session.get(TrustCredential, c.credential_ref) is None:
        raise DomainValidationError("credential not found", ["CREDENTIAL_NOT_FOUND"])
    row = SignatureRecord(**c.model_dump())
    return _commit(session, row, "signature_record", c.signature_id)


def add_agent_attestation(session: Session, c: AgentAttestationContract) -> AgentAttestation:
    if session.get(TrustCredential, c.credential_ref) is None:
        raise DomainValidationError("credential not found", ["CREDENTIAL_NOT_FOUND"])
    row = AgentAttestation(**c.model_dump())
    return _commit(session, row, "agent_attestation", c.attestation_id)
