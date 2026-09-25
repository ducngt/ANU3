# Security & Trust Analysis — P2-T02 + P3-00/P3-01

## Trust boundaries

1. Uploaded bytes are untrusted input.
2. Source Registry / Source Authority Mapping determine institutional authority; MIME type, filename, storage location and analyzer output do not.
3. Object Store Adapter is an implementation provider, not a source-of-truth authority.
4. Extractors/analyzers can derive metadata/text but cannot promote Epistemic Type or Validation State.
5. Retrieval index is a projection, not source-of-truth.
6. Capability/Smart Box metadata declares ability/implementation only; it cannot confer Authority.

## Controls implemented

- SHA-256 content addressing and post-ingest integrity verification.
- Object paths derived only from validated digest, preventing filename path traversal.
- Configurable ingest size limit (`ANU_MAX_INGEST_BYTES`, default 50 MiB) and bounded streaming in the HTTP upload boundary.
- Source lifecycle/effective-time validation before ingest.
- Fail-closed authoritative-source requirement for Fact/Evidence/Decision.
- Epistemic type immutability across artifact versions.
- Supersede history retained with explicit Lifecycle Transition; prior bytes/provenance are not deleted.
- Extraction failure retained as governed failure state; no silent promotion.
- Retrieval results carry source/provenance/integrity linkage.
- Capability/Smart Box schemas reject undeclared fields and do not contain standing Authority primitives.
- Box operation bindings must be a subset of Capability Contract operations.
- Provider logic is kept behind adapters.

## Residual risks / later hardening

- Production deployments need malware scanning/content sandboxing for uploaded documents/media.
- OCR/ASR/video analysis providers will require model/provider evaluation, privacy and data-residency controls.
- Production semantic retrieval requires embedding-model evaluation and index access controls.
- Real learner/person data requires separate privacy/retention/access G2 approval.
- P3 execution runtime will require Authority/Delegation/Policy enforcement at execution gates; this tranche does not execute Boxes.
