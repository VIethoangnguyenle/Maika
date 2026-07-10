---
description: Canonical Maika vNext task workflow.
---

# /task

Maika vNext runs one plan-first workflow:

```text
intent-analysis
→ grounding-explorer
→ architecture-reconciler
→ grounded-brainstorming
→ writing-spec
→ writing-plan
→ validating-plan
→ executing-task
→ reviewing-task
→ reviewing-change
→ verification-before-completion
→ knowledge-curator
```

## Public Commands

The target scaffold exposes the canonical workflow through `maika task`:

- `maika task start --id <change-id> --class <class> --title <title>`
- `maika task explore --id <change-id>`
- `maika task reconcile --id <change-id>`
- `maika task brainstorm --id <change-id>`
- `maika task spec --id <change-id>`
- `maika task plan --id <change-id>`
- `maika task validate-plan --id <change-id>`
- `maika task review --id <change-id>`
- `maika task apply --id <change-id>`
- `maika task verify --id <change-id>`
- `maika task archive --id <change-id>`
- `maika task status [--id <change-id>]`
- `maika task resume --id <change-id>`
- `maika task cancel --id <change-id>`

`maika task verify` writes `verification/COMMANDS.yaml` and
`verification/VERIFICATION_REPORT.md`, then marks the workspace `COMPLETED`.
`maika task archive` requires verified completion, regenerates
`knowledge/long-term/knowledge-index.yaml`, writes `ARCHIVE_MANIFEST.yaml`, and
moves the workspace to `<framework-root>/archive/<change-id>`.

## Artifact Order

```text
CHANGE.yaml
INTENT.md
exploration/GROUNDING.yaml
exploration/EVIDENCE_MANIFEST.yaml
RECONCILIATION.md
SPEC.md
IMPLEMENTATION_PLAN.md
generated/PLAN_VALIDATION.json
generated/PLAN_MANIFEST.json
generated/TASK_QUEUE.json
briefs/TASK-001.md
results/TASK-001.yaml
reviews/TASK-001.md
reviews/FINAL_REVIEW.md
verification/COMMANDS.yaml
verification/VERIFICATION_REPORT.md
ARCHIVE_MANIFEST.yaml
```

## Rules

- Standard and architectural changes require three-lens grounding before final
  design.
- Implementers receive immutable briefs, not parent-session history.
- Reviewers do not modify application code.
- Undeclared application-code writes are blocked by the vNext write gate.
- Completion requires structured results, review, and fresh verification.
