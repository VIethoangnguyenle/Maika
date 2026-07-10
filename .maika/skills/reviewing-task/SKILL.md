---
name: reviewing-task
version: '1.0'
description: >
  Review one Maika vNext task result against its immutable brief, changed diff,
  tests, declared write scope, and structured evidence without modifying
  application code.
---

# Reviewing Task

## Purpose
Accept or reject one implemented task.

## Triggers
Use after a task result passes the result-contract gate.

## Inputs
- `briefs/TASK-NNN.md`
- `results/TASK-NNN.yaml`
- Diff package for the task.
- Capability IDs: `exact_source_inspection`, `runtime_verification`,
  `review_dispatch`.

## Required outcomes
- `reviews/TASK-NNN.md` records spec compliance and quality verdicts.
- Critical and Important findings are actionable.
- Minor findings are recorded for final review.

## Invariants
- Reviewers do not modify application code.
- Do not re-plan silently.
- Do not approve missing verification evidence.

## Evidence requirements
Check changed files, deleted files, changed symbols, commands, observed output,
brief hash, allowed files, and acceptance criteria.

## Process
1. Read the brief and result.
2. Inspect the diff package.
3. Compare implementation to the task requirements.
4. Classify findings as CRITICAL, IMPORTANT, MINOR, or NOTE.
5. Return verdict.

## Stop conditions
- Result schema is invalid.
- Diff exceeds allowed scope.
- Missing evidence prevents review.

## Output contract
Write `reviews/TASK-NNN.md` with verdict `APPROVED` or `CHANGES_REQUIRED`.

## Next handoff
Fix dispatch for findings, or orchestrator queue completion.
