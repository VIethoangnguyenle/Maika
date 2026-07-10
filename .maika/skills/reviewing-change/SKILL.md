---
name: reviewing-change
version: '1.0'
description: >
  Perform final whole-change review for Maika vNext after task reviews complete,
  checking integration, deleted references, verification evidence, and unresolved
  findings before completion.
---

# Reviewing Change

## Purpose
Review the complete change, not a single task.

## Triggers
Use after all required task reviews pass and before verification or completion.

## Inputs
- Full branch diff package.
- `SPEC.md`
- `IMPLEMENTATION_PLAN.md`
- Task results and reviews.
- Capability IDs: `exact_source_inspection`, `dependency_analysis`,
  `runtime_verification`.

## Required outcomes
- `reviews/FINAL_REVIEW.md`.
- `reviews/FINDINGS.yaml` for unresolved Minor or Note items.
- Critical and Important findings resolved before completion.

## Invariants
- Do not modify application code.
- Do not ignore cross-task integration.
- Do not approve stale generated artifacts.

## Evidence requirements
Use diff evidence, task results, final verification, deleted-reference scans, and
acceptance-criteria coverage.

## Process
1. Read the spec, plan, results, and reviews.
2. Inspect the complete diff.
3. Check integration and deletion discipline.
4. Classify findings.
5. Return final verdict.

## Stop conditions
- Any task lacks review.
- Critical or Important finding remains.
- Verification evidence is stale or missing.

## Output contract
Write `reviews/FINAL_REVIEW.md` with verdict and `reviews/FINDINGS.yaml` when
findings exist.

## Next handoff
`verification-before-completion`.
