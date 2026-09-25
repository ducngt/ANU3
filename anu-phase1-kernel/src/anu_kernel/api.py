from __future__ import annotations

import json
from pathlib import Path

from fastapi import Depends, FastAPI, Header, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from sqlalchemy import text
from sqlalchemy.orm import Session

from .contracts import (
    AuditEventContract,
    AuthorityEvaluationRequest,
    AuthorityGrantContract,
    CompetenceAssertionContract,
    DecisionRecordContract,
    DelegationGrantContract,
    DelegationRevocationContract,
    IdentityContract,
    KernelEventEnvelope,
    LifecycleTransitionContract,
    PolicyContract,
    PolicyEvaluationRequest,
    ProvenanceRecordContract,
    ReplayRequestContract,
    RoleAssignmentContract,
    SemanticDefinitionContract,
    GovernedActionRequest,
    TrustCredentialContract,
    SignatureRecordContract,
    AgentAttestationContract,
    IntegrityHashRequest,
)
from .db import get_session_factory
from .errors import DomainValidationError, RepositoryConflict
from .repository import (
    add_audit,
    add_authority,
    add_competence,
    add_decision,
    add_delegation,
    add_event,
    add_identity,
    add_lifecycle_transition,
    add_policy,
    add_provenance,
    add_role,
    add_semantic,
    revoke_delegation,
    add_trust_credential,
    add_signature_record,
    add_agent_attestation,
)
from .services import evaluate_authority, evaluate_policy, replay_decision
from .authn import authenticate_bearer_token
from .enforcement import enforce_governed_action
from .trust import integrity_ref, verify_signature_record, verify_agent_attestation
from .errors import AuthenticationError

KERNEL_VERSION = "0.3.0"
app = FastAPI(title="ANU Phase-1 Kernel", version=KERNEL_VERSION)


def get_session():
    session = get_session_factory()()
    try:
        yield session
    finally:
        session.close()


@app.exception_handler(RepositoryConflict)
def repository_conflict_handler(_: Request, exc: RepositoryConflict):
    return JSONResponse(
        status_code=409,
        content={
            "error": exc.code,
            "resource_type": exc.resource_type,
            "resource_id": exc.resource_id,
            "detail": str(exc),
        },
    )


@app.exception_handler(DomainValidationError)
def domain_validation_handler(_: Request, exc: DomainValidationError):
    return JSONResponse(
        status_code=422,
        content={"error": exc.code, "detail": str(exc), "reason_codes": exc.reason_codes},
    )


@app.exception_handler(AuthenticationError)
def authentication_error_handler(_: Request, exc: AuthenticationError):
    return JSONResponse(
        status_code=401,
        content={"error": exc.code, "detail": str(exc), "reason_codes": exc.reason_codes},
        headers={"WWW-Authenticate": "Bearer"},
    )


def get_authenticated_principal(
    authorization: str | None = Header(default=None),
    session: Session = Depends(get_session),
):
    if not authorization or not authorization.startswith("Bearer "):
        raise AuthenticationError("Bearer token required", ["BEARER_TOKEN_REQUIRED"])
    return authenticate_bearer_token(session, authorization[7:].strip())


@app.get("/", include_in_schema=False)
def root():
    return RedirectResponse(url="/human", status_code=307)


@app.get("/health")
def health(session: Session = Depends(get_session)):
    session.execute(text("SELECT 1"))
    return {"status": "ok", "phase": 1, "kernel_version": KERNEL_VERSION}


def _load_release_status() -> dict:
    candidates = [
        Path("docs/verification/LATEST.json"),
        Path(__file__).resolve().parents[2] / "docs" / "verification" / "LATEST.json",
    ]
    for path in candidates:
        if path.exists():
            try:
                return json.loads(path.read_text(encoding="utf-8"))
            except Exception:
                pass
    return {
        "work_id": "P1-T02",
        "status": "VERIFICATION_EVIDENCE_NOT_FOUND",
        "human_gate": "G3_NOT_READY",
        "message": "Run the automated verifier; Human does not need to use Swagger or inspect CI logs.",
    }


@app.get("/human/status")
def human_status():
    return _load_release_status()


@app.get("/human", response_class=HTMLResponse, include_in_schema=False)
def human_dashboard():
    status = _load_release_status()
    checks = status.get("checks", {})
    rows = "".join(
        f"<tr><td>{name}</td><td><strong>{value}</strong></td></tr>"
        for name, value in checks.items()
    )
    limitations = "".join(f"<li>{item}</li>" for item in status.get("known_limitations", [])) or "<li>None recorded</li>"
    return f"""
    <!doctype html><html><head><meta charset='utf-8'><title>ANU Phase 1 Human Dashboard</title>
    <style>body{{font-family:system-ui;max-width:920px;margin:40px auto;padding:0 20px;line-height:1.5}}
    table{{border-collapse:collapse;width:100%}}td,th{{border:1px solid #ddd;padding:10px;text-align:left}}
    .gate{{font-size:1.2rem;padding:12px;background:#f3f4f6;border-radius:8px}}</style></head><body>
    <h1>ANU Phase 1 — Human Dashboard</h1>
    <p class='gate'><b>Work:</b> {status.get('work_id','P1-T02')} · <b>Status:</b> {status.get('status')} · <b>Human Gate:</b> {status.get('human_gate')}</p>
    <p>{status.get('summary','Technical work is executed and verified by AI/CI. Human reviews meaning, authority, evidence, outcome and residual risk.')}</p>
    <h2>Verification evidence</h2><table><tr><th>Check</th><th>Result</th></tr>{rows}</table>
    <h2>Known limitations</h2><ul>{limitations}</ul>
    <h2>Human action</h2><p>{status.get('human_action','Review the G3 acceptance packet. Do not review code or run technical tests by default.')}</p>
    <p><a href='/human/status'>Machine-readable status</a> · <a href='/health'>Runtime health</a></p>
    </body></html>
    """


@app.post("/v1/identities")
def create_identity(body: IdentityContract, session: Session = Depends(get_session)):
    add_identity(session, body)
    return body


@app.post("/v1/semantics")
def create_semantic(body: SemanticDefinitionContract, session: Session = Depends(get_session)):
    add_semantic(session, body)
    return body


@app.post("/v1/roles")
def create_role(body: RoleAssignmentContract, session: Session = Depends(get_session)):
    add_role(session, body)
    return body


@app.post("/v1/competences")
def create_competence(body: CompetenceAssertionContract, session: Session = Depends(get_session)):
    add_competence(session, body)
    return body


@app.post("/v1/authorities")
def create_authority(body: AuthorityGrantContract, session: Session = Depends(get_session)):
    add_authority(session, body)
    return body


@app.post("/v1/delegations")
def create_delegation(body: DelegationGrantContract, session: Session = Depends(get_session)):
    add_delegation(session, body)
    return body


@app.post("/v1/delegations/revoke")
def delegation_revoke(body: DelegationRevocationContract, session: Session = Depends(get_session)):
    revoke_delegation(session, body)
    return body


@app.post("/v1/policies")
def create_policy(body: PolicyContract, session: Session = Depends(get_session)):
    add_policy(session, body)
    return body


@app.post("/v1/policy/evaluate")
def policy_eval(body: PolicyEvaluationRequest, session: Session = Depends(get_session)):
    return evaluate_policy(session, body)


@app.post("/v1/provenance")
def create_provenance(body: ProvenanceRecordContract, session: Session = Depends(get_session)):
    add_provenance(session, body)
    return body


@app.post("/v1/audit")
def create_audit(body: AuditEventContract, session: Session = Depends(get_session)):
    add_audit(session, body)
    return body


@app.post("/v1/lifecycle/transitions")
def create_lifecycle_transition(body: LifecycleTransitionContract, session: Session = Depends(get_session)):
    add_lifecycle_transition(session, body)
    return body


@app.post("/v1/events")
def create_event(body: KernelEventEnvelope, session: Session = Depends(get_session)):
    add_event(session, body)
    return body


@app.post("/v1/decisions")
def create_decision(body: DecisionRecordContract, session: Session = Depends(get_session)):
    add_decision(session, body)
    return body


@app.post("/v1/authority/evaluate")
def authority_eval(body: AuthorityEvaluationRequest, session: Session = Depends(get_session)):
    return evaluate_authority(session, body)


@app.post("/v1/replay")
def replay(body: ReplayRequestContract, session: Session = Depends(get_session)):
    try:
        return replay_decision(session, body)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.post("/v1/governed/evaluate")
def governed_evaluate(
    body: GovernedActionRequest,
    principal=Depends(get_authenticated_principal),
    session: Session = Depends(get_session),
):
    return enforce_governed_action(session, principal, body)


@app.post("/v1/trust/credentials")
def create_trust_credential(body: TrustCredentialContract, session: Session = Depends(get_session)):
    add_trust_credential(session, body)
    return body


@app.post("/v1/trust/signatures")
def create_signature(body: SignatureRecordContract, session: Session = Depends(get_session)):
    add_signature_record(session, body)
    return verify_signature_record(session, body)


@app.post("/v1/trust/signatures/verify")
def signature_verify(body: SignatureRecordContract, session: Session = Depends(get_session)):
    return verify_signature_record(session, body)


@app.post("/v1/trust/attestations")
def create_attestation(body: AgentAttestationContract, session: Session = Depends(get_session)):
    add_agent_attestation(session, body)
    return verify_agent_attestation(session, body)


@app.post("/v1/trust/attestations/verify")
def attestation_verify(body: AgentAttestationContract, session: Session = Depends(get_session)):
    return verify_agent_attestation(session, body)


@app.post("/v1/integrity/hash")
def hash_artifact(body: IntegrityHashRequest):
    return {"algorithm": "SHA-256", "integrity_ref": integrity_ref(body.artifact)}
