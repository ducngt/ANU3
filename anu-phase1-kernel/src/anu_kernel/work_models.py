from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import JSON, Boolean, DateTime, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from .db import Base


class WorkContractVersion(Base):
    __tablename__ = "work_contract_version"
    __table_args__ = (UniqueConstraint("work_type_id", "version", name="uq_work_contract_version"),)
    row_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    work_type_id: Mapped[str] = mapped_column(String(255), index=True)
    name: Mapped[str] = mapped_column(String(255))
    description: Mapped[str] = mapped_column(Text)
    version: Mapped[str] = mapped_column(String(64), index=True)
    owner_ref: Mapped[str] = mapped_column(String(255), index=True)
    goal: Mapped[str] = mapped_column(Text)
    scope: Mapped[dict] = mapped_column(JSON, default=dict)
    execution_class: Mapped[str] = mapped_column(String(8), index=True)
    allowed_autonomy: Mapped[str] = mapped_column(String(8), index=True)
    human_participants: Mapped[list] = mapped_column(JSON, default=list)
    agent_assignments: Mapped[list] = mapped_column(JSON, default=list)
    capability_refs: Mapped[list] = mapped_column(JSON, default=list)
    data_scope: Mapped[dict] = mapped_column(JSON, default=dict)
    knowledge_requirements: Mapped[list] = mapped_column(JSON, default=list)
    decision_points: Mapped[list] = mapped_column(JSON, default=list)
    approval_points: Mapped[list] = mapped_column(JSON, default=list)
    signature_policy_ref: Mapped[str | None] = mapped_column(String(320), nullable=True)
    evidence_requirements: Mapped[list] = mapped_column(JSON, default=list)
    risk_class: Mapped[str] = mapped_column(String(64), index=True)
    outcome_definition: Mapped[dict] = mapped_column(JSON, default=dict)
    escalation: Mapped[dict] = mapped_column(JSON, default=dict)
    failure_policy: Mapped[dict] = mapped_column(JSON, default=dict)
    trace_policy: Mapped[dict] = mapped_column(JSON, default=dict)
    retention: Mapped[dict] = mapped_column(JSON, default=dict)
    effective_from: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    effective_to: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    lifecycle_state: Mapped[str] = mapped_column(String(32), default="ACTIVE", index=True)
    provenance_ref: Mapped[str] = mapped_column(String(255), index=True)
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), index=True)


class WorkGraphVersion(Base):
    __tablename__ = "work_graph_version"
    __table_args__ = (UniqueConstraint("graph_id", "version", name="uq_work_graph_version"),)
    row_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    graph_id: Mapped[str] = mapped_column(String(255), index=True)
    work_type_ref: Mapped[str] = mapped_column(String(320), index=True)
    version: Mapped[str] = mapped_column(String(64), index=True)
    owner_ref: Mapped[str] = mapped_column(String(255), index=True)
    entry_node: Mapped[str] = mapped_column(String(255))
    nodes: Mapped[list] = mapped_column(JSON, default=list)
    effective_from: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    effective_to: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    lifecycle_state: Mapped[str] = mapped_column(String(32), default="ACTIVE", index=True)
    provenance_ref: Mapped[str] = mapped_column(String(255), index=True)
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), index=True)


class WorkExecutionPlanRecord(Base):
    __tablename__ = "work_execution_plan"
    plan_id: Mapped[str] = mapped_column(String(255), primary_key=True)
    work_type_ref: Mapped[str] = mapped_column(String(320), index=True)
    work_graph_ref: Mapped[str] = mapped_column(String(320), index=True)
    goal: Mapped[str] = mapped_column(Text)
    execution_class: Mapped[str] = mapped_column(String(8), index=True)
    autonomy_level: Mapped[str] = mapped_column(String(8), index=True)
    required_capability_refs: Mapped[list] = mapped_column(JSON, default=list)
    required_checks: Mapped[list] = mapped_column(JSON, default=list)
    decision_points: Mapped[list] = mapped_column(JSON, default=list)
    signature_points: Mapped[list] = mapped_column(JSON, default=list)
    fallback: Mapped[dict] = mapped_column(JSON, default=dict)
    trace_policy: Mapped[dict] = mapped_column(JSON, default=dict)
    provenance_ref: Mapped[str] = mapped_column(String(255), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)


class WorkInstanceRecord(Base):
    __tablename__ = "work_instance"
    work_id: Mapped[str] = mapped_column(String(255), primary_key=True)
    plan_ref: Mapped[str] = mapped_column(String(255), index=True)
    work_type_ref: Mapped[str] = mapped_column(String(320), index=True)
    work_graph_ref: Mapped[str] = mapped_column(String(320), index=True)
    execution_class: Mapped[str] = mapped_column(String(8), index=True)
    autonomy_level: Mapped[str] = mapped_column(String(8), index=True)
    state: Mapped[str] = mapped_column(String(32), index=True)
    requester_ref: Mapped[str] = mapped_column(String(255), index=True)
    context: Mapped[dict] = mapped_column(JSON, default=dict)
    trace_id: Mapped[str] = mapped_column(String(255), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)


class WorkTaskRecord(Base):
    __tablename__ = "work_task_record"
    task_id: Mapped[str] = mapped_column(String(255), primary_key=True)
    work_id: Mapped[str] = mapped_column(String(255), index=True)
    node_id: Mapped[str] = mapped_column(String(255), index=True)
    actor_ref: Mapped[str] = mapped_column(String(255), index=True)
    actor_kind: Mapped[str] = mapped_column(String(32), index=True)
    action: Mapped[str] = mapped_column(String(255), index=True)
    input_payload: Mapped[dict] = mapped_column(JSON, default=dict)
    output_payload: Mapped[dict] = mapped_column(JSON, default=dict)
    evidence_refs: Mapped[list] = mapped_column(JSON, default=list)
    authority_ref: Mapped[str | None] = mapped_column(String(255), nullable=True)
    delegation_ref: Mapped[str | None] = mapped_column(String(255), nullable=True)
    policy_ref: Mapped[str | None] = mapped_column(String(320), nullable=True)
    signature_ref: Mapped[str | None] = mapped_column(String(255), nullable=True)
    attestation_ref: Mapped[str | None] = mapped_column(String(255), nullable=True)
    artifact_ref: Mapped[str | None] = mapped_column(String(255), nullable=True)
    provenance_ref: Mapped[str] = mapped_column(String(255), index=True)
    status: Mapped[str] = mapped_column(String(32), index=True)
    reason_codes: Mapped[list] = mapped_column(JSON, default=list)
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)


class WorkTransitionRecord(Base):
    __tablename__ = "work_transition_record"
    transition_id: Mapped[str] = mapped_column(String(255), primary_key=True)
    work_id: Mapped[str] = mapped_column(String(255), index=True)
    actor_ref: Mapped[str] = mapped_column(String(255), index=True)
    actor_kind: Mapped[str] = mapped_column(String(32), index=True)
    from_state: Mapped[str] = mapped_column(String(32), index=True)
    to_state: Mapped[str] = mapped_column(String(32), index=True)
    reason: Mapped[str] = mapped_column(Text)
    evidence_refs: Mapped[list] = mapped_column(JSON, default=list)
    authority_ref: Mapped[str | None] = mapped_column(String(255), nullable=True)
    delegation_ref: Mapped[str | None] = mapped_column(String(255), nullable=True)
    policy_ref: Mapped[str | None] = mapped_column(String(320), nullable=True)
    signature_ref: Mapped[str | None] = mapped_column(String(255), nullable=True)
    attestation_ref: Mapped[str | None] = mapped_column(String(255), nullable=True)
    artifact_ref: Mapped[str | None] = mapped_column(String(255), nullable=True)
    provenance_ref: Mapped[str] = mapped_column(String(255), index=True)
    applied: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    reason_codes: Mapped[list] = mapped_column(JSON, default=list)
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)


class HandoverRecord(Base):
    __tablename__ = "work_handover_record"
    handover_id: Mapped[str] = mapped_column(String(255), primary_key=True)
    work_id: Mapped[str] = mapped_column(String(255), index=True)
    actor_ref: Mapped[str] = mapped_column(String(255), index=True)
    from_state: Mapped[str] = mapped_column(String(32), index=True)
    reason_codes: Mapped[list] = mapped_column(JSON, default=list)
    human_target_ref: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    preserved_state: Mapped[bool] = mapped_column(Boolean, default=True)
    provenance_ref: Mapped[str] = mapped_column(String(255), index=True)
    status: Mapped[str] = mapped_column(String(32), default="OPEN", index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
