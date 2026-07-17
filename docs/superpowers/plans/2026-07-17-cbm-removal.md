# CBM Removal Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Remove the `codebase-memory-mcp` (CBM) provider from Maika entirely, reroute its capabilities to UA-MCP and Serena, and add a doctor contamination check that detects CBM-installer artifacts in host configuration.

**Architecture:** Per `docs/superpowers/specs/2026-07-17-cbm-removal-design.md`. Base is `master-v2` after the Serena Phase 1 merge (`777ecd6`). The removal proceeds inside-out: first the additive doctor check (independent), then config/doctrine, then runtime code, gates, workflows, lifecycle surfaces, docs, and finally a repo-wide guard test that locks the removal in. Every task leaves the suite green and commits.

**Tech Stack:** Python 3.12 (`/usr/bin/python3 -m pytest` — never the venv python, it has no pytest), YAML configs, Jinja-rendered skills.

**Verified inventory (2026-07-17, post-merge tree):** the reference sites listed per task below come from `grep -rn "codebase[-_]memory\|\bCBM\b"` over the live tree. Re-run the grep at execution time if the base has moved; line numbers are anchors, not gospel.

**Global conventions for every task:**

- Test command: `/usr/bin/python3 -m pytest <paths> -q` from the repo root.
- Gate-check tests: `/usr/bin/python3 -m pytest .maika/tools/gate-check/tests .maika/tools/microloop-orchestrator/tests -q`.
- The title-case strings `"Codebase Memory"` inside `gates.py:1471` (kernel forbidden-content list) and `cli/tests/test_agent_kernel.py:38` are **kept deliberately** — they forbid the kernel from mentioning the provider. Do not remove them.
- Do not touch `.worktrees/`, `build/`, `docs/refactor/`, `docs/plans/`, `upgrade/` — archived or generated content.

---

### Task 1: Branch setup

**Files:** none (git only)

- [ ] **Step 1: Create the feature branch from the merged base**

```bash
cd /home/zane/Desktop/agent-memory-arch-v3
git checkout master-v2 && git pull --rebase origin master-v2
git checkout -b feature/remove-cbm
```

- [ ] **Step 2: Verify green baseline**

Run: `/usr/bin/python3 -m pytest cli/tests .maika/tools/gate-check/tests .maika/tools/microloop-orchestrator/tests -q`
Expected: all pass (record the count; every task must end at ≥ this count minus deliberately deleted tests).

---

### Task 2: Doctor contamination check (additive, TDD)

**Files:**
- Modify: `cli/mcp/doctor.py` (model on `_memory_governance_state`, `doctor.py:303-328`)
- Test: `cli/tests/test_mcp_doctor.py`

- [ ] **Step 1: Write the failing tests** (append to `cli/tests/test_mcp_doctor.py`; reuse the file's existing `write_resolved` helper, passing explicit `mcps=["db-access"]` so this task is independent of later default changes)

```python
def test_doctor_flags_cbm_contamination(tmp_path):
    target = tmp_path / "proj"
    home = tmp_path / "home"
    write_resolved(target, mcps=["db-access"])
    hooks = home / ".claude" / "hooks"
    hooks.mkdir(parents=True)
    (hooks / "cbm-gate.sh").write_text(
        "# Installed by codebase-memory-mcp\n", encoding="utf-8")
    status = build_doctor_status(target, home)
    assert status.cbm_contamination == "contaminated"
    assert status.health_state == "degraded"
    text = render_report(status)
    assert "cbm contamination: CONTAMINATED" in text
    assert "codebase-memory-mcp uninstall" in text


def test_doctor_flags_cbm_in_global_settings(tmp_path):
    target = tmp_path / "proj"
    home = tmp_path / "home"
    write_resolved(target, mcps=["db-access"])
    settings = home / ".claude" / "settings.json"
    settings.parent.mkdir(parents=True)
    settings.write_text(json.dumps({"hooks": {"PreToolUse": [
        {"matcher": "Grep|Glob",
         "hooks": [{"command": "codebase-memory-mcp hook run"}]}]}}),
        encoding="utf-8")
    status = build_doctor_status(target, home)
    assert status.cbm_contamination == "contaminated"
    assert any("settings.json" in item for item in status.contamination_findings)


def test_doctor_flags_cbm_in_project_config(tmp_path):
    target = tmp_path / "proj"
    home = tmp_path / "home"
    write_resolved(target, mcps=["db-access"])
    mcp_json = target / ".mcp.json"
    mcp_json.write_text(json.dumps(
        {"mcpServers": {"codebase-memory-mcp": {"command": "codebase-memory-mcp"}}}),
        encoding="utf-8")
    status = build_doctor_status(target, home)
    assert status.cbm_contamination == "contaminated"


def test_doctor_contamination_clean(tmp_path):
    target = tmp_path / "proj"
    home = tmp_path / "home"
    write_resolved(target, mcps=["db-access"])
    status = build_doctor_status(target, home)
    assert status.cbm_contamination == "clean"
    assert status.contamination_findings == []
    assert "cbm contamination: CLEAN" in render_report(status)


def test_doctor_contamination_never_mutates(tmp_path):
    target = tmp_path / "proj"
    home = tmp_path / "home"
    write_resolved(target, mcps=["db-access"])
    hook = home / ".claude" / "hooks" / "cbm-gate.sh"
    hook.parent.mkdir(parents=True)
    payload = "# Installed by codebase-memory-mcp\n"
    hook.write_text(payload, encoding="utf-8")
    build_doctor_status(target, home)
    assert hook.read_text(encoding="utf-8") == payload
```

- [ ] **Step 2: Run to verify failure**

Run: `/usr/bin/python3 -m pytest cli/tests/test_mcp_doctor.py -q -k contamination`
Expected: FAIL — `AttributeError: ... no attribute 'cbm_contamination'`

- [ ] **Step 3: Implement in `cli/mcp/doctor.py`**

Add two fields to `DoctorStatus` (after `governance_warnings`):

```python
    cbm_contamination: str = "clean"   # clean | contaminated
    contamination_findings: list[str] = field(default_factory=list)
```

Add the detector next to `_memory_governance_state` (detection only — doctor never edits host-owned files, same provider boundary as the agent-memory governance check):

```python
CBM_MARKER = "codebase-memory"
CBM_REMEDIATION = (
    "run `codebase-memory-mcp uninstall`, remove ~/.local/bin/codebase-memory-mcp, "
    "then re-run `maika doctor mcp`"
)
_CBM_SCAN_MAX_BYTES = 262144


def _file_mentions_cbm(path: Path) -> bool:
    try:
        if path.stat().st_size > _CBM_SCAN_MAX_BYTES:
            return False
        return CBM_MARKER in path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return False


def _cbm_contamination_state(home: Path, target: Path) -> tuple[str, list[str]]:
    """Detect codebase-memory-mcp installer artifacts in host configuration.

    The upstream installer writes global PreToolUse/SessionStart hooks and
    skills that override Maika provider doctrine in every project."""
    findings: list[str] = []
    global_settings = home / ".claude" / "settings.json"
    if global_settings.is_file() and _file_mentions_cbm(global_settings):
        findings.append(f"global agent settings reference codebase-memory: {global_settings}")
    for directory in (home / ".claude" / "hooks", home / ".claude" / "skills"):
        if not directory.is_dir():
            continue
        findings.extend(
            f"installer artifact references codebase-memory: {path}"
            for path in sorted(directory.rglob("*"))
            if path.is_file() and _file_mentions_cbm(path)
        )
    for path in (target / ".claude" / "settings.json", target / ".mcp.json"):
        if path.is_file() and _file_mentions_cbm(path):
            findings.append(f"project config references codebase-memory: {path}")
    return ("contaminated" if findings else "clean"), findings
```

In `build_doctor_status`, call it after `_memory_governance_state` and thread the result through; contamination forces overall degradation:

```python
    cbm_contamination, contamination_findings = _cbm_contamination_state(home, target)
    if cbm_contamination == "contaminated":
        health_state = "degraded"
```

and add `cbm_contamination=cbm_contamination, contamination_findings=contamination_findings,` to the returned `DoctorStatus`.

Add the render helper and call it from `render_report` right after `_render_governance(status)`:

```python
def _render_cbm_contamination(status: DoctorStatus) -> str:
    if status.cbm_contamination == "clean":
        return "- cbm contamination: CLEAN\n"
    out = ["- cbm contamination: CONTAMINATED\n"]
    out.extend(f"  - WARNING: {finding}\n" for finding in status.contamination_findings)
    out.append(f"  - remediation: {CBM_REMEDIATION}\n")
    return "".join(out)
```

- [ ] **Step 4: Run the doctor suite**

Run: `/usr/bin/python3 -m pytest cli/tests/test_mcp_doctor.py -q`
Expected: PASS (contamination tests plus all pre-existing tests; the CLEAN line may require adjusting any doctor test that snapshots the full report body — update those assertions to include the new line, never delete them).

- [ ] **Step 5: Commit**

```bash
git add cli/mcp/doctor.py cli/tests/test_mcp_doctor.py
git commit -m "feat(doctor): detect codebase-memory-mcp global/project config contamination"
```

---

### Task 3: Provider registry, capability registry, capability mapping, validator

**Files:**
- Modify: `.maika/config/provider-registry.yaml:8-11,59-103`
- Modify: `.maika/profiles/capability-registry.yaml:3-9,36-43,50-66,77-83`
- Modify: `.maika/profiles/provider-capabilities.yaml` (UA block `semantic_code_search` supporting lines ~24-26; CBM block ~28-44)
- Modify: `cli/agent_content/provider_capabilities.py:22-27,66-73,137-147,235-238`
- Test: `cli/tests/test_provider_capabilities.py:147,150,167-175,262-277`

- [ ] **Step 1: Update tests first.** In `cli/tests/test_provider_capabilities.py`:
  - Delete the assertions/mutations that pin CBM (`lines 147, 167-175, 262-263, 274`: cbm primary role, "unknown CBM tools", cbm tool contract, `semantic_index_structure.preferred == "codebase-memory-mcp"`).
  - Replace line 150's `compatibility_aggregate` assert with the new shape:

```python
    registry = load_capability_registry(FRAMEWORK)
    dependency = registry["capabilities"]["dependency_analysis"]
    assert dependency["primary_provider"] == "understand-anything"
    assert "codebase-memory-mcp" not in str(registry)
```

  - Keep the negative-mutation test at line 277 (`structured_graph_trace.preferred` flipped must fail) but flip it to a provider that still exists, e.g. `"serena"`.
  - Add one new mutation test:

```python
def test_registry_rejects_codebase_memory_provider():
    doc = copy.deepcopy(load_provider_registry(FRAMEWORK))
    doc["providers"]["codebase-memory-mcp"] = {
        "display_name": "Codebase Memory MCP", "kind": "semantic_code_index",
        "setup_ref": "codebase-memory-mcp",
        "capabilities": {"primary": ["semantic_code_search"]},
    }
    registry = load_capability_registry(FRAMEWORK)
    errors = validate_canonical_provider_registry(doc, registry)
    assert any("unknown capability" in error for error in errors)
```

(match the file's existing import/loader helper names — read the top of the file before editing).

- [ ] **Step 2: Run to verify the new/changed tests fail**

Run: `/usr/bin/python3 -m pytest cli/tests/test_provider_capabilities.py -q`
Expected: FAIL (registry still contains CBM).

- [ ] **Step 3: Edit `.maika/config/provider-registry.yaml`**
  - Line 8: `corroborating: [codebase-memory-mcp, current-source]` → `corroborating: [current-source]`.
  - Delete the whole `semantic_index_structure:` authority lane (lines 10-13).
  - Delete the whole `codebase-memory-mcp:` provider block (lines 59-103, through `supporting: [architecture_discovery, call_chain_trace, impact_analysis]`).
  - In the `understand-anything` provider block, extend the primary capability list with `dependency_analysis`:

```yaml
    capabilities:
      primary: [architecture_discovery, domain_flow_trace, call_chain_trace, impact_analysis, graph_path_trace, inheritance_trace, dependency_analysis]
```

- [ ] **Step 4: Edit `.maika/profiles/capability-registry.yaml`**
  - `architecture_discovery`: `tools: [get_tour, get_layer_info, find_entry_points, query_nodes]`; `supporting_providers: [current-source]` (drop cbm).
  - `dependency_analysis`: rewrite the entry to:

```yaml
  dependency_analysis:
    description: Truy vết dependency path và phạm vi ảnh hưởng (blast radius).
    tools: [find_impact, find_path]
    freshness: [code_graph]
    preferred_evidence: [symbol_node, dependency_path, call_path, blast_radius, code_graph_edge]
    primary_provider: understand-anything
    supporting_providers: [current-source]
```

  - `call_chain_trace` and `impact_analysis`: `supporting_providers: [codebase-memory-mcp, current-source]` → `[current-source]`.
  - Delete the entire `semantic_code_search:` capability entry (lines ~77-83). Fuzzy anchor discovery is doctrine-routed to UA `query_nodes` (already a tool of `call_chain_trace` and now `architecture_discovery`), not a standalone capability.

- [ ] **Step 5: Edit `.maika/profiles/provider-capabilities.yaml`**
  - In the `understand-anything` block: delete the `semantic_code_search: role: supporting` sub-entry; add a primary `dependency_analysis` entry mirroring the registry:

```yaml
      dependency_analysis:
        role: primary
        tools: [find_impact, find_path]
```

  - Delete the entire `codebase-memory-mcp:` block.

- [ ] **Step 6: Edit `cli/agent_content/provider_capabilities.py`**
  - Delete the `CBM_TOOLS` set (lines 22-27).
  - In `expected_authority` (line ~66): delete the `"semantic_index_structure"` lane entry.
  - Delete the `if provider_id == "codebase-memory-mcp":` validation branch (lines ~137-147) and the `elif provider == "codebase-memory-mcp":` branch (lines ~235-238).

- [ ] **Step 7: Run and fix**

Run: `/usr/bin/python3 -m pytest cli/tests/test_provider_capabilities.py cli/tests/test_capability_runtime.py -q`
Expected: `test_provider_capabilities` PASS. `test_capability_runtime` may fail on line 44/149 (`["codebase-memory-mcp"]` render context, `"dependency_analysis" in plan["capabilities"]`); change the selection list to `["understand-anything"]` and keep the `dependency_analysis` assertion (it must still pass via UA).

- [ ] **Step 8: Commit**

```bash
git add .maika/config/provider-registry.yaml .maika/profiles/ cli/agent_content/provider_capabilities.py cli/tests/test_provider_capabilities.py cli/tests/test_capability_runtime.py
git commit -m "refactor(providers): retire semantic_code_search, reroute dependency_analysis to UA, drop CBM from registries"
```

---

### Task 4: Skill contracts and rules doctrine

**Files:**
- Modify (frontmatter/capability blocks): `.maika/skills/{grounding-explorer,reviewing-change,convention-intelligence-builder,writing-plan,lightweight-change,grounded-brainstorming,reviewing-task,database-explorer,writing-spec,infra-tdd,validating-plan,architecture-reconciler}/SKILL.md`, `.maika/skills/skill-index.yaml`
- Modify: `.maika/rules/jit/providers.md:35`, `.maika/rules/core/evidence.md:16`, `.maika/rules/jit/knowledge-lifecycle.md`, `.maika/procedures/context-loader.md` (CBM-abbreviation mentions)
- Modify: `.maika/skills/grounding-explorer/SKILL.md:210-217` (TOOL_HEALTH example)
- Test: `cli/tests/test_structured_trace_skills.py`, `cli/tests/test_skill_contracts.py:83-95`

- [ ] **Step 1: Inventory the exact sites**

Run: `/usr/bin/grep -rn "semantic_code_search\|dependency_analysis\|\bCBM\b\|Codebase Memory" .maika/skills .maika/rules .maika/procedures`
Expected: the files listed above. Work from this output, not from memory.

- [ ] **Step 2: Edit skill capability contracts.** In every SKILL.md frontmatter/capability block found:
  - Delete `semantic_code_search` from `conditional:` blocks (including its `triggers:` list) — there is no replacement entry; fuzzy discovery is now UA `query_nodes` under the already-declared structured-trace capabilities.
  - Keep `dependency_analysis` entries (the capability survives, re-pointed to UA in Task 3).
  - Where prose describes CBM as the fuzzy/discovery provider, rewrite the sentence to route to UA `query_nodes` with host search as corroboration. Mirror the same edits in `skill-index.yaml` capability summaries.

- [ ] **Step 3: Rewrite the doctrine lines.**
  - `.maika/rules/jit/providers.md:35` — replace the row

```
| `semantic_code_search` | Codebase Memory (CBM, conditional) | fuzzy semantic anchor discovery, graph-gap recovery và reviewer counter-evidence |
```

with

```
| fuzzy anchor discovery | Understand-Anything `query_nodes` (primary), host search (corroborating) | dùng khi tên/anchor chưa rõ; Serena `find_symbol` khi đã biết tên; graph gap/stale → current source |
```

  - `.maika/rules/core/evidence.md:16` — the numbered provider list entry `2. **Codebase Memory (CBM)** — graph symbol/dependency, call path, phạm vi ảnh hưởng.` → replace with `2. **Serena** — symbol identity, references, implementations, diagnostics (LSP).` unless Serena already holds a numbered entry; in that case delete entry 2 and renumber.
  - `knowledge-lifecycle.md` / `context-loader.md`: delete or reroute their CBM sentences per the same doctrine (grep output from Step 1 shows the lines).
  - `grounding-explorer/SKILL.md:210-217` — replace the `codebase-memory-mcp: status: unavailable` TOOL_HEALTH example block with a `serena:` degradation example:

```yaml
  serena:
    status: unavailable
    degradation:
      probe_ran: true
      error: "language server failed to initialize"
      fallback_used: current_source
      missing_evidence: "symbol references"
      confidence_impact: "medium"
```

- [ ] **Step 4: Update the contract tests.**
  - `cli/tests/test_structured_trace_skills.py`: delete mutation #1 (line ~50, "CBM semantic search moved back to required") and every `semantic_code_search` assertion (lines 39, 57, 68, 80); keep the `dependency_analysis` assertions (57-58 pinned-exclusion, 162 required) as-is.
  - `cli/tests/test_skill_contracts.py:83-95`: the synthetic YAML uses `semantic_code_search` merely as an example ID for "required+conditional conflict" — replace both occurrences with `historical_context_retrieval` (still a real capability) so the generic validation stays covered.

- [ ] **Step 5: Run**

Run: `/usr/bin/python3 -m pytest cli/tests/test_structured_trace_skills.py cli/tests/test_skill_contracts.py cli/tests/test_scaffold.py -q`
Expected: first two PASS; if `test_scaffold` fails here it belongs to Task 8 — note it, don't fix yet.

- [ ] **Step 6: Commit**

```bash
git add .maika/skills .maika/rules .maika/procedures cli/tests/test_structured_trace_skills.py cli/tests/test_skill_contracts.py
git commit -m "refactor(skills): drop semantic_code_search conditional contracts, reroute fuzzy discovery doctrine to UA"
```

---

### Task 5: Runtime provider code removal

**Files:**
- Delete: `cli/mcp/integration/codebase_memory.py`, `cli/tests/fixtures/provider_contracts/codebase-memory/` (entire dir, including any `.json` fixtures beside the two provenance YAMLs)
- Modify: `cli/commands/provider.py:18,189-190,211-222`, `cli/provider_actions.py:71`, `cli/mcp/pilot_readiness.py:15-19,33,51,55`, `cli/platforms/claude_code.py:30-41`, `cli/platforms/antigravity.py:29-40`, `cli/tools/templatize.py:36-...,108,138`
- Test: `cli/tests/test_provider_adapters.py`, `cli/tests/test_provider_invocations.py:85`, `cli/tests/test_trace_evidence_flow.py`, `cli/tests/test_platforms.py:51,236-253`, `cli/tests/test_pilot_readiness.py`, `cli/tests/test_vnext_w2_reasoning_layer.py:62`

- [ ] **Step 1: Delete the adapter and fixtures**

```bash
git rm cli/mcp/integration/codebase_memory.py
git rm -r cli/tests/fixtures/provider_contracts/codebase-memory
```

- [ ] **Step 2: `cli/commands/provider.py`** — remove `codebase_memory` from the `cli.mcp.integration` import (line 18); delete the `elif provider_id == codebase_memory.PROVIDER_ID:` normalization branch (189-190) and the whole CBM support-call/`--trigger` warning block (211-222). The generic trigger/reason machinery in `cli/mcp/integration/evidence.py` stays — it is provider-neutral.

- [ ] **Step 3: `cli/provider_actions.py:71`** — `if item in {"codebase-memory-mcp", "understand-anything"}` → `if item == "understand-anything"`.

- [ ] **Step 4: `cli/mcp/pilot_readiness.py`** — delete the CBM lane check (lines 15-19: `cbm`, `exploration`, `forbidden_cbm` and the blocker append); shrink the provider loop (line 33) to `("understand-anything", "agent-memory", "db-access")`; update the two prose strings: line 51 `"UA/CBM read-only discovery"` → `"UA read-only discovery"`, line 55 drop `"CBM mutation/deletion"` from the list.

- [ ] **Step 5: Platform mappings** — delete the whole `# ── Code Exploration (codebase-memory-mcp) ──` block in both `cli/platforms/claude_code.py` (lines 30-41) and `cli/platforms/antigravity.py` (lines 29-40). No `.maika` template consumes those eleven abstract ops (verified by grep on 2026-07-17), so this is a declaration-without-consumer cleanup.

- [ ] **Step 6: `cli/tools/templatize.py`** — delete the `HARDCODED_CODEBASE_MEMORY` dict (line 36 through its closing brace) and its two registrations (lines 108 and 138).

- [ ] **Step 7: Update the tests.**
  - `test_provider_adapters.py`: remove `codebase_memory` from the import (line 6) and delete the four CBM test functions (lines ~40-75: tools-list validation, hash drift, unknown-tool support call, normalize).
  - `test_provider_invocations.py:85` and `test_trace_evidence_flow.py:34`: these build a synthetic provider-registry dict with a CBM entry to exercise generic invocation recording. Rename the synthetic provider to a fake (`"acme-index": {"display_name": "Acme Index", "kind": "semantic_code_index"}`) and update every `provider="codebase-memory-mcp"` call and `provider_observations[0]["provider_id"]` assertion in those files to `"acme-index"`. The behavior under test (trigger-bound conditional support calls) is provider-neutral and must keep passing.
  - `test_platforms.py`: line 51 → `["understand-anything"]`; delete `test_codebase_memory_resolves_in_render_context_claude` (236-244) and `..._antigravity` (247-253).
  - `test_pilot_readiness.py`: drop the CBM expectations (2 sites; grep the file).
  - `test_vnext_w2_reasoning_layer.py:62`: remove `codebase_memory` from the tool-name regex alternation (`|codebase_memory` → gone). Line 52's `"codebase" + "-explorer"` is an unrelated legacy skill-name string — leave it.

- [ ] **Step 8: Run**

Run: `/usr/bin/python3 -m pytest cli/tests/test_provider_adapters.py cli/tests/test_provider_invocations.py cli/tests/test_trace_evidence_flow.py cli/tests/test_platforms.py cli/tests/test_pilot_readiness.py cli/tests/test_vnext_w2_reasoning_layer.py -q`
Expected: PASS.

- [ ] **Step 9: Commit**

```bash
git add -A cli
git commit -m "refactor(cli): remove codebase-memory adapter, platform mappings, pilot lane checks"
```

---

### Task 6: Gate-check

**Files:**
- Modify: `.maika/tools/gate-check/gates.py:1176,1329-1345`
- Test: `.maika/tools/gate-check/tests/test_trace_gates.py`, `test_provider_invocation_gate.py:86-87`, `test_grounding_package_gates.py:78-109`, `test_gates.py:119`

- [ ] **Step 1: `gates.py`**
  - Line 1176: delete the entry `"codebase-memory-mcp": {"semantic_index_structure"},` from `expected_authorities` (keep the UA entry).
  - Lines ~1329-1345: delete the whole CBM index-boundary rule — from `cbm_observations = [obs for obs in observations ...` through the end of its `for key in keys:` comparison loop (the rule that demands two `index_status` snapshots around material CBM evidence). Nothing replaces it.

- [ ] **Step 2: `test_trace_gates.py`** (22 references)
  - Delete the CBM-specific tests: support-call-without-trigger mutations (~lines 222-250), the CBM authority-invalid test (~190-204), and the index-boundary tests (~339+, `cbm = [...]` observations with `index_status` pairs).
  - In the corroboration tests (~280-288) where `"providers": ["understand-anything", "codebase-memory-mcp"]`, replace `"codebase-memory-mcp"` with `"current-source"`.
  - Update the module docstring (line 4) to stop describing the removed mutations.

- [ ] **Step 3: Other gate tests**
  - `test_provider_invocation_gate.py:86-87` — the "deliberately unverified tool names" case uses CBM; repoint the fixture to a provider absent from the registry, e.g. `{"provider_id": "acme-index", "tool": "search_graph"}`, keeping the semantics (no snapshot in registry ⇒ unverified allowed/flagged exactly as today).
  - `test_grounding_package_gates.py:78-109` — TOOL_HEALTH fixtures use `codebase_memory={...}` provider entries; rename the fixture key/provider to `serena` (mirrors the Task 4 SKILL.md example).
  - `test_gates.py:119` — the string `"trace via cbm"` is an arbitrary reason payload; change to `"trace via provider"`.

- [ ] **Step 4: Run**

Run: `/usr/bin/python3 -m pytest .maika/tools/gate-check/tests -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add .maika/tools/gate-check
git commit -m "refactor(gates): drop CBM authority lane and index-boundary rule"
```

---

### Task 7: External workflows and dispatch

**Files:**
- Modify: `.maika/config/external-workflows.yaml:56-70`, `.maika/procedures/dispatch-kernel.md:44`, `.maika/tools/microloop-orchestrator/vnext_dispatch.py:29`
- Test: `cli/tests/test_external_workflows.py:21`, `.maika/tools/microloop-orchestrator/tests/test_external_workflow_safety.py`, `cli/tests/test_system_model.py:57`

- [ ] **Step 1:** Delete the `codebase-memory-index:` and `codebase-memory-query:` workflow entries from `external-workflows.yaml` (lines 56-70).
- [ ] **Step 2:** Remove `codebase-memory-index` from the `request_only` lists in `dispatch-kernel.md:44` and `vnext_dispatch.py:29` (both become `[understand, understand-domain]`).
- [ ] **Step 3:** `test_external_workflows.py:21` mutates `codebase-memory-query` to prove read-only enforcement — repoint the mutation to the `understand` workflow (or whichever remaining `read_only` workflow the file's fixture loads; check the file). `test_external_workflow_safety.py`: same treatment for its single reference. `test_system_model.py:57` asserts `"owner: codebase-memory-mcp"` appears in the rendered system model — delete that assertion (and its sibling lines for the removed workflows, if any).
- [ ] **Step 4: Run**

Run: `/usr/bin/python3 -m pytest cli/tests/test_external_workflows.py cli/tests/test_system_model.py .maika/tools/microloop-orchestrator/tests -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add .maika/config/external-workflows.yaml .maika/procedures/dispatch-kernel.md .maika/tools/microloop-orchestrator cli/tests/test_external_workflows.py cli/tests/test_system_model.py
git commit -m "refactor(workflows): remove codebase-memory index/query workflows"
```

---

### Task 8: Manifest, scaffold, init/update lifecycle

**Files:**
- Modify: `cli/plugin-manifest.yaml:17-28` (delete the `codebase-memory-mcp:` mcp_capabilities block)
- Modify: `cli/commands/update.py` (stale-selection prune; find the exact site by grepping `mcps` in it)
- Test: `cli/tests/test_manifest_setup.py`, `cli/tests/test_init.py`, `cli/tests/test_update.py`, `cli/tests/test_scaffold.py`, `cli/tests/test_snapshots.py`, `cli/tests/test_platform_command.py`

- [ ] **Step 1: Write the stale-selection test first** (append to `cli/tests/test_update.py`, mirroring its existing update-invocation helper):

```python
def test_update_prunes_unknown_mcp_selection(tmp_path, capsys):
    # A project scaffolded before CBM removal still lists it in resolved-config.
    # update must drop unknown selections with a warning instead of crashing
    # or re-rendering setup docs for a provider the manifest no longer knows.
    target = scaffold_project(tmp_path, mcps=["understand-anything", "codebase-memory-mcp"])
    run_update(target)
    resolved = load_resolved_config(target)
    assert "codebase-memory-mcp" not in resolved["mcps"]
    assert "understand-anything" in resolved["mcps"]
    assert "unknown mcp" in capsys.readouterr().out.lower()
```

(Adapt helper names to the file's actual fixtures — read `test_update.py:1-40` first; the existing tests there scaffold via `mcps=("codebase-memory-mcp", ...)` keyword.)

- [ ] **Step 2: Run to verify failure**

Run: `/usr/bin/python3 -m pytest cli/tests/test_update.py -q -k prunes`
Expected: FAIL (update either keeps the selection or crashes on the missing manifest key).

- [ ] **Step 3: Delete the manifest block** `mcp_capabilities.codebase-memory-mcp` (`cli/plugin-manifest.yaml:17-28`, through `args: []`).

- [ ] **Step 4: Implement the prune** in the update path (`cli/commands/update.py`): where the resolved config's `mcps` are re-read for re-rendering, filter against `manifest["mcp_capabilities"]` keys, print `warning: unknown mcp selection dropped: <name>` for each removal, and persist the filtered list back to resolved-config. Keep it to a few lines at the existing read site — no new module.

- [ ] **Step 5: Sweep the lifecycle tests.** These use CBM as an arbitrary selected provider; substitute without losing coverage:
  - `test_init.py`: default fixture `mcps=("codebase-memory-mcp", "confluence", "db-access")` (line 23) → `("understand-anything", "confluence", "db-access")` — note this makes `resolve_ua_mcp_dir` prompts active in defaults; if that breaks unrelated tests, use `("db-access", "confluence")` instead and keep one explicit UA test. `parse_multi_values` cases (118-119), `selected_mcps` cases (131-137, 433-488), line 536 `resolve_ua_mcp_dir(["codebase-memory-mcp"], ...)` → `(["db-access"], ...)`. The three-provider MCP_SETUP tests (600-628) → `["understand-anything", "serena"]` and drop the cbm loop element.
  - `test_update.py:10,150`: same substitutions (`db-access` / drop cbm from the three-provider list).
  - `test_scaffold.py:194`: `has_capability(["codebase-memory-mcp"], caps, "code_exploration")` → `has_capability(["understand-anything"], caps, "code_exploration")` (UA also provides `code_exploration`); lines 408, 424, 680, 696: swap the selection to `["db-access"]` and update the rendered-yaml expectation at 424 (`mcps: [db-access]`).
  - `test_snapshots.py:12,16,20`: `["codebase-memory-mcp", "confluence", "db-access"]` → `["confluence", "db-access"]`.
  - `test_platform_command.py:151,227`: `["understand-anything", "codebase-memory-mcp", "serena"]` → `["understand-anything", "serena"]`.
  - `test_manifest_setup.py`: this file pins the CBM setup block itself (lines 41-72). Rewrite its fixture accessor to `manifest["mcp_capabilities"]["understand-anything"]["setup"]` and re-target the assertions at the UA setup contract (engine check path, server command `understand-anything`-style fields — read the UA manifest block first); delete asserts that only make sense for CBM (`install_hint --skip-config`, binary path ending `/codebase-memory-mcp`). Add one guard assert:

```python
def test_manifest_has_no_codebase_memory_capability():
    manifest = load_manifest(FRAMEWORK)
    assert "codebase-memory-mcp" not in manifest["mcp_capabilities"]
```

- [ ] **Step 6: Run the lifecycle suite**

Run: `/usr/bin/python3 -m pytest cli/tests/test_init.py cli/tests/test_update.py cli/tests/test_scaffold.py cli/tests/test_snapshots.py cli/tests/test_platform_command.py cli/tests/test_manifest_setup.py -q`
Expected: PASS, including the Step 1 prune test.

- [ ] **Step 7: Commit**

```bash
git add cli/plugin-manifest.yaml cli/commands/update.py cli/tests/
git commit -m "refactor(lifecycle): drop CBM from manifest, prune stale selections on update"
```

---

### Task 9: Remaining test-surface cleanups

**Files:**
- Test: `cli/tests/test_mcp_doctor.py`, `cli/tests/test_mcp_config.py`, `cli/tests/test_ua_setup.py`, `cli/tests/test_end_to_end_learning_loop.py:45,63`, `cli/tests/test_assumption_policy.py:69`

- [ ] **Step 1: `test_mcp_doctor.py`** — the file's `write_resolved` default is `mcps or ["codebase-memory-mcp"]` (line 24) and ~12 call sites configure a `codebase-memory-mcp` server entry. Change the default to `["db-access"]` and mechanically substitute every `"codebase-memory-mcp"` server/selection/assertion string with `"db-access"` (lines 495-589, 714 comment). The doctor logic under test (config matching, redaction, antigravity fix copy) is provider-agnostic.
- [ ] **Step 2: `test_mcp_config.py`** — same substitution for the JSON/TOML server-name fixtures (lines 11-67): `codebase-memory-mcp` → `db-access`.
- [ ] **Step 3: `test_ua_setup.py`** — the render-snippet fixtures use `codebase-memory-mcp` as an arbitrary `server_key`/command (lines 116-120, 262-265): rename to `example-mcp`. Keep the "Index the codebase" section-rendering assertions (268, 284) — they test the generic `index_hint` mechanism, and the inline fixture dict supplies its own hint text.
- [ ] **Step 4: Cosmetic strings** — `test_end_to_end_learning_loop.py`: `"CBM-1"` evidence id → `"SER-1"` (both sites, dict and YAML). `test_assumption_policy.py:69`: `failed_probe="cbm probe timeout"` → `"serena probe timeout"`.
- [ ] **Step 5: Run the full CLI suite**

Run: `/usr/bin/python3 -m pytest cli/tests -q`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add cli/tests
git commit -m "test: sweep incidental codebase-memory fixtures to surviving providers"
```

---

### Task 10: Documentation

**Files:**
- Modify: `README.md:63,353-354,397,600` (+ the Serena responsibility-matrix section — grep `Codebase Memory` in the file)
- Modify: `docs/superpowers/specs/2026-07-16-serena-semantic-provider-integration-design.md`, `docs/superpowers/plans/2026-07-16-serena-semantic-provider-phase1.md`
- Test: `cli/tests/test_serena_documentation.py:26`

- [ ] **Step 1: README**
  - Line 63: `3. Hỏi MCP servers: Codebase Memory, Confluence, DB Remote nếu bạn có.` → `3. Hỏi MCP servers: Understand Anything, Serena, Confluence, DB Remote nếu bạn có.`
  - Provider table (353-354): delete the Codebase Memory row; rewrite the UA row's second cell to drop `; Codebase Memory hỗ trợ sau — extract logic tại node UA đã định vị` and end at `(UA-first)` rationale.
  - Line 397 (`CBM material evidence cần hai call index_status...`): delete the sentence (the gate is gone).
  - Line 600 status example: `MCPs: codebase-memory-mcp, db-access` → `MCPs: understand-anything, serena, db-access`.
  - Serena section responsibility matrix: replace CBM rows with the Task 4 doctrine (UA `query_nodes` fuzzy discovery / current-source counter-evidence).
  - Add an uninstall subsection under the MCP docs:

```markdown
### Gỡ codebase-memory-mcp (provider đã bị loại bỏ)

Installer của codebase-memory-mcp ghi hook/skill vào cấu hình global (`~/.claude/`),
ghi đè provider doctrine của mọi project. Maika không còn hỗ trợ provider này.

1. `codebase-memory-mcp uninstall`
2. `rm ~/.local/bin/codebase-memory-mcp`
3. `maika doctor mcp` — mục `cbm contamination` phải báo CLEAN.
```

- [ ] **Step 2: `test_serena_documentation.py:26`** — the required-terms list includes `"CBM"`; replace with `"query_nodes"` so the doc test now pins the new routing instead. Run it against the updated README section.
- [ ] **Step 3: Amend the Serena docs** — at the top of both the 2026-07-16 design and phase-1 plan, insert:

```markdown
> **Amended 2026-07-17:** Codebase Memory MCP has been removed from the provider
> ecosystem (see `2026-07-17-cbm-removal-design.md`). CBM rows in the
> responsibility matrix and routing doctrine below are superseded: fuzzy semantic
> anchor discovery routes to UA `query_nodes` (host search corroborating), and
> conditional graph-gap/counter-evidence work routes to current source.
```

Then update design §5.2 matrix rows, §9.1 step 4, and §18's provider stack listing in place (delete/replace CBM lines); in the phase-1 plan update the doctrine lines found by `grep -n -i "cbm\|codebase" <file>` the same way. Do not restructure either document.

- [ ] **Step 4: Run**

Run: `/usr/bin/python3 -m pytest cli/tests/test_serena_documentation.py -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add README.md docs/superpowers cli/tests/test_serena_documentation.py
git commit -m "docs: reroute provider docs off CBM, add uninstall guidance, amend Serena doctrine"
```

---

### Task 11: Repo-wide guard test and full verification

**Files:**
- Create: `cli/tests/test_no_cbm_references.py`

- [ ] **Step 1: Write the guard test**

```python
"""Locks the CBM removal: no live source may reference codebase-memory again.

Docs archives, the removal/uninstall documentation, and the doctor
contamination detector (which must name the marker to detect it) are the
only allowed mentions."""

import re
import subprocess
from pathlib import Path

ALLOWED_PREFIXES = (
    "docs/",
    "upgrade/",
    "README.md",
    "cli/mcp/doctor.py",
    "cli/tests/test_mcp_doctor.py",
    "cli/tests/test_no_cbm_references.py",
)
PATTERN = re.compile(r"codebase[-_]memory")


def test_no_codebase_memory_references():
    root = Path(__file__).resolve().parents[2]
    files = subprocess.run(
        ["git", "ls-files"], cwd=root, capture_output=True, text=True, check=True,
    ).stdout.splitlines()
    offenders = []
    for rel in files:
        if rel.startswith(ALLOWED_PREFIXES):
            continue
        try:
            text = (root / rel).read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        if PATTERN.search(text):
            offenders.append(rel)
    assert not offenders, f"codebase-memory references remain: {offenders}"
```

- [ ] **Step 2: Run the guard**

Run: `/usr/bin/python3 -m pytest cli/tests/test_no_cbm_references.py -q`
Expected: PASS. If it fails, each offender is a missed site — fix it in the task it belongs to (config → Task 3, code → Task 5, tests → Task 9) and re-run.

- [ ] **Step 3: Full suite**

Run: `/usr/bin/python3 -m pytest cli/tests .maika/tools/gate-check/tests .maika/tools/microloop-orchestrator/tests -q`
Expected: all PASS; count ≥ Task 1 baseline minus the deliberately deleted CBM tests, plus the new contamination/prune/guard tests.

- [ ] **Step 4: Commit and push the branch**

```bash
git add cli/tests/test_no_cbm_references.py
git commit -m "test: guard against codebase-memory reference reintroduction"
git push -u origin feature/remove-cbm
```

- [ ] **Step 5: Open the PR** against `master-v2` summarizing: root cause (global-config-stomping installer), rerouting doctrine, doctor contamination check, stale-selection prune, guard test.

---

## Self-review checklist (done at plan time)

- Spec §4 doctrine → Tasks 3-4; §5 file scope → Tasks 3-9 (inventory cross-checked against the 2026-07-17 grep); §6 doctor → Task 2; §7 migration → Task 8 (prune + re-emit via manifest) and Task 10 (uninstall docs); §8 verification → per-task pytest steps + Task 11 guard; §9 non-goals respected (no auto-delete of user config, no replacement engine, agent-memory untouched).
- Known judgment calls the executor may exercise: `test_init` default-mcps substitution (db-access vs understand-anything, Step 5 note), `evidence.md` renumbering, `test_manifest_setup` re-target details. Everything else is mechanical.
