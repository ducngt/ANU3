from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import JSON, Boolean, DateTime, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from .db import Base


class SourceRegistry(Base):
    __tablename__ = "source_registry"
    source_id: Mapped[str] = mapped_column(String(255), primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    source_kind: Mapped[str] = mapped_column(String(64), index=True)
    owner_ref: Mapped[str] = mapped_column(String(255), index=True)
    description: Mapped[str | None] = mapped_column(Text(), nullable=True)
    synthetic_fixture: Mapped[bool] = mapped_column(Boolean, default=False)
    effective_from: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    effective_to: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    lifecycle_state: Mapped[str] = mapped_column(String(32), default="ACTIVE", index=True)
    provenance_ref: Mapped[str | None] = mapped_column(String(255), nullable=True)
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), index=True)


class SourceAuthorityMapping(Base):
    __tablename__ = "source_authority_mapping"
    mapping_id: Mapped[str] = mapped_column(String(255), primary_key=True)
    source_ref: Mapped[str] = mapped_column(String(255), index=True)
    semantic_type: Mapped[str] = mapped_column(String(255), index=True)
    authority_scope: Mapped[dict] = mapped_column(JSON, default=dict)
    authoritative: Mapped[bool] = mapped_column(Boolean, default=True)
    effective_from: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    effective_to: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    lifecycle_state: Mapped[str] = mapped_column(String(32), default="ACTIVE", index=True)
    provenance_ref: Mapped[str | None] = mapped_column(String(255), nullable=True)
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), index=True)


class DataContractVersion(Base):
    __tablename__ = "data_contract_version"
    __table_args__ = (UniqueConstraint("contract_id", "version", name="uq_data_contract_id_version"),)
    row_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    contract_id: Mapped[str] = mapped_column(String(255), index=True)
    data_type: Mapped[str] = mapped_column(String(128), index=True)
    semantic_definition: Mapped[str] = mapped_column(String(255), index=True)
    schema: Mapped[dict] = mapped_column(JSON)
    owner: Mapped[str] = mapped_column(String(255), index=True)
    authoritative_source: Mapped[str | None] = mapped_column(String(255), nullable=True)
    producers: Mapped[list] = mapped_column(JSON, default=list)
    consumers: Mapped[list] = mapped_column(JSON, default=list)
    freshness_requirement: Mapped[str | None] = mapped_column(String(255), nullable=True)
    quality_rules: Mapped[list] = mapped_column(JSON, default=list)
    provenance_requirement: Mapped[str] = mapped_column(String(64), default="REQUIRED")
    access_policy: Mapped[str | None] = mapped_column(String(255), nullable=True)
    privacy_class: Mapped[str] = mapped_column(String(64), default="INTERNAL")
    integrity_requirement: Mapped[str] = mapped_column(String(64), default="HASH")
    retention_rule: Mapped[str | None] = mapped_column(String(255), nullable=True)
    version: Mapped[str] = mapped_column(String(64), index=True)
    compatibility_policy: Mapped[str] = mapped_column(String(128))
    lifecycle_state: Mapped[str] = mapped_column(String(32), default="ACTIVE", index=True)
    provenance_ref: Mapped[str | None] = mapped_column(String(255), nullable=True)
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), index=True)


class DataObjectVersion(Base):
    __tablename__ = "data_object_version"
    version_id: Mapped[str] = mapped_column(String(255), primary_key=True)
    data_id: Mapped[str] = mapped_column(String(255), index=True)
    contract_ref: Mapped[str] = mapped_column(String(320), index=True)
    semantic_type: Mapped[str] = mapped_column(String(255), index=True)
    schema_version: Mapped[str] = mapped_column(String(64))
    subject_refs: Mapped[list] = mapped_column(JSON, default=list)
    source_system_id: Mapped[str] = mapped_column(String(255), index=True)
    source_record_ref: Mapped[str] = mapped_column(String(255))
    source_authority_scope: Mapped[dict] = mapped_column(JSON, default=dict)
    owner_ref: Mapped[str] = mapped_column(String(255), index=True)
    context_ref: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    effective_from: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    effective_to: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    recorded_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    epistemic_type: Mapped[str] = mapped_column(String(32), index=True)
    validation_state: Mapped[str] = mapped_column(String(32), index=True)
    provenance_ref: Mapped[str] = mapped_column(String(255), index=True)
    integrity_ref: Mapped[str | None] = mapped_column(String(255), nullable=True)
    access_policy_ref: Mapped[str | None] = mapped_column(String(255), nullable=True)
    retention_policy_ref: Mapped[str | None] = mapped_column(String(255), nullable=True)
    lifecycle_state: Mapped[str] = mapped_column(String(32), default="ACTIVE", index=True)
    payload: Mapped[dict] = mapped_column(JSON)
    supersedes_ref: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    synthetic_output: Mapped[bool] = mapped_column(Boolean, default=False)


class KnowledgeObjectVersion(Base):
    __tablename__ = "knowledge_object_version"
    __table_args__ = (UniqueConstraint("knowledge_id", "version", name="uq_knowledge_id_version"),)
    row_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    knowledge_id: Mapped[str] = mapped_column(String(255), index=True)
    title: Mapped[str] = mapped_column(String(512), nullable=False)
    semantic_type: Mapped[str] = mapped_column(String(255), index=True)
    epistemic_type: Mapped[str] = mapped_column(String(32), index=True)
    validation_state: Mapped[str] = mapped_column(String(32), index=True)
    source_refs: Mapped[list] = mapped_column(JSON, default=list)
    author_owner: Mapped[str] = mapped_column(String(255), index=True)
    context_ref: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    relations: Mapped[list] = mapped_column(JSON, default=list)
    effective_from: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    effective_to: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    version: Mapped[str] = mapped_column(String(64), index=True)
    permissions: Mapped[dict] = mapped_column(JSON, default=dict)
    provenance_ref: Mapped[str] = mapped_column(String(255), index=True)
    lifecycle_state: Mapped[str] = mapped_column(String(32), default="ACTIVE", index=True)
    content_refs: Mapped[list] = mapped_column(JSON, default=list)
    recorded_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)


class IngestedArtifact(Base):
    __tablename__ = "ingested_artifact"
    artifact_id: Mapped[str] = mapped_column(String(255), primary_key=True)
    content_ref: Mapped[str] = mapped_column(String(1024), nullable=False)
    media_type: Mapped[str] = mapped_column(String(128), index=True)
    source_ref: Mapped[str] = mapped_column(String(255), index=True)
    owner_ref: Mapped[str] = mapped_column(String(255), index=True)
    context_ref: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    recorded_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    integrity_ref: Mapped[str] = mapped_column(String(255))
    metadata_json: Mapped[dict] = mapped_column("metadata", JSON, default=dict)
    provenance_ref: Mapped[str] = mapped_column(String(255), index=True)
    lifecycle_state: Mapped[str] = mapped_column(String(32), default="ACTIVE", index=True)


class UniversityMemoryRecord(Base):
    __tablename__ = "university_memory_record"
    memory_id: Mapped[str] = mapped_column(String(255), primary_key=True)
    memory_type: Mapped[str] = mapped_column(String(64), index=True)
    subject_ref: Mapped[str] = mapped_column(String(255), index=True)
    source_ref: Mapped[str] = mapped_column(String(255), index=True)
    summary: Mapped[str] = mapped_column(Text(), nullable=False)
    effective_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    recorded_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    provenance_ref: Mapped[str] = mapped_column(String(255), index=True)
    integrity_ref: Mapped[str | None] = mapped_column(String(255), nullable=True)
    tags: Mapped[list] = mapped_column(JSON, default=list)
    lifecycle_state: Mapped[str] = mapped_column(String(32), default="ACTIVE", index=True)
