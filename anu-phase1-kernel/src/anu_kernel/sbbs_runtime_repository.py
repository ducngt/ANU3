from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from .capability_contracts import CapabilityContract, SmartBoxManifest
from .capability_repository import add_capability, add_smart_box
from .db import ProvenanceRecord
from .errors import DomainValidationError, RepositoryConflict
from .sbbs_runtime_contracts import AdapterDefinition, AssemblyDefinition, ConnectionPlan, TransformDefinition
from .sbbs_runtime_models import (
    AdapterVersion,
    AssemblyVersion,
    CompatibilityEvidence,
    ConnectionPlanVersion,
    TransformVersion,
    WriteBoxCandidate,
)


def _commit(session: Session, row, resource_type: str, resource_id: str):
    session.add(row)
    try:
        session.commit()
    except IntegrityError as exc:
        session.rollback()
        raise RepositoryConflict(resource_type, resource_id) from exc
    return row


def _require_provenance(session: Session, provenance_ref: str) -> None:
    if session.get(ProvenanceRecord, provenance_ref) is None:
        raise DomainValidationError("provenance not found", ["PROVENANCE_REQUIRED"])


def add_transform(session: Session, c: TransformDefinition) -> TransformVersion:
    _require_provenance(session, c.provenance_ref)
    row = TransformVersion(
        transform_id=c.transform_id,
        version=c.version,
        name=c.name,
        owner_ref=c.owner_ref,
        from_contract_ref=c.from_contract_ref,
        to_contract_ref=c.to_contract_ref,
        mapping=c.mapping,
        constants=c.constants,
        semantic_preservation=c.semantic_preservation,
        lossy=c.lossy,
        effective_from=c.effective_period.valid_from,
        effective_to=c.effective_period.valid_until,
        lifecycle_state=c.lifecycle_state.value,
        provenance_ref=c.provenance_ref,
    )
    return _commit(session, row, "transform", f"{c.transform_id}@{c.version}")


def add_adapter(session: Session, c: AdapterDefinition) -> AdapterVersion:
    _require_provenance(session, c.provenance_ref)
    row = AdapterVersion(
        adapter_id=c.adapter_id,
        version=c.version,
        name=c.name,
        owner_ref=c.owner_ref,
        source_runtime_type=c.source_runtime_type,
        target_runtime_type=c.target_runtime_type,
        capability_scope=c.capability_scope,
        configuration=c.configuration,
        effective_from=c.effective_period.valid_from,
        effective_to=c.effective_period.valid_until,
        lifecycle_state=c.lifecycle_state.value,
        provenance_ref=c.provenance_ref,
    )
    return _commit(session, row, "adapter", f"{c.adapter_id}@{c.version}")


def add_compatibility_evidence(session: Session, row: CompatibilityEvidence) -> CompatibilityEvidence:
    return _commit(session, row, "compatibility_evidence", row.evidence_id)


def add_connection_plan(session: Session, c: ConnectionPlan) -> ConnectionPlanVersion:
    _require_provenance(session, c.provenance_ref)
    row = ConnectionPlanVersion(
        plan_id=c.plan_id,
        version=c.version,
        from_capability=c.from_capability,
        from_operation=c.from_operation,
        to_capability=c.to_capability,
        to_operation=c.to_operation,
        from_box_ref=c.from_box_ref,
        to_box_ref=c.to_box_ref,
        contract_ref=c.contract_ref,
        transformation_refs=c.transformation_refs,
        adapter_refs=c.adapter_refs,
        policy_checks=c.policy_checks,
        security_context=c.security_context,
        retry_policy=c.retry_policy.model_dump(mode="json"),
        observability_policy=c.observability_policy,
        compatibility_evidence=c.compatibility_evidence,
        effective_from=c.effective_period.valid_from,
        effective_to=c.effective_period.valid_until,
        lifecycle_state=c.lifecycle_state.value,
        provenance_ref=c.provenance_ref,
    )
    return _commit(session, row, "connection_plan", f"{c.plan_id}@{c.version}")


def add_assembly(session: Session, c: AssemblyDefinition) -> AssemblyVersion:
    _require_provenance(session, c.provenance_ref)
    for plan_ref in c.connection_plan_refs:
        if get_connection_plan(session, plan_ref) is None:
            raise DomainValidationError("assembly references unknown connection plan", ["CONNECTION_PLAN_NOT_FOUND"])
    row = AssemblyVersion(
        assembly_id=c.assembly_id,
        name=c.name,
        description=c.description,
        owner_ref=c.owner_ref,
        version=c.version,
        capability_refs=c.capability_refs,
        connection_plan_refs=c.connection_plan_refs,
        human_refs=c.human_refs,
        agent_refs=c.agent_refs,
        policy_refs=c.policy_refs,
        decision_points=c.decision_points,
        configuration=c.configuration,
        effective_from=c.effective_period.valid_from,
        effective_to=c.effective_period.valid_until,
        lifecycle_state=c.lifecycle_state.value,
        provenance_ref=c.provenance_ref,
    )
    return _commit(session, row, "assembly", f"{c.assembly_id}@{c.version}")


def get_transform(session: Session, ref: str) -> TransformVersion | None:
    if "@" not in ref:
        return None
    rid, version = ref.rsplit("@", 1)
    return session.scalar(select(TransformVersion).where(TransformVersion.transform_id == rid, TransformVersion.version == version))


def get_adapter(session: Session, ref: str) -> AdapterVersion | None:
    if "@" not in ref:
        return None
    rid, version = ref.rsplit("@", 1)
    return session.scalar(select(AdapterVersion).where(AdapterVersion.adapter_id == rid, AdapterVersion.version == version))


def get_connection_plan(session: Session, ref: str) -> ConnectionPlanVersion | None:
    if "@" not in ref:
        return None
    rid, version = ref.rsplit("@", 1)
    return session.scalar(select(ConnectionPlanVersion).where(ConnectionPlanVersion.plan_id == rid, ConnectionPlanVersion.version == version))


def get_assembly(session: Session, ref: str) -> AssemblyVersion | None:
    if "@" not in ref:
        return None
    rid, version = ref.rsplit("@", 1)
    return session.scalar(select(AssemblyVersion).where(AssemblyVersion.assembly_id == rid, AssemblyVersion.version == version))


def find_transform(session: Session, from_contracts: list[str], to_contracts: list[str]) -> TransformVersion | None:
    if not from_contracts or not to_contracts:
        return None
    return session.scalar(
        select(TransformVersion).where(
            TransformVersion.from_contract_ref.in_(from_contracts),
            TransformVersion.to_contract_ref.in_(to_contracts),
            TransformVersion.lifecycle_state == "ACTIVE",
        )
    )


def find_adapter(session: Session, source_runtime: str, target_runtime: str, capability_refs: list[str]) -> AdapterVersion | None:
    rows = session.scalars(
        select(AdapterVersion).where(
            AdapterVersion.source_runtime_type == source_runtime,
            AdapterVersion.target_runtime_type == target_runtime,
            AdapterVersion.lifecycle_state == "ACTIVE",
        )
    ).all()
    for row in rows:
        scope = set(row.capability_scope or [])
        if not scope or scope.intersection(capability_refs):
            return row
    return None


def add_write_box_candidate(session: Session, row: WriteBoxCandidate) -> WriteBoxCandidate:
    return _commit(session, row, "write_box_candidate", row.candidate_id)


def promote_write_box_candidate(session: Session, candidate: WriteBoxCandidate) -> tuple[str, str]:
    if candidate.stage != "VERIFIED":
        raise DomainValidationError("candidate must be verified before promotion", ["WRITE_BOX_NOT_VERIFIED"])
    capability = CapabilityContract.model_validate(candidate.capability_json)
    smart_box = SmartBoxManifest.model_validate(candidate.smart_box_json)
    add_capability(session, capability)
    add_smart_box(session, smart_box)
    candidate.stage = "PROMOTED"
    candidate.promoted_at = datetime.now(timezone.utc)
    session.add(candidate)
    session.commit()
    return f"{capability.capability_id}@{capability.version}", f"{smart_box.box_id}@{smart_box.box_version}"
