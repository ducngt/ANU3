"""Phase 2 Reality/Data/Memory foundation

Revision ID: 0003
Revises: 0002
"""
from alembic import op
import sqlalchemy as sa

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "source_registry",
        sa.Column("source_id", sa.String(255), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("source_kind", sa.String(64), nullable=False),
        sa.Column("owner_ref", sa.String(255), nullable=False),
        sa.Column("description", sa.Text()),
        sa.Column("synthetic_fixture", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("effective_from", sa.DateTime(timezone=True), nullable=False),
        sa.Column("effective_to", sa.DateTime(timezone=True)),
        sa.Column("lifecycle_state", sa.String(32), nullable=False),
        sa.Column("provenance_ref", sa.String(255)),
        sa.Column("recorded_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_source_registry_source_kind", "source_registry", ["source_kind"])
    op.create_index("ix_source_registry_owner_ref", "source_registry", ["owner_ref"])
    op.create_index("ix_source_registry_effective_from", "source_registry", ["effective_from"])
    op.create_index("ix_source_registry_effective_to", "source_registry", ["effective_to"])
    op.create_index("ix_source_registry_lifecycle_state", "source_registry", ["lifecycle_state"])
    op.create_index("ix_source_registry_recorded_at", "source_registry", ["recorded_at"])

    op.create_table(
        "source_authority_mapping",
        sa.Column("mapping_id", sa.String(255), primary_key=True),
        sa.Column("source_ref", sa.String(255), nullable=False),
        sa.Column("semantic_type", sa.String(255), nullable=False),
        sa.Column("authority_scope", sa.JSON(), nullable=False),
        sa.Column("authoritative", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("effective_from", sa.DateTime(timezone=True), nullable=False),
        sa.Column("effective_to", sa.DateTime(timezone=True)),
        sa.Column("lifecycle_state", sa.String(32), nullable=False),
        sa.Column("provenance_ref", sa.String(255)),
        sa.Column("recorded_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_source_authority_mapping_source_ref", "source_authority_mapping", ["source_ref"])
    op.create_index("ix_source_authority_mapping_semantic_type", "source_authority_mapping", ["semantic_type"])
    op.create_index("ix_source_authority_mapping_effective_from", "source_authority_mapping", ["effective_from"])
    op.create_index("ix_source_authority_mapping_effective_to", "source_authority_mapping", ["effective_to"])
    op.create_index("ix_source_authority_mapping_lifecycle_state", "source_authority_mapping", ["lifecycle_state"])
    op.create_index("ix_source_authority_mapping_recorded_at", "source_authority_mapping", ["recorded_at"])

    op.create_table(
        "data_contract_version",
        sa.Column("row_id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("contract_id", sa.String(255), nullable=False),
        sa.Column("data_type", sa.String(128), nullable=False),
        sa.Column("semantic_definition", sa.String(255), nullable=False),
        sa.Column("schema", sa.JSON(), nullable=False),
        sa.Column("owner", sa.String(255), nullable=False),
        sa.Column("authoritative_source", sa.String(255)),
        sa.Column("producers", sa.JSON(), nullable=False),
        sa.Column("consumers", sa.JSON(), nullable=False),
        sa.Column("freshness_requirement", sa.String(255)),
        sa.Column("quality_rules", sa.JSON(), nullable=False),
        sa.Column("provenance_requirement", sa.String(64), nullable=False),
        sa.Column("access_policy", sa.String(255)),
        sa.Column("privacy_class", sa.String(64), nullable=False),
        sa.Column("integrity_requirement", sa.String(64), nullable=False),
        sa.Column("retention_rule", sa.String(255)),
        sa.Column("version", sa.String(64), nullable=False),
        sa.Column("compatibility_policy", sa.String(128), nullable=False),
        sa.Column("lifecycle_state", sa.String(32), nullable=False),
        sa.Column("provenance_ref", sa.String(255)),
        sa.Column("recorded_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("contract_id", "version", name="uq_data_contract_id_version"),
    )
    for col in ["contract_id", "data_type", "semantic_definition", "owner", "version", "lifecycle_state", "recorded_at"]:
        op.create_index(f"ix_data_contract_version_{col}", "data_contract_version", [col])

    op.create_table(
        "data_object_version",
        sa.Column("version_id", sa.String(255), primary_key=True),
        sa.Column("data_id", sa.String(255), nullable=False),
        sa.Column("contract_ref", sa.String(320), nullable=False),
        sa.Column("semantic_type", sa.String(255), nullable=False),
        sa.Column("schema_version", sa.String(64), nullable=False),
        sa.Column("subject_refs", sa.JSON(), nullable=False),
        sa.Column("source_system_id", sa.String(255), nullable=False),
        sa.Column("source_record_ref", sa.String(255), nullable=False),
        sa.Column("source_authority_scope", sa.JSON(), nullable=False),
        sa.Column("owner_ref", sa.String(255), nullable=False),
        sa.Column("context_ref", sa.String(255)),
        sa.Column("effective_from", sa.DateTime(timezone=True), nullable=False),
        sa.Column("effective_to", sa.DateTime(timezone=True)),
        sa.Column("recorded_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("epistemic_type", sa.String(32), nullable=False),
        sa.Column("validation_state", sa.String(32), nullable=False),
        sa.Column("provenance_ref", sa.String(255), nullable=False),
        sa.Column("integrity_ref", sa.String(255)),
        sa.Column("access_policy_ref", sa.String(255)),
        sa.Column("retention_policy_ref", sa.String(255)),
        sa.Column("lifecycle_state", sa.String(32), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("supersedes_ref", sa.String(255)),
        sa.Column("synthetic_output", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    for col in ["data_id", "contract_ref", "semantic_type", "source_system_id", "owner_ref", "context_ref", "effective_from", "effective_to", "recorded_time", "epistemic_type", "validation_state", "provenance_ref", "lifecycle_state", "supersedes_ref"]:
        op.create_index(f"ix_data_object_version_{col}", "data_object_version", [col])

    op.create_table(
        "knowledge_object_version",
        sa.Column("row_id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("knowledge_id", sa.String(255), nullable=False),
        sa.Column("title", sa.String(512), nullable=False),
        sa.Column("semantic_type", sa.String(255), nullable=False),
        sa.Column("epistemic_type", sa.String(32), nullable=False),
        sa.Column("validation_state", sa.String(32), nullable=False),
        sa.Column("source_refs", sa.JSON(), nullable=False),
        sa.Column("author_owner", sa.String(255), nullable=False),
        sa.Column("context_ref", sa.String(255)),
        sa.Column("relations", sa.JSON(), nullable=False),
        sa.Column("effective_from", sa.DateTime(timezone=True), nullable=False),
        sa.Column("effective_to", sa.DateTime(timezone=True)),
        sa.Column("version", sa.String(64), nullable=False),
        sa.Column("permissions", sa.JSON(), nullable=False),
        sa.Column("provenance_ref", sa.String(255), nullable=False),
        sa.Column("lifecycle_state", sa.String(32), nullable=False),
        sa.Column("content_refs", sa.JSON(), nullable=False),
        sa.Column("recorded_time", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("knowledge_id", "version", name="uq_knowledge_id_version"),
    )
    for col in ["knowledge_id", "semantic_type", "epistemic_type", "validation_state", "author_owner", "context_ref", "effective_from", "effective_to", "version", "provenance_ref", "lifecycle_state", "recorded_time"]:
        op.create_index(f"ix_knowledge_object_version_{col}", "knowledge_object_version", [col])

    op.create_table(
        "ingested_artifact",
        sa.Column("artifact_id", sa.String(255), primary_key=True),
        sa.Column("content_ref", sa.String(1024), nullable=False),
        sa.Column("media_type", sa.String(128), nullable=False),
        sa.Column("source_ref", sa.String(255), nullable=False),
        sa.Column("owner_ref", sa.String(255), nullable=False),
        sa.Column("context_ref", sa.String(255)),
        sa.Column("observed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("recorded_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("integrity_ref", sa.String(255), nullable=False),
        sa.Column("metadata", sa.JSON(), nullable=False),
        sa.Column("provenance_ref", sa.String(255), nullable=False),
        sa.Column("lifecycle_state", sa.String(32), nullable=False),
    )
    for col in ["media_type", "source_ref", "owner_ref", "context_ref", "observed_at", "recorded_time", "provenance_ref", "lifecycle_state"]:
        op.create_index(f"ix_ingested_artifact_{col}", "ingested_artifact", [col])

    op.create_table(
        "university_memory_record",
        sa.Column("memory_id", sa.String(255), primary_key=True),
        sa.Column("memory_type", sa.String(64), nullable=False),
        sa.Column("subject_ref", sa.String(255), nullable=False),
        sa.Column("source_ref", sa.String(255), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("effective_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("recorded_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("provenance_ref", sa.String(255), nullable=False),
        sa.Column("integrity_ref", sa.String(255)),
        sa.Column("tags", sa.JSON(), nullable=False),
        sa.Column("lifecycle_state", sa.String(32), nullable=False),
    )
    for col in ["memory_type", "subject_ref", "source_ref", "effective_time", "recorded_time", "provenance_ref", "lifecycle_state"]:
        op.create_index(f"ix_university_memory_record_{col}", "university_memory_record", [col])


def downgrade() -> None:
    op.drop_table("university_memory_record")
    op.drop_table("ingested_artifact")
    op.drop_table("knowledge_object_version")
    op.drop_table("data_object_version")
    op.drop_table("data_contract_version")
    op.drop_table("source_authority_mapping")
    op.drop_table("source_registry")
