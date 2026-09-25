from __future__ import annotations

import json
import os
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from .contracts import ProvenanceRecordContract, LifecycleTransitionContract, LifecycleState
from .errors import DomainValidationError
from .ids import urn, uuid7
from .ingestion_contracts import (
    ArtifactIntegrityResult,
    ExtractionStatus,
    MultimodalArtifactIngestRequest,
    MultimodalArtifactIngestResult,
    KnowledgeMaterializationRequest,
    KnowledgeMaterializationResult,
    RetrievalHit,
    RetrievalMode,
    RetrievalQuery,
    RetrievalResponse,
)
from .ingestion_models import ArtifactObjectVersion, RetrievalProjection
from .ingestion_repository import add_artifact_version, upsert_retrieval_projection, validate_ingest_request
from .media_extractors import extract
from .object_store import FileSystemObjectStore
from .repository import add_provenance, add_lifecycle_transition
from .retrieval import INDEX_VERSION, cosine, lexical_score, vectorize
from .reality_contracts import EpistemicType, MemoryRecordContract, ValidationState, KnowledgeObjectContract
from .reality_repository import add_memory_record, add_knowledge_object
from .reality_models import UniversityMemoryRecord


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _artifact_searchable_text(request: MultimodalArtifactIngestRequest, extracted_text: str | None, metadata: dict) -> str:
    values = [
        request.artifact_id,
        request.filename,
        request.semantic_type,
        request.source_ref,
        extracted_text or "",
        json.dumps(metadata, ensure_ascii=False, sort_keys=True),
    ]
    for key in ("title", "caption", "transcript", "description", "keywords"):
        value = request.metadata.get(key)
        if value:
            values.append(value if isinstance(value, str) else json.dumps(value, ensure_ascii=False))
    return "\n".join(values)


def ingest_bytes(
    session: Session,
    request: MultimodalArtifactIngestRequest,
    data: bytes,
    *,
    store: FileSystemObjectStore | None = None,
) -> MultimodalArtifactIngestResult:
    if not data:
        raise DomainValidationError("empty artifact is not ingestible", ["EMPTY_ARTIFACT"])
    max_bytes = int(os.getenv("ANU_MAX_INGEST_BYTES", str(50 * 1024 * 1024)))
    if len(data) > max_bytes:
        raise DomainValidationError("artifact exceeds configured ingest size limit", ["ARTIFACT_TOO_LARGE"])
    validate_ingest_request(session, request)
    object_store = store or FileSystemObjectStore()
    storage_ref, content_hash, stored_path = object_store.put(data)
    analysis = extract(request.filename, request.declared_media_type, data, stored_path=stored_path)
    recorded = _now()

    prov_id = urn("provenance", uuid7())
    previous_prov: list[str] = []
    if request.supersedes_ref:
        previous = session.get(ArtifactObjectVersion, request.supersedes_ref)
        if previous is not None:
            previous_prov.append(previous.provenance_ref)
    add_provenance(
        session,
        ProvenanceRecordContract(
            provenance_id=prov_id,
            entity_ref=request.version_id,
            actor_ref=request.actor_ref,
            source_refs=[request.source_ref],
            input_refs=[request.supersedes_ref] if request.supersedes_ref else [],
            output_refs=[request.version_id, storage_ref],
            effective_time=request.observed_at,
            recorded_time=recorded,
            transformation_ref=analysis.analyzer_ref,
            previous_provenance_refs=previous_prov,
            integrity_ref=f"sha256:{content_hash}",
        ),
    )

    merged_metadata = dict(request.metadata)
    merged_metadata.update(analysis.metadata)
    row = ArtifactObjectVersion(
        version_id=request.version_id,
        artifact_id=request.artifact_id,
        filename=request.filename,
        semantic_type=request.semantic_type,
        media_type=analysis.media_type,
        byte_size=len(data),
        content_hash=content_hash,
        storage_ref=storage_ref,
        source_ref=request.source_ref,
        owner_ref=request.owner_ref,
        context_ref=request.context_ref,
        observed_at=request.observed_at,
        recorded_time=recorded,
        epistemic_type=request.epistemic_type.value,
        validation_state=request.validation_state.value,
        provenance_ref=prov_id,
        lifecycle_state=request.lifecycle_state.value,
        supersedes_ref=request.supersedes_ref,
        extraction_status=analysis.status.value,
        extracted_text=analysis.text,
        analyzer_ref=analysis.analyzer_ref,
        analyzer_version=analysis.analyzer_version,
        metadata_json=merged_metadata,
    )
    add_artifact_version(session, row)

    if request.supersedes_ref:
        previous = session.get(ArtifactObjectVersion, request.supersedes_ref)
        if previous is not None and previous.lifecycle_state == LifecycleState.ACTIVE.value:
            previous.lifecycle_state = LifecycleState.SUPERSEDED.value
            prior_projection = session.scalar(
                select(RetrievalProjection).where(
                    RetrievalProjection.object_ref == previous.version_id,
                    RetrievalProjection.index_version == INDEX_VERSION,
                )
            )
            if prior_projection is not None:
                prior_projection.lifecycle_state = LifecycleState.SUPERSEDED.value
            session.commit()
            add_lifecycle_transition(
                session,
                LifecycleTransitionContract(
                    transition_id=urn("lifecycle-transition", uuid7()),
                    object_ref=previous.version_id,
                    from_state=LifecycleState.ACTIVE,
                    to_state=LifecycleState.SUPERSEDED,
                    effective_time=request.observed_at,
                    recorded_time=recorded,
                    reason="Superseded by a new immutable artifact version",
                    actor_ref=request.actor_ref,
                    superseded_by_ref=request.version_id,
                    provenance_ref=prov_id,
                ),
            )

    searchable = _artifact_searchable_text(request, analysis.text, merged_metadata)
    projection = RetrievalProjection(
        projection_id=urn("retrieval-projection", uuid7()),
        object_ref=request.version_id,
        object_kind="ARTIFACT",
        title=request.metadata.get("title") or request.filename,
        semantic_type=request.semantic_type,
        epistemic_type=request.epistemic_type.value,
        validation_state=request.validation_state.value,
        source_refs=[request.source_ref],
        provenance_ref=prov_id,
        content_hash=content_hash,
        searchable_text=searchable,
        vector_json=vectorize(searchable),
        index_version=INDEX_VERSION,
        lifecycle_state=request.lifecycle_state.value,
        recorded_at=recorded,
    )
    upsert_retrieval_projection(session, projection)

    add_memory_record(
        session,
        MemoryRecordContract(
            memory_id=urn("memory", uuid7()),
            memory_type="KNOWLEDGE",
            subject_ref=request.artifact_id,
            source_ref=request.version_id,
            summary=f"Ingested {request.filename} ({analysis.media_type}) as immutable content {content_hash[:12]}",
            effective_time=request.observed_at,
            recorded_time=recorded,
            provenance_ref=prov_id,
            integrity_ref=f"sha256:{content_hash}",
            tags=["INGESTION", request.semantic_type, request.epistemic_type.value],
        ),
    )

    return MultimodalArtifactIngestResult(
        artifact_id=request.artifact_id,
        version_id=request.version_id,
        filename=request.filename,
        semantic_type=request.semantic_type,
        media_type=analysis.media_type,
        byte_size=len(data),
        content_hash=content_hash,
        storage_ref=storage_ref,
        source_ref=request.source_ref,
        epistemic_type=request.epistemic_type,
        validation_state=request.validation_state,
        provenance_ref=prov_id,
        extraction_status=analysis.status,
        extracted_text=analysis.text,
        analyzer_ref=analysis.analyzer_ref,
        analyzer_version=analysis.analyzer_version,
        metadata=merged_metadata,
        recorded_time=recorded,
        lifecycle_state=request.lifecycle_state,
    )



def materialize_knowledge_object(
    session: Session,
    request: KnowledgeMaterializationRequest,
) -> KnowledgeMaterializationResult:
    artifact = session.get(ArtifactObjectVersion, request.artifact_version_ref)
    if artifact is None:
        raise DomainValidationError("artifact version not found", ["ARTIFACT_VERSION_NOT_FOUND"])
    if artifact.extraction_status not in {ExtractionStatus.EXTRACTED.value, ExtractionStatus.METADATA_ONLY.value}:
        raise DomainValidationError("artifact extraction is not usable for knowledge materialization", ["ARTIFACT_EXTRACTION_NOT_USABLE"])
    recorded = _now()
    prov_id = urn("provenance", uuid7())
    knowledge_ref = f"{request.knowledge_id}@{request.version}"
    add_provenance(
        session,
        ProvenanceRecordContract(
            provenance_id=prov_id,
            entity_ref=knowledge_ref,
            actor_ref=request.actor_ref,
            source_refs=[artifact.source_ref, artifact.version_id],
            input_refs=[artifact.version_id, artifact.storage_ref],
            output_refs=[knowledge_ref],
            effective_time=request.effective_period.valid_from,
            recorded_time=recorded,
            transformation_ref=artifact.analyzer_ref,
            previous_provenance_refs=[artifact.provenance_ref],
            integrity_ref=f"sha256:{artifact.content_hash}",
        ),
    )
    contract = KnowledgeObjectContract(
        knowledge_id=request.knowledge_id,
        title=request.title,
        semantic_type=artifact.semantic_type,
        epistemic_type=EpistemicType(artifact.epistemic_type),
        validation_state=ValidationState(artifact.validation_state),
        source_refs=[artifact.source_ref, artifact.version_id],
        author_owner=request.author_owner,
        context_ref=request.context_ref,
        relations=request.relations,
        effective_period=request.effective_period,
        version=request.version,
        permissions=request.permissions,
        provenance_ref=prov_id,
        lifecycle_state=request.lifecycle_state,
        content_refs=[artifact.storage_ref],
        recorded_time=recorded,
    )
    add_knowledge_object(session, contract)
    searchable = "\n".join([
        request.knowledge_id,
        request.title,
        artifact.semantic_type,
        artifact.extracted_text or "",
        json.dumps(artifact.metadata_json or {}, ensure_ascii=False, sort_keys=True),
    ])
    upsert_retrieval_projection(
        session,
        RetrievalProjection(
            projection_id=urn("retrieval-projection", uuid7()),
            object_ref=knowledge_ref,
            object_kind="KNOWLEDGE",
            title=request.title,
            semantic_type=artifact.semantic_type,
            epistemic_type=artifact.epistemic_type,
            validation_state=artifact.validation_state,
            source_refs=[artifact.source_ref, artifact.version_id],
            provenance_ref=prov_id,
            content_hash=artifact.content_hash,
            searchable_text=searchable,
            vector_json=vectorize(searchable),
            index_version=INDEX_VERSION,
            lifecycle_state=request.lifecycle_state.value,
            recorded_at=recorded,
        ),
    )
    add_memory_record(
        session,
        MemoryRecordContract(
            memory_id=urn("memory", uuid7()),
            memory_type="KNOWLEDGE",
            subject_ref=request.knowledge_id,
            source_ref=artifact.version_id,
            summary=f"Knowledge materialized from {artifact.filename}; epistemic type preserved as {artifact.epistemic_type}",
            effective_time=request.effective_period.valid_from,
            recorded_time=recorded,
            provenance_ref=prov_id,
            integrity_ref=f"sha256:{artifact.content_hash}",
            tags=["KNOWLEDGE_MATERIALIZATION", artifact.semantic_type, artifact.epistemic_type],
        ),
    )
    return KnowledgeMaterializationResult(
        knowledge_ref=knowledge_ref,
        artifact_version_ref=artifact.version_id,
        epistemic_type=EpistemicType(artifact.epistemic_type),
        validation_state=ValidationState(artifact.validation_state),
        provenance_ref=prov_id,
        indexed=True,
    )


def verify_artifact_integrity(
    session: Session,
    version_id: str,
    *,
    store: FileSystemObjectStore | None = None,
) -> ArtifactIntegrityResult:
    row = session.get(ArtifactObjectVersion, version_id)
    if row is None:
        raise DomainValidationError("artifact version not found", ["ARTIFACT_VERSION_NOT_FOUND"])
    object_store = store or FileSystemObjectStore()
    state, observed = object_store.verify(row.storage_ref, row.content_hash)
    return ArtifactIntegrityResult(
        version_id=version_id,
        content_hash=row.content_hash,
        observed_hash=observed,
        integrity_state=state,
        storage_ref=row.storage_ref,
    )


def _matches_filters(row: RetrievalProjection, query: RetrievalQuery) -> bool:
    f = query.filters
    if f.object_kinds and row.object_kind not in f.object_kinds:
        return False
    if f.semantic_types and row.semantic_type not in f.semantic_types:
        return False
    if f.epistemic_types and row.epistemic_type not in {x.value for x in f.epistemic_types}:
        return False
    if f.validation_states and row.validation_state not in {x.value for x in f.validation_states}:
        return False
    if f.source_refs and not set(f.source_refs).intersection(row.source_refs or []):
        return False
    return True


def retrieve(session: Session, query: RetrievalQuery) -> RetrievalResponse:
    if not query.query.strip():
        raise DomainValidationError("retrieval query required", ["SEARCH_QUERY_REQUIRED"])
    qvec = vectorize(query.query)
    scored: list[RetrievalHit] = []
    rows = session.scalars(
        select(RetrievalProjection).where(RetrievalProjection.lifecycle_state == "ACTIVE")
    ).all()
    for row in rows:
        if not _matches_filters(row, query):
            continue
        lscore = lexical_score(query.query, row.searchable_text or "")
        vscore = cosine(qvec, row.vector_json or [])
        if query.mode == RetrievalMode.LEXICAL:
            score = lscore
        elif query.mode == RetrievalMode.VECTOR:
            score = vscore
        else:
            score = (0.45 * lscore) + (0.55 * vscore)
        if score <= 0:
            continue
        snippet = (row.searchable_text or "").replace("\n", " ")[:320]
        scored.append(
            RetrievalHit(
                ref=row.object_ref,
                object_kind=row.object_kind,
                title=row.title,
                semantic_type=row.semantic_type,
                epistemic_type=EpistemicType(row.epistemic_type) if row.epistemic_type else None,
                validation_state=ValidationState(row.validation_state) if row.validation_state else None,
                source_refs=row.source_refs or [],
                provenance_ref=row.provenance_ref if query.include_provenance else None,
                content_hash=row.content_hash,
                score=round(score, 6),
                lexical_score=round(lscore, 6),
                vector_score=round(vscore, 6),
                snippet=snippet,
            )
        )
    scored.sort(key=lambda item: (-item.score, item.ref))
    return RetrievalResponse(query=query.query, mode=query.mode, hits=scored[: query.limit], index_version=INDEX_VERSION)


def rebuild_memory_projection(session: Session) -> dict[str, int]:
    """Materialize searchable memory projection without making Memory a source of truth."""
    memory_rows = session.scalars(select(UniversityMemoryRecord)).all()
    count = 0
    for memory in memory_rows:
        searchable = "\n".join([
            memory.memory_id,
            memory.memory_type,
            memory.subject_ref,
            memory.source_ref,
            memory.summary,
            " ".join(memory.tags or []),
        ])
        row = RetrievalProjection(
            projection_id=f"urn:anu:retrieval-projection:memory:{memory.memory_id}",
            object_ref=memory.memory_id,
            object_kind="MEMORY_INDEX",
            title=memory.summary[:160],
            semantic_type=None,
            epistemic_type=None,
            validation_state=None,
            source_refs=[memory.source_ref],
            provenance_ref=memory.provenance_ref,
            content_hash=(memory.integrity_ref or "").removeprefix("sha256:") or None,
            searchable_text=searchable,
            vector_json=vectorize(searchable),
            index_version=INDEX_VERSION,
            lifecycle_state=memory.lifecycle_state,
            recorded_at=memory.recorded_time,
        )
        upsert_retrieval_projection(session, row)
        count += 1
    return {"indexed_memory_records": count}
