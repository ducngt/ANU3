from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pytest

from anu_kernel.contracts import EffectivePeriod, ProvenanceRecordContract
from anu_kernel.errors import DomainValidationError
from anu_kernel.ingestion_contracts import (
    MultimodalArtifactIngestRequest,
    RetrievalMode,
    RetrievalQuery,
)
from anu_kernel.ingestion_models import ArtifactObjectVersion
from anu_kernel.ingestion_services import ingest_bytes, rebuild_memory_projection, retrieve, verify_artifact_integrity
from anu_kernel.object_store import FileSystemObjectStore
from anu_kernel.reality_contracts import EpistemicType, SourceAuthorityMappingContract, SourceRegistryContract, ValidationState
from anu_kernel.reality_repository import add_source, add_source_authority
from anu_kernel.repository import add_provenance

ROOT = Path(__file__).resolve().parents[2]
FIXTURES = ROOT / "fixtures" / "aru-01" / "multimodal"


def now() -> datetime:
    return datetime(2026, 9, 25, 0, 0, tzinfo=timezone.utc)


def register_source(session, *, authoritative: bool = True, semantic_type: str = "urn:anu:semantic:learning-artifact") -> str:
    source_id = "urn:aru:source:learning-platform"
    prov = "urn:anu:prov:source:learning-platform"
    add_provenance(
        session,
        ProvenanceRecordContract(
            provenance_id=prov,
            entity_ref=source_id,
            actor_ref="urn:anu:human:data-steward",
            source_refs=["urn:aru:fixture:p2-t02"],
            input_refs=[],
            output_refs=[source_id],
            effective_time=now(),
            recorded_time=now(),
        ),
    )
    add_source(
        session,
        SourceRegistryContract(
            source_id=source_id,
            name="ARU Learning Platform",
            source_kind="SYNTHETIC_REGISTRY",
            owner_ref="urn:anu:org:aru",
            synthetic_fixture=True,
            effective_period=EffectivePeriod(valid_from=now()),
            provenance_ref=prov,
        ),
    )
    add_source_authority(
        session,
        SourceAuthorityMappingContract(
            mapping_id="urn:anu:source-authority:learning-artifact",
            source_ref=source_id,
            semantic_type=semantic_type,
            authority_scope={"institution": "urn:anu:org:aru"},
            authoritative=authoritative,
            effective_period=EffectivePeriod(valid_from=now()),
            provenance_ref=prov,
        ),
    )
    return source_id


def request_for(filename: str, source: str, *, version: str, epistemic=EpistemicType.CLAIM, supersedes=None):
    return MultimodalArtifactIngestRequest(
        artifact_id="urn:anu:artifact:aru-p2-t02",
        version_id=version,
        filename=filename,
        semantic_type="urn:anu:semantic:learning-artifact",
        source_ref=source,
        owner_ref="urn:anu:org:aru",
        actor_ref="urn:anu:human:data-steward",
        observed_at=now(),
        epistemic_type=epistemic,
        validation_state=ValidationState.APPROVED if epistemic == EpistemicType.FACT else ValidationState.VALIDATED,
        authority_scope={"institution": "urn:anu:org:aru"} if epistemic == EpistemicType.FACT else {},
        metadata={"title": "ARU-01 multimodal pilot"},
        supersedes_ref=supersedes,
    )


def test_pdf_docx_image_audio_video_are_ingested_as_immutable_objects(session, tmp_path):
    source = register_source(session)
    store = FileSystemObjectStore(tmp_path / "objects")
    cases = [
        ("programme-handbook.pdf", "application/pdf", "EXTRACTED"),
        ("course-spec.docx", "application/vnd.openxmlformats-officedocument.wordprocessingml.document", "EXTRACTED"),
        ("learning-diagram.png", "image/png", "METADATA_ONLY"),
        ("lecture-note.wav", "audio/x-wav", "METADATA_ONLY"),
        ("pilot-video.mp4", "video/mp4", "METADATA_ONLY"),
    ]
    previous = None
    for idx, (name, media_type, status) in enumerate(cases, start=1):
        req = request_for(name, source, version=f"urn:anu:artifact-version:multimodal:{idx}", supersedes=previous)
        req.declared_media_type = media_type
        result = ingest_bytes(session, req, (FIXTURES / name).read_bytes(), store=store)
        assert result.extraction_status.value == status
        assert result.content_hash
        assert store.path_for_ref(result.storage_ref).exists()
        previous = result.version_id
    assert session.query(ArtifactObjectVersion).count() == 5


def test_pdf_and_docx_text_becomes_retrievable_with_source_and_provenance(session, tmp_path):
    source = register_source(session)
    store = FileSystemObjectStore(tmp_path / "objects")
    req = request_for("programme-handbook.pdf", source, version="urn:anu:artifact-version:pdf:1")
    req.declared_media_type = "application/pdf"
    result = ingest_bytes(session, req, (FIXTURES / "programme-handbook.pdf").read_bytes(), store=store)
    assert "responsible AI systems" in (result.extracted_text or "")
    response = retrieve(session, RetrievalQuery(query="responsible AI systems", mode=RetrievalMode.HYBRID))
    assert response.hits
    hit = response.hits[0]
    assert hit.ref == result.version_id
    assert source in hit.source_refs
    assert hit.provenance_ref == result.provenance_ref
    assert hit.content_hash == result.content_hash


def test_fact_ingestion_fails_closed_without_source_authority(session, tmp_path):
    source = register_source(session, authoritative=False)
    req = request_for(
        "programme-handbook.pdf",
        source,
        version="urn:anu:artifact-version:fact:1",
        epistemic=EpistemicType.FACT,
    )
    with pytest.raises(DomainValidationError) as exc:
        ingest_bytes(session, req, (FIXTURES / "programme-handbook.pdf").read_bytes(), store=FileSystemObjectStore(tmp_path / "objects"))
    assert "SOURCE_AUTHORITY_REQUIRED" in exc.value.reason_codes


def test_corrupt_pdf_is_retained_but_marked_failed_not_promoted(session, tmp_path):
    source = register_source(session)
    req = request_for("corrupt.pdf", source, version="urn:anu:artifact-version:corrupt:1")
    req.declared_media_type = "application/pdf"
    result = ingest_bytes(session, req, b"%PDF-this-is-corrupt", store=FileSystemObjectStore(tmp_path / "objects"))
    assert result.extraction_status.value == "FAILED"
    assert result.extracted_text is None
    assert "extraction_error" in result.metadata


def test_tamper_is_detected_after_ingestion(session, tmp_path):
    source = register_source(session)
    store = FileSystemObjectStore(tmp_path / "objects")
    req = request_for("pilot-notes.txt", source, version="urn:anu:artifact-version:tamper:1")
    result = ingest_bytes(session, req, (FIXTURES / "pilot-notes.txt").read_bytes(), store=store)
    assert verify_artifact_integrity(session, result.version_id, store=store).integrity_state == "PASS"
    store.path_for_ref(result.storage_ref).write_bytes(b"tampered")
    assert verify_artifact_integrity(session, result.version_id, store=store).integrity_state == "FAIL"


def test_artifact_epistemic_type_cannot_be_mutated_by_new_version(session, tmp_path):
    source = register_source(session)
    store = FileSystemObjectStore(tmp_path / "objects")
    first = request_for("pilot-notes.txt", source, version="urn:anu:artifact-version:epi:1", epistemic=EpistemicType.CLAIM)
    ingest_bytes(session, first, b"draft claim", store=store)
    second = request_for("pilot-notes.txt", source, version="urn:anu:artifact-version:epi:2", epistemic=EpistemicType.FACT, supersedes=first.version_id)
    with pytest.raises(DomainValidationError) as exc:
        ingest_bytes(session, second, b"now official", store=store)
    assert "EPISTEMIC_TYPE_MUTATION_FORBIDDEN" in exc.value.reason_codes


def test_university_memory_projection_is_searchable_but_keeps_original_source_ref(session, tmp_path):
    source = register_source(session)
    store = FileSystemObjectStore(tmp_path / "objects")
    req = request_for("pilot-notes.txt", source, version="urn:anu:artifact-version:memory:1")
    ingest_bytes(session, req, (FIXTURES / "pilot-notes.txt").read_bytes(), store=store)
    stats = rebuild_memory_projection(session)
    assert stats["indexed_memory_records"] >= 1
    response = retrieve(session, RetrievalQuery(query="immutable content", mode=RetrievalMode.LEXICAL))
    memory_hits = [hit for hit in response.hits if hit.object_kind == "MEMORY_INDEX"]
    assert memory_hits
    assert memory_hits[0].source_refs[0].startswith("urn:anu:artifact-version:")


def test_stale_source_is_rejected_before_artifact_write(session, tmp_path):
    source = register_source(session)
    from anu_kernel.reality_models import SourceRegistry
    row = session.get(SourceRegistry, source)
    row.effective_to = datetime(2026, 9, 24, tzinfo=timezone.utc)
    session.commit()
    req = request_for("pilot-notes.txt", source, version="urn:anu:artifact-version:stale:1")
    with pytest.raises(DomainValidationError) as exc:
        ingest_bytes(session, req, b"stale source payload", store=FileSystemObjectStore(tmp_path / "objects"))
    assert "SOURCE_STALE_OR_INACTIVE" in exc.value.reason_codes


def test_knowledge_materialization_preserves_epistemic_type_and_provenance_chain(session, tmp_path):
    from anu_kernel.ingestion_contracts import KnowledgeMaterializationRequest
    from anu_kernel.ingestion_services import materialize_knowledge_object
    from anu_kernel.reality_services import provenance_graph

    source = register_source(session)
    store = FileSystemObjectStore(tmp_path / "objects")
    req = request_for("programme-handbook.pdf", source, version="urn:anu:artifact-version:knowledge:1")
    req.declared_media_type = "application/pdf"
    artifact = ingest_bytes(session, req, (FIXTURES / "programme-handbook.pdf").read_bytes(), store=store)
    result = materialize_knowledge_object(
        session,
        KnowledgeMaterializationRequest(
            knowledge_id="urn:anu:knowledge:programme-handbook",
            version="1.0.0",
            title="ARU-01 Programme Handbook Knowledge",
            artifact_version_ref=artifact.version_id,
            author_owner="urn:anu:org:academic-affairs",
            actor_ref="urn:anu:human:data-steward",
            effective_period=EffectivePeriod(valid_from=now()),
        ),
    )
    assert result.epistemic_type == EpistemicType.CLAIM
    graph = provenance_graph(session, result.provenance_ref)
    assert graph.completeness_status == "COMPLETE"
    assert any(edge["relation"] == "DERIVED_FROM" for edge in graph.edges)
    search = retrieve(session, RetrievalQuery(query="Programme Handbook Knowledge", mode=RetrievalMode.HYBRID))
    assert any(hit.object_kind == "KNOWLEDGE" and hit.provenance_ref == result.provenance_ref for hit in search.hits)


def test_ingest_size_limit_fails_closed(session, tmp_path, monkeypatch):
    source = register_source(session)
    monkeypatch.setenv("ANU_MAX_INGEST_BYTES", "4")
    req = request_for("big.txt", source, version="urn:anu:artifact-version:big:1")
    with pytest.raises(DomainValidationError) as exc:
        ingest_bytes(session, req, b"12345", store=FileSystemObjectStore(tmp_path / "objects"))
    assert "ARTIFACT_TOO_LARGE" in exc.value.reason_codes
