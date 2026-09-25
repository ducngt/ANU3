from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import JSON, DateTime, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from .db import Base


class CapabilityVersion(Base):
    __tablename__ = "capability_version"
    __table_args__ = (UniqueConstraint("capability_id", "version", name="uq_capability_id_version"),)
    row_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    capability_id: Mapped[str] = mapped_column(String(255), index=True)
    name: Mapped[str] = mapped_column(String(255))
    description: Mapped[str] = mapped_column(Text)
    owner_ref: Mapped[str] = mapped_column(String(255), index=True)
    domain: Mapped[str] = mapped_column(String(128), index=True)
    version: Mapped[str] = mapped_column(String(64), index=True)
    operations: Mapped[list] = mapped_column(JSON, default=list)
    requires_capabilities: Mapped[list] = mapped_column(JSON, default=list)
    data_scope: Mapped[list] = mapped_column(JSON, default=list)
    policy_refs: Mapped[list] = mapped_column(JSON, default=list)
    risk_class: Mapped[str] = mapped_column(String(32), default="E1")
    effective_from: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    effective_to: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    lifecycle_state: Mapped[str] = mapped_column(String(32), default="ACTIVE", index=True)
    provenance_ref: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), index=True)


class SmartBoxManifestVersion(Base):
    __tablename__ = "smart_box_manifest_version"
    __table_args__ = (UniqueConstraint("box_id", "box_version", name="uq_smart_box_id_version"),)
    row_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    box_id: Mapped[str] = mapped_column(String(255), index=True)
    capability_ref: Mapped[str] = mapped_column(String(320), index=True)
    box_version: Mapped[str] = mapped_column(String(64), index=True)
    provider_ref: Mapped[str] = mapped_column(String(255), index=True)
    runtime_type: Mapped[str] = mapped_column(String(128))
    operation_bindings: Mapped[list] = mapped_column(JSON, default=list)
    requires_capabilities: Mapped[list] = mapped_column(JSON, default=list)
    adapter_boundary: Mapped[str] = mapped_column(String(255))
    model_dependencies: Mapped[list] = mapped_column(JSON, default=list)
    data_classes: Mapped[list] = mapped_column(JSON, default=list)
    quality_slo: Mapped[dict] = mapped_column(JSON, default=dict)
    observability: Mapped[dict] = mapped_column(JSON, default=dict)
    effective_from: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    effective_to: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    lifecycle_state: Mapped[str] = mapped_column(String(32), default="ACTIVE", index=True)
    provenance_ref: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), index=True)
