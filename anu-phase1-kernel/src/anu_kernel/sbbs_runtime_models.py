from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import JSON, Boolean, DateTime, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from .db import Base


class TransformVersion(Base):
    __tablename__ = "transform_version"
    __table_args__ = (UniqueConstraint("transform_id", "version", name="uq_transform_id_version"),)
    row_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    transform_id: Mapped[str] = mapped_column(String(255), index=True)
    version: Mapped[str] = mapped_column(String(64), index=True)
    name: Mapped[str] = mapped_column(String(255))
    owner_ref: Mapped[str] = mapped_column(String(255), index=True)
    from_contract_ref: Mapped[str] = mapped_column(String(320), index=True)
    to_contract_ref: Mapped[str] = mapped_column(String(320), index=True)
    mapping: Mapped[dict] = mapped_column(JSON, default=dict)
    constants: Mapped[dict] = mapped_column(JSON, default=dict)
    semantic_preservation: Mapped[list] = mapped_column(JSON, default=list)
    lossy: Mapped[bool] = mapped_column(Boolean, default=False)
    effective_from: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    effective_to: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    lifecycle_state: Mapped[str] = mapped_column(String(32), default="ACTIVE", index=True)
    provenance_ref: Mapped[str] = mapped_column(String(255), index=True)
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), index=True)


class AdapterVersion(Base):
    __tablename__ = "adapter_version"
    __table_args__ = (UniqueConstraint("adapter_id", "version", name="uq_adapter_id_version"),)
    row_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    adapter_id: Mapped[str] = mapped_column(String(255), index=True)
    version: Mapped[str] = mapped_column(String(64), index=True)
    name: Mapped[str] = mapped_column(String(255))
    owner_ref: Mapped[str] = mapped_column(String(255), index=True)
    source_runtime_type: Mapped[str] = mapped_column(String(128), index=True)
    target_runtime_type: Mapped[str] = mapped_column(String(128), index=True)
    capability_scope: Mapped[list] = mapped_column(JSON, default=list)
    configuration: Mapped[dict] = mapped_column(JSON, default=dict)
    effective_from: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    effective_to: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    lifecycle_state: Mapped[str] = mapped_column(String(32), default="ACTIVE", index=True)
    provenance_ref: Mapped[str] = mapped_column(String(255), index=True)
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), index=True)


class CompatibilityEvidence(Base):
    __tablename__ = "compatibility_evidence"
    evidence_id: Mapped[str] = mapped_column(String(255), primary_key=True)
    from_capability_ref: Mapped[str] = mapped_column(String(320), index=True)
    from_operation: Mapped[str] = mapped_column(String(255))
    to_capability_ref: Mapped[str] = mapped_column(String(320), index=True)
    to_operation: Mapped[str] = mapped_column(String(255))
    compatible: Mapped[bool] = mapped_column(Boolean, index=True)
    direct: Mapped[bool] = mapped_column(Boolean)
    result_json: Mapped[dict] = mapped_column(JSON)
    request_hash: Mapped[str] = mapped_column(String(128), index=True)
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), index=True)


class ConnectionPlanVersion(Base):
    __tablename__ = "connection_plan_version"
    __table_args__ = (UniqueConstraint("plan_id", "version", name="uq_connection_plan_version"),)
    row_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    plan_id: Mapped[str] = mapped_column(String(255), index=True)
    version: Mapped[str] = mapped_column(String(64), index=True)
    from_capability: Mapped[str] = mapped_column(String(320), index=True)
    from_operation: Mapped[str] = mapped_column(String(255))
    to_capability: Mapped[str] = mapped_column(String(320), index=True)
    to_operation: Mapped[str] = mapped_column(String(255))
    from_box_ref: Mapped[str] = mapped_column(String(320), index=True)
    to_box_ref: Mapped[str] = mapped_column(String(320), index=True)
    contract_ref: Mapped[str | None] = mapped_column(String(320), nullable=True)
    transformation_refs: Mapped[list] = mapped_column(JSON, default=list)
    adapter_refs: Mapped[list] = mapped_column(JSON, default=list)
    policy_checks: Mapped[list] = mapped_column(JSON, default=list)
    security_context: Mapped[dict] = mapped_column(JSON, default=dict)
    retry_policy: Mapped[dict] = mapped_column(JSON, default=dict)
    observability_policy: Mapped[dict] = mapped_column(JSON, default=dict)
    compatibility_evidence: Mapped[list] = mapped_column(JSON, default=list)
    effective_from: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    effective_to: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    lifecycle_state: Mapped[str] = mapped_column(String(32), default="ACTIVE", index=True)
    provenance_ref: Mapped[str] = mapped_column(String(255), index=True)
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), index=True)


class AssemblyVersion(Base):
    __tablename__ = "assembly_version"
    __table_args__ = (UniqueConstraint("assembly_id", "version", name="uq_assembly_version"),)
    row_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    assembly_id: Mapped[str] = mapped_column(String(255), index=True)
    name: Mapped[str] = mapped_column(String(255))
    description: Mapped[str] = mapped_column(Text)
    owner_ref: Mapped[str] = mapped_column(String(255), index=True)
    version: Mapped[str] = mapped_column(String(64), index=True)
    capability_refs: Mapped[list] = mapped_column(JSON, default=list)
    connection_plan_refs: Mapped[list] = mapped_column(JSON, default=list)
    human_refs: Mapped[list] = mapped_column(JSON, default=list)
    agent_refs: Mapped[list] = mapped_column(JSON, default=list)
    policy_refs: Mapped[list] = mapped_column(JSON, default=list)
    decision_points: Mapped[list] = mapped_column(JSON, default=list)
    configuration: Mapped[dict] = mapped_column(JSON, default=dict)
    effective_from: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    effective_to: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    lifecycle_state: Mapped[str] = mapped_column(String(32), default="ACTIVE", index=True)
    provenance_ref: Mapped[str] = mapped_column(String(255), index=True)
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), index=True)


class WireExecutionRecord(Base):
    __tablename__ = "wire_execution_record"
    execution_id: Mapped[str] = mapped_column(String(255), primary_key=True)
    plan_ref: Mapped[str] = mapped_column(String(320), index=True)
    trace_id: Mapped[str] = mapped_column(String(255), index=True)
    status: Mapped[str] = mapped_column(String(32), index=True)
    selected_box_ref: Mapped[str | None] = mapped_column(String(320), nullable=True)
    input_payload: Mapped[dict] = mapped_column(JSON)
    output_payload: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    trace_json: Mapped[list] = mapped_column(JSON, default=list)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    completed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)


class AssemblyExecutionRecord(Base):
    __tablename__ = "assembly_execution_record"
    execution_id: Mapped[str] = mapped_column(String(255), primary_key=True)
    assembly_ref: Mapped[str] = mapped_column(String(320), index=True)
    trace_id: Mapped[str] = mapped_column(String(255), index=True)
    status: Mapped[str] = mapped_column(String(32), index=True)
    input_payload: Mapped[dict] = mapped_column(JSON)
    final_payload: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    connection_results: Mapped[list] = mapped_column(JSON, default=list)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    completed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)


class WriteBoxCandidate(Base):
    __tablename__ = "write_box_candidate"
    candidate_id: Mapped[str] = mapped_column(String(255), primary_key=True)
    intent: Mapped[str] = mapped_column(Text)
    actor_ref: Mapped[str] = mapped_column(String(255), index=True)
    capability_json: Mapped[dict] = mapped_column(JSON)
    smart_box_json: Mapped[dict] = mapped_column(JSON)
    specification: Mapped[str] = mapped_column(Text)
    knowledge_refs: Mapped[list] = mapped_column(JSON, default=list)
    rule_refs: Mapped[list] = mapped_column(JSON, default=list)
    examples: Mapped[list] = mapped_column(JSON, default=list)
    provenance_ref: Mapped[str] = mapped_column(String(255), index=True)
    recommended_action: Mapped[str] = mapped_column(String(32), index=True)
    existing_capability_refs: Mapped[list] = mapped_column(JSON, default=list)
    audit_json: Mapped[dict] = mapped_column(JSON)
    stage: Mapped[str] = mapped_column(String(32), default="DRAFT", index=True)
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), index=True)
    promoted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
