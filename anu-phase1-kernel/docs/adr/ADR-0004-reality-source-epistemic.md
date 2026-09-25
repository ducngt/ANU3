# ADR-0004 — Reality/Data source authority and epistemic governance

## Context

Phase 2 introduces Data Envelope/Contract, Source Registry, temporal projection, Knowledge Object and University Memory while preserving the Phase 1 constitutional Kernel.

## Decision

- Source-of-authority is registered by semantic type and scope; storage location does not imply authority.
- Epistemic Type and Validation State are independent dimensions.
- A Data Object cannot mutate its epistemic type in place. A governed transition from inference/claim to an official fact/decision creates a distinct object with provenance rather than rewriting the old record.
- Official-like Data Objects (`FACT`, `EVIDENCE`, `DECISION`) fail closed without a matching authoritative source mapping.
- University Memory stores index records that retain `source_ref` and `provenance_ref`; it does not become a competing source-of-record.
- Phase 1 Provenance primitives and Event Envelope are reused rather than duplicated.

## Consequences

This is deliberately conservative. It makes epistemic promotion explicit and replayable, prevents AI output from silently becoming institutional truth, and keeps future provider/storage replacement behind contracts/adapters.

## Migration / rollback

Alembic revision `0003` adds only Phase 2 tables. Downgrade returns to revision `0002` without rewriting Phase 1 history.
