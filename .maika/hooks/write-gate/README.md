# Maika Write Gate Hook

Runtime hook for platforms that support pre-write/pre-edit tool interception.

The hook blocks application-code writes unless all implementation preflight
artifacts exist and pass:

- `knowledge/active/KNOWLEDGE_CHECKPOINT.md` passes
  `tools/gate-check/gates.py::validate_knowledge_checkpoint`.
- `knowledge/active/AGENT_TRANSPARENCY.md` passes the apply gate (`Pha 2 DONE`
  and no unresolved `[BLOCKER-ARCH]`).
- A valid `knowledge/active/TASK_HANDOFF.<node>.md` or
  `knowledge/active/IMPLEMENTATION_CONTEXT.md` passes
  `validate_implementation_context` and its `## Allowed Files` section matches
  the code file being written.

Framework artifacts and Maika planning/spec docs are allowed so the agent can
create the workspace, checkpoint, spec, queue, results, and reviews before
implementation writes.

Documentation/understanding artifacts (`.md`, `.markdown`, `.txt`, `.rst`) are
also exempt anywhere in the tree — they are not application code, so the agent
can hand over a codebase-understanding doc without a checkpoint. Code writes
(`.py`, `.ts`, …) remain gated.

The runner is runtime-aware:
- `--runtime claude` blocks with exit code 2 and stderr.
- `--runtime codex` blocks with Codex `PreToolUse` JSON.
- `--runtime antigravity` blocks with Antigravity decision JSON.
