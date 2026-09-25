# P1-T03 Change Envelope — Trust/AuthN Hardening

## Human-approved basis

G0/G1/G2 remain inherited from the accepted Phase-1 model. Tranche 02 G3 was accepted. No new Human meaning/authority decision is introduced by this tranche.

## Technical scope owned by AI

- AuthN adapter boundary.
- PEP composition.
- Trust Registry credential metadata.
- Human Signature verification.
- Agent Attestation verification.
- Integrity hashing.
- Alembic 0002 migration.
- backup/restore adapters and evidence.
- PostgreSQL portability/live-CI path.
- tests, schemas, evidence and independent verification.

## Guardrails

- Authentication cannot create Authority.
- Signature cannot create Authority.
- Agent Attestation cannot become Human approval.
- Private keys are not persisted in Kernel.
- Missing Authority/Policy/Delegation fails closed.
- History must survive backup/restore.

## Human gate

No Human gate is requested until live PostgreSQL technical evidence passes.
