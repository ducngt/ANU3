# Phase-1 Executable Architecture — Tranche 03

## Constitutional boundary

The Kernel remains a modular monolith. Logical responsibility boundaries are explicit without requiring network-service fragmentation.

```text
Human purpose / meaning / authority / acceptance
                    |
                    v
              Human Dashboard
                    |
                    v
External IdP -> AuthN Adapter -----------+
                                          |
Kernel API -> PEP ------------------------+--> Authority / Delegation
           |                              +--> Policy Decision
           |                              +--> Trust Registry
           |                              +--> Signature / Attestation verification
           |
           +-> Identity / Semantics
           +-> Role / Competence
           +-> Provenance / Audit
           +-> Lifecycle / Events
           +-> Historical Replay
                    |
                    v
        versioned relational persistence
```

`LAYER != HOP`: these are contract/responsibility boundaries, not mandatory microservices.

## Authentication, authorization and authority

Authentication answers who is interacting and maps verified external credential claims to an existing ANU Identity. The AuthN adapter cannot create Authority. The PEP independently evaluates current Authority/Delegation and versioned Policy.

`AUTHENTICATION != AUTHORIZATION != AUTHORITY` is enforced structurally rather than by naming convention.

## Trust Registry

Trust Registry stores credential validation metadata: subject binding, public key, fingerprint, issuer, validity period, status and revocation metadata. Private keys are outside Kernel persistence.

The Tranche-03 reference verifier supports Ed25519 detached signatures. This is a provider-independent reference mechanism, not a declaration that one cryptographic profile is the institutional/legal standard.

## Human Signature

A cryptographically valid signature becomes institutionally valid only when all of these are independently valid at signature time:

1. credential binding and lifecycle;
2. detached signature over the canonical signature statement;
3. active signer role;
4. referenced institutional Authority.

Therefore `SIGNATURE != AUTHORITY` and `SIGNED != TRUE` remain intact.

## Agent Attestation

Agent Attestation records Agent identity/version, owner, runtime, model dependency, purpose, work, action, capability/tool, delegation, policy version, input references, artifact hash, time, credential and attestation signature.

A consequential Agent attestation requires an active delegation at the attestation effective time. It never becomes Human approval.

## Migration and database portability

Alembic remains the sole deployed schema migration mechanism. Revision `0002` introduces Trust Registry, Signature Record and Agent Attestation persistence. Runtime engine creation is lazy, allowing PostgreSQL migration SQL to compile in offline architecture verification without loading a DBAPI driver.

GitHub Actions includes a PostgreSQL 16 live lane for migration, ARU-01 trust-chain execution and backup/restore verification.

## Backup / restore

The backup adapter uses the SQLite backup API for the executable reference environment and `pg_dump`/`pg_restore` for PostgreSQL. Verification must prove institutional history survives restore; a successful backup command alone is insufficient evidence.

## Human-directed delivery boundary

Technical verification remains an AI/CI responsibility. If live PostgreSQL evidence is unavailable, the Work is shown as a technical blocker rather than asking Human to inspect CI, execute commands or waive an engineering check.
