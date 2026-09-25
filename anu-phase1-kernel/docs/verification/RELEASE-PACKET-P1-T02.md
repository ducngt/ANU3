# Human-facing Release Packet — P1-T02

## 1. Human-readable summary

Tranche 02 corrects the delivery model to Human-directed / AI-executed and hardens the existing Phase-1 Kernel without changing the approved canonical meaning or authority model.

## 2. Architecture delta

- Runtime schema auto-create removed; Alembic is authoritative for schema migration.
- Human Dashboard added at `/human`; root redirects there.
- Technical API remains at `/docs` but is not a Human acceptance surface.
- Policy Decision, Delegation Revocation, Audit and Lifecycle transition surfaces completed for the current Phase-1 model.

## 3. Contract/schema delta

Added:

- `anu.delegation-revocation.v1`
- `anu.policy-evaluation-request.v1`

Existing public Phase-1 contracts are preserved.

## 4. Implementation

- deterministic repository conflict handling (`409 RESOURCE_CONFLICT`);
- fail-closed policy decision baseline;
- automated ARU-01 pilot runner;
- automated migration/test/schema/pilot verification;
- independent verifier and GitHub Actions verification workflow;
- Human Dashboard and machine-readable G3 status.

## 5. Tests

The automated suite includes unit, API, conformance, replay, policy and independent-release checks. See `LATEST.json` and `TECHNICAL-DETAILS-P1-T02.json`.

## 6. Security / trust analysis

Preserved invariants include CAPABILITY != AUTHORITY, AUTHORITY != COMPETENCE and AGENT IDENTITY != PERMANENT AUTHORITY. Missing applicable policy fails closed. Delegation cannot broaden delegator scope and revocation stops future use.

## 7. Migration / compatibility impact

No new DB schema migration is required for this tranche. The major operational change is removal of runtime `create_all`; deployments must apply Alembic migration before starting the API. Automated verification proves clean upgrade/downgrade/re-upgrade.

## 8. Verification evidence

See `LATEST.json`. G3 is exposed only when all primary technical checks and the independent verifier pass.

## 9. Open Human decisions

G3 only: Accept / Require change / Reject based on meaning, authority/responsibility, outcome, evidence, limitations and residual risk.

## 10. Documentation update

Updated README, architecture, changelog, AI change envelope, Human Dashboard and G3 acceptance report.
