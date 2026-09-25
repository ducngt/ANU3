from __future__ import annotations

import os
from datetime import datetime, timezone

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, Integer, String, Text, create_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker
from sqlalchemy.pool import StaticPool


DATABASE_URL = os.getenv("ANU_DATABASE_URL", "sqlite+pysqlite:///./anu_kernel.db")


class Base(DeclarativeBase):
    pass


class KernelObject(Base):
    __tablename__ = "kernel_object"
    id: Mapped[str] = mapped_column(String(255), primary_key=True)
    semantic_type: Mapped[str] = mapped_column(String(255), index=True)
    object_kind: Mapped[str] = mapped_column(String(64), index=True)
    lifecycle_state: Mapped[str] = mapped_column(String(32), default="ACTIVE", index=True)
    current_version: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))


class IdentityRecord(Base):
    __tablename__ = "identity_record"
    identity_id: Mapped[str] = mapped_column(String(255), primary_key=True)
    subject_id: Mapped[str] = mapped_column(String(255), index=True)
    subject_type: Mapped[str] = mapped_column(String(32), index=True)
    assurance_level: Mapped[str] = mapped_column(String(32), default="BASIC")
    status: Mapped[str] = mapped_column(String(32), default="ACTIVE")
    credential_refs: Mapped[list] = mapped_column(JSON, default=list)
    aliases: Mapped[list] = mapped_column(JSON, default=list)
    effective_from: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    effective_to: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), index=True)
    lifecycle_state: Mapped[str] = mapped_column(String(32), default="ACTIVE")
    provenance_ref: Mapped[str | None] = mapped_column(String(255), nullable=True)


class SemanticDefinition(Base):
    __tablename__ = "semantic_definition"
    row_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    semantic_id: Mapped[str] = mapped_column(String(255), index=True)
    canonical_name: Mapped[str] = mapped_column(String(255))
    definition: Mapped[str] = mapped_column(Text)
    namespace: Mapped[str] = mapped_column(String(255))
    semantic_kind: Mapped[str] = mapped_column(String(64))
    owner_ref: Mapped[str] = mapped_column(String(255))
    context_ref: Mapped[str | None] = mapped_column(String(255), nullable=True)
    relations: Mapped[list] = mapped_column(JSON, default=list)
    mappings: Mapped[list] = mapped_column(JSON, default=list)
    version: Mapped[str] = mapped_column(String(64))
    effective_from: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    effective_to: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), index=True)
    lifecycle_state: Mapped[str] = mapped_column(String(32), default="ACTIVE")
    provenance_ref: Mapped[str | None] = mapped_column(String(255), nullable=True)


class RoleAssignment(Base):
    __tablename__ = "role_assignment"
    assignment_id: Mapped[str] = mapped_column(String(255), primary_key=True)
    subject_ref: Mapped[str] = mapped_column(String(255), index=True)
    role_ref: Mapped[str] = mapped_column(String(255), index=True)
    context_ref: Mapped[str] = mapped_column(String(255), index=True)
    assigned_by: Mapped[str] = mapped_column(String(255))
    basis_ref: Mapped[str | None] = mapped_column(String(255), nullable=True)
    effective_from: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    effective_to: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), index=True)
    lifecycle_state: Mapped[str] = mapped_column(String(32), default="ACTIVE")
    provenance_ref: Mapped[str | None] = mapped_column(String(255), nullable=True)


class CompetenceAssertion(Base):
    __tablename__ = "competence_assertion"
    assertion_id: Mapped[str] = mapped_column(String(255), primary_key=True)
    subject_ref: Mapped[str] = mapped_column(String(255), index=True)
    competence_ref: Mapped[str] = mapped_column(String(255), index=True)
    level: Mapped[str] = mapped_column(String(64))
    scope: Mapped[dict] = mapped_column(JSON, default=dict)
    evidence_refs: Mapped[list] = mapped_column(JSON, default=list)
    asserted_by: Mapped[str] = mapped_column(String(255))
    validation_state: Mapped[str] = mapped_column(String(32), default="VALIDATED")
    effective_from: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    effective_to: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), index=True)
    lifecycle_state: Mapped[str] = mapped_column(String(32), default="ACTIVE")
    provenance_ref: Mapped[str | None] = mapped_column(String(255), nullable=True)


class AuthorityGrant(Base):
    __tablename__ = "authority_grant"
    authority_id: Mapped[str] = mapped_column(String(255), primary_key=True)
    subject_ref: Mapped[str] = mapped_column(String(255), index=True)
    subject_type: Mapped[str] = mapped_column(String(32), index=True)
    authority_type: Mapped[str] = mapped_column(String(255), index=True)
    basis_ref: Mapped[str] = mapped_column(String(255))
    issuer_ref: Mapped[str] = mapped_column(String(255))
    scope: Mapped[dict] = mapped_column(JSON, default=dict)
    consequence_class: Mapped[str] = mapped_column(String(64))
    competence_requirements: Mapped[list] = mapped_column(JSON, default=list)
    delegation_allowed: Mapped[bool] = mapped_column(Boolean, default=False)
    delegation_constraints: Mapped[dict] = mapped_column(JSON, default=dict)
    effective_from: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    effective_to: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), index=True)
    policy_refs: Mapped[list] = mapped_column(JSON, default=list)
    lifecycle_state: Mapped[str] = mapped_column(String(32), default="ACTIVE", index=True)
    provenance_ref: Mapped[str | None] = mapped_column(String(255), nullable=True)


class DelegationGrant(Base):
    __tablename__ = "delegation_grant"
    delegation_id: Mapped[str] = mapped_column(String(255), primary_key=True)
    delegator_ref: Mapped[str] = mapped_column(String(255), index=True)
    delegatee_ref: Mapped[str] = mapped_column(String(255), index=True)
    authority_ref: Mapped[str] = mapped_column(String(255), ForeignKey("authority_grant.authority_id"), index=True)
    delegated_scope: Mapped[dict] = mapped_column(JSON, default=dict)
    purpose: Mapped[str] = mapped_column(Text)
    conditions: Mapped[list] = mapped_column(JSON, default=list)
    valid_from: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    valid_until: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), index=True)
    redelegation_allowed: Mapped[bool] = mapped_column(Boolean, default=False)
    revocation_policy_ref: Mapped[str | None] = mapped_column(String(255), nullable=True)
    issued_under_policy: Mapped[str] = mapped_column(String(255))
    lifecycle_state: Mapped[str] = mapped_column(String(32), default="ACTIVE", index=True)
    provenance_ref: Mapped[str | None] = mapped_column(String(255), nullable=True)


class DelegationRevocation(Base):
    __tablename__ = "delegation_revocation"
    revocation_id: Mapped[str] = mapped_column(String(255), primary_key=True)
    delegation_id: Mapped[str] = mapped_column(String(255), ForeignKey("delegation_grant.delegation_id"), index=True)
    effective_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), index=True)
    actor_ref: Mapped[str] = mapped_column(String(255))
    reason: Mapped[str] = mapped_column(Text)
    provenance_ref: Mapped[str | None] = mapped_column(String(255), nullable=True)


class PolicyVersion(Base):
    __tablename__ = "policy_version"
    row_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    policy_id: Mapped[str] = mapped_column(String(255), index=True)
    policy_type: Mapped[str] = mapped_column(String(128))
    issuer_ref: Mapped[str] = mapped_column(String(255))
    authority_basis_ref: Mapped[str] = mapped_column(String(255))
    version: Mapped[str] = mapped_column(String(64), index=True)
    scope: Mapped[dict] = mapped_column(JSON, default=dict)
    conditions: Mapped[list] = mapped_column(JSON, default=list)
    effects: Mapped[list] = mapped_column(JSON, default=list)
    effective_from: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    effective_to: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), index=True)
    supersedes_ref: Mapped[str | None] = mapped_column(String(255), nullable=True)
    exception_rules: Mapped[list] = mapped_column(JSON, default=list)
    lifecycle_state: Mapped[str] = mapped_column(String(32), default="ACTIVE", index=True)
    provenance_ref: Mapped[str | None] = mapped_column(String(255), nullable=True)


class ProvenanceRecord(Base):
    __tablename__ = "provenance_record"
    provenance_id: Mapped[str] = mapped_column(String(255), primary_key=True)
    entity_ref: Mapped[str] = mapped_column(String(255), index=True)
    activity_ref: Mapped[str | None] = mapped_column(String(255), nullable=True)
    actor_ref: Mapped[str] = mapped_column(String(255), index=True)
    work_ref: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    capability_ref: Mapped[str | None] = mapped_column(String(255), nullable=True)
    tool_ref: Mapped[str | None] = mapped_column(String(255), nullable=True)
    model_ref: Mapped[str | None] = mapped_column(String(255), nullable=True)
    source_refs: Mapped[list] = mapped_column(JSON, default=list)
    input_refs: Mapped[list] = mapped_column(JSON, default=list)
    output_refs: Mapped[list] = mapped_column(JSON, default=list)
    transformation_ref: Mapped[str | None] = mapped_column(String(255), nullable=True)
    effective_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    recorded_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    integrity_ref: Mapped[str | None] = mapped_column(String(255), nullable=True)
    previous_provenance_refs: Mapped[list] = mapped_column(JSON, default=list)


class AuditEvent(Base):
    __tablename__ = "audit_event"
    audit_id: Mapped[str] = mapped_column(String(255), primary_key=True)
    event_type: Mapped[str] = mapped_column(String(255), index=True)
    actor_identity: Mapped[str] = mapped_column(String(255), index=True)
    role_context: Mapped[list] = mapped_column(JSON, default=list)
    authority_ref: Mapped[str | None] = mapped_column(String(255), nullable=True)
    delegation_ref: Mapped[str | None] = mapped_column(String(255), nullable=True)
    policy_refs: Mapped[list] = mapped_column(JSON, default=list)
    action: Mapped[str] = mapped_column(String(255), index=True)
    target_ref: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    result: Mapped[str] = mapped_column(String(64))
    work_ref: Mapped[str | None] = mapped_column(String(255), nullable=True)
    trace_id: Mapped[str] = mapped_column(String(255), index=True)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    provenance_ref: Mapped[str | None] = mapped_column(String(255), nullable=True)
    integrity_ref: Mapped[str | None] = mapped_column(String(255), nullable=True)


class LifecycleTransition(Base):
    __tablename__ = "lifecycle_transition"
    transition_id: Mapped[str] = mapped_column(String(255), primary_key=True)
    object_ref: Mapped[str] = mapped_column(String(255), index=True)
    from_state: Mapped[str] = mapped_column(String(32))
    to_state: Mapped[str] = mapped_column(String(32))
    effective_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    recorded_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    reason: Mapped[str] = mapped_column(Text)
    actor_ref: Mapped[str] = mapped_column(String(255))
    authority_ref: Mapped[str | None] = mapped_column(String(255), nullable=True)
    policy_ref: Mapped[str | None] = mapped_column(String(255), nullable=True)
    superseded_by_ref: Mapped[str | None] = mapped_column(String(255), nullable=True)
    provenance_ref: Mapped[str | None] = mapped_column(String(255), nullable=True)


class KernelEvent(Base):
    __tablename__ = "kernel_event"
    event_id: Mapped[str] = mapped_column(String(255), primary_key=True)
    event_type: Mapped[str] = mapped_column(String(255), index=True)
    source: Mapped[str] = mapped_column(String(255))
    subject: Mapped[str] = mapped_column(String(255), index=True)
    time: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    effective_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    recorded_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    work_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    actor_identity: Mapped[str] = mapped_column(String(255), index=True)
    role: Mapped[str | None] = mapped_column(String(255), nullable=True)
    authority_ref: Mapped[str | None] = mapped_column(String(255), nullable=True)
    delegation_ref: Mapped[str | None] = mapped_column(String(255), nullable=True)
    policy_version: Mapped[str | None] = mapped_column(String(255), nullable=True)
    artifact_ref: Mapped[str | None] = mapped_column(String(255), nullable=True)
    integrity_ref: Mapped[str | None] = mapped_column(String(255), nullable=True)
    signature_ref: Mapped[str | None] = mapped_column(String(255), nullable=True)
    provenance_ref: Mapped[str | None] = mapped_column(String(255), nullable=True)
    correlation_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    causation_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    schema_version: Mapped[str] = mapped_column(String(64), default="1.0.0")


class DecisionRecord(Base):
    __tablename__ = "decision_record"
    decision_id: Mapped[str] = mapped_column(String(255), primary_key=True)
    subject_ref: Mapped[str] = mapped_column(String(255), index=True)
    role_refs: Mapped[list] = mapped_column(JSON, default=list)
    authority_ref: Mapped[str] = mapped_column(String(255), index=True)
    delegation_ref: Mapped[str | None] = mapped_column(String(255), nullable=True)
    policy_ref: Mapped[str] = mapped_column(String(255), index=True)
    evidence_refs: Mapped[list] = mapped_column(JSON, default=list)
    artifact_ref: Mapped[str | None] = mapped_column(String(255), nullable=True)
    signature_ref: Mapped[str | None] = mapped_column(String(255), nullable=True)
    outcome: Mapped[str] = mapped_column(String(64))
    effective_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    recorded_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    provenance_ref: Mapped[str] = mapped_column(String(255), index=True)


class TrustCredential(Base):
    __tablename__ = "trust_credential"
    credential_id: Mapped[str] = mapped_column(String(255), primary_key=True)
    subject_ref: Mapped[str] = mapped_column(String(255), index=True)
    credential_type: Mapped[str] = mapped_column(String(64))
    public_key_pem: Mapped[str] = mapped_column(Text)
    fingerprint_sha256: Mapped[str] = mapped_column(String(128), index=True)
    issuer_ref: Mapped[str] = mapped_column(String(255))
    valid_from: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    valid_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    status: Mapped[str] = mapped_column(String(32), default="ACTIVE", index=True)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), index=True)
    provenance_ref: Mapped[str | None] = mapped_column(String(255), nullable=True)


class SignatureRecord(Base):
    __tablename__ = "signature_record"
    signature_id: Mapped[str] = mapped_column(String(255), primary_key=True)
    signer_identity_ref: Mapped[str] = mapped_column(String(255), index=True)
    signer_type: Mapped[str] = mapped_column(String(32))
    signer_role_ref: Mapped[str] = mapped_column(String(255))
    authority_ref: Mapped[str] = mapped_column(String(255), index=True)
    credential_ref: Mapped[str] = mapped_column(String(255), ForeignKey("trust_credential.credential_id"), index=True)
    signature_method: Mapped[str] = mapped_column(String(64))
    intent: Mapped[str] = mapped_column(Text)
    artifact_ref: Mapped[str] = mapped_column(String(255), index=True)
    artifact_version: Mapped[str] = mapped_column(String(128))
    artifact_hash: Mapped[str] = mapped_column(String(255))
    work_ref: Mapped[str | None] = mapped_column(String(255), nullable=True)
    decision_ref: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    policy_version: Mapped[str] = mapped_column(String(255))
    delegation_ref: Mapped[str | None] = mapped_column(String(255), nullable=True)
    signed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    signature_value: Mapped[str] = mapped_column(Text)
    provenance_ref: Mapped[str | None] = mapped_column(String(255), nullable=True)
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), index=True)


class AgentAttestation(Base):
    __tablename__ = "agent_attestation"
    attestation_id: Mapped[str] = mapped_column(String(255), primary_key=True)
    agent_ref: Mapped[str] = mapped_column(String(255), index=True)
    agent_version: Mapped[str] = mapped_column(String(128))
    owner_ref: Mapped[str] = mapped_column(String(255))
    runtime_ref: Mapped[str] = mapped_column(String(255))
    model_dependency: Mapped[str | None] = mapped_column(String(255), nullable=True)
    purpose: Mapped[str] = mapped_column(Text)
    work_ref: Mapped[str] = mapped_column(String(255), index=True)
    action: Mapped[str] = mapped_column(String(255), index=True)
    capability_ref: Mapped[str] = mapped_column(String(255))
    tool_ref: Mapped[str | None] = mapped_column(String(255), nullable=True)
    delegation_ref: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    policy_version: Mapped[str] = mapped_column(String(255))
    input_refs: Mapped[list] = mapped_column(JSON, default=list)
    artifact_ref: Mapped[str] = mapped_column(String(255), index=True)
    artifact_hash: Mapped[str] = mapped_column(String(255))
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    credential_ref: Mapped[str] = mapped_column(String(255), ForeignKey("trust_credential.credential_id"), index=True)
    attestation_signature: Mapped[str] = mapped_column(Text)
    provenance_ref: Mapped[str | None] = mapped_column(String(255), nullable=True)
    consequential: Mapped[bool] = mapped_column(Boolean, default=True)
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), index=True)


def make_engine(url: str | None = None):
    db_url = url or DATABASE_URL
    connect_args = {"check_same_thread": False} if db_url.startswith("sqlite") else {}
    kwargs = {"future": True, "connect_args": connect_args}
    if db_url.startswith("sqlite") and ":memory:" in db_url:
        kwargs["poolclass"] = StaticPool
    return create_engine(db_url, **kwargs)


_runtime_engine = None
_session_factory = None


def get_runtime_engine():
    global _runtime_engine
    if _runtime_engine is None:
        _runtime_engine = make_engine()
    return _runtime_engine


def get_session_factory():
    global _session_factory
    if _session_factory is None:
        _session_factory = sessionmaker(
            bind=get_runtime_engine(), autoflush=False, autocommit=False, future=True
        )
    return _session_factory
