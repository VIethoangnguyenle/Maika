---
name: grounded-brainstorming
version: '1.0'
description: >
  Compare grounded solution approaches after reconciliation, using verified
  evidence and project conventions while avoiding ungrounded implementation
  detail or provider-specific tool instructions.
---

# Grounded Brainstorming

## Purpose
Explore solution approaches using `RECONCILIATION.md` and evidence before the
behavioral spec is written.

## Triggers
Use when reconciliation is `READY` and the change has multiple viable designs,
or when user approval is required for standard or architectural scope.

## Inputs
- `CHANGE.yaml`
- `INTENT.md`
- `RECONCILIATION.md`
- `exploration/GROUNDING.yaml`
- `exploration/EVIDENCE_MANIFEST.yaml`
- Capability IDs: `business_knowledge_retrieval`, `convention_retrieval`.

## Required outcomes
- Two or three approaches with tradeoffs.
- Recommended approach with evidence references.
- Explicit rejected alternatives.
- User decisions recorded when required.

## Invariants
- Brainstorming là stance, không phải workflow cứng.
- Visualize tự do when a diagram clarifies flow, state, integration, callback,
  job, or data path.
- Do visualize complex sequences; ASCII diagram bắt buộc khi có flow/state/data path.
- capture insight đó vào `RECONCILIATION.md`.
- Keep focus on vấn đề user nêu.

## Evidence requirements
Every approach cites evidence IDs or is labeled as an inference. Architecture,
security, persistence, and contract choices require explicit approval.

## Process
1. Read the reconciliation verdict.
2. Compare approaches and tradeoffs.
3. Draw an ASCII flow or state diagram when it clarifies the decision.
4. Record the selected approach and rejected alternatives.
5. Update `RECONCILIATION.md` with decisions.

## Stop conditions
- A required decision is uncovered.
- Evidence is stale or conflicting.
- The user rejects all viable approaches.

## Output contract
Update `RECONCILIATION.md` with chosen approach, decision evidence, and open
questions.

## Next handoff
`writing-spec`.
