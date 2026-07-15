# Serena Semantic Provider Phase 1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Integrate `serena-agent==1.5.3` into Maika as an optional, read-only semantic symbol and diagnostics provider for Codex, Claude Code, and Antigravity, with pinned contracts, real MCP health evidence, and complete installation documentation.

**Architecture:** Maika remains the workflow, authority, write-gate, verification, and knowledge control plane. Serena runs behind one Maika-owned custom context whose `fixed_tools` exposes only eight verified read/maintenance tools; UA-MCP remains primary for architecture/domain/structured traversal, Codebase Memory remains conditional fuzzy anchor discovery, and current source plus tests remain authoritative. Phase 2 symbolic writes are a separate release and cannot start until native write-hook events are captured on all three supported hosts.

**Tech Stack:** Python 3.11+, pytest, YAML, JSON/TOML MCP configuration, MCP JSON-RPC, Serena `1.5.3`, Jinja2 scaffold templates.

## Global Constraints

- Pin Serena exactly to `serena-agent==1.5.3` (`v1.5.3`, commit `2449313c0d7427275c4c66aedff7d4881782f713`).
- Support all Maika hosts: `codex`, `claude-code`, and `antigravity`.
- Phase 1 exposed tools are exactly: `get_symbols_overview`, `find_symbol`, `find_referencing_symbols`, `find_implementations`, `find_declaration`, `get_diagnostics_for_file`, `get_diagnostics_for_symbol`, `restart_language_server`.
- Do not expose Serena editing, memory, onboarding, basic file/search/shell, project-switching, workflow-prompt, or dashboard tools.
- UA-MCP owns architecture, domain, structured relationships, call trace, impact, path, hierarchy, entry-point, and graph-backed consumer analysis; its full 18-tool contract remains intact.
- Codebase Memory is primary only for fuzzy semantic anchor discovery and is conditional for graph gaps, staleness, or counter-evidence.
- Serena is primary only for exact symbol identity/navigation/reference/implementation and LSP diagnostics.
- AgentMemory observations are historical candidates; only verified candidates may be promoted to Maika durable knowledge.
- Current source and observed test/runtime output override every provider.
- Do not claim static hidden-consumer completeness; record provider scope and use current-source counter-evidence when dynamic wiring risk applies.
- Do not mutate user-global MCP configuration. Generate copy/paste-safe workspace snippets and inspect the actual native config with doctor.
- Do not add Serena write capabilities, write tool mappings, or write invocation lanes in Phase 1.
- Follow `.maika/DEVELOPMENT_RULES.md`, especially R1, R3, R4, R5, and R7.

---

## File Map

| File | Responsibility |
|---|---|
| `cli/mcp/integration/serena.py` | Pinned Phase 1 tool contract, runtime `tools/list` validation, response normalization. |
| `cli/tests/fixtures/provider_contracts/serena/*` | Hash-bound MCP `tools/list` evidence captured from the pinned release and Maika context. |
| `.maika/config/serena-context.yml` | Single-project, no-memory, fixed read-only Serena surface. |
| `cli/plugin-manifest.yaml` | Serena selection, exact install/server recipe, conditional context scaffold. |
| `.maika/config/provider-registry.yaml` | Serena identity, authority lane, read-only tool contract. |
| `.maika/profiles/capability-registry.yaml` | Canonical `symbolic_code_navigation` and `code_diagnostics` capabilities and their trigger. |
| `.maika/profiles/provider-capabilities.yaml` | Concrete capability-to-Serena tool routing. |
| `.maika/rules/jit/providers.md` | Correct UA/Serena/CBM/AgentMemory/current-source doctrine. |
| `.maika/skills/grounding-explorer/SKILL.md` | Conditional symbolic navigation consumer. |
| `.maika/skills/executing-task/SKILL.md` | Conditional diagnostics consumer after source changes. |
| `.maika/skills/reviewing-task/SKILL.md` | Independent symbolic reference and diagnostics counter-evidence. |
| `.maika/skills/reviewing-change/SKILL.md` | Change-level symbolic and diagnostics counter-evidence. |
| `cli/agent_content/provider_capabilities.py` | Mechanical Serena contract and lane validation. |
| `cli/commands/provider.py` | Serena observation normalization in recorded evidence. |
| `cli/platforms/{base,codex,claude_code,antigravity}.py` | Eight optional abstract-to-native Serena tool mappings. |
| `cli/mcp/ua_setup.py` | Generic command detection and JSON/TOML, multi-provider setup sections. |
| `cli/commands/init.py` | Aggregate all selected setup providers instead of overwriting `MCP_SETUP.md`. |
| `cli/commands/platform.py` | Refresh setup instructions when an additional host is enabled. |
| `cli/mcp/doctor.py` | Runtime Serena `tools/list` report from the configured server. |
| `README.md` | Concise integration overview and platform support matrix. |
| `docs/providers/serena.md` | Complete install, configuration, verification, troubleshooting, upgrade, and Phase 2 gate guide. |

---

### Task 1: Pin and validate the Serena read-only MCP contract

**Files:**
- Create: `cli/mcp/integration/serena.py`
- Create: `.maika/config/serena-context.yml`
- Create: `cli/tests/fixtures/provider_contracts/serena/tools-list-readonly-v1.json`
- Create: `cli/tests/fixtures/provider_contracts/serena/tools-list-readonly-v1.provenance.yaml`
- Modify: `cli/tests/test_provider_adapters.py`
- Modify: `cli/tests/test_provider_contract_fixtures.py`

**Interfaces:**
- Produces: `SERENA_READ_TOOLS: frozenset[str]`, `SERENA_FORBIDDEN_TOOLS: frozenset[str]`, `tool_surface_hash(tools) -> str`, `validate_tools_list(snapshot, expected_tool_surface_hash="") -> dict`, `normalize_response(tool, raw) -> dict`.
- Consumes: `cli.mcp.integration.base.hash_payload` and `cli.mcp.integration.contract_fixtures.load_contract_fixture`.

- [ ] **Step 1: Add failing adapter tests**

```python
from cli.mcp.integration import agent_memory, codebase_memory, serena, understand_anything

def test_serena_readonly_surface_is_exact_and_write_free():
    fixture = _fixture("serena", "tools-list-readonly-v1.json")
    result = serena.validate_tools_list(fixture)
    assert result["status"] == "ready"
    assert set(result["tools"]) == serena.SERENA_READ_TOOLS
    assert set(result["tools"]).isdisjoint(serena.SERENA_FORBIDDEN_TOOLS)

def test_serena_write_or_memory_tool_degrades_contract():
    fixture = _fixture("serena", "tools-list-readonly-v1.json")
    changed = json.loads(json.dumps(fixture))
    changed["tools"].append({"name": "rename_symbol", "inputSchema": {"type": "object"}})
    result = serena.validate_tools_list(changed)
    assert result["status"] == "degraded"
    assert result["forbidden"] == ["rename_symbol"]

def test_serena_observation_is_semantic_not_architecture_authority():
    result = serena.normalize_response("find_symbol", b'{"symbols": []}')
    assert result["authority"] == "semantic_symbol_resolution"
    assert result["canonical"] is False
```

- [ ] **Step 2: Run the tests and observe the missing adapter/fixture failure**

Run: `python3 -m pytest cli/tests/test_provider_adapters.py -q`

Expected: FAIL during import because `cli.mcp.integration.serena` does not exist.

- [ ] **Step 3: Add the adapter with the exact Phase 1 contract**

```python
"""Serena adapter for Maika's pinned Phase 1 read-only semantic surface."""
from __future__ import annotations

import hashlib
import json

from cli.mcp.integration.base import hash_payload

PROVIDER_ID = "serena"
SERENA_READ_TOOLS = frozenset({
    "get_symbols_overview", "find_symbol", "find_referencing_symbols",
    "find_implementations", "find_declaration", "get_diagnostics_for_file",
    "get_diagnostics_for_symbol", "restart_language_server",
})
SERENA_FORBIDDEN_TOOLS = frozenset({
    "replace_symbol_body", "insert_after_symbol", "insert_before_symbol",
    "rename_symbol", "safe_delete_symbol", "create_text_file", "replace_content",
    "delete_lines", "replace_lines", "insert_at_line", "read_file", "list_dir",
    "find_file", "search_for_pattern", "execute_shell_command", "write_memory",
    "read_memory", "list_memories", "delete_memory", "rename_memory", "edit_memory",
    "activate_project", "remove_project", "onboarding", "initial_instructions",
    "open_dashboard", "serena_info",
})

def tool_surface_hash(tools: list[dict] | list[str]) -> str:
    normalized = sorted(
        [item if isinstance(item, dict) else {"name": str(item)} for item in tools],
        key=lambda item: str(item.get("name") or ""),
    )
    payload = json.dumps(normalized, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return "sha256:" + hashlib.sha256(payload.encode("utf-8")).hexdigest()

def validate_tools_list(snapshot: dict, *, expected_tool_surface_hash: str = "") -> dict:
    tools = snapshot.get("tools") if isinstance(snapshot, dict) else None
    if not isinstance(tools, list):
        return {"status": "degraded", "reason": "tools/list missing tools array"}
    names = {str(item.get("name")) for item in tools if isinstance(item, dict) and item.get("name")}
    missing = sorted(SERENA_READ_TOOLS - names)
    unexpected = sorted(names - SERENA_READ_TOOLS)
    forbidden = sorted(names & SERENA_FORBIDDEN_TOOLS)
    observed_hash = tool_surface_hash(tools)
    hash_changed = bool(expected_tool_surface_hash and observed_hash != expected_tool_surface_hash)
    ready = not missing and not unexpected and not forbidden and not hash_changed
    return {
        "status": "ready" if ready else "degraded",
        "missing": missing, "unexpected": unexpected, "forbidden": forbidden,
        "tool_surface_hash": observed_hash, "prior_probe_valid": not hash_changed,
        "tools": sorted(names),
    }

def normalize_response(tool: str, raw: bytes | str) -> dict:
    if tool not in SERENA_READ_TOOLS:
        raise ValueError(f"unknown Serena Phase 1 tool {tool!r}")
    return {
        "provider_id": PROVIDER_ID,
        "tool": tool,
        "response_hash": hash_payload(raw),
        "authority": "semantic_symbol_resolution",
        "canonical": False,
        "status": "success",
        "provider_snapshot": {"version": "1.5.3", "language_backend": "unverified"},
    }
```

- [ ] **Step 4: Create the exact fixed context and capture the real fixture**

Create `.maika/config/serena-context.yml` with this exact content:

```yaml
description: Maika read-only semantic code intelligence
prompt: |
  Serena supplies semantic symbol and diagnostic observations. Maika owns workflow,
  write authority, verification, memory, and durable knowledge. Current source and
  observed tests override Serena observations.
fixed_tools:
  - get_symbols_overview
  - find_symbol
  - find_referencing_symbols
  - find_implementations
  - find_declaration
  - get_diagnostics_for_file
  - get_diagnostics_for_symbol
  - restart_language_server
single_project: true
```

Serena `1.5.3` does not accept `structured_tool_output` in a custom context;
omit that field. This was verified against the pinned runtime during Task 1.

Create a throwaway Serena project and `/tmp/maika-serena-contract/mcp.json` with this content:

```json
{
  "mcpServers": {
    "serena": {
      "command": "serena",
      "args": [
        "start-mcp-server", "--project", "/tmp/maika-serena-contract",
        "--context", "/home/zane/Desktop/agent-memory-arch-v3/.maika/config/serena-context.yml",
        "--mode", "no-memories", "--enable-web-dashboard", "false",
        "--open-web-dashboard", "false"
      ]
    }
  }
}
```

Run the existing MCP bridge against that recipe:

```bash
uvx --from 'serena-agent==1.5.3' serena project create /tmp/maika-serena-contract --language python
python3 .maika/tools/mcp-bridge/mcp_client.py \
  --config /tmp/maika-serena-contract/mcp.json --server serena tools-list
```

Copy only `result.result.tools` into `{"tools": [...]}` and verify the names equal the eight Global Constraints tools. Start the provenance sidecar with these seven literal fields:

```yaml
provider: serena
repository: oraios/serena
revision: 2449313c0d7427275c4c66aedff7d4881782f713
captured_at: '2026-07-16T00:00:00Z'
tool: tools/list
contract_version: 1
```

Calculate the required value with:

```bash
python3 -c 'from pathlib import Path; from cli.mcp.integration.contract_fixtures import content_sha256; print(content_sha256(Path("cli/tests/fixtures/provider_contracts/serena/tools-list-readonly-v1.json").read_bytes()))'
```

Append `content_sha256:` followed by the literal output of that command. The fixture validator must reject any other value.

- [ ] **Step 5: Run focused contract tests**

Run: `python3 -m pytest cli/tests/test_provider_adapters.py cli/tests/test_provider_contract_fixtures.py -q`

Expected: PASS, with no missing, unexpected, forbidden, or hash mismatch result.

- [ ] **Step 6: Commit**

```bash
git add cli/mcp/integration/serena.py .maika/config/serena-context.yml cli/tests/fixtures/provider_contracts/serena cli/tests/test_provider_adapters.py cli/tests/test_provider_contract_fixtures.py
git commit -m "feat: pin Serena read-only tool contract"
```

### Task 2: Add the Maika-owned fixed Serena context

**Files:**
- Modify: `cli/plugin-manifest.yaml`
- Modify: `cli/tests/test_manifest_setup.py`
- Modify: `cli/tests/test_scaffold.py`

**Interfaces:**
- Produces: scaffolded `.maika/config/serena-context.yml` whenever selected MCP `serena` provides `semantic_code_intelligence`.
- Consumes: `scaffold_plugins(... requires_capability ...)` and Jinja `project_root` server expansion.

- [ ] **Step 1: Add failing manifest and scaffold tests**

```python
def test_serena_manifest_is_pinned_and_uses_maika_context():
    manifest = load_manifest(MAIKA_ROOT)
    cap = manifest["mcp_capabilities"]["serena"]
    assert cap["provides"] == "semantic_code_intelligence"
    assert cap["setup"]["version"] == "1.5.3"
    assert cap["setup"]["server"]["command"] == "serena"
    assert "{project_root}/.maika/config/serena-context.yml" in cap["setup"]["server"]["args"]

def test_serena_context_scaffolds_only_when_selected(tmp_path):
    selected = _scaffold(tmp_path / "selected", ["serena"])
    omitted = _scaffold(tmp_path / "omitted", [])
    assert (selected / ".maika/config/serena-context.yml").is_file()
    assert not (omitted / ".maika/config/serena-context.yml").exists()
```

- [ ] **Step 2: Run focused tests to verify failure**

Run: `python3 -m pytest cli/tests/test_manifest_setup.py cli/tests/test_scaffold.py -q`

Expected: FAIL because the `serena` manifest capability and context plugin are absent.

- [ ] **Step 3: Verify the fixed context created in Task 1**

```yaml
description: Maika read-only semantic code intelligence
prompt: |
  Serena supplies semantic symbol and diagnostic observations. Maika owns workflow,
  write authority, verification, memory, and durable knowledge. Current source and
  observed tests override Serena observations.
fixed_tools:
  - get_symbols_overview
  - find_symbol
  - find_referencing_symbols
  - find_implementations
  - find_declaration
  - get_diagnostics_for_file
  - get_diagnostics_for_symbol
  - restart_language_server
single_project: true
```

Do not add `structured_tool_output`: the pinned Serena `1.5.3` context schema
rejects it. The fixed tool list is the Phase 1 surface boundary.

- [ ] **Step 4: Add the exact manifest capability and conditional plugin**

```yaml
  serena:
    provides: semantic_code_intelligence
    display: "Serena — read-only semantic symbols, references and diagnostics"
    setup:
      version: "1.5.3"
      engine_check:
        default: {kind: command_exists, command: serena}
      install_hint:
        default: "uv tool install --python 3.13 'serena-agent==1.5.3'"
      prepare_hint: "serena project create {project_root} --language {language}  # omit --language for Maika language 'other' and let Serena infer"
      server:
        command: serena
        args:
          - start-mcp-server
          - --project
          - "{project_root}"
          - --context
          - "{project_root}/.maika/config/serena-context.yml"
          - --mode
          - no-memories
          - --enable-web-dashboard
          - "false"
          - --open-web-dashboard
          - "false"
```

```yaml
  - name: serena-context
    type: profile
    source: config/serena-context.yml
    template: false
    requires_capability: semantic_code_intelligence
    output: "{{ platform.framework_root }}/config/serena-context.yml"
```

- [ ] **Step 5: Run focused tests**

Run: `python3 -m pytest cli/tests/test_manifest_setup.py cli/tests/test_scaffold.py -q`

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add cli/plugin-manifest.yaml cli/tests/test_manifest_setup.py cli/tests/test_scaffold.py
git commit -m "feat: scaffold Maika Serena read-only context"
```

### Task 3: Register Serena capabilities without weakening UA ownership

**Files:**
- Modify: `.maika/profiles/capability-registry.yaml`
- Modify: `.maika/profiles/provider-capabilities.yaml`
- Modify: `.maika/config/provider-registry.yaml`
- Modify: `cli/agent_content/provider_capabilities.py`
- Modify: `cli/tests/test_provider_capabilities.py`

**Interfaces:**
- Produces: capability IDs `symbolic_code_navigation`, `code_diagnostics`; trigger `language_diagnostics_required`; provider authority lane `semantic_symbol_resolution`.
- Consumes: Task 1 `SERENA_READ_TOOLS` values; canonical provider validator.

- [ ] **Step 1: Add failing canonical contract tests**

```python
def test_serena_is_primary_only_for_symbols_and_diagnostics():
    mapping, capabilities = _docs()
    providers = load_provider_registry(FRAMEWORK)
    serena = mapping["providers"]["serena"]["capabilities"]
    assert serena["symbolic_code_navigation"]["role"] == "primary"
    assert serena["code_diagnostics"]["role"] == "primary"
    assert capabilities["capabilities"]["architecture_discovery"]["primary_provider"] == "understand-anything"
    assert capabilities["capabilities"]["call_chain_trace"]["primary_provider"] == "understand-anything"
    assert set(providers["providers"]["serena"]["tool_contract"]["tools"]) == SERENA_READ_TOOLS

def test_serena_contract_has_only_read_only_discovery_lane():
    providers = load_provider_registry(FRAMEWORK)
    lanes = providers["providers"]["serena"]["tool_contract"]["lanes"]
    assert set(lanes) == {"discovery"}
    assert lanes["discovery"]["mutability"] == "read_only"
```

- [ ] **Step 2: Run the validator tests and observe unknown provider/capability failures**

Run: `python3 -m pytest cli/tests/test_provider_capabilities.py -q`

Expected: FAIL because `serena`, the two capabilities, and authority lane are not registered.

- [ ] **Step 3: Add canonical capability entries**

```yaml
  symbolic_code_navigation:
    description: Resolve exact symbol identity, declarations, implementations and LSP references.
    tools: [serena_symbols_overview, serena_find_symbol, serena_find_references, serena_find_declaration, serena_find_implementations]
    health: [serena]
    primary_provider: serena
    preferred_evidence: [symbol_identity, declaration, implementation, semantic_reference]
  code_diagnostics:
    description: Read current language-server diagnostics without editing source.
    tools: [serena_file_diagnostics, serena_symbol_diagnostics, serena_restart_language_server]
    health: [serena]
    primary_provider: serena
    preferred_evidence: [language_diagnostic]

  language_diagnostics_required:
    description: Implementation or review needs current LSP diagnostics for supported changed source.
```

- [ ] **Step 4: Add the concrete mapping and provider registry entries**

```yaml
  serena:
    capabilities:
      symbolic_code_navigation:
        role: primary
        tools: [get_symbols_overview, find_symbol, find_referencing_symbols, find_implementations, find_declaration]
      code_diagnostics:
        role: primary
        tools: [get_diagnostics_for_file, get_diagnostics_for_symbol, restart_language_server]
```

```yaml
  semantic_symbol_resolution:
    preferred: serena
    corroborating: [current-source, understand-anything]
    conflict_action: verify_current_source
```

```yaml
  serena:
    display_name: Serena
    kind: semantic_language_server
    setup_ref: serena
    tool_contract:
      tools: [get_symbols_overview, find_symbol, find_referencing_symbols, find_implementations, find_declaration, get_diagnostics_for_file, get_diagnostics_for_symbol, restart_language_server]
      lanes:
        discovery:
          tools: [get_symbols_overview, find_symbol, find_referencing_symbols, find_implementations, find_declaration, get_diagnostics_for_file, get_diagnostics_for_symbol, restart_language_server]
          mutability: read_only
    capabilities:
      primary: [symbolic_code_navigation, code_diagnostics]
```

- [ ] **Step 5: Extend mechanical validation**

Add `SERENA_TOOLS` with the same eight names to `provider_capabilities.py`. Validate exact equality, exactly one `discovery` lane, `mutability: read_only`, and equality between lane tools and contract tools. Add `serena` to the manifest-backed provider identity path; do not add it to `SYNTHETIC_PROVIDERS`.

- [ ] **Step 6: Run provider and identity tests**

Run: `python3 -m pytest cli/tests/test_provider_capabilities.py -q`

Expected: PASS; UA's 18-tool snapshot and primary architecture/trace mappings remain unchanged.

- [ ] **Step 7: Commit**

```bash
git add .maika/profiles/capability-registry.yaml .maika/profiles/provider-capabilities.yaml .maika/config/provider-registry.yaml cli/agent_content/provider_capabilities.py cli/tests/test_provider_capabilities.py
git commit -m "feat: register Serena semantic capabilities"
```

### Task 4: Route Serena through skills and provider evidence

**Files:**
- Modify: `.maika/rules/jit/providers.md`
- Modify: `.maika/skills/grounding-explorer/SKILL.md`
- Modify: `.maika/skills/executing-task/SKILL.md`
- Modify: `.maika/skills/reviewing-task/SKILL.md`
- Modify: `.maika/skills/reviewing-change/SKILL.md`
- Modify: `cli/commands/provider.py`
- Modify: `cli/tests/test_structured_trace_skills.py`
- Modify: `cli/tests/test_provider_invocations.py`

**Interfaces:**
- Consumes: Task 1 `serena.normalize_response`; Task 3 capability IDs and trigger.
- Produces: conditional calls with recorded trigger/reason and normalized Serena observations.

- [ ] **Step 1: Add failing skill-consumer tests**

```python
def test_serena_capabilities_have_real_skill_consumers(skill_docs):
    assert skill_docs["grounding-explorer"]["capabilities"]["conditional"]["symbolic_code_navigation"]["triggers"] == [
        "unresolved_anchor", "graph_gap", "relevant_graph_stale"
    ]
    for name in ("executing-task", "reviewing-task", "reviewing-change"):
        assert "language_diagnostics_required" in skill_docs[name]["capabilities"]["conditional"]["code_diagnostics"]["triggers"]

def test_ua_remains_trace_owner_in_provider_doctrine():
    text = PROVIDERS_RULE.read_text(encoding="utf-8")
    assert "UA-MCP" in text and "18 tools" in text
    assert "Serena không thay thế UA-MCP" in text
    assert "không bảo đảm hidden-consumer completeness" in text
```

- [ ] **Step 2: Run tests to verify missing consumers**

Run: `python3 -m pytest cli/tests/test_structured_trace_skills.py -q`

Expected: FAIL because the two new capability IDs and diagnostics trigger have no skill consumers.

- [ ] **Step 3: Add conditional skill contracts**

Use these exact front-matter routes:

```yaml
# grounding-explorer
    symbolic_code_navigation:
      triggers: [unresolved_anchor, graph_gap, relevant_graph_stale]

# executing-task
  conditional:
    code_diagnostics:
      triggers: [language_diagnostics_required]

# reviewing-task and reviewing-change
    symbolic_code_navigation:
      triggers: [hidden_consumer_risk, reviewer_counter_evidence, relevant_graph_stale]
    code_diagnostics:
      triggers: [language_diagnostics_required]
```

In each body, state that symbolic references are scoped LSP evidence, not proof of every reflective/configured/event consumer; current source is required for the material claim.

- [ ] **Step 4: Rewrite provider doctrine around ownership**

The rule must state:

1. UA-MCP's 18 tools own graph/project freshness, architecture/domain discovery, relationships, trace, impact, path, hierarchy, entry points, and node source access.
2. `get_node_source` reads source for a UA node; it does not reduce UA to a source-only provider.
3. Serena owns exact symbol identity, declaration, implementation, LSP reference, and diagnostics observations.
4. Codebase Memory owns fuzzy semantic anchor discovery and is conditional counter-evidence only.
5. AgentMemory is historical candidate context; current source/tests are authoritative.
6. No static provider guarantees hidden consumers outside the semantics it models.

- [ ] **Step 5: Normalize Serena provider recordings**

```python
from cli.mcp.integration import agent_memory, codebase_memory, current_source, serena, understand_anything

# in the provider-specific normalization chain
elif provider_id == serena.PROVIDER_ID:
    normalized = serena.normalize_response(tool, response_bytes)
```

- [ ] **Step 6: Run skill and command tests**

Run: `python3 -m pytest cli/tests/test_structured_trace_skills.py cli/tests/test_provider_invocations.py cli/tests/test_trace_evidence_flow.py -q`

Expected: PASS and Serena calls outside its read-only discovery lane remain rejected.

- [ ] **Step 7: Commit**

```bash
git add .maika/rules/jit/providers.md .maika/skills/grounding-explorer/SKILL.md .maika/skills/executing-task/SKILL.md .maika/skills/reviewing-task/SKILL.md .maika/skills/reviewing-change/SKILL.md cli/commands/provider.py cli/tests/test_structured_trace_skills.py cli/tests/test_provider_invocations.py
git commit -m "feat: route Serena semantic evidence through Maika"
```

### Task 5: Add Serena tool mappings for every supported platform

**Files:**
- Modify: `cli/platforms/base.py`
- Modify: `cli/platforms/codex.py`
- Modify: `cli/platforms/claude_code.py`
- Modify: `cli/platforms/antigravity.py`
- Modify: `cli/platforms/generic.py`
- Modify: `cli/tests/test_platforms.py`

**Interfaces:**
- Produces: eight optional abstract Serena operations resolvable in all platform render contexts.
- Consumes: Task 3 capability registry tool names.

- [ ] **Step 1: Add failing cross-platform mapping tests**

```python
SERENA_MAPPING = {
    "serena_symbols_overview": "get_symbols_overview",
    "serena_find_symbol": "find_symbol",
    "serena_find_references": "find_referencing_symbols",
    "serena_find_declaration": "find_declaration",
    "serena_find_implementations": "find_implementations",
    "serena_file_diagnostics": "get_diagnostics_for_file",
    "serena_symbol_diagnostics": "get_diagnostics_for_symbol",
    "serena_restart_language_server": "restart_language_server",
}

def test_serena_mapping_exists_on_all_supported_platforms():
    for cls in (CodexPlatform, ClaudeCodePlatform, AntigravityPlatform):
        assert set(SERENA_MAPPING) <= set(cls().tool_mapping)

def test_serena_native_names_are_platform_correct():
    assert ClaudeCodePlatform().tool_mapping["serena_find_symbol"] == "mcp__serena__find_symbol"
    assert AntigravityPlatform().tool_mapping["serena_find_symbol"] == "mcp_serena_find_symbol"
    assert CodexPlatform().tool_mapping["serena_find_symbol"] == "find_symbol"
```

- [ ] **Step 2: Run tests and observe unknown/missing mappings**

Run: `python3 -m pytest cli/tests/test_platforms.py -q`

Expected: FAIL because the optional mapping vocabulary does not include Serena operations.

- [ ] **Step 3: Add all eight names to `OPTIONAL_TOOL_KEYS` and each adapter**

Codex and Generic values are the raw right-hand names in `SERENA_MAPPING`. Claude Code prefixes each of those names with `mcp__serena__`; Antigravity prefixes each with `mcp_serena_`. Do not add any editing tool mapping.

- [ ] **Step 4: Run all platform tests**

Run: `python3 -m pytest cli/tests/test_platforms.py cli/tests/test_snapshots.py -q`

Expected: PASS with no unknown optional mappings and no snapshot drift outside rendered Maika content.

- [ ] **Step 5: Commit**

```bash
git add cli/platforms/base.py cli/platforms/codex.py cli/platforms/claude_code.py cli/platforms/antigravity.py cli/platforms/generic.py cli/tests/test_platforms.py
git commit -m "feat: map Serena reads across Maika platforms"
```

### Task 6: Generate one complete multi-provider, multi-platform setup guide

**Files:**
- Modify: `cli/mcp/ua_setup.py`
- Modify: `cli/commands/init.py`
- Modify: `cli/commands/update.py`
- Modify: `cli/commands/platform.py`
- Modify: `cli/tests/test_ua_setup.py`
- Modify: `cli/tests/test_init.py`
- Modify: `cli/tests/test_update.py`
- Modify: `cli/tests/test_platform_command.py`

**Interfaces:**
- Produces: `resolve_engine_check` support for `{kind: command_exists, command: str}`; `render_server_snippet(..., platform) -> str`; `render_mcp_setup_section(...) -> str`; atomic aggregate `MCP_SETUP.md`.
- Consumes: selected MCPs, all enabled project platforms, manifest setup blocks.

- [ ] **Step 1: Add failing setup tests**

```python
def test_command_exists_engine_check(monkeypatch, tmp_path):
    monkeypatch.setattr("cli.mcp.ua_setup.shutil.which", lambda command: "/bin/serena" if command == "serena" else None)
    setup = {"engine_check": {"default": {"kind": "command_exists", "command": "serena"}}}
    assert ua_setup.resolve_engine_check(setup, "codex", tmp_path) is True

def test_codex_server_snippet_is_toml():
    text = ua_setup.render_server_snippet(SERENA_SETUP, server_key="serena", platform="codex", ua_mcp_dir="", project_root="/proj")
    assert "[mcp_servers.serena]" in text
    assert 'command = "serena"' in text

def test_json_hosts_receive_json_snippets():
    for platform in ("claude-code", "antigravity"):
        text = ua_setup.render_server_snippet(SERENA_SETUP, server_key="serena", platform=platform, ua_mcp_dir="", project_root="/proj")
        assert json.loads(text)["mcpServers"]["serena"]["command"] == "serena"

def test_setup_aggregates_multiple_providers_and_enabled_hosts(tmp_path):
    emit_mcp_setup_files(tmp_path, ["codex", "claude-code", "antigravity"], ["understand-anything", "codebase-memory-mcp", "serena"], manifest, "/srv/ua")
    text = (tmp_path / ".maika/MCP_SETUP.md").read_text(encoding="utf-8")
    for provider in ("understand-anything", "codebase-memory-mcp", "serena"):
        assert f"## Provider: {provider}" in text
    for platform in ("Codex", "Claude Code", "Antigravity"):
        assert platform in text
```

- [ ] **Step 2: Run setup tests and confirm overwrite/format failures**

Run: `python3 -m pytest cli/tests/test_ua_setup.py cli/tests/test_init.py -q`

Expected: FAIL because only path/file engine checks exist, Codex is rendered as JSON, and `emit_mcp_setup_files` overwrites prior providers.

- [ ] **Step 3: Implement command detection and platform-native rendering**

Import `shutil`. For `command_exists`, return `shutil.which(spec["command"]) is not None`. Render Codex with:

```toml
[mcp_servers.serena]
command = "serena"
args = ["start-mcp-server", "--project", "/proj", "--context", "/proj/.maika/config/serena-context.yml", "--mode", "no-memories", "--enable-web-dashboard", "false", "--open-web-dashboard", "false"]
```

Render Claude Code and Antigravity as the existing `{"mcpServers": ...}` JSON shape. Omit an empty `env` object from both formats.

- [ ] **Step 4: Replace per-provider writes with one aggregate render**

`emit_mcp_setup_files` must receive `platform_keys: list[str]`, collect every selected provider's setup section, join once under `# Maika MCP Setup`, then call `write_text` exactly once. It must still remove a stale file when no selected provider has a setup block.

Prepare commands must expand `{project_root}` and `{language}`. When Maika language is `other`, render `serena project create /absolute/project/path` without a `--language` argument. No separate Serena index build is required; explain that the LSP initializes on project activation.

- [ ] **Step 5: Refresh setup instructions on host enable**

After `project.enable`, rebuild `MCP_SETUP.md` using `project_config["platforms"]["enabled"]`, resolved MCP selection/language, and the same aggregate renderer. Stage the refreshed file in the existing adapter transaction; do not write it after the transaction.

- [ ] **Step 6: Run init, update, and platform lifecycle tests**

Run: `python3 -m pytest cli/tests/test_ua_setup.py cli/tests/test_init.py cli/tests/test_update.py cli/tests/test_platform_command.py -q`

Expected: PASS; a UA+CBM+Serena selection retains all three sections after init and update, and enabling each host adds its native snippet without deleting prior sections.

- [ ] **Step 7: Commit**

```bash
git add cli/mcp/ua_setup.py cli/commands/init.py cli/commands/update.py cli/commands/platform.py cli/tests/test_ua_setup.py cli/tests/test_init.py cli/tests/test_update.py cli/tests/test_platform_command.py
git commit -m "feat: render complete cross-platform MCP setup"
```

### Task 7: Probe Serena's real MCP surface in doctor

**Files:**
- Create: `cli/mcp/runtime_probe.py`
- Modify: `cli/mcp/doctor.py`
- Modify: `cli/tests/test_mcp_doctor.py`

**Interfaces:**
- Produces: `probe_tools_list(server: dict, bridge_path: Path) -> tuple[dict | None, str]`; doctor setup lines `contract: READY ...` or `contract: DEGRADED ...`.
- Consumes: Task 1 `serena.validate_tools_list`, actual matched native config, existing `.maika/tools/mcp-bridge/mcp_client.py`.

- [ ] **Step 1: Add failing runtime-doctor tests**

```python
def test_doctor_marks_serena_ready_from_real_tools_list(tmp_path, monkeypatch):
    target, home = _init_serena(tmp_path)
    fixture = json.loads((FIXTURES / "serena/tools-list-readonly-v1.json").read_text())
    monkeypatch.setattr("cli.mcp.doctor.probe_tools_list", lambda server, bridge_path: (fixture, ""))
    status = build_doctor_status(target, home, maika_root=MAIKA_ROOT)
    assert "contract: READY (8 read-only tools)" in status.setup_reports["serena"]

def test_doctor_degrades_serena_when_write_tool_is_exposed(tmp_path, monkeypatch):
    target, home = _init_serena(tmp_path)
    snapshot = {"tools": [{"name": "rename_symbol", "inputSchema": {"type": "object"}}]}
    monkeypatch.setattr("cli.mcp.doctor.probe_tools_list", lambda server, bridge_path: (snapshot, ""))
    status = build_doctor_status(target, home, maika_root=MAIKA_ROOT)
    assert any("DEGRADED" in line and "rename_symbol" in line for line in status.setup_reports["serena"])
```

- [ ] **Step 2: Run doctor tests and observe missing probe**

Run: `python3 -m pytest cli/tests/test_mcp_doctor.py -q`

Expected: FAIL because doctor only checks config presence and never runs `tools/list`.

- [ ] **Step 3: Implement the narrow bridge loader**

```python
from __future__ import annotations
import importlib.util
from pathlib import Path

def probe_tools_list(server: dict, bridge_path: Path) -> tuple[dict | None, str]:
    spec = importlib.util.spec_from_file_location("maika_mcp_runtime_probe", bridge_path)
    if spec is None or spec.loader is None:
        return None, "MCP bridge could not be loaded"
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    if "command" in server:
        response, error = module.call_stdio(server, "tools-list", None, {})
    else:
        response, error = module.call_http(server, "tools-list", None, {})
    if error:
        return None, error
    return ((response or {}).get("result") or None), ""
```

- [ ] **Step 4: Add Serena-only doctor contract reporting**

Probe only when `serena` is selected, matched, and its engine check passes. Use `maika_root / ".maika/tools/mcp-bridge/mcp_client.py"`. Feed the returned result into `serena.validate_tools_list`. Report missing/unexpected/forbidden names without secrets or raw env values. A failed launch/handshake is `contract: DEGRADED — <error>`; it is never reported as READY from config presence alone.

- [ ] **Step 5: Run doctor and bridge regression tests**

Run: `python3 -m pytest cli/tests/test_mcp_doctor.py cli/tests/test_mcp_bridge.py cli/tests/test_mcp_config.py -q`

Expected: PASS, including secret-redaction tests.

- [ ] **Step 6: Commit**

```bash
git add cli/mcp/runtime_probe.py cli/mcp/doctor.py cli/tests/test_mcp_doctor.py
git commit -m "feat: verify Serena runtime tool surface"
```

### Task 8: Write complete user documentation for every Maika platform

**Files:**
- Modify: `README.md`
- Create: `docs/providers/serena.md`
- Create: `cli/tests/test_serena_documentation.py`

**Interfaces:**
- Produces: one authoritative Serena install/operation guide linked from the README.
- Consumes: exact commands and config formats from Tasks 2, 6, and 7.

- [ ] **Step 1: Add failing documentation assertions**

```python
def test_serena_guide_covers_all_supported_platforms_and_phase_boundary():
    text = (ROOT / "docs/providers/serena.md").read_text(encoding="utf-8")
    for term in ("Codex", "Claude Code", "Antigravity", "serena-agent==1.5.3"):
        assert term in text
    for tool in SERENA_READ_TOOLS:
        assert tool in text
    assert "UA-MCP" in text and "18 tools" in text
    assert "Phase 2" in text and "not enabled" in text
    assert "maika doctor mcp" in text

def test_readme_links_serena_guide():
    assert "docs/providers/serena.md" in (ROOT / "README.md").read_text(encoding="utf-8")
```

- [ ] **Step 2: Run the documentation tests and observe the missing guide**

Run: `python3 -m pytest cli/tests/test_serena_documentation.py -q`

Expected: FAIL because the guide and README link do not exist.

- [ ] **Step 3: Write `docs/providers/serena.md` with these complete sections**

1. Purpose and non-goals, including the exact UA/Serena/CBM/AgentMemory/current-source authority table.
2. Prerequisites: Python range supported by Serena, `uv`, Serena pin, supported Maika languages, and LSP-specific prerequisites.
3. Selection during `maika init` and resulting Maika-owned context path.
4. Project creation command for each Maika language; for `other`, use Serena inference and then inspect `.serena/project.yml`.
5. Exact Codex TOML workspace config.
6. Exact Claude Code JSON workspace config.
7. Exact Antigravity JSON workspace config.
8. Verification: `serena tools list --all --quiet`, `maika doctor mcp --target /absolute/project/path`, expected eight-tool READY surface, and one symbol/reference/diagnostic smoke call.
9. Troubleshooting: binary missing, project config missing, language server unavailable, empty symbols, stale LSP, unexpected/write tools, Windows path quoting, and logs without secrets.
10. Upgrade procedure: change pin, recapture `tools/list`, update provenance hash, run contract/platform/full CI, and only then update docs.
11. Phase 2 release gate: write tools are not enabled; require actual native hook event payloads for all three hosts, extend existing write gate, deny pathless symbol writes, and run bypass characterization before any registry/mapping change.
12. Uninstall: remove `serena` from selected MCPs, update Maika, remove workspace MCP entry, optionally uninstall the uv tool, and preserve/delete `.serena` only by explicit user choice.

- [ ] **Step 4: Add a concise README matrix and link**

The README matrix must show `Codex | Claude Code | Antigravity` as supported, `read-only symbols/references/diagnostics` as Phase 1, and link to `docs/providers/serena.md`. It must not duplicate the full guide.

- [ ] **Step 5: Run documentation and snapshot tests**

Run: `python3 -m pytest cli/tests/test_serena_documentation.py cli/tests/test_snapshots.py -q`

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add README.md docs/providers/serena.md cli/tests/test_serena_documentation.py
git commit -m "docs: add complete Serena setup guide"
```

### Task 9: Phase 1 acceptance and Phase 2 stop gate

**Files:**
- Modify: `docs/providers/serena.md` only if observed commands differ from the guide.

**Interfaces:**
- Consumes: all prior task outputs.
- Produces: a verified Phase 1 branch and an explicit decision that Phase 2 remains closed.

- [ ] **Step 1: Verify the forbidden surface mechanically**

Run:

```bash
rg -n "replace_symbol_body|insert_after_symbol|insert_before_symbol|rename_symbol|safe_delete_symbol|write_memory|onboarding|execute_shell_command" \
  .maika/config/serena-context.yml .maika/profiles/provider-capabilities.yaml cli/platforms
```

Expected: no match in the Serena context, Serena provider capability tools, or Serena platform mapping entries. Matches belonging to unrelated providers/native platform tools must be inspected and documented rather than deleted.

- [ ] **Step 2: Run focused Serena integration tests**

Run:

```bash
python3 -m pytest \
  cli/tests/test_provider_adapters.py \
  cli/tests/test_provider_contract_fixtures.py \
  cli/tests/test_provider_capabilities.py \
  cli/tests/test_structured_trace_skills.py \
  cli/tests/test_platforms.py \
  cli/tests/test_ua_setup.py \
  cli/tests/test_mcp_doctor.py \
  cli/tests/test_serena_documentation.py -q
```

Expected: PASS.

- [ ] **Step 3: Scaffold and inspect all three hosts**

For each host, initialize a fresh temporary project with UA, CBM, Serena, and AgentMemory selected, then assert the generated `MCP_SETUP.md` includes every provider and the correct native Serena format:

```bash
maika init --target /tmp/maika-serena-codex --platform codex --mcp understand-anything --mcp codebase-memory-mcp --mcp serena --mcp agent-memory --language python --yes --ua-mcp-dir /srv/ua
maika init --target /tmp/maika-serena-claude --platform claude-code --mcp understand-anything --mcp codebase-memory-mcp --mcp serena --mcp agent-memory --language python --yes --ua-mcp-dir /srv/ua
maika init --target /tmp/maika-serena-antigravity --platform antigravity --mcp understand-anything --mcp codebase-memory-mcp --mcp serena --mcp agent-memory --language python --yes --ua-mcp-dir /srv/ua
```

Expected: all three commands commit safely; Serena context exists under `.maika/config`; Codex guide uses TOML; Claude Code and Antigravity guides use JSON; no Serena write tool is present.

- [ ] **Step 4: Run full repository verification**

Run: `python3 scripts/run_ci.py`

Expected: exit code 0 with all tests, validators, generated-content checks, and snapshots passing.

- [ ] **Step 5: Inspect repository state**

Run: `git status --short && git log --oneline -10`

Expected: no untracked or unstaged files; one focused commit per task.

- [ ] **Step 6: Keep Phase 2 closed**

Confirm all five Serena write tools remain absent from the context, canonical capability registry, provider capability mapping, and platform mappings. Do not create the Phase 2 implementation plan until runtime payload evidence exists for Serena write calls on Codex, Claude Code, and Antigravity and shows that the existing Maika write gate can intercept or safely deny each call.

---

## Deferred Follow-up: Dogfood the Complete Provider Stack on Maika

After this Phase 1 integration is merged and verified, create a separate brainstorming/spec/plan cycle for developing Maika itself with UA-MCP, Serena, Codebase Memory, AgentMemory, and Maika durable knowledge. That follow-up must define session-start recall, query planning, provider selection, verified evidence capture, end-of-session learning candidates, verified-only durable promotion, stale-knowledge handling, and measurable improvement across sessions. It is independent from installing Serena and must not be folded into this Phase 1 branch.
