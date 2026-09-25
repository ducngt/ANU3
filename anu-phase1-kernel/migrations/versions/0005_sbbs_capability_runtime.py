"""P3-02..P3-07 SBBS capability runtime

Revision ID: 0005
Revises: 0004
"""
from alembic import op
import sqlalchemy as sa

revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "transform_version",
        sa.Column("row_id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("transform_id", sa.String(255), nullable=False),
        sa.Column("version", sa.String(64), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("owner_ref", sa.String(255), nullable=False),
        sa.Column("from_contract_ref", sa.String(320), nullable=False),
        sa.Column("to_contract_ref", sa.String(320), nullable=False),
        sa.Column("mapping", sa.JSON(), nullable=False),
        sa.Column("constants", sa.JSON(), nullable=False),
        sa.Column("semantic_preservation", sa.JSON(), nullable=False),
        sa.Column("lossy", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("effective_from", sa.DateTime(timezone=True), nullable=False),
        sa.Column("effective_to", sa.DateTime(timezone=True), nullable=True),
        sa.Column("lifecycle_state", sa.String(32), nullable=False, server_default="ACTIVE"),
        sa.Column("provenance_ref", sa.String(255), nullable=False),
        sa.Column("recorded_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("transform_id", "version", name="uq_transform_id_version"),
    )
    for col in ["transform_id","version","owner_ref","from_contract_ref","to_contract_ref","effective_from","effective_to","lifecycle_state","provenance_ref","recorded_at"]:
        op.create_index(f"ix_transform_version_{col}", "transform_version", [col])

    op.create_table(
        "adapter_version",
        sa.Column("row_id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("adapter_id", sa.String(255), nullable=False),
        sa.Column("version", sa.String(64), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("owner_ref", sa.String(255), nullable=False),
        sa.Column("source_runtime_type", sa.String(128), nullable=False),
        sa.Column("target_runtime_type", sa.String(128), nullable=False),
        sa.Column("capability_scope", sa.JSON(), nullable=False),
        sa.Column("configuration", sa.JSON(), nullable=False),
        sa.Column("effective_from", sa.DateTime(timezone=True), nullable=False),
        sa.Column("effective_to", sa.DateTime(timezone=True), nullable=True),
        sa.Column("lifecycle_state", sa.String(32), nullable=False, server_default="ACTIVE"),
        sa.Column("provenance_ref", sa.String(255), nullable=False),
        sa.Column("recorded_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("adapter_id", "version", name="uq_adapter_id_version"),
    )
    for col in ["adapter_id","version","owner_ref","source_runtime_type","target_runtime_type","effective_from","effective_to","lifecycle_state","provenance_ref","recorded_at"]:
        op.create_index(f"ix_adapter_version_{col}", "adapter_version", [col])

    op.create_table(
        "compatibility_evidence",
        sa.Column("evidence_id", sa.String(255), primary_key=True),
        sa.Column("from_capability_ref", sa.String(320), nullable=False),
        sa.Column("from_operation", sa.String(255), nullable=False),
        sa.Column("to_capability_ref", sa.String(320), nullable=False),
        sa.Column("to_operation", sa.String(255), nullable=False),
        sa.Column("compatible", sa.Boolean(), nullable=False),
        sa.Column("direct", sa.Boolean(), nullable=False),
        sa.Column("result_json", sa.JSON(), nullable=False),
        sa.Column("request_hash", sa.String(128), nullable=False),
        sa.Column("recorded_at", sa.DateTime(timezone=True), nullable=False),
    )
    for col in ["from_capability_ref","to_capability_ref","compatible","request_hash","recorded_at"]:
        op.create_index(f"ix_compatibility_evidence_{col}", "compatibility_evidence", [col])

    op.create_table(
        "connection_plan_version",
        sa.Column("row_id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("plan_id", sa.String(255), nullable=False),
        sa.Column("version", sa.String(64), nullable=False),
        sa.Column("from_capability", sa.String(320), nullable=False),
        sa.Column("from_operation", sa.String(255), nullable=False),
        sa.Column("to_capability", sa.String(320), nullable=False),
        sa.Column("to_operation", sa.String(255), nullable=False),
        sa.Column("from_box_ref", sa.String(320), nullable=False),
        sa.Column("to_box_ref", sa.String(320), nullable=False),
        sa.Column("contract_ref", sa.String(320), nullable=True),
        sa.Column("transformation_refs", sa.JSON(), nullable=False),
        sa.Column("adapter_refs", sa.JSON(), nullable=False),
        sa.Column("policy_checks", sa.JSON(), nullable=False),
        sa.Column("security_context", sa.JSON(), nullable=False),
        sa.Column("retry_policy", sa.JSON(), nullable=False),
        sa.Column("observability_policy", sa.JSON(), nullable=False),
        sa.Column("compatibility_evidence", sa.JSON(), nullable=False),
        sa.Column("effective_from", sa.DateTime(timezone=True), nullable=False),
        sa.Column("effective_to", sa.DateTime(timezone=True), nullable=True),
        sa.Column("lifecycle_state", sa.String(32), nullable=False, server_default="ACTIVE"),
        sa.Column("provenance_ref", sa.String(255), nullable=False),
        sa.Column("recorded_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("plan_id", "version", name="uq_connection_plan_version"),
    )
    for col in ["plan_id","version","from_capability","to_capability","from_box_ref","to_box_ref","effective_from","effective_to","lifecycle_state","provenance_ref","recorded_at"]:
        op.create_index(f"ix_connection_plan_version_{col}", "connection_plan_version", [col])

    op.create_table(
        "assembly_version",
        sa.Column("row_id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("assembly_id", sa.String(255), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("owner_ref", sa.String(255), nullable=False),
        sa.Column("version", sa.String(64), nullable=False),
        sa.Column("capability_refs", sa.JSON(), nullable=False),
        sa.Column("connection_plan_refs", sa.JSON(), nullable=False),
        sa.Column("human_refs", sa.JSON(), nullable=False),
        sa.Column("agent_refs", sa.JSON(), nullable=False),
        sa.Column("policy_refs", sa.JSON(), nullable=False),
        sa.Column("decision_points", sa.JSON(), nullable=False),
        sa.Column("configuration", sa.JSON(), nullable=False),
        sa.Column("effective_from", sa.DateTime(timezone=True), nullable=False),
        sa.Column("effective_to", sa.DateTime(timezone=True), nullable=True),
        sa.Column("lifecycle_state", sa.String(32), nullable=False, server_default="ACTIVE"),
        sa.Column("provenance_ref", sa.String(255), nullable=False),
        sa.Column("recorded_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("assembly_id", "version", name="uq_assembly_version"),
    )
    for col in ["assembly_id","owner_ref","version","effective_from","effective_to","lifecycle_state","provenance_ref","recorded_at"]:
        op.create_index(f"ix_assembly_version_{col}", "assembly_version", [col])

    op.create_table(
        "wire_execution_record",
        sa.Column("execution_id", sa.String(255), primary_key=True),
        sa.Column("plan_ref", sa.String(320), nullable=False),
        sa.Column("trace_id", sa.String(255), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("selected_box_ref", sa.String(320), nullable=True),
        sa.Column("input_payload", sa.JSON(), nullable=False),
        sa.Column("output_payload", sa.JSON(), nullable=True),
        sa.Column("trace_json", sa.JSON(), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=False),
    )
    for col in ["plan_ref","trace_id","status","started_at","completed_at"]:
        op.create_index(f"ix_wire_execution_record_{col}", "wire_execution_record", [col])

    op.create_table(
        "assembly_execution_record",
        sa.Column("execution_id", sa.String(255), primary_key=True),
        sa.Column("assembly_ref", sa.String(320), nullable=False),
        sa.Column("trace_id", sa.String(255), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("input_payload", sa.JSON(), nullable=False),
        sa.Column("final_payload", sa.JSON(), nullable=True),
        sa.Column("connection_results", sa.JSON(), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=False),
    )
    for col in ["assembly_ref","trace_id","status","started_at","completed_at"]:
        op.create_index(f"ix_assembly_execution_record_{col}", "assembly_execution_record", [col])

    op.create_table(
        "write_box_candidate",
        sa.Column("candidate_id", sa.String(255), primary_key=True),
        sa.Column("intent", sa.Text(), nullable=False),
        sa.Column("actor_ref", sa.String(255), nullable=False),
        sa.Column("capability_json", sa.JSON(), nullable=False),
        sa.Column("smart_box_json", sa.JSON(), nullable=False),
        sa.Column("specification", sa.Text(), nullable=False),
        sa.Column("knowledge_refs", sa.JSON(), nullable=False),
        sa.Column("rule_refs", sa.JSON(), nullable=False),
        sa.Column("examples", sa.JSON(), nullable=False),
        sa.Column("provenance_ref", sa.String(255), nullable=False),
        sa.Column("recommended_action", sa.String(32), nullable=False),
        sa.Column("existing_capability_refs", sa.JSON(), nullable=False),
        sa.Column("audit_json", sa.JSON(), nullable=False),
        sa.Column("stage", sa.String(32), nullable=False, server_default="DRAFT"),
        sa.Column("recorded_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("promoted_at", sa.DateTime(timezone=True), nullable=True),
    )
    for col in ["actor_ref","provenance_ref","recommended_action","stage","recorded_at"]:
        op.create_index(f"ix_write_box_candidate_{col}", "write_box_candidate", [col])


def downgrade() -> None:
    op.drop_table("write_box_candidate")
    op.drop_table("assembly_execution_record")
    op.drop_table("wire_execution_record")
    op.drop_table("assembly_version")
    op.drop_table("connection_plan_version")
    op.drop_table("compatibility_evidence")
    op.drop_table("adapter_version")
    op.drop_table("transform_version")
