from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from .capability_models import CapabilityVersion
from .db import ProvenanceRecord
from .errors import DomainValidationError, RepositoryConflict
from .work_contracts import GovernedWorkGraph, WorkContract
from .work_models import (
    WorkContractVersion,
    WorkGraphVersion,
    WorkExecutionPlanRecord,
    WorkInstanceRecord,
    WorkTaskRecord,
    WorkTransitionRecord,
    HandoverRecord,
)


def _commit(session: Session, row, resource_type: str, resource_id: str):
    session.add(row)
    try:
        session.commit()
    except IntegrityError as exc:
        session.rollback()
        raise RepositoryConflict(resource_type, resource_id) from exc
    return row


def _require_provenance(session: Session, ref: str) -> None:
    if session.get(ProvenanceRecord, ref) is None:
        raise DomainValidationError("provenance not found", ["PROVENANCE_REQUIRED"])


def _split_ref(ref: str) -> tuple[str, str]:
    if "@" not in ref:
        raise DomainValidationError("versioned reference required", ["VERSIONED_REF_REQUIRED"])
    return ref.rsplit("@", 1)


def _require_capability(session: Session, ref: str) -> None:
    cid, version = _split_ref(ref)
    row = session.scalar(select(CapabilityVersion).where(CapabilityVersion.capability_id == cid, CapabilityVersion.version == version))
    if row is None:
        raise DomainValidationError("capability not found", ["CAPABILITY_NOT_FOUND"])


def add_work_contract(session: Session, c: WorkContract) -> WorkContractVersion:
    _require_provenance(session, c.provenance_ref)
    for ref in c.capability_refs:
        _require_capability(session, ref)
    row = WorkContractVersion(
        work_type_id=c.work_type_id,
        name=c.name,
        description=c.description,
        version=c.version,
        owner_ref=c.owner_ref,
        goal=c.goal,
        scope=c.scope,
        execution_class=c.execution_class.value,
        allowed_autonomy=c.allowed_autonomy.value,
        human_participants=[x.model_dump(mode="json") for x in c.human_participants],
        agent_assignments=[x.model_dump(mode="json") for x in c.agent_assignments],
        capability_refs=c.capability_refs,
        data_scope=c.data_scope,
        knowledge_requirements=c.knowledge_requirements,
        decision_points=[x.model_dump(mode="json") for x in c.decision_points],
        approval_points=[x.model_dump(mode="json") for x in c.approval_points],
        signature_policy_ref=c.signature_policy_ref,
        evidence_requirements=c.evidence_requirements,
        risk_class=c.risk_class,
        outcome_definition=c.outcome_definition,
        escalation=c.escalation,
        failure_policy=c.failure_policy,
        trace_policy=c.trace_policy,
        retention=c.retention,
        effective_from=c.effective_period.valid_from,
        effective_to=c.effective_period.valid_until,
        lifecycle_state=c.lifecycle_state.value,
        provenance_ref=c.provenance_ref,
    )
    return _commit(session, row, "work_contract", f"{c.work_type_id}@{c.version}")


def get_work_contract(session: Session, ref: str) -> WorkContractVersion | None:
    if "@" not in ref:
        return None
    wid, version = ref.rsplit("@", 1)
    return session.scalar(select(WorkContractVersion).where(WorkContractVersion.work_type_id == wid, WorkContractVersion.version == version))


def add_work_graph(session: Session, c: GovernedWorkGraph) -> WorkGraphVersion:
    _require_provenance(session, c.provenance_ref)
    if get_work_contract(session, c.work_type_ref) is None:
        raise DomainValidationError("work contract not found", ["WORK_CONTRACT_NOT_FOUND"])
    row = WorkGraphVersion(
        graph_id=c.graph_id,
        work_type_ref=c.work_type_ref,
        version=c.version,
        owner_ref=c.owner_ref,
        entry_node=c.entry_node,
        nodes=[n.model_dump(mode="json") for n in c.nodes],
        effective_from=c.effective_period.valid_from,
        effective_to=c.effective_period.valid_until,
        lifecycle_state=c.lifecycle_state.value,
        provenance_ref=c.provenance_ref,
    )
    return _commit(session, row, "work_graph", f"{c.graph_id}@{c.version}")


def get_work_graph(session: Session, ref: str) -> WorkGraphVersion | None:
    if "@" not in ref:
        return None
    gid, version = ref.rsplit("@", 1)
    return session.scalar(select(WorkGraphVersion).where(WorkGraphVersion.graph_id == gid, WorkGraphVersion.version == version))


def active_graph_for_work_type(session: Session, work_type_ref: str) -> WorkGraphVersion | None:
    return session.scalar(
        select(WorkGraphVersion)
        .where(WorkGraphVersion.work_type_ref == work_type_ref, WorkGraphVersion.lifecycle_state == "ACTIVE")
        .order_by(WorkGraphVersion.recorded_at.desc())
    )


def add_execution_plan(session: Session, row: WorkExecutionPlanRecord) -> WorkExecutionPlanRecord:
    _require_provenance(session, row.provenance_ref)
    return _commit(session, row, "work_execution_plan", row.plan_id)


def add_work_instance(session: Session, row: WorkInstanceRecord) -> WorkInstanceRecord:
    return _commit(session, row, "work_instance", row.work_id)


def get_work_instance(session: Session, work_id: str) -> WorkInstanceRecord | None:
    return session.get(WorkInstanceRecord, work_id)


def add_task_record(session: Session, row: WorkTaskRecord) -> WorkTaskRecord:
    return _commit(session, row, "work_task", row.task_id)


def add_transition_record(session: Session, row: WorkTransitionRecord) -> WorkTransitionRecord:
    return _commit(session, row, "work_transition", row.transition_id)


def add_handover_record(session: Session, row: HandoverRecord) -> HandoverRecord:
    return _commit(session, row, "work_handover", row.handover_id)


def update_work_state(session: Session, work: WorkInstanceRecord, state: str) -> WorkInstanceRecord:
    work.state = state
    work.updated_at = datetime.now(timezone.utc)
    session.add(work)
    session.commit()
    return work


def work_transitions(session: Session, work_id: str) -> list[WorkTransitionRecord]:
    return session.scalars(select(WorkTransitionRecord).where(WorkTransitionRecord.work_id == work_id).order_by(WorkTransitionRecord.recorded_at, WorkTransitionRecord.transition_id)).all()


def work_tasks(session: Session, work_id: str) -> list[WorkTaskRecord]:
    return session.scalars(select(WorkTaskRecord).where(WorkTaskRecord.work_id == work_id).order_by(WorkTaskRecord.recorded_at, WorkTaskRecord.task_id)).all()


def work_handovers(session: Session, work_id: str) -> list[HandoverRecord]:
    return session.scalars(select(HandoverRecord).where(HandoverRecord.work_id == work_id).order_by(HandoverRecord.created_at, HandoverRecord.handover_id)).all()
