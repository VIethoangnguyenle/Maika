---
name: executing-task
version: '1.0'
description: >
  Execute exactly one immutable Maika vNext task brief in a fresh isolated
  context, producing structured YAML results with commands, changed files,
  changed symbols, deviations, concerns, and commit evidence.
---

# Executing Task

## Purpose
Implement one compiled task brief without deriving strategy from parent-session
history or a vague request.

## Triggers
Use for a `PENDING` task in `TASK_QUEUE.json` after the plan is approved and
brief integrity passes.

## Inputs
- One `briefs/TASK-NNN.md`.
- Allowed files from the brief header.
- Dependency outputs listed by the orchestrator.
- Capability IDs: `runtime_verification`, `version_control`.

## Required outcomes
- One task implemented or blocked.
- `results/TASK-NNN.yaml` follows the result contract.
- Focused tests are run and recorded.
- Commit SHA is recorded when code changes.

## Invariants
- Do not edit files outside allowed scope.
- Do not change the plan or queue.
- Do not complete from exit code alone.
- Escalate stale plan, missing context, or undeclared file needs.

## Evidence requirements
Record commands, expected output, observed output, exit code, changed files,
deleted files, changed symbols, deviations, concerns, and commit SHA.

## Process
1. Read the brief.
2. Verify scope and preconditions.
3. Follow test-first steps when the brief requires behavior changes.
4. Implement only declared work.
5. Run focused verification.
6. Write structured result.

## Stop conditions
- Brief hash mismatch.
- Required file is undeclared.
- Plan is stale.
- Verification repeatedly fails for the same reason.

## Output contract
Write `results/TASK-NNN.yaml` with:
- `task_id: TASK-NNN`
- `status: success` only when the task is complete
- `files.create`, `files.modify`, `files.delete`, and `files.test` matching the
  compiled task scope
- `verification.passed: true` plus observed output

Blocked or incomplete work must be reported through the orchestrator retry/block
path, not by pretending the task result succeeded.

## Next handoff
`reviewing-task`.
