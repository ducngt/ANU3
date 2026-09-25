from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import JSON, DateTime, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from .db import Base


class ArtifactObjectVersion(Base):
    __tablename__ = "artifact_object_version"
    version_id: Mapped[str] = mapped_column(String(255), primary_key=True)
    artifact_id: Mapped[str] = mapped_column(String(255), index=True)
    filename: Mapped[str] = mapped_column(String(512))
    semantic_type: Mapped[str] = mapped_column(String(255), index=True)
    media_type: Mapped[str] = mapped_column(String(128), index=True)
    byte_size: Mapped[int] = mapped_column(Integer)
    content_hash: Mapped[str] = mapped_column(String(128), index=True)
    storage_ref: Mapped[str] = mapped_column(String(1024), index=True)
    source_ref: Mapped[str] = mapped_column(String(255), index=True)
    owner_ref: Mapped[str] = mapped_column(String(255), index=True)
    context_ref: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    recorded_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    epistemic_type: Mapped[str] = mapped_column(String(32), index=True)
    validation_state: Mapped[str] = mapped_column(String(32), index=True)
    provenance_ref: Mapped[str] = mapped_column(String(255), index=True)
    lifecycle_state: Mapped[str] = mapped_column(String(32), default="ACTIVE", index=True)
    supersedes_ref: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    extraction_status: Mapped[str] = mapped_column(String(32), index=True)
    extracted_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    analyzer_ref: Mapped[str] = mapped_column(String(255))
    analyzer_version: Mapped[str] = mapped_column(String(64))
    metadata_json: Mapped[dict] = mapped_column("metadata", JSON, default=dict)


class RetrievalProjection(Base):
    __tablename__ = "retrieval_projection"
    __table_args__ = (UniqueConstraint("object_ref", "index_version", name="uq_retrieval_object_index_version"),)
    row_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    projection_id: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    object_ref: Mapped[str] = mapped_column(String(255), index=True)
    object_kind: Mapped[str] = mapped_column(String(64), index=True)
    title: Mapped[str] = mapped_column(String(512))
    semantic_type: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    epistemic_type: Mapped[str | None] = mapped_column(String(32), nullable=True, index=True)
    validation_state: Mapped[str | None] = mapped_column(String(32), nullable=True, index=True)
    source_refs: Mapped[list] = mapped_column(JSON, default=list)
    provenance_ref: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    content_hash: Mapped[str | None] = mapped_column(String(128), nullable=True)
    searchable_text: Mapped[str] = mapped_column(Text, default="")
    vector_json: Mapped[list] = mapped_column(JSON, default=list)
    index_version: Mapped[str] = mapped_column(String(64), default="anu-hash-vector-v1", index=True)
    lifecycle_state: Mapped[str] = mapped_column(String(32), default="ACTIVE", index=True)
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), index=True)
