from __future__ import annotations

import argparse
import base64
import json
from datetime import datetime
from pathlib import Path

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from sqlalchemy.orm import sessionmaker

from anu_kernel.contracts import AgentAttestationContract, SignatureRecordContract, TrustCredentialContract
from anu_kernel.db import make_engine
from anu_kernel.repository import add_trust_credential
from anu_kernel.trust import (
    attestation_signing_bytes,
    public_key_fingerprint_sha256,
    signature_signing_bytes,
    verify_agent_attestation,
    verify_signature_record,
)
from aru01_pilot import run_pilot


def dt(s: str) -> datetime:
    return datetime.fromisoformat(s.replace("Z", "+00:00"))


def key_material():
    private = Ed25519PrivateKey.generate()
    pem = private.public_key().public_bytes(
        serialization.Encoding.PEM,
        serialization.PublicFormat.SubjectPublicKeyInfo,
    ).decode("utf-8")
    return private, pem


def sign(private: Ed25519PrivateKey, payload: bytes) -> str:
    return base64.b64encode(private.sign(payload)).decode("ascii")


def run_trust_pilot(database_url: str) -> dict:
    base = run_pilot(database_url)
    if not base["pass"]:
        return {"scenario": "ARU-01 Trust Chain", "pass": False, "base_pilot": base}

    engine = make_engine(database_url)
    Session = sessionmaker(bind=engine, future=True)
    human = "urn:anu:human:h003"
    agent = "urn:anu:agent:qa-01"
    human_private, human_pem = key_material()
    agent_private, agent_pem = key_material()

    with Session() as session:
        add_trust_credential(session, TrustCredentialContract(
            credential_id="urn:anu:credential:sign:h003",
            subject_ref=human,
            public_key_pem=human_pem,
            fingerprint_sha256=public_key_fingerprint_sha256(human_pem),
            issuer_ref="urn:anu:trust:aru",
            valid_from=dt("2026-01-01T00:00:00Z"),
        ))
        add_trust_credential(session, TrustCredentialContract(
            credential_id="urn:anu:credential:agent:qa-01",
            subject_ref=agent,
            public_key_pem=agent_pem,
            fingerprint_sha256=public_key_fingerprint_sha256(agent_pem),
            issuer_ref="urn:anu:trust:aru",
            valid_from=dt("2026-01-01T00:00:00Z"),
        ))

        unsigned_signature = SignatureRecordContract(
            signature_id="urn:anu:signature:programme-revision-001",
            signer_identity_ref=human,
            signer_role_ref="urn:anu:semantic:role:programme-owner",
            authority_ref="urn:anu:authority:programme-owner-approve",
            credential_ref="urn:anu:credential:sign:h003",
            intent="Approve programme revision",
            artifact_ref="urn:anu:programme:software-engineering",
            artifact_version="1.3",
            artifact_hash="sha256:programme-revision-001",
            work_ref="urn:anu:work:programme-revision-001",
            decision_ref="urn:anu:decision:programme-revision-001",
            policy_version="urn:anu:policy:academic-approval@1.0.0",
            signed_at=dt("2026-10-15T10:00:00Z"),
            signature_value="",
            provenance_ref="urn:anu:provenance:programme-revision-001",
        )
        human_signature = unsigned_signature.model_copy(update={
            "signature_value": sign(human_private, signature_signing_bytes(unsigned_signature))
        })
        human_verify = verify_signature_record(session, human_signature)
        tampered_verify = verify_signature_record(
            session,
            human_signature.model_copy(update={"artifact_hash": "sha256:tampered"}),
        )

        unsigned_attestation = AgentAttestationContract(
            attestation_id="urn:anu:attestation:qa-01:programme-revision-001",
            agent_ref=agent,
            agent_version="qa-agent@1.0.0",
            owner_ref="urn:anu:org:aru:qa",
            runtime_ref="urn:anu:runtime:reference",
            model_dependency="replaceable:model",
            purpose="Bounded programme precheck",
            work_ref="urn:anu:work:programme-revision-001",
            action="academic.programme.approve",
            capability_ref="urn:anu:capability:academic.programme.approve",
            tool_ref="urn:anu:tool:qa-precheck",
            delegation_ref="urn:anu:delegation:qa-precheck-oct2026",
            policy_version="urn:anu:policy:academic-approval@1.0.0",
            input_refs=["urn:anu:artifact:programme-proposal@1.3"],
            artifact_ref="urn:anu:artifact:qa-precheck@1.0",
            artifact_hash="sha256:qa-precheck-001",
            timestamp=dt("2026-10-15T09:30:00Z"),
            credential_ref="urn:anu:credential:agent:qa-01",
            attestation_signature="",
            provenance_ref="urn:anu:provenance:programme-revision-001",
        )
        attestation = unsigned_attestation.model_copy(update={
            "attestation_signature": sign(agent_private, attestation_signing_bytes(unsigned_attestation))
        })
        attestation_verify = verify_agent_attestation(session, attestation)

    checks = {
        "base_authority_delegation_replay": base["pass"],
        "human_signature_institutionally_valid": human_verify.institutional_valid,
        "tamper_detection": not tampered_verify.cryptographically_valid,
        "agent_attestation_valid_with_active_delegation": attestation_verify.attestation_valid,
        "signature_does_not_replace_authority": human_verify.authority_valid,
    }
    return {
        "scenario": "ARU-01 Programme Revision Trust Chain",
        "checks": checks,
        "pass": all(checks.values()),
        "human_signature": human_verify.model_dump(mode="json"),
        "tampered_signature": tampered_verify.model_dump(mode="json"),
        "agent_attestation": attestation_verify.model_dump(mode="json"),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--database-url", required=True)
    parser.add_argument("--output")
    args = parser.parse_args()
    result = run_trust_pilot(args.database_url)
    payload = json.dumps(result, ensure_ascii=False, indent=2)
    if args.output:
        Path(args.output).write_text(payload + "\n", encoding="utf-8")
    print(payload)
    return 0 if result["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
