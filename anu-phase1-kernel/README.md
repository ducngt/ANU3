# ANU Phase 1 Kernel

Executable reference implementation of the ANU 4.0 Constitutional Kernel under ANU-URA-1.0 and ANU-HB-1.2.

## Human-directed / AI-executed delivery

Human owns purpose, meaning, institutional authority, standards, responsibility and acceptance. AI/CI owns repository discovery, architecture, contracts, implementation, migration, tests, conformance, technical verification and evidence preparation.

Human does **not** need to operate Swagger, Alembic or pytest by default. The Human-facing runtime entry point is `/human`; `/docs` remains a technical surface for AI/engineering verification.

## Phase-1 scope

- P1-00 Canonical Meta-Model
- P1-01 Identity Kernel
- P1-02 Semantic Registry
- P1-03 Role & Competence Kernel
- P1-04 Authority Kernel
- P1-05 Delegation Kernel
- P1-06 Policy Kernel
- P1-07 Provenance & Audit Kernel
- P1-08 Version & Lifecycle Kernel
- P1-09 Core Contract & Event Model
- P1-10 Conformance & Historical Replay

## Current tranche: 0.3.0 candidate

Tranche 03 hardens the Trust & Control boundary without collapsing the constitutional distinctions:

- external authentication is mapped into ANU Identity but does not create institutional Authority;
- a Policy Enforcement Point composes Authentication, Authority/Delegation and versioned Policy and fails closed;
- Trust Registry stores public-key credential metadata only, never private signing keys;
- Human Signature verification checks cryptographic integrity, credential validity, active role and Authority independently;
- Agent Attestation is separate from Human Signature and consequential Agent attestations require active bounded delegation;
- canonical SHA-256 integrity references detect artifact tampering;
- Alembic revision `0002` adds trust credential, signature and attestation persistence;
- database engine creation is lazy so architecture/migration tooling can compile PostgreSQL DDL without requiring a runtime driver;
- backup/restore adapters cover SQLite reference operation and PostgreSQL target operation;
- GitHub Actions contains a PostgreSQL 16 live verification lane.

## Verification state

Local isolated-environment checks pass, including migration cycle, automated tests, ARU-01 trust-chain pilot, 27 JSON Schema exports, PostgreSQL offline migration compilation, SQLite backup/restore and independent verification.

The Human gate remains **G3_NOT_READY** until live PostgreSQL migration + ARU-01 + backup/restore evidence is produced by an environment that actually provides PostgreSQL. This is a technical blocked-queue item; no Human technical decision is requested.

## AI/CI verification

```bash
python scripts/verify_phase1.py
python scripts/independent_verify.py
```

Human-facing evidence is generated into `docs/verification/`.

## Runtime

The application assumes migrations have already been applied by the deployment pipeline. It intentionally does not call `Base.metadata.create_all()` at startup.

```bash
alembic upgrade head
uvicorn anu_kernel.api:app --app-dir src --host 0.0.0.0 --port 8000
```

Open `/human` for the Human Dashboard. `/docs` is not the default Human acceptance surface.
