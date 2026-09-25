from __future__ import annotations

import base64
import hashlib
import json
from datetime import datetime, timezone
from typing import Any

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
from sqlalchemy import select
from sqlalchemy.orm import Session

from .contracts import (
    AgentAttestationContract,
    AttestationVerificationResult,
    AuthorityEvaluationRequest,
    SignatureRecordContract,
    SignatureVerificationResult,
    SubjectType,
)
from .db import AuthorityGrant, IdentityRecord, TrustCredential
from .services import active_delegations, active_roles, evaluate_authority


def _cmp_dt(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def canonical_json_bytes(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def integrity_ref(value: Any) -> str:
    return "sha256:" + hashlib.sha256(canonical_json_bytes(value)).hexdigest()


def public_key_fingerprint_sha256(public_key_pem: str) -> str:
    key = serialization.load_pem_public_key(public_key_pem.encode("utf-8"))
    if not isinstance(key, Ed25519PublicKey):
        raise ValueError("only Ed25519 public keys are supported by the Phase-1 reference adapter")
    der = key.public_bytes(serialization.Encoding.DER, serialization.PublicFormat.SubjectPublicKeyInfo)
    return "sha256:" + hashlib.sha256(der).hexdigest()


def _active_credential(credential: TrustCredential, at: datetime) -> tuple[bool, list[str]]:
    reasons: list[str] = []
    if credential.status != "ACTIVE":
        reasons.append("CREDENTIAL_NOT_ACTIVE")
    if _cmp_dt(at) < _cmp_dt(credential.valid_from):
        reasons.append("CREDENTIAL_NOT_YET_VALID")
    if credential.valid_until is not None and _cmp_dt(at) >= _cmp_dt(credential.valid_until):
        reasons.append("CREDENTIAL_EXPIRED")
    if credential.revoked_at is not None and _cmp_dt(at) >= _cmp_dt(credential.revoked_at):
        reasons.append("CREDENTIAL_REVOKED")
    return not reasons, reasons


def _verify_ed25519(public_key_pem: str, payload: bytes, signature_b64: str) -> bool:
    try:
        key = serialization.load_pem_public_key(public_key_pem.encode("utf-8"))
        if not isinstance(key, Ed25519PublicKey):
            return False
        signature = base64.b64decode(signature_b64.encode("ascii"), validate=True)
        key.verify(signature, payload)
        return True
    except (ValueError, InvalidSignature, TypeError):
        return False


def signature_signing_payload(record: SignatureRecordContract) -> dict[str, Any]:
    return record.model_dump(
        mode="json",
        exclude={"signature_value"},
    )


def signature_signing_bytes(record: SignatureRecordContract) -> bytes:
    return canonical_json_bytes(signature_signing_payload(record))


def attestation_signing_payload(record: AgentAttestationContract) -> dict[str, Any]:
    return record.model_dump(
        mode="json",
        exclude={"attestation_signature"},
    )


def attestation_signing_bytes(record: AgentAttestationContract) -> bytes:
    return canonical_json_bytes(attestation_signing_payload(record))


def verify_signature_record(session: Session, record: SignatureRecordContract) -> SignatureVerificationResult:
    reasons: list[str] = []
    credential = session.get(TrustCredential, record.credential_ref)
    credential_valid = False
    cryptographically_valid = False

    if credential is None:
        reasons.append("CREDENTIAL_NOT_FOUND")
    else:
        credential_valid, credential_reasons = _active_credential(credential, record.signed_at)
        reasons.extend(credential_reasons)
        if credential.subject_ref != record.signer_identity_ref:
            credential_valid = False
            reasons.append("CREDENTIAL_SUBJECT_MISMATCH")
        expected_fingerprint = public_key_fingerprint_sha256(credential.public_key_pem)
        if expected_fingerprint != credential.fingerprint_sha256:
            credential_valid = False
            reasons.append("CREDENTIAL_FINGERPRINT_MISMATCH")
        cryptographically_valid = _verify_ed25519(
            credential.public_key_pem,
            signature_signing_bytes(record),
            record.signature_value,
        )
        if not cryptographically_valid:
            reasons.append("SIGNATURE_INVALID")

    roles = active_roles(session, record.signer_identity_ref, record.signed_at)
    role_valid = any(r.role_ref == record.signer_role_ref for r in roles)
    if not role_valid:
        reasons.append("SIGNER_ROLE_NOT_ACTIVE")

    authority_valid = False
    grant = session.get(AuthorityGrant, record.authority_ref)
    if grant is None:
        reasons.append("AUTHORITY_NOT_FOUND")
    elif grant.subject_ref != record.signer_identity_ref:
        reasons.append("AUTHORITY_SUBJECT_MISMATCH")
    else:
        identity = session.scalar(
            select(IdentityRecord).where(IdentityRecord.subject_id == record.signer_identity_ref)
        )
        subject_type = SubjectType(identity.subject_type) if identity else SubjectType.HUMAN
        evaluation = evaluate_authority(
            session,
            AuthorityEvaluationRequest(
                subject_ref=record.signer_identity_ref,
                subject_type=subject_type,
                action=grant.authority_type,
                resource=(grant.scope or {}).get("resource"),
                context_ref=(grant.scope or {}).get("context"),
                at=record.signed_at,
            ),
        )
        authority_valid = record.authority_ref in evaluation["authority_refs"]
        if not authority_valid:
            reasons.extend(evaluation["reason_codes"] or ["AUTHORITY_INVALID"])

    institutional_valid = credential_valid and cryptographically_valid and role_valid and authority_valid
    return SignatureVerificationResult(
        signature_id=record.signature_id,
        cryptographically_valid=cryptographically_valid,
        credential_valid=credential_valid,
        role_valid=role_valid,
        authority_valid=authority_valid,
        institutional_valid=institutional_valid,
        reason_codes=sorted(set(reasons)),
    )


def verify_agent_attestation(session: Session, record: AgentAttestationContract) -> AttestationVerificationResult:
    reasons: list[str] = []
    credential = session.get(TrustCredential, record.credential_ref)
    credential_valid = False
    cryptographically_valid = False
    if credential is None:
        reasons.append("CREDENTIAL_NOT_FOUND")
    else:
        credential_valid, credential_reasons = _active_credential(credential, record.timestamp)
        reasons.extend(credential_reasons)
        if credential.subject_ref != record.agent_ref:
            credential_valid = False
            reasons.append("CREDENTIAL_SUBJECT_MISMATCH")
        expected_fingerprint = public_key_fingerprint_sha256(credential.public_key_pem)
        if expected_fingerprint != credential.fingerprint_sha256:
            credential_valid = False
            reasons.append("CREDENTIAL_FINGERPRINT_MISMATCH")
        cryptographically_valid = _verify_ed25519(
            credential.public_key_pem,
            attestation_signing_bytes(record),
            record.attestation_signature,
        )
        if not cryptographically_valid:
            reasons.append("ATTESTATION_SIGNATURE_INVALID")

    delegation_valid = not record.consequential
    if record.consequential:
        active = active_delegations(session, record.agent_ref, record.timestamp)
        delegation_valid = any(d.delegation_id == record.delegation_ref for d in active)
        if not delegation_valid:
            reasons.append("ACTIVE_DELEGATION_REQUIRED")

    attestation_valid = credential_valid and cryptographically_valid and delegation_valid
    return AttestationVerificationResult(
        attestation_id=record.attestation_id,
        cryptographically_valid=cryptographically_valid,
        credential_valid=credential_valid,
        delegation_valid=delegation_valid,
        attestation_valid=attestation_valid,
        reason_codes=sorted(set(reasons)),
    )
