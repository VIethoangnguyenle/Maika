---
name: convention-intelligence-builder
version: '1.0'
description: >
  Build and maintain Maika vNext convention intelligence by extracting recurring
  concrete naming, structure, testing, and boundary patterns from verified
  source evidence.
---

# Convention Intelligence Builder

## Purpose
Capture concrete project conventions that planners and reviewers can apply.

## Triggers
Use during onboarding, after a major refactor, or when repeated review findings
show a convention gap.

## Inputs
- Current source and tests.
- Existing `knowledge/long-term/conventions.yaml`.
- Capability IDs: `exact_source_inspection`, `architecture_discovery`,
  `dependency_analysis`.

## Required outcomes
- Convention entries are concrete and reusable.
- Each entry has scope, examples, and applies-to tags.
- Knowledge index can expose matching entries.

## Invariants
- Do not store philosophy here.
- Do not add a convention from a single accidental example.
- Do not hard-code provider behavior.

## Evidence requirements
Each convention cites verified source examples and counterexamples when useful.

## Process
1. Inspect source patterns.
2. Group repeated concrete conventions.
3. Separate convention from Author DNA.
4. Write convention entries.
5. Regenerate knowledge index.

## Stop conditions
- Evidence is too sparse.
- Pattern is philosophical rather than concrete.
- Existing convention already covers it.

## Output contract
Write `knowledge/long-term/conventions.yaml` updates and index changes.

## Next handoff
`grounding-explorer` and `validating-plan` consume the conventions.
