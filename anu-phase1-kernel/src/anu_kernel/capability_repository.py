from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from .capability_contracts import CapabilityContract, SmartBoxManifest
from .capability_models import CapabilityVersion, SmartBoxManifestVersion
from .db import ProvenanceRecord
from .errors import DomainValidationError, RepositoryConflict


def _commit(session: Session, row, resource_type: str, resource_id: str):
    session.add(row)
    try:
        session.commit()
    except IntegrityError as exc:
        session.rollback()
        raise RepositoryConflict(resource_type, resource_id) from exc
    return row


def add_capability(session: Session, c: CapabilityContract) -> CapabilityVersion:
    if session.get(ProvenanceRecord, c.provenance_ref) is None:
        raise DomainValidationError("provenance not found", ["PROVENANCE_REQUIRED"])
    row = CapabilityVersion(
        capability_id=c.capability_id,
        name=c.name,
        description=c.description,
        owner_ref=c.owner_ref,
        domain=c.domain,
        version=c.version,
        operations=[op.model_dump(mode="json") for op in c.operations],
        requires_capabilities=c.requires_capabilities,
        data_scope=c.data_scope,
        policy_refs=c.policy_refs,
        risk_class=c.risk_class,
        effective_from=c.effective_period.valid_from,
        effective_to=c.effective_period.valid_until,
        lifecycle_state=c.lifecycle_state.value,
        provenance_ref=c.provenance_ref,
    )
    return _commit(session, row, "capability", f"{c.capability_id}@{c.version}")


def _capability_by_ref(session: Session, capability_ref: str) -> CapabilityVersion | None:
    if "@" not in capability_ref:
        return None
    capability_id, version = capability_ref.rsplit("@", 1)
    return session.scalar(
        select(CapabilityVersion).where(
            CapabilityVersion.capability_id == capability_id,
            CapabilityVersion.version == version,
            CapabilityVersion.lifecycle_state == "ACTIVE",
        )
    )


def add_smart_box(session: Session, c: SmartBoxManifest) -> SmartBoxManifestVersion:
    capability = _capability_by_ref(session, c.capability_ref)
    if capability is None:
        raise DomainValidationError("capability contract not found", ["CAPABILITY_CONTRACT_NOT_FOUND"])
    operation_ids = {op["operation_id"] for op in capability.operations or []}
    binding_ids = {binding.operation_id for binding in c.operation_bindings}
    if not binding_ids.issubset(operation_ids):
        raise DomainValidationError("Smart Box binds an operation not declared by capability contract", ["BOX_OPERATION_NOT_IN_CONTRACT"])
    if session.get(ProvenanceRecord, c.provenance_ref) is None:
        raise DomainValidationError("provenance not found", ["PROVENANCE_REQUIRED"])
    row = SmartBoxManifestVersion(
        box_id=c.box_id,
        capability_ref=c.capability_ref,
        box_version=c.box_version,
        provider_ref=c.provider_ref,
        runtime_type=c.runtime_type,
        operation_bindings=[op.model_dump(mode="json") for op in c.operation_bindings],
        requires_capabilities=c.requires_capabilities,
        adapter_boundary=c.adapter_boundary,
        model_dependencies=c.model_dependencies,
        data_classes=c.data_classes,
        quality_slo=c.quality_slo,
        observability=c.observability,
        effective_from=c.effective_period.valid_from,
        effective_to=c.effective_period.valid_until,
        lifecycle_state=c.lifecycle_state.value,
        provenance_ref=c.provenance_ref,
    )
    return _commit(session, row, "smart_box_manifest", f"{c.box_id}@{c.box_version}")
