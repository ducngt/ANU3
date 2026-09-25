"""Phase 1 trust/authentication hardening

Revision ID: 0002
Revises: 0001
"""
from alembic import op
import sqlalchemy as sa

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "trust_credential",
        sa.Column("credential_id", sa.String(255), primary_key=True),
        sa.Column("subject_ref", sa.String(255), nullable=False),
        sa.Column("credential_type", sa.String(64), nullable=False),
        sa.Column("public_key_pem", sa.Text(), nullable=False),
        sa.Column("fingerprint_sha256", sa.String(128), nullable=False),
        sa.Column("issuer_ref", sa.String(255), nullable=False),
        sa.Column("valid_from", sa.DateTime(timezone=True), nullable=False),
        sa.Column("valid_until", sa.DateTime(timezone=True)),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True)),
        sa.Column("recorded_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("provenance_ref", sa.String(255)),
    )
    op.create_index("ix_trust_credential_subject_ref", "trust_credential", ["subject_ref"])
    op.create_index("ix_trust_credential_fingerprint_sha256", "trust_credential", ["fingerprint_sha256"])
    op.create_table(
        "signature_record",
        sa.Column("signature_id", sa.String(255), primary_key=True),
        sa.Column("signer_identity_ref", sa.String(255), nullable=False),
        sa.Column("signer_type", sa.String(32), nullable=False),
        sa.Column("signer_role_ref", sa.String(255), nullable=False),
        sa.Column("authority_ref", sa.String(255), nullable=False),
        sa.Column("credential_ref", sa.String(255), sa.ForeignKey("trust_credential.credential_id"), nullable=False),
        sa.Column("signature_method", sa.String(64), nullable=False),
        sa.Column("intent", sa.Text(), nullable=False),
        sa.Column("artifact_ref", sa.String(255), nullable=False),
        sa.Column("artifact_version", sa.String(128), nullable=False),
        sa.Column("artifact_hash", sa.String(255), nullable=False),
        sa.Column("work_ref", sa.String(255)),
        sa.Column("decision_ref", sa.String(255)),
        sa.Column("policy_version", sa.String(255), nullable=False),
        sa.Column("delegation_ref", sa.String(255)),
        sa.Column("signed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("signature_value", sa.Text(), nullable=False),
        sa.Column("provenance_ref", sa.String(255)),
        sa.Column("recorded_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "agent_attestation",
        sa.Column("attestation_id", sa.String(255), primary_key=True),
        sa.Column("agent_ref", sa.String(255), nullable=False),
        sa.Column("agent_version", sa.String(128), nullable=False),
        sa.Column("owner_ref", sa.String(255), nullable=False),
        sa.Column("runtime_ref", sa.String(255), nullable=False),
        sa.Column("model_dependency", sa.String(255)),
        sa.Column("purpose", sa.Text(), nullable=False),
        sa.Column("work_ref", sa.String(255), nullable=False),
        sa.Column("action", sa.String(255), nullable=False),
        sa.Column("capability_ref", sa.String(255), nullable=False),
        sa.Column("tool_ref", sa.String(255)),
        sa.Column("delegation_ref", sa.String(255)),
        sa.Column("policy_version", sa.String(255), nullable=False),
        sa.Column("input_refs", sa.JSON(), nullable=False),
        sa.Column("artifact_ref", sa.String(255), nullable=False),
        sa.Column("artifact_hash", sa.String(255), nullable=False),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("credential_ref", sa.String(255), sa.ForeignKey("trust_credential.credential_id"), nullable=False),
        sa.Column("attestation_signature", sa.Text(), nullable=False),
        sa.Column("provenance_ref", sa.String(255)),
        sa.Column("consequential", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("recorded_at", sa.DateTime(timezone=True), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("agent_attestation")
    op.drop_table("signature_record")
    op.drop_index("ix_trust_credential_fingerprint_sha256", table_name="trust_credential")
    op.drop_index("ix_trust_credential_subject_ref", table_name="trust_credential")
    op.drop_table("trust_credential")
