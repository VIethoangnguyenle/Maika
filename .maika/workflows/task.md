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

## Current W3 Commands

The W3 runtime is exposed through the vNext CLI slice:

- `vnext-init` creates `CHANGE.yaml`, `INTENT.md`, and `STATE.yaml`.
- `vnext-validate-reasoning` validates `INTENT.md`, `GROUNDING.yaml`, and
  `EVIDENCE_MANIFEST.yaml`.
- `vnext-validate-spec` validates `SPEC.md`.
- `vnext-compile` validates and compiles `IMPLEMENTATION_PLAN.md`.
- `vnext-review-plan` records independent plan review.
- `vnext-run` dispatches implementation, fix, task-review, and final-review
  workers through fresh prompts and validates their written artifacts.
- `vnext-status` reads canonical workspace state.

The public `/task start|explore|reconcile|brainstorm|spec|plan|validate-plan|apply|review|verify|archive|status|resume|cancel`
surface is the W5 cutover target, not a completed W3 command registry.

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
```

## Rules

- Standard and architectural changes require three-lens grounding before final
  design.
- Implementers receive immutable briefs, not parent-session history.
- Reviewers do not modify application code.
- Undeclared application-code writes are blocked by the vNext write gate.
- Completion requires structured results, review, and fresh verification.
