# P1-T03 GitHub Actions / PostgreSQL CI Activation

Status: READY_TO_PUBLISH
Date: 2026-09-25
Human pilot: OK
Human G3: NOT YET REQUESTED

## Purpose

Provide repeatable external evidence for the remaining Tranche 03 technical blocker without asking Human to run migration, PostgreSQL, backup/restore, pytest, or Swagger manually.

## CI evidence path

1. Locate the ANU Phase 1 project at repository root or `anu-phase1-kernel/`.
2. Run local contract/migration/conformance verification.
3. Start PostgreSQL 16 as an isolated GitHub Actions service.
4. Apply Alembic migrations to a clean PostgreSQL database.
5. Run the ARU-01 Programme Revision Trust Chain pilot on PostgreSQL.
6. Create a PostgreSQL custom-format backup.
7. Restore to a separate clean database.
8. Prove institutional decision history is present after restore.
9. Run an independent verifier and independently qualify the PostgreSQL evidence.
10. Publish machine-readable artifacts plus a Human-readable Actions summary.

## Guardrails

- CI evidence does not constitute Human G3 acceptance.
- No production credentials are used.
- PostgreSQL credentials are ephemeral test credentials scoped to the workflow service container.
- A valid signature does not create authority.
- Agent attestation does not replace Human approval.
- Failure of any live PostgreSQL or independent qualification check fails the workflow.

## Human role

Human enables/allows repository Actions and later reviews the qualified outcome/evidence packet. Human does not run CI steps or inspect implementation details by default.
