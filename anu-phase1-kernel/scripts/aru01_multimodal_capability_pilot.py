from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import func, select
from sqlalchemy.orm import sessionmaker

from anu_kernel.capability_contracts import (
    CapabilityContract,
    CapabilityDiscoveryQuery,
    CapabilityOperation,
    SmartBoxManifest,
    SmartBoxOperationBinding,
)
from anu_kernel.capability_models import CapabilityVersion, SmartBoxManifestVersion
from anu_kernel.capability_repository import add_capability, add_smart_box
from anu_kernel.capability_services import discover_capabilities
from anu_kernel.contracts import EffectivePeriod, ProvenanceRecordContract
from anu_kernel.db import make_engine
from anu_kernel.ingestion_contracts import (
    KnowledgeMaterializationRequest,
    MultimodalArtifactIngestRequest,
    RetrievalMode,
    RetrievalQuery,
)
from anu_kernel.ingestion_models import ArtifactObjectVersion, RetrievalProjection
from anu_kernel.ingestion_services import (
    ingest_bytes,
    materialize_knowledge_object,
    rebuild_memory_projection,
    retrieve,
    verify_artifact_integrity,
)
from anu_kernel.object_store import FileSystemObjectStore
from anu_kernel.reality_contracts import (
    EpistemicType,
    SourceAuthorityMappingContract,
    SourceRegistryContract,
    ValidationState,
)
from anu_kernel.reality_models import KnowledgeObjectVersion, UniversityMemoryRecord
from anu_kernel.reality_repository import add_source, add_source_authority
from anu_kernel.reality_services import provenance_graph
from anu_kernel.repository import add_provenance

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "fixtures" / "aru-01" / "multimodal"


def dt(value: str = "2026-09-25T00:00:00+00:00") -> datetime:
    return datetime.fromisoformat(value).astimezone(timezone.utc)


def _prov(session, pid: str, entity: str, source_refs: list[str], previous: list[str] | None = None):
    add_provenance(
        session,
        ProvenanceRecordContract(
            provenance_id=pid,
            entity_ref=entity,
            actor_ref="urn:anu:human:data-steward",
            source_refs=source_refs,
            input_refs=[],
            output_refs=[entity],
            effective_time=dt(),
            recorded_time=dt(),
            previous_provenance_refs=previous or [],
        ),
    )


def _seed_source(session) -> str:
    source_id = "urn:aru:source:multimodal-learning-platform"
    prov_id = "urn:anu:prov:p2t02-source"
    _prov(session, prov_id, source_id, ["urn:aru:fixture:p2-t02"])
    add_source(
        session,
        SourceRegistryContract(
            source_id=source_id,
            name="ARU-01 Multimodal Learning Platform",
            source_kind="SYNTHETIC_REGISTRY",
            owner_ref="urn:anu:org:aru",
            description="Synthetic authoritative source for P2-T02 pilot artifacts",
            synthetic_fixture=True,
            effective_period=EffectivePeriod(valid_from=dt()),
            provenance_ref=prov_id,
        ),
    )
    add_source_authority(
        session,
        SourceAuthorityMappingContract(
            mapping_id="urn:anu:source-authority:p2t02-learning-artifact",
            source_ref=source_id,
            semantic_type="urn:anu:semantic:learning-artifact",
            authority_scope={"institution": "urn:anu:org:aru"},
            authoritative=True,
            effective_period=EffectivePeriod(valid_from=dt()),
            provenance_ref=prov_id,
        ),
    )
    return source_id


def _ingest(session, store: FileSystemObjectStore, source: str) -> list[dict]:
    cases = [
        ("programme-handbook.pdf", "application/pdf"),
        ("course-spec.docx", "application/vnd.openxmlformats-officedocument.wordprocessingml.document"),
        ("learning-diagram.png", "image/png"),
        ("lecture-note.wav", "audio/x-wav"),
        ("pilot-video.mp4", "video/mp4"),
    ]
    results: list[dict] = []
    for idx, (filename, media_type) in enumerate(cases, start=1):
        req = MultimodalArtifactIngestRequest(
            artifact_id=f"urn:anu:artifact:aru-p2t02:{idx}",
            version_id=f"urn:anu:artifact-version:aru-p2t02:{idx}:v1",
            filename=filename,
            semantic_type="urn:anu:semantic:learning-artifact",
            source_ref=source,
            owner_ref="urn:anu:org:aru",
            actor_ref="urn:anu:human:data-steward",
            observed_at=dt(),
            epistemic_type=EpistemicType.FACT if filename == "programme-handbook.pdf" else EpistemicType.CLAIM,
            validation_state=ValidationState.APPROVED if filename == "programme-handbook.pdf" else ValidationState.VALIDATED,
            authority_scope={"institution": "urn:anu:org:aru"} if filename == "programme-handbook.pdf" else {},
            declared_media_type=media_type,
            metadata={"title": f"ARU-01 {filename}", "pilot": "P2-T02"},
        )
        result = ingest_bytes(session, req, (FIXTURES / filename).read_bytes(), store=store)
        results.append(result.model_dump(mode="json"))
    return results


def _materialize_knowledge(session, artifact_version_ref: str) -> dict:
    result = materialize_knowledge_object(
        session,
        KnowledgeMaterializationRequest(
            knowledge_id="urn:anu:knowledge:aru-programme-handbook",
            version="1.0.0",
            title="ARU-01 Programme Handbook Knowledge",
            artifact_version_ref=artifact_version_ref,
            author_owner="urn:anu:org:academic-affairs",
            actor_ref="urn:anu:human:data-steward",
            effective_period=EffectivePeriod(valid_from=dt()),
        ),
    )
    return result.model_dump(mode="json")


def _seed_capability(session) -> dict:
    cap_ref = "urn:anu:capability:knowledge-retrieval@1.0.0"
    cap_prov = "urn:anu:prov:p3-capability-knowledge-retrieval"
    box_a_prov = "urn:anu:prov:p3-box-retrieval-local"
    box_b_prov = "urn:anu:prov:p3-box-retrieval-alt"
    _prov(session, cap_prov, cap_ref, ["urn:aru:fixture:p3-contract"])
    _prov(session, box_a_prov, "urn:anu:box:retrieval:local@1.0.0", [cap_ref], [cap_prov])
    _prov(session, box_b_prov, "urn:anu:box:retrieval:alt@1.0.0", [cap_ref], [cap_prov])
    add_capability(
        session,
        CapabilityContract(
            capability_id="urn:anu:capability:knowledge-retrieval",
            name="Knowledge Retrieval",
            description="Retrieve governed knowledge while preserving source/provenance.",
            owner_ref="urn:anu:org:academic-affairs",
            domain="knowledge",
            version="1.0.0",
            operations=[
                CapabilityOperation(
                    operation_id="knowledge.retrieve",
                    purpose="Find governed knowledge",
                    input_semantics=["urn:anu:semantic:retrieval-query"],
                    output_semantics=["urn:anu:semantic:retrieval-result"],
                    policy_refs=["urn:anu:policy:retrieval-access@1.0.0"],
                )
            ],
            data_scope=["INTERNAL", "CONFIDENTIAL-ACADEMIC"],
            policy_refs=["urn:anu:policy:retrieval-access@1.0.0"],
            risk_class="E1",
            effective_period=EffectivePeriod(valid_from=dt()),
            provenance_ref=cap_prov,
        ),
    )
    for box_id, provider, prov in [
        ("urn:anu:box:retrieval:local", "urn:anu:provider:reference-local", box_a_prov),
        ("urn:anu:box:retrieval:alt", "urn:anu:provider:reference-alternate", box_b_prov),
    ]:
        add_smart_box(
            session,
            SmartBoxManifest(
                box_id=box_id,
                capability_ref=cap_ref,
                box_version="1.0.0",
                provider_ref=provider,
                runtime_type="PYTHON_ADAPTER",
                operation_bindings=[SmartBoxOperationBinding(operation_id="knowledge.retrieve", handler_ref="anu.retrieval:retrieve")],
                adapter_boundary="urn:anu:adapter-boundary:knowledge-retrieval",
                data_classes=["INTERNAL", "CONFIDENTIAL-ACADEMIC"],
                quality_slo={"p95_ms": 500},
                observability={"trace": True, "metrics": True},
                effective_period=EffectivePeriod(valid_from=dt()),
                provenance_ref=prov,
            ),
        )
    discovery = discover_capabilities(
        session,
        CapabilityDiscoveryQuery(
            operation_id="knowledge.retrieve",
            input_semantics=["urn:anu:semantic:retrieval-query"],
            output_semantics=["urn:anu:semantic:retrieval-result"],
            domain="knowledge",
        ),
    )
    return discovery.model_dump(mode="json")


def run_pilot(database_url: str, object_store_root: str | Path) -> dict:
    engine = make_engine(database_url)
    Session = sessionmaker(bind=engine, future=True)
    store = FileSystemObjectStore(object_store_root)
    with Session() as session:
        source = _seed_source(session)
        artifacts = _ingest(session, store, source)
        pdf = artifacts[0]
        knowledge = _materialize_knowledge(session, pdf["version_id"])
        rebuild = rebuild_memory_projection(session)
        retrieval = retrieve(session, RetrievalQuery(query="responsible AI systems", mode=RetrievalMode.HYBRID))
        discovery = _seed_capability(session)
        integrity = verify_artifact_integrity(session, pdf["version_id"], store=store)
        graph = provenance_graph(session, knowledge["provenance_ref"])
        counts = {
            "artifacts": int(session.scalar(select(func.count()).select_from(ArtifactObjectVersion)) or 0),
            "knowledge_objects": int(session.scalar(select(func.count()).select_from(KnowledgeObjectVersion)) or 0),
            "memory_records": int(session.scalar(select(func.count()).select_from(UniversityMemoryRecord)) or 0),
            "retrieval_projections": int(session.scalar(select(func.count()).select_from(RetrievalProjection)) or 0),
            "capabilities": int(session.scalar(select(func.count()).select_from(CapabilityVersion)) or 0),
            "boxes": int(session.scalar(select(func.count()).select_from(SmartBoxManifestVersion)) or 0),
        }
    checks = {
        "five_multimodal_types_ingested": len(artifacts) == 5,
        "pdf_text_extracted": "responsible AI systems" in (artifacts[0].get("extracted_text") or ""),
        "docx_text_extracted": "provenance-aware design" in (artifacts[1].get("extracted_text") or ""),
        "image_metadata_ingested": artifacts[2]["extraction_status"] == "METADATA_ONLY",
        "audio_metadata_ingested": artifacts[3]["extraction_status"] == "METADATA_ONLY",
        "video_metadata_ingested": artifacts[4]["extraction_status"] == "METADATA_ONLY",
        "artifact_integrity_pass": integrity.integrity_state == "PASS",
        "knowledge_epistemic_preserved": knowledge["epistemic_type"] == artifacts[0]["epistemic_type"],
        "provenance_chain_complete": graph.completeness_status == "COMPLETE" and len(graph.edges) >= 1,
        "retrieval_has_source_and_provenance": bool(retrieval.hits and retrieval.hits[0].source_refs and retrieval.hits[0].provenance_ref),
        "memory_projection_materialized": rebuild["indexed_memory_records"] >= 1,
        "capability_discovery_pass": len(discovery["hits"]) == 1,
        "provider_replaceability_visible": len(discovery["hits"][0]["box_refs"]) == 2,
    }
    return {
        "work_id": "P2-T02-P3-01-MULTIMODAL-CAPABILITY-FOUNDATION",
        "pass": all(checks.values()),
        "checks": checks,
        "counts": counts,
        "artifacts": artifacts,
        "knowledge": knowledge,
        "retrieval": retrieval.model_dump(mode="json"),
        "capability_discovery": discovery,
        "object_store_root": str(Path(object_store_root).resolve()),
        "synthetic_data_only": True,
    }


if __name__ == "__main__":
    db = os.getenv("ANU_DATABASE_URL", "sqlite+pysqlite:///./anu_kernel.db")
    store_root = os.getenv("ANU_OBJECT_STORE_ROOT", "./var/object-store")
    result = run_pilot(db, store_root)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    raise SystemExit(0 if result["pass"] else 1)
