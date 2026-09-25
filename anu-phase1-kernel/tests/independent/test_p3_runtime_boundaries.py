from __future__ import annotations

import inspect

from anu_kernel import sbbs_runtime_services
from anu_kernel.capability_contracts import CapabilityContract
from anu_kernel.sbbs_runtime_contracts import ConnectionPlan


def test_thin_wire_does_not_discover_or_select_capabilities():
    source = inspect.getsource(sbbs_runtime_services.execute_wire)
    assert "discover_capabilities" not in source
    assert "CapabilityDiscoveryQuery" not in source
    assert "plan_connection" not in source


def test_connection_plan_requires_compatibility_evidence_field():
    assert "compatibility_evidence" in ConnectionPlan.model_fields


def test_capability_contract_has_no_authority_field():
    assert "authority" not in CapabilityContract.model_fields
    assert "delegation" not in CapabilityContract.model_fields


def test_wire_only_executes_predeclared_plan():
    source = inspect.getsource(sbbs_runtime_services.execute_wire)
    assert "get_connection_plan" in source
    assert "COMPATIBILITY_EVIDENCE_REQUIRED" in source
