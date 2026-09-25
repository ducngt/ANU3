from __future__ import annotations

from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from anu_kernel.capability_contracts import (
    CapabilityContract,
    CapabilityDiscoveryQuery,
    CapabilityOperation,
    SmartBoxManifest,
    SmartBoxOperationBinding,
)
from anu_kernel.capability_repository import add_capability, add_smart_box
from anu_kernel.capability_services import discover_capabilities
from anu_kernel.contracts import EffectivePeriod, ProvenanceRecordContract
from anu_kernel.errors import DomainValidationError
from anu_kernel.repository import add_provenance


def dt() -> datetime:
    return datetime(2026, 9, 25, tzinfo=timezone.utc)


def prov(session, pid: str, entity: str):
    add_provenance(
        session,
        ProvenanceRecordContract(
            provenance_id=pid,
            entity_ref=entity,
            actor_ref="urn:anu:human:capability-owner",
            source_refs=["urn:aru:fixture:p3-contract"],
            input_refs=[],
            output_refs=[entity],
            effective_time=dt(),
            recorded_time=dt(),
        ),
    )


def capability(provenance_ref: str):
    return CapabilityContract(
        capability_id="urn:anu:capability:knowledge-retrieval",
        name="Knowledge Retrieval",
        description="Retrieve governed knowledge with source and provenance.",
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
        provenance_ref=provenance_ref,
    )


def box(provenance_ref: str, *, box_id: str, provider: str):
    return SmartBoxManifest(
        box_id=box_id,
        capability_ref="urn:anu:capability:knowledge-retrieval@1.0.0",
        box_version="1.0.0",
        provider_ref=provider,
        runtime_type="PYTHON_ADAPTER",
        operation_bindings=[SmartBoxOperationBinding(operation_id="knowledge.retrieve", handler_ref="anu.retrieval:retrieve")],
        adapter_boundary="urn:anu:adapter-boundary:knowledge-retrieval",
        data_classes=["INTERNAL", "CONFIDENTIAL-ACADEMIC"],
        quality_slo={"p95_ms": 500},
        observability={"trace": True, "metrics": True},
        effective_period=EffectivePeriod(valid_from=dt()),
        provenance_ref=provenance_ref,
    )


def test_capability_contract_schema_rejects_hidden_authority_field():
    payload = capability("urn:anu:prov:cap").model_dump(mode="json")
    payload["authority"] = "standing-power"
    with pytest.raises(ValidationError):
        CapabilityContract.model_validate(payload)


def test_registry_discovers_capability_and_multiple_replaceable_box_providers(session):
    prov(session, "urn:anu:prov:cap", "urn:anu:capability:knowledge-retrieval@1.0.0")
    prov(session, "urn:anu:prov:box:a", "urn:anu:box:retrieval:a@1.0.0")
    prov(session, "urn:anu:prov:box:b", "urn:anu:box:retrieval:b@1.0.0")
    add_capability(session, capability("urn:anu:prov:cap"))
    add_smart_box(session, box("urn:anu:prov:box:a", box_id="urn:anu:box:retrieval:a", provider="urn:anu:provider:local"))
    add_smart_box(session, box("urn:anu:prov:box:b", box_id="urn:anu:box:retrieval:b", provider="urn:anu:provider:alternate"))
    response = discover_capabilities(
        session,
        CapabilityDiscoveryQuery(
            operation_id="knowledge.retrieve",
            input_semantics=["urn:anu:semantic:retrieval-query"],
            output_semantics=["urn:anu:semantic:retrieval-result"],
            domain="knowledge",
        ),
    )
    assert len(response.hits) == 1
    hit = response.hits[0]
    assert hit.capability_ref == "urn:anu:capability:knowledge-retrieval@1.0.0"
    assert len(hit.box_refs) == 2


def test_box_cannot_bind_operation_not_declared_by_capability(session):
    prov(session, "urn:anu:prov:cap", "urn:anu:capability:knowledge-retrieval@1.0.0")
    prov(session, "urn:anu:prov:box", "urn:anu:box:bad@1.0.0")
    add_capability(session, capability("urn:anu:prov:cap"))
    bad = box("urn:anu:prov:box", box_id="urn:anu:box:bad", provider="urn:anu:provider:bad")
    bad.operation_bindings = [SmartBoxOperationBinding(operation_id="institution.approve", handler_ref="bad:approve")]
    with pytest.raises(DomainValidationError) as exc:
        add_smart_box(session, bad)
    assert "BOX_OPERATION_NOT_IN_CONTRACT" in exc.value.reason_codes
