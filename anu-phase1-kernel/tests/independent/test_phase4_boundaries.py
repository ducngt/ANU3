from __future__ import annotations

from datetime import datetime, timezone

import pytest

from anu_kernel.work_contracts import (
    ApprovalPoint,
    AutonomyLevel,
    DecisionPoint,
    ExecutionClass,
    ExecutionPlanRequest,
    WorkContract,
)
from anu_kernel.contracts import EffectivePeriod

NOW = datetime(2026, 1, 1, tzinfo=timezone.utc)


def test_execution_planner_request_cannot_accept_authority_policy_or_datascope():
    fields = set(ExecutionPlanRequest.model_fields)
    assert "authority_ref" not in fields
    assert "authority_refs" not in fields
    assert "policy_ref" not in fields
    assert "policy_refs" not in fields
    assert "data_scope" not in fields
    assert "signature_requirement" not in fields


def test_e3_contract_requires_human_authority_decision_and_human_approval():
    base = dict(
        work_type_id="urn:anu:work-type:e3-boundary",
        name="E3",
        description="boundary",
        version="1.0.0",
        owner_ref="urn:anu:org:aru-01",
        goal="Approve academic change",
        execution_class=ExecutionClass.E3,
        allowed_autonomy=AutonomyLevel.A2,
        risk_class="HIGH",
        effective_period=EffectivePeriod(valid_from=NOW),
        provenance_ref="urn:anu:provenance:test",
    )
    with pytest.raises(ValueError):
        WorkContract(**base)
    with pytest.raises(ValueError):
        WorkContract(
            **base,
            decision_points=[DecisionPoint(decision_id="d", description="decision", consequential=True, human_authority_required=True)],
        )
    ok = WorkContract(
        **base,
        decision_points=[DecisionPoint(decision_id="d", description="decision", consequential=True, human_authority_required=True)],
        approval_points=[ApprovalPoint(approval_id="a", description="approval", human_required=True, signature_required=True)],
    )
    assert ok.allowed_autonomy == AutonomyLevel.A2


def test_e3_contract_may_declare_post_approval_autonomy_but_keeps_human_decision():
    c = WorkContract(
        work_type_id="urn:anu:work-type:e3-contextual-autonomy",
        name="E3 contextual",
        description="A3 is only meaningful after Human approval; runtime enforces pre-decision A2 ceiling.",
        version="1.0.0",
        owner_ref="urn:anu:org:aru-01",
        goal="governed action",
        execution_class=ExecutionClass.E3,
        allowed_autonomy=AutonomyLevel.A3,
        decision_points=[DecisionPoint(decision_id="d", description="d", consequential=True, human_authority_required=True)],
        approval_points=[ApprovalPoint(approval_id="a", description="a", human_required=True, signature_required=True)],
        risk_class="HIGH",
        effective_period=EffectivePeriod(valid_from=NOW),
        provenance_ref="urn:anu:provenance:test",
    )
    assert c.allowed_autonomy == AutonomyLevel.A3
