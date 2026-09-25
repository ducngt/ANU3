# ADR-0008 — Governed Human–AI Work Runtime

## Context
P3 provides reusable Capability/Assembly execution but does not define institutional Work responsibility, Human/Agent coordination, approval, handover or responsibility replay.

## Decision
Create one governed execution runtime with versioned Work Contract, Governed Work Graph, Human/Agent/Capability tasks, Authority/Policy gates, approval/signature nodes, failure/handover/recovery and persistent trace/replay.

Execution Planner consumes approved Work meaning/risk and may select an allowed graph/capabilities, but it cannot create Authority, Policy, DataScope, Signature Requirement or institutional exceptions.

## Consequences
- Human judgment/authority remains explicit in E3.
- Agent identity/capability never creates Authority.
- Failure stops execution and preserves a replayable state/handover record.
- Phase 4 consumes P1/P2/P3 contracts without semantic redefinition.

## Migration / rollback
Alembic `0006`; downgrade removes only Phase 4 runtime tables and returns to accepted P3 `0005` baseline.
