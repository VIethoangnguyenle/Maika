---
name: knowledge-curator
version: '1.0'
description: >
  Curate Maika vNext knowledge after verified completion by extracting reusable
  lessons, updating durable knowledge stores, regenerating indexes, and archiving
  the change workspace.
---

# Knowledge Curator

## Purpose
Move verified work into durable knowledge and archive artifacts.

## Triggers
Use after `verification-before-completion` returns `VERIFIED`.

## Inputs
- `verification/VERIFICATION_REPORT.md`
- `reviews/FINAL_REVIEW.md`
- `SPEC.md`
- Task results.
- Capability IDs: `business_knowledge_retrieval`, `convention_retrieval`.

## Required outcomes
- Reusable lessons extracted.
- Author DNA updated only for recurring intent or philosophy.
- Conventions updated only for recurring concrete patterns.
- Knowledge index regenerated.
- Workspace archived.

## Invariants
- Do not add one-off observations to durable knowledge.
- Do not overwrite user-owned knowledge without evidence.
- Do not archive failed verification.

## Evidence requirements
Each knowledge update cites source files, reviews, or verification artifacts.

## Process
1. Read verification and review artifacts.
2. Extract reusable lessons.
3. Update knowledge stores only when criteria are met.
4. Regenerate indexes.
5. Archive the workspace.

## Stop conditions
- Verification failed.
- A knowledge update lacks evidence.
- Archive readiness gate fails.

## Output contract
Write updated knowledge files, regenerated index, archive path, and archive
report.

## Next handoff
Completed change state.
