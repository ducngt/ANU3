"""P2-T02 multimodal ingestion/retrieval + P3 contract registry foundation

Revision ID: 0004
Revises: 0003
"""
from alembic import op
import sqlalchemy as sa

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "artifact_object_version",
        sa.Column("version_id", sa.String(255), primary_key=True),
        sa.Column("artifact_id", sa.String(255), nullable=False),
        sa.Column("filename", sa.String(512), nullable=False),
        sa.Column("semantic_type", sa.String(255), nullable=False),
        sa.Column("media_type", sa.String(128), nullable=False),
        sa.Column("byte_size", sa.Integer(), nullable=False),
        sa.Column("content_hash", sa.String(128), nullable=False),
        sa.Column("storage_ref", sa.String(1024), nullable=False),
        sa.Column("source_ref", sa.String(255), nullable=False),
        sa.Column("owner_ref", sa.String(255), nullable=False),
        sa.Column("context_ref", sa.String(255), nullable=True),
        sa.Column("observed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("recorded_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("epistemic_type", sa.String(32), nullable=False),
        sa.Column("validation_state", sa.String(32), nullable=False),
        sa.Column("provenance_ref", sa.String(255), nullable=False),
        sa.Column("lifecycle_state", sa.String(32), nullable=False, server_default="ACTIVE"),
        sa.Column("supersedes_ref", sa.String(255), nullable=True),
        sa.Column("extraction_status", sa.String(32), nullable=False),
        sa.Column("extracted_text", sa.Text(), nullable=True),
        sa.Column("analyzer_ref", sa.String(255), nullable=False),
        sa.Column("analyzer_version", sa.String(64), nullable=False),
        sa.Column("metadata", sa.JSON(), nullable=False),
    )
    for column in ["artifact_id", "semantic_type", "media_type", "content_hash", "storage_ref", "source_ref", "owner_ref", "context_ref", "observed_at", "recorded_time", "epistemic_type", "validation_state", "provenance_ref", "lifecycle_state", "supersedes_ref", "extraction_status"]:
        op.create_index(f"ix_artifact_object_version_{column}", "artifact_object_version", [column])

    op.create_table(
        "retrieval_projection",
        sa.Column("row_id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("projection_id", sa.String(255), nullable=False, unique=True),
        sa.Column("object_ref", sa.String(255), nullable=False),
        sa.Column("object_kind", sa.String(64), nullable=False),
        sa.Column("title", sa.String(512), nullable=False),
        sa.Column("semantic_type", sa.String(255), nullable=True),
        sa.Column("epistemic_type", sa.String(32), nullable=True),
        sa.Column("validation_state", sa.String(32), nullable=True),
        sa.Column("source_refs", sa.JSON(), nullable=False),
        sa.Column("provenance_ref", sa.String(255), nullable=True),
        sa.Column("content_hash", sa.String(128), nullable=True),
        sa.Column("searchable_text", sa.Text(), nullable=False),
        sa.Column("vector_json", sa.JSON(), nullable=False),
        sa.Column("index_version", sa.String(64), nullable=False),
        sa.Column("lifecycle_state", sa.String(32), nullable=False, server_default="ACTIVE"),
        sa.Column("recorded_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("object_ref", "index_version", name="uq_retrieval_object_index_version"),
    )
    for column in ["projection_id", "object_ref", "object_kind", "semantic_type", "epistemic_type", "validation_state", "provenance_ref", "index_version", "lifecycle_state", "recorded_at"]:
        op.create_index(f"ix_retrieval_projection_{column}", "retrieval_projection", [column])

    op.create_table(
        "capability_version",
        sa.Column("row_id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("capability_id", sa.String(255), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("owner_ref", sa.String(255), nullable=False),
        sa.Column("domain", sa.String(128), nullable=False),
        sa.Column("version", sa.String(64), nullable=False),
        sa.Column("operations", sa.JSON(), nullable=False),
        sa.Column("requires_capabilities", sa.JSON(), nullable=False),
        sa.Column("data_scope", sa.JSON(), nullable=False),
        sa.Column("policy_refs", sa.JSON(), nullable=False),
        sa.Column("risk_class", sa.String(32), nullable=False),
        sa.Column("effective_from", sa.DateTime(timezone=True), nullable=False),
        sa.Column("effective_to", sa.DateTime(timezone=True), nullable=True),
        sa.Column("lifecycle_state", sa.String(32), nullable=False, server_default="ACTIVE"),
        sa.Column("provenance_ref", sa.String(255), nullable=True),
        sa.Column("recorded_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("capability_id", "version", name="uq_capability_id_version"),
    )
    for column in ["capability_id", "owner_ref", "domain", "version", "effective_from", "effective_to", "lifecycle_state", "provenance_ref", "recorded_at"]:
        op.create_index(f"ix_capability_version_{column}", "capability_version", [column])

    op.create_table(
        "smart_box_manifest_version",
        sa.Column("row_id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("box_id", sa.String(255), nullable=False),
        sa.Column("capability_ref", sa.String(320), nullable=False),
        sa.Column("box_version", sa.String(64), nullable=False),
        sa.Column("provider_ref", sa.String(255), nullable=False),
        sa.Column("runtime_type", sa.String(128), nullable=False),
        sa.Column("operation_bindings", sa.JSON(), nullable=False),
        sa.Column("requires_capabilities", sa.JSON(), nullable=False),
        sa.Column("adapter_boundary", sa.String(255), nullable=False),
        sa.Column("model_dependencies", sa.JSON(), nullable=False),
        sa.Column("data_classes", sa.JSON(), nullable=False),
        sa.Column("quality_slo", sa.JSON(), nullable=False),
        sa.Column("observability", sa.JSON(), nullable=False),
        sa.Column("effective_from", sa.DateTime(timezone=True), nullable=False),
        sa.Column("effective_to", sa.DateTime(timezone=True), nullable=True),
        sa.Column("lifecycle_state", sa.String(32), nullable=False, server_default="ACTIVE"),
        sa.Column("provenance_ref", sa.String(255), nullable=True),
        sa.Column("recorded_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("box_id", "box_version", name="uq_smart_box_id_version"),
    )
    for column in ["box_id", "capability_ref", "box_version", "provider_ref", "effective_from", "effective_to", "lifecycle_state", "provenance_ref", "recorded_at"]:
        op.create_index(f"ix_smart_box_manifest_version_{column}", "smart_box_manifest_version", [column])


def downgrade() -> None:
    op.drop_table("smart_box_manifest_version")
    op.drop_table("capability_version")
    op.drop_table("retrieval_projection")
    op.drop_table("artifact_object_version")
