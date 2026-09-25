# ADR-0007 — SBBS Capability Runtime

## Context
P3-00/P3-01 established Capability Contract, Smart Box Manifest and discovery. ANU-URA Phase 3 requires compatibility, adapter/transform registry, Connection Planner, Thin Smart Wire, Assembly runtime, Write Box Studio and architecture audit.

## Decision
Implement P3-02..P3-07 as additive, contract-first modules behind the existing P1/P2 primitives.

- Compatibility checks Capability, semantic I/O, contract/schema refs, constraints, permissions, security, policy and provider runtime compatibility.
- No connection may be persisted without machine-readable compatibility evidence.
- Transformations and adapters are versioned registry objects; technology-specific bridging remains in adapters.
- Connection Planner emits a declarative plan and never executes business logic.
- Smart Wire executes an approved plan only: policy/security gate, declarative transform, adapter routing, handler route, trace/observability. It does not discover, match or select capabilities.
- Assembly owns composition and stores explicit capability/connection references.
- Write Box Studio MVP performs Discover-before-Build, contract-first candidate packaging, architecture audit, sandbox verification and controlled promotion.
- Capability/Box/Assembly objects do not confer institutional Authority.

## Consequences
The runtime can replace a provider behind an unchanged Capability Contract, recover/replay persisted plans/assemblies, and add a new capability through Write Box without changing Constitutional Core.

## Rollback
Alembic `0005 -> 0004` removes only P3 runtime tables. P1/P2 and accepted P3-01 contract/registry history remain intact.
