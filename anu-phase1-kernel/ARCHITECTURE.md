# ANU Executable Architecture — Phase 2 Tranche 01

## Baseline

Phase 1 Tranche 03 is the accepted Constitutional Kernel baseline. Phase 2 extends it additively; it does not redefine Identity, Authority, Policy, Provenance, Trust, Event or Lifecycle primitives.

```text
Human purpose / meaning / authority / acceptance
                    |
                    v
            Constitutional Kernel
 Identity · Semantics · Authority · Policy · Trust
 Provenance · Audit · Lifecycle · Replay · Events
                    |
                    v
          Reality / Data / Memory Fabric
   +----------------+------------------------+
   |                |                        |
Source Registry  Data Contracts        Knowledge Objects
   |                |                        |
Authority Map -> Data Envelope versions      |
                    |                        |
             Temporal Projection             |
                    +-----------+------------+
                                |
                         Provenance Graph
                                |
                      University Memory Index
                                |
                         Search / Retrieval
```

`LAYER != HOP`: the boundaries above are logical ownership/contract boundaries and remain deployable as a modular monolith in the reference implementation.

## Source authority

A storage system does not become authoritative merely because it contains data. Source Authority Mapping binds a registered source to a semantic type and bounded authority scope.

Official-like state (`FACT`, `EVIDENCE`, `DECISION`) fails closed unless a matching authoritative source mapping exists. AI inference stores may hold `INFERENCE`, `PREDICTION` and `RECOMMENDATION` without acquiring authority over official records.

## Epistemic governance

Epistemic Type and Validation State are independent axes. Validation does not change what kind of knowledge an object is.

The reference implementation forbids in-place epistemic mutation for a Data Object. A governed transition from inference/claim to official state must create a distinct object linked by provenance. This makes the transition explicit and replayable.

## Data Contract and Envelope

The Data Contract follows the URA contract shape: identity/version, semantic definition, schema, owner, authoritative source, producers/consumers, freshness, quality, provenance, access/privacy, integrity, retention and compatibility policy.

The Data Envelope carries global identity, contract/schema version, source record and authority scope, owner/context, bitemporal metadata, epistemic/validation state, provenance/integrity, policy references, lifecycle and payload.

## Temporal projection

Consequential state is stored as append-only versions. Projection is reconstructed by effective time and optionally by recorded time. The ARU-01 pilot proves that Programme v1 can still be reconstructed after v2 becomes current.

## Provenance and University Memory

Phase 2 reuses the Phase 1 Provenance Record rather than creating a competing lineage system. Graph traversal follows `previous_provenance_refs`.

University Memory is an institutional index over decisions/actions/outcomes/failures/changes/capabilities/knowledge. Every memory record retains `source_ref` and `provenance_ref`; Memory does not replace the authoritative source.

## Ingestion and retrieval

The tranche registers object/document metadata, media type, source, owner, integrity reference and provenance. Binary object storage remains behind future provider adapters.

Search/retrieval is intentionally a portable lexical baseline across Data, Knowledge and Memory. Production search/vector providers are replaceable implementation concerns, not semantic authorities.

## Migration and compatibility

Alembic revision `0003` adds only Phase 2 tables. Phase 1 contracts/APIs remain available. Downgrade removes Phase 2 tables and returns to the accepted revision `0002` without rewriting Phase 1 history.

## Human-directed delivery boundary

ARU-01 synthetic data scope and Source Authority/Epistemic guardrails were approved at G0/G1/G2. AI/CI owns implementation and verification. Human G3 is requested only after live PostgreSQL evidence clears the remaining technical gate.
