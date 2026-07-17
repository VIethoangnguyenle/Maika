# Codebase Memory MCP Removal Design

**Date:** 2026-07-17
**Status:** Approved
**Scope:** Remove the `codebase-memory-mcp` provider from Maika; reroute its capability to UA-MCP and Serena; add doctor detection for CBM global-config contamination.
**Sequencing:** Implemented only after the `serena-semantic-phase1` branch merges. This change is a separate branch on top of that merge, never folded into the in-flight Serena work.

## 1. Decision summary

Maika removes Codebase Memory MCP (CBM) from its provider ecosystem entirely: registry, manifest, integration adapter, platform adapters, rules, procedures, skills, gates, tests, and documentation. The `semantic_code_search` capability it held is rerouted to UA-MCP `query_nodes` as primary with host search tools as corroboration. `maika doctor mcp` gains a contamination check that detects CBM-written hooks/skills/config in global and project agent configuration and reports structured degradation with remediation steps.

No replacement fuzzy-semantic-search engine is built. This is a net-negative-complexity change consistent with `.maika/DEVELOPMENT_RULES.md`.

## 2. Problem

The `codebase-memory-mcp` binary ships an `install` command that writes directly into **global** agent configuration:

- a `PreToolUse` hook matching `Grep|Glob` that augments every host search with CBM `search_graph`;
- a `SessionStart` hook injecting a "use codebase-memory MCP" reminder on startup/resume/clear/compact;
- skills, `settings.json` entries, `.mcp.json` entries, plus editor MCP config for VS Code, Zed, Gemini/Antigravity, and Kilocode.

These facts were verified against the installed binary (`~/.local/bin/codebase-memory-mcp`, static ELF): its install plan (`agent.install.plan.v1`) includes `cbm_install_hook_gate_script`, `cbm_install_skills`, `cbm_install_agent_configs`, and hook payload markers (`# codebase-memory-mcp search augmenter (Claude Code PreToolUse)`, `# Installed by codebase-memory-mcp`).

Because the writes are global, **every project on the machine** is steered toward CBM-first exploration, overriding Maika's UA-first provider doctrine. Maika's manifest already defends with a `--skip-config` install hint (`cli/plugin-manifest.yaml`), but Maika cannot control users following upstream install docs or upstream upgrade paths re-running the installer.

Two facts make removal cheap and low-loss right now:

1. **Realized CBM value is ~zero.** The registry grants CBM one primary capability (`semantic_code_search`); no per-repo CBM index exists on active projects, while UA graphs are healthy (maika-cli 1799 nodes, ngac 2137 nodes).
2. **The Serena integration is in flight.** The 2026-07-16 Serena design keeps CBM only as a conditional provider; amending that doctrine before Phase 1 hardens it in code is the cheapest possible timing.

## 3. Considered approaches

### 3.1 Remove CBM entirely (selected)

Reroute fuzzy discovery to UA `query_nodes`; rely on Serena for exact symbol work; add doctor contamination detection. Permanently eliminates the global-override risk and one vendor binary. Loses true embedding-based fuzzy search — which is not currently indexed anywhere, so nothing in active use is lost.

### 3.2 Keep CBM but isolate it (rejected)

Mirror the agent-memory precedent (`integration_mode: mcp_proxy_only`, hooks off, never run `install`). Least doctrine churn, but upstream installers/upgrades can still stomp global config at any time, and the failure mode is silent. Does not meet the requirement to replace the provider.

### 3.3 Replace CBM with another fuzzy-search provider (rejected)

No mature MCP-only candidate exists; Serena is symbol-exact, not fuzzy; building an embedding index inside Maika violates the framework's net-negative-complexity rule.

## 4. Post-removal responsibility doctrine

The following rows replace all CBM rows in the Serena integration design's responsibility matrix (§5.2 of `2026-07-16-serena-semantic-provider-integration-design.md`):

| Concern | Primary provider | Supporting | Authority rule |
|---|---|---|---|
| Fuzzy semantic anchor discovery | UA-MCP `query_nodes` (name/summary/tags) | host Grep/Glob; Serena `find_symbol` once a name is known | UA graph must be identity-verified and fresh enough for the claim |
| UA graph gap or stale graph | current source via host search | Serena navigation | stale UA traversal remains navigation evidence only for affected files |
| Reviewer counter-evidence | current source | Serena `find_referencing_symbols` | current source and tests win conflicts |
| Hidden consumer risk | UA first, then current source | Serena references | unchanged: no provider may claim completeness for missing dynamic/config/reflection edges |

Registry-level changes:

- The `semantic_index_structure` authority lane is deleted; no provider claims it.
- `structured_graph_trace.corroborating` drops `codebase-memory-mcp` and keeps `current-source`.
- The `semantic_code_search` capability ID is retired; skills that consumed it are rewritten against UA `query_nodes` under existing UA capability IDs. No new capability ID is introduced without a consumer.

## 5. Technical scope

All references are on the live tree (excluding `build/`, worktrees, and archived docs). The full grep inventory is the implementation checklist source of truth; the categories are:

**Deleted files:**

- `cli/mcp/integration/codebase_memory.py`
- `cli/tests/fixtures/provider_contracts/codebase-memory/` (both provenance fixtures)

**Config and doctrine:**

- `.maika/config/provider-registry.yaml` — remove provider block and authority references (§4).
- `.maika/config/external-workflows.yaml`, `.maika/profiles/provider-capabilities.yaml`, `.maika/profiles/capability-registry.yaml` — remove CBM entries.
- `.maika/rules/core/evidence.md`, `.maika/rules/jit/providers.md`, `.maika/rules/jit/knowledge-lifecycle.md` — rewrite provider doctrine per §4.
- `.maika/procedures/context-loader.md`, `.maika/procedures/dispatch-kernel.md` — remove CBM routing.
- `.maika/skills/grounding-explorer/SKILL.md`, `.maika/skills/architecture-reconciler/SKILL.md`, `.maika/skills/skill-index.yaml` — reroute to UA `query_nodes` / host search.

**CLI:**

- `cli/plugin-manifest.yaml` — remove `mcp_capabilities.codebase-memory-mcp` (UA already provides `code_exploration`).
- `cli/provider_actions.py`, `cli/commands/provider.py`, `cli/mcp/pilot_readiness.py`, `cli/agent_content/provider_capabilities.py`, `cli/platforms/claude_code.py`, `cli/platforms/antigravity.py`, `cli/tools/templatize.py` — remove CBM branches and imports.

**Gates and tools:**

- `.maika/tools/gate-check/gates.py` and its tests, `.maika/tools/microloop-orchestrator/vnext_dispatch.py` and its tests — remove CBM-specific gate/dispatch handling.

**Tests:** update the ~20 CLI test modules that reference CBM (init, update, scaffold, snapshots, manifest setup, mcp config/doctor, platforms, provider adapters/capabilities/invocations, capability runtime, structured trace, trace evidence, system model, pilot readiness, external workflows, end-to-end learning loop, vnext W2, ua_setup).

**Documentation:**

- `README.md`, `docs/architecture/control-plane/product-design.md`, plan/inventory docs — remove CBM as a supported provider; add uninstall guidance (§7).
- Amend `docs/superpowers/specs/2026-07-16-serena-semantic-provider-integration-design.md` (§2, §3, §5, §6, §9, §15.3, §18, §19) and `docs/superpowers/plans/2026-07-16-serena-semantic-provider-phase1.md` doctrine lines: CBM rows replaced per §4 above. Amendments are dated edits noting this removal design; history stays in git.

## 6. Doctor contamination check

`maika doctor mcp` gains one detection step, `cbm_contamination`, covering both scopes:

- **Global:** `~/.claude/settings.json` hook entries whose command contains `codebase-memory`; files under `~/.claude/hooks/` and `~/.claude/skills/` containing the markers `codebase-memory-mcp` or `# Installed by codebase-memory-mcp`.
- **Project:** `.claude/settings.json` and `.mcp.json` entries referencing `codebase-memory`.

Findings produce a **degraded** doctor status with a structured remediation message: run `codebase-memory-mcp uninstall`, remove the binary, and re-run doctor. The check **never deletes or edits** user configuration — detection and guidance only. Absence of findings produces a healthy line so the check is visibly running.

## 7. Migration and lifecycle

- `maika update --reconfigure` on an existing project prunes the CBM section from generated `MCP_SETUP.md` and rendered MCP config for every enabled platform, preserving other providers (reuses the existing manifest-driven re-emit path; no second installer).
- Documentation gains an uninstall section: `codebase-memory-mcp uninstall`, delete `~/.local/bin/codebase-memory-mcp`, re-run `maika doctor mcp` to confirm a clean contamination check.
- Projects that previously selected CBM and run plain `maika update` without `--reconfigure` keep working: the provider is simply no longer offered, and doctor reports stale rendered config as remediation guidance.

## 8. Verification plan

- **Registry/manifest tests:** no `codebase-memory` reference remains in registry, manifest, profiles, or generated setup output; retired capability ID has no remaining consumer.
- **Routing tests:** grounding/discovery skills resolve fuzzy-anchor queries through UA `query_nodes`; degradation when the UA graph is stale routes to host search, not to a removed provider.
- **Doctor tests:** contamination fixtures for each scope (global hook entry, hook-script marker, skill marker, project settings, project `.mcp.json`) classify as degraded with remediation; clean fixture classifies healthy; doctor never mutates fixture files.
- **Lifecycle tests:** `maika init` no longer offers CBM; `maika update --reconfigure` on a fixture project with a rendered CBM section removes exactly that section on every platform.
- **Repo-wide guard:** a test asserts the live tree (excluding archived docs and git history) contains no `codebase-memory` references outside this design doc and the uninstall documentation.
- Full suite passes with `/usr/bin/python3 -m pytest`.

## 9. Non-goals

- Building or bundling a replacement embedding/fuzzy search engine.
- Modifying or auto-deleting anything in the user's global configuration (detection only).
- Changing the agent-memory provider or its isolation model.
- Amending the Serena Phase 1 implementation branch while it is in flight.
- Removing the user's installed CBM binary or its local indexes; that remains a documented manual step.
