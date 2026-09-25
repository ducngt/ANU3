# G3 Human Acceptance Report — Phase 1 Tranche 02

## Human-readable outcome

Status: **VERIFIED_FOR_G3**  
Human Gate: **G3_READY**

The delivery flow has been corrected to the ANU Handbook model: Human provides intent/meaning/authority/acceptance; AI performs implementation, migration, tests, conformance and verification. Human is no longer expected to operate Swagger, Alembic or pytest.

## Architecture delta

- API runtime no longer silently creates database schema; Alembic owns migration history.
- Root route now opens a Human Dashboard rather than a technical 404.
- Duplicate canonical identities and other primary-key conflicts return deterministic `409 RESOURCE_CONFLICT`, not HTTP 500.
- Delegation revocation, Audit, Lifecycle Transition and Policy Decision endpoints are exposed through Kernel contracts.
- Policy evaluation is conservative and fail-closed; it is deliberately not a general-purpose business-rule engine.

## Contract/schema delta

Added machine-readable contracts for delegation revocation and policy-evaluation request. Existing contracts remain backward-compatible in this tranche.

## Verification evidence

- clean_migration_cycle: **PASS**
- automated_tests: **PASS**
- aru01_end_to_end_pilot: **PASS**
- contract_schema_export: **PASS**

- independent_verifier: **PASS**

## Security / trust analysis

The Kernel continues to enforce CAPABILITY != AUTHORITY, AUTHORITY != COMPETENCE and AGENT IDENTITY != PERMANENT AUTHORITY. Missing applicable policy fails closed. Delegation remains bounded, time-limited and revocable.

## Migration / compatibility impact

No database schema change was required for Tranche 02. Runtime schema auto-creation was removed to prevent migration drift. Clean upgrade/downgrade/re-upgrade is verified automatically.

## Known limitations / residual risk

- Production-grade AuthN/AuthZ adapter is not yet integrated; Phase 1 keeps authentication separate from institutional authority.
- Cryptographic signature/attestation verification and Trust Registry remain a later trust-hardening tranche.
- PostgreSQL-native integration and backup/restore evidence are not yet demonstrated; SQLite is used for this executable reference verification.
- This is Tranche 02 verification, not a declaration that all Phase 1 exit criteria are institutionally accepted.

## Open Human decision — G3

Decision needed: Does this tranche preserve the intended ANU meaning, authority boundaries and acceptable pilot behavior?

Options: **Accept / Require change / Reject**. Technical implementation choices are not part of the default Human review.
