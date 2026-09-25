# Changelog

## 0.6.0 — P3-02..P3-07 SBBS Capability Runtime

- Recorded `P2-T02 + P3-01 G3 ACCEPTED` as the new baseline.
- Added Compatibility Engine with machine-readable evidence and fail-closed connection planning.
- Added versioned Transform and Adapter registries.
- Added declarative Connection Planner.
- Added Thin Smart Wire runtime with policy/security gates, transform/adapter execution and tracing; no discovery/planning logic in Wire.
- Added Assembly Registry/Runtime with explicit connection composition and persisted execution trace.
- Added Write Box Studio MVP with Discover-before-Build, architecture audit and controlled promotion.
- Demonstrated provider replacement behind an unchanged Capability Contract.
- Added Alembic revision `0005`.
- Exported 67 executable JSON Schemas.
- Added ARU-01 full SBBS runtime pilot, recovery/replay and independent P3 boundary verifier.
- Local verification passes; live PostgreSQL revision `0005` evidence remains the external CI gate before G3.

## 0.5.0 — P2-T02 multimodal memory + P3 capability contract foundation

- Recorded P2-T01 Human G3 acceptance as the new Phase 2 baseline.
- Added content-addressed immutable Object Store Adapter and real-byte multimodal ingestion.
- Added PDF/DOCX deterministic extraction and image/audio/video media metadata analysis.
- Added source lifecycle/effective-time validation at ingestion.
- Added immutable artifact versions, supersede history and tamper verification.
- Added Artifact -> Knowledge provenance materialization preserving Epistemic Type/Validation State.
- Added University Memory retrieval projection and hybrid lexical/hash-vector reference retrieval.
- Added Capability Contract, Capability Registry, Smart Box Manifest and semantic discovery.
- Enforced `CAPABILITY != AUTHORITY` by excluding institutional authority from capability/box contracts.
- Demonstrated provider replaceability with two Smart Box manifests for one Capability Contract.
- Added database + object-store recovery verification.
- Added Alembic revision `0004`.
- Exported 50 executable JSON Schemas.
- Full local verification and independent boundary audit pass; live PostgreSQL revision `0004` evidence remains the external CI gate before G3.

## 0.4.0 — Phase 2 Reality/Data/Memory foundation

- Preserved the Human-accepted Phase 1 Tranche 03 baseline and added Phase 2 additively.
- Added Source Registry and scoped Source Authority Mapping.
- Added Data Contract and versioned institutional Data Envelope.
- Added independent Epistemic Type and Validation State.
- Added fail-closed source-authority checks for official-like Fact/Evidence/Decision state.
- Prevented in-place epistemic mutation; governed promotion requires a distinct object with provenance.
- Added bitemporal historical projection for data versions.
- Added Knowledge Object versioning and metadata-first object/document ingestion.
- Added Provenance graph traversal reusing Phase 1 provenance primitives.
- Added University Memory index with mandatory source/provenance linkage.
- Added portable baseline search/retrieval across Data, Knowledge and Memory.
- Added Alembic revision `0003`.
- Added ARU-01 synthetic Reality/Data/Memory pilot and Phase 2 verification tooling.
- Exported 39 executable JSON Schemas.
- Local Phase 2 verification passes; live PostgreSQL evidence remains the technical gate before G3.

## 0.3.0 — Trust, AuthN/PEP and persistence hardening

- Added external JWT authentication adapter boundary without institutional Authority creation.
- Added fail-closed Policy Enforcement Point composing authentication, Authority/Delegation and versioned Policy.
- Added Trust Registry public-key credential metadata.
- Added Ed25519 Human Signature verification with separate credential, role, authority and integrity checks.
- Added Agent Attestation verification requiring active delegation for consequential actions.
- Added canonical SHA-256 integrity references and tamper-detection tests.
- Added Alembic revision `0002` for trust credentials, signatures and Agent attestations.
- Refactored runtime DB engine creation to lazy initialization, enabling PostgreSQL offline migration compilation without a DBAPI driver.
- Added SQLite/PostgreSQL backup/restore adapters and restore-evidence checks.
- Added PostgreSQL 16 live verification CI lane and independent Trust boundary tests.
- Exported 27 executable JSON Schemas.
- Tranche remains G3-not-ready until live PostgreSQL evidence is attached.

## 0.2.0 — Human-directed delivery correction

- Removed runtime `Base.metadata.create_all()` to restore migration discipline.
- Added deterministic 409 conflict behavior for duplicate canonical records.
- Added delegation revocation, audit, lifecycle-transition and policy-evaluation API surfaces.
- Added fail-closed baseline policy decision service.
- Added ARU-01 automated pilot runner.
- Added automated migration/test/contract/pilot verification and separate independent verifier.
- Added Human Dashboard and G3 acceptance evidence generation.
- Removed the bundled runtime SQLite database from the release package.
