from __future__ import annotations

import base64
from datetime import datetime

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from anu_kernel.contracts import (
    AgentAttestationContract,
    AuthorityGrantContract,
    AuthorityScope,
    DelegationGrantContract,
    DelegationRevocationContract,
    EffectivePeriod,
    IdentityContract,
    SignatureRecordContract,
    RoleAssignmentContract,
    SubjectType,
    TrustCredentialContract,
)
from anu_kernel.repository import (
    add_authority,
    add_delegation,
    add_identity,
    add_role,
    add_trust_credential,
    revoke_delegation,
)
from anu_kernel.trust import (
    attestation_signing_bytes,
    public_key_fingerprint_sha256,
    signature_signing_bytes,
    verify_agent_attestation,
    verify_signature_record,
)


def dt(s: str) -> datetime:
    return datetime.fromisoformat(s.replace("Z", "+00:00"))


def keypair():
    private = Ed25519PrivateKey.generate()
    pem = private.public_key().public_bytes(
        serialization.Encoding.PEM,
        serialization.PublicFormat.SubjectPublicKeyInfo,
    ).decode("utf-8")
    return private, pem


def sign(private, payload: bytes) -> str:
    return base64.b64encode(private.sign(payload)).decode("ascii")


def test_valid_crypto_signature_does_not_create_authority(session):
    signer = "urn:anu:human:h200"
    private, pem = keypair()
    credential_id = "urn:anu:credential:sign:h200"
    add_identity(session, IdentityContract(
        identity_id="urn:anu:identity:human:h200",
        subject_id=signer,
        subject_type=SubjectType.HUMAN,
        effective_period=EffectivePeriod(valid_from=dt("2026-01-01T00:00:00Z")),
    ))
    add_role(session, RoleAssignmentContract(
        assignment_id="role-h200", subject_ref=signer, role_ref="programme-owner",
        context_ref="urn:anu:programme:se", assigned_by="urn:anu:human:rector",
        effective_period=EffectivePeriod(valid_from=dt("2026-01-01T00:00:00Z")),
    ))
    add_trust_credential(session, TrustCredentialContract(
        credential_id=credential_id,
        subject_ref=signer,
        public_key_pem=pem,
        fingerprint_sha256=public_key_fingerprint_sha256(pem),
        issuer_ref="urn:anu:trust:aru",
        valid_from=dt("2026-01-01T00:00:00Z"),
    ))
    unsigned = SignatureRecordContract(
        signature_id="urn:anu:signature:s200",
        signer_identity_ref=signer,
        signer_role_ref="programme-owner",
        authority_ref="urn:anu:authority:missing",
        credential_ref=credential_id,
        intent="Approve programme revision",
        artifact_ref="urn:anu:artifact:programme-proposal",
        artifact_version="1.0",
        artifact_hash="sha256:abc",
        policy_version="urn:anu:policy:approval@1.0.0",
        signed_at=dt("2026-10-15T10:00:00Z"),
        signature_value="",
    )
    signed = unsigned.model_copy(update={"signature_value": sign(private, signature_signing_bytes(unsigned))})
    result = verify_signature_record(session, signed)
    assert result.cryptographically_valid is True
    assert result.credential_valid is True
    assert result.authority_valid is False
    assert result.institutional_valid is False


def test_human_signature_requires_crypto_credential_and_authority(session):
    signer = "urn:anu:human:h201"
    private, pem = keypair()
    credential_id = "urn:anu:credential:sign:h201"
    authority_id = "urn:anu:authority:h201-approve"
    add_identity(session, IdentityContract(
        identity_id="urn:anu:identity:human:h201",
        subject_id=signer,
        subject_type=SubjectType.HUMAN,
        effective_period=EffectivePeriod(valid_from=dt("2026-01-01T00:00:00Z")),
    ))
    add_role(session, RoleAssignmentContract(
        assignment_id="role-h201", subject_ref=signer, role_ref="programme-owner",
        context_ref="urn:anu:programme:se", assigned_by="urn:anu:human:rector",
        effective_period=EffectivePeriod(valid_from=dt("2026-01-01T00:00:00Z")),
    ))
    add_authority(session, AuthorityGrantContract(
        authority_id=authority_id,
        subject_ref=signer,
        subject_type=SubjectType.HUMAN,
        authority_type="academic.programme.approve",
        basis_ref="urn:anu:policy:approval@1.0.0",
        issuer_ref="urn:anu:org:aru",
        scope=AuthorityScope(resource="urn:anu:programme:se", action="academic.programme.approve"),
        consequence_class="ACADEMIC_CONSEQUENCE",
        effective_period=EffectivePeriod(valid_from=dt("2026-01-01T00:00:00Z"), valid_until=dt("2027-01-01T00:00:00Z")),
    ))
    add_trust_credential(session, TrustCredentialContract(
        credential_id=credential_id,
        subject_ref=signer,
        public_key_pem=pem,
        fingerprint_sha256=public_key_fingerprint_sha256(pem),
        issuer_ref="urn:anu:trust:aru",
        valid_from=dt("2026-01-01T00:00:00Z"),
    ))
    unsigned = SignatureRecordContract(
        signature_id="urn:anu:signature:s201",
        signer_identity_ref=signer,
        signer_role_ref="programme-owner",
        authority_ref=authority_id,
        credential_ref=credential_id,
        intent="Approve programme revision",
        artifact_ref="urn:anu:programme:se",
        artifact_version="1.3",
        artifact_hash="sha256:1234",
        policy_version="urn:anu:policy:approval@1.0.0",
        signed_at=dt("2026-10-15T10:00:00Z"),
        signature_value="",
    )
    signed = unsigned.model_copy(update={"signature_value": sign(private, signature_signing_bytes(unsigned))})
    result = verify_signature_record(session, signed)
    assert result.institutional_valid is True

    tampered = signed.model_copy(update={"artifact_hash": "sha256:tampered"})
    tampered_result = verify_signature_record(session, tampered)
    assert tampered_result.cryptographically_valid is False
    assert tampered_result.institutional_valid is False


def test_agent_attestation_requires_active_delegation_and_never_becomes_human_signature(session):
    human = "urn:anu:human:h202"
    agent = "urn:anu:agent:a202"
    private, pem = keypair()
    credential_id = "urn:anu:credential:agent:a202"
    authority_id = "urn:anu:authority:h202-approve"
    delegation_id = "urn:anu:delegation:a202"
    add_identity(session, IdentityContract(
        identity_id="urn:anu:identity:human:h202", subject_id=human, subject_type=SubjectType.HUMAN,
        effective_period=EffectivePeriod(valid_from=dt("2026-01-01T00:00:00Z")),
    ))
    add_identity(session, IdentityContract(
        identity_id="urn:anu:identity:agent:a202", subject_id=agent, subject_type=SubjectType.AGENT,
        effective_period=EffectivePeriod(valid_from=dt("2026-01-01T00:00:00Z")),
    ))
    add_authority(session, AuthorityGrantContract(
        authority_id=authority_id,
        subject_ref=human,
        subject_type=SubjectType.HUMAN,
        authority_type="academic.programme.precheck",
        basis_ref="urn:anu:policy:precheck@1.0.0",
        issuer_ref="urn:anu:org:aru",
        scope=AuthorityScope(resource="urn:anu:programme:se", action="academic.programme.precheck"),
        consequence_class="ACADEMIC_SUPPORT",
        delegation_allowed=True,
        effective_period=EffectivePeriod(valid_from=dt("2026-01-01T00:00:00Z"), valid_until=dt("2027-01-01T00:00:00Z")),
    ))
    add_delegation(session, DelegationGrantContract(
        delegation_id=delegation_id,
        delegator_ref=human,
        delegatee_ref=agent,
        authority_ref=authority_id,
        delegated_scope=AuthorityScope(resource="urn:anu:programme:se", action="academic.programme.precheck"),
        purpose="Programme precheck",
        valid_from=dt("2026-10-01T00:00:00Z"),
        valid_until=dt("2026-11-01T00:00:00Z"),
        issued_under_policy="urn:anu:policy:delegation@1.0.0",
    ))
    add_trust_credential(session, TrustCredentialContract(
        credential_id=credential_id,
        subject_ref=agent,
        public_key_pem=pem,
        fingerprint_sha256=public_key_fingerprint_sha256(pem),
        issuer_ref="urn:anu:trust:aru",
        valid_from=dt("2026-01-01T00:00:00Z"),
    ))

    def make_attestation(ts: datetime, attestation_id: str) -> AgentAttestationContract:
        unsigned = AgentAttestationContract(
            attestation_id=attestation_id,
            agent_ref=agent,
            agent_version="qa-agent@1.0.0",
            owner_ref="urn:anu:org:aru:qa",
            runtime_ref="urn:anu:runtime:reference",
            model_dependency="replaceable:model",
            purpose="Programme precheck",
            work_ref="urn:anu:work:pr-2026-001",
            action="academic.programme.precheck",
            capability_ref="urn:anu:capability:programme-precheck",
            delegation_ref=delegation_id,
            policy_version="urn:anu:policy:precheck@1.0.0",
            input_refs=["urn:anu:artifact:programme-proposal@1.3"],
            artifact_ref="urn:anu:artifact:qa-precheck@1.0",
            artifact_hash="sha256:agent-output",
            timestamp=ts,
            credential_ref=credential_id,
            attestation_signature="",
        )
        return unsigned.model_copy(update={"attestation_signature": sign(private, attestation_signing_bytes(unsigned))})

    before = make_attestation(dt("2026-10-15T10:00:00Z"), "urn:anu:attestation:a202:1")
    assert verify_agent_attestation(session, before).attestation_valid is True

    revoke_delegation(session, DelegationRevocationContract(
        revocation_id="urn:anu:delegation-revocation:a202",
        delegation_id=delegation_id,
        effective_time=dt("2026-10-20T00:00:00Z"),
        recorded_at=dt("2026-10-20T00:01:00Z"),
        actor_ref=human,
        reason="test revocation",
    ))
    after = make_attestation(dt("2026-10-21T10:00:00Z"), "urn:anu:attestation:a202:2")
    result = verify_agent_attestation(session, after)
    assert result.cryptographically_valid is True
    assert result.delegation_valid is False
    assert result.attestation_valid is False
    assert "ACTIVE_DELEGATION_REQUIRED" in result.reason_codes
