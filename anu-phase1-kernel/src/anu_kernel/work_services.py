from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session

from .contracts import (
    AgentAttestationContract,
    AuditEventContract,
    AuthorityEvaluationRequest,
    Effect,
    PolicyEvaluationRequest,
    SignatureRecordContract,
    SubjectType,
)
from .db import AgentAttestation, IdentityRecord, ProvenanceRecord, SignatureRecord
from .errors import DomainValidationError
from .ids import urn, uuid7
from .repository import add_audit
from .services import evaluate_authority, evaluate_policy
from .trust import verify_agent_attestation, verify_signature_record
from .sbbs_runtime_contracts import AssemblyExecutionRequest
from .sbbs_runtime_services import execute_assembly
from .work_contracts import (
    AutonomyLevel,
    ExecutionClass,
    ExecutionPlan,
    ExecutionPlanRequest,
    GovernedWorkGraph,
    HandoverRequest,
    HandoverResult,
    ResponsibilityTraceItem,
    WorkContract,
    WorkInstanceView,
    WorkReplayResult,
    WorkStartRequest,
    WorkState,
    WorkTaskRequest,
    WorkTaskResult,
    WorkTransitionRequest,
    WorkTransitionResult,
)
from .work_models import (
    HandoverRecord,
    WorkExecutionPlanRecord,
    WorkInstanceRecord,
    WorkTaskRecord,
    WorkTransitionRecord,
)
from .work_repository import (
    active_graph_for_work_type,
    add_execution_plan,
    add_handover_record,
    add_task_record,
    add_transition_record,
    add_work_contract,
    add_work_graph,
    add_work_instance,
    get_work_contract,
    get_work_graph,
    get_work_instance,
    update_work_state,
    work_handovers,
    work_tasks,
    work_transitions,
)


_AUTONOMY_ORDER = {f"A{i}": i for i in range(6)}

_ALLOWED_TRANSITIONS: dict[str, set[str]] = {
    "CREATED": {"CONTEXT_READY", "BLOCKED", "CANCELLED"},
    "CONTEXT_READY": {"IN_PROGRESS", "BLOCKED", "CANCELLED"},
    "IN_PROGRESS": {"PROPOSAL_READY", "REVIEW_REQUIRED", "EXECUTED", "EVIDENCE_CAPTURED", "BLOCKED", "FAILED"},
    "PROPOSAL_READY": {"REVIEW_REQUIRED", "REVISION_REQUIRED", "BLOCKED", "CANCELLED"},
    "REVIEW_REQUIRED": {"APPROVED", "REJECTED", "REVISION_REQUIRED", "BLOCKED", "CANCELLED"},
    "APPROVED": {"ACTION_AUTHORIZED", "EVIDENCE_CAPTURED", "CLOSED", "BLOCKED"},
    "REJECTED": {"CLOSED", "REVISION_REQUIRED"},
    "REVISION_REQUIRED": {"IN_PROGRESS", "CANCELLED"},
    "ACTION_AUTHORIZED": {"EXECUTING", "BLOCKED", "CANCELLED"},
    "EXECUTING": {"EXECUTED", "BLOCKED", "FAILED"},
    "EXECUTED": {"EVIDENCE_CAPTURED", "BLOCKED"},
    "EVIDENCE_CAPTURED": {"OUTCOME_OBSERVED", "CLOSED", "BLOCKED"},
    "OUTCOME_OBSERVED": {"CLOSED"},
    "BLOCKED": {"RECOVERING", "ESCALATED", "CANCELLED"},
    "ESCALATED": {"RECOVERING", "CANCELLED"},
    "FAILED": {"RECOVERING", "ESCALATED", "CANCELLED"},
    "RECOVERING": {"CONTEXT_READY", "IN_PROGRESS", "REVIEW_REQUIRED", "CANCELLED"},
    "CANCELLED": set(),
    "CLOSED": set(),
}


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _split_ref(ref: str) -> tuple[str, str]:
    if "@" not in ref:
        raise DomainValidationError("versioned reference required", ["VERSIONED_REF_REQUIRED"])
    return ref.rsplit("@", 1)


def _contract_from_row(row) -> WorkContract:
    from .contracts import EffectivePeriod, LifecycleState
    return WorkContract(
        work_type_id=row.work_type_id,
        name=row.name,
        description=row.description,
        version=row.version,
        owner_ref=row.owner_ref,
        goal=row.goal,
        scope=row.scope or {},
        execution_class=ExecutionClass(row.execution_class),
        allowed_autonomy=AutonomyLevel(row.allowed_autonomy),
        human_participants=row.human_participants or [],
        agent_assignments=row.agent_assignments or [],
        capability_refs=row.capability_refs or [],
        data_scope=row.data_scope or {},
        knowledge_requirements=row.knowledge_requirements or [],
        decision_points=row.decision_points or [],
        approval_points=row.approval_points or [],
        signature_policy_ref=row.signature_policy_ref,
        evidence_requirements=row.evidence_requirements or [],
        risk_class=row.risk_class,
        outcome_definition=row.outcome_definition or {},
        escalation=row.escalation or {},
        failure_policy=row.failure_policy or {},
        trace_policy=row.trace_policy or {},
        retention=row.retention or {},
        effective_period=EffectivePeriod(valid_from=row.effective_from, valid_until=row.effective_to),
        lifecycle_state=LifecycleState(row.lifecycle_state),
        provenance_ref=row.provenance_ref,
    )


def _graph_from_row(row) -> GovernedWorkGraph:
    from .contracts import EffectivePeriod, LifecycleState
    return GovernedWorkGraph(
        graph_id=row.graph_id,
        work_type_ref=row.work_type_ref,
        version=row.version,
        owner_ref=row.owner_ref,
        entry_node=row.entry_node,
        nodes=row.nodes or [],
        effective_period=EffectivePeriod(valid_from=row.effective_from, valid_until=row.effective_to),
        lifecycle_state=LifecycleState(row.lifecycle_state),
        provenance_ref=row.provenance_ref,
    )


def _identity_type(session: Session, subject_ref: str) -> SubjectType:
    row = session.query(IdentityRecord).filter(IdentityRecord.subject_id == subject_ref).first()
    if row is None:
        # Synthetic pilot defaults to Human only when caller explicitly marks HUMAN.
        return SubjectType.HUMAN
    return SubjectType(row.subject_type)


def _signature_contract(row: SignatureRecord) -> SignatureRecordContract:
    return SignatureRecordContract(
        signature_id=row.signature_id,
        signer_identity_ref=row.signer_identity_ref,
        signer_type=row.signer_type,
        signer_role_ref=row.signer_role_ref,
        authority_ref=row.authority_ref,
        credential_ref=row.credential_ref,
        signature_method=row.signature_method,
        intent=row.intent,
        artifact_ref=row.artifact_ref,
        artifact_version=row.artifact_version,
        artifact_hash=row.artifact_hash,
        work_ref=row.work_ref,
        decision_ref=row.decision_ref,
        policy_version=row.policy_version,
        delegation_ref=row.delegation_ref,
        signed_at=row.signed_at.replace(tzinfo=timezone.utc) if row.signed_at.tzinfo is None else row.signed_at,
        signature_value=row.signature_value,
        provenance_ref=row.provenance_ref,
    )


def _attestation_contract(row: AgentAttestation) -> AgentAttestationContract:
    return AgentAttestationContract(
        attestation_id=row.attestation_id,
        agent_ref=row.agent_ref,
        agent_version=row.agent_version,
        owner_ref=row.owner_ref,
        runtime_ref=row.runtime_ref,
        model_dependency=row.model_dependency,
        purpose=row.purpose,
        work_ref=row.work_ref,
        action=row.action,
        capability_ref=row.capability_ref,
        tool_ref=row.tool_ref,
        delegation_ref=row.delegation_ref,
        policy_version=row.policy_version,
        input_refs=row.input_refs or [],
        artifact_ref=row.artifact_ref,
        artifact_hash=row.artifact_hash,
        timestamp=row.timestamp.replace(tzinfo=timezone.utc) if row.timestamp.tzinfo is None else row.timestamp,
        credential_ref=row.credential_ref,
        attestation_signature=row.attestation_signature,
        provenance_ref=row.provenance_ref,
        consequential=row.consequential,
    )


def _audit(session: Session, *, event_type: str, actor_ref: str, action: str, work_id: str, trace_id: str, result: str, target_ref: str | None = None, authority_ref: str | None = None, delegation_ref: str | None = None, policy_refs: list[str] | None = None, provenance_ref: str | None = None) -> None:
    now = _now()
    add_audit(session, AuditEventContract(
        audit_id=urn("audit", uuid7()),
        event_type=event_type,
        actor_identity=actor_ref,
        authority_ref=authority_ref,
        delegation_ref=delegation_ref,
        policy_refs=policy_refs or [],
        action=action,
        target_ref=target_ref,
        result=result,
        work_ref=work_id,
        trace_id=trace_id,
        occurred_at=now,
        recorded_at=now,
        provenance_ref=provenance_ref,
    ))


def register_work_contract(session: Session, contract: WorkContract):
    return add_work_contract(session, contract)


def register_work_graph(session: Session, graph: GovernedWorkGraph):
    return add_work_graph(session, graph)


def plan_execution(session: Session, req: ExecutionPlanRequest) -> ExecutionPlan:
    if session.get(ProvenanceRecord, req.provenance_ref) is None:
        raise DomainValidationError("provenance not found", ["PROVENANCE_REQUIRED"])
    contract_row = get_work_contract(session, req.work_type_ref)
    if contract_row is None or contract_row.lifecycle_state != "ACTIVE":
        raise DomainValidationError("active work contract not found", ["WORK_CONTRACT_NOT_FOUND"])
    graph_row = active_graph_for_work_type(session, req.work_type_ref)
    if graph_row is None:
        raise DomainValidationError("active work graph not found", ["WORK_GRAPH_NOT_FOUND"])
    contract = _contract_from_row(contract_row)
    if req.risk_class != contract.risk_class:
        raise DomainValidationError("risk class differs from approved Work Contract", ["RISK_CLASS_MISMATCH"])
    requested = set(req.requested_capability_refs)
    allowed = set(contract.capability_refs)
    if not requested.issubset(allowed):
        raise DomainValidationError("requested capability outside approved Work Contract", ["CAPABILITY_OUTSIDE_WORK_CONTRACT"])
    # Planner deliberately does not accept or synthesize authority/policy/data-scope inputs.
    checks = ["identity", "role", "authority_if_consequential", "policy", "data_scope", "evidence", "signature_if_required", "trace"]
    plan = ExecutionPlan(
        plan_id=urn("execution-plan", uuid7()),
        work_type_ref=req.work_type_ref,
        work_graph_ref=f"{graph_row.graph_id}@{graph_row.version}",
        goal=req.goal,
        execution_class=contract.execution_class,
        autonomy_level=contract.allowed_autonomy,
        required_capability_refs=sorted(requested or allowed),
        required_checks=checks,
        decision_points=[x.decision_id for x in contract.decision_points],
        signature_points=[x.approval_id for x in contract.approval_points if x.signature_required],
        fallback={"on_missing_authority": "HANDOVER", "on_missing_evidence": "HANDOVER", "on_failure": "PRESERVE_STATE_HANDOVER"},
        trace_policy=contract.trace_policy,
        provenance_ref=req.provenance_ref,
        created_at=_now(),
    )
    add_execution_plan(session, WorkExecutionPlanRecord(
        plan_id=plan.plan_id,
        work_type_ref=plan.work_type_ref,
        work_graph_ref=plan.work_graph_ref,
        goal=plan.goal,
        execution_class=plan.execution_class.value,
        autonomy_level=plan.autonomy_level.value,
        required_capability_refs=plan.required_capability_refs,
        required_checks=plan.required_checks,
        decision_points=plan.decision_points,
        signature_points=plan.signature_points,
        fallback=plan.fallback,
        trace_policy=plan.trace_policy,
        provenance_ref=plan.provenance_ref,
        created_at=plan.created_at,
    ))
    return plan


def start_work(session: Session, req: WorkStartRequest) -> WorkInstanceView:
    plan = session.get(WorkExecutionPlanRecord, req.plan_ref)
    if plan is None:
        raise DomainValidationError("execution plan not found", ["EXECUTION_PLAN_NOT_FOUND"])
    now = _now()
    row = WorkInstanceRecord(
        work_id=urn("work", uuid7()),
        plan_ref=plan.plan_id,
        work_type_ref=plan.work_type_ref,
        work_graph_ref=plan.work_graph_ref,
        execution_class=plan.execution_class,
        autonomy_level=plan.autonomy_level,
        state=WorkState.CREATED.value,
        requester_ref=req.requester_ref,
        context=req.context,
        trace_id=req.trace_id,
        created_at=now,
        updated_at=now,
    )
    add_work_instance(session, row)
    _audit(session, event_type="WORK_CREATED", actor_ref=req.requester_ref, action="work.create", work_id=row.work_id, trace_id=row.trace_id, result="CREATED", provenance_ref=plan.provenance_ref)
    return _work_view(row)


def _work_view(row: WorkInstanceRecord) -> WorkInstanceView:
    return WorkInstanceView(
        work_id=row.work_id,
        plan_ref=row.plan_ref,
        work_type_ref=row.work_type_ref,
        execution_class=ExecutionClass(row.execution_class),
        autonomy_level=AutonomyLevel(row.autonomy_level),
        state=WorkState(row.state),
        requester_ref=row.requester_ref,
        context=row.context or {},
        trace_id=row.trace_id,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def _contract_graph_for_work(session: Session, work: WorkInstanceRecord) -> tuple[WorkContract, GovernedWorkGraph]:
    c_row = get_work_contract(session, work.work_type_ref)
    g_row = get_work_graph(session, work.work_graph_ref)
    if c_row is None or g_row is None:
        raise DomainValidationError("work contract/graph unavailable", ["WORK_DEFINITION_UNAVAILABLE"])
    return _contract_from_row(c_row), _graph_from_row(g_row)


def _node(graph: GovernedWorkGraph, node_id: str):
    for n in graph.nodes:
        if n.node_id == node_id:
            return n
    raise DomainValidationError("work node not found", ["WORK_NODE_NOT_FOUND"])


def _agent_assignment(contract: WorkContract, agent_ref: str):
    for a in contract.agent_assignments:
        if a.agent_ref == agent_ref:
            return a
    return None


def _block_and_handover(session: Session, work: WorkInstanceRecord, actor_ref: str, provenance_ref: str, reasons: list[str], target_ref: str | None = None) -> None:
    now = _now()
    previous = work.state
    transition = WorkTransitionRecord(
        transition_id=urn("work-transition", uuid7()),
        work_id=work.work_id,
        actor_ref=actor_ref,
        actor_kind="SYSTEM",
        from_state=previous,
        to_state=WorkState.BLOCKED.value,
        reason=";".join(sorted(set(reasons))),
        evidence_refs=[],
        provenance_ref=provenance_ref,
        applied=True,
        reason_codes=sorted(set(reasons)),
        recorded_at=now,
    )
    add_transition_record(session, transition)
    update_work_state(session, work, WorkState.BLOCKED.value)
    add_handover_record(session, HandoverRecord(
        handover_id=urn("handover", uuid7()),
        work_id=work.work_id,
        actor_ref=actor_ref,
        from_state=previous,
        reason_codes=sorted(set(reasons)),
        human_target_ref=target_ref,
        preserved_state=True,
        provenance_ref=provenance_ref,
        status="OPEN",
        created_at=now,
    ))
    _audit(session, event_type="WORK_HANDOVER_REQUIRED", actor_ref=actor_ref, action="work.handover", work_id=work.work_id, trace_id=work.trace_id, result="BLOCKED", provenance_ref=provenance_ref)


def execute_task(session: Session, req: WorkTaskRequest) -> WorkTaskResult:
    work = get_work_instance(session, req.work_id)
    if work is None:
        raise DomainValidationError("work not found", ["WORK_NOT_FOUND"])
    if session.get(ProvenanceRecord, req.provenance_ref) is None:
        raise DomainValidationError("provenance not found", ["PROVENANCE_REQUIRED"])
    contract, graph = _contract_graph_for_work(session, work)
    node = _node(graph, req.node_id)
    reasons: list[str] = []
    output: dict[str, Any] = {}

    if node.node_type == "AGENT_TASK":
        if req.actor_kind != "AGENT":
            reasons.append("AGENT_TASK_REQUIRES_AGENT")
        assignment = _agent_assignment(contract, req.actor_ref)
        if assignment is None:
            reasons.append("AGENT_NOT_ASSIGNED")
        else:
            if req.action in assignment.forbidden_actions:
                reasons.append("AGENT_ACTION_FORBIDDEN")
            if assignment.allowed_actions and req.action not in assignment.allowed_actions:
                reasons.append("AGENT_ACTION_NOT_ALLOWED")
            required_autonomy = (node.allowed_autonomy or contract.allowed_autonomy).value
            if _AUTONOMY_ORDER[required_autonomy] > _AUTONOMY_ORDER[assignment.autonomy_ceiling.value]:
                reasons.append("AUTONOMY_EXCEEDS_ASSIGNMENT")
            if _AUTONOMY_ORDER[required_autonomy] > _AUTONOMY_ORDER[contract.allowed_autonomy.value]:
                reasons.append("AUTONOMY_EXCEEDS_WORK_CONTRACT")
            if contract.execution_class == ExecutionClass.E3 and work.state not in {WorkState.APPROVED.value, WorkState.ACTION_AUTHORIZED.value, WorkState.EXECUTING.value, WorkState.EXECUTED.value} and _AUTONOMY_ORDER[required_autonomy] > _AUTONOMY_ORDER[AutonomyLevel.A2.value]:
                reasons.append("E3_PRE_DECISION_AUTONOMY_MAX_A2")
        if node.required_authority_action:
            if not req.delegation_ref:
                reasons.append("ACTIVE_DELEGATION_REQUIRED")
            if not req.attestation_ref:
                reasons.append("AGENT_ATTESTATION_REQUIRED")
            if req.attestation_ref:
                att_row = session.get(AgentAttestation, req.attestation_ref)
                if att_row is None:
                    reasons.append("ATTESTATION_NOT_FOUND")
                else:
                    verification = verify_agent_attestation(session, _attestation_contract(att_row))
                    if not verification.attestation_valid:
                        reasons.extend(verification.reason_codes or ["ATTESTATION_INVALID"])

    elif node.node_type == "HUMAN_TASK":
        if req.actor_kind != "HUMAN":
            reasons.append("HUMAN_TASK_REQUIRES_HUMAN")

    elif node.node_type == "CAPABILITY_TASK":
        if not node.capability_ref or node.capability_ref not in contract.capability_refs:
            reasons.append("CAPABILITY_OUTSIDE_WORK_CONTRACT")
        assembly_ref = node.configuration.get("assembly_ref")
        if assembly_ref and not reasons:
            result = execute_assembly(session, AssemblyExecutionRequest(
                assembly_ref=assembly_ref,
                input_payload=req.input_payload,
                trace_id=work.trace_id,
            ))
            if result.status != "SUCCEEDED":
                reasons.append("CAPABILITY_EXECUTION_FAILED")
            else:
                output = result.final_payload or {}
        elif not reasons:
            output = dict(req.input_payload)

    elif node.node_type == "TIMER":
        if not bool(req.input_payload.get("timer_elapsed")):
            reasons.append("TIMER_NOT_ELAPSED")
        else:
            output = {"timer_elapsed": True}

    elif node.node_type == "EVENT_WAIT":
        if not bool(req.input_payload.get("event_received")):
            reasons.append("EVENT_NOT_RECEIVED")
        else:
            output = {"event_received": True, "event_ref": req.input_payload.get("event_ref")}

    elif node.node_type == "POLICY_GATE":
        action = node.required_authority_action or req.action
        subject_type = _identity_type(session, req.actor_ref)
        auth = evaluate_authority(session, AuthorityEvaluationRequest(
            subject_ref=req.actor_ref,
            subject_type=subject_type,
            action=action,
            resource=node.required_resource_ref,
            context_ref=work.work_type_ref,
            at=_now(),
        ))
        if not auth["allowed"]:
            reasons.extend(auth["reason_codes"] or ["AUTHORITY_NOT_PRESENT"])
        pd = evaluate_policy(session, PolicyEvaluationRequest(
            subject_ref=req.actor_ref,
            authority_refs=auth["authority_refs"],
            delegation_refs=auth["delegation_refs"],
            resource=node.required_resource_ref,
            action=action,
            context=work.work_type_ref,
            risk=contract.risk_class,
            at=_now(),
        ))
        if pd.effect not in {Effect.ALLOW, Effect.REQUIRE_REVIEW, Effect.REQUIRE_SIGNATURE}:
            reasons.extend(pd.reason_codes or ["POLICY_DENY"])
        output = {"authority_refs": auth["authority_refs"], "delegation_refs": auth["delegation_refs"], "policy_refs": pd.policy_refs, "policy_effect": pd.effect.value}

    else:
        # Control nodes are normally driven by transition_work; recording them as a task is allowed for trace only.
        output = dict(req.input_payload)

    if reasons:
        _block_and_handover(session, work, req.actor_ref, req.provenance_ref, reasons, contract.escalation.get("human_target_ref"))
        status = "HANDOVER_REQUIRED"
    else:
        status = "SUCCEEDED"

    now = _now()
    row = WorkTaskRecord(
        task_id=urn("work-task", uuid7()),
        work_id=work.work_id,
        node_id=req.node_id,
        actor_ref=req.actor_ref,
        actor_kind=req.actor_kind,
        action=req.action,
        input_payload=req.input_payload,
        output_payload=output,
        evidence_refs=req.evidence_refs,
        authority_ref=req.authority_ref,
        delegation_ref=req.delegation_ref,
        policy_ref=req.policy_ref,
        signature_ref=req.signature_ref,
        attestation_ref=req.attestation_ref,
        artifact_ref=req.artifact_ref,
        provenance_ref=req.provenance_ref,
        status=status,
        reason_codes=sorted(set(reasons)),
        recorded_at=now,
    )
    add_task_record(session, row)
    _audit(session, event_type="WORK_TASK", actor_ref=req.actor_ref, action=req.action, work_id=work.work_id, trace_id=work.trace_id, result=status, target_ref=req.node_id, authority_ref=req.authority_ref, delegation_ref=req.delegation_ref, policy_refs=[req.policy_ref] if req.policy_ref else [], provenance_ref=req.provenance_ref)
    return WorkTaskResult(task_id=row.task_id, work_id=work.work_id, node_id=req.node_id, actor_ref=req.actor_ref, status=status, output_payload=output, reason_codes=row.reason_codes, recorded_at=now)


def _approval_point(contract: WorkContract, to_state: WorkState):
    if to_state != WorkState.APPROVED:
        return None
    return next((p for p in contract.approval_points if p.human_required), None)


def transition_work(session: Session, req: WorkTransitionRequest) -> WorkTransitionResult:
    work = get_work_instance(session, req.work_id)
    if work is None:
        raise DomainValidationError("work not found", ["WORK_NOT_FOUND"])
    if session.get(ProvenanceRecord, req.provenance_ref) is None:
        raise DomainValidationError("provenance not found", ["PROVENANCE_REQUIRED"])
    contract, _ = _contract_graph_for_work(session, work)
    from_state = WorkState(work.state)
    reasons: list[str] = []
    if req.to_state.value not in _ALLOWED_TRANSITIONS.get(from_state.value, set()):
        reasons.append("INVALID_WORK_STATE_TRANSITION")

    if req.to_state in {WorkState.REVIEW_REQUIRED, WorkState.APPROVED, WorkState.ACTION_AUTHORIZED}:
        if contract.evidence_requirements and len(req.evidence_refs) < len(contract.evidence_requirements):
            reasons.append("MANDATORY_EVIDENCE_MISSING")

    approval = _approval_point(contract, req.to_state)
    policy_refs: list[str] = []
    if approval is not None:
        if req.actor_kind != "HUMAN":
            reasons.append("HUMAN_APPROVAL_REQUIRED")
        action = approval.required_authority_action
        if action:
            auth = evaluate_authority(session, AuthorityEvaluationRequest(
                subject_ref=req.actor_ref,
                subject_type=_identity_type(session, req.actor_ref),
                action=action,
                resource=approval.resource_ref,
                context_ref=work.work_type_ref,
                at=_now(),
            ))
            if not auth["allowed"]:
                reasons.extend(auth["reason_codes"] or ["AUTHORITY_NOT_PRESENT"])
            if req.authority_ref and req.authority_ref not in auth["authority_refs"]:
                reasons.append("AUTHORITY_REF_NOT_VALID")
            if not req.authority_ref:
                reasons.append("AUTHORITY_REF_REQUIRED")
            pd = evaluate_policy(session, PolicyEvaluationRequest(
                subject_ref=req.actor_ref,
                role_context=[],
                authority_refs=auth["authority_refs"],
                delegation_refs=auth["delegation_refs"],
                resource=approval.resource_ref,
                action=action,
                context=work.work_type_ref,
                risk=contract.risk_class,
                at=_now(),
            ))
            policy_refs = pd.policy_refs
            if pd.effect == Effect.DENY:
                reasons.extend(pd.reason_codes or ["POLICY_DENY"])
            if req.policy_ref and req.policy_ref not in pd.policy_refs:
                reasons.append("POLICY_REF_NOT_APPLICABLE")
            if not req.policy_ref:
                reasons.append("POLICY_REF_REQUIRED")
            signature_required = approval.signature_required or pd.effect == Effect.REQUIRE_SIGNATURE
        else:
            signature_required = approval.signature_required
        if signature_required:
            if not req.signature_ref:
                reasons.append("HUMAN_SIGNATURE_REQUIRED")
            else:
                sig = session.get(SignatureRecord, req.signature_ref)
                if sig is None:
                    reasons.append("SIGNATURE_NOT_FOUND")
                else:
                    result = verify_signature_record(session, _signature_contract(sig))
                    if not result.institutional_valid:
                        reasons.extend(result.reason_codes or ["SIGNATURE_INVALID"])
                    if sig.work_ref not in (None, work.work_id):
                        reasons.append("SIGNATURE_WORK_MISMATCH")
                    if req.artifact_ref and sig.artifact_ref != req.artifact_ref:
                        reasons.append("SIGNATURE_ARTIFACT_MISMATCH")

    if contract.execution_class == ExecutionClass.E3 and req.to_state == WorkState.APPROVED and req.actor_kind != "HUMAN":
        reasons.append("E3_HUMAN_AUTHORITY_REQUIRED")

    now = _now()
    if reasons:
        _block_and_handover(session, work, req.actor_ref, req.provenance_ref, reasons, contract.escalation.get("human_target_ref"))
        return WorkTransitionResult(
            transition_id=urn("work-transition", uuid7()),
            work_id=work.work_id,
            from_state=from_state,
            to_state=WorkState.BLOCKED,
            status="HANDOVER_REQUIRED",
            reason_codes=sorted(set(reasons)),
            recorded_at=now,
        )

    row = WorkTransitionRecord(
        transition_id=urn("work-transition", uuid7()),
        work_id=work.work_id,
        actor_ref=req.actor_ref,
        actor_kind=req.actor_kind,
        from_state=from_state.value,
        to_state=req.to_state.value,
        reason=req.reason,
        evidence_refs=req.evidence_refs,
        authority_ref=req.authority_ref,
        delegation_ref=req.delegation_ref,
        policy_ref=req.policy_ref,
        signature_ref=req.signature_ref,
        attestation_ref=req.attestation_ref,
        artifact_ref=req.artifact_ref,
        provenance_ref=req.provenance_ref,
        applied=True,
        reason_codes=[],
        recorded_at=now,
    )
    add_transition_record(session, row)
    update_work_state(session, work, req.to_state.value)
    _audit(session, event_type="WORK_TRANSITION", actor_ref=req.actor_ref, action=f"work.transition.{req.to_state.value.lower()}", work_id=work.work_id, trace_id=work.trace_id, result="APPLIED", authority_ref=req.authority_ref, delegation_ref=req.delegation_ref, policy_refs=policy_refs or ([req.policy_ref] if req.policy_ref else []), provenance_ref=req.provenance_ref)
    return WorkTransitionResult(transition_id=row.transition_id, work_id=work.work_id, from_state=from_state, to_state=req.to_state, status="APPLIED", reason_codes=[], recorded_at=now)


def request_handover(session: Session, req: HandoverRequest) -> HandoverResult:
    work = get_work_instance(session, req.work_id)
    if work is None:
        raise DomainValidationError("work not found", ["WORK_NOT_FOUND"])
    if session.get(ProvenanceRecord, req.provenance_ref) is None:
        raise DomainValidationError("provenance not found", ["PROVENANCE_REQUIRED"])
    now = _now()
    previous = WorkState(work.state)
    row = HandoverRecord(
        handover_id=urn("handover", uuid7()),
        work_id=work.work_id,
        actor_ref=req.actor_ref,
        from_state=previous.value,
        reason_codes=req.reason_codes,
        human_target_ref=req.human_target_ref,
        preserved_state=req.preserved_state,
        provenance_ref=req.provenance_ref,
        status="OPEN",
        created_at=now,
    )
    add_handover_record(session, row)
    if work.state != WorkState.BLOCKED.value:
        update_work_state(session, work, WorkState.BLOCKED.value)
    _audit(session, event_type="WORK_HANDOVER", actor_ref=req.actor_ref, action="work.handover", work_id=work.work_id, trace_id=work.trace_id, result="OPEN", provenance_ref=req.provenance_ref)
    return HandoverResult(handover_id=row.handover_id, work_id=work.work_id, from_state=previous, reason_codes=req.reason_codes, human_target_ref=req.human_target_ref, created_at=now)


def replay_work(session: Session, work_id: str) -> WorkReplayResult:
    work = get_work_instance(session, work_id)
    if work is None:
        raise DomainValidationError("work not found", ["WORK_NOT_FOUND"])
    events: list[tuple[datetime, ResponsibilityTraceItem]] = []
    seq = 0
    for t in work_transitions(session, work_id):
        seq += 1
        item = ResponsibilityTraceItem(
            sequence=seq,
            event_type="TRANSITION",
            actor_ref=t.actor_ref,
            actor_kind=t.actor_kind,
            state_from=t.from_state,
            state_to=t.to_state,
            authority_ref=t.authority_ref,
            delegation_ref=t.delegation_ref,
            policy_ref=t.policy_ref,
            evidence_refs=t.evidence_refs or [],
            signature_ref=t.signature_ref,
            attestation_ref=t.attestation_ref,
            artifact_ref=t.artifact_ref,
            reason_codes=t.reason_codes or [],
            recorded_at=t.recorded_at,
        )
        events.append((t.recorded_at, item))
    for t in work_tasks(session, work_id):
        seq += 1
        item = ResponsibilityTraceItem(
            sequence=seq,
            event_type=f"TASK:{t.node_id}:{t.status}",
            actor_ref=t.actor_ref,
            actor_kind=t.actor_kind,
            authority_ref=t.authority_ref,
            delegation_ref=t.delegation_ref,
            policy_ref=t.policy_ref,
            evidence_refs=t.evidence_refs or [],
            signature_ref=t.signature_ref,
            attestation_ref=t.attestation_ref,
            artifact_ref=t.artifact_ref,
            reason_codes=t.reason_codes or [],
            recorded_at=t.recorded_at,
        )
        events.append((t.recorded_at, item))
    for h in work_handovers(session, work_id):
        seq += 1
        item = ResponsibilityTraceItem(
            sequence=seq,
            event_type="HANDOVER",
            actor_ref=h.actor_ref,
            actor_kind="SYSTEM",
            state_from=h.from_state,
            state_to="BLOCKED",
            reason_codes=h.reason_codes or [],
            recorded_at=h.created_at,
        )
        events.append((h.created_at, item))
    events.sort(key=lambda x: (x[0], x[1].event_type))
    chain: list[ResponsibilityTraceItem] = []
    for i, (_, item) in enumerate(events, start=1):
        data = item.model_dump()
        data["sequence"] = i
        chain.append(ResponsibilityTraceItem(**data))
    warnings: list[str] = []
    contract, _ = _contract_graph_for_work(session, work)
    if contract.execution_class == ExecutionClass.E3:
        approvals = [x for x in chain if x.state_to == "APPROVED"]
        if approvals and any(not x.authority_ref or not x.signature_ref for x in approvals):
            warnings.append("E3_APPROVAL_TRACE_INCOMPLETE")
    return WorkReplayResult(
        work_id=work_id,
        current_state=WorkState(work.state),
        trace_id=work.trace_id,
        responsibility_chain=chain,
        replay_complete=not warnings,
        warnings=warnings,
    )
