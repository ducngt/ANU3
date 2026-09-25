# ANU Kernel + P2 Multimodal Memory + P3 Capability Contract Foundation

Executable reference implementation under ANU-URA-1.0 and ANU-HB-1.2.

## Human-directed / AI-executed delivery

Human owns purpose, meaning, institutional authority, standards, responsibility and acceptance. AI/CI owns repository discovery, architecture, contracts, implementation, migration, tests, conformance, technical verification and evidence preparation.

Human does **not** need to operate Swagger, Alembic, pytest or PostgreSQL by default. `/human` is the Human-facing status surface; `/docs` remains a technical surface.

## Accepted baselines

- Phase 1 Tranche 03: G3 accepted, G4 pilot-institutionalized.
- Phase 2 Tranche 01: G3 accepted.

## P2-T02 scope

- real-byte ingestion for PDF, DOCX, image, audio, video and text;
- content-addressed immutable Object Store Adapter with SHA-256 integrity;
- source lifecycle/effective-time checks and fail-closed source authority;
- deterministic PDF/DOCX extraction and media metadata adapters;
- extraction failure retention rather than destructive discard;
- Artifact -> Knowledge provenance chain with epistemic type preserved;
- University Memory projection with source/provenance linkage;
- lexical + provider-neutral hashing-vector retrieval baseline;
- retrieval results include source refs, provenance refs and content hash;
- database + object-store recovery proof.

## P3-00/P3-01 scope

- Capability Contract;
- Capability Registry;
- Smart Box Manifest;
- discovery by operation/domain/semantic I/O;
- replaceable provider manifests for the same Capability Contract;
- `CAPABILITY != AUTHORITY` enforced by contract structure.

P3 execution runtime is **not** opened yet: Connection Planner, Smart Wire, Assembly and Write Box Studio remain later versioned work.

## Verification state

Local verification for version `0.5.0` passes:

- Alembic `0001 -> 0002 -> 0003 -> 0004`, downgrade to base, re-upgrade;
- full automated test suite;
- ARU-01 five-format multimodal pilot;
- Artifact -> Knowledge provenance replay;
- University Memory indexing/retrieval;
- Capability Registry + two-provider Smart Box discovery;
- 50 executable JSON Schemas;
- PostgreSQL offline migration compilation;
- SQLite database + object-store backup/restore with post-restore integrity/retrieval/discovery;
- independent P2-T02/P3 boundary verifier.

Live PostgreSQL revision `0004` migration/pilot/recovery evidence remains the external GitHub Actions gate before Human G3.

## Known reference limitations

Image/audio/video bytes are fully ingested and integrity-governed, but the reference analyzer is metadata-first. OCR, speech transcription and video semantic analysis remain replaceable provider adapters for later upgrades. The vector retriever is a deterministic reference implementation, not a production embedding commitment.

## AI/CI verification

```bash
python scripts/verify_p2t02_p3.py
```

Human-facing evidence is generated into `docs/verification/`.

## Runtime

The application assumes migrations have already been applied by the deployment pipeline. It intentionally does not call `Base.metadata.create_all()` at startup.

```bash
alembic upgrade head
uvicorn anu_kernel.api:app --app-dir src --host 0.0.0.0 --port 8000
```
