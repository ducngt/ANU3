from __future__ import annotations

from datetime import datetime

from fastapi.testclient import TestClient
from sqlalchemy.orm import sessionmaker

from anu_kernel.api import app, get_session
from anu_kernel.db import Base, make_engine


def dt(s: str) -> datetime:
    return datetime.fromisoformat(s.replace("Z", "+00:00"))


def make_client():
    engine = make_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine, future=True)

    def override_session():
        with Session() as session:
            yield session

    app.dependency_overrides[get_session] = override_session
    return TestClient(app), Session


def test_duplicate_identity_returns_structured_409():
    client, _ = make_client()
    payload = {
        "identity_id": "urn:anu:identity:human:h003",
        "subject_id": "urn:anu:human:h003",
        "subject_type": "HUMAN",
        "assurance_level": "HIGH",
        "status": "ACTIVE",
        "credential_refs": [],
        "aliases": ["Programme Owner SE"],
        "effective_period": {"valid_from": "2026-01-01T00:00:00Z", "valid_until": None},
        "lifecycle_state": "ACTIVE",
        "provenance_ref": None,
    }
    assert client.post("/v1/identities", json=payload).status_code == 200
    duplicate = client.post("/v1/identities", json=payload)
    assert duplicate.status_code == 409
    assert duplicate.json()["error"] == "RESOURCE_CONFLICT"


def test_human_dashboard_replaces_root_404():
    client, _ = make_client()
    response = client.get("/", follow_redirects=False)
    assert response.status_code == 307
    dashboard = client.get("/human")
    assert dashboard.status_code == 200
    assert "Human Dashboard" in dashboard.text


def test_governed_endpoint_requires_authentication(monkeypatch):
    client, _ = make_client()
    response = client.post("/v1/governed/evaluate", json={
        "action": "academic.programme.approve",
        "resource": "urn:anu:programme:se",
        "context": None,
        "risk": "HIGH",
        "at": "2026-10-15T10:00:00Z",
        "competence_refs": [],
    })
    assert response.status_code == 401
    assert response.json()["error"] == "AUTHENTICATION_FAILED"


def test_integrity_hash_is_deterministic():
    client, _ = make_client()
    one = client.post("/v1/integrity/hash", json={"artifact": {"b": 2, "a": 1}})
    two = client.post("/v1/integrity/hash", json={"artifact": {"a": 1, "b": 2}})
    assert one.status_code == 200
    assert two.status_code == 200
    assert one.json()["integrity_ref"] == two.json()["integrity_ref"]
    assert one.json()["integrity_ref"].startswith("sha256:")
