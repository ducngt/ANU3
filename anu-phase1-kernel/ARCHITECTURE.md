# ANU Executable Architecture — P2-T02 + P3-00/P3-01

## Baselines

- Phase 1 Tranche 03: Human G3 accepted; G4 pilot-institutionalized.
- Phase 2 Tranche 01: Human G3 accepted.
- P2-T02 and P3-00/P3-01 are additive, versioned extensions. They do not redefine Identity, Authority, Policy, Provenance, Trust, Event, Lifecycle, Data Contract or Epistemic primitives.

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
 Source Registry -> Authority Mapping -> Data/Artifact versions
                    |                         |
                    |                 Content-addressed
                    |                  Object Store Adapter
                    |                         |
                    +------> Extraction/Metadata
                                      |
                              Knowledge Object
                                      |
                         University Memory Index
                                      |
                      Lexical + Vector Retrieval
                                      |
                    source + provenance returned
                    |
                    v
       Capability Contract Foundation (P3)
 Capability Registry -> Smart Box Manifest -> Discovery
                    |
         NO execution/authority promotion yet
```

`LAYER != HOP`: these are logical responsibility and contract boundaries. The reference deployment remains a modular monolith.

## Source authority and epistemic governance

`SOURCE AUTHORITY != STORAGE LOCATION` and `MEMORY != SOURCE OF TRUTH` remain mandatory. Official-like state (`FACT`, `EVIDENCE`, `DECISION`) fails closed without a matching active/effective source-authority mapping. Source lifecycle/effective time is checked at ingestion time.

Epistemic Type and Validation State remain independent. Ingestion/extraction never promotes a file into Fact/Decision. Artifact versions cannot mutate epistemic type in place; a governed transition must create a distinct derived object and preserve provenance.

## P2-T02 multimodal ingestion

The ingestion boundary accepts real bytes for PDF, DOCX, image, audio, video and text artifacts. Bytes are written through a content-addressed Object Store Adapter using SHA-256. The institutional reference is stable (`urn:anu:object:sha256:<digest>`) and the provider-specific filesystem path is hidden behind the adapter.

Deterministic analyzers:

- PDF: text/page extraction through a PDF adapter;
- DOCX: paragraphs/tables through a DOCX adapter;
- image: governed artifact + image metadata;
- WAV/audio: governed artifact + media metadata;
- video/audio: governed artifact + ffprobe metadata where available;
- text: UTF-8 extraction.

Extraction failure does not delete the artifact. The immutable artifact remains recorded with `FAILED` extraction status and integrity/provenance.

OCR, speech transcription and video semantic analysis are deliberately provider adapters for later versioned upgrades; they are not hidden inside the Core.

## Artifact -> Knowledge -> Memory provenance

Materializing Knowledge from an ingested artifact creates a new Knowledge Object with its own provenance record derived from the artifact provenance. The artifact's epistemic type and validation state are preserved by deterministic extraction. University Memory records point back to artifact/knowledge sources and provenance; Memory remains an index/history fabric, not the authoritative source.

## Retrieval

P2-T02 introduces a provider-neutral retrieval projection. The reference provider combines lexical overlap and a deterministic hashing-vector baseline. Every returned hit carries source references, provenance reference and content hash where applicable.

The hashing vector is a replaceable reference implementation, not an institutional source of truth and not a production model commitment.

## P3-00/P3-01 Capability contract foundation

P3 opens only the contract/catalog surface:

- versioned Capability Contract;
- Capability Registry;
- versioned Smart Box Manifest;
- operation-to-handler binding metadata;
- discovery by operation, domain and semantic inputs/outputs;
- multiple provider manifests can satisfy the same capability contract.

`CAPABILITY != AUTHORITY` is enforced structurally: Capability/Smart Box contracts do not confer or embed institutional Authority. A Box can only declare implementation bindings, dependencies, data classes, policy references, quality SLO and observability metadata.

Connection Planner, Smart Wire execution, Assembly runtime and Write Box Studio are intentionally outside this tranche.

## Recovery model

Database state and content-addressed object storage are recovered as separate logical stores. Verification requires both:

1. database migration/backup/restore;
2. object-store copy/restore;
3. post-restore artifact integrity verification;
4. retrieval with provenance after restore;
5. Capability/Box discovery after restore.

## Migration and compatibility

Alembic revision `0004` adds artifact versions, retrieval projections, Capability Registry and Smart Box Manifest Registry. Revision `0003` remains the accepted P2-T01 baseline. Downgrade returns to `0003` without rewriting prior institutional history.

## Human-directed delivery boundary

Human-approved ARU-01 synthetic-data scope and P2 Source Authority/Epistemic G2 guardrails remain unchanged. P2-T02 uses only synthetic fixtures and therefore does not open a new privacy G2. Real SIS/LMS/HR or personal data remains a separate Human G2 decision.

AI/CI owns implementation, migration, tests, replay/recovery and conformance. Human G3 is opened only after the live PostgreSQL CI evidence for revision `0004` has been independently qualified.
