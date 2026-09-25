# P3 Regression Verification Fix

## Root cause

The accepted P2-T02/P3-01 regression verifier encoded two implementation-state assumptions as exact release criteria:

- schema export had to report exactly 50 schemas;
- the live database head had to equal Alembic revision `0004`.

P3 Runtime is an additive release. It legitimately adds schemas and migration `0005`, so those exact-value checks produced false regression failures even while the accepted P2-T02/P3-01 behavior continued to pass.

## Correction

The regression gate now checks compatibility rather than frozen repository size:

- schema export must succeed, retain all required P2-T02/P3-01 baseline schemas, and contain at least the accepted baseline count;
- PostgreSQL must migrate cleanly to the repository's current Alembic head;
- accepted baseline revision `0004` must remain in the current migration ancestry;
- the P2-T02/P3-01 pilot, recovery, provenance, retrieval, capability registry and provider-replaceability evidence must still pass;
- independent evidence qualification accepts additive later heads only when the baseline checks remain true.

This keeps the accepted baseline protected while allowing versioned additive evolution.
