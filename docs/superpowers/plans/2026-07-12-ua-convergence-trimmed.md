# UA Convergence (Trimmed) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Converge the Understand-Anything provider integration on evidence-backed fixes only — one canonical provider ID, path-safe UA-MCP, one structured metadata tool — and generate real graph data before building anything else.

**Architecture:** This plan replaces the 17-phase "Convergence & Closure" plan (see Supersession, Task 1). It keeps the three fixes whose defects are verified in code today (identity drift, path escape in `_resolve_file_path`, text-only freshness output) and defers all speculative infrastructure (trace-evidence contracts, refresh lifecycle, system-model validator, host qualification) behind an observed-failure gate per `.maika/DEVELOPMENT_RULES.md` R3/R7. Two repos are touched: **Maika** (`/home/zane/Desktop/agent-memory-arch-v3`, branch `master-v2`) and **UA-MCP** (`/home/zane/Desktop/ai-tools/Understand-Anything-MCP`, branch `main`).

**Tech Stack:** Python 3.12, PyYAML, pytest (Maika: `/usr/bin/python3 -m pytest`; UA-MCP: `uv run --with pytest pytest`), FastMCP.

**Verified defect inventory (2026-07-12, Maika @ 853ec45, UA-MCP @ 9a27787):**

| Defect | Evidence | Fixed by |
|---|---|---|
| Provider ID drift: `understand-anything` (manifest `mcp_capabilities`, `external-workflows.yaml` owner) vs `understand-anything-mcp` (`capability-registry.yaml` ×8, `provider-capabilities.yaml`, validator, 3 tests) | grep, this date | Track 1 |
| `_resolve_file_path` joins `graph.root_path + node.file_path` with no containment check — absolute/`..`/symlink escape reads outside project root | `kg_loader.py:964-996` | Track 2 / U-a |
| Freshness/graph state only available as emoji text (`get_graph_stats`) — unusable as machine signal | `server.py:180-278` | Track 2 / U-b |
| Zero UA graphs exist on this machine (0 `.understand-anything/` dirs under `~/Desktop`); UA pipeline never ran end-to-end | `find` sweep, this date | Track 0 |

**Explicitly deferred (Track 3 — do NOT implement without the evidence gate):** provider-registry.yaml + alias API, vendored contract pinning, structured query layer + `ua-mcp` CLI, TRACE_REQUEST/TRACE_EVIDENCE schemas, gate migration, refresh lifecycle, system-model validator + mutation suite, behavior fixtures UA-1..15, 3-host qualification.

---

## Execution order

1. Task 1 (supersession bookkeeping) → Tasks 2–6 = **Maika PR 1** (identity convergence).
2. Tasks 7–9 = **UA-MCP PR U-a** (path safety). Independent of PR 1.
3. Tasks 10–12 = **UA-MCP PR U-b** (structured metadata, v0.2.0). After U-a.
4. Task 13 = **Maika PR 2** (freshness probe → structured tool). After U-b lands.
5. Task 14 = **Track 0 dogfood** (user-driven, parallel any time after U-b).
6. Track 3 stays closed until Task 14's exit gate produces observed failures.

Branch naming: Maika `ua-convergence/identity`, `ua-convergence/metadata-probe`; UA-MCP `hardening/path-safety`, `feat/graph-metadata`.

---

### Task 1: Supersede the original plan (R6 bookkeeping)

**Files:**
- Move: `upgrade/maika-understand-anything-convergence-closure-plan (2).md` → `docs/superpowers/plans/2026-07-12-ua-convergence-full-plan-SUPERSEDED.md`
- Create: this file (`docs/superpowers/plans/2026-07-12-ua-convergence-trimmed.md`)

- [ ] **Step 1: Create branch**

```bash
cd /home/zane/Desktop/agent-memory-arch-v3
git checkout -b ua-convergence/identity
```

- [ ] **Step 2: Move the original plan and stamp it**

```bash
git mv "upgrade/maika-understand-anything-convergence-closure-plan (2).md" \
  docs/superpowers/plans/2026-07-12-ua-convergence-full-plan-SUPERSEDED.md 2>/dev/null \
  || mv "upgrade/maika-understand-anything-convergence-closure-plan (2).md" \
  docs/superpowers/plans/2026-07-12-ua-convergence-full-plan-SUPERSEDED.md
```

Then prepend this header to the moved file (before the `# Maika × Understand-Anything…` title):

```markdown
> **Status: SUPERSEDED by docs/superpowers/plans/2026-07-12-ua-convergence-trimmed.md (2026-07-12).**
> Reason: builds 17 phases of enforcement for unobserved failures (violates DEVELOPMENT_RULES R3/R7);
> no UA graph has ever been generated on this machine, so freshness/health/fixture design has no data.
> Phases 5–17 remain here as the deferred backlog; unlock conditions live in the trimmed plan, Track 3.
```

- [ ] **Step 3: Commit both plan files**

```bash
git add docs/superpowers/plans/2026-07-12-ua-convergence-trimmed.md \
  docs/superpowers/plans/2026-07-12-ua-convergence-full-plan-SUPERSEDED.md
git rm --cached "upgrade/maika-understand-anything-convergence-closure-plan (2).md" 2>/dev/null || true
git commit -m "docs(plan): trimmed UA convergence plan; supersede 17-phase closure plan (R6)

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

## Track 1 — Canonical provider identity (Maika PR 1)

Canonical ID everywhere: `understand-anything`. `UA-MCP` / `Understand-Anything MCP` stay as prose display names only (`.maika/rules/jit/providers.md` is untouched).

### Task 2: Failing tests for `validate_provider_identity`

**Files:**
- Modify: `cli/tests/test_provider_capabilities.py`
- Test: `cli/tests/test_provider_capabilities.py`

- [ ] **Step 1: Add the tests**

Append to `cli/tests/test_provider_capabilities.py` (note: `FRAMEWORK = Path(__file__).resolve().parents[2] / ".maika"` already exists at the top; add `yaml` import and `REPO` beside it):

```python
import yaml

REPO = Path(__file__).resolve().parents[2]


def _identity_inputs():
    mapping, registry = _docs()
    manifest = yaml.safe_load(
        (REPO / "cli" / "plugin-manifest.yaml").read_text(encoding="utf-8")
    )
    workflows = yaml.safe_load(
        (FRAMEWORK / "config" / "external-workflows.yaml").read_text(encoding="utf-8")
    )
    manifest_ids = set((manifest.get("mcp_capabilities") or {}).keys())
    owners = {
        spec.get("owner")
        for spec in (workflows.get("workflows") or {}).values()
        if spec.get("owner")
    }
    return mapping, registry, manifest_ids, owners


def test_identity_flags_provider_missing_from_manifest():
    from cli.agent_content.provider_capabilities import validate_provider_identity
    mapping = {"providers": {"understand-anything-mcp": {"capabilities": {}}}}
    registry = {"capabilities": {}}
    errors = validate_provider_identity(
        mapping, registry, manifest_ids={"understand-anything"}, workflow_owners=set()
    )
    assert any("understand-anything-mcp" in e for e in errors)


def test_identity_flags_unknown_workflow_owner():
    from cli.agent_content.provider_capabilities import validate_provider_identity
    mapping = {"providers": {"understand-anything": {"capabilities": {}}}}
    registry = {"capabilities": {}}
    errors = validate_provider_identity(
        mapping, registry,
        manifest_ids={"understand-anything"},
        workflow_owners={"understand-anything-mcp"},
    )
    assert any("workflow owner" in e for e in errors)


def test_identity_accepts_synthetic_current_source():
    from cli.agent_content.provider_capabilities import validate_provider_identity
    mapping = {"providers": {"current-source": {"capabilities": {}}}}
    registry = {"capabilities": {"x": {"primary_provider": "current-source"}}}
    errors = validate_provider_identity(
        mapping, registry, manifest_ids=set(), workflow_owners=set()
    )
    assert errors == []


def test_repo_provider_ids_converge_across_surfaces():
    from cli.agent_content.provider_capabilities import validate_provider_identity
    mapping, registry, manifest_ids, owners = _identity_inputs()
    assert validate_provider_identity(mapping, registry, manifest_ids, owners) == []
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `/usr/bin/python3 -m pytest cli/tests/test_provider_capabilities.py -v -k identity`
Expected: 4 FAIL/ERROR with `ImportError: cannot import name 'validate_provider_identity'`

### Task 3: Implement `validate_provider_identity`

**Files:**
- Modify: `cli/agent_content/provider_capabilities.py`
- Test: `cli/tests/test_provider_capabilities.py`

- [ ] **Step 1: Add the validator**

Append to `cli/agent_content/provider_capabilities.py`:

```python
SYNTHETIC_PROVIDERS = {"current-source"}


def validate_provider_identity(
    mapping: dict,
    registry: dict,
    manifest_ids: set[str],
    workflow_owners: set[str],
) -> list[str]:
    """Cross-surface identity check: every provider ID used in the profiles must be
    a plugin-manifest mcp_capabilities key (or the synthetic current-source), and
    every external-workflow owner must be a known provider ID."""
    errors: list[str] = []
    used: set[str] = set((mapping.get("providers") or {}).keys())
    for capability, spec in (registry.get("capabilities") or {}).items():
        primary = (spec or {}).get("primary_provider")
        if primary:
            used.add(primary)
        for supporting in (spec or {}).get("supporting_providers") or []:
            used.add(supporting)
    known = manifest_ids | SYNTHETIC_PROVIDERS
    for provider in sorted(used - known):
        errors.append(
            f"provider ID {provider!r} not in plugin-manifest mcp_capabilities "
            f"(known: {sorted(known)!r})"
        )
    for owner in sorted(workflow_owners - used - known):
        errors.append(f"workflow owner {owner!r} is not a known provider ID")
    return errors
```

- [ ] **Step 2: Run tests — unit tests pass, real-file test still fails**

Run: `/usr/bin/python3 -m pytest cli/tests/test_provider_capabilities.py -v -k identity`
Expected: 3 PASS, and `test_repo_provider_ids_converge_across_surfaces` FAIL with `provider ID 'understand-anything-mcp' not in plugin-manifest mcp_capabilities` — this failure is the litmus that drift detection works against real repo files.

- [ ] **Step 3: Commit the validator (red on real data is expected and documented)**

```bash
git add cli/agent_content/provider_capabilities.py cli/tests/test_provider_capabilities.py
git commit -m "feat(providers): cross-surface provider identity validator (red: drift exists)

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

### Task 4: Rename `understand-anything-mcp` → `understand-anything`

**Files:**
- Modify: `.maika/profiles/provider-capabilities.yaml:3` (provider key)
- Modify: `.maika/profiles/capability-registry.yaml` (lines 6, 23, 29, 36, 43, 50, 56, 64)
- Modify: `cli/agent_content/provider_capabilities.py` (guard sites, previously lines 53–54 and 68)
- Modify: `cli/tests/test_provider_capabilities.py:22,42`, `cli/tests/test_generated_reports.py:15`

- [ ] **Step 1: Rename in the two profile YAMLs**

In `.maika/profiles/provider-capabilities.yaml` change the provider key:

```yaml
providers:
  understand-anything:
    freshness_probe:
      tool: get_graph_stats
```

In `.maika/profiles/capability-registry.yaml` replace all 8 occurrences of `understand-anything-mcp` with `understand-anything` (6× `primary_provider:`, 2× inside `supporting_providers:` lists).

- [ ] **Step 2: Rename in validator guards and tests**

In `cli/agent_content/provider_capabilities.py`, the three comparisons/messages `provider == "understand-anything-mcp"` / `"understand-anything-mcp: unknown freshness probe"` become `"understand-anything"`. In `cli/tests/test_provider_capabilities.py` lines 22 and 42, `mapping["providers"]["understand-anything-mcp"]` → `mapping["providers"]["understand-anything"]`. In `cli/tests/test_generated_reports.py:15`, `provider: understand-anything-mcp` → `provider: understand-anything`.

- [ ] **Step 3: Verify zero occurrences remain and tests pass**

```bash
/usr/bin/grep -rn "understand-anything-mcp" --include="*.py" --include="*.yaml" .maika/ cli/ scripts/ .github/ ; echo "exit=$?"
```

Expected: no output, `exit=1`.

Run: `/usr/bin/python3 -m pytest cli/tests/test_provider_capabilities.py cli/tests/test_generated_reports.py -v`
Expected: ALL PASS (including `test_repo_provider_ids_converge_across_surfaces`).

- [ ] **Step 4: Commit**

```bash
git add -A .maika/profiles cli/agent_content/provider_capabilities.py cli/tests
git commit -m "fix(providers): converge provider ID on understand-anything across all surfaces

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

### Task 5: Wire identity check into `maika content validate-provider-capabilities` + ledger entry

**Files:**
- Modify: `cli/commands/content.py` (the `validate-provider-capabilities` action, ~line 159)
- Modify: `docs/refactor/maika-vnext/enforcement-ledger.yaml` (append entry ENF-027; verify 026 is still the last ID first)

- [ ] **Step 1: Extend the content action**

In `cli/commands/content.py`, inside `if action == "validate-provider-capabilities":`, after the existing `errors = validate_provider_capabilities(mapping, registry)` line, add:

```python
        import yaml as _yaml
        from cli.agent_content.provider_capabilities import validate_provider_identity
        manifest_path = Path(target) / "cli" / "plugin-manifest.yaml"
        workflows_path = framework / "config" / "external-workflows.yaml"
        manifest_ids: set[str] = set()
        owners: set[str] = set()
        if manifest_path.is_file():
            manifest_doc = _yaml.safe_load(manifest_path.read_text(encoding="utf-8")) or {}
            manifest_ids = set((manifest_doc.get("mcp_capabilities") or {}).keys())
        if workflows_path.is_file():
            wf_doc = _yaml.safe_load(workflows_path.read_text(encoding="utf-8")) or {}
            owners = {
                spec.get("owner")
                for spec in (wf_doc.get("workflows") or {}).values()
                if spec.get("owner")
            }
        errors += validate_provider_identity(mapping, registry, manifest_ids, owners)
```

(Match the surrounding import/`Path` style of content.py — if `Path` and a yaml loader are already imported at module level, reuse them instead of local imports.)

- [ ] **Step 2: Verify CLI passes and fails correctly**

```bash
/usr/bin/python3 -m cli.maika content validate-provider-capabilities
```

(Entry point is `maika = cli.maika:main` per pyproject; the installed `maika` binary works too. Note `scripts/run_ci.py:28` already runs this exact action, so identity errors enter CI automatically — no CI wiring needed.)
Expected: `provider capabilities valid: 3 providers`, exit 0.

Mutation check (manual, do not commit): temporarily change one `primary_provider:` in `capability-registry.yaml` back to `understand-anything-mcp`, rerun — expected exit 1 with a `provider-capability:` identity error. Revert with `git checkout .maika/profiles/capability-registry.yaml`.

- [ ] **Step 3: Append ledger entry (R3)**

Append to `entries:` in `docs/refactor/maika-vnext/enforcement-ledger.yaml` (first confirm ENF-026 is still the highest ID; if not, use the next free number):

```yaml
  - id: ENF-027
    mechanism: provider-identity
    type: validator
    status: active
    failure:
      classification: observed_failure
      reference: docs/superpowers/plans/2026-07-12-ua-convergence-trimmed.md
      summary: >-
        Provider ID drift observed 2026-07-12: manifest/external-workflows used
        understand-anything while capability-registry (8 refs), provider-capabilities
        and validator guards used understand-anything-mcp.
    implementation:
      files: [cli/agent_content/provider_capabilities.py]
      consumers: [cli/commands/content.py, cli/tests/test_provider_capabilities.py]
    scope: {change_classes: [standard, architectural]}
    reviewed_at: 2026-07-12
```

- [ ] **Step 4: Commit**

```bash
git add cli/commands/content.py docs/refactor/maika-vnext/enforcement-ledger.yaml
git commit -m "feat(content): surface provider identity errors in validate-provider-capabilities; ledger ENF-027

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

### Task 6: Full CI + PR

- [ ] **Step 1: Full test suite and CI script**

Run: `/usr/bin/python3 -m pytest cli/tests/ .maika/tools/gate-check/tests/ -q`
Expected: all pass, 0 failures.

Run: `/usr/bin/python3 scripts/run_ci.py`
Expected: green (same gate as previous slices: test-first → run_ci → diff-check).

Run: `git diff --check`
Expected: no output.

- [ ] **Step 2: Push and open PR**

```bash
git push -u origin ua-convergence/identity
gh pr create --base master-v2 --title "UA convergence Track 1: canonical provider ID understand-anything" \
  --body "$(cat <<'EOF'
Converges provider identity on `understand-anything` (manifest + external-workflows spelling) across capability-registry (8 refs), provider-capabilities, validator guards and tests. Adds cross-surface identity validator (ENF-027) wired into `maika content validate-provider-capabilities` so re-drift fails CI. Supersedes the 17-phase closure plan per R6 (see docs/superpowers/plans/2026-07-12-ua-convergence-trimmed.md).

🤖 Generated with [Claude Code](https://claude.com/claude-code)
EOF
)"
```

---

## Track 2 — UA-MCP minimal hardening (repo: `/home/zane/Desktop/ai-tools/Understand-Anything-MCP`)

### Task 7: Failing path-safety tests (PR U-a)

**Files:**
- Create: `tests/test_path_safety.py`
- Test: `tests/test_path_safety.py`

- [ ] **Step 1: Create branch**

```bash
cd /home/zane/Desktop/ai-tools/Understand-Anything-MCP
git checkout -b hardening/path-safety
```

- [ ] **Step 2: Write the tests**

Create `tests/test_path_safety.py`:

```python
"""_resolve_file_path must never read outside the project root (or an
UPSTREAM_ROOTS entry for upstream: nodes) — graphs are agent-generated JSON
and must be treated as untrusted input."""
import os

import pytest

import kg_loader as kgl


def _graph(tmp_path):
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "ok.java").write_text("class Ok {}", encoding="utf-8")
    return kgl.ProjectGraph(name="p", root_path=str(tmp_path), project_info={})


def _node(node_id, file_path):
    # Node has no field defaults — from_dict fills them.
    return kgl.Node.from_dict({"id": node_id, "type": "file", "name": "n",
                               "filePath": file_path})


def test_legit_relative_path_resolves(tmp_path):
    g = _graph(tmp_path)
    got = kgl._resolve_file_path(g, _node("file:ok", "src/ok.java"))
    assert got == os.path.realpath(os.path.join(str(tmp_path), "src", "ok.java"))


def test_absolute_path_rejected(tmp_path):
    g = _graph(tmp_path)
    outside = tmp_path.parent / "secret.txt"
    outside.write_text("s", encoding="utf-8")
    assert kgl._resolve_file_path(g, _node("file:x", str(outside))) is None


def test_dotdot_escape_rejected(tmp_path):
    g = _graph(tmp_path)
    (tmp_path.parent / "escape.txt").write_text("s", encoding="utf-8")
    assert kgl._resolve_file_path(g, _node("file:x", "../escape.txt")) is None


def test_symlink_escape_rejected(tmp_path):
    g = _graph(tmp_path)
    outside = tmp_path.parent / "target.txt"
    outside.write_text("s", encoding="utf-8")
    link = tmp_path / "link.txt"
    try:
        link.symlink_to(outside)
    except (OSError, NotImplementedError):
        pytest.skip("symlinks unavailable")
    assert kgl._resolve_file_path(g, _node("file:x", "link.txt")) is None


def test_nul_byte_rejected(tmp_path):
    g = _graph(tmp_path)
    assert kgl._resolve_file_path(g, _node("file:x", "src/ok\x00.java")) is None


def test_upstream_root_containment(tmp_path, monkeypatch):
    g = _graph(tmp_path)
    upstream = tmp_path.parent / "upstream"
    (upstream / "lib").mkdir(parents=True)
    (upstream / "lib" / "u.java").write_text("class U {}", encoding="utf-8")
    monkeypatch.setenv("UPSTREAM_ROOTS", str(upstream))
    ok = kgl._resolve_file_path(g, _node("upstream:u", "lib/u.java"))
    assert ok == os.path.realpath(os.path.join(str(upstream), "lib", "u.java"))
    (tmp_path.parent / "beyond.txt").write_text("s", encoding="utf-8")
    assert kgl._resolve_file_path(g, _node("upstream:x", "../beyond.txt")) is None
```

(Constructors verified against `kg_loader.py`: `ProjectGraph(name, root_path, project_info)` are the three defaultless fields — line 170; `Node` has no defaults, so tests build nodes via `Node.from_dict` — line 26.)

- [ ] **Step 3: Run tests to verify current behavior fails**

Run: `uv run --with pytest pytest tests/test_path_safety.py -v`
Expected: `test_legit_relative_path_resolves` and `test_upstream_root_containment` (positive half) PASS; `test_absolute_path_rejected`, `test_dotdot_escape_rejected`, `test_symlink_escape_rejected`, `test_nul_byte_rejected` FAIL (current code resolves them).

### Task 8: Implement containment in `_resolve_file_path`

**Files:**
- Modify: `kg_loader.py:964-996` (`_resolve_file_path`)
- Test: `tests/test_path_safety.py`

- [ ] **Step 1: Add helper and rewrite resolution**

Add above `_resolve_file_path` in `kg_loader.py`:

```python
def _contained_path(root: str, rel_path: str) -> str | None:
    """Resolve rel_path against root; return the absolute path only if it exists
    and its real path stays inside root (graphs are untrusted input)."""
    if not rel_path or "\x00" in rel_path or os.path.isabs(rel_path):
        return None
    root_real = os.path.realpath(root)
    candidate = os.path.realpath(os.path.join(root_real, rel_path))
    try:
        if os.path.commonpath([root_real, candidate]) != root_real:
            return None
    except ValueError:  # different drives (Windows)
        return None
    return candidate if os.path.exists(candidate) else None
```

Rewrite the body of `_resolve_file_path` to use it (keep the docstring, update the resolution-order note):

```python
    candidate = _contained_path(graph.root_path, node.file_path)
    if candidate is not None:
        return candidate

    if node.id.startswith("upstream:"):
        upstream_roots = os.environ.get("UPSTREAM_ROOTS", "")
        for root in upstream_roots.split(","):
            root = root.strip()
            if not root:
                continue
            candidate = _contained_path(root, node.file_path)
            if candidate is not None:
                return candidate

    return None
```

(Preserve any remaining tail logic of the original function only if it exists beyond the upstream loop — read `kg_loader.py:978-996` first; the original simply returns None at the end.)

- [ ] **Step 2: Run the new tests**

Run: `uv run --with pytest pytest tests/test_path_safety.py -v`
Expected: ALL PASS.

### Task 9: Full UA-MCP suite + commit + PR

- [ ] **Step 1: Full suite**

Run: `uv run --with pytest pytest tests/ -v`
Expected: all pass (55 pre-existing + new). If a pre-existing test fixture relied on escape behavior (e.g. absolute `file_path` in fixtures), fix the fixture, not the containment.

- [ ] **Step 2: Commit and PR**

```bash
git add kg_loader.py tests/test_path_safety.py
git commit -m "fix(loader): contain source reads to project root / UPSTREAM_ROOTS

Graphs are agent-generated JSON and must be treated as untrusted input:
reject absolute paths, .. traversal, NUL bytes and symlink escapes in
_resolve_file_path.

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
git push -u origin hardening/path-safety
gh pr create --base main --title "Path containment for node source reads" \
  --body "Rejects absolute/../symlink/NUL escapes when resolving node.file_path. 🤖 Generated with [Claude Code](https://claude.com/claude-code)"
```

### Task 10: Failing tests for `get_graph_metadata` (PR U-b)

**Files:**
- Create: `tests/test_graph_metadata.py`
- Test: `tests/test_graph_metadata.py`

- [ ] **Step 1: Create branch (after U-a merges)**

```bash
cd /home/zane/Desktop/ai-tools/Understand-Anything-MCP
git checkout main && git pull && git checkout -b feat/graph-metadata
```

- [ ] **Step 2: Write the tests**

Create `tests/test_graph_metadata.py`:

```python
"""build_graph_metadata: one structured, JSON-safe snapshot of graph state
(identity, counts, graph commit, repository HEAD, freshness) — the machine
counterpart of the human get_graph_stats text."""
import json
import subprocess

import kg_loader as kgl


def _git(tmp_path, *args):
    subprocess.run(["git", *args], cwd=tmp_path, check=True, capture_output=True)


def _repo_with_graph(tmp_path):
    _git(tmp_path, "init")
    _git(tmp_path, "-c", "user.email=t@t", "-c", "user.name=t", "commit",
         "--allow-empty", "-m", "init")
    return kgl.ProjectGraph(name="p", root_path=str(tmp_path), project_info={})


def test_metadata_shape_and_json_safety(tmp_path):
    g = _repo_with_graph(tmp_path)
    meta = kgl.build_graph_metadata(g)
    encoded = json.dumps(meta)  # must be JSON-serializable
    assert json.loads(encoded)["contract_version"] == 1
    assert meta["project"] == "p"
    assert meta["root_path"] == str(tmp_path)
    for key in ("node_count", "edge_count", "domain_node_count", "graph_commit",
                "analyzed_at"):
        assert key in meta["graph"]
    assert set(meta["freshness"]) >= {"status", "stale_file_count",
                                      "stale_files_sample", "git_commit_hash"}


def test_repository_head_matches_git(tmp_path):
    g = _repo_with_graph(tmp_path)
    head = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=tmp_path,
        capture_output=True, text=True, check=True,
    ).stdout.strip()
    meta = kgl.build_graph_metadata(g)
    assert meta["repository"]["head"] == head


def test_head_empty_outside_git_repo(tmp_path):
    g = kgl.ProjectGraph(name="p", root_path=str(tmp_path), project_info={})
    meta = kgl.build_graph_metadata(g)
    assert meta["repository"]["head"] == ""
    assert meta["freshness"]["status"] == "UNKNOWN"
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `uv run --with pytest pytest tests/test_graph_metadata.py -v`
Expected: FAIL with `AttributeError: module 'kg_loader' has no attribute 'build_graph_metadata'`

### Task 11: Implement `build_graph_metadata` + MCP tool with error envelope

**Files:**
- Modify: `kg_loader.py` (new functions next to `check_freshness`, ~line 336)
- Modify: `server.py` (new tool after `get_graph_stats`, ~line 279)
- Test: `tests/test_graph_metadata.py`

- [ ] **Step 1: kg_loader functions**

Add to `kg_loader.py` after `check_freshness`:

```python
def get_repository_head(root_path: str) -> str:
    """Current HEAD of the repo at root_path; '' if not a repo / git missing."""
    try:
        proc = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=root_path, capture_output=True, text=True, timeout=10,
        )
    except (OSError, subprocess.SubprocessError):
        return ""
    return proc.stdout.strip() if proc.returncode == 0 else ""


def build_graph_metadata(graph: ProjectGraph) -> dict[str, Any]:
    """Structured, JSON-safe snapshot of graph state. Single source of truth for
    machine consumers; get_graph_stats remains the human rendering."""
    freshness = check_freshness(graph)
    return {
        "contract_version": 1,
        "project": graph.name,
        "root_path": graph.root_path,
        "graph": {
            "node_count": len(graph.nodes),
            "edge_count": len(graph.edges),
            "domain_node_count": len(graph.domain_nodes),
            "layer_count": len(graph.layers),
            "graph_commit": graph.git_commit_hash,
            "analyzed_at": graph.analyzed_at,
        },
        "repository": {"head": get_repository_head(graph.root_path)},
        "freshness": freshness,
    }
```

(`subprocess` may need importing in kg_loader.py — check the imports; `check_freshness` already shells out to git, so it is likely present.)

- [ ] **Step 2: MCP tool in server.py**

Add after `get_graph_stats` (~line 279):

```python
# ---------------------------------------------------------------------------
# Tool: get_graph_metadata (structured)
# ---------------------------------------------------------------------------

@mcp.tool()
def get_graph_metadata(project: str | None = None) -> str:
    """
    Structured JSON snapshot of a project's graph state: identity, node/edge
    counts, graph commit, repository HEAD and freshness. Machine counterpart
    of get_graph_stats — parse it instead of the text output.

    Args:
        project: Project name. Leave empty if only one project is loaded.

    Returns:
        JSON string: {"ok": true, ...metadata} or
        {"ok": false, "error": {"code", "message", "remediation"}}.
    """
    try:
        graph = _resolve_project(project)
    except ValueError as e:
        return json.dumps({
            "ok": False,
            "error": {
                "code": "unknown_project",
                "message": str(e),
                "remediation": "Call list_projects and pass an exact project name.",
            },
        })
    return json.dumps({"ok": True, **kgl.build_graph_metadata(graph)})
```

(`json` may need importing in server.py — check the imports.)

- [ ] **Step 3: Run tests**

Run: `uv run --with pytest pytest tests/test_graph_metadata.py tests/ -v`
Expected: ALL PASS.

### Task 12: Version bump + README + release commit

**Files:**
- Modify: `pyproject.toml` (version `0.1.0` → `0.2.0`)
- Modify: `README.md` (add `get_graph_metadata` to the tool table)

- [ ] **Step 1: Bump and document**

In `pyproject.toml`: `version = "0.2.0"`. In `README.md`, add one row to the tools list: `get_graph_metadata — structured JSON graph/freshness snapshot (machine counterpart of get_graph_stats)`.

- [ ] **Step 2: Full suite, commit, PR**

Run: `uv run --with pytest pytest tests/ -v` — expected all pass.

```bash
git add kg_loader.py server.py tests/test_graph_metadata.py pyproject.toml README.md
git commit -m "feat: get_graph_metadata structured tool + repository HEAD; v0.2.0

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
git push -u origin feat/graph-metadata
gh pr create --base main --title "get_graph_metadata: structured graph/freshness snapshot (v0.2.0)" \
  --body "JSON tool with ok/error envelope, graph commit + repo HEAD + freshness. Text tools unchanged. 🤖 Generated with [Claude Code](https://claude.com/claude-code)"
```

### Task 13: Maika PR 2 — point freshness probe at the structured tool

**Files:**
- Modify: `.maika/profiles/provider-capabilities.yaml` (freshness_probe.tool)
- Modify: `cli/agent_content/provider_capabilities.py` (UA_TOOLS set)
- Test: `cli/tests/test_provider_capabilities.py`

Only after UA-MCP v0.2.0 is merged. Consumer for the new UA_TOOLS entry is the yaml probe reference (R1-compliant, same PR).

- [ ] **Step 1: Failing check**

In `.maika/profiles/provider-capabilities.yaml`:

```yaml
    freshness_probe:
      tool: get_graph_metadata
```

Run: `/usr/bin/python3 -m pytest cli/tests/test_provider_capabilities.py -v`
Expected: FAIL — `unknown freshness probe` (tool not in UA_TOOLS yet). This proves the validator guards the probe.

- [ ] **Step 2: Add tool to UA_TOOLS and pass**

In `cli/agent_content/provider_capabilities.py`, add `"get_graph_metadata",` to the `UA_TOOLS` set.

Run: `/usr/bin/python3 -m pytest cli/tests/ -q` — expected all pass.

- [ ] **Step 3: Commit + PR**

```bash
cd /home/zane/Desktop/agent-memory-arch-v3
git checkout master-v2 && git pull && git checkout -b ua-convergence/metadata-probe
git add .maika/profiles/provider-capabilities.yaml cli/agent_content/provider_capabilities.py
git commit -m "feat(providers): freshness probe uses structured get_graph_metadata (UA-MCP v0.2.0)

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
git push -u origin ua-convergence/metadata-probe
gh pr create --base master-v2 --title "UA convergence: structured freshness probe" \
  --body "Requires UA-MCP >= 0.2.0. 🤖 Generated with [Claude Code](https://claude.com/claude-code)"
```

---

## Track 0 — Generate real data + dogfood (user-driven, no code)

This is the evidence engine for Track 3. It needs interactive sessions in the target projects (graph generation is agent-driven via the `/understand` plugin skill), so the orchestrating agent prepares and records; the user runs the sessions.

### Task 14: Dogfood checklist

- [ ] **Step 1: Build graphs for two projects**

In a Claude Code session inside `/home/zane/Desktop/ngac` (the previously pinned project): run `/understand`, then `/understand-domain`. Repeat in `/home/zane/Desktop/agent-memory-arch-v3` if time allows (UA on a mostly-Markdown/Python framework repo is itself a data point).

Verify after each:

```bash
ls -la <project>/.understand-anything/
```

Expected: `knowledge-graph.json`, `meta.json` (and `domain-graph.json` after /understand-domain).

- [ ] **Step 2: Probe the server against the real graph**

```bash
cd /home/zane/Desktop/ai-tools/Understand-Anything-MCP
uv run python -c "
import kg_loader as kgl, json
g = kgl.load_project('/home/zane/Desktop/ngac')
print(json.dumps(kgl.build_graph_metadata(g), indent=2))"
```

(Loader entry point verified: `load_project(project_root)` at `kg_loader.py:239`.) Record the output — this is the first real freshness/health data point ever captured.

- [ ] **Step 3: Run 5 grounding questions through Maika task flow in ngac**

One question per archetype: (1) call-chain trace of a core flow, (2) impact of changing a central class, (3) domain-flow question, (4) deliberately ambiguous anchor (a name matching multiple nodes), (5) a question touching a file changed after graph build (stale-relevant).

- [ ] **Step 4: Log every run**

Create `docs/superpowers/plans/2026-07-12-ua-dogfood-log.md` in Maika with one row per run:

```markdown
| # | Project | Question | Tools actually called | UA primary? | Failure observed | Class |
|---|---------|----------|----------------------|-------------|------------------|-------|
```

`Class` ∈ {routing (agent didn't pick UA), anchor (wrong/ambiguous node), freshness (stale misused), fidelity (graph wrong vs source), gate (gate-check misfire), none}.

- [ ] **Step 5: Exit gate**

For each non-`none` failure: reproduce it once, then add an `enforcement-ledger.yaml` candidate entry (classification `observed_failure`, reference the dogfood log). **Only these entries unlock Track 3 items.** If all runs are clean, Track 3 stays closed and the initiative ends here — that is a success, not a gap.

---

## Track 3 — Deferred backlog (evidence-gated, no tasks)

Source material: phases 5–17 of the superseded plan. Each item lists its unlock condition; without a matching ledger entry from Task 14, do not build it (R3).

| Deferred item | Unlock condition (observed in dogfood log) |
|---|---|
| Gate migration off CBM-specific regex (`gates.py:22-27,83,205`) | ≥1 `gate`-class failure: gate-check blocks a valid UA-primary run |
| Replace hard-coded `UA_TOOLS` with contract export | UA-MCP tool set changes and the drift actually bites (validator false-pass/fail) |
| TRACE_REQUEST/TRACE_EVIDENCE schemas + deterministic pre-worker execution | ≥2 `routing`-class failures: worker ignores UA despite healthy fresh graph |
| Refresh workflow lifecycle (BLOCKED → /understand → re-probe → resume) | ≥1 `freshness`-class failure where the ad-hoc path loses task state |
| Graph health checks (dangling edges, dup IDs) in UA-MCP | ≥1 `fidelity`-class failure traced to a malformed graph |
| Structured query layer + `ua-mcp` CLI | Any Track 3 item above lands and needs machine traversal output |
| System-model validator + mutation suite, 3-host qualification | Multiple Track 3 items landed and cross-surface drift recurred after ENF-027 |
