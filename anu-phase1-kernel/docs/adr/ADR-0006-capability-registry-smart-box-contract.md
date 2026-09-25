# ADR-0006 — Capability Registry and Smart Box Manifest foundation

## Context
Phase 3 needs reusable, discoverable capabilities without coupling capability identity to a provider implementation or granting authority to code merely because it can perform an operation.

## Decision
Create versioned Capability Contracts and Smart Box Manifests. Capability identity/semantics/owner/version/lifecycle are stable; provider-specific runtime bindings live in Smart Box manifests behind adapter boundaries. Discovery matches operations and semantic input/output contracts.

## Constitutional constraint
`CAPABILITY != AUTHORITY`. Capability and Smart Box contracts contain policy references and data scope but do not confer institutional Authority. Consequential runtime execution remains gated by the Phase 1 Authority/Delegation/Policy system when P3 execution is opened later.

## Consequences
Multiple providers may implement one Capability Contract. Replacing a provider is non-breaking when the contract/quality/security obligations are preserved.
