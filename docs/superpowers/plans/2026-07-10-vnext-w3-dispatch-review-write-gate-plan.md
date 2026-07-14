# Maika vNext W3 Dispatch, Review, and Write Gate Plan

## Objective
Replace the vNext execution stub with a mechanical dispatcher that requires
fresh prompts, file handoff, structured task results, task review, fix dispatch,
final review, retry limits, and write-gate-enforced declared scope.

## Scope
- Add task-review and final-review gate contracts.
- Extend result-contract file scope to `create`, `modify`, `delete`, and `test`.
- Replace `vnext_dispatch.run_queue()` stub with implementation, fix,
  task-review, and final-review dispatches.
- Preserve plan-review dispatch as the planning dispatch type.
- Keep vNext writes constrained by `TASK_QUEUE.json` while a task is
  `in_progress`.
- Update workflow/tool docs and the executing-task skill to match the enforced
  result schema.

## Non-goals
- Public `/task ...` command cutover remains W5.
- Capability adapter runtime remains W4.
- Verification/archive/knowledge cutover remains W6.

## Acceptance Criteria
- Exit code `0` without `results/TASK-NNN.yaml` blocks the task.
- A valid result cannot complete a task without `reviews/TASK-NNN.md`.
- `CHANGES_REQUIRED` dispatches `fix` and re-runs task review until retry budget
  is exhausted.
- Successful queue execution writes and validates `reviews/FINAL_REVIEW.md`.
- The write gate allows declared deletes and still blocks undeclared app-code
  writes.
- Focused dispatcher, gate, and write-gate tests pass.

## Review Notes
- The W3 runner intentionally keeps generated queue state as the source of truth.
- App-code writes are only permitted while exactly one vNext task is
  `in_progress`; review/final-review prompts may write workspace artifacts but
  not application files.
