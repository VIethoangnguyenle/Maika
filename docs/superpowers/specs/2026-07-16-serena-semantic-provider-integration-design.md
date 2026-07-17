# Serena Semantic Provider Integration Design

**Date:** 2026-07-16
**Status:** Approved
**Scope:** Maika framework integration for Codex, Claude Code, and Antigravity

## 1. Decision summary

Maika will integrate Serena as an optional semantic code-intelligence provider. Serena will supply symbol-aware navigation, diagnostics, and, in a later gated phase, semantic editing and refactoring. Maika remains the control plane for capability routing, workflow state, write authorization, evidence, verification, review, and durable knowledge governance.

The integration will not adopt Serena's memory, onboarding, general file/search/shell tools, workflow prompts, or dashboard as Maika runtime authorities. Those surfaces overlap with Maika or the host and would create a second control plane.

The rollout has two phases:

1. **Phase 1 — semantic read:** symbol overview, symbol lookup, references, declarations, implementations, and diagnostics.
2. **Phase 2 — gated semantic write:** rename, safe delete, symbol body replacement, and insertion around symbols. Phase 2 is disabled until Maika proves that its existing write gate intercepts Serena MCP write calls on every supported platform.

All user-facing installation and operational documentation is part of the feature, not follow-up polish.

## 2. Problem

Maika already has a mature provider control plane:

- Understand-Anything MCP (UA-MCP) is the primary source for structured architecture, domain, relationship, call-chain, impact, graph-path, and inheritance traversal.
- Codebase Memory MCP (CBM) is the primary source for fuzzy semantic code discovery and a conditional source of graph-gap or reviewer counter-evidence.
- current source is authoritative for exact code facts and application behavior.
- AgentMemory supplies historical/session recall as candidate-only evidence.
- Maika supplies freshness rules, evidence envelopes, phase gates, task contracts, review, verification, audit, and knowledge promotion.

The missing layer is an IDE-like semantic execution engine over the current source tree. Maika's `current-source` provider is synthetic, and `exact_source_inspection` names abstract read operations but does not provide LSP-backed symbol identity, references, implementations, diagnostics, rename, safe delete, or symbol-aware editing. Host text tools can modify files, but they do not close this semantic gap consistently across platforms.

Serena fills that gap through LSP or its JetBrains backend. It does not replace Maika's orchestration or governance.

## 3. Verified upstream facts

This design was checked against these sources:

- Serena stable release `1.5.3`, Git tag `v1.5.3` at `2449313c0d7427275c4c66aedff7d4881782f713`.
- Serena main revision `8e90d923fbf4bcb162e2255ba5ec06357cd58fef` for the design-time capability survey.
- Understand-Anything producer revision `092feec79f6f7c78d95c9c55087fb48fa1178c99`.
- Understand-Anything MCP revision `0b4f3e2b18dc038bf28856821f568f05358fab2d`.
- Codebase Memory MCP revision `2469ecc3a7a2f80debe296e1f17a1efcfdb9450c`.

The resulting facts are:

1. Understand-Anything graph artifacts do not embed source bodies. A graph node carries identity and navigation metadata such as name, type, file path, line range, summary, tags, and complexity.
2. UA-MCP is a broad 18-tool structured graph interface; `get_node_source` is only its source-resolution tool. It also owns project/freshness inspection, node discovery, relationships, call trace, architecture layers, entry points, impact, paths, inheritance, tours, and domain flows. `get_node_source` resolves a graph node's file path against the live project, reads the current file, and extracts a function/class block or a truncated file. CBM is not a required dependency for reading the source of a UA node.
3. UA-MCP structured impact is reverse traversal over graph edges. At the audited revision, `find_impact` follows incoming `imports`, `calls`, `extends`, and `implements` relationships. It cannot prove the absence of a consumer that the producer did not encode as an edge.
4. CBM is technically capable of more than semantic search: it owns an independent index and exposes structural search, path tracing, change impact, graph queries, architecture, and source snippets. Maika deliberately narrows CBM's normal role to avoid competing structural authorities.
5. Serena provides semantic retrieval, diagnostics, reference-aware refactoring, and symbolic editing, but assumes the client, repository, configuration, and local machine are trusted. Maika must retain its own safety and verification boundaries.

## 4. Considered approaches

### 4.1 Full Serena adoption

Enable Serena's semantic tools, memory, onboarding, file/search/shell tools, prompts, and dashboard.

**Rejected.** This duplicates Maika's memory and workflow layers, enlarges the tool surface, and introduces conflicting instructions and authorities.

### 4.2 Read-only Serena integration

Expose only semantic navigation and diagnostics.

**Safe but incomplete.** This provides immediate value and is the correct first rollout phase, but it does not close the semantic refactoring gap.

### 4.3 Selective semantic provider with gated write

Expose a minimal read surface first, then add write tools only after mechanical gate interception is proven.

**Selected.** This preserves Maika's control plane while eventually adding the full useful portion of Serena's semantic execution layer.

## 5. Provider responsibility doctrine

### 5.1 UA-MCP full tool surface

Maika treats UA-MCP as its primary structured graph provider, not as a single source-reading tool. At the audited revision, its 18 tools form five coherent groups:

| Group | UA-MCP tools | Role in Maika |
|---|---|---|
| Project identity and freshness | `list_projects`, `get_graph_stats`, `get_graph_metadata` | Select the graph, verify its identity, and scope freshness before material use |
| Node and architecture discovery | `get_tour`, `query_nodes`, `get_node_detail`, `get_layer_info`, `find_entry_points`, `search_by_file_path` | Locate architectural/domain anchors and understand graph structure |
| Structured relationships and traversal | `get_relationships`, `trace_call_chain`, `find_impact`, `find_path`, `get_class_hierarchy` | Trace graph-backed consumers, calls, blast radius, paths, and inheritance |
| Domain graph | `get_domain_overview`, `get_domain_detail`, `get_domain_flow_detail` | Retrieve domain boundaries, details, and structured business flows |
| Source resolution | `get_node_source` | Read current source for an already identified graph node |

Serena does not replace any of these graph/domain responsibilities. It adds precise LSP-backed symbol identity, references, implementations, diagnostics, and gated refactoring over current source. CBM does not replace these responsibilities either; its normal role remains fuzzy semantic anchor discovery plus explicitly triggered graph-gap or counter-evidence work.

### 5.2 Responsibility matrix

| Concern | Primary provider | Conditional/supporting provider | Authority rule |
|---|---|---|---|
| Architecture and domain discovery | UA-MCP | current source | UA graph must be healthy and fresh enough for the claim |
| Structured relationships, call trace, impact, path, inheritance | UA-MCP | current source | UA owns consumers represented in its graph |
| Source for a known UA node | UA-MCP `get_node_source` | Serena or current-source tools | The live file remains authoritative |
| Exact symbol identity and body | Serena | current-source host tools | Verify against the current file |
| References, declarations, implementations | Serena | UA structured edges | Serena is preferred when the language backend supports the operation |
| Diagnostics | Serena | runtime build/lint/test | Serena diagnostics do not replace verification commands |
| Fuzzy semantic anchor discovery | CBM | UA node query | CBM is primary for vocabulary-mismatch discovery |
| UA graph gap, stale graph, reviewer counter-evidence | CBM | current source | Conditional use only; record the activation reason |
| Hidden consumer risk | UA first, then conditional counter-evidence | CBM semantic search and current source | No provider may claim completeness for missing dynamic/config/reflection edges |
| Historical/session recall | AgentMemory | durable Maika knowledge | Candidate-only; never current-code authority |
| Canonical project knowledge | Maika knowledge kernel | verified memories/evidence | Promotion requires verification |
| Exact current behavior | current source plus tests | all providers for navigation | Current source and observed runtime evidence win conflicts |

The term “hidden consumer” must not be used as if one static graph can guarantee completeness. UA owns structured traversal of edges it has. CBM may be called only when a graph-gap, staleness, dynamic-wiring risk, or reviewer counter-evidence trigger is recorded.

## 6. Architecture

```text
Codex              Claude Code              Antigravity
  |                     |                         |
  +---------------- host MCP adapters ------------+
                        |
                 Maika control plane
          capability routing / phase / gates
          evidence / freshness / test / review
            |             |              |
          UA-MCP        Serena           CBM
       structured     semantic IDE    fuzzy semantic
       graph/trace    read + gated    discovery and
       and impact       write        conditional gaps
            \             |              /
             +-------- current source ---+
                  exact authority + tests
```

One canonical provider contract is rendered through three host adapters. Platform-specific MCP tool naming and configuration locations do not leak into canonical skills.

## 7. Serena capability contract

Maika will add a provider with ID `serena` and kind `semantic_code_intelligence`. Canonical skills consume these capability IDs:

### 7.1 `symbolic_code_navigation`

Read-only tools:

- `get_symbols_overview`
- `find_symbol`
- `find_referencing_symbols`
- `find_declaration`
- `find_implementations`

The implementation must treat backend-dependent tools as optional contract members unless the selected language/backend fixture proves them available.

### 7.2 `code_diagnostics`

Read-only tools:

- `get_diagnostics_for_file`
- `get_diagnostics_for_symbol`

Diagnostics are observations, not completion evidence. Build, lint, and test commands remain required according to the task class.

### 7.3 `symbolic_code_editing`

Write tools:

- `replace_symbol_body`
- `insert_before_symbol`
- `insert_after_symbol`

### 7.4 `semantic_code_refactoring`

Write tools:

- `rename_symbol`
- `safe_delete_symbol`

### 7.5 Maintenance lane

`restart_language_server` is an operational recovery action. It is not evidence that a source claim or edit is correct.

## 8. Tool exposure and exclusions

The Maika-managed Serena context will use a fixed minimal tool set. It will exclude:

- all Serena memory tools;
- onboarding;
- generic file reads/writes and pattern replacement already supplied by the host;
- directory/file discovery tools already supplied by the host;
- shell execution;
- Serena workflow prompts that can bypass or conflict with Maika phases;
- project switching in single-project operation;
- the Serena dashboard by default.

Serena will start with `no-memories`, a Maika-managed context, a fixed project root, and the web dashboard disabled. Maika will not run `serena setup <host>` because that command can install host-specific prompts or hooks outside Maika's ownership. Maika will render the MCP entry itself through the existing setup path.

## 9. Routing and data flow

### 9.1 Read flow

1. Classify the question by capability rather than provider name.
2. For architecture/domain/trace/impact, probe UA freshness and use UA structured traversal.
3. For a known UA node, UA may read its source directly. If exact symbol identity, overload resolution, references, implementations, or diagnostics matter, route to Serena.
4. Use CBM semantic search only for fuzzy anchor discovery or a recorded conditional trigger.
5. Verify material exact claims against current source.
6. Record provider identity, request/response hashes, source revision, tool surface, freshness, and degradation in the existing evidence envelope.

### 9.2 Write flow

```text
approved immutable task brief
  -> Maika verifies EXECUTING state and allowed symbol/file scope
  -> Serena semantic edit/refactor
  -> capture changed files, changed symbols, and Git diff
  -> focused diagnostics plus required build/test
  -> independent task/change review
  -> evidence-bound result and knowledge impact
```

Serena success never means task completion. The diff, current source, tests, and Maika review gates remain authoritative.

## 10. Rollout phases

### 10.1 Phase 1 — read-only

The first release exposes only `symbolic_code_navigation`, `code_diagnostics`, and maintenance recovery. The generated Serena project/context must be read-only or otherwise omit all write tools from `tools/list`.

Phase 1 is available on Codex, Claude Code, and Antigravity in the same release. If one host cannot satisfy setup discovery and real tool-surface probing, the integration is not declared complete for all platforms.

### 10.2 Phase 2 — gated write

Current Maika hook matchers cover native host write tools but do not cover Serena MCP write calls. Phase 2 is blocked until all of the following are true:

1. A real PreToolUse or equivalent trigger for Serena MCP write calls is demonstrated on each supported host.
2. The existing write gate is extended; no parallel authorization mechanism is created.
3. Gate tests deny semantic writes before `EXECUTING`, outside the allowed task scope, and with stale/mismatched briefs.
4. Gate tests allow an in-scope operation in a valid execution session.
5. End-to-end tests prove diff capture, focused verification, review, and partial-failure handling.

Any platform that cannot prove interception stays read-only.

## 11. Installation and lifecycle

Serena is selected through the existing Maika MCP selection flow during `maika init` or `maika update --reconfigure`.

The supported release contract will pin `serena-agent==1.5.3`. Upgrading Serena requires refreshing the captured `tools/list` fixture, schema hash, compatibility tests, and documentation before changing the pin.

The setup path is:

1. Check `uv`, Python `>=3.11,<3.15`, Serena availability, and language-specific backend prerequisites.
2. Install the pinned Serena package through `uv tool`.
3. Render a Maika-owned Serena context and project/language configuration.
4. Render the Serena MCP entry for every enabled host adapter.
5. Start Serena with the exact project, Maika context, `no-memories`, and dashboard disabled.
6. Run `maika doctor mcp` and a real read-only symbol smoke test.

The setup renderer will extend the existing manifest-driven `MCP_SETUP.md` path. It will not introduce a second installer or doctor.

Lifecycle requirements:

- Existing projects enable Serena through `maika update --reconfigure`.
- Platform enable/disable operations preserve the shared provider selection and render/remove only platform-owned adapter configuration.
- Upgrade keeps the provider version pinned until compatibility evidence is refreshed.
- Uninstall removes Maika-owned Serena configuration without deleting user-owned source, global Serena data unrelated to Maika, or another project's configuration.
- Windows PowerShell and POSIX command forms are documented and tested for quoting/path handling.

## 12. Doctor and health model

Doctor must inspect all enabled platforms, not only the primary one. It must report:

- executable presence and Serena version;
- MCP config discovery and redacted server entry;
- project activation and selected language backend;
- real `tools/list` result and tool-contract hash;
- required read tools present;
- forbidden memory/onboarding/shell/basic file tools absent;
- write tools absent during Phase 1;
- language-server initialization and a symbol smoke-test result;
- structured degradation and remediation.

Registration alone is not health. A running MCP server without a usable project/language backend is degraded.

## 13. Error and degradation policy

- **Serena missing or unhealthy:** record degradation and route according to provider doctrine; do not silently claim semantic coverage.
- **Unsupported language or operation:** use current-source/host inspection and, where applicable, UA traversal. Lower confidence and name the missing semantic evidence.
- **LSP initialization timeout or crash:** retry within a bounded budget, restart once, then degrade.
- **Stale UA graph:** Serena may verify current symbols and CBM may recover fuzzy anchors, but stale UA traversal is navigation evidence only for affected files.
- **Conflicting providers:** do not merge conflicting claims into `verified`; resolve using current source and tests.
- **Semantic write error or partial diff:** stop, preserve the working tree, inspect the diff, and do not automatically revert user changes.
- **Tool reports success:** continue through diff, test/build, review, and evidence gates.

## 14. Security

Serena's trust model assumes a trusted local machine, MCP client, repository, and configuration. Maika therefore retains these boundaries:

- fixed minimal tool exposure;
- no Serena shell tool;
- no Serena memory or onboarding;
- no remote network binding by default;
- pinned Serena release and captured tool schemas;
- existing Maika write gate for all semantic writes;
- explicit documentation of language-server downloads and package-manager trust;
- sandbox recommendation for untrusted repositories or agents.

The installer must not silently add Serena's optional host hooks, auto-approval behavior, or global prompt overrides.

## 15. Verification plan

### 15.1 Unit and contract tests

- Provider registry and capability mapping validation.
- No capability without a real skill/consumer in the same change.
- Serena `tools/list` and input-schema fixture for the pinned release.
- Required read tools are present and forbidden tools are absent.
- Phase 1 fixture contains no write tools.
- Platform mappings contain no unknown or unresolved tool keys.
- Setup templates contain no unresolved placeholders.
- Doctor classification covers compatible, degraded, incompatible, missing executable, wrong version, missing tool, and forbidden-tool cases.

### 15.2 Platform integration tests

- Codex, Claude Code, and Antigravity render the expected MCP server command and config shape.
- Config discovery reads the rendered location and redacts sensitive environment values.
- Enabling/disabling one platform does not corrupt another platform's adapter.
- POSIX and Windows paths with spaces remain valid.

### 15.3 Read behavior tests

Use fixture repositories with representative Python, TypeScript, and Java symbols to verify:

- overview and exact symbol lookup;
- references and implementations when supported;
- file/symbol diagnostics;
- source correspondence with the current file;
- unsupported-operation degradation;
- UA-first structured trace and conditional CBM activation reasons.

Other Serena languages are documented as upstream-supported, not Maika-certified, until added to this behavioral matrix.

### 15.4 Phase 2 tests

- Each host emits an interceptable event for every Serena write tool.
- Gate deny/allow behavior is tied to task state, brief freshness, and file/symbol scope.
- Rename updates real references and produces a reviewable diff.
- Safe delete refuses or reports live usages correctly.
- Symbol replacement/insertion preserves surrounding code and line endings.
- Partial failure leaves an inspectable diff.
- Required test/build and independent review remain mandatory.

## 16. Documentation acceptance criteria

The root README must contain a complete Serena integration section covering:

1. the problem Serena solves;
2. the Maika/UA/Serena/CBM/AgentMemory/current-source responsibility matrix;
3. Phase 1 and Phase 2 architecture;
4. prerequisites for Linux, macOS, and Windows;
5. language-backend prerequisites and the distinction between upstream-supported and Maika-certified languages;
6. new-project quickstart;
7. enabling Serena in an existing Maika project;
8. exact Codex, Claude Code, and Antigravity configuration behavior;
9. the disabled Serena memory/onboarding/basic-tool surfaces;
10. doctor commands, expected healthy output, and a real smoke test;
11. troubleshooting for PATH, startup timeouts, missing language servers, unsupported tools, stale projects, and MCP discovery;
12. upgrade, rollback, disable, and uninstall procedures;
13. security, telemetry, language-server download, and sandbox boundaries;
14. limitations, including the fact that no static provider guarantees every hidden consumer.

`MCP_SETUP.md` is generated from the same manifest/setup contract used by the installer. Documentation tests will verify required commands and sections and reject unresolved placeholders. README examples and generated setup instructions must not recommend `serena setup <host>` for a Maika-managed project.

## 17. Success criteria

Phase 1 is complete only when:

- all three supported hosts configure and probe Serena successfully;
- the pinned read tool surface is enforced;
- memory/onboarding/basic write/shell tools are absent;
- representative symbol/reference/diagnostic smoke tests pass;
- UA/CBM/current-source routing matches the responsibility doctrine;
- failure cases produce structured degradation;
- README and generated setup documentation satisfy Section 16.

Phase 2 is complete only when all three platforms additionally prove write-call interception, scope enforcement, diff/test/review evidence, and partial-failure behavior.

## 18. Follow-up workstream: dogfood Maika's complete development loop

After this integration is implemented and qualified, a separate design/spec will configure the Maika repository itself to use the complete provider stack:

```text
Understand-Anything -> architecture/domain/structured trace and impact
Serena              -> exact symbols/references/diagnostics/refactoring
Codebase Memory     -> fuzzy semantic discovery and conditional graph gaps
AgentMemory         -> episodic/session recall as candidate-only memory
Maika knowledge     -> verified, version-controlled durable knowledge
```

That workstream will design a session-to-session improvement loop:

```text
bootstrap current knowledge and recall candidates
  -> gather code evidence and perform verified work
  -> end-of-session retrospective
  -> automatically capture learning candidates
  -> deduplicate and reconcile with current source
  -> promote only verified knowledge
  -> measure whether the next session starts with better context
```

Automatic capture is allowed; automatic promotion to canonical knowledge is not. The follow-up spec will cover bootstrap, capture, retention, conflict resolution, promotion gates, privacy, and effectiveness metrics. It is intentionally outside the implementation scope of this Serena provider integration.

## 19. Non-goals

- Replacing Maika with Serena.
- Replacing UA structured traversal with Serena.
- Using CBM as the default structural trace authority.
- Replacing current-source/test authority with any graph or LSP observation.
- Enabling Serena memory or onboarding.
- Enabling Serena shell/basic file tools.
- Shipping semantic write before cross-platform mechanical gating is proven.
- Implementing the Maika-repository dogfood memory loop in the same change.
