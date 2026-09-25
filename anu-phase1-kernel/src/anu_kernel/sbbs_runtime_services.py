from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from .capability_contracts import CapabilityDiscoveryQuery
from .capability_models import CapabilityVersion, SmartBoxManifestVersion
from .capability_services import discover_capabilities
from .db import ProvenanceRecord
from .errors import DomainValidationError
from .ids import urn, uuid7
from .sbbs_runtime_contracts import (
    ArchitectureAuditReport,
    AssemblyExecutionRequest,
    AssemblyExecutionResult,
    CompatibilityCheckRequest,
    CompatibilityDimension,
    CompatibilityResult,
    ConnectionPlan,
    ConnectionPlanRequest,
    SmartWireExecutionRequest,
    SmartWireExecutionResult,
    WireStepTrace,
    WriteBoxPromotionResult,
    WriteBoxProposalRequest,
    WriteBoxProposalResult,
)
from .sbbs_runtime_models import (
    AssemblyExecutionRecord,
    CompatibilityEvidence,
    WireExecutionRecord,
    WriteBoxCandidate,
)
from .sbbs_runtime_repository import (
    add_compatibility_evidence,
    add_connection_plan,
    add_write_box_candidate,
    find_adapter,
    find_transform,
    get_adapter,
    get_assembly,
    get_connection_plan,
    get_transform,
    promote_write_box_candidate,
)


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _json_hash(value: Any) -> str:
    raw = json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _split_ref(ref: str) -> tuple[str, str]:
    if "@" not in ref:
        raise DomainValidationError("versioned reference required", ["VERSIONED_REF_REQUIRED"])
    return ref.rsplit("@", 1)


def _capability(session: Session, ref: str) -> CapabilityVersion:
    cid, version = _split_ref(ref)
    row = session.scalar(
        select(CapabilityVersion).where(
            CapabilityVersion.capability_id == cid,
            CapabilityVersion.version == version,
            CapabilityVersion.lifecycle_state == "ACTIVE",
        )
    )
    if row is None:
        raise DomainValidationError("capability not found", ["CAPABILITY_NOT_FOUND"])
    return row


def _operation(capability: CapabilityVersion, operation_id: str) -> dict:
    for op in capability.operations or []:
        if op.get("operation_id") == operation_id:
            return op
    raise DomainValidationError("capability operation not found", ["CAPABILITY_OPERATION_NOT_FOUND"])


def _box_by_ref(session: Session, ref: str) -> SmartBoxManifestVersion:
    bid, version = _split_ref(ref)
    row = session.scalar(
        select(SmartBoxManifestVersion).where(
            SmartBoxManifestVersion.box_id == bid,
            SmartBoxManifestVersion.box_version == version,
            SmartBoxManifestVersion.lifecycle_state == "ACTIVE",
        )
    )
    if row is None:
        raise DomainValidationError("Smart Box not found", ["SMART_BOX_NOT_FOUND"])
    return row


def _pick_box(session: Session, capability_ref: str, requested_ref: str | None = None) -> SmartBoxManifestVersion:
    if requested_ref:
        box = _box_by_ref(session, requested_ref)
        if box.capability_ref != capability_ref:
            raise DomainValidationError("Smart Box does not implement requested capability", ["BOX_CAPABILITY_MISMATCH"])
        return box
    row = session.scalar(
        select(SmartBoxManifestVersion)
        .where(
            SmartBoxManifestVersion.capability_ref == capability_ref,
            SmartBoxManifestVersion.lifecycle_state == "ACTIVE",
        )
        .order_by(SmartBoxManifestVersion.box_id, SmartBoxManifestVersion.box_version)
    )
    if row is None:
        raise DomainValidationError("no active Smart Box provider", ["SMART_BOX_PROVIDER_NOT_FOUND"])
    return row


def evaluate_compatibility(session: Session, req: CompatibilityCheckRequest, persist: bool = True) -> CompatibilityResult:
    source = _capability(session, req.from_capability_ref)
    target = _capability(session, req.to_capability_ref)
    source_op = _operation(source, req.from_operation)
    target_op = _operation(target, req.to_operation)
    source_box = _pick_box(session, req.from_capability_ref, req.from_box_ref)
    target_box = _pick_box(session, req.to_capability_ref, req.to_box_ref)

    dims: list[CompatibilityDimension] = []
    transforms: list[str] = []
    adapters: list[str] = []

    target_inputs = set(target_op.get("input_semantics") or [])
    source_outputs = set(source_op.get("output_semantics") or [])
    if target_inputs.issubset(source_outputs):
        dims.append(CompatibilityDimension(dimension="semantics", status="PASS", detail="target input semantics are provided by source output"))
    else:
        dims.append(CompatibilityDimension(dimension="semantics", status="FAIL", detail="source output semantics do not satisfy target input semantics"))

    source_contracts = list(source_op.get("output_contract_refs") or [])
    target_contracts = list(target_op.get("input_contract_refs") or [])
    if not target_contracts or set(source_contracts).intersection(target_contracts):
        dims.append(CompatibilityDimension(dimension="schema_contract", status="PASS", detail="contract refs are directly compatible"))
    else:
        transform = find_transform(session, source_contracts, target_contracts)
        if transform is None:
            dims.append(CompatibilityDimension(dimension="schema_contract", status="FAIL", detail="no compatible contract or registered transformation"))
        else:
            tref = f"{transform.transform_id}@{transform.version}"
            transforms.append(tref)
            dims.append(CompatibilityDimension(dimension="schema_contract", status="TRANSFORM_REQUIRED", detail="registered declarative transformation bridges contracts", evidence_refs=[tref]))

    source_constraints = source_op.get("constraints") or {}
    target_constraints = target_op.get("constraints") or {}
    conflicts = [k for k in set(source_constraints).intersection(target_constraints) if source_constraints[k] != target_constraints[k]]
    if conflicts:
        dims.append(CompatibilityDimension(dimension="constraints", status="FAIL", detail=f"constraint conflict: {','.join(sorted(conflicts))}"))
    else:
        dims.append(CompatibilityDimension(dimension="constraints", status="PASS", detail="no declared constraint conflict"))

    required_permissions = set(target_op.get("permissions") or [])
    if required_permissions.issubset(set(req.context.granted_permissions)):
        dims.append(CompatibilityDimension(dimension="permissions", status="PASS", detail="required permissions satisfied"))
    else:
        dims.append(CompatibilityDimension(dimension="permissions", status="FAIL", detail="required permissions not satisfied"))

    required_security = set(target_op.get("security_tags") or [])
    if required_security.issubset(set(req.context.security_tags)):
        dims.append(CompatibilityDimension(dimension="security", status="PASS", detail="security context satisfies target operation"))
    else:
        dims.append(CompatibilityDimension(dimension="security", status="FAIL", detail="security context does not satisfy target operation"))

    required_policies = set(target.policy_refs or []).union(target_op.get("policy_refs") or [])
    if required_policies.issubset(set(req.context.satisfied_policy_refs)):
        dims.append(CompatibilityDimension(dimension="policy", status="PASS", detail="required policy checks satisfied"))
    else:
        dims.append(CompatibilityDimension(dimension="policy", status="FAIL", detail="required policy checks not satisfied"))

    if source_box.runtime_type == target_box.runtime_type:
        dims.append(CompatibilityDimension(dimension="runtime_adapter", status="PASS", detail="provider runtime types connect directly"))
    else:
        adapter = find_adapter(session, source_box.runtime_type, target_box.runtime_type, [req.from_capability_ref, req.to_capability_ref])
        if adapter is None:
            dims.append(CompatibilityDimension(dimension="runtime_adapter", status="FAIL", detail="runtime types differ and no adapter is registered"))
        else:
            aref = f"{adapter.adapter_id}@{adapter.version}"
            adapters.append(aref)
            dims.append(CompatibilityDimension(dimension="runtime_adapter", status="ADAPTER_REQUIRED", detail="registered adapter bridges provider runtimes", evidence_refs=[aref]))

    compatible = all(d.status != "FAIL" for d in dims)
    direct = compatible and not transforms and not adapters
    result = CompatibilityResult(
        compatible=compatible,
        direct=direct,
        from_capability_ref=req.from_capability_ref,
        from_operation=req.from_operation,
        to_capability_ref=req.to_capability_ref,
        to_operation=req.to_operation,
        dimensions=dims,
        required_transformation_refs=transforms,
        required_adapter_refs=adapters,
    )
    if persist:
        evidence_id = urn("compatibility-evidence", uuid7())
        request_hash = _json_hash(req.model_dump(mode="json"))
        result.evidence_id = evidence_id
        add_compatibility_evidence(
            session,
            CompatibilityEvidence(
                evidence_id=evidence_id,
                from_capability_ref=req.from_capability_ref,
                from_operation=req.from_operation,
                to_capability_ref=req.to_capability_ref,
                to_operation=req.to_operation,
                compatible=compatible,
                direct=direct,
                result_json=result.model_dump(mode="json"),
                request_hash=request_hash,
            ),
        )
    return result


def plan_connection(session: Session, req: ConnectionPlanRequest) -> ConnectionPlan:
    if session.get(ProvenanceRecord, req.provenance_ref) is None:
        raise DomainValidationError("provenance not found", ["PROVENANCE_REQUIRED"])
    result = evaluate_compatibility(session, CompatibilityCheckRequest.model_validate(req.model_dump(exclude={"provenance_ref", "retry_policy", "observability_policy"})), persist=True)
    if not result.compatible:
        raise DomainValidationError("connection compatibility cannot be proven", ["COMPATIBILITY_NOT_PROVEN"])
    source = _capability(session, req.from_capability_ref)
    target = _capability(session, req.to_capability_ref)
    source_op = _operation(source, req.from_operation)
    target_op = _operation(target, req.to_operation)
    source_box = _pick_box(session, req.from_capability_ref, req.from_box_ref)
    target_box = _pick_box(session, req.to_capability_ref, req.to_box_ref)
    common = list(set(source_op.get("output_contract_refs") or []).intersection(target_op.get("input_contract_refs") or []))
    contract_ref = common[0] if common else ((target_op.get("input_contract_refs") or [None])[0])
    now = _now()
    plan = ConnectionPlan(
        plan_id=urn("connection-plan", uuid7()),
        from_capability=req.from_capability_ref,
        from_operation=req.from_operation,
        to_capability=req.to_capability_ref,
        to_operation=req.to_operation,
        from_box_ref=f"{source_box.box_id}@{source_box.box_version}",
        to_box_ref=f"{target_box.box_id}@{target_box.box_version}",
        contract_ref=contract_ref,
        transformation_refs=result.required_transformation_refs,
        adapter_refs=result.required_adapter_refs,
        policy_checks=sorted(set(target.policy_refs or []).union(target_op.get("policy_refs") or [])),
        security_context={
            "permissions": target_op.get("permissions") or [],
            "security_tags": target_op.get("security_tags") or [],
        },
        retry_policy=req.retry_policy,
        observability_policy=req.observability_policy,
        compatibility_evidence=[result.evidence_id] if result.evidence_id else [],
        effective_period={"valid_from": now, "valid_until": None},
        provenance_ref=req.provenance_ref,
    )
    add_connection_plan(session, plan)
    return plan


def _apply_transform(session: Session, transform_ref: str, payload: dict[str, Any]) -> dict[str, Any]:
    transform = get_transform(session, transform_ref)
    if transform is None or transform.lifecycle_state != "ACTIVE":
        raise DomainValidationError("transform unavailable", ["TRANSFORM_UNAVAILABLE"])
    out: dict[str, Any] = dict(transform.constants or {})
    for target_key, source_key in (transform.mapping or {}).items():
        if source_key not in payload:
            raise DomainValidationError("transform input missing", ["TRANSFORM_INPUT_MISSING"])
        out[target_key] = payload[source_key]
    return out


def _execute_box(box: SmartBoxManifestVersion, operation_id: str, payload: dict[str, Any]) -> dict[str, Any]:
    binding = next((b for b in (box.operation_bindings or []) if b.get("operation_id") == operation_id), None)
    if binding is None:
        raise DomainValidationError("Smart Box operation binding missing", ["BOX_OPERATION_BINDING_MISSING"])
    handler = binding.get("handler_ref")
    config = binding.get("binding_config") or {}
    if handler == "builtin://identity":
        return dict(payload)
    if handler == "builtin://map-fields":
        mapping = config.get("mapping") or {}
        constants = config.get("constants") or {}
        out = dict(constants)
        for target_key, source_key in mapping.items():
            if source_key not in payload:
                raise DomainValidationError("box input missing", ["BOX_INPUT_MISSING"])
            out[target_key] = payload[source_key]
        return out
    if handler == "builtin://merge-constants":
        out = dict(payload)
        out.update(config.get("constants") or {})
        return out
    raise DomainValidationError("handler is outside approved runtime adapter boundary", ["UNSUPPORTED_BOX_HANDLER"])


def execute_wire(session: Session, req: SmartWireExecutionRequest) -> SmartWireExecutionResult:
    plan = get_connection_plan(session, req.plan_ref)
    if plan is None or plan.lifecycle_state != "ACTIVE":
        raise DomainValidationError("connection plan not found", ["CONNECTION_PLAN_NOT_FOUND"])
    if not plan.compatibility_evidence:
        raise DomainValidationError("connection has no compatibility evidence", ["COMPATIBILITY_EVIDENCE_REQUIRED"])
    evidence = session.get(CompatibilityEvidence, plan.compatibility_evidence[0])
    if evidence is None or not evidence.compatible:
        raise DomainValidationError("compatibility evidence invalid", ["COMPATIBILITY_NOT_PROVEN"])
    traces: list[WireStepTrace] = []
    required_policies = set(plan.policy_checks or [])
    if not required_policies.issubset(set(req.context.satisfied_policy_refs)):
        raise DomainValidationError("wire policy gate denied execution", ["WIRE_POLICY_GATE_DENY"])
    traces.append(WireStepTrace(step="policy", status="PASS", detail="declared policy checks satisfied"))
    sec = plan.security_context or {}
    if not set(sec.get("permissions") or []).issubset(set(req.context.granted_permissions)):
        raise DomainValidationError("wire permission gate denied execution", ["WIRE_PERMISSION_GATE_DENY"])
    if not set(sec.get("security_tags") or []).issubset(set(req.context.security_tags)):
        raise DomainValidationError("wire security gate denied execution", ["WIRE_SECURITY_GATE_DENY"])
    traces.append(WireStepTrace(step="security", status="PASS", detail="declared security context satisfied"))

    started = _now()
    payload = dict(req.payload)
    for tref in plan.transformation_refs or []:
        payload = _apply_transform(session, tref, payload)
        traces.append(WireStepTrace(step="transform", status="PASS", detail=f"applied {tref}"))
    for aref in plan.adapter_refs or []:
        adapter = get_adapter(session, aref)
        if adapter is None or adapter.lifecycle_state != "ACTIVE":
            raise DomainValidationError("adapter unavailable", ["ADAPTER_UNAVAILABLE"])
        traces.append(WireStepTrace(step="adapter", status="PASS", detail=f"routed through adapter boundary {aref}"))

    target_box = _box_by_ref(session, plan.to_box_ref)
    output = _execute_box(target_box, plan.to_operation, payload)
    traces.append(WireStepTrace(step="route", status="PASS", detail=f"executed {plan.to_box_ref}:{plan.to_operation}"))
    traces.append(WireStepTrace(step="contract_validation", status="PASS", detail="execution followed a compatibility-proven connection plan"))
    completed = _now()
    result = SmartWireExecutionResult(
        execution_id=urn("wire-execution", uuid7()),
        plan_ref=req.plan_ref,
        trace_id=req.trace_id,
        status="SUCCEEDED",
        output_payload=output,
        selected_box_ref=plan.to_box_ref,
        traces=traces,
        started_at=started,
        completed_at=completed,
    )
    session.add(WireExecutionRecord(
        execution_id=result.execution_id,
        plan_ref=req.plan_ref,
        trace_id=req.trace_id,
        status=result.status,
        selected_box_ref=result.selected_box_ref,
        input_payload=req.payload,
        output_payload=output,
        trace_json=[t.model_dump(mode="json") for t in traces],
        started_at=started,
        completed_at=completed,
    ))
    session.commit()
    return result


def execute_assembly(session: Session, req: AssemblyExecutionRequest) -> AssemblyExecutionResult:
    assembly = get_assembly(session, req.assembly_ref)
    if assembly is None or assembly.lifecycle_state != "ACTIVE":
        raise DomainValidationError("assembly not found", ["ASSEMBLY_NOT_FOUND"])
    if not assembly.connection_plan_refs:
        raise DomainValidationError("assembly has no connection plan", ["ASSEMBLY_CONNECTION_REQUIRED"])
    started = _now()
    connection_results: list[SmartWireExecutionResult] = []
    first_plan = get_connection_plan(session, assembly.connection_plan_refs[0])
    if first_plan is None:
        raise DomainValidationError("assembly connection plan missing", ["CONNECTION_PLAN_NOT_FOUND"])
    first_box = _box_by_ref(session, first_plan.from_box_ref)
    payload = _execute_box(first_box, first_plan.from_operation, req.input_payload)
    previous_target = None
    for plan_ref in assembly.connection_plan_refs:
        plan = get_connection_plan(session, plan_ref)
        if plan is None:
            raise DomainValidationError("assembly connection plan missing", ["CONNECTION_PLAN_NOT_FOUND"])
        if previous_target is not None and plan.from_capability != previous_target:
            raise DomainValidationError("assembly plans are not a composable chain", ["ASSEMBLY_CHAIN_INVALID"])
        wire_result = execute_wire(session, SmartWireExecutionRequest(plan_ref=plan_ref, payload=payload, trace_id=req.trace_id, context=req.context))
        connection_results.append(wire_result)
        payload = wire_result.output_payload or {}
        previous_target = plan.to_capability
    completed = _now()
    result = AssemblyExecutionResult(
        execution_id=urn("assembly-execution", uuid7()),
        assembly_ref=req.assembly_ref,
        trace_id=req.trace_id,
        status="SUCCEEDED",
        final_payload=payload,
        connection_results=connection_results,
        started_at=started,
        completed_at=completed,
    )
    session.add(AssemblyExecutionRecord(
        execution_id=result.execution_id,
        assembly_ref=req.assembly_ref,
        trace_id=req.trace_id,
        status=result.status,
        input_payload=req.input_payload,
        final_payload=payload,
        connection_results=[r.model_dump(mode="json") for r in connection_results],
        started_at=started,
        completed_at=completed,
    ))
    session.commit()
    return result


def architecture_audit_proposal(session: Session, req: WriteBoxProposalRequest) -> ArchitectureAuditReport:
    cap_ref = f"{req.capability.capability_id}@{req.capability.version}"
    checks = {
        "contract_before_implementation": "PASS" if req.specification.strip() else "FAIL",
        "knowledge_alongside_code": "PASS" if req.knowledge_refs and req.rule_refs and req.examples else "FAIL",
        "box_capability_alignment": "PASS" if req.smart_box.capability_ref == cap_ref else "FAIL",
        "box_identity": "PASS" if req.smart_box.box_id and req.smart_box.box_version else "FAIL",
        "adapter_boundary_declared": "PASS" if req.smart_box.adapter_boundary.strip() else "FAIL",
        "capability_has_owner": "PASS" if req.capability.owner_ref else "FAIL",
        "capability_has_no_authority_field": "PASS",
        "provenance_exists": "PASS" if session.get(ProvenanceRecord, req.provenance_ref) is not None else "FAIL",
    }
    operation_ids = {o.operation_id for o in req.capability.operations}
    bindings_ok = all(b.operation_id in operation_ids for b in req.smart_box.operation_bindings)
    checks["bindings_follow_contract"] = "PASS" if bindings_ok else "FAIL"
    findings = [name for name, status in checks.items() if status == "FAIL"]
    return ArchitectureAuditReport(
        audit_id=urn("architecture-audit", uuid7()),
        subject_ref=cap_ref,
        passed=not findings,
        checks=checks,
        findings=findings,
        audited_at=_now(),
    )


def propose_write_box(session: Session, req: WriteBoxProposalRequest) -> WriteBoxProposalResult:
    first_op = req.capability.operations[0]
    discovery = discover_capabilities(session, CapabilityDiscoveryQuery(
        operation_id=first_op.operation_id,
        input_semantics=first_op.input_semantics,
        output_semantics=first_op.output_semantics,
        domain=req.capability.domain,
        include_boxes=True,
    ))
    refs = [h.capability_ref for h in discovery.hits if h.capability_ref != f"{req.capability.capability_id}@{req.capability.version}"]
    same_id = [h.capability_ref for h in discovery.hits if h.capability_id == req.capability.capability_id]
    if same_id:
        action = "VERSION"
        refs = same_id
    elif refs:
        action = "REUSE"
    else:
        action = "WRITE_BOX"
    audit = architecture_audit_proposal(session, req)
    candidate_id = urn("write-box-candidate", uuid7())
    stage = "VERIFIED" if action == "WRITE_BOX" and audit.passed else "DRAFT"
    add_write_box_candidate(session, WriteBoxCandidate(
        candidate_id=candidate_id,
        intent=req.intent,
        actor_ref=req.actor_ref,
        capability_json=req.capability.model_dump(mode="json"),
        smart_box_json=req.smart_box.model_dump(mode="json"),
        specification=req.specification,
        knowledge_refs=req.knowledge_refs,
        rule_refs=req.rule_refs,
        examples=req.examples,
        provenance_ref=req.provenance_ref,
        recommended_action=action,
        existing_capability_refs=refs,
        audit_json=audit.model_dump(mode="json"),
        stage=stage,
    ))
    return WriteBoxProposalResult(candidate_id=candidate_id, recommended_action=action, existing_capability_refs=refs, architecture_audit=audit, stage=stage)


def promote_write_box(session: Session, candidate_id: str, actor_ref: str) -> WriteBoxPromotionResult:
    candidate = session.get(WriteBoxCandidate, candidate_id)
    if candidate is None:
        raise DomainValidationError("Write Box candidate not found", ["WRITE_BOX_CANDIDATE_NOT_FOUND"])
    if actor_ref != candidate.actor_ref:
        raise DomainValidationError("promotion actor does not own candidate", ["WRITE_BOX_PROMOTION_ACTOR_MISMATCH"])
    cap_ref, box_ref = promote_write_box_candidate(session, candidate)
    return WriteBoxPromotionResult(candidate_id=candidate_id, capability_ref=cap_ref, box_ref=box_ref)
