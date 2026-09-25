# P2-T01 Change Envelope — Reality, Data & Memory Foundation

## Human-approved scope

ARU-01 synthetic institutional data only. G0/G1/G2 approved.

## Architecture delta

Adds Source Registry, Source Authority Mapping, Data Contract, Data Envelope versions, bitemporal projection, Knowledge Object versions, metadata-first object/document ingestion, University Memory index, provenance graph traversal and baseline search/retrieval.

## Contract delta

Adds 12 machine-readable Phase 2 contracts while preserving all Phase 1 contracts.

## Security/trust

Official-like state fails closed when source authority/provenance is missing. Synthetic output cannot claim FACT/EVIDENCE/DECISION. Real PII integrations are explicitly out of scope.

## Compatibility

Additive migration `0003`; existing Phase 1 API/contract surfaces remain available.
