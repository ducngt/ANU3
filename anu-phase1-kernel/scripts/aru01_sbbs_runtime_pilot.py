from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy.orm import sessionmaker

from anu_kernel.capability_contracts import CapabilityContract, CapabilityDiscoveryQuery, CapabilityOperation, SmartBoxManifest, SmartBoxOperationBinding
from anu_kernel.capability_repository import add_capability, add_smart_box
from anu_kernel.capability_services import discover_capabilities
from anu_kernel.contracts import EffectivePeriod, ProvenanceRecordContract
from anu_kernel.db import make_engine
from anu_kernel.repository import add_provenance
from anu_kernel.sbbs_runtime_contracts import AdapterDefinition, AssemblyDefinition, AssemblyExecutionRequest, ConnectionPlanRequest, SmartWireExecutionRequest, TransformDefinition, WriteBoxProposalRequest
from anu_kernel.sbbs_runtime_repository import add_adapter, add_assembly, add_transform
from anu_kernel.sbbs_runtime_services import execute_assembly, execute_wire, plan_connection, promote_write_box, propose_write_box

NOW = datetime(2026, 9, 25, tzinfo=timezone.utc)
PROV = "urn:anu:provenance:aru01-p3-runtime"
OWNER = "urn:anu:org:aru-01"


def cap(cid, opid, ins, outs, in_contracts, out_contracts):
    return CapabilityContract(
        capability_id=cid, name=cid.rsplit(":",1)[-1], description="ARU-01 P3 runtime reference capability",
        owner_ref=OWNER, domain="learning-curriculum", version="1.0.0",
        operations=[CapabilityOperation(operation_id=opid, purpose="ARU-01 pilot", input_semantics=ins, output_semantics=outs, input_contract_refs=in_contracts, output_contract_refs=out_contracts)],
        effective_period=EffectivePeriod(valid_from=NOW), provenance_ref=PROV,
    )


def box(bid, cref, opid, config):
    return SmartBoxManifest(
        box_id=bid, capability_ref=cref, box_version="1.0.0", provider_ref=f"urn:anu:provider:{bid.rsplit(':',1)[-1]}",
        runtime_type="python-local", operation_bindings=[SmartBoxOperationBinding(operation_id=opid, handler_ref="builtin://map-fields", binding_config=config)],
        adapter_boundary=f"urn:anu:adapter-boundary:{bid.rsplit(':',1)[-1]}", effective_period=EffectivePeriod(valid_from=NOW), provenance_ref=PROV,
    )


def run_pilot(database_url: str) -> dict:
    Session = sessionmaker(bind=make_engine(database_url), future=True)
    with Session() as session:
        add_provenance(session, ProvenanceRecordContract(provenance_id=PROV, entity_ref="urn:anu:work:aru01-p3-runtime", actor_ref="urn:anu:agent:ai-factory", effective_time=NOW, recorded_time=NOW))
        source = cap("urn:anu:capability:programme-retrieval", "programme.retrieve", ["urn:anu:semantic:programme-query"], ["urn:anu:semantic:programme-record"], ["urn:anu:contract:programme-query.v1"], ["urn:anu:contract:programme-record.v1"])
        add_capability(session, source)
        add_smart_box(session, box("urn:anu:box:programme-retrieval-a", f"{source.capability_id}@1.0.0", "programme.retrieve", {"mapping":{"programme_id":"programme_code","title":"title"}}))
        add_smart_box(session, box("urn:anu:box:programme-retrieval-b", f"{source.capability_id}@1.0.0", "programme.retrieve", {"mapping":{"programme_id":"programme_code","title":"title"}}))

        summary = cap("urn:anu:capability:programme-summary", "programme.summarize", ["urn:anu:semantic:programme-record"], ["urn:anu:semantic:programme-summary"], ["urn:anu:contract:programme-record.v1"], ["urn:anu:contract:programme-summary.v1"])
        summary_box = box("urn:anu:box:programme-summary", f"{summary.capability_id}@1.0.0", "programme.summarize", {"mapping":{"programme_id":"programme_id","summary":"title"}})
        proposal = propose_write_box(session, WriteBoxProposalRequest(
            intent="Create programme summary capability for ARU-01 pilot",
            actor_ref="urn:anu:human:aru01-capability-owner", capability=summary, smart_box=summary_box,
            specification="Summarize a programme record without changing its authoritative source or authority.",
            knowledge_refs=["urn:anu:knowledge:programme-semantics"], rule_refs=["urn:anu:rule:programme-summary"],
            examples=[{"input":{"programme_id":"P1","title":"CS"},"output":{"programme_id":"P1","summary":"CS"}}], provenance_ref=PROV,
        ))
        promoted = promote_write_box(session, proposal.candidate_id, "urn:anu:human:aru01-capability-owner")
        discovery = discover_capabilities(session, CapabilityDiscoveryQuery(operation_id="programme.summarize"))

        outputs = []
        plans = []
        assembly_refs = []
        for suffix in ["a", "b"]:
            plan = plan_connection(session, ConnectionPlanRequest(
                from_capability_ref=f"{source.capability_id}@1.0.0", from_operation="programme.retrieve",
                to_capability_ref=promoted.capability_ref, to_operation="programme.summarize",
                from_box_ref=f"urn:anu:box:programme-retrieval-{suffix}@1.0.0", provenance_ref=PROV,
            ))
            plans.append(plan)
            assembly = AssemblyDefinition(
                assembly_id=f"urn:anu:assembly:aru01-programme-summary-{suffix}", name="ARU-01 Programme Summary",
                description="P3 capability composition and provider replacement proof", owner_ref=OWNER, version="1.0.0",
                capability_refs=[f"{source.capability_id}@1.0.0", promoted.capability_ref], connection_plan_refs=[f"{plan.plan_id}@1.0.0"],
                effective_period=EffectivePeriod(valid_from=NOW), provenance_ref=PROV,
            )
            add_assembly(session, assembly)
            assembly_refs.append(f"{assembly.assembly_id}@1.0.0")
            result = execute_assembly(session, AssemblyExecutionRequest(
                assembly_ref=f"{assembly.assembly_id}@1.0.0", input_payload={"programme_code":"BSC-CS","title":"Computer Science"}, trace_id=f"aru01-p3-{suffix}"))
            outputs.append(result.final_payload)

        legacy = cap("urn:anu:capability:legacy-programme", "legacy.read", [], ["urn:anu:semantic:programme-record"], [], ["urn:anu:contract:legacy-programme.v1"])
        add_capability(session, legacy)
        legacy_box = SmartBoxManifest(
            box_id="urn:anu:box:legacy-programme", capability_ref=f"{legacy.capability_id}@1.0.0", box_version="1.0.0",
            provider_ref="urn:anu:provider:legacy-programme", runtime_type="legacy-rpc",
            operation_bindings=[SmartBoxOperationBinding(operation_id="legacy.read", handler_ref="builtin://identity")],
            adapter_boundary="urn:anu:adapter-boundary:legacy-programme", effective_period=EffectivePeriod(valid_from=NOW), provenance_ref=PROV,
        )
        add_smart_box(session, legacy_box)
        transform = TransformDefinition(
            transform_id="urn:anu:transform:legacy-programme-to-canonical", version="1.0.0", name="Legacy programme to canonical", owner_ref=OWNER,
            from_contract_ref="urn:anu:contract:legacy-programme.v1", to_contract_ref="urn:anu:contract:programme-record.v1",
            mapping={"programme_id":"legacy_id","title":"legacy_title"}, semantic_preservation=["urn:anu:semantic:programme-record"],
            effective_period=EffectivePeriod(valid_from=NOW), provenance_ref=PROV,
        )
        adapter = AdapterDefinition(
            adapter_id="urn:anu:adapter:legacy-rpc-to-python-local", version="1.0.0", name="Legacy RPC bridge", owner_ref=OWNER,
            source_runtime_type="legacy-rpc", target_runtime_type="python-local", capability_scope=[f"{legacy.capability_id}@1.0.0", promoted.capability_ref],
            effective_period=EffectivePeriod(valid_from=NOW), provenance_ref=PROV,
        )
        add_transform(session, transform); add_adapter(session, adapter)
        legacy_plan = plan_connection(session, ConnectionPlanRequest(
            from_capability_ref=f"{legacy.capability_id}@1.0.0", from_operation="legacy.read", to_capability_ref=promoted.capability_ref,
            to_operation="programme.summarize", provenance_ref=PROV,
        ))
        legacy_wire = execute_wire(session, SmartWireExecutionRequest(
            plan_ref=f"{legacy_plan.plan_id}@1.0.0", payload={"legacy_id":"BSC-CS","legacy_title":"Computer Science"}, trace_id="aru01-p3-legacy"))

        passed = (
            proposal.architecture_audit.passed
            and proposal.recommended_action == "WRITE_BOX"
            and promoted.capability_ref in [h.capability_ref for h in discovery.hits]
            and len(plans) == 2
            and all(p.compatibility_evidence for p in plans)
            and outputs[0] == outputs[1] == {"programme_id":"BSC-CS","summary":"Computer Science"}
            and legacy_plan.transformation_refs == ["urn:anu:transform:legacy-programme-to-canonical@1.0.0"]
            and legacy_plan.adapter_refs == ["urn:anu:adapter:legacy-rpc-to-python-local@1.0.0"]
            and legacy_wire.output_payload == {"programme_id":"BSC-CS","summary":"Computer Science"}
        )
        return {
            "pass": passed,
            "write_box_action": proposal.recommended_action,
            "architecture_audit_pass": proposal.architecture_audit.passed,
            "promoted_capability_ref": promoted.capability_ref,
            "discovered": [h.capability_ref for h in discovery.hits],
            "connection_plans": [f"{p.plan_id}@{p.version}" for p in plans],
            "assembly_refs": assembly_refs,
            "provider_outputs": outputs,
            "provider_replacement_preserved_contract": outputs[0] == outputs[1],
            "legacy_transform_adapter_plan": f"{legacy_plan.plan_id}@1.0.0",
            "legacy_transform_refs": legacy_plan.transformation_refs,
            "legacy_adapter_refs": legacy_plan.adapter_refs,
            "legacy_wire_output": legacy_wire.output_payload,
        }
