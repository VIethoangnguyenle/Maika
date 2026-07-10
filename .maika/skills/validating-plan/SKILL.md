---
name: validating-plan
version: '1.0'
description: >
  Independently validate Maika vNext IMPLEMENTATION_PLAN.md against SPEC.md,
  grounding evidence, source anchors, acceptance criteria, and deterministic
  compilation requirements before execution can begin.
---

# Validating Plan

## Purpose
Decide whether a plan is executable without giving implementers strategic room
to reinterpret vague work.

## Triggers
Use after `writing-plan` produces `IMPLEMENTATION_PLAN.md` and before plan
compilation or dispatch.

## Inputs
- `SPEC.md`
- `IMPLEMENTATION_PLAN.md`
- `exploration/EVIDENCE_MANIFEST.yaml`
- Current source.
- Capability IDs: `exact_source_inspection`, `dependency_analysis`,
  `runtime_verification`.

## Required outcomes
- `generated/PLAN_VALIDATION.json` has verdict and check records.
- Plan metadata hashes match current artifacts.
- Acceptance criteria are covered by tasks.
- Dependencies are acyclic.

## Invariants
- Only `APPROVED` plans execute.
- No placeholders.
- No undeclared write scope.
- No uncited contract or architecture change.

## Evidence requirements
Validate source anchors, symbols, delete targets, expected failing and passing
tests, and evidence IDs.

## Process
1. Parse plan frontmatter and task sections.
2. Verify hashes and base commit.
3. Check file and symbol anchors.
4. Check acceptance-criteria coverage.
5. Run `vnext-plan`.
6. Return verdict.

## Stop conditions
- Plan is stale.
- Plan omits required AC or migration/rollback/security sections.
- Required source anchors are missing.

## Output contract
Write `generated/PLAN_VALIDATION.json` and return `APPROVED`, `REVISE`,
`STALE`, or `BLOCKED`.

## Next handoff
Plan compiler, then `executing-task`.
