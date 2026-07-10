---
name: architecture-reconciler
version: '1.0'
description: >
  Reconcile current behavior, desired behavior, evidence conflicts, and viable
  extension seams before Maika vNext brainstorming or specification begins.
---

# Architecture Reconciler

## Purpose
Convert grounding into `RECONCILIATION.md`: current behavior, desired behavior,
extension seam, alternatives, contradictions, user decisions, and readiness.

## Triggers
Use after `grounding-explorer` passes, when evidence conflicts, or when planning
discovers an ungrounded architecture assumption.

## Inputs
- `CHANGE.yaml`
- `INTENT.md`
- `exploration/GROUNDING.yaml`
- `exploration/EVIDENCE_MANIFEST.yaml`
- Capability IDs: `architecture_discovery`, `dependency_analysis`,
  `convention_retrieval`.

## Required outcomes
- Current and desired behavior are separated.
- Alternatives and tradeoffs are grounded in evidence IDs.
- Contradictions and user-only decisions are explicit.
- Readiness for brainstorming or spec is recorded.

## Invariants
- Do not choose an architecture without evidence.
- Do not implement or edit application code.
- Do not hide unresolved conflicts.

## Evidence requirements
Every significant recommendation cites claim IDs from
`EVIDENCE_MANIFEST.yaml`. Inferences are labeled as such.

## Process
1. Read all grounding claims.
2. Summarize current behavior.
3. Summarize desired behavior from `INTENT.md`.
4. Identify extension seams and alternatives.
5. Record contradictions, risks, and required user decisions.
6. Write readiness verdict.

## Stop conditions
- Evidence conflicts block design.
- A required public-contract, security, persistence, or destructive decision is
  uncovered.
- The desired behavior cannot be separated from implementation strategy.

## Output contract
Write `RECONCILIATION.md` with a readiness verdict: `READY`, `NEEDS_CONTEXT`, or
`BLOCKED`.

## Next handoff
`grounded-brainstorming` for standard and architectural changes, or
`writing-spec` when the change is already sufficiently constrained.
