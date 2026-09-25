from __future__ import annotations

import base64
from datetime import datetime, timezone

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from anu_kernel.capability_contracts import CapabilityContract, CapabilityOperation
from anu_kernel.capability_repository import add_capability
from anu_kernel.contracts import (
    AuthorityGrantContract,
    AuthorityScope,
    EffectivePeriod,
    IdentityContract,
    PolicyContract,
    ProvenanceRecordContract,
    RoleAssignmentContract,
    SignatureRecordContract,
    SubjectType,
    TrustCredentialContract,
)
from anu_kernel.repository import (
    add_authority,
    add_identity,
    add_policy,
    add_provenance,
    add_role,
    add_signature_record,
    add_trust_credential,
)
from anu_kernel.trust import public_key_fingerprint_sha256, signature_signing_bytes
from anu_kernel.work_contracts import (
    AgentAssignment,
    ApprovalPoint,
    AutonomyLevel,
    DecisionPoint,
    ExecutionClass,
    ExecutionPlanRequest,
    GovernedWorkGraph,
    WorkContract,
    WorkNode,
    WorkParticipant,
    WorkStartRequest,
    WorkState,
    WorkTaskRequest,
    WorkTransitionRequest,
)
from anu_kernel.work_services import (
    execute_task,
    plan_execution,
    register_work_contract,
    register_work_graph,
    replay_work,
    start_work,
    transition_work,
)

NOW = datetime(2026, 1, 1, 0, 0, tzinfo=timezone.utc)
OWNER = "urn:anu:org:aru-01"
HUMAN = "urn:anu:human:programme-owner"
AGENT = "urn:anu:agent:academic-assistant"
PROV = "urn:anu:provenance:p4-test"
CAP = "urn:anu:capability:knowledge-retrieval"
CAP_REF = f"{CAP}@1.0.0"


def _seed_base(session):
    add_provenance(session, ProvenanceRecordContract(
        provenance_id=PROV,
        entity_ref="urn:anu:work:p4-test-seed",
        actor_ref="urn:anu:agent:ai-factory",
        effective_time=NOW,
        recorded_time=NOW,
    ))
    add_capability(session, CapabilityContract(
        capability_id=CAP,
        name="Knowledge Retrieval",
        description="P4 reference capability",
        owner_ref=OWNER,
        domain="learning-curriculum",
        version="1.0.0",
        operations=[CapabilityOperation(
            operation_id="knowledge.retrieve",
            purpose="Retrieve governed knowledge",
            input_semantics=["urn:anu:semantic:knowledge-query"],
            output_semantics=["urn:anu:semantic:knowledge-result"],
        )],
        effective_period=EffectivePeriod(valid_from=NOW),
        provenance_ref=PROV,
    ))
    add_identity(session, IdentityContract(
        identity_id="urn:anu:identity:human:programme-owner",
        subject_id=HUMAN,
        subject_type=SubjectType.HUMAN,
        effective_period=EffectivePeriod(valid_from=NOW),
        provenance_ref=PROV,
    ))
    add_identity(session, IdentityContract(
        identity_id="urn:anu:identity:agent:academic-assistant",
        subject_id=AGENT,
        subject_type=SubjectType.AGENT,
        effective_period=EffectivePeriod(valid_from=NOW),
        provenance_ref=PROV,
    ))


def _contract(work_type: str, execution_class: ExecutionClass, autonomy: AutonomyLevel, *, approval=False, signature=False, evidence=None):
    return WorkContract(
        work_type_id=work_type,
        name=work_type.rsplit(":", 1)[-1],
        description="P4 governed work conformance fixture",
        version="1.0.0",
        owner_ref=OWNER,
        goal="Execute governed Human-Agent-Capability work",
        execution_class=execution_class,
        allowed_autonomy=autonomy,
        human_participants=[WorkParticipant(subject_ref=HUMAN, role_ref="programme-owner", responsibility="Human judgment and institutional responsibility")],
        agent_assignments=[AgentAssignment(
            agent_ref=AGENT,
            purpose="Analyze and prepare",
            owner_ref=OWNER,
            allowed_capability_refs=[CAP_REF],
            allowed_actions=["summarize", "prepare-revision", "analyze-evidence"],
            forbidden_actions=["approve", "publish-canonical"],
            autonomy_ceiling=autonomy,
            human_supervisor_ref=HUMAN,
        )],
        capability_refs=[CAP_REF],
        data_scope={"classes": ["SYNTHETIC-ACADEMIC"]},
        knowledge_requirements=["urn:anu:knowledge:programme"],
        decision_points=[DecisionPoint(
            decision_id="decision-main",
            description="Human institutional decision" if execution_class == ExecutionClass.E3 else "Review decision",
            consequential=execution_class == ExecutionClass.E3,
            human_authority_required=execution_class == ExecutionClass.E3,
            evidence_required=evidence or [],
        )] if approval else [],
        approval_points=[ApprovalPoint(
            approval_id="approval-main",
            description="Human approval",
            human_required=True,
            signature_required=signature,
            required_role_ref="programme-owner",
            required_authority_action="academic.programme.approve" if execution_class == ExecutionClass.E3 else "learning.asset.publish",
            resource_ref="urn:anu:programme:se" if execution_class == ExecutionClass.E3 else "urn:anu:learning-asset:lb-01",
        )] if approval else [],
        signature_policy_ref="urn:anu:policy:e3-approval@1.0.0" if signature else None,
        evidence_requirements=evidence or [],
        risk_class="HIGH" if execution_class == ExecutionClass.E3 else ("MEDIUM" if execution_class == ExecutionClass.E2 else "LOW"),
        outcome_definition={"observable": True},
        escalation={"human_target_ref": HUMAN},
        failure_policy={"on_missing_authority": "STOP_HANDOVER", "on_missing_evidence": "STOP_HANDOVER"},
        trace_policy={"responsibility_chain": True, "replay": True},
        retention={"mode": "PILOT"},
        effective_period=EffectivePeriod(valid_from=NOW),
        provenance_ref=PROV,
    )


def _graph(work_type_ref: str, graph_id: str, execution_class: ExecutionClass):
    nodes = [
        WorkNode(node_id="human-goal", node_type="HUMAN_TASK", label="Human goal", actor_ref=HUMAN, next_nodes=["capability"]),
        WorkNode(node_id="capability", node_type="CAPABILITY_TASK", label="Governed capability", capability_ref=CAP_REF, next_nodes=["agent-analysis"]),
        WorkNode(node_id="agent-analysis", node_type="AGENT_TASK", label="Agent analysis", actor_ref=AGENT, allowed_autonomy=AutonomyLevel.A1 if execution_class == ExecutionClass.E1 else AutonomyLevel.A2, next_nodes=["review"] if execution_class != ExecutionClass.E1 else ["outcome"]),
    ]
    if execution_class != ExecutionClass.E1:
        nodes.append(WorkNode(node_id="review", node_type="APPROVAL_SIGNATURE", label="Human review/approval", actor_ref=HUMAN, signature_required=execution_class == ExecutionClass.E3, next_nodes=["outcome"]))
    nodes.append(WorkNode(node_id="outcome", node_type="HUMAN_TASK", label="Observe outcome", actor_ref=HUMAN, next_nodes=[]))
    return GovernedWorkGraph(
        graph_id=graph_id,
        work_type_ref=work_type_ref,
        version="1.0.0",
        owner_ref=OWNER,
        entry_node="human-goal",
        nodes=nodes,
        effective_period=EffectivePeriod(valid_from=NOW),
        provenance_ref=PROV,
    )


def _plan_start(session, contract: WorkContract, graph: GovernedWorkGraph, trace_id: str):
    register_work_contract(session, contract)
    register_work_graph(session, graph)
    ref = f"{contract.work_type_id}@{contract.version}"
    plan = plan_execution(session, ExecutionPlanRequest(
        goal=contract.goal,
        requester_ref=HUMAN,
        work_type_ref=ref,
        risk_class=contract.risk_class,
        requested_capability_refs=[CAP_REF],
        provenance_ref=PROV,
    ))
    work = start_work(session, WorkStartRequest(plan_ref=plan.plan_id, requester_ref=HUMAN, context={"pilot": "ARU-01"}, trace_id=trace_id))
    return plan, work


def _transition(session, work_id, actor, kind, state, *, evidence=None, authority=None, policy=None, signature=None, artifact=None):
    return transition_work(session, WorkTransitionRequest(
        work_id=work_id,
        actor_ref=actor,
        actor_kind=kind,
        to_state=state,
        reason=f"move to {state.value}",
        evidence_refs=evidence or [],
        authority_ref=authority,
        policy_ref=policy,
        signature_ref=signature,
        artifact_ref=artifact,
        provenance_ref=PROV,
    ))


def _seed_human_authority(session, action: str, resource: str, policy_id: str, require_signature: bool):
    add_role(session, RoleAssignmentContract(
        assignment_id=f"urn:anu:role-assignment:{action}",
        subject_ref=HUMAN,
        role_ref="programme-owner",
        context_ref=resource,
        assigned_by="urn:anu:human:rector",
        effective_period=EffectivePeriod(valid_from=NOW),
        provenance_ref=PROV,
    ))
    authority_id = f"urn:anu:authority:{action}"
    add_authority(session, AuthorityGrantContract(
        authority_id=authority_id,
        subject_ref=HUMAN,
        subject_type=SubjectType.HUMAN,
        authority_type=action,
        basis_ref=f"{policy_id}@1.0.0",
        issuer_ref=OWNER,
        scope=AuthorityScope(resource=resource, action=action),
        consequence_class="ACADEMIC_CONSEQUENCE" if require_signature else "ACADEMIC_CHANGE",
        effective_period=EffectivePeriod(valid_from=NOW),
        provenance_ref=PROV,
    ))
    effects = [{"effect": "ALLOW"}]
    if require_signature:
        effects.append({"require": "human-signature"})
    add_policy(session, PolicyContract(
        policy_id=policy_id,
        policy_type="WORK_APPROVAL",
        issuer_ref=OWNER,
        authority_basis_ref=authority_id,
        version="1.0.0",
        scope={"resource": resource, "action": action},
        effects=effects,
        effective_period=EffectivePeriod(valid_from=NOW),
        provenance_ref=PROV,
    ))
    return authority_id, f"{policy_id}@1.0.0"


def _signed_approval(session, work_id: str, authority_id: str, policy_ref: str, artifact_ref: str):
    private = Ed25519PrivateKey.generate()
    pem = private.public_key().public_bytes(serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo).decode("utf-8")
    credential_id = "urn:anu:credential:p4-human"
    add_trust_credential(session, TrustCredentialContract(
        credential_id=credential_id,
        subject_ref=HUMAN,
        public_key_pem=pem,
        fingerprint_sha256=public_key_fingerprint_sha256(pem),
        issuer_ref="urn:anu:trust:aru-01",
        valid_from=NOW,
        provenance_ref=PROV,
    ))
    unsigned = SignatureRecordContract(
        signature_id=f"urn:anu:signature:{work_id.rsplit(':',1)[-1]}",
        signer_identity_ref=HUMAN,
        signer_role_ref="programme-owner",
        authority_ref=authority_id,
        credential_ref=credential_id,
        intent="Approve ARU-01 academic change",
        artifact_ref=artifact_ref,
        artifact_version="1.0.0",
        artifact_hash="sha256:aru01-academic-change",
        work_ref=work_id,
        policy_version=policy_ref,
        signed_at=datetime.now(timezone.utc),
        signature_value="",
        provenance_ref=PROV,
    )
    sig = base64.b64encode(private.sign(signature_signing_bytes(unsigned))).decode("ascii")
    signed = unsigned.model_copy(update={"signature_value": sig})
    add_signature_record(session, signed)
    return signed.signature_id


def test_work_contract_guardrails_block_excess_autonomy():
    with pytest.raises(ValueError):
        _contract("urn:anu:work-type:bad-e1", ExecutionClass.E1, AutonomyLevel.A2)
    with pytest.raises(ValueError):
        WorkContract(
            **{**_contract("urn:anu:work-type:e3", ExecutionClass.E3, AutonomyLevel.A2, approval=True, signature=True, evidence=["evidence"]).model_dump(),
               "decision_points": []}
        )


def test_e1_human_agent_capability_work_replays_without_authority(session):
    _seed_base(session)
    contract = _contract("urn:anu:work-type:e1-synthesis", ExecutionClass.E1, AutonomyLevel.A1)
    graph = _graph(f"{contract.work_type_id}@1.0.0", "urn:anu:work-graph:e1", ExecutionClass.E1)
    plan, work = _plan_start(session, contract, graph, "trace-e1")
    assert "authority_refs" not in type(plan).model_fields
    _transition(session, work.work_id, HUMAN, "HUMAN", WorkState.CONTEXT_READY)
    _transition(session, work.work_id, HUMAN, "HUMAN", WorkState.IN_PROGRESS)
    human = execute_task(session, WorkTaskRequest(work_id=work.work_id, node_id="human-goal", actor_ref=HUMAN, actor_kind="HUMAN", action="set-goal", provenance_ref=PROV))
    cap = execute_task(session, WorkTaskRequest(work_id=work.work_id, node_id="capability", actor_ref="urn:anu:capability-runtime", actor_kind="CAPABILITY", action="knowledge.retrieve", input_payload={"topic": "programme"}, provenance_ref=PROV))
    agent = execute_task(session, WorkTaskRequest(work_id=work.work_id, node_id="agent-analysis", actor_ref=AGENT, actor_kind="AGENT", action="summarize", input_payload=cap.output_payload, provenance_ref=PROV))
    assert human.status == cap.status == agent.status == "SUCCEEDED"
    _transition(session, work.work_id, AGENT, "AGENT", WorkState.EVIDENCE_CAPTURED)
    _transition(session, work.work_id, HUMAN, "HUMAN", WorkState.OUTCOME_OBSERVED)
    _transition(session, work.work_id, HUMAN, "HUMAN", WorkState.CLOSED)
    replay = replay_work(session, work.work_id)
    assert replay.current_state == WorkState.CLOSED
    assert replay.replay_complete is True
    assert {x.actor_kind for x in replay.responsibility_chain if x.actor_kind} >= {"HUMAN", "AGENT", "CAPABILITY"}


def test_e2_agent_cannot_approve_or_publish_canonical(session):
    _seed_base(session)
    authority_id, policy_ref = _seed_human_authority(session, "learning.asset.publish", "urn:anu:learning-asset:lb-01", "urn:anu:policy:learning-asset-publish", False)
    contract = _contract("urn:anu:work-type:e2-learning-asset", ExecutionClass.E2, AutonomyLevel.A2, approval=True, evidence=["revision-evidence"])
    graph = _graph(f"{contract.work_type_id}@1.0.0", "urn:anu:work-graph:e2", ExecutionClass.E2)
    _, work = _plan_start(session, contract, graph, "trace-e2-block")
    _transition(session, work.work_id, HUMAN, "HUMAN", WorkState.CONTEXT_READY)
    _transition(session, work.work_id, HUMAN, "HUMAN", WorkState.IN_PROGRESS)
    blocked = execute_task(session, WorkTaskRequest(work_id=work.work_id, node_id="agent-analysis", actor_ref=AGENT, actor_kind="AGENT", action="publish-canonical", provenance_ref=PROV))
    assert blocked.status == "HANDOVER_REQUIRED"
    assert "AGENT_ACTION_FORBIDDEN" in blocked.reason_codes
    assert replay_work(session, work.work_id).current_state == WorkState.BLOCKED

    # Separate instance proves Human review/approval succeeds with existing authority/policy.
    plan = plan_execution(session, ExecutionPlanRequest(goal=contract.goal, requester_ref=HUMAN, work_type_ref=f"{contract.work_type_id}@1.0.0", risk_class=contract.risk_class, requested_capability_refs=[CAP_REF], provenance_ref=PROV))
    good = start_work(session, WorkStartRequest(plan_ref=plan.plan_id, requester_ref=HUMAN, trace_id="trace-e2-good"))
    _transition(session, good.work_id, HUMAN, "HUMAN", WorkState.CONTEXT_READY)
    _transition(session, good.work_id, HUMAN, "HUMAN", WorkState.IN_PROGRESS)
    agent = execute_task(session, WorkTaskRequest(work_id=good.work_id, node_id="agent-analysis", actor_ref=AGENT, actor_kind="AGENT", action="prepare-revision", provenance_ref=PROV))
    assert agent.status == "SUCCEEDED"
    _transition(session, good.work_id, AGENT, "AGENT", WorkState.PROPOSAL_READY)
    _transition(session, good.work_id, HUMAN, "HUMAN", WorkState.REVIEW_REQUIRED, evidence=["urn:anu:evidence:revision"])
    approved = _transition(session, good.work_id, HUMAN, "HUMAN", WorkState.APPROVED, evidence=["urn:anu:evidence:revision"], authority=authority_id, policy=policy_ref, artifact="urn:anu:learning-asset:lb-01")
    assert approved.status == "APPLIED"
    _transition(session, good.work_id, HUMAN, "HUMAN", WorkState.CLOSED)
    assert replay_work(session, good.work_id).current_state == WorkState.CLOSED


def test_e3_requires_human_authority_policy_and_valid_signature(session):
    _seed_base(session)
    authority_id, policy_ref = _seed_human_authority(session, "academic.programme.approve", "urn:anu:programme:se", "urn:anu:policy:e3-approval", True)
    contract = _contract("urn:anu:work-type:e3-academic-change", ExecutionClass.E3, AutonomyLevel.A2, approval=True, signature=True, evidence=["qualified-evidence"])
    graph = _graph(f"{contract.work_type_id}@1.0.0", "urn:anu:work-graph:e3", ExecutionClass.E3)
    _, work = _plan_start(session, contract, graph, "trace-e3")
    _transition(session, work.work_id, HUMAN, "HUMAN", WorkState.CONTEXT_READY)
    _transition(session, work.work_id, HUMAN, "HUMAN", WorkState.IN_PROGRESS)
    analysis = execute_task(session, WorkTaskRequest(work_id=work.work_id, node_id="agent-analysis", actor_ref=AGENT, actor_kind="AGENT", action="analyze-evidence", provenance_ref=PROV))
    assert analysis.status == "SUCCEEDED"
    _transition(session, work.work_id, AGENT, "AGENT", WorkState.REVIEW_REQUIRED, evidence=["urn:anu:evidence:qualified"])

    # Agent may recommend but cannot perform the consequential approval.
    denied = _transition(session, work.work_id, AGENT, "AGENT", WorkState.APPROVED, evidence=["urn:anu:evidence:qualified"], authority=authority_id, policy=policy_ref, artifact="urn:anu:programme:se")
    assert denied.status == "HANDOVER_REQUIRED"
    assert "HUMAN_APPROVAL_REQUIRED" in denied.reason_codes or "E3_HUMAN_AUTHORITY_REQUIRED" in denied.reason_codes

    # New instance proves Human-authority + signature path end to end.
    plan = plan_execution(session, ExecutionPlanRequest(goal=contract.goal, requester_ref=HUMAN, work_type_ref=f"{contract.work_type_id}@1.0.0", risk_class=contract.risk_class, requested_capability_refs=[CAP_REF], provenance_ref=PROV))
    good = start_work(session, WorkStartRequest(plan_ref=plan.plan_id, requester_ref=HUMAN, trace_id="trace-e3-good"))
    _transition(session, good.work_id, HUMAN, "HUMAN", WorkState.CONTEXT_READY)
    _transition(session, good.work_id, HUMAN, "HUMAN", WorkState.IN_PROGRESS)
    _transition(session, good.work_id, AGENT, "AGENT", WorkState.REVIEW_REQUIRED, evidence=["urn:anu:evidence:qualified"])
    sig_id = _signed_approval(session, good.work_id, authority_id, policy_ref, "urn:anu:programme:se")
    approved = _transition(session, good.work_id, HUMAN, "HUMAN", WorkState.APPROVED, evidence=["urn:anu:evidence:qualified"], authority=authority_id, policy=policy_ref, signature=sig_id, artifact="urn:anu:programme:se")
    assert approved.status == "APPLIED"
    _transition(session, good.work_id, HUMAN, "HUMAN", WorkState.ACTION_AUTHORIZED, evidence=["urn:anu:evidence:qualified"])
    _transition(session, good.work_id, HUMAN, "HUMAN", WorkState.EXECUTING)
    _transition(session, good.work_id, HUMAN, "HUMAN", WorkState.EXECUTED)
    _transition(session, good.work_id, HUMAN, "HUMAN", WorkState.EVIDENCE_CAPTURED)
    _transition(session, good.work_id, HUMAN, "HUMAN", WorkState.OUTCOME_OBSERVED)
    _transition(session, good.work_id, HUMAN, "HUMAN", WorkState.CLOSED)
    replay = replay_work(session, good.work_id)
    assert replay.current_state == WorkState.CLOSED
    assert replay.replay_complete is True
    approvals = [x for x in replay.responsibility_chain if x.state_to == "APPROVED"]
    assert len(approvals) == 1
    assert approvals[0].authority_ref == authority_id
    assert approvals[0].signature_ref == sig_id
