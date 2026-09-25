# ANU Kernel + Phase 2 Reality/Data/Memory

Executable reference implementation under ANU-URA-1.0 and ANU-HB-1.2.

## Human-directed / AI-executed delivery

Human owns purpose, meaning, institutional authority, standards, responsibility and acceptance. AI/CI owns repository discovery, architecture, contracts, implementation, migration, tests, conformance, technical verification and evidence preparation.

Human does **not** need to operate Swagger, Alembic or pytest by default. The Human-facing runtime entry point is `/human`; `/docs` remains a technical surface for AI/engineering verification.

## Accepted Phase 1 baseline

Phase 1 Tranche 03 is Human G3 accepted and G4 institutionalized for **pilot/reference use**. Future changes are versioned upgrades and must preserve its historical evidence.

The accepted Kernel provides Identity, Semantics, Role/Competence, Authority/Delegation, Policy, Provenance/Audit, Lifecycle, Event/Decision contracts, historical replay, AuthN/PEP separation, Trust Registry, Human Signature and Agent Attestation primitives.

## Phase 2 Tranche 01 scope

Phase 2 implements the Reality/Data/Memory foundation with Human-approved ARU-01 synthetic institutional data:

- Source Registry;
- Source Authority Mapping by semantic type and scope;
- Data Contract;
- institutional Data Envelope with effective-time + recorded-time history;
- fail-closed source authority for official-like state;
- independent Epistemic Type and Validation State;
- Knowledge Object versioning;
- metadata-first object/document ingestion with integrity reference;
- Provenance graph traversal using Phase 1 provenance primitives;
- University Memory index that points back to source records rather than becoming a shadow source-of-truth;
- baseline search/retrieval;
- ARU-01 programme/enrollment/learning/inference fixtures and historical projection replay.

## Key Phase 2 invariants

- `SOURCE AUTHORITY != STORAGE LOCATION`
- `MEMORY != SOURCE OF TRUTH`
- `INFERENCE != FACT`
- `PREDICTION != EVIDENCE`
- `RECOMMENDATION != DECISION`
- `SYNTHETIC OUTPUT != AUTHORITATIVE EVIDENCE`
- consequential history is append/supersede, not destructive overwrite

## Verification state

Phase 2 Tranche 01 local verification passes:

- migration `0001 -> 0002 -> 0003`, downgrade to base, and re-upgrade;
- full automated test suite;
- ARU-01 Reality/Data/Memory pilot;
- machine-readable contract schema export;
- PostgreSQL offline migration compilation;
- SQLite reference backup/restore with historical projection replay.

Human G3 is **not requested yet**. Live PostgreSQL migration + Phase 2 pilot + backup/restore evidence remains an AI/CI technical gate.

## AI/CI verification

```bash
python scripts/verify_phase1.py
python scripts/verify_phase2.py
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
