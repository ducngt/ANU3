# ANU Kernel + P2 Reality/Memory + P3 SBBS Capability Runtime

Executable reference implementation under ANU-URA-1.0, ANU-HB-1.2 and SBBS 2.0.

## Human-directed / AI-executed delivery

Human owns purpose, meaning, institutional authority, standards, responsibility and acceptance. AI/CI owns architecture, contracts, implementation, migrations, tests, replay, audit, conformance and technical evidence. Human does not need to run Swagger, Alembic, pytest or PostgreSQL by default.

## Accepted baselines

- Phase 1 Tranche 03: G3 accepted; G4 pilot-institutionalized.
- Phase 2 Tranche 01: G3 accepted.
- P2-T02 + P3-01: G3 accepted.

## P3-02..P3-07 scope

- Compatibility Engine across Capability, semantic I/O, contract/schema, constraints, permissions, security and policy;
- versioned Adapter/Transform Registry;
- declarative Connection Planner with mandatory compatibility evidence;
- Thin Smart Wire runtime: route, transform, adapter boundary, policy/security gate, retry metadata, tracing/observability — no discovery/planning/business logic;
- Assembly Registry/Runtime with explicit composition;
- Write Box Studio MVP: Discover-before-Build, Contract-before-Code, architecture audit, sandbox candidate and controlled promotion;
- provider replacement behind an unchanged Capability Contract;
- recovery/replay of connection plans and assemblies;
- ARU-01 synthetic end-to-end SBBS runtime pilot.

## Verification state

Local verification for version `0.6.0` passes:

- Alembic `0001 -> ... -> 0005`, downgrade to base, re-upgrade;
- full automated test suite;
- ARU-01 Write Box -> register -> discover -> match -> plan -> assemble -> execute pilot;
- transform + adapter execution path;
- provider replacement preserves consumer contract;
- 67 executable JSON Schemas;
- PostgreSQL offline migration compilation;
- backup/restore + post-restore Assembly replay;
- independent Thin Wire / authority / compatibility-evidence boundary audit.

Live PostgreSQL revision `0005` runtime/recovery evidence remains the external GitHub Actions gate before Human G3.

## Runtime boundary

`CAPABILITY != AUTHORITY`. Smart Wire executes a pre-approved declarative Connection Plan; it does not discover or select capabilities. Write Box can create/version capability packages but cannot grant authority or modify Constitutional Core.

## AI/CI verification

```bash
python scripts/verify_p3_runtime.py
```

## Runtime

```bash
alembic upgrade head
uvicorn anu_kernel.api:app --app-dir src --host 0.0.0.0 --port 8000
```
