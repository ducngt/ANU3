from __future__ import annotations

from fastapi.testclient import TestClient
from sqlalchemy.orm import sessionmaker

from anu_kernel.api import app, get_session
from anu_kernel.db import Base, make_engine
import anu_kernel.reality_models
import anu_kernel.ingestion_models
import anu_kernel.capability_models


def make_client():
    engine = make_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine, future=True)

    def override_session():
        with Session() as session:
            yield session

    app.dependency_overrides[get_session] = override_session
    return TestClient(app)


def test_multimodal_upload_and_retrieval_api(monkeypatch, tmp_path):
    monkeypatch.setenv("ANU_OBJECT_STORE_ROOT", str(tmp_path / "objects"))
    client = make_client()
    assert client.post("/v2/sources", json={
        "source_id": "urn:aru:source:api-upload",
        "name": "API Upload Source",
        "source_kind": "SYNTHETIC_REGISTRY",
        "owner_ref": "urn:anu:org:aru",
        "synthetic_fixture": True,
        "effective_period": {"valid_from": "2026-01-01T00:00:00Z", "valid_until": None},
        "lifecycle_state": "ACTIVE",
        "provenance_ref": None,
    }).status_code == 200
    response = client.post(
        "/v2/artifacts/ingest",
        data={
            "artifact_id": "urn:anu:artifact:api:1",
            "version_id": "urn:anu:artifact-version:api:1:v1",
            "semantic_type": "urn:anu:semantic:learning-artifact",
            "source_ref": "urn:aru:source:api-upload",
            "owner_ref": "urn:anu:org:aru",
            "actor_ref": "urn:anu:human:data-steward",
            "observed_at": "2026-09-25T00:00:00Z",
            "epistemic_type": "CLAIM",
            "validation_state": "VALIDATED",
            "metadata_json": '{"title":"API provenance note"}',
        },
        files={"file": ("note.txt", b"source provenance retrieval", "text/plain")},
    )
    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["extraction_status"] == "EXTRACTED"
    integrity = client.get(f"/v2/artifacts/{payload['version_id']}/integrity")
    assert integrity.status_code == 200
    assert integrity.json()["integrity_state"] == "PASS"
    search = client.post("/v2/retrieval/search", json={"query": "provenance retrieval", "mode": "HYBRID"})
    assert search.status_code == 200
    assert search.json()["hits"][0]["provenance_ref"]
    assert search.json()["hits"][0]["source_refs"] == ["urn:aru:source:api-upload"]


def test_capability_registry_box_discovery_api():
    client = make_client()
    for pid, entity in [
        ("urn:anu:prov:api-cap", "urn:anu:capability:api-retrieval@1.0.0"),
        ("urn:anu:prov:api-box", "urn:anu:box:api-retrieval@1.0.0"),
    ]:
        assert client.post("/v1/provenance", json={
            "provenance_id": pid,
            "entity_ref": entity,
            "actor_ref": "urn:anu:human:capability-owner",
            "source_refs": ["urn:aru:fixture:api"],
            "input_refs": [],
            "output_refs": [entity],
            "effective_time": "2026-09-25T00:00:00Z",
            "recorded_time": "2026-09-25T00:00:00Z",
            "previous_provenance_refs": [],
        }).status_code == 200
    cap = client.post("/v3/capabilities", json={
        "capability_id": "urn:anu:capability:api-retrieval",
        "name": "API Retrieval",
        "description": "Reference retrieval capability",
        "owner_ref": "urn:anu:org:aru",
        "domain": "knowledge",
        "version": "1.0.0",
        "operations": [{
            "operation_id": "knowledge.retrieve",
            "purpose": "retrieve",
            "input_semantics": ["urn:anu:semantic:retrieval-query"],
            "output_semantics": ["urn:anu:semantic:retrieval-result"],
            "input_contract_refs": [],
            "output_contract_refs": [],
            "constraints": {},
            "policy_refs": [],
        }],
        "requires_capabilities": [],
        "data_scope": ["INTERNAL"],
        "policy_refs": [],
        "risk_class": "E1",
        "effective_period": {"valid_from": "2026-09-25T00:00:00Z", "valid_until": None},
        "lifecycle_state": "ACTIVE",
        "provenance_ref": "urn:anu:prov:api-cap",
    })
    assert cap.status_code == 200, cap.text
    box = client.post("/v3/boxes", json={
        "box_id": "urn:anu:box:api-retrieval",
        "capability_ref": "urn:anu:capability:api-retrieval@1.0.0",
        "box_version": "1.0.0",
        "provider_ref": "urn:anu:provider:api",
        "runtime_type": "PYTHON_ADAPTER",
        "operation_bindings": [{"operation_id": "knowledge.retrieve", "handler_ref": "anu.retrieval:retrieve", "timeout_seconds": 30, "idempotent": True}],
        "requires_capabilities": [],
        "adapter_boundary": "urn:anu:adapter-boundary:api-retrieval",
        "model_dependencies": [],
        "data_classes": ["INTERNAL"],
        "quality_slo": {},
        "observability": {"trace": True},
        "effective_period": {"valid_from": "2026-09-25T00:00:00Z", "valid_until": None},
        "lifecycle_state": "ACTIVE",
        "provenance_ref": "urn:anu:prov:api-box",
    })
    assert box.status_code == 200, box.text
    discover = client.post("/v3/discover", json={"operation_id": "knowledge.retrieve", "domain": "knowledge"})
    assert discover.status_code == 200
    assert discover.json()["hits"][0]["box_refs"] == ["urn:anu:box:api-retrieval@1.0.0"]
