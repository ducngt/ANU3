from __future__ import annotations

from datetime import datetime, timezone

import pytest

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
from anu_kernel.sbbs_runtime_contracts import (
    AdapterDefinition,
    AssemblyDefinition,
    AssemblyExecutionRequest,
    CompatibilityCheckRequest,
    CompatibilityContext,
    ConnectionPlanRequest,
    SmartWireExecutionRequest,
    TransformDefinition,
    WriteBoxProposalRequest,
)
from anu_kernel.sbbs_runtime_repository import add_adapter, add_assembly, add_transform
from anu_kernel.sbbs_runtime_services import (
    evaluate_compatibility,
    execute_assembly,
    execute_wire,
    plan_connection,
    promote_write_box,
    propose_write_box,
)

NOW = datetime(2026, 9, 25, 0, 0, tzinfo=timezone.utc)
PROV = "urn:anu:provenance:p3-runtime-test"
OWNER = "urn:anu:org:aru-01"


def _provenance(session):
    add_provenance(session, ProvenanceRecordContract(
        provenance_id=PROV,
        entity_ref="urn:anu:work:p3-runtime-test",
        actor_ref="urn:anu:agent:ai-factory",
        effective_time=NOW,
        recorded_time=NOW,
    ))


def _capability(cap_id: str, op_id: str, input_sem: list[str], output_sem: list[str], input_contracts: list[str], output_contracts: list[str], *, permissions=None, security=None, policies=None):
    return CapabilityContract(
        capability_id=cap_id,
        name=cap_id.rsplit(":", 1)[-1],
        description="P3 runtime conformance fixture",
        owner_ref=OWNER,
        domain="learning-curriculum",
        version="1.0.0",
        operations=[CapabilityOperation(
            operation_id=op_id,
            purpose="conformance operation",
            input_semantics=input_sem,
            output_semantics=output_sem,
            input_contract_refs=input_contracts,
            output_contract_refs=output_contracts,
            permissions=permissions or [],
            security_tags=security or [],
            policy_refs=policies or [],
        )],
        policy_refs=[],
        effective_period=EffectivePeriod(valid_from=NOW),
        provenance_ref=PROV,
    )


def _box(box_id: str, cap_ref: str, op_id: str, runtime: str, handler: str, config=None):
    return SmartBoxManifest(
        box_id=box_id,
        capability_ref=cap_ref,
        box_version="1.0.0",
        provider_ref=f"urn:anu:provider:{box_id.rsplit(':',1)[-1]}",
        runtime_type=runtime,
        operation_bindings=[SmartBoxOperationBinding(operation_id=op_id, handler_ref=handler, binding_config=config or {})],
        adapter_boundary=f"urn:anu:adapter-boundary:{box_id.rsplit(':',1)[-1]}",
        effective_period=EffectivePeriod(valid_from=NOW),
        provenance_ref=PROV,
    )


def _seed_direct_pair(session):
    _provenance(session)
    src = _capability(
        "urn:anu:capability:programme-retrieval",
        "programme.retrieve",
        ["urn:anu:semantic:programme-query"],
        ["urn:anu:semantic:programme-record"],
        ["urn:anu:contract:programme-query.v1"],
        ["urn:anu:contract:programme-record.v1"],
    )
    dst = _capability(
        "urn:anu:capability:programme-summary",
        "programme.summarize",
        ["urn:anu:semantic:programme-record"],
        ["urn:anu:semantic:programme-summary"],
        ["urn:anu:contract:programme-record.v1"],
        ["urn:anu:contract:programme-summary.v1"],
    )
    add_capability(session, src)
    add_capability(session, dst)
    add_smart_box(session, _box(
        "urn:anu:box:programme-retrieval-a",
        f"{src.capability_id}@1.0.0",
        "programme.retrieve",
        "python-local",
        "builtin://map-fields",
        {"mapping": {"programme_id": "programme_code", "title": "title"}},
    ))
    add_smart_box(session, _box(
        "urn:anu:box:programme-summary",
        f"{dst.capability_id}@1.0.0",
        "programme.summarize",
        "python-local",
        "builtin://map-fields",
        {"mapping": {"programme_id": "programme_id", "summary": "title"}},
    ))
    return src, dst


def test_compatibility_plan_wire_and_assembly(session):
    src, dst = _seed_direct_pair(session)
    req = CompatibilityCheckRequest(
        from_capability_ref=f"{src.capability_id}@1.0.0",
        from_operation="programme.retrieve",
        to_capability_ref=f"{dst.capability_id}@1.0.0",
        to_operation="programme.summarize",
    )
    check = evaluate_compatibility(session, req)
    assert check.compatible is True
    assert check.direct is True
    assert check.evidence_id

    plan = plan_connection(session, ConnectionPlanRequest(**req.model_dump(), provenance_ref=PROV))
    assert plan.compatibility_evidence
    assert plan.transformation_refs == []
    assert plan.adapter_refs == []

    wire = execute_wire(session, SmartWireExecutionRequest(
        plan_ref=f"{plan.plan_id}@{plan.version}",
        payload={"programme_id": "BSC-CS", "title": "Computer Science"},
        trace_id="trace-direct",
    ))
    assert wire.status == "SUCCEEDED"
    assert wire.output_payload == {"programme_id": "BSC-CS", "summary": "Computer Science"}
    assert {t.step for t in wire.traces} >= {"policy", "security", "route", "contract_validation"}

    assembly = AssemblyDefinition(
        assembly_id="urn:anu:assembly:programme-readable-summary",
        name="Programme readable summary",
        description="Reference SBBS composition",
        owner_ref=OWNER,
        version="1.0.0",
        capability_refs=[f"{src.capability_id}@1.0.0", f"{dst.capability_id}@1.0.0"],
        connection_plan_refs=[f"{plan.plan_id}@{plan.version}"],
        effective_period=EffectivePeriod(valid_from=NOW),
        provenance_ref=PROV,
    )
    add_assembly(session, assembly)
    result = execute_assembly(session, AssemblyExecutionRequest(
        assembly_ref=f"{assembly.assembly_id}@1.0.0",
        input_payload={"programme_code": "BSC-CS", "title": "Computer Science"},
        trace_id="trace-assembly",
    ))
    assert result.status == "SUCCEEDED"
    assert result.final_payload["summary"] == "Computer Science"


def test_transform_and_adapter_are_declarative_and_required(session):
    _provenance(session)
    src = _capability(
        "urn:anu:capability:legacy-programme",
        "legacy.read",
        ["urn:anu:semantic:query"],
        ["urn:anu:semantic:programme-record"],
        ["urn:anu:contract:legacy-query.v1"],
        ["urn:anu:contract:legacy-programme.v1"],
    )
    dst = _capability(
        "urn:anu:capability:canonical-programme",
        "programme.accept",
        ["urn:anu:semantic:programme-record"],
        ["urn:anu:semantic:programme-record"],
        ["urn:anu:contract:canonical-programme.v1"],
        ["urn:anu:contract:canonical-programme.v1"],
    )
    add_capability(session, src); add_capability(session, dst)
    add_smart_box(session, _box("urn:anu:box:legacy-programme", f"{src.capability_id}@1.0.0", "legacy.read", "legacy-rpc", "builtin://identity"))
    add_smart_box(session, _box("urn:anu:box:canonical-programme", f"{dst.capability_id}@1.0.0", "programme.accept", "python-local", "builtin://identity"))

    request = CompatibilityCheckRequest(
        from_capability_ref=f"{src.capability_id}@1.0.0",
        from_operation="legacy.read",
        to_capability_ref=f"{dst.capability_id}@1.0.0",
        to_operation="programme.accept",
    )
    failed = evaluate_compatibility(session, request)
    assert failed.compatible is False

    transform = TransformDefinition(
        transform_id="urn:anu:transform:legacy-to-canonical-programme",
        version="1.0.0",
        name="Legacy to canonical programme",
        owner_ref=OWNER,
        from_contract_ref="urn:anu:contract:legacy-programme.v1",
        to_contract_ref="urn:anu:contract:canonical-programme.v1",
        mapping={"programme_id": "legacy_id", "title": "legacy_title"},
        semantic_preservation=["urn:anu:semantic:programme-record"],
        effective_period=EffectivePeriod(valid_from=NOW),
        provenance_ref=PROV,
    )
    adapter = AdapterDefinition(
        adapter_id="urn:anu:adapter:legacy-rpc-to-local",
        version="1.0.0",
        name="Legacy RPC bridge",
        owner_ref=OWNER,
        source_runtime_type="legacy-rpc",
        target_runtime_type="python-local",
        capability_scope=[f"{src.capability_id}@1.0.0", f"{dst.capability_id}@1.0.0"],
        effective_period=EffectivePeriod(valid_from=NOW),
        provenance_ref=PROV,
    )
    add_transform(session, transform); add_adapter(session, adapter)
    passed = evaluate_compatibility(session, request)
    assert passed.compatible is True
    assert passed.direct is False
    assert passed.required_transformation_refs == [f"{transform.transform_id}@1.0.0"]
    assert passed.required_adapter_refs == [f"{adapter.adapter_id}@1.0.0"]

    plan = plan_connection(session, ConnectionPlanRequest(**request.model_dump(), provenance_ref=PROV))
    result = execute_wire(session, SmartWireExecutionRequest(
        plan_ref=f"{plan.plan_id}@1.0.0",
        payload={"legacy_id": "PRG-01", "legacy_title": "Computing"},
        trace_id="trace-transform",
    ))
    assert result.output_payload == {"programme_id": "PRG-01", "title": "Computing"}
    assert any(t.step == "transform" for t in result.traces)
    assert any(t.step == "adapter" for t in result.traces)


def test_policy_security_and_permission_gate_fail_closed(session):
    _provenance(session)
    src = _capability("urn:anu:capability:source", "source.emit", [], ["urn:anu:semantic:evidence"], [], ["urn:anu:contract:evidence.v1"])
    dst = _capability(
        "urn:anu:capability:evidence-capture", "evidence.capture",
        ["urn:anu:semantic:evidence"], ["urn:anu:semantic:evidence"],
        ["urn:anu:contract:evidence.v1"], ["urn:anu:contract:evidence.v1"],
        permissions=["evidence.write"], security=["INTERNAL"], policies=["urn:anu:policy:evidence-capture@1.0.0"],
    )
    add_capability(session, src); add_capability(session, dst)
    add_smart_box(session, _box("urn:anu:box:source", f"{src.capability_id}@1.0.0", "source.emit", "python-local", "builtin://identity"))
    add_smart_box(session, _box("urn:anu:box:evidence", f"{dst.capability_id}@1.0.0", "evidence.capture", "python-local", "builtin://identity"))
    base = dict(from_capability_ref=f"{src.capability_id}@1.0.0", from_operation="source.emit", to_capability_ref=f"{dst.capability_id}@1.0.0", to_operation="evidence.capture")
    denied = evaluate_compatibility(session, CompatibilityCheckRequest(**base))
    assert denied.compatible is False
    context = CompatibilityContext(granted_permissions=["evidence.write"], security_tags=["INTERNAL"], satisfied_policy_refs=["urn:anu:policy:evidence-capture@1.0.0"])
    plan = plan_connection(session, ConnectionPlanRequest(**base, context=context, provenance_ref=PROV))
    with pytest.raises(DomainValidationError) as exc:
        execute_wire(session, SmartWireExecutionRequest(plan_ref=f"{plan.plan_id}@1.0.0", payload={"evidence": "x"}, trace_id="deny"))
    assert "WIRE_POLICY_GATE_DENY" in exc.value.reason_codes
    ok = execute_wire(session, SmartWireExecutionRequest(plan_ref=f"{plan.plan_id}@1.0.0", payload={"evidence": "x"}, trace_id="allow", context=context))
    assert ok.status == "SUCCEEDED"


def test_provider_replacement_does_not_break_consumer_contract(session):
    src, dst = _seed_direct_pair(session)
    cap_ref = f"{src.capability_id}@1.0.0"
    add_smart_box(session, _box(
        "urn:anu:box:programme-retrieval-b", cap_ref, "programme.retrieve", "python-local", "builtin://map-fields",
        {"mapping": {"programme_id": "programme_code", "title": "title"}},
    ))
    base = dict(from_capability_ref=cap_ref, from_operation="programme.retrieve", to_capability_ref=f"{dst.capability_id}@1.0.0", to_operation="programme.summarize", provenance_ref=PROV)
    plan_a = plan_connection(session, ConnectionPlanRequest(**base, from_box_ref="urn:anu:box:programme-retrieval-a@1.0.0"))
    plan_b = plan_connection(session, ConnectionPlanRequest(**base, from_box_ref="urn:anu:box:programme-retrieval-b@1.0.0"))
    for name, plan in [("a", plan_a), ("b", plan_b)]:
        assembly = AssemblyDefinition(
            assembly_id=f"urn:anu:assembly:provider-swap-{name}", name="provider swap", description="provider replacement proof",
            owner_ref=OWNER, version="1.0.0", capability_refs=[cap_ref, f"{dst.capability_id}@1.0.0"],
            connection_plan_refs=[f"{plan.plan_id}@1.0.0"], effective_period=EffectivePeriod(valid_from=NOW), provenance_ref=PROV,
        )
        add_assembly(session, assembly)
        output = execute_assembly(session, AssemblyExecutionRequest(
            assembly_ref=f"{assembly.assembly_id}@1.0.0", input_payload={"programme_code": "P1", "title": "Same Contract"}, trace_id=f"swap-{name}"))
        assert output.final_payload == {"programme_id": "P1", "summary": "Same Contract"}


def test_write_box_studio_discovers_before_build_and_promotes_new_capability(session):
    _provenance(session)
    existing = _capability(
        "urn:anu:capability:text-source", "text.emit", [], ["urn:anu:semantic:text"], [], ["urn:anu:contract:text.v1"]
    )
    add_capability(session, existing)
    add_smart_box(session, _box("urn:anu:box:text-source", f"{existing.capability_id}@1.0.0", "text.emit", "python-local", "builtin://identity"))

    new_cap = _capability(
        "urn:anu:capability:text-normalize", "text.normalize", ["urn:anu:semantic:text"], ["urn:anu:semantic:text"], ["urn:anu:contract:text.v1"], ["urn:anu:contract:text.v1"]
    )
    new_box = _box("urn:anu:box:text-normalize", f"{new_cap.capability_id}@1.0.0", "text.normalize", "python-local", "builtin://identity")
    proposal = propose_write_box(session, WriteBoxProposalRequest(
        intent="Normalize a text artifact without changing institutional semantics",
        actor_ref="urn:anu:human:capability-owner",
        capability=new_cap,
        smart_box=new_box,
        specification="Input text is returned in canonical text contract; no authority or policy mutation.",
        knowledge_refs=["urn:anu:knowledge:text-normalization"],
        rule_refs=["urn:anu:rule:text-preservation"],
        examples=[{"input": {"text": "abc"}, "output": {"text": "abc"}}],
        provenance_ref=PROV,
    ))
    assert proposal.recommended_action == "WRITE_BOX"
    assert proposal.architecture_audit.passed is True
    assert proposal.stage == "VERIFIED"
    promoted = promote_write_box(session, proposal.candidate_id, "urn:anu:human:capability-owner")
    assert promoted.capability_ref == f"{new_cap.capability_id}@1.0.0"
    discovery = discover_capabilities(session, CapabilityDiscoveryQuery(operation_id="text.normalize"))
    assert [h.capability_ref for h in discovery.hits] == [promoted.capability_ref]

    plan = plan_connection(session, ConnectionPlanRequest(
        from_capability_ref=f"{existing.capability_id}@1.0.0", from_operation="text.emit",
        to_capability_ref=promoted.capability_ref, to_operation="text.normalize", provenance_ref=PROV,
    ))
    assembly = AssemblyDefinition(
        assembly_id="urn:anu:assembly:text-normalization", name="Text normalization", description="Write Box composition proof",
        owner_ref=OWNER, version="1.0.0", capability_refs=[f"{existing.capability_id}@1.0.0", promoted.capability_ref],
        connection_plan_refs=[f"{plan.plan_id}@1.0.0"], effective_period=EffectivePeriod(valid_from=NOW), provenance_ref=PROV,
    )
    add_assembly(session, assembly)
    output = execute_assembly(session, AssemblyExecutionRequest(assembly_ref=f"{assembly.assembly_id}@1.0.0", input_payload={"text": "hello"}, trace_id="write-box-compose"))
    assert output.final_payload == {"text": "hello"}


def test_write_box_audit_blocks_incomplete_candidate(session):
    _provenance(session)
    cap = _capability("urn:anu:capability:unsafe-empty", "unsafe.run", [], ["urn:anu:semantic:x"], [], ["urn:anu:contract:x.v1"])
    box = _box("urn:anu:box:unsafe-empty", f"{cap.capability_id}@1.0.0", "unsafe.run", "python-local", "builtin://identity")
    proposal = propose_write_box(session, WriteBoxProposalRequest(
        intent="Incomplete candidate", actor_ref="urn:anu:human:owner", capability=cap, smart_box=box,
        specification="", knowledge_refs=[], rule_refs=[], examples=[], provenance_ref=PROV,
    ))
    assert proposal.architecture_audit.passed is False
    assert proposal.stage == "DRAFT"
    with pytest.raises(DomainValidationError):
        promote_write_box(session, proposal.candidate_id, "urn:anu:human:owner")
