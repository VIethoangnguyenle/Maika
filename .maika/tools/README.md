# Maika Tools

- `gate-check/`: mechanical gates for workspace, intent, grounding, spec, plan,
  brief integrity, result contract, task review, final review, and archive
  readiness.
- `microloop-orchestrator/`: W1-W3 vNext workspace, compiler, dispatcher,
  result collection, retry loop, task review loop, and final review dispatch.
- `knowledge-index/`: durable knowledge index generation.
- `rule-projector/`: generated rule projections.
- `mcp-bridge/`: platform MCP setup support.

Capability routing lives in the scaffolded profiles (`profiles/capabilities.md`
and `profiles/capability-registry.yaml`) plus the CLI adapter runtime.

Framework-development-only tools are not scaffolded unless a manifest consumer
declares them.
