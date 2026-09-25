from __future__ import annotations

from fastapi.testclient import TestClient
from sqlalchemy.orm import sessionmaker

from anu_kernel.api import app, get_session
from anu_kernel.db import Base, make_engine
import anu_kernel.reality_models  # ensure shared metadata contains P2 tables


def make_client():
    engine = make_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine, future=True)

    def override_session():
        with Session() as session:
            yield session

    app.dependency_overrides[get_session] = override_session
    return TestClient(app)


def test_health_reports_phase_2():
    client = make_client()
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["phase"] == 2
    assert response.json()["kernel_version"] == "0.5.0"


def test_phase2_source_registry_endpoint_is_exposed():
    client = make_client()
    response = client.post(
        "/v2/sources",
        json={
            "source_id": "urn:aru:source:test",
            "name": "ARU Test Source",
            "source_kind": "SYNTHETIC_REGISTRY",
            "owner_ref": "urn:anu:org:aru",
            "synthetic_fixture": True,
            "effective_period": {"valid_from": "2026-01-01T00:00:00Z", "valid_until": None},
            "lifecycle_state": "ACTIVE",
            "provenance_ref": None,
        },
    )
    assert response.status_code == 200
    assert response.json()["source_id"] == "urn:aru:source:test"
