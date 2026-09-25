from __future__ import annotations

from typing import Any

from pydantic import Field, model_validator

from .contracts import EffectivePeriod, KernelModel, LifecycleState


class CapabilityOperation(KernelModel):
    operation_id: str
    purpose: str
    input_semantics: list[str] = Field(default_factory=list)
    output_semantics: list[str] = Field(default_factory=list)
    input_contract_refs: list[str] = Field(default_factory=list)
    output_contract_refs: list[str] = Field(default_factory=list)
    constraints: dict[str, Any] = Field(default_factory=dict)
    policy_refs: list[str] = Field(default_factory=list)


class CapabilityContract(KernelModel):
    capability_id: str
    name: str
    description: str
    owner_ref: str
    domain: str
    version: str
    operations: list[CapabilityOperation]
    requires_capabilities: list[str] = Field(default_factory=list)
    data_scope: list[str] = Field(default_factory=list)
    policy_refs: list[str] = Field(default_factory=list)
    risk_class: str = "E1"
    effective_period: EffectivePeriod
    lifecycle_state: LifecycleState = LifecycleState.ACTIVE
    provenance_ref: str

    @model_validator(mode="after")
    def capability_is_not_authority(self) -> "CapabilityContract":
        if not self.operations:
            raise ValueError("capability requires at least one operation")
        return self


class SmartBoxOperationBinding(KernelModel):
    operation_id: str
    handler_ref: str
    timeout_seconds: int = Field(default=30, ge=1, le=3600)
    idempotent: bool = True


class SmartBoxManifest(KernelModel):
    box_id: str
    capability_ref: str
    box_version: str
    provider_ref: str
    runtime_type: str
    operation_bindings: list[SmartBoxOperationBinding]
    requires_capabilities: list[str] = Field(default_factory=list)
    adapter_boundary: str
    model_dependencies: list[str] = Field(default_factory=list)
    data_classes: list[str] = Field(default_factory=list)
    quality_slo: dict[str, Any] = Field(default_factory=dict)
    observability: dict[str, Any] = Field(default_factory=dict)
    effective_period: EffectivePeriod
    lifecycle_state: LifecycleState = LifecycleState.ACTIVE
    provenance_ref: str


class CapabilityDiscoveryQuery(KernelModel):
    operation_id: str | None = None
    input_semantics: list[str] = Field(default_factory=list)
    output_semantics: list[str] = Field(default_factory=list)
    domain: str | None = None
    capability_id: str | None = None
    include_boxes: bool = True
    limit: int = Field(default=50, ge=1, le=200)


class CapabilityDiscoveryHit(KernelModel):
    capability_ref: str
    capability_id: str
    capability_version: str
    name: str
    domain: str
    owner_ref: str
    matched_operations: list[str] = Field(default_factory=list)
    box_refs: list[str] = Field(default_factory=list)
    match_reasons: list[str] = Field(default_factory=list)


class CapabilityDiscoveryResponse(KernelModel):
    query: CapabilityDiscoveryQuery
    hits: list[CapabilityDiscoveryHit] = Field(default_factory=list)
