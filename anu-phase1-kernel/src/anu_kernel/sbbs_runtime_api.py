from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from .api_dependencies import get_session
from .sbbs_runtime_contracts import (
    AdapterDefinition,
    AssemblyDefinition,
    AssemblyExecutionRequest,
    CompatibilityCheckRequest,
    ConnectionPlanRequest,
    SmartWireExecutionRequest,
    TransformDefinition,
    WriteBoxPromotionRequest,
    WriteBoxProposalRequest,
)
from .sbbs_runtime_repository import add_adapter, add_assembly, add_transform
from .sbbs_runtime_services import (
    evaluate_compatibility,
    execute_assembly,
    execute_wire,
    plan_connection,
    promote_write_box,
    propose_write_box,
)

router = APIRouter(prefix="/v3/runtime", tags=["Phase 3 SBBS Capability Runtime"])


@router.post("/transforms")
def create_transform(body: TransformDefinition, session: Session = Depends(get_session)):
    add_transform(session, body)
    return body


@router.post("/adapters")
def create_adapter(body: AdapterDefinition, session: Session = Depends(get_session)):
    add_adapter(session, body)
    return body


@router.post("/compatibility/check")
def compatibility_check(body: CompatibilityCheckRequest, session: Session = Depends(get_session)):
    return evaluate_compatibility(session, body, persist=True)


@router.post("/connections/plan")
def create_connection_plan(body: ConnectionPlanRequest, session: Session = Depends(get_session)):
    return plan_connection(session, body)


@router.post("/wire/execute")
def wire_execute(body: SmartWireExecutionRequest, session: Session = Depends(get_session)):
    return execute_wire(session, body)


@router.post("/assemblies")
def create_assembly(body: AssemblyDefinition, session: Session = Depends(get_session)):
    add_assembly(session, body)
    return body


@router.post("/assemblies/execute")
def assembly_execute(body: AssemblyExecutionRequest, session: Session = Depends(get_session)):
    return execute_assembly(session, body)


@router.post("/write-box/propose")
def write_box_propose(body: WriteBoxProposalRequest, session: Session = Depends(get_session)):
    return propose_write_box(session, body)


@router.post("/write-box/promote")
def write_box_promote(body: WriteBoxPromotionRequest, session: Session = Depends(get_session)):
    return promote_write_box(session, body.candidate_id, body.actor_ref)
