---
name: grounding-explorer
version: '1.0'
description: >
  Build the three-lens grounding package for Maika vNext by collecting verified
  codebase, business, and convention evidence before any final architecture or
  implementation plan is written.
---

# Grounding Explorer

## Purpose
Produce `exploration/GROUNDING.yaml` and `exploration/EVIDENCE_MANIFEST.yaml`
from the current repository, business knowledge, and project conventions.

## Triggers
Use after `intent-analysis` for standard or architectural changes, or when a
planner reports missing evidence.

## Inputs
- `CHANGE.yaml`
- `INTENT.md`
- Current repository source.
- Knowledge stores under `knowledge/long-term/`.
- Capability IDs: `architecture_discovery`, `exact_source_inspection`,
  `dependency_analysis`, `business_knowledge_retrieval`,
  `convention_retrieval`, `runtime_verification`.

## Required outcomes
- `GROUNDING.yaml` has non-empty `codebase`, `business`, and `conventions`
  lenses.
- `EVIDENCE_MANIFEST.yaml` lists claim IDs, statuses, categories, and sources.
- Conflicting or missing mandatory evidence is explicit.

## Invariants
- Source files are authoritative for exact code facts.
- Graph or memory evidence supports source, never replaces it.
- Every inference is labeled.
- Do not design the final solution.

## Evidence requirements
Verified code claims need file paths, symbols where applicable, and file hashes.
Business claims need a source or an `inferred` status. Convention claims cite
rule IDs, examples, or approved knowledge entries.

## Process
1. Inspect source entry points and related tests.
2. Trace dependencies and blast radius.
3. Collect business terms, actors, rules, states, and unresolved questions.
4. Collect applicable conventions and conflicts.
5. Emit claim IDs and source records.
6. Run the `exploration-evidence` gate.

## Stop conditions
- A mandatory lens is empty.
- Evidence conflicts materially.
- Tool health prevents exact source inspection.
- A user-only business or contract decision is discovered.

## Output contract
Write `exploration/GROUNDING.yaml`, `exploration/EVIDENCE_MANIFEST.yaml`, and
tool-health notes if needed. Return a readiness verdict.

## Next handoff
`architecture-reconciler`.
