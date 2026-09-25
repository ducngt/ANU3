from __future__ import annotations

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import sessionmaker

from anu_kernel.db import make_engine
from anu_kernel.reality_models import DataObjectVersion, SourceAuthorityMapping
from scripts.foundation_data_lab import app


TOKEN = "synthetic-foundation-lab-token-very-long"
HEADERS = {"X-ANU-Foundation-Token": TOKEN}


def test_foundation_lab_requires_configured_token(monkeypatch, tmp_path):
    monkeypatch.delenv("ANU_FOUNDATION_LAB_TOKEN", raising=False)
    monkeypatch.setenv("ANU_FOUNDATION_LAB_DB", str(tmp_path / "foundation-lab.sqlite3"))
    client = TestClient(app)
    assert client.get("/foundation").status_code == 200
    assert client.post("/foundation/bootstrap").status_code == 503
    monkeypatch.setenv("ANU_FOUNDATION_LAB_TOKEN", TOKEN)
    assert client.post("/foundation/bootstrap").status_code == 401


def test_foundation_data_is_shared_by_contract_without_claiming_authority(monkeypatch, tmp_path):
    path = tmp_path / "foundation-lab.sqlite3"
    monkeypatch.setenv("ANU_FOUNDATION_LAB_TOKEN", TOKEN)
    monkeypatch.setenv("ANU_FOUNDATION_LAB_DB", str(path))
    client = TestClient(app)
    assert client.post("/foundation/bootstrap", headers=HEADERS).status_code == 200
    assert client.post("/foundation/bootstrap", headers=HEADERS).status_code == 200
    assert client.post("/foundation/records", headers=HEADERS, json={
        "kind": "programme", "code": "SE-TEST", "title": "Synthetic software engineering",
        "synthetic_acknowledged": False,
    }).status_code == 422
    for kind, code in [("programme", "SE-TEST"), ("competency", "C-TEST"),
                       ("organisation", "ORG-TEST"), ("policy", "POL-TEST")]:
        response = client.post("/foundation/records", headers=HEADERS, json={
            "kind": kind, "code": code, "title": f"Synthetic {kind}",
            "synthetic_acknowledged": True,
        })
        assert response.status_code == 200, response.text
        assert response.json()["status"] == "SYNTHETIC_UNVALIDATED"

    lis = client.get("/foundation/views/lis", headers=HEADERS)
    ris = client.get("/foundation/views/ris", headers=HEADERS)
    assert lis.status_code == ris.status_code == 200
    assert {item["payload"]["code"] for item in lis.json()["items"]} == {"SE-TEST", "C-TEST", "ORG-TEST", "POL-TEST"}
    assert {item["payload"]["code"] for item in ris.json()["items"]} == {"SE-TEST", "ORG-TEST", "POL-TEST"}
    assert client.get("/foundation/views/other", headers=HEADERS).status_code == 404
    for item in lis.json()["items"]:
        assert item["epistemic_type"] == "CLAIM"
        assert item["validation_state"] == "UNVALIDATED"
        assert item["provenance_ref"] and item["source_ref"] and item["contract_ref"]
    engine = make_engine(f"sqlite+pysqlite:///{path}")
    with sessionmaker(bind=engine, future=True)() as session:
        assert session.scalars(select(SourceAuthorityMapping)).all() == []
        assert all(row.synthetic_output and row.epistemic_type == "CLAIM" for row in session.scalars(select(DataObjectVersion)).all())
    engine.dispose()
