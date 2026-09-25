# ADR-0005 — Multimodal ingestion, object storage and retrieval boundary

## Context
P2-T02 must ingest real multimodal artifacts while preserving source authority, epistemic classification, integrity and provenance without locking the Core to one storage/search/AI vendor.

## Decision
Use content-addressed SHA-256 institutional object references behind an Object Store Adapter. Store artifact versions separately from bytes. Extraction/analyzer providers are adapters. Retrieval projects governed records into a replaceable lexical/vector index and returns source/provenance with every hit.

## Consequences
- Storage location never becomes source authority.
- Extraction failure does not delete evidence/history.
- OCR/ASR/video-analysis providers can evolve without changing institutional contracts.
- Database and object-store recovery must both be verified.

## Migration / rollback
Revision `0004`; downgrade returns to `0003`. Existing P2-T01 data is unchanged.
