from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Literal

from pydantic import Field, model_validator

from .contracts import EffectivePeriod, KernelModel, LifecycleState


class EpistemicType(str, Enum):
    FACT = "FACT"
    EVIDENCE = "EVIDENCE"
    CLAIM = "CLAIM"
    INFERENCE = "INFERENCE"
    PREDICTION = "PREDICTION"
    RECOMMENDATION = "RECOMMENDATION"
    DECISION = "DECISION"


class ValidationState(str, Enum):
    UNVALIDATED = "UNVALIDATED"
    VALIDATED = "VALIDATED"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    SUPERSEDED = "SUPERSEDED"


class SourceRegistryContract(KernelModel):
    source_id: str
    name: str
    source_kind: str
    owner_ref: str
    description: str | None = None
    synthetic_fixture: bool = False
    effective_period: EffectivePeriod
    lifecycle_state: LifecycleState = LifecycleState.ACTIVE
    provenance_ref: str | None = None


class SourceAuthorityMappingContract(KernelModel):
    mapping_id: str
    source_ref: str
    semantic_type: str
    authority_scope: dict[str, Any] = Field(default_factory=dict)
    authoritative: bool = True
    effective_period: EffectivePeriod
    lifecycle_state: LifecycleState = LifecycleState.ACTIVE
    provenance_ref: str | None = None


class DataContractContract(KernelModel):
    contract_id: str
    data_type: str
    semantic_definition: str
    schema_data: dict[str, Any] = Field(alias="schema", serialization_alias="schema")
    owner: str
    authoritative_source: str | None = None
    producers: list[str] = Field(default_factory=list)
    consumers: list[str] = Field(default_factory=list)
    freshness_requirement: str | None = None
    quality_rules: list[dict[str, Any]] = Field(default_factory=list)
    provenance_requirement: str = "REQUIRED"
    access_policy: str | None = None
    privacy_class: str = "INTERNAL"
    integrity_requirement: str = "HASH"
    retention_rule: str | None = None
    version: str
    compatibility_policy: str = "BACKWARD_COMPATIBLE_OPTIONAL_ADDITIONS"
    lifecycle_state: LifecycleState = LifecycleState.ACTIVE
    provenance_ref: str | None = None


class DataSourceRef(KernelModel):
    system_id: str
    record_ref: str
    authority_scope: dict[str, Any] = Field(default_factory=dict)


class DataEnvelopeContract(KernelModel):
    data_id: str
    version_id: str
    contract_ref: str
    semantic_type: str
    schema_version: str
    subject_refs: list[str] = Field(default_factory=list)
    source: DataSourceRef
    owner_ref: str
    context_ref: str | None = None
    effective_period: EffectivePeriod
    recorded_time: datetime
    epistemic_type: EpistemicType
    validation_state: ValidationState = ValidationState.UNVALIDATED
    provenance_ref: str
    integrity_ref: str | None = None
    access_policy_ref: str | None = None
    retention_policy_ref: str | None = None
    lifecycle_state: LifecycleState = LifecycleState.ACTIVE
    payload: dict[str, Any]
    supersedes_ref: str | None = None
    synthetic_output: bool = False

    @model_validator(mode="after")
    def synthetic_not_authoritative(self) -> "DataEnvelopeContract":
        if self.synthetic_output and self.epistemic_type in {
            EpistemicType.FACT,
            EpistemicType.EVIDENCE,
            EpistemicType.DECISION,
        }:
            raise ValueError(
                "SYNTHETIC OUTPUT != AUTHORITATIVE EVIDENCE/FACT/DECISION"
            )
        return self


class DataProjectionRequest(KernelModel):
    data_id: str
    effective_at: datetime
    recorded_at: datetime | None = None


class DataProjectionResult(KernelModel):
    data_id: str
    version_id: str
    semantic_type: str
    epistemic_type: EpistemicType
    validation_state: ValidationState
    payload: dict[str, Any]
    source_ref: str
    provenance_ref: str
    effective_period: EffectivePeriod
    recorded_time: datetime


class KnowledgeObjectContract(KernelModel):
    knowledge_id: str
    title: str
    semantic_type: str
    epistemic_type: EpistemicType
    validation_state: ValidationState
    source_refs: list[str] = Field(default_factory=list)
    author_owner: str
    context_ref: str | None = None
    relations: list[dict[str, Any]] = Field(default_factory=list)
    effective_period: EffectivePeriod
    version: str
    permissions: dict[str, Any] = Field(default_factory=dict)
    provenance_ref: str
    lifecycle_state: LifecycleState = LifecycleState.ACTIVE
    content_refs: list[str] = Field(default_factory=list)
    recorded_time: datetime


class IngestedArtifactContract(KernelModel):
    artifact_id: str
    content_ref: str
    media_type: str
    source_ref: str
    owner_ref: str
    context_ref: str | None = None
    observed_at: datetime
    recorded_time: datetime
    integrity_ref: str
    metadata: dict[str, Any] = Field(default_factory=dict)
    provenance_ref: str
    lifecycle_state: LifecycleState = LifecycleState.ACTIVE


class MemoryRecordContract(KernelModel):
    memory_id: str
    memory_type: Literal[
        "DECISION", "ACTION", "OUTCOME", "FAILURE", "CHANGE", "CAPABILITY", "KNOWLEDGE"
    ]
    subject_ref: str
    source_ref: str
    summary: str
    effective_time: datetime
    recorded_time: datetime
    provenance_ref: str
    integrity_ref: str | None = None
    tags: list[str] = Field(default_factory=list)
    lifecycle_state: LifecycleState = LifecycleState.ACTIVE


class SearchResultItem(KernelModel):
    ref: str
    object_type: str
    title: str
    semantic_type: str | None = None
    epistemic_type: EpistemicType | None = None
    validation_state: ValidationState | None = None
    source_ref: str | None = None
    snippet: str | None = None


class SearchResponse(KernelModel):
    query: str
    results: list[SearchResultItem] = Field(default_factory=list)


class ProvenanceGraphResult(KernelModel):
    root_provenance_ref: str
    nodes: list[dict[str, Any]] = Field(default_factory=list)
    edges: list[dict[str, str]] = Field(default_factory=list)
    completeness_status: str = "COMPLETE"
    warnings: list[str] = Field(default_factory=list)
