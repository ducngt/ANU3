from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from .api_dependencies import get_session
from .reality_contracts import (
    DataContractContract,
    DataEnvelopeContract,
    DataProjectionRequest,
    IngestedArtifactContract,
    KnowledgeObjectContract,
    MemoryRecordContract,
    SourceAuthorityMappingContract,
    SourceRegistryContract,
)
from .reality_repository import (
    add_data_contract,
    add_data_object,
    add_ingested_artifact,
    add_knowledge_object,
    add_memory_record,
    add_source,
    add_source_authority,
)
from .reality_services import project_data, provenance_graph, search_memory

router = APIRouter(prefix="/v2", tags=["Phase 2 Reality/Data/Memory"])


@router.post("/sources")
def create_source(body: SourceRegistryContract, session: Session = Depends(get_session)):
    add_source(session, body)
    return body


@router.post("/source-authority")
def create_source_authority(body: SourceAuthorityMappingContract, session: Session = Depends(get_session)):
    add_source_authority(session, body)
    return body


@router.post("/data-contracts")
def create_data_contract(body: DataContractContract, session: Session = Depends(get_session)):
    add_data_contract(session, body)
    return body


@router.post("/data")
def create_data(body: DataEnvelopeContract, session: Session = Depends(get_session)):
    add_data_object(session, body)
    return body


@router.get("/data/{data_id}/projection")
def get_data_projection(
    data_id: str,
    effective_at: datetime = Query(...),
    recorded_at: datetime | None = Query(default=None),
    session: Session = Depends(get_session),
):
    return project_data(session, DataProjectionRequest(data_id=data_id, effective_at=effective_at, recorded_at=recorded_at))


@router.post("/knowledge")
def create_knowledge(body: KnowledgeObjectContract, session: Session = Depends(get_session)):
    add_knowledge_object(session, body)
    return body


@router.post("/ingest")
def ingest_artifact(body: IngestedArtifactContract, session: Session = Depends(get_session)):
    add_ingested_artifact(session, body)
    return body


@router.post("/memory")
def create_memory(body: MemoryRecordContract, session: Session = Depends(get_session)):
    add_memory_record(session, body)
    return body


@router.get("/provenance/{provenance_id}/graph")
def get_provenance_graph(provenance_id: str, session: Session = Depends(get_session)):
    return provenance_graph(session, provenance_id)


@router.get("/search")
def search(q: str = Query(...), limit: int = Query(default=20, ge=1, le=100), session: Session = Depends(get_session)):
    return search_memory(session, q, limit)
