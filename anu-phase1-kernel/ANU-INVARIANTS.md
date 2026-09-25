# ANU Phase-1 Invariants

The implementation MUST preserve these invariants:

- CAPABILITY != AUTHORITY
- AUTHORITY != COMPETENCE
- AUTHENTICATION != AUTHORIZATION
- AUTHENTICATION != SIGNATURE
- SIGNATURE != AUTHORITY
- AGENT IDENTITY != PERMANENT AUTHORITY
- MODEL IS REPLACEABLE
- ORGANIZATION IS CONFIGURABLE
- UNIVERSITY MEMORY MUST PERSIST
- POLICY IS VERSIONED
- LAYER != HOP
- TRUST != SURVEILLANCE

Additional implementation guards:

- Global identity is shared across Human, Agent, Organization, Capability, Work,
  Evidence, Policy, Decision and Artifact references.
- No consequential grant, delegation, policy activation, lifecycle transition or
  decision may be represented only by mutable current state.
- Revocation, supersession, deprecation and retirement append history and never
  erase institutional provenance.
- Policy/authority evaluation is effective-time aware.
- Agent identity alone never yields institutional authority.
- Delegation is non-redelegable by default and may never exceed the delegator's
  active authority scope.
- Missing/ambiguous authority on consequential actions fails closed.
