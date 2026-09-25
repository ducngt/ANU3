# ADR-0003 — Separate Authentication, Authority, Signature and Agent Attestation

## Status
Accepted for Phase-1 Tranche 03 implementation.

## Decision

ANU Kernel treats authentication, authorization, institutional authority, Human signature and Agent attestation as distinct contracts and evaluation steps.

External authentication evidence is mapped to an existing ANU Identity. It does not grant Authority. Consequential access passes through a PEP that separately evaluates Authority/Delegation and Policy. Trust Registry stores public verification material and lifecycle metadata, never private signing keys.

Human Signature verification must not infer institutional validity from cryptographic validity alone. Agent Attestation is a technical responsibility-chain record and cannot substitute for Human approval/signature.

## Consequences

- More explicit evidence and failure reasons.
- Provider/IdP/signature technology remains replaceable behind contracts.
- Institutional policy retains control of authority and required signature semantics.
- Additional migration and Trust Registry lifecycle responsibilities are introduced.
