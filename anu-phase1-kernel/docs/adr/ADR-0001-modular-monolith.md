# ADR-0001 - Phase-1 deployment baseline

## Context
Phase 1 requires strong semantic and contract boundaries but does not require a
network service per logical module.

## Decision
Use a modular monolith for the initial Kernel. Preserve strict package, contract,
policy/authority, data ownership and observability boundaries. Split physical
services only when scale, isolation, ownership or security evidence justifies it.

## Consequences
- lower early operational complexity;
- easier cross-module conformance tests and refactoring;
- no permission to bypass logical boundaries through direct internal coupling.
