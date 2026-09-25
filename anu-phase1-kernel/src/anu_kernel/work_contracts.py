from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Literal

from pydantic import Field, model_validator

from .contracts import EffectivePeriod, KernelModel, LifecycleState


class ExecutionClass(str, Enum):
    E0 = "E0"
    E1 = "E1"
    E2 = "E2"
    E3 = "E3"


class AutonomyLevel(str, Enum):
    A0 = "A0"
    A1 = "A1"
    A2 = "A2"
    A3 = "A3"
    A4 = "A4"
    A5 = "A5"


class WorkState(str, Enum):
    CREATED = "CREATED"
    CONTEXT_READY = "CONTEXT_READY"
    IN_PROGRESS = "IN_PROGRESS"
    PROPOSAL_READY = "PROPOSAL_READY"
    REVIEW_REQUIRED = "REVIEW_REQUIRED"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    REVISION_REQUIRED = "REVISION_REQUIRED"
    ACTION_AUTHORIZED = "ACTION_AUTHORIZED"
    EXECUTING = "EXECUTING"
    EXECUTED = "EXECUTED"
    EVIDENCE_CAPTURED = "EVIDENCE_CAPTURED"
    OUTCOME_OBSERVED = "OUTCOME_OBSERVED"
    CLOSED = "CLOSED"
    BLOCKED = "BLOCKED"
    ESCALATED = "ESCALATED"
    CANCELLED = "CANCELLED"
    FAILED = "FAILED"
    RECOVERING = "RECOVERING"


TaskType = Literal[
    "HUMAN_TASK",
    "AGENT_TASK",
    "CAPABILITY_TASK",
    "POLICY_GATE",
    "DECISION",
    "APPROVAL_SIGNATURE",
    "TIMER",
    "EVENT_WAIT",
    "HANDOVER",
    "ESCALATION",
    "RECOVERY",
]


class WorkParticipant(KernelModel):
    subject_ref: str
    role_ref: str | None = None
    responsibility: str


class AgentAssignment(KernelModel):
    agent_ref: str
    purpose: str
    owner_ref: str
    allowed_capability_refs: list[str] = Field(default_factory=list)
    allowed_actions: list[str] = Field(default_factory=list)
    forbidden_actions: list[str] = Field(default_factory=list)
    autonomy_ceiling: AutonomyLevel
    delegation_required_for_consequential_action: bool = True
    human_supervisor_ref: str | None = None


class DecisionPoint(KernelModel):
    decision_id: str
    description: str
    consequential: bool = False
    human_authority_required: bool = False
    evidence_required: list[str] = Field(default_factory=list)


class ApprovalPoint(KernelModel):
    approval_id: str
    description: str
    human_required: bool = True
    signature_required: bool = False
    required_role_ref: str | None = None
    required_authority_action: str | None = None
    resource_ref: str | None = None


class WorkContract(KernelModel):
    work_type_id: str
    name: str
    description: str
    version: str
    owner_ref: str
    goal: str
    scope: dict[str, Any] = Field(default_factory=dict)
    execution_class: ExecutionClass
    allowed_autonomy: AutonomyLevel
    human_participants: list[WorkParticipant] = Field(default_factory=list)
    agent_assignments: list[AgentAssignment] = Field(default_factory=list)
    capability_refs: list[str] = Field(default_factory=list)
    data_scope: dict[str, Any] = Field(default_factory=dict)
    knowledge_requirements: list[str] = Field(default_factory=list)
    decision_points: list[DecisionPoint] = Field(default_factory=list)
    approval_points: list[ApprovalPoint] = Field(default_factory=list)
    signature_policy_ref: str | None = None
    evidence_requirements: list[str] = Field(default_factory=list)
    risk_class: str
    outcome_definition: dict[str, Any] = Field(default_factory=dict)
    escalation: dict[str, Any] = Field(default_factory=dict)
    failure_policy: dict[str, Any] = Field(default_factory=dict)
    trace_policy: dict[str, Any] = Field(default_factory=lambda: {"responsibility_chain": True, "replay": True})
    retention: dict[str, Any] = Field(default_factory=dict)
    effective_period: EffectivePeriod
    lifecycle_state: LifecycleState = LifecycleState.ACTIVE
    provenance_ref: str

    @model_validator(mode="after")
    def enforce_phase4_guardrails(self) -> "WorkContract":
        if self.execution_class == ExecutionClass.E1 and self.allowed_autonomy not in {AutonomyLevel.A0, AutonomyLevel.A1}:
            raise ValueError("E1 autonomy must be A0/A1")
        if self.execution_class == ExecutionClass.E3:
            if not any(p.human_authority_required for p in self.decision_points):
                raise ValueError("E3 requires a Human-authority decision point")
            if not any(p.human_required for p in self.approval_points):
                raise ValueError("E3 requires Human approval")
        return self


class WorkNode(KernelModel):
    node_id: str
    node_type: TaskType
    label: str
    actor_ref: str | None = None
    capability_ref: str | None = None
    required_authority_action: str | None = None
    required_resource_ref: str | None = None
    evidence_required: list[str] = Field(default_factory=list)
    signature_required: bool = False
    attestation_required: bool = False
    allowed_autonomy: AutonomyLevel | None = None
    next_nodes: list[str] = Field(default_factory=list)
    failure_node: str | None = None
    configuration: dict[str, Any] = Field(default_factory=dict)


class GovernedWorkGraph(KernelModel):
    graph_id: str
    work_type_ref: str
    version: str
    owner_ref: str
    entry_node: str
    nodes: list[WorkNode]
    effective_period: EffectivePeriod
    lifecycle_state: LifecycleState = LifecycleState.ACTIVE
    provenance_ref: str

    @model_validator(mode="after")
    def validate_graph(self) -> "GovernedWorkGraph":
        ids = [n.node_id for n in self.nodes]
        if len(ids) != len(set(ids)):
            raise ValueError("work graph node ids must be unique")
        if self.entry_node not in set(ids):
            raise ValueError("entry_node must exist")
        known = set(ids)
        for node in self.nodes:
            unknown = set(node.next_nodes) - known
            if node.failure_node:
                unknown |= {node.failure_node} - known
            if unknown:
                raise ValueError(f"unknown work graph node refs: {sorted(unknown)}")
        return self


class ExecutionPlanRequest(KernelModel):
    goal: str
    context: dict[str, Any] = Field(default_factory=dict)
    requester_ref: str
    role_refs: list[str] = Field(default_factory=list)
    work_type_ref: str
    risk_class: str
    requested_capability_refs: list[str] = Field(default_factory=list)
    provenance_ref: str


class ExecutionPlan(KernelModel):
    plan_id: str
    work_type_ref: str
    work_graph_ref: str
    goal: str
    execution_class: ExecutionClass
    autonomy_level: AutonomyLevel
    required_capability_refs: list[str]
    required_checks: list[str]
    decision_points: list[str]
    signature_points: list[str]
    fallback: dict[str, Any]
    trace_policy: dict[str, Any]
    provenance_ref: str
    created_at: datetime


class WorkStartRequest(KernelModel):
    plan_ref: str
    requester_ref: str
    context: dict[str, Any] = Field(default_factory=dict)
    trace_id: str


class WorkInstanceView(KernelModel):
    work_id: str
    plan_ref: str
    work_type_ref: str
    execution_class: ExecutionClass
    autonomy_level: AutonomyLevel
    state: WorkState
    requester_ref: str
    context: dict[str, Any] = Field(default_factory=dict)
    trace_id: str
    created_at: datetime
    updated_at: datetime


class WorkTaskRequest(KernelModel):
    work_id: str
    node_id: str
    actor_ref: str
    actor_kind: Literal["HUMAN", "AGENT", "CAPABILITY"]
    action: str
    input_payload: dict[str, Any] = Field(default_factory=dict)
    evidence_refs: list[str] = Field(default_factory=list)
    authority_ref: str | None = None
    delegation_ref: str | None = None
    policy_ref: str | None = None
    signature_ref: str | None = None
    attestation_ref: str | None = None
    artifact_ref: str | None = None
    provenance_ref: str


class WorkTaskResult(KernelModel):
    task_id: str
    work_id: str
    node_id: str
    actor_ref: str
    status: Literal["SUCCEEDED", "BLOCKED", "FAILED", "HANDOVER_REQUIRED"]
    output_payload: dict[str, Any] = Field(default_factory=dict)
    reason_codes: list[str] = Field(default_factory=list)
    recorded_at: datetime


class WorkTransitionRequest(KernelModel):
    work_id: str
    actor_ref: str
    actor_kind: Literal["HUMAN", "AGENT", "SYSTEM"]
    to_state: WorkState
    reason: str
    evidence_refs: list[str] = Field(default_factory=list)
    authority_ref: str | None = None
    delegation_ref: str | None = None
    policy_ref: str | None = None
    signature_ref: str | None = None
    attestation_ref: str | None = None
    artifact_ref: str | None = None
    provenance_ref: str


class WorkTransitionResult(KernelModel):
    transition_id: str
    work_id: str
    from_state: WorkState
    to_state: WorkState
    status: Literal["APPLIED", "BLOCKED", "HANDOVER_REQUIRED"]
    reason_codes: list[str] = Field(default_factory=list)
    recorded_at: datetime


class HandoverRequest(KernelModel):
    work_id: str
    actor_ref: str
    reason_codes: list[str]
    human_target_ref: str | None = None
    preserved_state: bool = True
    provenance_ref: str


class HandoverResult(KernelModel):
    handover_id: str
    work_id: str
    from_state: WorkState
    status: Literal["OPEN"] = "OPEN"
    reason_codes: list[str]
    human_target_ref: str | None = None
    created_at: datetime


class WorkReplayRequest(KernelModel):
    work_id: str


class ResponsibilityTraceItem(KernelModel):
    sequence: int
    event_type: str
    actor_ref: str | None = None
    actor_kind: str | None = None
    state_from: str | None = None
    state_to: str | None = None
    authority_ref: str | None = None
    delegation_ref: str | None = None
    policy_ref: str | None = None
    evidence_refs: list[str] = Field(default_factory=list)
    signature_ref: str | None = None
    attestation_ref: str | None = None
    artifact_ref: str | None = None
    reason_codes: list[str] = Field(default_factory=list)
    recorded_at: datetime


class WorkReplayResult(KernelModel):
    work_id: str
    current_state: WorkState
    trace_id: str
    responsibility_chain: list[ResponsibilityTraceItem]
    replay_complete: bool
    warnings: list[str] = Field(default_factory=list)
