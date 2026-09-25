from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from .db import ProvenanceRecord
from .errors import DomainValidationError, RepositoryConflict
from .reality_contracts import (
    DataContractContract,
    DataEnvelopeContract,
    EpistemicType,
    IngestedArtifactContract,
    KnowledgeObjectContract,
    MemoryRecordContract,
    SourceAuthorityMappingContract,
    SourceRegistryContract,
)
from .reality_models import (
    DataContractVersion,
    DataObjectVersion,
    IngestedArtifact,
    KnowledgeObjectVersion,
    SourceAuthorityMapping,
    SourceRegistry,
    UniversityMemoryRecord,
)


def _commit(session: Session, row, resource_type: str, resource_id: str):
    session.add(row)
    try:
        session.commit()
    except IntegrityError as exc:
        session.rollback()
        raise RepositoryConflict(resource_type, resource_id) from exc
    return row


def add_source(session: Session, c: SourceRegistryContract) -> SourceRegistry:
    row = SourceRegistry(
        source_id=c.source_id,
        name=c.name,
        source_kind=c.source_kind,
        owner_ref=c.owner_ref,
        description=c.description,
        synthetic_fixture=c.synthetic_fixture,
        effective_from=c.effective_period.valid_from,
        effective_to=c.effective_period.valid_until,
        lifecycle_state=c.lifecycle_state.value,
        provenance_ref=c.provenance_ref,
    )
    return _commit(session, row, "source_registry", c.source_id)


def add_source_authority(session: Session, c: SourceAuthorityMappingContract) -> SourceAuthorityMapping:
    if session.get(SourceRegistry, c.source_ref) is None:
        raise DomainValidationError("source not found", ["SOURCE_NOT_FOUND"])
    row = SourceAuthorityMapping(
        mapping_id=c.mapping_id,
        source_ref=c.source_ref,
        semantic_type=c.semantic_type,
        authority_scope=c.authority_scope,
        authoritative=c.authoritative,
        effective_from=c.effective_period.valid_from,
        effective_to=c.effective_period.valid_until,
        lifecycle_state=c.lifecycle_state.value,
        provenance_ref=c.provenance_ref,
    )
    return _commit(session, row, "source_authority_mapping", c.mapping_id)


def add_data_contract(session: Session, c: DataContractContract) -> DataContractVersion:
    if c.authoritative_source and session.get(SourceRegistry, c.authoritative_source) is None:
        raise DomainValidationError("authoritative source not found", ["AUTHORITATIVE_SOURCE_NOT_FOUND"])
    row = DataContractVersion(
        contract_id=c.contract_id,
        data_type=c.data_type,
        semantic_definition=c.semantic_definition,
        schema=c.schema_data,
        owner=c.owner,
        authoritative_source=c.authoritative_source,
        producers=c.producers,
        consumers=c.consumers,
        freshness_requirement=c.freshness_requirement,
        quality_rules=c.quality_rules,
        provenance_requirement=c.provenance_requirement,
        access_policy=c.access_policy,
        privacy_class=c.privacy_class,
        integrity_requirement=c.integrity_requirement,
        retention_rule=c.retention_rule,
        version=c.version,
        compatibility_policy=c.compatibility_policy,
        lifecycle_state=c.lifecycle_state.value,
        provenance_ref=c.provenance_ref,
    )
    return _commit(session, row, "data_contract", f"{c.contract_id}@{c.version}")


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


def _contract_row(session: Session, ref: str) -> DataContractVersion | None:
    if "@" not in ref:
        return None
    contract_id, version = ref.rsplit("@", 1)
    return session.scalar(
        select(DataContractVersion).where(
            DataContractVersion.contract_id == contract_id,
            DataContractVersion.version == version,
            DataContractVersion.lifecycle_state == "ACTIVE",
        )
    )


def _authoritative_mapping(session: Session, c: DataEnvelopeContract) -> SourceAuthorityMapping | None:
    candidates = session.scalars(
        select(SourceAuthorityMapping).where(
            SourceAuthorityMapping.source_ref == c.source.system_id,
            SourceAuthorityMapping.semantic_type == c.semantic_type,
            SourceAuthorityMapping.authoritative.is_(True),
            SourceAuthorityMapping.lifecycle_state == "ACTIVE",
        )
    ).all()
    for mapping in candidates:
        if _scope_contains(mapping.authority_scope or {}, c.source.authority_scope or {}):
            return mapping
    return None


def add_data_object(session: Session, c: DataEnvelopeContract) -> DataObjectVersion:
    if session.get(SourceRegistry, c.source.system_id) is None:
        raise DomainValidationError("source not found", ["SOURCE_NOT_FOUND"])
    contract = _contract_row(session, c.contract_ref)
    if contract is None:
        raise DomainValidationError("data contract not found", ["DATA_CONTRACT_NOT_FOUND"])
    if contract.semantic_definition != c.semantic_type:
        raise DomainValidationError("semantic type does not match data contract", ["SEMANTIC_CONTRACT_MISMATCH"])
    if session.get(ProvenanceRecord, c.provenance_ref) is None:
        raise DomainValidationError("provenance not found", ["PROVENANCE_REQUIRED"])

    existing_versions = session.scalars(
        select(DataObjectVersion).where(DataObjectVersion.data_id == c.data_id)
    ).all()
    if existing_versions:
        existing_types = {row.epistemic_type for row in existing_versions}
        if c.epistemic_type.value not in existing_types:
            raise DomainValidationError(
                "epistemic type is immutable for a data object; create a new object with provenance for a governed transition",
                ["EPISTEMIC_TYPE_MUTATION_FORBIDDEN"],
            )
        if not c.supersedes_ref:
            raise DomainValidationError("new version must supersede a prior version", ["SUPERSEDES_REQUIRED"])
        previous = session.get(DataObjectVersion, c.supersedes_ref)
        if previous is None or previous.data_id != c.data_id:
            raise DomainValidationError("invalid supersedes_ref", ["INVALID_SUPERSEDES_REF"])

    official_like = c.epistemic_type in {EpistemicType.FACT, EpistemicType.EVIDENCE, EpistemicType.DECISION}
    if official_like and _authoritative_mapping(session, c) is None:
        raise DomainValidationError(
            "official-like data requires an authoritative source mapping for this semantic type and scope",
            ["SOURCE_AUTHORITY_REQUIRED"],
        )

    row = DataObjectVersion(
        version_id=c.version_id,
        data_id=c.data_id,
        contract_ref=c.contract_ref,
        semantic_type=c.semantic_type,
        schema_version=c.schema_version,
        subject_refs=c.subject_refs,
        source_system_id=c.source.system_id,
        source_record_ref=c.source.record_ref,
        source_authority_scope=c.source.authority_scope,
        owner_ref=c.owner_ref,
        context_ref=c.context_ref,
        effective_from=c.effective_period.valid_from,
        effective_to=c.effective_period.valid_until,
        recorded_time=c.recorded_time,
        epistemic_type=c.epistemic_type.value,
        validation_state=c.validation_state.value,
        provenance_ref=c.provenance_ref,
        integrity_ref=c.integrity_ref,
        access_policy_ref=c.access_policy_ref,
        retention_policy_ref=c.retention_policy_ref,
        lifecycle_state=c.lifecycle_state.value,
        payload=c.payload,
        supersedes_ref=c.supersedes_ref,
        synthetic_output=c.synthetic_output,
    )
    return _commit(session, row, "data_object_version", c.version_id)


def add_knowledge_object(session: Session, c: KnowledgeObjectContract) -> KnowledgeObjectVersion:
    if session.get(ProvenanceRecord, c.provenance_ref) is None:
        raise DomainValidationError("provenance not found", ["PROVENANCE_REQUIRED"])
    row = KnowledgeObjectVersion(
        knowledge_id=c.knowledge_id,
        title=c.title,
        semantic_type=c.semantic_type,
        epistemic_type=c.epistemic_type.value,
        validation_state=c.validation_state.value,
        source_refs=c.source_refs,
        author_owner=c.author_owner,
        context_ref=c.context_ref,
        relations=c.relations,
        effective_from=c.effective_period.valid_from,
        effective_to=c.effective_period.valid_until,
        version=c.version,
        permissions=c.permissions,
        provenance_ref=c.provenance_ref,
        lifecycle_state=c.lifecycle_state.value,
        content_refs=c.content_refs,
        recorded_time=c.recorded_time,
    )
    return _commit(session, row, "knowledge_object", f"{c.knowledge_id}@{c.version}")


def add_ingested_artifact(session: Session, c: IngestedArtifactContract) -> IngestedArtifact:
    if session.get(SourceRegistry, c.source_ref) is None:
        raise DomainValidationError("source not found", ["SOURCE_NOT_FOUND"])
    if session.get(ProvenanceRecord, c.provenance_ref) is None:
        raise DomainValidationError("provenance not found", ["PROVENANCE_REQUIRED"])
    row = IngestedArtifact(
        artifact_id=c.artifact_id,
        content_ref=c.content_ref,
        media_type=c.media_type,
        source_ref=c.source_ref,
        owner_ref=c.owner_ref,
        context_ref=c.context_ref,
        observed_at=c.observed_at,
        recorded_time=c.recorded_time,
        integrity_ref=c.integrity_ref,
        metadata_json=c.metadata,
        provenance_ref=c.provenance_ref,
        lifecycle_state=c.lifecycle_state.value,
    )
    return _commit(session, row, "ingested_artifact", c.artifact_id)


def add_memory_record(session: Session, c: MemoryRecordContract) -> UniversityMemoryRecord:
    if session.get(ProvenanceRecord, c.provenance_ref) is None:
        raise DomainValidationError("provenance not found", ["PROVENANCE_REQUIRED"])
    row = UniversityMemoryRecord(
        memory_id=c.memory_id,
        memory_type=c.memory_type,
        subject_ref=c.subject_ref,
        source_ref=c.source_ref,
        summary=c.summary,
        effective_time=c.effective_time,
        recorded_time=c.recorded_time,
        provenance_ref=c.provenance_ref,
        integrity_ref=c.integrity_ref,
        tags=c.tags,
        lifecycle_state=c.lifecycle_state.value,
    )
    return _commit(session, row, "university_memory_record", c.memory_id)
