"""P4 Governed Human-AI Work Runtime

Revision ID: 0006
Revises: 0005
"""
from alembic import op
import sqlalchemy as sa

revision = "0006"
down_revision = "0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "work_contract_version",
        sa.Column("row_id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("work_type_id", sa.String(255), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("version", sa.String(64), nullable=False),
        sa.Column("owner_ref", sa.String(255), nullable=False),
        sa.Column("goal", sa.Text(), nullable=False),
        sa.Column("scope", sa.JSON(), nullable=False),
        sa.Column("execution_class", sa.String(8), nullable=False),
        sa.Column("allowed_autonomy", sa.String(8), nullable=False),
        sa.Column("human_participants", sa.JSON(), nullable=False),
        sa.Column("agent_assignments", sa.JSON(), nullable=False),
        sa.Column("capability_refs", sa.JSON(), nullable=False),
        sa.Column("data_scope", sa.JSON(), nullable=False),
        sa.Column("knowledge_requirements", sa.JSON(), nullable=False),
        sa.Column("decision_points", sa.JSON(), nullable=False),
        sa.Column("approval_points", sa.JSON(), nullable=False),
        sa.Column("signature_policy_ref", sa.String(320), nullable=True),
        sa.Column("evidence_requirements", sa.JSON(), nullable=False),
        sa.Column("risk_class", sa.String(64), nullable=False),
        sa.Column("outcome_definition", sa.JSON(), nullable=False),
        sa.Column("escalation", sa.JSON(), nullable=False),
        sa.Column("failure_policy", sa.JSON(), nullable=False),
        sa.Column("trace_policy", sa.JSON(), nullable=False),
        sa.Column("retention", sa.JSON(), nullable=False),
        sa.Column("effective_from", sa.DateTime(timezone=True), nullable=False),
        sa.Column("effective_to", sa.DateTime(timezone=True), nullable=True),
        sa.Column("lifecycle_state", sa.String(32), nullable=False, server_default="ACTIVE"),
        sa.Column("provenance_ref", sa.String(255), nullable=False),
        sa.Column("recorded_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("work_type_id", "version", name="uq_work_contract_version"),
    )
    for col in ["work_type_id","version","owner_ref","execution_class","allowed_autonomy","risk_class","effective_from","effective_to","lifecycle_state","provenance_ref","recorded_at"]:
        op.create_index(f"ix_work_contract_version_{col}", "work_contract_version", [col])

    op.create_table(
        "work_graph_version",
        sa.Column("row_id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("graph_id", sa.String(255), nullable=False),
        sa.Column("work_type_ref", sa.String(320), nullable=False),
        sa.Column("version", sa.String(64), nullable=False),
        sa.Column("owner_ref", sa.String(255), nullable=False),
        sa.Column("entry_node", sa.String(255), nullable=False),
        sa.Column("nodes", sa.JSON(), nullable=False),
        sa.Column("effective_from", sa.DateTime(timezone=True), nullable=False),
        sa.Column("effective_to", sa.DateTime(timezone=True), nullable=True),
        sa.Column("lifecycle_state", sa.String(32), nullable=False, server_default="ACTIVE"),
        sa.Column("provenance_ref", sa.String(255), nullable=False),
        sa.Column("recorded_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("graph_id", "version", name="uq_work_graph_version"),
    )
    for col in ["graph_id","work_type_ref","version","owner_ref","effective_from","effective_to","lifecycle_state","provenance_ref","recorded_at"]:
        op.create_index(f"ix_work_graph_version_{col}", "work_graph_version", [col])

    op.create_table(
        "work_execution_plan",
        sa.Column("plan_id", sa.String(255), primary_key=True),
        sa.Column("work_type_ref", sa.String(320), nullable=False),
        sa.Column("work_graph_ref", sa.String(320), nullable=False),
        sa.Column("goal", sa.Text(), nullable=False),
        sa.Column("execution_class", sa.String(8), nullable=False),
        sa.Column("autonomy_level", sa.String(8), nullable=False),
        sa.Column("required_capability_refs", sa.JSON(), nullable=False),
        sa.Column("required_checks", sa.JSON(), nullable=False),
        sa.Column("decision_points", sa.JSON(), nullable=False),
        sa.Column("signature_points", sa.JSON(), nullable=False),
        sa.Column("fallback", sa.JSON(), nullable=False),
        sa.Column("trace_policy", sa.JSON(), nullable=False),
        sa.Column("provenance_ref", sa.String(255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    for col in ["work_type_ref","work_graph_ref","execution_class","autonomy_level","provenance_ref","created_at"]:
        op.create_index(f"ix_work_execution_plan_{col}", "work_execution_plan", [col])

    op.create_table(
        "work_instance",
        sa.Column("work_id", sa.String(255), primary_key=True),
        sa.Column("plan_ref", sa.String(255), nullable=False),
        sa.Column("work_type_ref", sa.String(320), nullable=False),
        sa.Column("work_graph_ref", sa.String(320), nullable=False),
        sa.Column("execution_class", sa.String(8), nullable=False),
        sa.Column("autonomy_level", sa.String(8), nullable=False),
        sa.Column("state", sa.String(32), nullable=False),
        sa.Column("requester_ref", sa.String(255), nullable=False),
        sa.Column("context", sa.JSON(), nullable=False),
        sa.Column("trace_id", sa.String(255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    for col in ["plan_ref","work_type_ref","work_graph_ref","execution_class","autonomy_level","state","requester_ref","trace_id","created_at","updated_at"]:
        op.create_index(f"ix_work_instance_{col}", "work_instance", [col])

    op.create_table(
        "work_task_record",
        sa.Column("task_id", sa.String(255), primary_key=True),
        sa.Column("work_id", sa.String(255), nullable=False),
        sa.Column("node_id", sa.String(255), nullable=False),
        sa.Column("actor_ref", sa.String(255), nullable=False),
        sa.Column("actor_kind", sa.String(32), nullable=False),
        sa.Column("action", sa.String(255), nullable=False),
        sa.Column("input_payload", sa.JSON(), nullable=False),
        sa.Column("output_payload", sa.JSON(), nullable=False),
        sa.Column("evidence_refs", sa.JSON(), nullable=False),
        sa.Column("authority_ref", sa.String(255), nullable=True),
        sa.Column("delegation_ref", sa.String(255), nullable=True),
        sa.Column("policy_ref", sa.String(320), nullable=True),
        sa.Column("signature_ref", sa.String(255), nullable=True),
        sa.Column("attestation_ref", sa.String(255), nullable=True),
        sa.Column("artifact_ref", sa.String(255), nullable=True),
        sa.Column("provenance_ref", sa.String(255), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("reason_codes", sa.JSON(), nullable=False),
        sa.Column("recorded_at", sa.DateTime(timezone=True), nullable=False),
    )
    for col in ["work_id","node_id","actor_ref","actor_kind","action","provenance_ref","status","recorded_at"]:
        op.create_index(f"ix_work_task_record_{col}", "work_task_record", [col])

    op.create_table(
        "work_transition_record",
        sa.Column("transition_id", sa.String(255), primary_key=True),
        sa.Column("work_id", sa.String(255), nullable=False),
        sa.Column("actor_ref", sa.String(255), nullable=False),
        sa.Column("actor_kind", sa.String(32), nullable=False),
        sa.Column("from_state", sa.String(32), nullable=False),
        sa.Column("to_state", sa.String(32), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("evidence_refs", sa.JSON(), nullable=False),
        sa.Column("authority_ref", sa.String(255), nullable=True),
        sa.Column("delegation_ref", sa.String(255), nullable=True),
        sa.Column("policy_ref", sa.String(320), nullable=True),
        sa.Column("signature_ref", sa.String(255), nullable=True),
        sa.Column("attestation_ref", sa.String(255), nullable=True),
        sa.Column("artifact_ref", sa.String(255), nullable=True),
        sa.Column("provenance_ref", sa.String(255), nullable=False),
        sa.Column("applied", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("reason_codes", sa.JSON(), nullable=False),
        sa.Column("recorded_at", sa.DateTime(timezone=True), nullable=False),
    )
    for col in ["work_id","actor_ref","actor_kind","from_state","to_state","provenance_ref","applied","recorded_at"]:
        op.create_index(f"ix_work_transition_record_{col}", "work_transition_record", [col])

    op.create_table(
        "work_handover_record",
        sa.Column("handover_id", sa.String(255), primary_key=True),
        sa.Column("work_id", sa.String(255), nullable=False),
        sa.Column("actor_ref", sa.String(255), nullable=False),
        sa.Column("from_state", sa.String(32), nullable=False),
        sa.Column("reason_codes", sa.JSON(), nullable=False),
        sa.Column("human_target_ref", sa.String(255), nullable=True),
        sa.Column("preserved_state", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("provenance_ref", sa.String(255), nullable=False),
        sa.Column("status", sa.String(32), nullable=False, server_default="OPEN"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    for col in ["work_id","actor_ref","from_state","human_target_ref","provenance_ref","status","created_at"]:
        op.create_index(f"ix_work_handover_record_{col}", "work_handover_record", [col])


def downgrade() -> None:
    op.drop_table("work_handover_record")
    op.drop_table("work_transition_record")
    op.drop_table("work_task_record")
    op.drop_table("work_instance")
    op.drop_table("work_execution_plan")
    op.drop_table("work_graph_version")
    op.drop_table("work_contract_version")
