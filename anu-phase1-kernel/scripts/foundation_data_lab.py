"""Opt-in shared foundational data intake, backed by ANU Phase 2 contracts.

Synthetic-only reference boundary: this service does not approve institutional
facts or authenticate an institutional data steward. It validates consumer
views via versioned data contracts rather than direct cross-domain DB access.
"""
from __future__ import annotations

import os
import secrets
import subprocess
import sys
import threading
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from fastapi import FastAPI, Header, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import sessionmaker

from anu_kernel.contracts import EffectivePeriod, ProvenanceRecordContract
from anu_kernel.db import make_engine
from anu_kernel.reality_contracts import (
    DataContractContract, DataEnvelopeContract, DataSourceRef, EpistemicType,
    SourceRegistryContract, ValidationState,
)
from anu_kernel.reality_models import DataContractVersion, DataObjectVersion, SourceRegistry
from anu_kernel.reality_repository import add_data_contract, add_data_object, add_source
from anu_kernel.repository import add_provenance
from anu_kernel.reality_services import project_data
from anu_kernel.reality_contracts import DataProjectionRequest

ROOT = Path(__file__).resolve().parents[1]
SOURCE = "urn:anu:source:foundation-lab-synthetic"
OWNER = "urn:anu:org:aru01-synthetic"
ACTOR = "urn:anu:service:foundation-data-lab"
CONTRACTS = {
    "programme": ("urn:anu:data-contract:foundation-programme-lab", "urn:anu:semantic:programme", ["LIS", "RIS"]),
    "competency": ("urn:anu:data-contract:foundation-competency-lab", "urn:anu:semantic:competency", ["LIS"]),
    "organisation": ("urn:anu:data-contract:foundation-organisation-lab", "urn:anu:semantic:organisation", ["LIS", "RIS"]),
    "policy": ("urn:anu:data-contract:foundation-policy-lab", "urn:anu:semantic:policy-reference", ["LIS", "RIS"]),
}
app = FastAPI(title="ANU foundation intake lab", docs_url=None, redoc_url=None, openapi_url=None)
_db_lock = threading.Lock()
_migrated_urls: set[str] = set()


class Intake(BaseModel):
    kind: str
    code: str = Field(min_length=2, max_length=40, pattern=r"^[A-Za-z0-9._-]+$")
    title: str = Field(min_length=3, max_length=160)
    description: str = Field(default="", max_length=500)
    synthetic_acknowledged: bool


def _require_token(value: str | None) -> None:
    expected = os.environ.get("ANU_FOUNDATION_LAB_TOKEN", "")
    if len(expected) < 24:
        raise HTTPException(503, "Set ANU_FOUNDATION_LAB_TOKEN (24+ characters)")
    if not value or not secrets.compare_digest(value, expected):
        raise HTTPException(401, "Invalid foundation lab token")


def _url() -> str:
    raw = os.environ.get("ANU_FOUNDATION_LAB_DB", "").strip()
    if not raw or not Path(raw).is_absolute() or Path(raw).name != "foundation-lab.sqlite3":
        raise HTTPException(503, "Set ANU_FOUNDATION_LAB_DB to an absolute foundation-lab.sqlite3 path")
    path = Path(raw).resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    url = f"sqlite+pysqlite:///{path}"
    with _db_lock:
        if url not in _migrated_urls:
            env = {**os.environ, "ANU_DATABASE_URL": url}
            result = subprocess.run(
                [sys.executable, "-m", "alembic", "-c", "alembic.ini", "upgrade", "head"],
                cwd=ROOT, env=env, capture_output=True, text=True, timeout=90, check=False,
            )
            if result.returncode:
                raise HTTPException(500, "Could not migrate foundation lab database")
            _migrated_urls.add(url)
    return url


def _session():
    engine = make_engine(_url())
    return engine, sessionmaker(bind=engine, future=True)()


def _bootstrap(session) -> None:
    now = datetime.now(timezone.utc)
    source_provenance = "urn:anu:provenance:foundation-lab-source"
    if not session.get(SourceRegistry, SOURCE):
        add_provenance(session, ProvenanceRecordContract(
            provenance_id=source_provenance, entity_ref=SOURCE, actor_ref=ACTOR,
            effective_time=now, recorded_time=now, source_refs=["urn:anu:fixture:aru01"],
        ))
        add_source(session, SourceRegistryContract(
            source_id=SOURCE, name="ARU-01 synthetic foundation intake", source_kind="FIXTURE",
            owner_ref=OWNER, synthetic_fixture=True, effective_period=EffectivePeriod(valid_from=now),
            provenance_ref=source_provenance,
        ))
    for kind, (contract_id, semantic, consumers) in CONTRACTS.items():
        if session.scalar(select(DataContractVersion).where(
            DataContractVersion.contract_id == contract_id, DataContractVersion.version == "1.0.0",
        )):
            continue
        add_data_contract(session, DataContractContract(
            contract_id=contract_id, data_type="FOUNDATIONAL_SYNTHETIC_CANDIDATE",
            semantic_definition=semantic,
            schema={"type": "object", "required": ["code", "title"], "properties": {
                "code": {"type": "string"}, "title": {"type": "string"}, "description": {"type": "string"}}},
            owner=OWNER, authoritative_source=None, producers=[SOURCE],
            consumers=[f"urn:anu:consumer:{consumer.lower()}" for consumer in consumers],
            privacy_class="SYNTHETIC", access_policy="SYNTHETIC_LAB_ONLY",
            quality_rules=[{"rule": "source-provenance-required"}],
            version="1.0.0", provenance_ref=source_provenance,
        ))


@app.get("/foundation", response_class=HTMLResponse, include_in_schema=False)
def page():
    return Path(__file__).with_suffix(".html").read_text(encoding="utf-8")


@app.post("/foundation/bootstrap")
def bootstrap(x_anu_foundation_token: str | None = Header(default=None)):
    _require_token(x_anu_foundation_token)
    engine, session = _session()
    try:
        _bootstrap(session)
        return {"source": SOURCE, "contracts": list(CONTRACTS), "mode": "SYNTHETIC_CANDIDATE"}
    finally:
        session.close(); engine.dispose()


@app.post("/foundation/records")
def create_record(body: Intake, x_anu_foundation_token: str | None = Header(default=None)):
    _require_token(x_anu_foundation_token)
    if body.kind not in CONTRACTS or body.synthetic_acknowledged is not True:
        raise HTTPException(422, "Select a known foundational kind and confirm synthetic input")
    engine, session = _session()
    try:
        if not session.get(SourceRegistry, SOURCE):
            raise HTTPException(409, "Register synthetic foundation source and contracts first")
        now = datetime.now(timezone.utc)
        suffix = uuid4().hex
        contract_id, semantic, _ = CONTRACTS[body.kind]
        data_id = f"urn:anu:data:foundation-lab:{body.kind}:{suffix}"
        version_id = f"urn:anu:data-version:foundation-lab:{suffix}"
        provenance_ref = f"urn:anu:provenance:foundation-lab:{suffix}"
        add_provenance(session, ProvenanceRecordContract(
            provenance_id=provenance_ref, entity_ref=version_id, actor_ref=ACTOR,
            source_refs=[SOURCE], output_refs=[version_id], effective_time=now, recorded_time=now,
        ))
        add_data_object(session, DataEnvelopeContract(
            data_id=data_id, version_id=version_id, contract_ref=f"{contract_id}@1.0.0",
            semantic_type=semantic, schema_version="1.0.0",
            source=DataSourceRef(system_id=SOURCE, record_ref=f"fixture:{body.code}:{suffix}"),
            owner_ref=OWNER, effective_period=EffectivePeriod(valid_from=now), recorded_time=now,
            epistemic_type=EpistemicType.CLAIM, validation_state=ValidationState.UNVALIDATED,
            provenance_ref=provenance_ref, synthetic_output=True,
            payload={"code": body.code, "title": body.title, "description": body.description},
        ))
        return {"data_id": data_id, "version_id": version_id, "contract_ref": f"{contract_id}@1.0.0",
                "provenance_ref": provenance_ref, "status": "SYNTHETIC_UNVALIDATED"}
    finally:
        session.close(); engine.dispose()


@app.get("/foundation/views/{consumer}")
def consumer_view(consumer: str, x_anu_foundation_token: str | None = Header(default=None)):
    _require_token(x_anu_foundation_token)
    if consumer not in {"lis", "ris"}:
        raise HTTPException(404, "Unknown consumer")
    engine, session = _session()
    try:
        rows = session.scalars(select(DataObjectVersion).where(
            DataObjectVersion.source_system_id == SOURCE,
            DataObjectVersion.synthetic_output.is_(True),
            DataObjectVersion.lifecycle_state == "ACTIVE",
        ).order_by(DataObjectVersion.recorded_time, DataObjectVersion.version_id)).all()
        items = []
        for row in rows:
            cid, version = row.contract_ref.rsplit("@", 1)
            contract = session.scalar(select(DataContractVersion).where(
                DataContractVersion.contract_id == cid, DataContractVersion.version == version,
                DataContractVersion.lifecycle_state == "ACTIVE",
            ))
            if contract is None or f"urn:anu:consumer:{consumer}" not in (contract.consumers or []):
                continue
            projection = project_data(session, DataProjectionRequest(
                data_id=row.data_id, effective_at=datetime.now(timezone.utc),
            ))
            items.append({"data_id": row.data_id, "version_id": projection.version_id,
                "semantic_type": projection.semantic_type, "payload": projection.payload,
                "epistemic_type": projection.epistemic_type, "validation_state": projection.validation_state,
                "source_ref": projection.source_ref, "provenance_ref": projection.provenance_ref,
                "contract_ref": row.contract_ref, "privacy_class": contract.privacy_class})
        return {"consumer": consumer.upper(), "mode": "SYNTHETIC_PREVIEW_ONLY", "items": items}
    finally:
        session.close(); engine.dispose()
