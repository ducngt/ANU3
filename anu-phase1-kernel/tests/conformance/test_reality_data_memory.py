from __future__ import annotations

from datetime import datetime

import pytest

from anu_kernel.contracts import ProvenanceRecordContract
from anu_kernel.errors import DomainValidationError
from anu_kernel.repository import add_provenance
from anu_kernel.reality_contracts import (
    DataContractContract,
    DataEnvelopeContract,
    DataProjectionRequest,
    DataSourceRef,
    EffectivePeriod,
    EpistemicType,
    IngestedArtifactContract,
    KnowledgeObjectContract,
    MemoryRecordContract,
    SourceAuthorityMappingContract,
    SourceRegistryContract,
    ValidationState,
)
from anu_kernel.reality_repository import (
    add_data_contract,
    add_data_object,
    add_ingested_artifact,
    add_knowledge_object,
    add_memory_record,
    add_source,
    add_source_authority,
)
from anu_kernel.reality_services import project_data, provenance_graph, search_memory


def dt(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def prov(session, ref: str, entity: str, previous: list[str] | None = None):
    add_provenance(
        session,
        ProvenanceRecordContract(
            provenance_id=ref,
            entity_ref=entity,
            actor_ref="urn:anu:human:data-steward",
            source_refs=["urn:aru:source:synthetic-pilot"],
            input_refs=[],
            output_refs=[entity],
            effective_time=dt("2026-01-01T00:00:00Z"),
            recorded_time=dt("2026-01-01T00:00:00Z"),
            previous_provenance_refs=previous or [],
        ),
    )


def source(session, source_id: str, semantic_type: str, authoritative: bool = True):
    p = f"urn:anu:prov:{source_id.rsplit(':',1)[-1]}"
    prov(session, p, source_id)
    add_source(
        session,
        SourceRegistryContract(
            source_id=source_id,
            name=source_id,
            source_kind="SYNTHETIC_REGISTRY",
            owner_ref="urn:anu:org:aru",
            synthetic_fixture=True,
            effective_period=EffectivePeriod(valid_from=dt("2026-01-01T00:00:00Z")),
            provenance_ref=p,
        ),
    )
    add_source_authority(
        session,
        SourceAuthorityMappingContract(
            mapping_id=f"urn:anu:source-authority:{source_id.rsplit(':',1)[-1]}:{semantic_type.rsplit(':',1)[-1]}",
            source_ref=source_id,
            semantic_type=semantic_type,
            authority_scope={"institution": "urn:anu:org:aru"},
            authoritative=authoritative,
            effective_period=EffectivePeriod(valid_from=dt("2026-01-01T00:00:00Z")),
            provenance_ref=p,
        ),
    )


def data_contract(session, source_id: str, semantic_type: str, contract_id: str = "urn:anu:data-contract:test"):
    add_data_contract(
        session,
        DataContractContract(
            contract_id=contract_id,
            data_type="OPERATIONAL_DATA",
            semantic_definition=semantic_type,
            schema={"type": "object"},
            owner="urn:anu:org:aru",
            authoritative_source=source_id,
            producers=[source_id],
            consumers=["urn:anu:capability:test"],
            quality_rules=[{"rule": "required-id"}],
            version="1.0.0",
        ),
    )
    return f"{contract_id}@1.0.0"


def envelope(
    *,
    data_id: str,
    version_id: str,
    contract_ref: str,
    semantic_type: str,
    source_id: str,
    provenance_ref: str,
    epistemic_type: EpistemicType = EpistemicType.FACT,
    validation_state: ValidationState = ValidationState.APPROVED,
    effective_from: str = "2026-01-01T00:00:00Z",
    effective_to: str | None = None,
    recorded_time: str = "2026-01-02T00:00:00Z",
    supersedes_ref: str | None = None,
    payload: dict | None = None,
    synthetic_output: bool = False,
):
    return DataEnvelopeContract(
        data_id=data_id,
        version_id=version_id,
        contract_ref=contract_ref,
        semantic_type=semantic_type,
        schema_version="1.0.0",
        source=DataSourceRef(
            system_id=source_id,
            record_ref=f"record:{version_id}",
            authority_scope={"institution": "urn:anu:org:aru"},
        ),
        owner_ref="urn:anu:org:aru",
        effective_period=EffectivePeriod(
            valid_from=dt(effective_from),
            valid_until=dt(effective_to) if effective_to else None,
        ),
        recorded_time=dt(recorded_time),
        epistemic_type=epistemic_type,
        validation_state=validation_state,
        provenance_ref=provenance_ref,
        payload=payload or {"value": version_id},
        supersedes_ref=supersedes_ref,
        synthetic_output=synthetic_output,
    )


def test_official_fact_requires_authoritative_source(session):
    semantic = "urn:anu:semantic:enrollment"
    src = "urn:aru:source:ai-inference"
    source(session, src, semantic, authoritative=False)
    cref = data_contract(session, src, semantic)
    prov(session, "urn:anu:prov:data1", "urn:anu:data:enrollment:1")
    with pytest.raises(DomainValidationError) as exc:
        add_data_object(
            session,
            envelope(
                data_id="urn:anu:data:enrollment:1",
                version_id="urn:anu:data-version:enrollment:1:v1",
                contract_ref=cref,
                semantic_type=semantic,
                source_id=src,
                provenance_ref="urn:anu:prov:data1",
            ),
        )
    assert "SOURCE_AUTHORITY_REQUIRED" in exc.value.reason_codes


def test_inference_may_be_stored_without_becoming_fact(session):
    semantic = "urn:anu:semantic:learner-risk"
    src = "urn:aru:source:ai-inference"
    source(session, src, semantic, authoritative=False)
    cref = data_contract(session, src, semantic)
    prov(session, "urn:anu:prov:risk", "urn:anu:data:risk:1")
    row = add_data_object(
        session,
        envelope(
            data_id="urn:anu:data:risk:1",
            version_id="urn:anu:data-version:risk:1:v1",
            contract_ref=cref,
            semantic_type=semantic,
            source_id=src,
            provenance_ref="urn:anu:prov:risk",
            epistemic_type=EpistemicType.INFERENCE,
            validation_state=ValidationState.VALIDATED,
        ),
    )
    assert row.epistemic_type == "INFERENCE"


def test_epistemic_type_cannot_mutate_in_place(session):
    semantic = "urn:anu:semantic:learner-risk"
    src = "urn:aru:source:ai-inference"
    source(session, src, semantic, authoritative=True)
    cref = data_contract(session, src, semantic)
    prov(session, "urn:anu:prov:risk1", "urn:anu:data:risk:1")
    prov(session, "urn:anu:prov:risk2", "urn:anu:data:risk:1", ["urn:anu:prov:risk1"])
    add_data_object(
        session,
        envelope(
            data_id="urn:anu:data:risk:1",
            version_id="urn:anu:data-version:risk:1:v1",
            contract_ref=cref,
            semantic_type=semantic,
            source_id=src,
            provenance_ref="urn:anu:prov:risk1",
            epistemic_type=EpistemicType.INFERENCE,
        ),
    )
    with pytest.raises(DomainValidationError) as exc:
        add_data_object(
            session,
            envelope(
                data_id="urn:anu:data:risk:1",
                version_id="urn:anu:data-version:risk:1:v2",
                contract_ref=cref,
                semantic_type=semantic,
                source_id=src,
                provenance_ref="urn:anu:prov:risk2",
                epistemic_type=EpistemicType.FACT,
                supersedes_ref="urn:anu:data-version:risk:1:v1",
            ),
        )
    assert "EPISTEMIC_TYPE_MUTATION_FORBIDDEN" in exc.value.reason_codes


def test_bitemporal_projection_reconstructs_old_programme(session):
    semantic = "urn:anu:semantic:programme-version"
    src = "urn:aru:source:academic-governance"
    source(session, src, semantic, authoritative=True)
    cref = data_contract(session, src, semantic, "urn:anu:data-contract:programme-version")
    prov(session, "urn:anu:prov:programme-v1", "urn:anu:data:programme:se")
    prov(session, "urn:anu:prov:programme-v2", "urn:anu:data:programme:se", ["urn:anu:prov:programme-v1"])
    add_data_object(
        session,
        envelope(
            data_id="urn:anu:data:programme:se",
            version_id="urn:anu:data-version:programme:se:v1",
            contract_ref=cref,
            semantic_type=semantic,
            source_id=src,
            provenance_ref="urn:anu:prov:programme-v1",
            effective_from="2026-01-01T00:00:00Z",
            effective_to="2026-09-01T00:00:00Z",
            recorded_time="2026-01-02T00:00:00Z",
            payload={"programme_version": "1.0"},
        ),
    )
    add_data_object(
        session,
        envelope(
            data_id="urn:anu:data:programme:se",
            version_id="urn:anu:data-version:programme:se:v2",
            contract_ref=cref,
            semantic_type=semantic,
            source_id=src,
            provenance_ref="urn:anu:prov:programme-v2",
            effective_from="2026-09-01T00:00:00Z",
            recorded_time="2026-09-02T00:00:00Z",
            supersedes_ref="urn:anu:data-version:programme:se:v1",
            payload={"programme_version": "2.0"},
        ),
    )
    old = project_data(
        session,
        DataProjectionRequest(
            data_id="urn:anu:data:programme:se",
            effective_at=dt("2026-06-01T00:00:00Z"),
        ),
    )
    new = project_data(
        session,
        DataProjectionRequest(
            data_id="urn:anu:data:programme:se",
            effective_at=dt("2026-10-01T00:00:00Z"),
        ),
    )
    assert old.payload["programme_version"] == "1.0"
    assert new.payload["programme_version"] == "2.0"


def test_provenance_graph_preserves_derivation_chain(session):
    prov(session, "urn:anu:prov:root", "urn:anu:data:root")
    prov(session, "urn:anu:prov:child", "urn:anu:data:child", ["urn:anu:prov:root"])
    graph = provenance_graph(session, "urn:anu:prov:child")
    assert graph.completeness_status == "COMPLETE"
    assert {n["provenance_id"] for n in graph.nodes} == {"urn:anu:prov:root", "urn:anu:prov:child"}
    assert graph.edges[0]["relation"] == "DERIVED_FROM"


def test_knowledge_object_keeps_epistemic_and_validation_separate(session):
    prov(session, "urn:anu:prov:knowledge", "urn:anu:knowledge:programme-guide")
    row = add_knowledge_object(
        session,
        KnowledgeObjectContract(
            knowledge_id="urn:anu:knowledge:programme-guide",
            title="Programme Guide",
            semantic_type="urn:anu:semantic:programme-guide",
            epistemic_type=EpistemicType.CLAIM,
            validation_state=ValidationState.APPROVED,
            source_refs=["urn:anu:data:programme:se"],
            author_owner="urn:anu:org:aru:academic-affairs",
            effective_period=EffectivePeriod(valid_from=dt("2026-01-01T00:00:00Z")),
            version="1.0.0",
            provenance_ref="urn:anu:prov:knowledge",
            content_refs=["urn:anu:artifact:programme-guide@1.0.0"],
            recorded_time=dt("2026-01-02T00:00:00Z"),
        ),
    )
    assert row.epistemic_type == "CLAIM"
    assert row.validation_state == "APPROVED"


def test_ingestion_and_memory_are_traceable_not_source_of_truth(session):
    src = "urn:aru:source:learning-platform"
    semantic = "urn:anu:semantic:learning-artifact"
    source(session, src, semantic, authoritative=True)
    prov(session, "urn:anu:prov:artifact", "urn:anu:artifact:learning:1")
    prov(session, "urn:anu:prov:memory", "urn:anu:memory:1", ["urn:anu:prov:artifact"])
    artifact = add_ingested_artifact(
        session,
        IngestedArtifactContract(
            artifact_id="urn:anu:artifact:learning:1",
            content_ref="object://aru01/learning/1.pdf",
            media_type="application/pdf",
            source_ref=src,
            owner_ref="urn:anu:human:learner-001",
            observed_at=dt("2026-02-01T00:00:00Z"),
            recorded_time=dt("2026-02-01T00:00:01Z"),
            integrity_ref="sha256:learning-1",
            provenance_ref="urn:anu:prov:artifact",
        ),
    )
    memory = add_memory_record(
        session,
        MemoryRecordContract(
            memory_id="urn:anu:memory:1",
            memory_type="KNOWLEDGE",
            subject_ref="urn:anu:human:learner-001",
            source_ref=artifact.artifact_id,
            summary="Learning artifact observed; memory index points back to source artifact.",
            effective_time=dt("2026-02-01T00:00:00Z"),
            recorded_time=dt("2026-02-01T00:00:02Z"),
            provenance_ref="urn:anu:prov:memory",
            tags=["learning", "artifact"],
        ),
    )
    assert memory.source_ref == artifact.artifact_id


def test_search_returns_data_knowledge_and_memory(session):
    semantic = "urn:anu:semantic:programme-version"
    src = "urn:aru:source:academic-governance"
    source(session, src, semantic, authoritative=True)
    cref = data_contract(session, src, semantic)
    prov(session, "urn:anu:prov:search-data", "urn:anu:data:programme:search")
    prov(session, "urn:anu:prov:search-knowledge", "urn:anu:knowledge:search")
    prov(session, "urn:anu:prov:search-memory", "urn:anu:memory:search")
    add_data_object(
        session,
        envelope(
            data_id="urn:anu:data:programme:search",
            version_id="urn:anu:data-version:programme:search:v1",
            contract_ref=cref,
            semantic_type=semantic,
            source_id=src,
            provenance_ref="urn:anu:prov:search-data",
            payload={"name": "Software Engineering Programme"},
        ),
    )
    add_knowledge_object(
        session,
        KnowledgeObjectContract(
            knowledge_id="urn:anu:knowledge:search",
            title="Software Engineering Programme Knowledge",
            semantic_type="urn:anu:semantic:programme-knowledge",
            epistemic_type=EpistemicType.CLAIM,
            validation_state=ValidationState.VALIDATED,
            source_refs=["urn:anu:data:programme:search"],
            author_owner="urn:anu:org:aru",
            effective_period=EffectivePeriod(valid_from=dt("2026-01-01T00:00:00Z")),
            version="1.0.0",
            provenance_ref="urn:anu:prov:search-knowledge",
            recorded_time=dt("2026-01-02T00:00:00Z"),
        ),
    )
    add_memory_record(
        session,
        MemoryRecordContract(
            memory_id="urn:anu:memory:search",
            memory_type="CHANGE",
            subject_ref="urn:anu:data:programme:search",
            source_ref="urn:anu:data:programme:search",
            summary="Software Engineering Programme changed.",
            effective_time=dt("2026-01-01T00:00:00Z"),
            recorded_time=dt("2026-01-03T00:00:00Z"),
            provenance_ref="urn:anu:prov:search-memory",
        ),
    )
    results = search_memory(session, "Software Engineering")
    assert {item.object_type for item in results.results} == {"DATA", "KNOWLEDGE", "MEMORY_INDEX"}


def test_synthetic_output_cannot_claim_fact_or_evidence():
    with pytest.raises(ValueError):
        envelope(
            data_id="urn:anu:data:synthetic",
            version_id="urn:anu:data-version:synthetic:v1",
            contract_ref="urn:anu:data-contract:test@1.0.0",
            semantic_type="urn:anu:semantic:test",
            source_id="urn:aru:source:ai",
            provenance_ref="urn:anu:prov:synthetic",
            epistemic_type=EpistemicType.EVIDENCE,
            synthetic_output=True,
        )
