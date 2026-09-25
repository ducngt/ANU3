from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class KernelModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class LifecycleState(str, Enum):
    DRAFT = "DRAFT"
    ACTIVE = "ACTIVE"
    SUSPENDED = "SUSPENDED"
    SUPERSEDED = "SUPERSEDED"
    REVOKED = "REVOKED"
    DEPRECATED = "DEPRECATED"
    RETIRED = "RETIRED"
    ARCHIVED = "ARCHIVED"


class SubjectType(str, Enum):
    HUMAN = "HUMAN"
    AGENT = "AGENT"
    ORGANIZATION = "ORGANIZATION"
    SERVICE = "SERVICE"
    DEVICE = "DEVICE"
    CAPABILITY = "CAPABILITY"
    WORK = "WORK"
    EVIDENCE = "EVIDENCE"
    POLICY = "POLICY"
    DECISION = "DECISION"
    ARTIFACT = "ARTIFACT"
    DATA = "DATA"


class Effect(str, Enum):
    ALLOW = "ALLOW"
    DENY = "DENY"
    REQUIRE_REVIEW = "REQUIRE_REVIEW"
    REQUIRE_SIGNATURE = "REQUIRE_SIGNATURE"


class ObjectRef(KernelModel):
    id: str
    semantic_type: str
    version: str | None = None


class EffectivePeriod(KernelModel):
    valid_from: datetime
    valid_until: datetime | None = None

    @model_validator(mode="after")
    def validate_period(self) -> "EffectivePeriod":
        if self.valid_until is not None and self.valid_until <= self.valid_from:
            raise ValueError("valid_until must be after valid_from")
        return self


class IdentityContract(KernelModel):
    identity_id: str
    subject_id: str
    subject_type: SubjectType
    assurance_level: str = "BASIC"
    status: str = "ACTIVE"
    credential_refs: list[str] = Field(default_factory=list)
    aliases: list[str] = Field(default_factory=list)
    effective_period: EffectivePeriod
    lifecycle_state: LifecycleState = LifecycleState.ACTIVE
    provenance_ref: str | None = None


class SemanticDefinitionContract(KernelModel):
    semantic_id: str
    canonical_name: str
    definition: str
    namespace: str = "urn:anu:semantic"
    semantic_kind: str
    owner_ref: str
    context_ref: str | None = None
    relations: list[dict[str, Any]] = Field(default_factory=list)
    mappings: list[dict[str, Any]] = Field(default_factory=list)
    version: str
    effective_period: EffectivePeriod
    lifecycle_state: LifecycleState = LifecycleState.ACTIVE
    provenance_ref: str | None = None


class RoleAssignmentContract(KernelModel):
    assignment_id: str
    subject_ref: str
    role_ref: str
    context_ref: str
    assigned_by: str
    basis_ref: str | None = None
    effective_period: EffectivePeriod
    lifecycle_state: LifecycleState = LifecycleState.ACTIVE
    provenance_ref: str | None = None


class CompetenceAssertionContract(KernelModel):
    assertion_id: str
    subject_ref: str
    competence_ref: str
    level: str
    scope: dict[str, Any] = Field(default_factory=dict)
    evidence_refs: list[str] = Field(default_factory=list)
    asserted_by: str
    validation_state: str = "VALIDATED"
    effective_period: EffectivePeriod
    lifecycle_state: LifecycleState = LifecycleState.ACTIVE
    provenance_ref: str | None = None


class AuthorityScope(KernelModel):
    institution: str | None = None
    domain: str | None = None
    resource: str | None = None
    action: str | None = None
    context: str | None = None


class AuthorityGrantContract(KernelModel):
    authority_id: str
    subject_ref: str
    subject_type: SubjectType
    authority_type: str
    basis_ref: str
    issuer_ref: str
    scope: AuthorityScope
    consequence_class: str
    competence_requirements: list[str] = Field(default_factory=list)
    delegation_allowed: bool = False
    delegation_constraints: dict[str, Any] = Field(default_factory=dict)
    effective_period: EffectivePeriod
    policy_refs: list[str] = Field(default_factory=list)
    lifecycle_state: LifecycleState = LifecycleState.ACTIVE
    provenance_ref: str | None = None

    @model_validator(mode="after")
    def no_agent_standing_authority(self) -> "AuthorityGrantContract":
        if self.subject_type == SubjectType.AGENT:
            raise ValueError("AGENT IDENTITY != PERMANENT AUTHORITY: use delegation")
        return self


class DelegationGrantContract(KernelModel):
    delegation_id: str
    delegator_ref: str
    delegatee_ref: str
    authority_ref: str
    delegated_scope: AuthorityScope
    purpose: str
    conditions: list[dict[str, Any]] = Field(default_factory=list)
    valid_from: datetime
    valid_until: datetime
    redelegation_allowed: bool = False
    revocation_policy_ref: str | None = None
    issued_under_policy: str
    lifecycle_state: LifecycleState = LifecycleState.ACTIVE
    provenance_ref: str | None = None

    @model_validator(mode="after")
    def validate_period(self) -> "DelegationGrantContract":
        if self.valid_until <= self.valid_from:
            raise ValueError("valid_until must be after valid_from")
        return self


class DelegationRevocationContract(KernelModel):
    revocation_id: str
    delegation_id: str
    effective_time: datetime
    recorded_at: datetime
    actor_ref: str
    reason: str
    provenance_ref: str | None = None


class PolicyContract(KernelModel):
    policy_id: str
    policy_type: str
    issuer_ref: str
    authority_basis_ref: str
    version: str
    scope: dict[str, Any] = Field(default_factory=dict)
    conditions: list[dict[str, Any]] = Field(default_factory=list)
    effects: list[dict[str, Any]] = Field(default_factory=list)
    effective_period: EffectivePeriod
    supersedes_ref: str | None = None
    exception_rules: list[dict[str, Any]] = Field(default_factory=list)
    lifecycle_state: LifecycleState = LifecycleState.ACTIVE
    provenance_ref: str | None = None


class AuthorityEvaluationRequest(KernelModel):
    subject_ref: str
    subject_type: SubjectType
    action: str
    resource: str | None = None
    context_ref: str | None = None
    at: datetime
    competence_refs: list[str] = Field(default_factory=list)


class PolicyEvaluationRequest(KernelModel):
    subject_ref: str
    role_context: list[str] = Field(default_factory=list)
    authority_refs: list[str] = Field(default_factory=list)
    delegation_refs: list[str] = Field(default_factory=list)
    resource: str | None = None
    action: str
    context: str | None = None
    risk: str | None = None
    at: datetime


class PolicyDecisionContract(KernelModel):
    decision_id: str
    policy_refs: list[str]
    evaluated_at: datetime
    subject_ref: str
    role_context: list[str] = Field(default_factory=list)
    authority_refs: list[str] = Field(default_factory=list)
    delegation_refs: list[str] = Field(default_factory=list)
    resource: str | None = None
    action: str
    context: str | None = None
    risk: str | None = None
    effect: Effect
    obligations: list[str] = Field(default_factory=list)
    reason_codes: list[str] = Field(default_factory=list)
    trace_ref: str | None = None


class ProvenanceRecordContract(KernelModel):
    provenance_id: str
    entity_ref: str
    activity_ref: str | None = None
    actor_ref: str
    work_ref: str | None = None
    capability_ref: str | None = None
    tool_ref: str | None = None
    model_ref: str | None = None
    source_refs: list[str] = Field(default_factory=list)
    input_refs: list[str] = Field(default_factory=list)
    output_refs: list[str] = Field(default_factory=list)
    transformation_ref: str | None = None
    effective_time: datetime
    recorded_time: datetime
    integrity_ref: str | None = None
    previous_provenance_refs: list[str] = Field(default_factory=list)


class AuditEventContract(KernelModel):
    audit_id: str
    event_type: str
    actor_identity: str
    role_context: list[str] = Field(default_factory=list)
    authority_ref: str | None = None
    delegation_ref: str | None = None
    policy_refs: list[str] = Field(default_factory=list)
    action: str
    target_ref: str | None = None
    result: str
    work_ref: str | None = None
    trace_id: str
    occurred_at: datetime
    recorded_at: datetime
    provenance_ref: str | None = None
    integrity_ref: str | None = None


class LifecycleTransitionContract(KernelModel):
    transition_id: str
    object_ref: str
    from_state: LifecycleState
    to_state: LifecycleState
    effective_time: datetime
    recorded_time: datetime
    reason: str
    actor_ref: str
    authority_ref: str | None = None
    policy_ref: str | None = None
    superseded_by_ref: str | None = None
    provenance_ref: str | None = None


class KernelEventEnvelope(KernelModel):
    event_id: str
    event_type: str
    source: str
    subject: str
    time: datetime
    effective_time: datetime | None = None
    recorded_time: datetime
    work_id: str | None = None
    actor_identity: str
    role: str | None = None
    authority_ref: str | None = None
    delegation_ref: str | None = None
    policy_version: str | None = None
    artifact_ref: str | None = None
    integrity_ref: str | None = None
    signature_ref: str | None = None
    provenance_ref: str | None = None
    correlation_id: str | None = None
    causation_id: str | None = None
    schema_version: str = "1.0.0"


class DecisionRecordContract(KernelModel):
    decision_id: str
    subject_ref: str
    role_refs: list[str]
    authority_ref: str
    delegation_ref: str | None = None
    policy_ref: str
    evidence_refs: list[str]
    artifact_ref: str | None = None
    signature_ref: str | None = None
    outcome: str
    effective_time: datetime
    recorded_time: datetime
    provenance_ref: str


class ReplayRequestContract(KernelModel):
    target_ref: str
    perspective: Literal["AS_EFFECTIVE_AT", "AS_KNOWN_AT"] = "AS_EFFECTIVE_AT"
    effective_at: datetime | None = None
    recorded_at: datetime | None = None

    @model_validator(mode="after")
    def require_time(self) -> "ReplayRequestContract":
        if self.perspective == "AS_EFFECTIVE_AT" and self.effective_at is None:
            raise ValueError("effective_at is required for AS_EFFECTIVE_AT")
        if self.perspective == "AS_KNOWN_AT" and self.recorded_at is None:
            raise ValueError("recorded_at is required for AS_KNOWN_AT")
        return self


class ReplayResultContract(KernelModel):
    target_ref: str
    perspective: str
    reconstructed_state: dict[str, Any]
    identity_refs: list[str] = Field(default_factory=list)
    role_assignments: list[str] = Field(default_factory=list)
    competence_assertions: list[str] = Field(default_factory=list)
    authority_refs: list[str] = Field(default_factory=list)
    delegation_refs: list[str] = Field(default_factory=list)
    policy_versions: list[str] = Field(default_factory=list)
    evidence_refs: list[str] = Field(default_factory=list)
    lifecycle_state: str | None = None
    provenance_chain: list[str] = Field(default_factory=list)
    source_event_refs: list[str] = Field(default_factory=list)
    integrity_status: str = "NOT_VERIFIED"
    completeness_status: str = "COMPLETE"
    warnings: list[str] = Field(default_factory=list)

# --- Tranche 03: authentication boundary, trust, signature and attestation ---

class AuthenticationContext(KernelModel):
    identity_id: str
    subject_ref: str
    subject_type: SubjectType
    credential_ref: str
    authentication_method: str
    assurance_level: str
    authenticated_at: datetime
    issuer: str | None = None


class GovernedActionRequest(KernelModel):
    action: str
    resource: str | None = None
    context: str | None = None
    risk: str | None = None
    at: datetime
    competence_refs: list[str] = Field(default_factory=list)


class EnforcementDecisionContract(KernelModel):
    subject_ref: str
    authenticated: bool
    authorized: bool
    authority_valid: bool
    policy_effect: Effect
    allowed_to_proceed: bool
    authority_refs: list[str] = Field(default_factory=list)
    delegation_refs: list[str] = Field(default_factory=list)
    policy_refs: list[str] = Field(default_factory=list)
    obligations: list[str] = Field(default_factory=list)
    reason_codes: list[str] = Field(default_factory=list)


class TrustCredentialContract(KernelModel):
    credential_id: str
    subject_ref: str
    credential_type: Literal["ED25519_PUBLIC_KEY"] = "ED25519_PUBLIC_KEY"
    public_key_pem: str
    fingerprint_sha256: str
    issuer_ref: str
    valid_from: datetime
    valid_until: datetime | None = None
    status: Literal["ACTIVE", "SUSPENDED", "REVOKED", "EXPIRED"] = "ACTIVE"
    revoked_at: datetime | None = None
    provenance_ref: str | None = None

    @model_validator(mode="after")
    def validate_lifecycle(self) -> "TrustCredentialContract":
        if self.valid_until is not None and self.valid_until <= self.valid_from:
            raise ValueError("valid_until must be after valid_from")
        if self.status == "REVOKED" and self.revoked_at is None:
            raise ValueError("revoked_at is required when credential is REVOKED")
        return self


class SignatureRecordContract(KernelModel):
    signature_id: str
    signer_identity_ref: str
    signer_type: Literal["HUMAN"] = "HUMAN"
    signer_role_ref: str
    authority_ref: str
    credential_ref: str
    signature_method: Literal["ED25519"] = "ED25519"
    intent: str
    artifact_ref: str
    artifact_version: str
    artifact_hash: str
    work_ref: str | None = None
    decision_ref: str | None = None
    policy_version: str
    delegation_ref: str | None = None
    signed_at: datetime
    signature_value: str
    provenance_ref: str | None = None


class SignatureVerificationResult(KernelModel):
    signature_id: str
    cryptographically_valid: bool
    credential_valid: bool
    role_valid: bool
    authority_valid: bool
    institutional_valid: bool
    reason_codes: list[str] = Field(default_factory=list)


class AgentAttestationContract(KernelModel):
    attestation_id: str
    agent_ref: str
    agent_version: str
    owner_ref: str
    runtime_ref: str
    model_dependency: str | None = None
    purpose: str
    work_ref: str
    action: str
    capability_ref: str
    tool_ref: str | None = None
    delegation_ref: str | None = None
    policy_version: str
    input_refs: list[str] = Field(default_factory=list)
    artifact_ref: str
    artifact_hash: str
    timestamp: datetime
    credential_ref: str
    attestation_signature: str
    provenance_ref: str | None = None
    consequential: bool = True

    @model_validator(mode="after")
    def require_delegation_for_consequential_action(self) -> "AgentAttestationContract":
        if self.consequential and not self.delegation_ref:
            raise ValueError("consequential Agent action requires delegation_ref")
        return self


class AttestationVerificationResult(KernelModel):
    attestation_id: str
    cryptographically_valid: bool
    credential_valid: bool
    delegation_valid: bool
    attestation_valid: bool
    reason_codes: list[str] = Field(default_factory=list)


class IntegrityHashRequest(KernelModel):
    artifact: Any


class IntegrityHashResult(KernelModel):
    algorithm: Literal["SHA-256"] = "SHA-256"
    integrity_ref: str
