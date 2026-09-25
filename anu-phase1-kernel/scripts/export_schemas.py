from __future__ import annotations

import json
from pathlib import Path

from anu_kernel import contracts

MODELS = {
    "anu.identity.v1": contracts.IdentityContract,
    "anu.semantic-definition.v1": contracts.SemanticDefinitionContract,
    "anu.role-assignment.v1": contracts.RoleAssignmentContract,
    "anu.competence-assertion.v1": contracts.CompetenceAssertionContract,
    "anu.authority-grant.v1": contracts.AuthorityGrantContract,
    "anu.delegation.v1": contracts.DelegationGrantContract,
    "anu.delegation-revocation.v1": contracts.DelegationRevocationContract,
    "anu.policy.v1": contracts.PolicyContract,
    "anu.policy-evaluation-request.v1": contracts.PolicyEvaluationRequest,
    "anu.policy-decision.v1": contracts.PolicyDecisionContract,
    "anu.provenance-record.v1": contracts.ProvenanceRecordContract,
    "anu.audit-event.v1": contracts.AuditEventContract,
    "anu.lifecycle-transition.v1": contracts.LifecycleTransitionContract,
    "anu.event-envelope.v1": contracts.KernelEventEnvelope,
    "anu.decision-record.v1": contracts.DecisionRecordContract,
    "anu.replay-request.v1": contracts.ReplayRequestContract,
    "anu.replay-result.v1": contracts.ReplayResultContract,
    "anu.authentication-context.v1": contracts.AuthenticationContext,
    "anu.governed-action-request.v1": contracts.GovernedActionRequest,
    "anu.enforcement-decision.v1": contracts.EnforcementDecisionContract,
    "anu.trust-credential.v1": contracts.TrustCredentialContract,
    "anu.signature-record.v1": contracts.SignatureRecordContract,
    "anu.signature-verification-result.v1": contracts.SignatureVerificationResult,
    "anu.agent-attestation.v1": contracts.AgentAttestationContract,
    "anu.attestation-verification-result.v1": contracts.AttestationVerificationResult,
    "anu.integrity-hash-request.v1": contracts.IntegrityHashRequest,
    "anu.integrity-hash-result.v1": contracts.IntegrityHashResult,
}

out = Path(__file__).resolve().parents[1] / "contracts" / "schemas"
out.mkdir(parents=True, exist_ok=True)
for name, model in MODELS.items():
    schema = model.model_json_schema(mode="validation")
    schema["$id"] = f"urn:anu:schema:{name}"
    (out / f"{name}.json").write_text(json.dumps(schema, indent=2, ensure_ascii=False) + "\n")
print(f"exported {len(MODELS)} schemas to {out}")
