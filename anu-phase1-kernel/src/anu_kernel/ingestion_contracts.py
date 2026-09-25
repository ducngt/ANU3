from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Literal

from pydantic import Field, model_validator

from .contracts import EffectivePeriod, KernelModel, LifecycleState
from .reality_contracts import EpistemicType, ValidationState


class ExtractionStatus(str, Enum):
    EXTRACTED = "EXTRACTED"
    METADATA_ONLY = "METADATA_ONLY"
    UNSUPPORTED = "UNSUPPORTED"
    FAILED = "FAILED"


class RetrievalMode(str, Enum):
    LEXICAL = "LEXICAL"
    VECTOR = "VECTOR"
    HYBRID = "HYBRID"


class MultimodalArtifactIngestRequest(KernelModel):
    artifact_id: str
    version_id: str
    filename: str
    semantic_type: str
    source_ref: str
    owner_ref: str
    actor_ref: str
    observed_at: datetime
    epistemic_type: EpistemicType = EpistemicType.CLAIM
    validation_state: ValidationState = ValidationState.UNVALIDATED
    authority_scope: dict[str, Any] = Field(default_factory=dict)
    context_ref: str | None = None
    declared_media_type: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    supersedes_ref: str | None = None
    lifecycle_state: LifecycleState = LifecycleState.ACTIVE

    @model_validator(mode="after")
    def official_like_requires_declared_scope(self) -> "MultimodalArtifactIngestRequest":
        if self.epistemic_type in {EpistemicType.FACT, EpistemicType.EVIDENCE, EpistemicType.DECISION}:
            if not self.authority_scope:
                raise ValueError("official-like artifact requires authority_scope")
        return self


class MultimodalArtifactIngestResult(KernelModel):
    artifact_id: str
    version_id: str
    filename: str
    semantic_type: str
    media_type: str
    byte_size: int
    content_hash: str
    storage_ref: str
    source_ref: str
    epistemic_type: EpistemicType
    validation_state: ValidationState
    provenance_ref: str
    extraction_status: ExtractionStatus
    extracted_text: str | None = None
    analyzer_ref: str
    analyzer_version: str
    metadata: dict[str, Any] = Field(default_factory=dict)
    recorded_time: datetime
    lifecycle_state: LifecycleState = LifecycleState.ACTIVE


class ArtifactIntegrityResult(KernelModel):
    version_id: str
    content_hash: str
    observed_hash: str | None = None
    integrity_state: Literal["PASS", "FAIL", "MISSING"]
    storage_ref: str


class RetrievalFilter(KernelModel):
    object_kinds: list[str] = Field(default_factory=list)
    semantic_types: list[str] = Field(default_factory=list)
    epistemic_types: list[EpistemicType] = Field(default_factory=list)
    validation_states: list[ValidationState] = Field(default_factory=list)
    source_refs: list[str] = Field(default_factory=list)


class RetrievalQuery(KernelModel):
    query: str
    mode: RetrievalMode = RetrievalMode.HYBRID
    filters: RetrievalFilter = Field(default_factory=RetrievalFilter)
    limit: int = Field(default=20, ge=1, le=100)
    include_provenance: bool = True


class RetrievalHit(KernelModel):
    ref: str
    object_kind: str
    title: str
    semantic_type: str | None = None
    epistemic_type: EpistemicType | None = None
    validation_state: ValidationState | None = None
    source_refs: list[str] = Field(default_factory=list)
    provenance_ref: str | None = None
    content_hash: str | None = None
    score: float
    lexical_score: float
    vector_score: float
    snippet: str | None = None


class RetrievalResponse(KernelModel):
    query: str
    mode: RetrievalMode
    hits: list[RetrievalHit] = Field(default_factory=list)
    index_version: str = "anu-hash-vector-v1"

class KnowledgeMaterializationRequest(KernelModel):
    knowledge_id: str
    version: str
    title: str
    artifact_version_ref: str
    author_owner: str
    actor_ref: str
    context_ref: str | None = None
    relations: list[dict[str, Any]] = Field(default_factory=list)
    permissions: dict[str, Any] = Field(default_factory=dict)
    effective_period: EffectivePeriod
    lifecycle_state: LifecycleState = LifecycleState.ACTIVE


class KnowledgeMaterializationResult(KernelModel):
    knowledge_ref: str
    artifact_version_ref: str
    epistemic_type: EpistemicType
    validation_state: ValidationState
    provenance_ref: str
    indexed: bool = True
