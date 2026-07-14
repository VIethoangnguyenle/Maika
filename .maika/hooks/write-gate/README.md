# Maika Write Gate Hook

Runtime hook for platforms that support pre-write/pre-edit tool interception.

The hook blocks application-code writes unless the vNext workspace gate passes:

- `profiles/execution-mode.yaml` has `workflow_engine: vnext`.
- Exactly one `changes/<id>/STATE.yaml` is `EXECUTING`.
- `generated/PLAN_VALIDATION.json` is approved.
- `generated/TASK_QUEUE.json` matches `generated/PLAN_MANIFEST.json`.
- Exactly one task is `in_progress`.
- The target path is declared in that task's `files` contract.

Framework artifacts and Maika planning/spec docs are allowed so the agent can
create the workspace, spec, queue, briefs, results, and reviews before
implementation writes.

Documentation/understanding artifacts (`.md`, `.markdown`, `.txt`, `.rst`) are
also exempt anywhere in the tree — they are not application code, so the agent
can hand over a codebase-understanding doc without a checkpoint. Code writes
(`.py`, `.ts`, …) remain gated.

The runner is runtime-aware:
- `--runtime claude` blocks with exit code 2 and stderr.
- `--runtime codex` blocks with Codex `PreToolUse` JSON.
- `--runtime antigravity` blocks with Antigravity decision JSON.
