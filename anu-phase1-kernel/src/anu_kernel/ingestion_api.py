from __future__ import annotations

import json
import os
from datetime import datetime

from fastapi import APIRouter, Depends, File, Form, UploadFile
from sqlalchemy.orm import Session

from .api_dependencies import get_session
from .ingestion_contracts import MultimodalArtifactIngestRequest, RetrievalQuery, KnowledgeMaterializationRequest
from .ingestion_services import ingest_bytes, rebuild_memory_projection, retrieve, verify_artifact_integrity, materialize_knowledge_object
from .errors import DomainValidationError

router = APIRouter(prefix="/v2", tags=["Phase 2 Multimodal/Memory/Retrieval"])


@router.post("/artifacts/ingest")
async def ingest_multimodal_artifact(
    file: UploadFile = File(...),
    artifact_id: str = Form(...),
    version_id: str = Form(...),
    semantic_type: str = Form(...),
    source_ref: str = Form(...),
    owner_ref: str = Form(...),
    actor_ref: str = Form(...),
    observed_at: datetime = Form(...),
    epistemic_type: str = Form("CLAIM"),
    validation_state: str = Form("UNVALIDATED"),
    authority_scope_json: str = Form("{}"),
    context_ref: str | None = Form(default=None),
    metadata_json: str = Form("{}"),
    supersedes_ref: str | None = Form(default=None),
    session: Session = Depends(get_session),
):
    max_bytes = int(os.getenv("ANU_MAX_INGEST_BYTES", str(50 * 1024 * 1024)))
    chunks: list[bytes] = []
    total = 0
    while True:
        chunk = await file.read(min(1024 * 1024, max_bytes + 1))
        if not chunk:
            break
        total += len(chunk)
        if total > max_bytes:
            raise DomainValidationError("artifact exceeds configured ingest size limit", ["ARTIFACT_TOO_LARGE"])
        chunks.append(chunk)
    payload = b"".join(chunks)
    try:
        authority_scope = json.loads(authority_scope_json)
        metadata = json.loads(metadata_json)
    except json.JSONDecodeError as exc:
        raise DomainValidationError("invalid JSON form metadata", ["INVALID_INGEST_METADATA_JSON"]) from exc
    body = MultimodalArtifactIngestRequest(
        artifact_id=artifact_id,
        version_id=version_id,
        filename=file.filename or "artifact.bin",
        semantic_type=semantic_type,
        source_ref=source_ref,
        owner_ref=owner_ref,
        actor_ref=actor_ref,
        observed_at=observed_at,
        epistemic_type=epistemic_type,
        validation_state=validation_state,
        authority_scope=authority_scope,
        context_ref=context_ref,
        declared_media_type=file.content_type,
        metadata=metadata,
        supersedes_ref=supersedes_ref,
    )
    return ingest_bytes(session, body, payload)


@router.post("/knowledge/materialize")
def knowledge_materialize(body: KnowledgeMaterializationRequest, session: Session = Depends(get_session)):
    return materialize_knowledge_object(session, body)


@router.get("/artifacts/{version_id}/integrity")
def artifact_integrity(version_id: str, session: Session = Depends(get_session)):
    return verify_artifact_integrity(session, version_id)


@router.post("/retrieval/search")
def retrieval_search(body: RetrievalQuery, session: Session = Depends(get_session)):
    return retrieve(session, body)


@router.post("/memory/reindex")
def memory_reindex(session: Session = Depends(get_session)):
    return rebuild_memory_projection(session)
