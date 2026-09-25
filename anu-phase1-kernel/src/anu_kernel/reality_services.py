from __future__ import annotations

import json
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from .contracts import EffectivePeriod
from .db import ProvenanceRecord
from .errors import DomainValidationError
from .reality_contracts import (
    DataProjectionRequest,
    DataProjectionResult,
    EpistemicType,
    ProvenanceGraphResult,
    SearchResponse,
    SearchResultItem,
    ValidationState,
)
from .reality_models import DataObjectVersion, KnowledgeObjectVersion, UniversityMemoryRecord


def _utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def project_data(session: Session, request: DataProjectionRequest) -> DataProjectionResult:
    rows = session.scalars(
        select(DataObjectVersion).where(DataObjectVersion.data_id == request.data_id)
    ).all()
    candidates: list[DataObjectVersion] = []
    effective_at = _utc(request.effective_at)
    known_at = _utc(request.recorded_at) if request.recorded_at else None
    for row in rows:
        start = _utc(row.effective_from)
        end = _utc(row.effective_to) if row.effective_to else None
        recorded = _utc(row.recorded_time)
        if start <= effective_at and (end is None or effective_at < end):
            if known_at is None or recorded <= known_at:
                candidates.append(row)
    if not candidates:
        raise DomainValidationError("no temporal projection found", ["DATA_PROJECTION_NOT_FOUND"])
    row = max(candidates, key=lambda item: _utc(item.recorded_time))
    return DataProjectionResult(
        data_id=row.data_id,
        version_id=row.version_id,
        semantic_type=row.semantic_type,
        epistemic_type=EpistemicType(row.epistemic_type),
        validation_state=ValidationState(row.validation_state),
        payload=row.payload,
        source_ref=row.source_system_id,
        provenance_ref=row.provenance_ref,
        effective_period=EffectivePeriod(valid_from=row.effective_from, valid_until=row.effective_to),
        recorded_time=row.recorded_time,
    )


def provenance_graph(session: Session, root_ref: str) -> ProvenanceGraphResult:
    visited: set[str] = set()
    nodes: list[dict] = []
    edges: list[dict[str, str]] = []
    warnings: list[str] = []

    def walk(ref: str):
        if ref in visited:
            return
        visited.add(ref)
        row = session.get(ProvenanceRecord, ref)
        if row is None:
            warnings.append(f"missing provenance record: {ref}")
            return
        nodes.append({
            "provenance_id": row.provenance_id,
            "entity_ref": row.entity_ref,
            "actor_ref": row.actor_ref,
            "source_refs": row.source_refs,
            "input_refs": row.input_refs,
            "output_refs": row.output_refs,
            "effective_time": row.effective_time.isoformat(),
            "recorded_time": row.recorded_time.isoformat(),
            "integrity_ref": row.integrity_ref,
        })
        for previous in row.previous_provenance_refs or []:
            edges.append({"from": row.provenance_id, "to": previous, "relation": "DERIVED_FROM"})
            walk(previous)

    walk(root_ref)
    return ProvenanceGraphResult(
        root_provenance_ref=root_ref,
        nodes=nodes,
        edges=edges,
        completeness_status="COMPLETE" if not warnings else "PARTIAL",
        warnings=warnings,
    )


def search_memory(session: Session, query: str, limit: int = 20) -> SearchResponse:
    q = query.strip().lower()
    if not q:
        raise DomainValidationError("search query required", ["SEARCH_QUERY_REQUIRED"])
    items: list[SearchResultItem] = []

    data_rows = session.scalars(select(DataObjectVersion)).all()
    for row in data_rows:
        haystack = " ".join([
            row.data_id,
            row.semantic_type,
            row.source_system_id,
            json.dumps(row.payload, ensure_ascii=False, sort_keys=True),
        ]).lower()
        if q in haystack:
            items.append(SearchResultItem(
                ref=row.version_id,
                object_type="DATA",
                title=row.data_id,
                semantic_type=row.semantic_type,
                epistemic_type=EpistemicType(row.epistemic_type),
                validation_state=ValidationState(row.validation_state),
                source_ref=row.source_system_id,
                snippet=json.dumps(row.payload, ensure_ascii=False)[:240],
            ))

    knowledge_rows = session.scalars(select(KnowledgeObjectVersion)).all()
    for row in knowledge_rows:
        haystack = " ".join([row.knowledge_id, row.title, row.semantic_type, " ".join(row.content_refs or [])]).lower()
        if q in haystack:
            items.append(SearchResultItem(
                ref=f"{row.knowledge_id}@{row.version}",
                object_type="KNOWLEDGE",
                title=row.title,
                semantic_type=row.semantic_type,
                epistemic_type=EpistemicType(row.epistemic_type),
                validation_state=ValidationState(row.validation_state),
                snippet="; ".join(row.content_refs or [])[:240],
            ))

    memory_rows = session.scalars(select(UniversityMemoryRecord)).all()
    for row in memory_rows:
        haystack = " ".join([row.memory_id, row.memory_type, row.subject_ref, row.source_ref, row.summary, " ".join(row.tags or [])]).lower()
        if q in haystack:
            items.append(SearchResultItem(
                ref=row.memory_id,
                object_type="MEMORY_INDEX",
                title=row.summary[:120],
                source_ref=row.source_ref,
                snippet=row.summary[:240],
            ))

    return SearchResponse(query=query, results=items[: max(1, min(limit, 100))])
