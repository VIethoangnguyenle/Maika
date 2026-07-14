# Maika vNext W4 Capability Runtime Plan

## Objective
Introduce one canonical capability runtime across platform adapters, with
health/freshness-aware routing and explicit degradation for unsupported
capabilities.

## Scope
- Add `profiles/capability-registry.yaml` as the canonical capability registry.
- Update `profiles/capabilities.md` to include dispatch and version-control IDs
  used by W2/W3 skills.
- Add `cli/capability_runtime.py` to route capabilities as `ready`, `degraded`,
  or `unsupported`.
- Expose `capability_registry` and `capability_routes` in every platform render
  context.
- Add dispatch capability flags for Claude Code, Codex, Antigravity, and
  generic adapters.
- Ship capability profiles through the plugin manifest.
- Extend skill-lint to reject provider names and unknown capability IDs in
  canonical skills.

## Non-goals
- No cost/risk/data-sensitivity routing.
- No model-tier selection logic.
- No skill-contract rewrite beyond vocabulary alignment.
- No physical deletion of legacy runtime paths before W7.

## Acceptance Criteria
- Every canonical skill capability ID exists in the registry.
- Every platform exposes a route for every capability.
- Stale code-index freshness degrades code capabilities.
- Failed dynamic-memory health degrades business-knowledge retrieval.
- Generic dispatch routes are explicitly unsupported.
- Provider names are absent from canonical skills and rejected by skill-lint.
- CLI/scaffold and skill-lint tests pass.
