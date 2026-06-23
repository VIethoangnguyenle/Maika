# Maika Write Gate Hook

Runtime hook for platforms that support pre-write/pre-edit tool interception.

The hook blocks application-code writes unless
`knowledge/active/KNOWLEDGE_CHECKPOINT.md` exists and passes
`tools/gate-check/gates.py::validate_knowledge_checkpoint`.

Framework artifacts, OpenSpec artifacts, and Maika planning/spec docs are allowed
so the agent can create the checkpoint/spec before implementation writes.

Documentation/understanding artifacts (`.md`, `.markdown`, `.txt`, `.rst`) are
also exempt anywhere in the tree — they are not application code, so the agent
can hand over a codebase-understanding doc without a checkpoint. Code writes
(`.py`, `.ts`, …) remain gated.

The runner is runtime-aware:
- `--runtime claude` blocks with exit code 2 and stderr.
- `--runtime codex` blocks with Codex `PreToolUse` JSON.
- `--runtime antigravity` blocks with Antigravity decision JSON.
