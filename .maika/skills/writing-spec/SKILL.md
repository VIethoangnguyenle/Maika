---
name: writing-spec
version: '1.0'
description: >
  Write class-aware Maika vNext SPEC.md from grounded evidence and reconciliation,
  including acceptance criteria, evidence references, and required ASCII diagrams
  for flow, state, integration, callback, job, or data-path changes.
---

# Writing Spec

## Purpose
Produce `SPEC.md` from grounded evidence, not from a vague request.

## Triggers
Use after reconciliation or grounded brainstorming, or for small changes after
light grounding.

## Inputs
- `CHANGE.yaml`
- `INTENT.md`
- `RECONCILIATION.md`
- `exploration/GROUNDING.yaml`
- `exploration/EVIDENCE_MANIFEST.yaml`
- Capability IDs: `business_knowledge_retrieval`, `convention_retrieval`.

## Required outcomes
- Small changes include Goal, Current Behavior, Desired Behavior, Acceptance
  Criteria, Relevant Evidence, and Evidence References.
- Standard and architectural changes include the full master-plan specification
  sections.
- Acceptance criteria are testable and cite evidence.

## Invariants
- No implementation task list in the spec.
- No uncited material behavior claim.
- Architecture, persistence, events, security, migration, and rollback sections
  are explicit for architectural changes.
- #### ASCII Flow / State Diagram is required when the task has flow, state,
  integration, callback, job, hoặc data path.
- Use the exact trigger phrase: flow, state, integration, callback, job, hoặc data path.

## Evidence requirements
Use claim IDs from `EVIDENCE_MANIFEST.yaml`. Diagram phải đánh dấu `unknown`, `assumption`, hoặc `needs BA/PO confirmation` when facts are uncertain.

## Process
1. Select the small or full spec contract based on `CHANGE.yaml`.
2. Write behavior and constraints.
3. Add acceptance criteria.
4. Include a diagram when required:

~~~md
#### ASCII Flow / State Diagram

```text
actor -> component -> state
```
~~~

5. Run the `spec` gate.

## Stop conditions
- Mandatory evidence is missing.
- Acceptance criteria cannot be tested.
- A user-only decision remains open.

## Output contract
Write `SPEC.md` and `generated/SPEC_VALIDATION.json` when the gate runs.

## Next handoff
`writing-plan`.
