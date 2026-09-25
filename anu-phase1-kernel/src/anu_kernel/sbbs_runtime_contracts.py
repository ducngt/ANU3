from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import Field, model_validator

from .capability_contracts import CapabilityContract, SmartBoxManifest
from .contracts import EffectivePeriod, KernelModel, LifecycleState


CompatibilityStatus = Literal["PASS", "FAIL", "TRANSFORM_REQUIRED", "ADAPTER_REQUIRED"]


class CompatibilityContext(KernelModel):
    granted_permissions: list[str] = Field(default_factory=list)
    security_tags: list[str] = Field(default_factory=list)
    satisfied_policy_refs: list[str] = Field(default_factory=list)


class CompatibilityCheckRequest(KernelModel):
    from_capability_ref: str
    from_operation: str
    to_capability_ref: str
    to_operation: str
    from_box_ref: str | None = None
    to_box_ref: str | None = None
    context: CompatibilityContext = Field(default_factory=CompatibilityContext)


class CompatibilityDimension(KernelModel):
    dimension: str
    status: CompatibilityStatus
    detail: str
    evidence_refs: list[str] = Field(default_factory=list)


class CompatibilityResult(KernelModel):
    compatible: bool
    direct: bool
    from_capability_ref: str
    from_operation: str
    to_capability_ref: str
    to_operation: str
    dimensions: list[CompatibilityDimension]
    required_transformation_refs: list[str] = Field(default_factory=list)
    required_adapter_refs: list[str] = Field(default_factory=list)
    evidence_id: str | None = None


class TransformDefinition(KernelModel):
    transform_id: str
    version: str
    name: str
    owner_ref: str
    from_contract_ref: str
    to_contract_ref: str
    mapping: dict[str, str] = Field(default_factory=dict)
    constants: dict[str, Any] = Field(default_factory=dict)
    semantic_preservation: list[str] = Field(default_factory=list)
    lossy: bool = False
    effective_period: EffectivePeriod
    lifecycle_state: LifecycleState = LifecycleState.ACTIVE
    provenance_ref: str


class AdapterDefinition(KernelModel):
    adapter_id: str
    version: str
    name: str
    owner_ref: str
    source_runtime_type: str
    target_runtime_type: str
    capability_scope: list[str] = Field(default_factory=list)
    configuration: dict[str, Any] = Field(default_factory=dict)
    effective_period: EffectivePeriod
    lifecycle_state: LifecycleState = LifecycleState.ACTIVE
    provenance_ref: str


class RetryPolicy(KernelModel):
    max_attempts: int = Field(default=1, ge=1, le=10)
    retry_on: list[str] = Field(default_factory=lambda: ["TRANSIENT_ERROR"])


class ConnectionPlanRequest(CompatibilityCheckRequest):
    provenance_ref: str
    retry_policy: RetryPolicy = Field(default_factory=RetryPolicy)
    observability_policy: dict[str, Any] = Field(default_factory=lambda: {"trace": True, "metrics": True})


class ConnectionPlan(KernelModel):
    plan_id: str
    version: str = "1.0.0"
    from_capability: str
    from_operation: str
    to_capability: str
    to_operation: str
    from_box_ref: str
    to_box_ref: str
    contract_ref: str | None = None
    transformation_refs: list[str] = Field(default_factory=list)
    adapter_refs: list[str] = Field(default_factory=list)
    policy_checks: list[str] = Field(default_factory=list)
    security_context: dict[str, Any] = Field(default_factory=dict)
    retry_policy: RetryPolicy = Field(default_factory=RetryPolicy)
    observability_policy: dict[str, Any] = Field(default_factory=dict)
    compatibility_evidence: list[str] = Field(default_factory=list)
    effective_period: EffectivePeriod
    lifecycle_state: LifecycleState = LifecycleState.ACTIVE
    provenance_ref: str


class WireStepTrace(KernelModel):
    step: str
    status: Literal["PASS", "FAIL", "SKIP"]
    detail: str


class SmartWireExecutionRequest(KernelModel):
    plan_ref: str
    payload: dict[str, Any]
    trace_id: str
    context: CompatibilityContext = Field(default_factory=CompatibilityContext)


class SmartWireExecutionResult(KernelModel):
    execution_id: str
    plan_ref: str
    trace_id: str
    status: Literal["SUCCEEDED", "FAILED"]
    output_payload: dict[str, Any] | None = None
    selected_box_ref: str | None = None
    traces: list[WireStepTrace] = Field(default_factory=list)
    started_at: datetime
    completed_at: datetime


class AssemblyDefinition(KernelModel):
    assembly_id: str
    name: str
    description: str
    owner_ref: str
    version: str
    capability_refs: list[str]
    connection_plan_refs: list[str]
    human_refs: list[str] = Field(default_factory=list)
    agent_refs: list[str] = Field(default_factory=list)
    policy_refs: list[str] = Field(default_factory=list)
    decision_points: list[dict[str, Any]] = Field(default_factory=list)
    configuration: dict[str, Any] = Field(default_factory=dict)
    effective_period: EffectivePeriod
    lifecycle_state: LifecycleState = LifecycleState.ACTIVE
    provenance_ref: str

    @model_validator(mode="after")
    def requires_composition(self) -> "AssemblyDefinition":
        if not self.capability_refs:
            raise ValueError("assembly requires at least one capability")
        return self


class AssemblyExecutionRequest(KernelModel):
    assembly_ref: str
    input_payload: dict[str, Any]
    trace_id: str
    context: CompatibilityContext = Field(default_factory=CompatibilityContext)


class AssemblyExecutionResult(KernelModel):
    execution_id: str
    assembly_ref: str
    trace_id: str
    status: Literal["SUCCEEDED", "FAILED"]
    final_payload: dict[str, Any] | None = None
    connection_results: list[SmartWireExecutionResult] = Field(default_factory=list)
    started_at: datetime
    completed_at: datetime


class ArchitectureAuditReport(KernelModel):
    audit_id: str
    subject_ref: str
    passed: bool
    checks: dict[str, Literal["PASS", "FAIL"]]
    findings: list[str] = Field(default_factory=list)
    audited_at: datetime


class WriteBoxProposalRequest(KernelModel):
    intent: str
    actor_ref: str
    capability: CapabilityContract
    smart_box: SmartBoxManifest
    specification: str
    knowledge_refs: list[str]
    rule_refs: list[str]
    examples: list[dict[str, Any]]
    provenance_ref: str


class WriteBoxProposalResult(KernelModel):
    candidate_id: str
    recommended_action: Literal["REUSE", "VERSION", "ADAPTER", "ASSEMBLY", "WRITE_BOX"]
    existing_capability_refs: list[str] = Field(default_factory=list)
    architecture_audit: ArchitectureAuditReport
    stage: Literal["DRAFT", "VERIFIED", "PROMOTED", "REJECTED"] = "DRAFT"


class WriteBoxPromotionRequest(KernelModel):
    candidate_id: str
    actor_ref: str


class WriteBoxPromotionResult(KernelModel):
    candidate_id: str
    capability_ref: str
    box_ref: str
    stage: Literal["PROMOTED"] = "PROMOTED"
