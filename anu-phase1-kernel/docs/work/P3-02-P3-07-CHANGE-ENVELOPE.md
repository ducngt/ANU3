# Change Envelope — P3-02..P3-07 SBBS Capability Runtime

Baseline: `P2-T02 + P3-01 G3 ACCEPTED`.

Scope:
- P3-02 Compatibility Engine
- P3-03 Adapter/Transform Registry
- P3-04 Connection Planner
- P3-05 Smart Wire Runtime
- P3-06 Assembly Registry/Runtime
- P3-07 Write Box Studio MVP + Architecture Audit

Guardrails:
- CAPABILITY != AUTHORITY
- Contract Before Connection
- Wire contains no business discovery/planning logic
- Adapter owns technology-specific bridging
- Assembly owns composition
- no connection without compatibility evidence
- breaking contracts are versioned
- Write Box cannot alter Constitutional Core or create institutional authority

Human Gate: no new G2 required because the tranche preserves the previously approved synthetic ARU-01 scope and does not change authority/privacy semantics. G3 opens only after independent live PostgreSQL evidence.
