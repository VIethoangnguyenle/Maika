---
name: writing-plan
version: '1.0'
description: >
  Write Maika vNext IMPLEMENTATION_PLAN.md from an approved SPEC.md and evidence
  manifest, producing deterministic task sections with exact files, anchors,
  tests, commands, expected results, and write scope.
---

# Writing Plan

## Purpose
Create the execution source of truth for a change.

## Triggers
Use when `SPEC.md` is approved and the change state is `PLANNING`.

## Inputs
- `SPEC.md`
- `exploration/EVIDENCE_MANIFEST.yaml`
- Current source.
- Capability IDs: `exact_source_inspection`, `dependency_analysis`,
  `runtime_verification`.

## Required outcomes
- `IMPLEMENTATION_PLAN.md` has metadata, global constraints, and `TASK-NNN`
  sections.
- Each task declares files, symbols, dependencies, acceptance criteria, test
  steps, commands, expected failures, expected passes, allowed adaptations, and
  re-plan triggers.

## Invariants
- No vague implementation tasks.
- No unanchored exact code instruction.
- No undeclared write scope.
- No placeholder text.

## Evidence requirements
Every task cites relevant evidence IDs and acceptance criteria. Existing files
and symbols must be verified against current source before the plan is written.

## Process
1. Read spec and evidence.
2. Map acceptance criteria to tasks.
3. Verify file and symbol anchors.
4. Write task sections.
5. Run plan validation.

## Stop conditions
- Spec hash or evidence is stale.
- Required source anchor is missing.
- A task needs a public-contract or security decision not in the spec.

## Output contract
Write `IMPLEMENTATION_PLAN.md` and return `READY_FOR_PLAN_REVIEW` or
`NEEDS_CONTEXT`.

## Next handoff
`validating-plan`.
