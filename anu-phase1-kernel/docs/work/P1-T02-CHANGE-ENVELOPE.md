# P1-T02 AI Change Envelope

WorkID: `P1-T02-HUMAN-DIRECTED-DELIVERY`

## Goal

Correct the delivery workflow to ANU-HB-1.2: Human does not operate or review technical implementation by default. AI/CI owns build, migration, test, conformance and evidence preparation; Human reviews meaning, authority, outcome, risk and acceptance.

## Allowed change area

- Phase-1 Kernel API/repository/services/contracts.
- ARU-01 automated pilot fixtures/runner.
- tests, migration verification, CI, verification evidence and Human Dashboard.

## Forbidden

- Do not change ANU invariants or canonical meaning without a Human gate.
- Do not create standing institutional authority for Agent identity.
- Do not delete/squash historical provenance for convenience.
- Do not hard-code institutional policy into UI or unrelated business functions.

## Required verification

- clean migration upgrade/downgrade/re-upgrade;
- contract/unit/conformance/API tests;
- ARU-01 end-to-end scenario;
- historical replay;
- independent verifier;
- Human-facing G3 release packet.

## Rollback

Tranche 02 contains no schema migration beyond baseline `0001`. Rollback is source-version rollback plus Alembic `downgrade base` only in disposable verification environments. Institutional history must never be destructively rolled back in production.
