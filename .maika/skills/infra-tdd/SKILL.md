---
name: infra-tdd
version: '1.0'
description: >
  Produce infrastructure technical design documents for Maika vNext when a
  change requires explicit operational architecture, decision records,
  verification strategy, and rollback planning.
---

# Infra TDD

## Purpose
Create infrastructure design evidence for architectural changes.

## Triggers
Use when `CHANGE.yaml` class is `architectural` and the spec needs operational
architecture, migration, rollback, or infrastructure tradeoffs.

## Inputs
- `INTENT.md`
- `GROUNDING.yaml`
- `RECONCILIATION.md`
- Capability IDs: `architecture_discovery`, `dependency_analysis`,
  `runtime_verification`.

## Required outcomes
- Technical design document with context, strategy, architecture, decisions,
  verification, migration, and rollback.
- Any ADRs required by the change.

## Invariants
- Do not replace `SPEC.md`.
- Do not skip security, migration, rollback, or operations for architectural
  changes.
- Do not implement from the design directly.

## Evidence requirements
Architectural decisions cite grounding claims, source anchors, and operational
constraints.

## Process
1. Read grounded artifacts.
2. Identify architecture decisions.
3. Write the design.
4. Record ADRs when needed.
5. Feed decisions back to `writing-spec`.

## Stop conditions
- Required operational evidence is missing.
- A migration or rollback decision needs user approval.
- Security impact is unresolved.

## Output contract
Write the TDD under project docs and list evidence references.

## Next handoff
`writing-spec`.
