# Codebase Memory (cb-mem) Init Integration — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace SocratiCode with `codebase-memory-mcp` as the `code_exploration` MCP backend in Maika `init`, add a `semantic_search` abstract op, and wire it consistently through manifest, platform tool_mapping, setup-block (MCP_SETUP.md), doctor, skills, and tests.

**Architecture:** Maika is a scaffolder — it does NOT call MCPs. It (a) emits `MCP_SETUP.md` (a server snippet the user pastes into the agent's MCP config) and (b) renders abstract tool names (`{{ tools.* }}`) into skills/rules for the **agent runtime** to call. An MCP is represented at 4 touchpoints: manifest entry, per-platform `tool_mapping`, an optional `setup` block (rendered to MCP_SETUP.md by `cli/mcp/ua_setup.py`), and static `doctor` verification (server-key match + engine_check). cb-mem follows the existing **understand-anything (UA)** setup pattern, differing only in: uvx runtime (no clone dir), no JSON `graph_artifacts` (its graph is SQLite `.codebase-memory/graph.db.zst`), and an index step.

**Tech Stack:** Python 3.12, pytest, Jinja2 (cli/renderer), YAML manifest (`cli/plugin-manifest.yaml`).

**Spec:** `docs/superpowers/specs/2026-06-22-codebase-memory-vs-socraticode-decision.md`

**Consistency invariant:** manifest key = server name in agent MCP config = tool prefix segment. Pin **`codebase-memory-mcp`** everywhere. Claude Code prefix `mcp__codebase-memory-mcp__<tool>`; Antigravity prefix `mcp_codebase-memory-mcp_<tool>`.

**Test runner:** Use `/usr/bin/python3 -m pytest` (the venv python3 has no pytest). Prefix shell with `rtk` per project convention.

---

## File Structure

- **Modify** `cli/platforms/base.py` — add `semantic_search` to `REQUIRED_TOOL_KEYS`.
- **Modify** `cli/platforms/claude_code.py` — remap code-exploration block socraticode → cb-mem; add `semantic_search`.
- **Modify** `cli/platforms/antigravity.py` — same as above (single-underscore prefix).
- **Modify** `cli/platforms/generic.py` — add `semantic_search` passthrough.
- **Modify** `cli/platforms/codex.py` — add `semantic_search` passthrough.
- **Modify** `cli/plugin-manifest.yaml` — remove `socraticode`; add `codebase-memory-mcp` (with `setup`); fix UA display text.
- **Modify** `cli/mcp/ua_setup.py` — `render_mcp_setup_md`: when no `graph_artifacts`, render an "Index the codebase" step from `index_hint`.
- **Modify** `.maika/skills/author-dna-builder/references/code-evidence-scan.md` — migrate hardcoded `codebase_context_search` → `{{ tools.semantic_search }}` (consumer for the new op).
- **Modify** `.maika/skills/convention-intelligence-builder/references/structural-audit-scan.md` — same migration.
- **Modify** `.maika/**` (prose) — relabel display token `Socraticode` → `Codebase Memory`.
- **Modify** `cli/tests/test_platforms.py`, `cli/tests/test_manifest_setup.py`, `cli/tests/test_ua_setup.py` — new/updated tests.

---

## Task 1: Add `semantic_search` abstract op to the keyset

**Files:**
- Modify: `cli/platforms/base.py:19-25` (REQUIRED_TOOL_KEYS, code-exploration group)
- Test: `cli/tests/test_platforms.py`

- [ ] **Step 1: Write the failing test**

Add to `cli/tests/test_platforms.py` (after `test_dynamic_memory_ops_are_required_keys`):

```python
def test_semantic_search_is_required_key():
    from cli.platforms.base import REQUIRED_TOOL_KEYS
    assert "semantic_search" in REQUIRED_TOOL_KEYS
```

- [ ] **Step 2: Run test to verify it fails**

Run: `rtk /usr/bin/python3 -m pytest cli/tests/test_platforms.py::test_semantic_search_is_required_key -v`
Expected: FAIL (`assert 'semantic_search' in REQUIRED_TOOL_KEYS`).

- [ ] **Step 3: Add the key**

In `cli/platforms/base.py`, inside `REQUIRED_TOOL_KEYS`, add `"semantic_search",` immediately after `"search_code",`:

```python
    "search_code",
    "semantic_search",
    "index_code",
```

- [ ] **Step 4: Run test to verify it passes (and see which platforms now fail)**

Run: `rtk /usr/bin/python3 -m pytest cli/tests/test_platforms.py::test_semantic_search_is_required_key -v`
Expected: PASS.

Run: `rtk /usr/bin/python3 -m pytest cli/tests/test_platforms.py::test_all_platforms_define_required_tool_keyset -v`
Expected: FAIL for all 4 platforms (missing `semantic_search` mapping) — fixed in Tasks 2–5.

- [ ] **Step 5: Commit**

```bash
rtk git add cli/platforms/base.py cli/tests/test_platforms.py
rtk git commit -m "feat(cli): add semantic_search to required tool keyset"
```

---

## Task 2: Remap Claude Code platform to cb-mem + add semantic_search

**Files:**
- Modify: `cli/platforms/claude_code.py:28-38` (Code Exploration block)
- Test: `cli/tests/test_platforms.py`

- [ ] **Step 1: Write the failing test**

Add to `cli/tests/test_platforms.py`:

```python
def test_codebase_memory_resolves_in_render_context_claude():
    ctx = get_platform("claude-code").build_render_context(["codebase-memory-mcp"], "python")
    t = ctx["tools"]
    assert t["search_code"] == "mcp__codebase-memory-mcp__search_code"
    assert t["semantic_search"] == "mcp__codebase-memory-mcp__semantic_query"
    assert t["find_blast_radius"] == "mcp__codebase-memory-mcp__detect_changes"
    assert t["trace_flow"] == "mcp__codebase-memory-mcp__trace_path"
    assert t["get_symbol"] == "mcp__codebase-memory-mcp__get_code_snippet"
    assert t["graph_stats"] == "mcp__codebase-memory-mcp__get_graph_schema"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `rtk /usr/bin/python3 -m pytest cli/tests/test_platforms.py::test_codebase_memory_resolves_in_render_context_claude -v`
Expected: FAIL (`KeyError: 'semantic_search'` or socraticode value mismatch).

- [ ] **Step 3: Replace the Code Exploration block**

In `cli/platforms/claude_code.py`, replace lines 28–38 (the `# ── Code Exploration (Socraticode — if available) ──` block) with:

```python
        # ── Code Exploration (codebase-memory-mcp) ──
        "search_code":       "mcp__codebase-memory-mcp__search_code",
        "semantic_search":   "mcp__codebase-memory-mcp__semantic_query",
        "index_code":        "mcp__codebase-memory-mcp__index_repository",
        "code_status":       "mcp__codebase-memory-mcp__index_status",
        "get_dependencies":  "mcp__codebase-memory-mcp__query_graph",
        "trace_flow":        "mcp__codebase-memory-mcp__trace_path",
        "find_blast_radius": "mcp__codebase-memory-mcp__detect_changes",
        "get_symbol":        "mcp__codebase-memory-mcp__get_code_snippet",
        "list_symbols":      "mcp__codebase-memory-mcp__search_graph",
        "graph_stats":       "mcp__codebase-memory-mcp__get_graph_schema",
        "graph_build":       "mcp__codebase-memory-mcp__index_repository",
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `rtk /usr/bin/python3 -m pytest cli/tests/test_platforms.py::test_codebase_memory_resolves_in_render_context_claude -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
rtk git add cli/platforms/claude_code.py cli/tests/test_platforms.py
rtk git commit -m "feat(cli): remap claude-code code-exploration to codebase-memory-mcp"
```

---

## Task 3: Remap Antigravity platform to cb-mem + add semantic_search

**Files:**
- Modify: `cli/platforms/antigravity.py:28-38` (Code Exploration block)
- Test: `cli/tests/test_platforms.py`

- [ ] **Step 1: Write the failing test**

Add to `cli/tests/test_platforms.py`:

```python
def test_codebase_memory_resolves_in_render_context_antigravity():
    ctx = get_platform("antigravity").build_render_context(["codebase-memory-mcp"], "python")
    t = ctx["tools"]
    assert t["search_code"] == "mcp_codebase-memory-mcp_search_code"
    assert t["semantic_search"] == "mcp_codebase-memory-mcp_semantic_query"
    assert t["find_blast_radius"] == "mcp_codebase-memory-mcp_detect_changes"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `rtk /usr/bin/python3 -m pytest cli/tests/test_platforms.py::test_codebase_memory_resolves_in_render_context_antigravity -v`
Expected: FAIL.

- [ ] **Step 3: Replace the Code Exploration block**

In `cli/platforms/antigravity.py`, replace lines 28–38 (the `# ── Code Exploration (Socraticode) ──` block) with:

```python
        # ── Code Exploration (codebase-memory-mcp) ──
        "search_code":       "mcp_codebase-memory-mcp_search_code",
        "semantic_search":   "mcp_codebase-memory-mcp_semantic_query",
        "index_code":        "mcp_codebase-memory-mcp_index_repository",
        "code_status":       "mcp_codebase-memory-mcp_index_status",
        "get_dependencies":  "mcp_codebase-memory-mcp_query_graph",
        "trace_flow":        "mcp_codebase-memory-mcp_trace_path",
        "find_blast_radius": "mcp_codebase-memory-mcp_detect_changes",
        "get_symbol":        "mcp_codebase-memory-mcp_get_code_snippet",
        "list_symbols":      "mcp_codebase-memory-mcp_search_graph",
        "graph_stats":       "mcp_codebase-memory-mcp_get_graph_schema",
        "graph_build":       "mcp_codebase-memory-mcp_index_repository",
```

- [ ] **Step 4: Run test to verify it passes**

Run: `rtk /usr/bin/python3 -m pytest cli/tests/test_platforms.py::test_codebase_memory_resolves_in_render_context_antigravity -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
rtk git add cli/platforms/antigravity.py cli/tests/test_platforms.py
rtk git commit -m "feat(cli): remap antigravity code-exploration to codebase-memory-mcp"
```

---

## Task 4: Add `semantic_search` passthrough to generic + codex

**Files:**
- Modify: `cli/platforms/generic.py:26` (after `search_code`)
- Modify: `cli/platforms/codex.py:24` (after `search_code`)
- Test: `cli/tests/test_platforms.py` (the existing `test_all_platforms_define_required_tool_keyset`)

- [ ] **Step 1: Run the keyset test to confirm generic+codex still fail**

Run: `rtk /usr/bin/python3 -m pytest cli/tests/test_platforms.py::test_all_platforms_define_required_tool_keyset -v`
Expected: FAIL listing `generic` and `codex` missing `semantic_search`.

- [ ] **Step 2: Add passthrough in generic.py**

In `cli/platforms/generic.py`, add immediately after the `"search_code":       "search_code",` line:

```python
        "semantic_search":   "semantic_search",
```

- [ ] **Step 3: Add passthrough in codex.py**

In `cli/platforms/codex.py`, add immediately after the `"search_code":       "search_code",` line:

```python
        "semantic_search":   "semantic_search",
```

- [ ] **Step 4: Run the full platform test file to verify it passes**

Run: `rtk /usr/bin/python3 -m pytest cli/tests/test_platforms.py -v`
Expected: PASS (all platforms now define the required keyset including `semantic_search`).

- [ ] **Step 5: Commit**

```bash
rtk git add cli/platforms/generic.py cli/platforms/codex.py
rtk git commit -m "feat(cli): add semantic_search passthrough to generic and codex"
```

---

## Task 5: Manifest — remove socraticode, add codebase-memory-mcp with setup

**Files:**
- Modify: `cli/plugin-manifest.yaml:17-31` (mcp_capabilities)
- Test: `cli/tests/test_manifest_setup.py`

- [ ] **Step 1: Write the failing tests**

Add to `cli/tests/test_manifest_setup.py`:

```python
def _cbm_setup():
    manifest = load_manifest(MAIKA_ROOT)
    return manifest["mcp_capabilities"]["codebase-memory-mcp"]["setup"]


def test_socraticode_removed_from_manifest():
    manifest = load_manifest(MAIKA_ROOT)
    assert "socraticode" not in manifest["mcp_capabilities"]


def test_cbm_capability_present():
    manifest = load_manifest(MAIKA_ROOT)
    cap = manifest["mcp_capabilities"]["codebase-memory-mcp"]
    assert cap["provides"] == "code_exploration"


def test_cbm_setup_server_is_uvx_no_clone_dir():
    setup = _cbm_setup()
    assert setup["server"]["command"] == "uvx"
    assert setup["server"]["args"] == ["codebase-memory-mcp"]
    # uvx is zero-config: no clone-dir placeholder anywhere in the server recipe
    assert "{ua_mcp_dir}" not in str(setup["server"])


def test_cbm_setup_has_no_graph_artifacts_but_has_index_hint():
    setup = _cbm_setup()
    assert "graph_artifacts" not in setup
    assert setup["index_hint"]  # non-empty string


def test_cbm_setup_engine_check_and_install_hint():
    setup = _cbm_setup()
    assert setup["engine_check"]["default"]["kind"] == "path_exists"
    assert "{home}" in setup["engine_check"]["default"]["path"]
    assert "default" in setup["install_hint"]
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `rtk /usr/bin/python3 -m pytest cli/tests/test_manifest_setup.py -k "cbm or socraticode" -v`
Expected: FAIL (KeyError `codebase-memory-mcp` / socraticode still present).

- [ ] **Step 3: Edit the manifest**

In `cli/plugin-manifest.yaml`, delete the 3-line `socraticode:` block (lines 17–19):

```yaml
  socraticode:
    provides: code_exploration
    display: "Socraticode — Semantic code search + dependency graph"
```

Then add this block immediately under `mcp_capabilities:` (where socraticode was):

```yaml
  codebase-memory-mcp:
    provides: code_exploration
    display: "Codebase Memory — Knowledge graph + semantic search (uvx, zero-config)"
    setup:
      engine_check:
        default: { kind: path_exists, path: "{home}/.local/bin/uv" }
      install_hint:
        default: "Install uv (https://astral.sh/uv); the MCP runs via `uvx codebase-memory-mcp` — no separate install needed."
      index_hint: "Ask the agent: 'Index this project' (runs index_repository). To auto-index on connect: `codebase-memory-mcp config set auto_index true`."
      server:
        command: "uvx"
        args: ["codebase-memory-mcp"]
```

Also update the UA `display` line (currently `"Understand Anything — Knowledge Graph (alternative to Socraticode)"`) to:

```yaml
    display: "Understand Anything — Knowledge Graph (alternative to Codebase Memory)"
```

> Note: `engine_check` on `{home}/.local/bin/uv` is a best-effort prerequisite check (uv's default installer location). It is a non-blocking doctor hint; if uv is installed elsewhere (e.g. Homebrew) doctor shows the install hint but the MCP still works.

- [ ] **Step 4: Run tests to verify they pass**

Run: `rtk /usr/bin/python3 -m pytest cli/tests/test_manifest_setup.py -v`
Expected: PASS (new cb-mem tests + existing UA tests).

- [ ] **Step 5: Commit**

```bash
rtk git add cli/plugin-manifest.yaml cli/tests/test_manifest_setup.py
rtk git commit -m "feat(cli): replace socraticode with codebase-memory-mcp in manifest"
```

---

## Task 6: Render an "Index" step in MCP_SETUP.md when no graph_artifacts

**Files:**
- Modify: `cli/mcp/ua_setup.py:69-89` (`render_mcp_setup_md`)
- Test: `cli/tests/test_ua_setup.py`

- [ ] **Step 1: Write the failing test**

Add to `cli/tests/test_ua_setup.py`:

```python
def test_render_mcp_setup_md_index_step_when_no_graph_artifacts():
    setup = {
        "install_hint": {"default": "install uv"},
        "index_hint": "Ask the agent: 'Index this project'.",
        "server": {"command": "uvx", "args": ["codebase-memory-mcp"]},
    }
    md = ua_setup.render_mcp_setup_md(
        setup, server_key="codebase-memory-mcp", platform="claude-code",
        ua_mcp_dir="", project_root="/proj",
    )
    assert "## 2. Index the codebase" in md
    assert "Ask the agent: 'Index this project'." in md
    assert "Generate graphs" not in md


def test_render_mcp_setup_md_keeps_generate_graphs_when_artifacts_present():
    setup = {
        "install_hint": {"default": "install"},
        "graph_artifacts": [{"name": "code", "path": ".x/g.json", "gen_cmd": "/understand"}],
        "server": {"command": "uv", "args": ["run", "server.py"]},
    }
    md = ua_setup.render_mcp_setup_md(
        setup, server_key="understand-anything", platform="claude-code",
        ua_mcp_dir="/srv", project_root="/proj",
    )
    assert "## 2. Generate graphs" in md
    assert "Index the codebase" not in md
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `rtk /usr/bin/python3 -m pytest cli/tests/test_ua_setup.py -k "index_step or generate_graphs" -v`
Expected: FAIL (current code always emits "## 2. Generate graphs").

- [ ] **Step 3: Update `render_mcp_setup_md`**

In `cli/mcp/ua_setup.py`, replace the body of `render_mcp_setup_md` (the `gen_lines = ...` assignment and the `return (...)` block) with:

```python
    hint = setup.get("install_hint", {})
    install = expand(hint.get(platform) or hint.get("default", ""), platform=platform)
    artifacts = setup.get("graph_artifacts", [])
    if artifacts:
        step2 = "## 2. Generate graphs\n" + "\n".join(
            f"Run: {a['gen_cmd']:<18} -> {a['path']} ({a['name']})" for a in artifacts
        )
    else:
        step2 = "## 2. Index the codebase\n" + setup.get("index_hint", "")
    snippet = render_server_snippet(
        setup, server_key=server_key, ua_mcp_dir=ua_mcp_dir, project_root=project_root,
    )
    body = json.dumps(snippet, indent=2, ensure_ascii=False)
    return (
        f"# MCP Setup — {server_key}\n\n"
        f"## 1. Install engine (if missing)\n{install}\n\n"
        f"{step2}\n\n"
        f"## 3. Wire MCP server (paste into the {platform} MCP config)\n"
        f"```json\n{body}\n```\n\n"
        f"## 4. Verify\nmaika doctor mcp --target {project_root}\n"
    )
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `rtk /usr/bin/python3 -m pytest cli/tests/test_ua_setup.py -v`
Expected: PASS (new tests + existing ua_setup tests).

- [ ] **Step 5: Commit**

```bash
rtk git add cli/mcp/ua_setup.py cli/tests/test_ua_setup.py
rtk git commit -m "feat(cli): render index step in MCP_SETUP.md when no graph artifacts"
```

---

## Task 7: Wire `semantic_search` consumer in skill references

**Files:**
- Modify: `.maika/skills/author-dna-builder/references/code-evidence-scan.md:112`
- Modify: `.maika/skills/convention-intelligence-builder/references/structural-audit-scan.md:21`

These currently call cb-mem-incompatible `codebase_context_search(...)` literally. Migrate to the abstract op so the renderer resolves it to the backend's semantic tool. This gives `semantic_search` a real consumer (DEVELOPMENT_RULES: no declaration without a consumer).

- [ ] **Step 1: Edit code-evidence-scan.md**

In `.maika/skills/author-dna-builder/references/code-evidence-scan.md`, change the line:

```
QUERY Socraticode: codebase_context_search("common logic abstraction helper util")
```

to:

```
QUERY Codebase Memory: {{ tools.semantic_search }}("common logic abstraction helper util")
```

- [ ] **Step 2: Edit structural-audit-scan.md**

In `.maika/skills/convention-intelligence-builder/references/structural-audit-scan.md`, change the line:

```
QUERY Socraticode: codebase_context_search("naming convention class suffix")
```

to:

```
QUERY Codebase Memory: {{ tools.semantic_search }}("naming convention class suffix")
```

- [ ] **Step 3: Verify no literal `codebase_context_search` remains**

Run: `rtk /usr/bin/grep -rn "codebase_context_search" .maika/`
Expected: no output (exit 1).

- [ ] **Step 4: Commit**

```bash
rtk git add .maika/skills/author-dna-builder/references/code-evidence-scan.md .maika/skills/convention-intelligence-builder/references/structural-audit-scan.md
rtk git commit -m "feat(skills): use semantic_search abstract op for code evidence/convention scan"
```

---

## Task 8: Relabel display token `Socraticode` → `Codebase Memory` in `.maika`

**Files:**
- Modify: all `.maika/**` files containing the literal token `Socraticode`.

The token `Socraticode` (the MCP) is distinct from `Socratic` (the questioning method in `infra-tdd/references/socratic-deep-dive.md`); replacing the full token `Socraticode` will NOT touch "Socratic deep-dive". Abstract ops `{{ tools.* }}` are unaffected (they don't contain the token).

- [ ] **Step 1: List affected files**

Run: `rtk /usr/bin/grep -rln "Socraticode" .maika/`
Expected: a list including `rules/rules-tool.md`, `rules/rules-exec.md`, `procedures/executor.md`, `meta-prompt.md`, `knowledge/templates/EXPLORE_CONTEXT.tpl.md`, `skills/skill-index.yaml`, `skills/author-dna-builder/SKILL.md`, `skills/convention-intelligence-builder/SKILL.md`, several `skills/infra-tdd/references/*.md`.

- [ ] **Step 2: Replace the token across .maika**

Run:

```bash
rtk /usr/bin/grep -rl "Socraticode" .maika/ | while read -r f; do
  python3 - "$f" <<'PY'
import sys
p = sys.argv[1]
s = open(p, encoding="utf-8").read()
open(p, "w", encoding="utf-8").write(s.replace("Socraticode", "Codebase Memory"))
PY
done
```

- [ ] **Step 3: Verify no `Socraticode` token remains and `Socratic deep-dive` is intact**

Run: `rtk /usr/bin/grep -rn "Socraticode" .maika/`
Expected: no output (exit 1).

Run: `rtk /usr/bin/grep -rn "Socratic deep-dive" .maika/skills/infra-tdd/references/socratic-deep-dive.md`
Expected: still present (method name untouched).

- [ ] **Step 4: Commit**

```bash
rtk git add .maika/
rtk git commit -m "docs(maika): relabel Socraticode -> Codebase Memory in prose"
```

---

## Task 9: Fix stale `socraticode` reference in test_platforms + full suite

**Files:**
- Modify: `cli/tests/test_platforms.py:36` (`test_render_context_includes_framework_root` uses `["socraticode"]`)

- [ ] **Step 1: Update the stale MCP key in the existing test**

In `cli/tests/test_platforms.py`, in `test_render_context_includes_framework_root`, change:

```python
    ctx = get_platform("antigravity").build_render_context(["socraticode"], "python")
```

to:

```python
    ctx = get_platform("antigravity").build_render_context(["codebase-memory-mcp"], "python")
```

- [ ] **Step 2: Run the full CLI test suite**

Run: `rtk /usr/bin/python3 -m pytest cli/tests/ -v`
Expected: PASS (all tests green; the 188-test baseline plus the new tests).

- [ ] **Step 3: Run an end-to-end init smoke check into a temp dir**

The console entry point `maika` (`.venv/bin/maika`, v3.0.0) is verified working. The init flag is `--mcp` (argparse `action="append"`, one value per flag).

```bash
rm -rf /tmp/maika-cbm-smoke
rtk maika init --target /tmp/maika-cbm-smoke --platform claude-code --mcp codebase-memory-mcp --language python --yes 2>&1 | tail -20
rtk /usr/bin/grep -n "codebase-memory-mcp" /tmp/maika-cbm-smoke/.claude/MCP_SETUP.md
```

Expected: init completes; `MCP_SETUP.md` contains the uvx `mcpServers` snippet with key `codebase-memory-mcp`, an `## 2. Index the codebase` section, and no `Generate graphs` section.

- [ ] **Step 4: Run the doctor against the smoke target**

```bash
rtk maika doctor mcp --target /tmp/maika-cbm-smoke 2>&1 | tail -25
```

Expected: report lists `codebase-memory-mcp` under Selected MCPs; a `### codebase-memory-mcp` setup section with an `engine:` line and a `wired:` line; no traceback.

- [ ] **Step 5: Commit**

```bash
rtk git add cli/tests/test_platforms.py
rtk git commit -m "test(cli): replace stale socraticode key with codebase-memory-mcp"
```

---

## Task 10: Update the spec status

**Files:**
- Modify: `docs/superpowers/specs/2026-06-22-codebase-memory-vs-socraticode-decision.md` (header `Status`)

- [ ] **Step 1: Mark the decision implemented**

Change the header line `**Status:** Decided — adopt ...` to:

```markdown
**Status:** Implemented — see docs/superpowers/plans/2026-06-22-codebase-memory-init-integration.md
```

- [ ] **Step 2: Commit**

```bash
rtk git add docs/superpowers/specs/2026-06-22-codebase-memory-vs-socraticode-decision.md
rtk git commit -m "docs: mark cb-mem decision implemented"
```

---

## Done-When (success criteria)

- `rtk /usr/bin/python3 -m pytest cli/tests/ -v` is fully green.
- No literal `socraticode` / `Socraticode` / `codebase_context_search` remains in `cli/` or `.maika/` (verify: `rtk /usr/bin/grep -rni "socraticode\|codebase_context_search" cli/ .maika/` → no output).
- `maika init … --mcps codebase-memory-mcp` emits an `MCP_SETUP.md` with the uvx server snippet (key `codebase-memory-mcp`) and an Index step.
- `maika doctor mcp` reports cb-mem without error.
- The 4 abstract code ops + `semantic_search` resolve to `mcp__codebase-memory-mcp__*` (claude-code) / `mcp_codebase-memory-mcp_*` (antigravity).
