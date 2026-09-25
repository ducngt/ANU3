"""Phase 1 Kernel baseline

Revision ID: 0001
Revises: None
"""
from alembic import op
import sqlalchemy as sa

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def _timestamps():
    return [
        sa.Column("recorded_at", sa.DateTime(timezone=True), nullable=False),
    ]


def upgrade() -> None:
    op.create_table(
        "kernel_object",
        sa.Column("id", sa.String(255), primary_key=True),
        sa.Column("semantic_type", sa.String(255), nullable=False),
        sa.Column("object_kind", sa.String(64), nullable=False),
        sa.Column("lifecycle_state", sa.String(32), nullable=False),
        sa.Column("current_version", sa.String(64)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "identity_record",
        sa.Column("identity_id", sa.String(255), primary_key=True),
        sa.Column("subject_id", sa.String(255), nullable=False),
        sa.Column("subject_type", sa.String(32), nullable=False),
        sa.Column("assurance_level", sa.String(32), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("credential_refs", sa.JSON(), nullable=False),
        sa.Column("aliases", sa.JSON(), nullable=False),
        sa.Column("effective_from", sa.DateTime(timezone=True), nullable=False),
        sa.Column("effective_to", sa.DateTime(timezone=True)),
        sa.Column("recorded_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("lifecycle_state", sa.String(32), nullable=False),
        sa.Column("provenance_ref", sa.String(255)),
    )
    op.create_table(
        "semantic_definition",
        sa.Column("row_id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("semantic_id", sa.String(255), nullable=False),
        sa.Column("canonical_name", sa.String(255), nullable=False),
        sa.Column("definition", sa.Text(), nullable=False),
        sa.Column("namespace", sa.String(255), nullable=False),
        sa.Column("semantic_kind", sa.String(64), nullable=False),
        sa.Column("owner_ref", sa.String(255), nullable=False),
        sa.Column("context_ref", sa.String(255)),
        sa.Column("relations", sa.JSON(), nullable=False),
        sa.Column("mappings", sa.JSON(), nullable=False),
        sa.Column("version", sa.String(64), nullable=False),
        sa.Column("effective_from", sa.DateTime(timezone=True), nullable=False),
        sa.Column("effective_to", sa.DateTime(timezone=True)),
        sa.Column("recorded_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("lifecycle_state", sa.String(32), nullable=False),
        sa.Column("provenance_ref", sa.String(255)),
        sa.UniqueConstraint("semantic_id", "version", name="uq_semantic_version"),
    )
    op.create_table(
        "role_assignment",
        sa.Column("assignment_id", sa.String(255), primary_key=True),
        sa.Column("subject_ref", sa.String(255), nullable=False),
        sa.Column("role_ref", sa.String(255), nullable=False),
        sa.Column("context_ref", sa.String(255), nullable=False),
        sa.Column("assigned_by", sa.String(255), nullable=False),
        sa.Column("basis_ref", sa.String(255)),
        sa.Column("effective_from", sa.DateTime(timezone=True), nullable=False),
        sa.Column("effective_to", sa.DateTime(timezone=True)),
        sa.Column("recorded_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("lifecycle_state", sa.String(32), nullable=False),
        sa.Column("provenance_ref", sa.String(255)),
    )
    op.create_table(
        "competence_assertion",
        sa.Column("assertion_id", sa.String(255), primary_key=True),
        sa.Column("subject_ref", sa.String(255), nullable=False),
        sa.Column("competence_ref", sa.String(255), nullable=False),
        sa.Column("level", sa.String(64), nullable=False),
        sa.Column("scope", sa.JSON(), nullable=False),
        sa.Column("evidence_refs", sa.JSON(), nullable=False),
        sa.Column("asserted_by", sa.String(255), nullable=False),
        sa.Column("validation_state", sa.String(32), nullable=False),
        sa.Column("effective_from", sa.DateTime(timezone=True), nullable=False),
        sa.Column("effective_to", sa.DateTime(timezone=True)),
        sa.Column("recorded_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("lifecycle_state", sa.String(32), nullable=False),
        sa.Column("provenance_ref", sa.String(255)),
    )
    op.create_table(
        "authority_grant",
        sa.Column("authority_id", sa.String(255), primary_key=True),
        sa.Column("subject_ref", sa.String(255), nullable=False),
        sa.Column("subject_type", sa.String(32), nullable=False),
        sa.Column("authority_type", sa.String(255), nullable=False),
        sa.Column("basis_ref", sa.String(255), nullable=False),
        sa.Column("issuer_ref", sa.String(255), nullable=False),
        sa.Column("scope", sa.JSON(), nullable=False),
        sa.Column("consequence_class", sa.String(64), nullable=False),
        sa.Column("competence_requirements", sa.JSON(), nullable=False),
        sa.Column("delegation_allowed", sa.Boolean(), nullable=False),
        sa.Column("delegation_constraints", sa.JSON(), nullable=False),
        sa.Column("effective_from", sa.DateTime(timezone=True), nullable=False),
        sa.Column("effective_to", sa.DateTime(timezone=True)),
        sa.Column("recorded_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("policy_refs", sa.JSON(), nullable=False),
        sa.Column("lifecycle_state", sa.String(32), nullable=False),
        sa.Column("provenance_ref", sa.String(255)),
        sa.CheckConstraint("subject_type <> 'AGENT'", name="ck_no_agent_standing_authority"),
    )
    op.create_table(
        "delegation_grant",
        sa.Column("delegation_id", sa.String(255), primary_key=True),
        sa.Column("delegator_ref", sa.String(255), nullable=False),
        sa.Column("delegatee_ref", sa.String(255), nullable=False),
        sa.Column("authority_ref", sa.String(255), sa.ForeignKey("authority_grant.authority_id"), nullable=False),
        sa.Column("delegated_scope", sa.JSON(), nullable=False),
        sa.Column("purpose", sa.Text(), nullable=False),
        sa.Column("conditions", sa.JSON(), nullable=False),
        sa.Column("valid_from", sa.DateTime(timezone=True), nullable=False),
        sa.Column("valid_until", sa.DateTime(timezone=True), nullable=False),
        sa.Column("recorded_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("redelegation_allowed", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("revocation_policy_ref", sa.String(255)),
        sa.Column("issued_under_policy", sa.String(255), nullable=False),
        sa.Column("lifecycle_state", sa.String(32), nullable=False),
        sa.Column("provenance_ref", sa.String(255)),
        sa.CheckConstraint("valid_until > valid_from", name="ck_delegation_valid_period"),
    )
    op.create_table(
        "delegation_revocation",
        sa.Column("revocation_id", sa.String(255), primary_key=True),
        sa.Column("delegation_id", sa.String(255), sa.ForeignKey("delegation_grant.delegation_id"), nullable=False),
        sa.Column("effective_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("recorded_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("actor_ref", sa.String(255), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("provenance_ref", sa.String(255)),
    )
    op.create_table(
        "policy_version",
        sa.Column("row_id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("policy_id", sa.String(255), nullable=False),
        sa.Column("policy_type", sa.String(128), nullable=False),
        sa.Column("issuer_ref", sa.String(255), nullable=False),
        sa.Column("authority_basis_ref", sa.String(255), nullable=False),
        sa.Column("version", sa.String(64), nullable=False),
        sa.Column("scope", sa.JSON(), nullable=False),
        sa.Column("conditions", sa.JSON(), nullable=False),
        sa.Column("effects", sa.JSON(), nullable=False),
        sa.Column("effective_from", sa.DateTime(timezone=True), nullable=False),
        sa.Column("effective_to", sa.DateTime(timezone=True)),
        sa.Column("recorded_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("supersedes_ref", sa.String(255)),
        sa.Column("exception_rules", sa.JSON(), nullable=False),
        sa.Column("lifecycle_state", sa.String(32), nullable=False),
        sa.Column("provenance_ref", sa.String(255)),
        sa.UniqueConstraint("policy_id", "version", name="uq_policy_version"),
    )
    op.create_table(
        "provenance_record",
        sa.Column("provenance_id", sa.String(255), primary_key=True),
        sa.Column("entity_ref", sa.String(255), nullable=False),
        sa.Column("activity_ref", sa.String(255)),
        sa.Column("actor_ref", sa.String(255), nullable=False),
        sa.Column("work_ref", sa.String(255)),
        sa.Column("capability_ref", sa.String(255)),
        sa.Column("tool_ref", sa.String(255)),
        sa.Column("model_ref", sa.String(255)),
        sa.Column("source_refs", sa.JSON(), nullable=False),
        sa.Column("input_refs", sa.JSON(), nullable=False),
        sa.Column("output_refs", sa.JSON(), nullable=False),
        sa.Column("transformation_ref", sa.String(255)),
        sa.Column("effective_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("recorded_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("integrity_ref", sa.String(255)),
        sa.Column("previous_provenance_refs", sa.JSON(), nullable=False),
    )
    op.create_table(
        "audit_event",
        sa.Column("audit_id", sa.String(255), primary_key=True),
        sa.Column("event_type", sa.String(255), nullable=False),
        sa.Column("actor_identity", sa.String(255), nullable=False),
        sa.Column("role_context", sa.JSON(), nullable=False),
        sa.Column("authority_ref", sa.String(255)),
        sa.Column("delegation_ref", sa.String(255)),
        sa.Column("policy_refs", sa.JSON(), nullable=False),
        sa.Column("action", sa.String(255), nullable=False),
        sa.Column("target_ref", sa.String(255)),
        sa.Column("result", sa.String(64), nullable=False),
        sa.Column("work_ref", sa.String(255)),
        sa.Column("trace_id", sa.String(255), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("recorded_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("provenance_ref", sa.String(255)),
        sa.Column("integrity_ref", sa.String(255)),
    )
    op.create_table(
        "lifecycle_transition",
        sa.Column("transition_id", sa.String(255), primary_key=True),
        sa.Column("object_ref", sa.String(255), nullable=False),
        sa.Column("from_state", sa.String(32), nullable=False),
        sa.Column("to_state", sa.String(32), nullable=False),
        sa.Column("effective_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("recorded_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("actor_ref", sa.String(255), nullable=False),
        sa.Column("authority_ref", sa.String(255)),
        sa.Column("policy_ref", sa.String(255)),
        sa.Column("superseded_by_ref", sa.String(255)),
        sa.Column("provenance_ref", sa.String(255)),
    )
    op.create_table(
        "kernel_event",
        sa.Column("event_id", sa.String(255), primary_key=True),
        sa.Column("event_type", sa.String(255), nullable=False),
        sa.Column("source", sa.String(255), nullable=False),
        sa.Column("subject", sa.String(255), nullable=False),
        sa.Column("time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("effective_time", sa.DateTime(timezone=True)),
        sa.Column("recorded_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("work_id", sa.String(255)),
        sa.Column("actor_identity", sa.String(255), nullable=False),
        sa.Column("role", sa.String(255)),
        sa.Column("authority_ref", sa.String(255)),
        sa.Column("delegation_ref", sa.String(255)),
        sa.Column("policy_version", sa.String(255)),
        sa.Column("artifact_ref", sa.String(255)),
        sa.Column("integrity_ref", sa.String(255)),
        sa.Column("signature_ref", sa.String(255)),
        sa.Column("provenance_ref", sa.String(255)),
        sa.Column("correlation_id", sa.String(255)),
        sa.Column("causation_id", sa.String(255)),
        sa.Column("schema_version", sa.String(64), nullable=False),
    )
    op.create_table(
        "decision_record",
        sa.Column("decision_id", sa.String(255), primary_key=True),
        sa.Column("subject_ref", sa.String(255), nullable=False),
        sa.Column("role_refs", sa.JSON(), nullable=False),
        sa.Column("authority_ref", sa.String(255), nullable=False),
        sa.Column("delegation_ref", sa.String(255)),
        sa.Column("policy_ref", sa.String(255), nullable=False),
        sa.Column("evidence_refs", sa.JSON(), nullable=False),
        sa.Column("artifact_ref", sa.String(255)),
        sa.Column("signature_ref", sa.String(255)),
        sa.Column("outcome", sa.String(64), nullable=False),
        sa.Column("effective_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("recorded_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("provenance_ref", sa.String(255), nullable=False),
    )


def downgrade() -> None:
    for table in [
        "decision_record", "kernel_event", "lifecycle_transition", "audit_event",
        "provenance_record", "policy_version", "delegation_revocation",
        "delegation_grant", "authority_grant", "competence_assertion",
        "role_assignment", "semantic_definition", "identity_record", "kernel_object"
    ]:
        op.drop_table(table)
