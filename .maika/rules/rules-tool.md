# Tool Rules

- Canonical skills refer to capability IDs.
- Concrete provider calls live in platform adapters and setup docs.
- Source inspection must use current source as authority.
- Runtime verification records command, expected output, observed output, and
  exit code.
- Reviewers do not modify application code.
- `mcp-status` records provider health before relying on dynamic capabilities.
- `handoff-slice` and `node-checkpoint` remain gate evidence for task handoff.
- `mcp-bridge` is the fallback path when a platform needs explicit MCP wiring.
- Handoff slices include `Applicable DNA/Conventions`.
- Node progress may be recorded as `NODE_CHECKPOINT.<node-id>.md`.
- Missing context may be requested as `CONTEXT_REQUEST.<node-id>.md`.
- `code-facts` evidence records `node_id` and blast-radius when graph evidence
  is available.
- `architecture-facts` evidence records source anchors, relationships, and
  relevant convention IDs; a `UA identifier` is valid when graph node IDs are
  not the source of the architecture fact.
