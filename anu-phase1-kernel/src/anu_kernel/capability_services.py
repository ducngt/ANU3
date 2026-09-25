from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from .capability_contracts import (
    CapabilityDiscoveryHit,
    CapabilityDiscoveryQuery,
    CapabilityDiscoveryResponse,
)
from .capability_models import CapabilityVersion, SmartBoxManifestVersion


def discover_capabilities(session: Session, query: CapabilityDiscoveryQuery) -> CapabilityDiscoveryResponse:
    capabilities = session.scalars(
        select(CapabilityVersion).where(CapabilityVersion.lifecycle_state == "ACTIVE")
    ).all()
    boxes = session.scalars(
        select(SmartBoxManifestVersion).where(SmartBoxManifestVersion.lifecycle_state == "ACTIVE")
    ).all()
    boxes_by_capability: dict[str, list[SmartBoxManifestVersion]] = {}
    for box in boxes:
        boxes_by_capability.setdefault(box.capability_ref, []).append(box)

    hits: list[CapabilityDiscoveryHit] = []
    for cap in capabilities:
        if query.capability_id and cap.capability_id != query.capability_id:
            continue
        if query.domain and cap.domain != query.domain:
            continue
        matched_operations: list[str] = []
        reasons: list[str] = []
        for operation in cap.operations or []:
            if query.operation_id and operation.get("operation_id") != query.operation_id:
                continue
            input_semantics = set(operation.get("input_semantics") or [])
            output_semantics = set(operation.get("output_semantics") or [])
            if query.input_semantics and not set(query.input_semantics).issubset(input_semantics):
                continue
            if query.output_semantics and not set(query.output_semantics).issubset(output_semantics):
                continue
            matched_operations.append(operation.get("operation_id"))
        if query.operation_id or query.input_semantics or query.output_semantics:
            if not matched_operations:
                continue
        if query.operation_id:
            reasons.append(f"provides operation {query.operation_id}")
        if query.input_semantics:
            reasons.append("accepts requested input semantics")
        if query.output_semantics:
            reasons.append("produces requested output semantics")
        if query.domain:
            reasons.append(f"domain={query.domain}")
        if not reasons:
            reasons.append("active capability contract")
        cref = f"{cap.capability_id}@{cap.version}"
        box_refs = []
        if query.include_boxes:
            box_refs = [f"{box.box_id}@{box.box_version}" for box in boxes_by_capability.get(cref, [])]
        hits.append(
            CapabilityDiscoveryHit(
                capability_ref=cref,
                capability_id=cap.capability_id,
                capability_version=cap.version,
                name=cap.name,
                domain=cap.domain,
                owner_ref=cap.owner_ref,
                matched_operations=matched_operations,
                box_refs=box_refs,
                match_reasons=reasons,
            )
        )
    hits.sort(key=lambda hit: (hit.capability_id, hit.capability_version))
    return CapabilityDiscoveryResponse(query=query, hits=hits[: query.limit])
