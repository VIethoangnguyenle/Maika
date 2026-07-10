---
name: intent-analysis
version: '1.0'
description: >
  Classify an incoming request into a Maika vNext change class, create or update
  CHANGE.yaml and INTENT.md, and decide which reasoning phases are required
  before specification or implementation may proceed.
---

# Intent Analysis

## Purpose
Turn a raw request into a concrete change record. Capture the user's intent,
classification, title, known constraints, and stop conditions without designing
the solution.

## Triggers
Use when a new `/task` request starts, when a resumed workspace lacks
`INTENT.md`, or when implementation discovers scope that may reclassify a
change.

## Inputs
- User request or ticket text.
- Existing `CHANGE.yaml`, if resuming.
- Existing `INTENT.md`, if present.
- Capability IDs: `business_knowledge_retrieval`, `convention_retrieval`.

## Required outcomes
- `CHANGE.yaml` records `change_id`, `class`, `title`, and timestamp.
- `INTENT.md` contains the request summary, class rationale, non-goals, and
  known blockers.
- Standard and architectural changes are routed to grounding before design.

## Invariants
- Do not propose architecture.
- Do not write application code.
- Do not downgrade public contract, persistence, security, or migration risk.

## Evidence requirements
Classification must cite exact request text or an explicit inference. Ambiguous
class, security, persistence, public contract, or destructive behavior stops for
user decision.

## Process
1. Read the request and any existing workspace files.
2. Assign `trivial`, `small`, `standard`, or `architectural`.
3. Record the reason in `INTENT.md`.
4. List unresolved public-contract or safety decisions.
5. Hand off to `grounding-explorer` unless the class explicitly skips grounding.

## Stop conditions
- The request lacks enough detail to classify.
- A public contract, database, security, or destructive decision is uncovered.
- The requested class conflicts with observed scope.

## Output contract
Write or update `CHANGE.yaml` and `INTENT.md`. Return `DONE`,
`NEEDS_CONTEXT`, or `BLOCKED` with the workspace path.

## Next handoff
`grounding-explorer` for standard and architectural changes; `writing-spec` for
small changes; mini-plan execution for trivial changes.
