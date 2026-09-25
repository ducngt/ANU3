from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from .api_dependencies import get_session
from .work_contracts import (
    ExecutionPlanRequest,
    GovernedWorkGraph,
    HandoverRequest,
    WorkContract,
    WorkStartRequest,
    WorkTaskRequest,
    WorkTransitionRequest,
)
from .work_services import (
    execute_task,
    plan_execution,
    register_work_contract,
    register_work_graph,
    replay_work,
    request_handover,
    start_work,
    transition_work,
)

router = APIRouter(prefix="/v4/work", tags=["Phase 4 Governed Human-AI Work Runtime"])


@router.post("/contracts")
def create_work_contract(body: WorkContract, session: Session = Depends(get_session)):
    register_work_contract(session, body)
    return body


@router.post("/graphs")
def create_work_graph(body: GovernedWorkGraph, session: Session = Depends(get_session)):
    register_work_graph(session, body)
    return body


@router.post("/plans")
def create_execution_plan(body: ExecutionPlanRequest, session: Session = Depends(get_session)):
    return plan_execution(session, body)


@router.post("/instances")
def create_work_instance(body: WorkStartRequest, session: Session = Depends(get_session)):
    return start_work(session, body)


@router.post("/tasks/execute")
def run_work_task(body: WorkTaskRequest, session: Session = Depends(get_session)):
    return execute_task(session, body)


@router.post("/transitions")
def apply_work_transition(body: WorkTransitionRequest, session: Session = Depends(get_session)):
    return transition_work(session, body)


@router.post("/handover")
def open_handover(body: HandoverRequest, session: Session = Depends(get_session)):
    return request_handover(session, body)


@router.get("/{work_id}/trace")
def get_work_trace(work_id: str, session: Session = Depends(get_session)):
    return replay_work(session, work_id)
