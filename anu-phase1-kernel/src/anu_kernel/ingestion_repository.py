from __future__ import annotations

from datetime import timezone

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from .db import ProvenanceRecord
from .errors import DomainValidationError, RepositoryConflict
from .ingestion_contracts import MultimodalArtifactIngestRequest
from .ingestion_models import ArtifactObjectVersion, RetrievalProjection
from .reality_contracts import EpistemicType
from .reality_models import SourceAuthorityMapping, SourceRegistry


def _commit(session: Session, row, resource_type: str, resource_id: str):
    session.add(row)
    try:
        session.commit()
    except IntegrityError as exc:
        session.rollback()
        raise RepositoryConflict(resource_type, resource_id) from exc
    return row


def _scope_contains(parent: dict, child: dict) -> bool:
    for key, child_value in child.items():
        if child_value is None:
            continue
        parent_value = parent.get(key)
        if parent_value in (None, "*", ["*"]):
            continue
        if isinstance(parent_value, list):
            if child_value not in parent_value:
                return False
        elif parent_value != child_value:
            return False
    return True


def source_is_authoritative(session: Session, source_ref: str, semantic_type: str, authority_scope: dict, observed_at=None) -> bool:
    rows = session.scalars(
        select(SourceAuthorityMapping).where(
            SourceAuthorityMapping.source_ref == source_ref,
            SourceAuthorityMapping.semantic_type == semantic_type,
            SourceAuthorityMapping.authoritative.is_(True),
            SourceAuthorityMapping.lifecycle_state == "ACTIVE",
        )
    ).all()
    for row in rows:
        if observed_at is not None:
            at = observed_at
            if at.tzinfo is None:
                at = at.replace(tzinfo=timezone.utc)
            start = row.effective_from
            end = row.effective_to
            if start.tzinfo is None:
                start = start.replace(tzinfo=timezone.utc)
            if end is not None and end.tzinfo is None:
                end = end.replace(tzinfo=timezone.utc)
            if at < start or (end is not None and at >= end):
                continue
        if _scope_contains(row.authority_scope or {}, authority_scope or {}):
            return True
    return False


def validate_ingest_request(session: Session, request: MultimodalArtifactIngestRequest) -> None:
    source = session.get(SourceRegistry, request.source_ref)
    if source is None:
        raise DomainValidationError("source not found", ["SOURCE_NOT_FOUND"])
    observed = request.observed_at
    if observed.tzinfo is None:
        observed = observed.replace(tzinfo=timezone.utc)
    source_from = source.effective_from
    source_to = source.effective_to
    if source_from.tzinfo is None:
        source_from = source_from.replace(tzinfo=timezone.utc)
    if source_to is not None and source_to.tzinfo is None:
        source_to = source_to.replace(tzinfo=timezone.utc)
    if source.lifecycle_state != "ACTIVE" or observed < source_from or (source_to is not None and observed >= source_to):
        raise DomainValidationError("source is not active/effective at observation time", ["SOURCE_STALE_OR_INACTIVE"])

    official_like = request.epistemic_type in {
        EpistemicType.FACT,
        EpistemicType.EVIDENCE,
        EpistemicType.DECISION,
    }
    if official_like and not source_is_authoritative(
        session, request.source_ref, request.semantic_type, request.authority_scope, request.observed_at
    ):
        raise DomainValidationError(
            "official-like artifact requires an authoritative source mapping",
            ["SOURCE_AUTHORITY_REQUIRED"],
        )

    previous = session.scalars(
        select(ArtifactObjectVersion).where(ArtifactObjectVersion.artifact_id == request.artifact_id)
    ).all()
    if previous:
        if not request.supersedes_ref:
            raise DomainValidationError("new artifact version must supersede a prior version", ["SUPERSEDES_REQUIRED"])
        superseded = session.get(ArtifactObjectVersion, request.supersedes_ref)
        if superseded is None or superseded.artifact_id != request.artifact_id:
            raise DomainValidationError("invalid artifact supersedes_ref", ["INVALID_SUPERSEDES_REF"])
        existing_types = {row.epistemic_type for row in previous}
        if request.epistemic_type.value not in existing_types:
            raise DomainValidationError(
                "epistemic type cannot mutate in-place across artifact versions; create a governed derived object",
                ["EPISTEMIC_TYPE_MUTATION_FORBIDDEN"],
            )


def add_artifact_version(session: Session, row: ArtifactObjectVersion) -> ArtifactObjectVersion:
    if session.get(ProvenanceRecord, row.provenance_ref) is None:
        raise DomainValidationError("provenance not found", ["PROVENANCE_REQUIRED"])
    return _commit(session, row, "artifact_object_version", row.version_id)


def upsert_retrieval_projection(session: Session, row: RetrievalProjection) -> RetrievalProjection:
    existing = session.scalar(
        select(RetrievalProjection).where(
            RetrievalProjection.object_ref == row.object_ref,
            RetrievalProjection.index_version == row.index_version,
        )
    )
    if existing is not None:
        existing.title = row.title
        existing.semantic_type = row.semantic_type
        existing.epistemic_type = row.epistemic_type
        existing.validation_state = row.validation_state
        existing.source_refs = row.source_refs
        existing.provenance_ref = row.provenance_ref
        existing.content_hash = row.content_hash
        existing.searchable_text = row.searchable_text
        existing.vector_json = row.vector_json
        existing.lifecycle_state = row.lifecycle_state
        session.commit()
        return existing
    return _commit(session, row, "retrieval_projection", row.projection_id)
