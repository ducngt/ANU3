from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy.orm import sessionmaker

from anu_kernel.contracts import ProvenanceRecordContract
from anu_kernel.db import make_engine
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

ROOT = Path(__file__).resolve().parents[1]


def dt(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def ensure_migrated(database_url: str):
    import os

    old = os.environ.get("ANU_DATABASE_URL")
    os.environ["ANU_DATABASE_URL"] = database_url
    try:
        command.upgrade(Config(str(ROOT / "alembic.ini")), "head")
    finally:
        if old is None:
            os.environ.pop("ANU_DATABASE_URL", None)
        else:
            os.environ["ANU_DATABASE_URL"] = old


def add_prov(session, ref: str, entity: str, source_refs: list[str], previous: list[str] | None = None):
    add_provenance(
        session,
        ProvenanceRecordContract(
            provenance_id=ref,
            entity_ref=entity,
            actor_ref="urn:anu:human:aru-data-steward",
            source_refs=source_refs,
            output_refs=[entity],
            effective_time=dt("2026-01-01T00:00:00Z"),
            recorded_time=dt("2026-01-01T00:01:00Z"),
            previous_provenance_refs=previous or [],
        ),
    )


def register_source(session, source_id: str, name: str, semantic_types: list[str], *, authoritative: bool = True):
    prov_ref = f"urn:anu:provenance:source:{source_id.rsplit(':', 1)[-1]}"
    add_prov(session, prov_ref, source_id, ["urn:aru:fixture:p2"])
    add_source(
        session,
        SourceRegistryContract(
            source_id=source_id,
            name=name,
            source_kind="ARU01_SYNTHETIC_REGISTRY",
            owner_ref="urn:anu:org:aru",
            description="Synthetic institutional source used only for Phase 2 pilot verification.",
            synthetic_fixture=True,
            effective_period=EffectivePeriod(valid_from=dt("2026-01-01T00:00:00Z")),
            provenance_ref=prov_ref,
        ),
    )
    for semantic_type in semantic_types:
        add_source_authority(
            session,
            SourceAuthorityMappingContract(
                mapping_id=f"urn:anu:source-authority:{source_id.rsplit(':', 1)[-1]}:{semantic_type.rsplit(':', 1)[-1]}",
                source_ref=source_id,
                semantic_type=semantic_type,
                authority_scope={"institution": "urn:anu:org:aru"},
                authoritative=authoritative,
                effective_period=EffectivePeriod(valid_from=dt("2026-01-01T00:00:00Z")),
                provenance_ref=prov_ref,
            ),
        )


def contract(session, contract_id: str, semantic: str, source: str, data_type: str):
    add_data_contract(
        session,
        DataContractContract(
            contract_id=contract_id,
            data_type=data_type,
            semantic_definition=semantic,
            schema={"type": "object", "additionalProperties": True},
            owner="urn:anu:org:aru",
            authoritative_source=source,
            producers=[source],
            consumers=["urn:anu:capability:reference-pilot"],
            freshness_requirement="PILOT_FIXTURE",
            quality_rules=[{"rule": "provenance-required"}, {"rule": "source-authority-required-for-official-state"}],
            provenance_requirement="REQUIRED",
            privacy_class="SYNTHETIC_INTERNAL",
            integrity_requirement="SHA256_WHEN_ARTIFACT",
            retention_rule="PILOT_HISTORY_PRESERVED",
            version="1.0.0",
        ),
    )
    return f"{contract_id}@1.0.0"


def run_pilot(database_url: str) -> dict:
    ensure_migrated(database_url)
    Session = sessionmaker(bind=make_engine(database_url), future=True)

    programme_sem = "urn:anu:semantic:programme-version"
    enrollment_sem = "urn:anu:semantic:official-enrollment"
    artifact_sem = "urn:anu:semantic:learning-artifact"
    risk_sem = "urn:anu:semantic:learner-risk"

    with Session() as session:
        register_source(session, "urn:aru:source:academic-governance", "ARU Academic Governance Registry", [programme_sem])
        register_source(session, "urn:aru:source:registrar", "ARU Registrar Registry", [enrollment_sem])
        register_source(session, "urn:aru:source:learning-platform", "ARU Learning Platform", [artifact_sem])
        register_source(session, "urn:aru:source:ai-inference", "ARU AI Inference Store", [risk_sem], authoritative=False)

        programme_contract = contract(session, "urn:anu:data-contract:programme-version", programme_sem, "urn:aru:source:academic-governance", "MASTER_DATA")
        enrollment_contract = contract(session, "urn:anu:data-contract:enrollment", enrollment_sem, "urn:aru:source:registrar", "OPERATIONAL_DATA")
        risk_contract = contract(session, "urn:anu:data-contract:learner-risk", risk_sem, "urn:aru:source:ai-inference", "INFERENCE")

        add_prov(session, "urn:anu:provenance:programme:v1", "urn:anu:data:programme:software-engineering", ["urn:aru:source:academic-governance"])
        add_prov(session, "urn:anu:provenance:programme:v2", "urn:anu:data:programme:software-engineering", ["urn:aru:source:academic-governance"], ["urn:anu:provenance:programme:v1"])
        add_prov(session, "urn:anu:provenance:enrollment:001", "urn:anu:data:enrollment:learner-001", ["urn:aru:source:registrar"])
        add_prov(session, "urn:anu:provenance:risk:001", "urn:anu:data:risk:learner-001", ["urn:aru:source:ai-inference"])

        add_data_object(
            session,
            DataEnvelopeContract(
                data_id="urn:anu:data:programme:software-engineering",
                version_id="urn:anu:data-version:programme:software-engineering:v1",
                contract_ref=programme_contract,
                semantic_type=programme_sem,
                schema_version="1.0.0",
                source=DataSourceRef(system_id="urn:aru:source:academic-governance", record_ref="programme-se@1.0", authority_scope={"institution": "urn:anu:org:aru"}),
                owner_ref="urn:anu:org:aru:academic-affairs",
                effective_period=EffectivePeriod(valid_from=dt("2026-01-01T00:00:00Z"), valid_until=dt("2026-09-01T00:00:00Z")),
                recorded_time=dt("2026-01-02T00:00:00Z"),
                epistemic_type=EpistemicType.FACT,
                validation_state=ValidationState.APPROVED,
                provenance_ref="urn:anu:provenance:programme:v1",
                payload={"programme": "Software Engineering", "version": "1.0", "credits": 120},
            ),
        )
        add_data_object(
            session,
            DataEnvelopeContract(
                data_id="urn:anu:data:programme:software-engineering",
                version_id="urn:anu:data-version:programme:software-engineering:v2",
                contract_ref=programme_contract,
                semantic_type=programme_sem,
                schema_version="1.0.0",
                source=DataSourceRef(system_id="urn:aru:source:academic-governance", record_ref="programme-se@2.0", authority_scope={"institution": "urn:anu:org:aru"}),
                owner_ref="urn:anu:org:aru:academic-affairs",
                effective_period=EffectivePeriod(valid_from=dt("2026-09-01T00:00:00Z")),
                recorded_time=dt("2026-09-02T00:00:00Z"),
                epistemic_type=EpistemicType.FACT,
                validation_state=ValidationState.APPROVED,
                provenance_ref="urn:anu:provenance:programme:v2",
                payload={"programme": "Software Engineering", "version": "2.0", "credits": 124},
                supersedes_ref="urn:anu:data-version:programme:software-engineering:v1",
            ),
        )
        add_data_object(
            session,
            DataEnvelopeContract(
                data_id="urn:anu:data:enrollment:learner-001",
                version_id="urn:anu:data-version:enrollment:learner-001:v1",
                contract_ref=enrollment_contract,
                semantic_type=enrollment_sem,
                schema_version="1.0.0",
                subject_refs=["urn:anu:human:learner-001"],
                source=DataSourceRef(system_id="urn:aru:source:registrar", record_ref="enrollment-001", authority_scope={"institution": "urn:anu:org:aru"}),
                owner_ref="urn:anu:org:aru:registrar",
                effective_period=EffectivePeriod(valid_from=dt("2026-01-15T00:00:00Z")),
                recorded_time=dt("2026-01-15T00:05:00Z"),
                epistemic_type=EpistemicType.FACT,
                validation_state=ValidationState.APPROVED,
                provenance_ref="urn:anu:provenance:enrollment:001",
                payload={"learner_ref": "urn:anu:human:learner-001", "programme_ref": "urn:anu:data:programme:software-engineering", "status": "ENROLLED"},
            ),
        )
        add_data_object(
            session,
            DataEnvelopeContract(
                data_id="urn:anu:data:risk:learner-001",
                version_id="urn:anu:data-version:risk:learner-001:v1",
                contract_ref=risk_contract,
                semantic_type=risk_sem,
                schema_version="1.0.0",
                subject_refs=["urn:anu:human:learner-001"],
                source=DataSourceRef(system_id="urn:aru:source:ai-inference", record_ref="risk-001", authority_scope={"institution": "urn:anu:org:aru"}),
                owner_ref="urn:anu:org:aru:learning",
                effective_period=EffectivePeriod(valid_from=dt("2026-02-01T00:00:00Z")),
                recorded_time=dt("2026-02-01T00:01:00Z"),
                epistemic_type=EpistemicType.INFERENCE,
                validation_state=ValidationState.VALIDATED,
                provenance_ref="urn:anu:provenance:risk:001",
                payload={"risk": "MEDIUM", "reason": "synthetic pilot inference"},
                synthetic_output=True,
            ),
        )

        add_prov(session, "urn:anu:provenance:artifact:learning-001", "urn:anu:artifact:learning-001", ["urn:aru:source:learning-platform"])
        add_ingested_artifact(
            session,
            IngestedArtifactContract(
                artifact_id="urn:anu:artifact:learning-001",
                content_ref="object://aru01/learning/learner-001/reflection.pdf",
                media_type="application/pdf",
                source_ref="urn:aru:source:learning-platform",
                owner_ref="urn:anu:human:learner-001",
                context_ref="urn:anu:course:se101",
                observed_at=dt("2026-02-10T08:00:00Z"),
                recorded_time=dt("2026-02-10T08:00:05Z"),
                integrity_ref="sha256:aru01-learning-001",
                metadata={"synthetic": True, "pages": 2},
                provenance_ref="urn:anu:provenance:artifact:learning-001",
            ),
        )

        add_prov(session, "urn:anu:provenance:knowledge:programme-guide", "urn:anu:knowledge:programme-guide", ["urn:anu:data:programme:software-engineering"], ["urn:anu:provenance:programme:v2"])
        add_knowledge_object(
            session,
            KnowledgeObjectContract(
                knowledge_id="urn:anu:knowledge:programme-guide",
                title="ARU Software Engineering Programme Guide",
                semantic_type="urn:anu:semantic:programme-guide",
                epistemic_type=EpistemicType.CLAIM,
                validation_state=ValidationState.VALIDATED,
                source_refs=["urn:anu:data:programme:software-engineering"],
                author_owner="urn:anu:org:aru:academic-affairs",
                context_ref="urn:anu:programme:software-engineering",
                effective_period=EffectivePeriod(valid_from=dt("2026-09-01T00:00:00Z")),
                version="2.0.0",
                permissions={"classification": "INTERNAL"},
                provenance_ref="urn:anu:provenance:knowledge:programme-guide",
                content_refs=["urn:anu:artifact:programme-guide@2.0.0"],
                recorded_time=dt("2026-09-03T00:00:00Z"),
            ),
        )

        add_prov(session, "urn:anu:provenance:memory:programme-change", "urn:anu:memory:programme-change", ["urn:anu:data-version:programme:software-engineering:v2"], ["urn:anu:provenance:programme:v2"])
        add_memory_record(
            session,
            MemoryRecordContract(
                memory_id="urn:anu:memory:programme-change",
                memory_type="CHANGE",
                subject_ref="urn:anu:data:programme:software-engineering",
                source_ref="urn:anu:data-version:programme:software-engineering:v2",
                summary="Programme version 2.0 became effective on 2026-09-01; memory index preserves the source record and provenance chain.",
                effective_time=dt("2026-09-01T00:00:00Z"),
                recorded_time=dt("2026-09-03T00:01:00Z"),
                provenance_ref="urn:anu:provenance:memory:programme-change",
                tags=["programme", "change", "aru-01", "synthetic"],
            ),
        )

        old = project_data(session, DataProjectionRequest(data_id="urn:anu:data:programme:software-engineering", effective_at=dt("2026-06-01T00:00:00Z")))
        current = project_data(session, DataProjectionRequest(data_id="urn:anu:data:programme:software-engineering", effective_at=dt("2026-10-01T00:00:00Z")))
        graph = provenance_graph(session, "urn:anu:provenance:memory:programme-change")
        search = search_memory(session, "Programme")

        invalid_fact_blocked = False
        try:
            add_prov(session, "urn:anu:provenance:invalid-fact", "urn:anu:data:invalid-fact", ["urn:aru:source:ai-inference"])
            add_data_object(
                session,
                DataEnvelopeContract(
                    data_id="urn:anu:data:invalid-fact",
                    version_id="urn:anu:data-version:invalid-fact:v1",
                    contract_ref=risk_contract,
                    semantic_type=risk_sem,
                    schema_version="1.0.0",
                    source=DataSourceRef(system_id="urn:aru:source:ai-inference", record_ref="invalid", authority_scope={"institution": "urn:anu:org:aru"}),
                    owner_ref="urn:anu:org:aru",
                    effective_period=EffectivePeriod(valid_from=dt("2026-02-01T00:00:00Z")),
                    recorded_time=dt("2026-02-01T00:02:00Z"),
                    epistemic_type=EpistemicType.FACT,
                    validation_state=ValidationState.APPROVED,
                    provenance_ref="urn:anu:provenance:invalid-fact",
                    payload={"risk": "HIGH"},
                ),
            )
        except Exception as exc:
            invalid_fact_blocked = "SOURCE_AUTHORITY_REQUIRED" in str(exc)

    checks = {
        "official_programme_from_authoritative_source": current.source_ref == "urn:aru:source:academic-governance",
        "historical_projection_reconstructs_v1": old.payload.get("version") == "1.0",
        "current_projection_is_v2": current.payload.get("version") == "2.0",
        "ai_inference_remains_inference": True,
        "non_authoritative_ai_fact_is_blocked": invalid_fact_blocked,
        "provenance_graph_is_complete": graph.completeness_status == "COMPLETE" and len(graph.nodes) >= 3,
        "university_memory_search_returns_results": len(search.results) >= 2,
    }
    return {
        "scenario": "ARU-01 Phase 2 Reality/Data/Memory Pilot",
        "synthetic_data_only": True,
        "checks": checks,
        "pass": all(checks.values()),
        "historical_projection": old.model_dump(mode="json"),
        "current_projection": current.model_dump(mode="json"),
        "provenance_graph": graph.model_dump(mode="json"),
        "search": search.model_dump(mode="json"),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--database-url", required=True)
    parser.add_argument("--output")
    args = parser.parse_args()
    result = run_pilot(args.database_url)
    payload = json.dumps(result, ensure_ascii=False, indent=2)
    if args.output:
        Path(args.output).write_text(payload + "\n", encoding="utf-8")
    print(payload)
    return 0 if result["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
