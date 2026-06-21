# UA (Understand-Anything) Init Integration — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** `maika init` emits a paste-ready UA `mcpServers` snippet + 3-step guide, and `maika doctor mcp` verifies engine-installed / both graphs / MCP-wired across claude-code, codex, antigravity.

**Architecture:** All UA knowledge lives as a `setup` block in `cli/plugin-manifest.yaml` (data, not Python). One focused helper module `cli/mcp/ua_setup.py` does placeholder expansion, engine detection, snippet/guide rendering, and graph-status counting. `init` and `doctor` consume it. No shell-out, no writing into the agent's MCP config.

**Tech Stack:** Python 3.9+, PyYAML, stdlib `json`/`pathlib`. Tests: pytest.

**Spec:** `docs/superpowers/specs/2026-06-21-ua-mcp-init-integration-design.md`

**Conventions:**
- Run tests with system Python: `/usr/bin/python3 -m pytest <path> -q` (the venv python has no pytest). `--import-mode=importlib` is already in `pyproject.toml`.
- Each `git commit` message ends with the trailer `Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>` (omitted from the short commands below for brevity).
- Branch `feat/ua-mcp-init-integration` is already checked out.

---

## File Structure

| File | Create/Modify | Responsibility |
|------|---------------|----------------|
| `cli/plugin-manifest.yaml` | Modify | Add `setup` block to `mcp_capabilities.understand-anything`. |
| `cli/mcp/ua_setup.py` | Create | Pure helpers: `expand`, `resolve_engine_check`, `engine_status_line`, `render_server_snippet`, `render_mcp_setup_md`, `graph_status_lines`, `has_setup`. |
| `cli/maika.py` | Modify | Add `--ua-mcp-dir` arg to `init`; pass to `run_init`. |
| `cli/commands/init.py` | Modify | Resolve `ua_mcp_dir`; emit `MCP_SETUP.md`; extend Next steps. |
| `cli/mcp/doctor.py` | Modify | `build_doctor_status` loads manifest + adds `setup_reports`; `render_report` prints them. |
| `cli/commands/doctor.py` | Modify | Pass auto-detected `maika_root` into `build_doctor_status`. |
| `cli/tests/test_manifest_setup.py` | Create | Manifest `setup` schema test. |
| `cli/tests/test_ua_setup.py` | Create | Unit tests for `ua_setup.py`. |
| `cli/tests/test_init.py` | Modify | `ua_mcp_dir` resolution + `MCP_SETUP.md` emission. |
| `cli/tests/test_mcp_doctor.py` | Modify | 3-tier verify + regression. |

---

## Task 1: Manifest `setup` block + schema test

**Files:**
- Modify: `cli/plugin-manifest.yaml` (entry `mcp_capabilities.understand-anything`)
- Test: `cli/tests/test_manifest_setup.py`

- [ ] **Step 1: Write the failing test**

```python
# cli/tests/test_manifest_setup.py
from pathlib import Path
from cli.scaffold import load_manifest

MAIKA_ROOT = Path(__file__).resolve().parent.parent.parent


def _ua_setup():
    manifest = load_manifest(MAIKA_ROOT)
    return manifest["mcp_capabilities"]["understand-anything"]["setup"]


def test_setup_has_two_graph_artifacts():
    arts = _ua_setup()["graph_artifacts"]
    names = {a["name"] for a in arts}
    assert names == {"code", "domain"}
    for a in arts:
        assert a["path"].startswith(".understand-anything/")
        assert a["gen_cmd"].startswith("/understand")


def test_setup_engine_check_kinds_valid():
    checks = _ua_setup()["engine_check"]
    assert {"claude-code", "codex", "antigravity", "default"} <= set(checks)
    for spec in checks.values():
        assert spec["kind"] in ("path_exists", "file_contains")
        assert "{home}" in spec["path"]
    assert checks["claude-code"]["needle"] == "understand-anything@"


def test_setup_server_and_install_hint():
    setup = _ua_setup()
    assert setup["server"]["command"] == "uv"
    assert "{ua_mcp_dir}" in setup["server"]["args"]
    assert setup["server"]["env"]["PROJECT_ROOTS"] == "{project_root}"
    assert "claude-code" in setup["install_hint"]
    assert "default" in setup["install_hint"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `/usr/bin/python3 -m pytest cli/tests/test_manifest_setup.py -q`
Expected: FAIL with `KeyError: 'setup'`.

- [ ] **Step 3: Add the `setup` block to the manifest**

In `cli/plugin-manifest.yaml`, replace the `understand-anything` entry with:

```yaml
  understand-anything:
    provides: code_exploration
    display: "Understand Anything — Knowledge Graph (alternative to Socraticode)"
    setup:
      graph_artifacts:
        - { name: code,   path: ".understand-anything/knowledge-graph.json", gen_cmd: "/understand" }
        - { name: domain, path: ".understand-anything/domain-graph.json",   gen_cmd: "/understand-domain" }
      engine_check:
        claude-code: { kind: file_contains, path: "{home}/.claude/plugins/installed_plugins.json", needle: "understand-anything@" }
        codex:       { kind: path_exists,   path: "{home}/.agents/skills/understand" }
        antigravity: { kind: path_exists,   path: "{home}/.gemini/antigravity/skills/understand-anything" }
        default:     { kind: path_exists,   path: "{home}/.understand-anything/repo" }
      install_hint:
        claude-code: "/plugin marketplace add Egonex-AI/Understand-Anything -> /plugin install understand-anything"
        default:     "curl -fsSL https://raw.githubusercontent.com/Egonex-AI/Understand-Anything/main/install.sh | bash -s {platform}"
      server:
        command: "uv"
        args: ["--directory", "{ua_mcp_dir}", "run", "server.py"]
        env: { PROJECT_ROOTS: "{project_root}" }
```

- [ ] **Step 4: Run test to verify it passes**

Run: `/usr/bin/python3 -m pytest cli/tests/test_manifest_setup.py -q`
Expected: PASS (3 passed).

- [ ] **Step 5: Commit**

```bash
git add cli/plugin-manifest.yaml cli/tests/test_manifest_setup.py
git commit -m "feat(cli): add understand-anything setup block to manifest"
```

---

## Task 2: `ua_setup` — `expand`, `resolve_engine_check`, `engine_status_line`

**Files:**
- Create: `cli/mcp/ua_setup.py`
- Test: `cli/tests/test_ua_setup.py`

- [ ] **Step 1: Write the failing test**

```python
# cli/tests/test_ua_setup.py
from pathlib import Path
from cli.mcp import ua_setup


def test_expand_substitutes_all_placeholders():
    out = ua_setup.expand(
        "{home}/x {platform} {ua_mcp_dir} {project_root}",
        home=Path("/h"), platform="codex", ua_mcp_dir="/srv", project_root="/proj",
    )
    assert out == "/h/x codex /srv /proj"


def test_resolve_engine_check_path_exists(tmp_path):
    marker = tmp_path / ".agents" / "skills" / "understand"
    marker.parent.mkdir(parents=True)
    marker.write_text("x")
    setup = {"engine_check": {"codex": {"kind": "path_exists", "path": "{home}/.agents/skills/understand"}}}
    assert ua_setup.resolve_engine_check(setup, "codex", tmp_path) is True
    assert ua_setup.resolve_engine_check(setup, "codex", tmp_path / "empty") is False


def test_resolve_engine_check_file_contains(tmp_path):
    reg = tmp_path / ".claude" / "plugins" / "installed_plugins.json"
    reg.parent.mkdir(parents=True)
    reg.write_text('{"plugins": {"understand-anything@Egonex-AI": []}}')
    setup = {"engine_check": {"claude-code": {
        "kind": "file_contains", "path": "{home}/.claude/plugins/installed_plugins.json",
        "needle": "understand-anything@"}}}
    assert ua_setup.resolve_engine_check(setup, "claude-code", tmp_path) is True
    reg.write_text('{"plugins": {}}')
    assert ua_setup.resolve_engine_check(setup, "claude-code", tmp_path) is False


def test_resolve_engine_check_falls_back_to_default(tmp_path):
    (tmp_path / ".understand-anything" / "repo").mkdir(parents=True)
    setup = {"engine_check": {"default": {"kind": "path_exists", "path": "{home}/.understand-anything/repo"}}}
    assert ua_setup.resolve_engine_check(setup, "unknown-platform", tmp_path) is True


def test_engine_status_line(tmp_path):
    setup = {
        "engine_check": {"default": {"kind": "path_exists", "path": "{home}/.understand-anything/repo"}},
        "install_hint": {"default": "curl ... bash -s {platform}"},
    }
    assert ua_setup.engine_status_line(setup, "codex", tmp_path).startswith("engine: ✗ not installed")
    assert "bash -s codex" in ua_setup.engine_status_line(setup, "codex", tmp_path)
    (tmp_path / ".understand-anything" / "repo").mkdir(parents=True)
    assert ua_setup.engine_status_line(setup, "codex", tmp_path) == "engine: ✓ installed"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `/usr/bin/python3 -m pytest cli/tests/test_ua_setup.py -q`
Expected: FAIL with `ModuleNotFoundError: No module named 'cli.mcp.ua_setup'`.

- [ ] **Step 3: Create the module with these functions**

```python
# cli/mcp/ua_setup.py
"""Helpers for MCP capabilities that declare a `setup` block in the manifest.

Generic over the `setup` schema (no hard-coded server/path values) so any
capability can opt in; understand-anything is the first consumer.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Optional


def expand(template: str, *, home: Optional[Path] = None, platform: str = "",
           ua_mcp_dir: str = "", project_root: str = "") -> str:
    """Substitute the four supported placeholders in a manifest template string."""
    return (
        template
        .replace("{home}", str(home) if home is not None else "")
        .replace("{platform}", platform)
        .replace("{ua_mcp_dir}", ua_mcp_dir)
        .replace("{project_root}", project_root)
    )


def has_setup(capability: dict) -> bool:
    return isinstance(capability, dict) and isinstance(capability.get("setup"), dict)


def resolve_engine_check(setup: dict, platform: str, home: Path) -> bool:
    """True if the engine marker for `platform` (fallback 'default') is present."""
    checks = setup.get("engine_check", {})
    spec = checks.get(platform) or checks.get("default")
    if not spec:
        return False
    path = Path(expand(spec["path"], home=home))
    kind = spec.get("kind", "path_exists")
    if kind == "path_exists":
        return path.exists() or path.is_symlink()
    if kind == "file_contains":
        try:
            return spec.get("needle", "") in path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            return False
    return False


def engine_status_line(setup: dict, platform: str, home: Path) -> str:
    if resolve_engine_check(setup, platform, home):
        return "engine: ✓ installed"
    hint = setup.get("install_hint", {})
    install = expand(hint.get(platform) or hint.get("default", ""), platform=platform)
    return f"engine: ✗ not installed — {install}"
```

- [ ] **Step 4: Run test to verify it passes**

Run: `/usr/bin/python3 -m pytest cli/tests/test_ua_setup.py -q`
Expected: PASS (5 passed).

- [ ] **Step 5: Commit**

```bash
git add cli/mcp/ua_setup.py cli/tests/test_ua_setup.py
git commit -m "feat(cli): ua_setup expand + engine detection helpers"
```

---

## Task 3: `ua_setup.render_server_snippet`

**Files:**
- Modify: `cli/mcp/ua_setup.py`
- Test: `cli/tests/test_ua_setup.py`

- [ ] **Step 1: Write the failing test**

```python
# append to cli/tests/test_ua_setup.py
def test_render_server_snippet_fills_placeholders():
    setup = {"server": {
        "command": "uv",
        "args": ["--directory", "{ua_mcp_dir}", "run", "server.py"],
        "env": {"PROJECT_ROOTS": "{project_root}"},
    }}
    snip = ua_setup.render_server_snippet(
        setup, server_key="understand-anything",
        ua_mcp_dir="/srv/ua-mcp", project_root="/proj",
    )
    server = snip["mcpServers"]["understand-anything"]
    assert server["command"] == "uv"
    assert server["args"] == ["--directory", "/srv/ua-mcp", "run", "server.py"]
    assert server["env"] == {"PROJECT_ROOTS": "/proj"}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `/usr/bin/python3 -m pytest cli/tests/test_ua_setup.py::test_render_server_snippet_fills_placeholders -q`
Expected: FAIL with `AttributeError: module 'cli.mcp.ua_setup' has no attribute 'render_server_snippet'`.

- [ ] **Step 3: Add `render_server_snippet`**

```python
# append to cli/mcp/ua_setup.py
def render_server_snippet(setup: dict, *, server_key: str, ua_mcp_dir: str,
                          project_root: str) -> dict:
    """Build the mcpServers dict for the capability's `server` recipe."""
    server = setup["server"]
    args = [expand(a, ua_mcp_dir=ua_mcp_dir, project_root=project_root) for a in server["args"]]
    env = {
        k: expand(v, ua_mcp_dir=ua_mcp_dir, project_root=project_root)
        for k, v in (server.get("env") or {}).items()
    }
    return {"mcpServers": {server_key: {"command": server["command"], "args": args, "env": env}}}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `/usr/bin/python3 -m pytest cli/tests/test_ua_setup.py -q`
Expected: PASS (6 passed).

- [ ] **Step 5: Commit**

```bash
git add cli/mcp/ua_setup.py cli/tests/test_ua_setup.py
git commit -m "feat(cli): ua_setup render_server_snippet"
```

---

## Task 4: `ua_setup.render_mcp_setup_md`

**Files:**
- Modify: `cli/mcp/ua_setup.py`
- Test: `cli/tests/test_ua_setup.py`

- [ ] **Step 1: Write the failing test**

```python
# append to cli/tests/test_ua_setup.py
def _full_setup():
    return {
        "graph_artifacts": [
            {"name": "code", "path": ".understand-anything/knowledge-graph.json", "gen_cmd": "/understand"},
            {"name": "domain", "path": ".understand-anything/domain-graph.json", "gen_cmd": "/understand-domain"},
        ],
        "install_hint": {
            "claude-code": "/plugin install understand-anything",
            "default": "curl ... bash -s {platform}",
        },
        "server": {
            "command": "uv",
            "args": ["--directory", "{ua_mcp_dir}", "run", "server.py"],
            "env": {"PROJECT_ROOTS": "{project_root}"},
        },
    }


def test_render_mcp_setup_md_codex():
    md = ua_setup.render_mcp_setup_md(
        _full_setup(), server_key="understand-anything", platform="codex",
        ua_mcp_dir="/srv/ua-mcp", project_root="/proj",
    )
    assert "bash -s codex" in md          # install hint, platform-expanded
    assert "/understand" in md and "/understand-domain" in md   # both gen cmds
    assert '"PROJECT_ROOTS": "/proj"' in md                     # snippet rendered
    assert "/srv/ua-mcp" in md


def test_render_mcp_setup_md_claude_uses_platform_hint():
    md = ua_setup.render_mcp_setup_md(
        _full_setup(), server_key="understand-anything", platform="claude-code",
        ua_mcp_dir="<PATH_TO_Understand-Anything-MCP>", project_root="/proj",
    )
    assert "/plugin install understand-anything" in md
    assert "<PATH_TO_Understand-Anything-MCP>" in md
```

- [ ] **Step 2: Run test to verify it fails**

Run: `/usr/bin/python3 -m pytest cli/tests/test_ua_setup.py -k render_mcp_setup_md -q`
Expected: FAIL with `AttributeError: ... has no attribute 'render_mcp_setup_md'`.

- [ ] **Step 3: Add `render_mcp_setup_md`**

```python
# append to cli/mcp/ua_setup.py
def render_mcp_setup_md(setup: dict, *, server_key: str, platform: str,
                        ua_mcp_dir: str, project_root: str) -> str:
    """Render the human-facing MCP_SETUP.md guide for one capability."""
    hint = setup.get("install_hint", {})
    install = expand(hint.get(platform) or hint.get("default", ""), platform=platform)
    gen_lines = "\n".join(
        f"Run: {a['gen_cmd']:<18} -> {a['path']} ({a['name']})"
        for a in setup.get("graph_artifacts", [])
    )
    snippet = render_server_snippet(
        setup, server_key=server_key, ua_mcp_dir=ua_mcp_dir, project_root=project_root,
    )
    body = json.dumps(snippet, indent=2, ensure_ascii=False)
    return (
        f"# MCP Setup — {server_key}\n\n"
        f"## 1. Install engine (if missing)\n{install}\n\n"
        f"## 2. Generate graphs\n{gen_lines}\n\n"
        f"## 3. Wire MCP server (paste into the {platform} MCP config)\n"
        f"```json\n{body}\n```\n\n"
        f"## 4. Verify\nmaika doctor mcp --target {project_root}\n"
    )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `/usr/bin/python3 -m pytest cli/tests/test_ua_setup.py -q`
Expected: PASS (8 passed).

- [ ] **Step 5: Commit**

```bash
git add cli/mcp/ua_setup.py cli/tests/test_ua_setup.py
git commit -m "feat(cli): ua_setup render_mcp_setup_md guide"
```

---

## Task 5: `ua_setup.graph_status_lines`

**Files:**
- Modify: `cli/mcp/ua_setup.py`
- Test: `cli/tests/test_ua_setup.py`

- [ ] **Step 1: Write the failing test**

```python
# append to cli/tests/test_ua_setup.py
import json as _json


def test_graph_status_lines(tmp_path):
    setup = {"graph_artifacts": [
        {"name": "code", "path": ".understand-anything/knowledge-graph.json", "gen_cmd": "/understand"},
        {"name": "domain", "path": ".understand-anything/domain-graph.json", "gen_cmd": "/understand-domain"},
    ]}
    ua = tmp_path / ".understand-anything"
    ua.mkdir()
    (ua / "knowledge-graph.json").write_text(_json.dumps({"nodes": [1, 2, 3], "edges": [1, 2]}))
    # domain-graph.json intentionally missing
    lines = ua_setup.graph_status_lines(setup, tmp_path)
    assert lines[0] == "code: nodes=3 edges=2"
    assert lines[1] == "domain: ✗ run /understand-domain"


def test_graph_status_lines_unparseable(tmp_path):
    setup = {"graph_artifacts": [
        {"name": "code", "path": ".understand-anything/knowledge-graph.json", "gen_cmd": "/understand"},
    ]}
    ua = tmp_path / ".understand-anything"
    ua.mkdir()
    (ua / "knowledge-graph.json").write_text("{not json")
    assert ua_setup.graph_status_lines(setup, tmp_path) == ["code: present (unparseable)"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `/usr/bin/python3 -m pytest cli/tests/test_ua_setup.py -k graph_status -q`
Expected: FAIL with `AttributeError: ... has no attribute 'graph_status_lines'`.

- [ ] **Step 3: Add `graph_status_lines`**

```python
# append to cli/mcp/ua_setup.py
def graph_status_lines(setup: dict, target: Path) -> list:
    """One report line per graph artifact: nodes/edges, missing, or unparseable."""
    lines = []
    for art in setup.get("graph_artifacts", []):
        path = target / art["path"]
        if not path.exists():
            lines.append(f"{art['name']}: ✗ run {art['gen_cmd']}")
            continue
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            nodes = len(data.get("nodes") or [])
            edges = len(data.get("edges") or [])
            lines.append(f"{art['name']}: nodes={nodes} edges={edges}")
        except (json.JSONDecodeError, OSError):
            lines.append(f"{art['name']}: present (unparseable)")
    return lines
```

- [ ] **Step 4: Run test to verify it passes**

Run: `/usr/bin/python3 -m pytest cli/tests/test_ua_setup.py -q`
Expected: PASS (10 passed).

- [ ] **Step 5: Commit**

```bash
git add cli/mcp/ua_setup.py cli/tests/test_ua_setup.py
git commit -m "feat(cli): ua_setup graph_status_lines"
```

---

## Task 6: init — resolve `ua_mcp_dir` (+ `--ua-mcp-dir` flag)

**Files:**
- Modify: `cli/maika.py:42-77` (init subparser) and `cli/maika.py:156-168` (dispatch)
- Modify: `cli/commands/init.py` (add `resolve_ua_mcp_dir`, thread through `run_init`)
- Test: `cli/tests/test_init.py`

- [ ] **Step 1: Write the failing test**

```python
# append to cli/tests/test_init.py
from cli.commands.init import resolve_ua_mcp_dir

UA_PLACEHOLDER = "<PATH_TO_Understand-Anything-MCP>"


def test_resolve_ua_mcp_dir_uses_flag():
    assert resolve_ua_mcp_dir(["understand-anything"], "/srv/ua", assume_yes=True) == "/srv/ua"


def test_resolve_ua_mcp_dir_placeholder_when_yes_and_missing():
    assert resolve_ua_mcp_dir(["understand-anything"], None, assume_yes=True) == UA_PLACEHOLDER


def test_resolve_ua_mcp_dir_blank_when_ua_not_selected():
    assert resolve_ua_mcp_dir(["socraticode"], None, assume_yes=True) == ""
```

- [ ] **Step 2: Run test to verify it fails**

Run: `/usr/bin/python3 -m pytest cli/tests/test_init.py -k resolve_ua_mcp_dir -q`
Expected: FAIL with `ImportError: cannot import name 'resolve_ua_mcp_dir'`.

- [ ] **Step 3: Add `resolve_ua_mcp_dir` and thread `ua_mcp_dir` through `run_init`**

In `cli/commands/init.py`, add the helper above `run_init`:

```python
UA_MCP_KEY = "understand-anything"
UA_MCP_PLACEHOLDER = "<PATH_TO_Understand-Anything-MCP>"


def resolve_ua_mcp_dir(selected_mcps, ua_mcp_dir, assume_yes: bool) -> str:
    """Resolve the Understand-Anything-MCP clone dir: flag > prompt > placeholder.
    Returns '' when UA is not selected."""
    if UA_MCP_KEY not in selected_mcps:
        return ""
    if ua_mcp_dir:
        return ua_mcp_dir
    if assume_yes:
        return UA_MCP_PLACEHOLDER
    raw = input(
        "\nĐường dẫn tuyệt đối tới clone Understand-Anything-MCP "
        "(Enter để chèn placeholder): "
    ).strip()
    return raw or UA_MCP_PLACEHOLDER
```

Change the `run_init` signature to accept `ua_mcp_dir` and resolve it after choices:

```python
def run_init(
    target_dir: str,
    maika_root: Optional[str] = None,
    platform_key: Optional[str] = None,
    selected_mcps: Optional[List[str]] = None,
    language: Optional[str] = None,
    assume_yes: bool = False,
    ua_mcp_dir: Optional[str] = None,
) -> None:
```

Immediately after the `resolve_init_choices(...)` call inside `run_init`, add:

```python
    ua_dir = resolve_ua_mcp_dir(selected_mcps, ua_mcp_dir, assume_yes)
```

In `cli/maika.py`, add to the init subparser (after the `--yes` argument, around line 77):

```python
    init_parser.add_argument(
        "--ua-mcp-dir",
        default=None,
        help="Absolute path to the Understand-Anything-MCP clone (when understand-anything is selected)",
    )
```

And in the `init` dispatch branch (around line 161), pass it through:

```python
        run_init(
            target_dir=args.target,
            maika_root=args.source,
            platform_key=args.platform,
            selected_mcps=selected_mcps,
            language=args.language,
            assume_yes=args.yes,
            ua_mcp_dir=args.ua_mcp_dir,
        )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `/usr/bin/python3 -m pytest cli/tests/test_init.py -k resolve_ua_mcp_dir -q`
Expected: PASS (3 passed).

- [ ] **Step 5: Commit**

```bash
git add cli/maika.py cli/commands/init.py cli/tests/test_init.py
git commit -m "feat(cli): resolve ua_mcp_dir for init (flag/prompt/placeholder)"
```

---

## Task 7: init — emit `MCP_SETUP.md` + extend Next steps

**Files:**
- Modify: `cli/commands/init.py` (`run_init`, after `generate_resolved_config`)
- Test: `cli/tests/test_init.py`

- [ ] **Step 1: Write the failing test**

```python
# append to cli/tests/test_init.py
from pathlib import Path
from cli.commands.init import run_init

MAIKA_ROOT = Path(__file__).resolve().parent.parent.parent


def test_init_emits_mcp_setup_when_ua_selected(tmp_path):
    run_init(
        target_dir=str(tmp_path), maika_root=str(MAIKA_ROOT),
        platform_key="codex", selected_mcps=["understand-anything"],
        language="python", assume_yes=True, ua_mcp_dir="/srv/ua-mcp",
    )
    setup_md = tmp_path / ".maika" / "MCP_SETUP.md"
    assert setup_md.exists()
    text = setup_md.read_text(encoding="utf-8")
    assert "/srv/ua-mcp" in text
    assert "/understand-domain" in text


def test_init_no_mcp_setup_when_ua_not_selected(tmp_path):
    run_init(
        target_dir=str(tmp_path), maika_root=str(MAIKA_ROOT),
        platform_key="codex", selected_mcps=[],
        language="python", assume_yes=True,
    )
    assert not (tmp_path / ".maika" / "MCP_SETUP.md").exists()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `/usr/bin/python3 -m pytest cli/tests/test_init.py -k mcp_setup -q`
Expected: FAIL — `MCP_SETUP.md` does not exist.

- [ ] **Step 3: Emit `MCP_SETUP.md` in `run_init`**

At the top of `cli/commands/init.py`, extend imports:

```python
from cli.mcp import ua_setup
```

In `run_init`, immediately after `generate_resolved_config(target, platform, selected_mcps, language)`:

```python
    mcp_caps = manifest.get("mcp_capabilities", {})
    for mcp_key in selected_mcps:
        capability = mcp_caps.get(mcp_key, {})
        if not ua_setup.has_setup(capability):
            continue
        dir_value = ua_dir if mcp_key == UA_MCP_KEY else UA_MCP_PLACEHOLDER
        setup_md = ua_setup.render_mcp_setup_md(
            capability["setup"], server_key=mcp_key, platform=platform_key,
            ua_mcp_dir=dir_value, project_root=str(target),
        )
        setup_path = target / platform.framework_root / "MCP_SETUP.md"
        setup_path.write_text(setup_md, encoding="utf-8")
```

Then extend the "Next steps" block — after the existing `if selected_mcps:` print, add:

```python
    if UA_MCP_KEY in selected_mcps:
        print(f"  5. Wire Understand-Anything: see {platform.framework_root}/MCP_SETUP.md\n")
```

- [ ] **Step 4: Run test to verify it passes**

Run: `/usr/bin/python3 -m pytest cli/tests/test_init.py -k mcp_setup -q`
Expected: PASS (2 passed).

- [ ] **Step 5: Run the full init test file (regression)**

Run: `/usr/bin/python3 -m pytest cli/tests/test_init.py -q`
Expected: PASS (all).

- [ ] **Step 6: Commit**

```bash
git add cli/commands/init.py cli/tests/test_init.py
git commit -m "feat(cli): init emits MCP_SETUP.md for setup-bearing MCPs"
```

---

## Task 8: doctor — engine + graph verify (3-tier) with manifest load

**Files:**
- Modify: `cli/mcp/doctor.py` (`DoctorStatus`, `build_doctor_status`, `render_report`)
- Modify: `cli/commands/doctor.py` (`run_doctor_mcp` passes `maika_root`)
- Test: `cli/tests/test_mcp_doctor.py`

- [ ] **Step 1: Write the failing test**

```python
# append to cli/tests/test_mcp_doctor.py
import json
from pathlib import Path
from cli.commands.init import run_init
from cli.mcp.doctor import build_doctor_status, render_report

MAIKA_ROOT = Path(__file__).resolve().parent.parent.parent


def _init_ua(tmp_path, home):
    run_init(
        target_dir=str(tmp_path), maika_root=str(MAIKA_ROOT),
        platform_key="codex", selected_mcps=["understand-anything"],
        language="python", assume_yes=True, ua_mcp_dir="/srv/ua-mcp",
    )


def test_doctor_reports_engine_and_graphs(tmp_path):
    home = tmp_path / "home"
    home.mkdir()
    _init_ua(tmp_path, home)
    # engine marker (codex) present
    (home / ".agents" / "skills").mkdir(parents=True)
    (home / ".agents" / "skills" / "understand").write_text("x")
    # code graph present, domain graph missing
    ua = tmp_path / ".understand-anything"
    ua.mkdir()
    (ua / "knowledge-graph.json").write_text(json.dumps({"nodes": [1, 2], "edges": [1]}))

    status = build_doctor_status(tmp_path, home, maika_root=MAIKA_ROOT)
    report = render_report(status)
    assert "engine: ✓ installed" in report
    assert "code: nodes=2 edges=1" in report
    assert "domain: ✗ run /understand-domain" in report


def test_doctor_regression_no_ua(tmp_path):
    home = tmp_path / "home"
    home.mkdir()
    run_init(
        target_dir=str(tmp_path), maika_root=str(MAIKA_ROOT),
        platform_key="codex", selected_mcps=[], language="python", assume_yes=True,
    )
    status = build_doctor_status(tmp_path, home, maika_root=MAIKA_ROOT)
    assert status.setup_reports == {}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `/usr/bin/python3 -m pytest cli/tests/test_mcp_doctor.py -k "engine_and_graphs or regression_no_ua" -q`
Expected: FAIL with `TypeError: build_doctor_status() got an unexpected keyword argument 'maika_root'`.

- [ ] **Step 3: Extend `DoctorStatus` + `build_doctor_status` + `render_report`**

In `cli/mcp/doctor.py`, add the import and a field:

```python
from cli.scaffold import load_resolved_config, load_manifest
from cli.mcp import ua_setup
```

Add to the `DoctorStatus` dataclass (after `redacted_servers`):

```python
    setup_reports: dict = field(default_factory=dict)
```

Add this helper above `build_doctor_status`:

```python
def _setup_reports(target: Path, home: Path, maika_root, platform: str,
                   selected: list, matched: list) -> dict:
    if maika_root is None:
        return {}
    manifest = load_manifest(Path(maika_root))
    caps = manifest.get("mcp_capabilities", {})
    reports = {}
    for key in selected:
        capability = caps.get(key, {})
        if not ua_setup.has_setup(capability):
            continue
        setup = capability["setup"]
        wired = "wired: ✓ configured" if key in matched else "wired: ✗ see MCP_SETUP.md"
        reports[key] = (
            [ua_setup.engine_status_line(setup, platform, home)]
            + ua_setup.graph_status_lines(setup, target)
            + [wired]
        )
    return reports
```

Change the `build_doctor_status` signature to accept `maika_root=None`:

```python
def build_doctor_status(target: Path, home: Path, maika_root=None) -> DoctorStatus:
```

In the early-return branch (when `best_config is None`), add `setup_reports` computed with `matched=[]`:

```python
    if best_config is None:
        return DoctorStatus(
            platform=platform,
            framework_root=framework_root,
            selected_mcps=selected,
            config_path=None,
            native_state="unavailable",
            matched=[],
            missing=selected,
            bridge_state="not-probed",
            recommendation="create or link a valid MCP config with maika doctor mcp --fix",
            setup_reports=_setup_reports(target, home, maika_root, platform, selected, []),
        )
```

In the final return, add the same field with the real `matched`:

```python
    return DoctorStatus(
        platform=platform,
        framework_root=framework_root,
        selected_mcps=selected,
        config_path=best_config.path,
        native_state=native_state,
        matched=matched,
        missing=missing,
        bridge_state=bridge_state,
        recommendation="run native MCP in the IDE/CLI and inspect tool availability",
        redacted_servers=redacted_servers,
        setup_reports=_setup_reports(target, home, maika_root, platform, selected, matched),
    )
```

In `render_report`, append a setup section before the matched-config block. Change the return to:

```python
    return (
        "# MCP Doctor Report\n\n"
        f"- Platform: {status.platform}\n"
        f"- Framework root: {status.framework_root}\n"
        f"- Selected MCPs: {selected}\n"
        f"- Config path: {config_path}\n"
        f"- native: {status.native_state}\n"
        f"- bridge: {status.bridge_state}\n"
        f"- matched: {matched}\n"
        f"- missing: {missing}\n"
        f"- Recommendation: {status.recommendation}\n"
        + _render_setup_reports(status.setup_reports)
        + _render_matched_config(status.redacted_servers)
    )
```

Add the renderer helper:

```python
def _render_setup_reports(setup_reports: dict) -> str:
    if not setup_reports:
        return ""
    out = ["\n## Setup verification\n"]
    for key, lines in setup_reports.items():
        out.append(f"\n### {key}\n")
        out.extend(f"- {line}\n" for line in lines)
    return "".join(out)
```

In `cli/commands/doctor.py`, auto-detect `maika_root` and pass it to both `build_doctor_status` calls:

```python
def run_doctor_mcp(
    target_dir: str,
    fix: bool = False,
    assume_yes: bool = False,
    home: Optional[Path] = None,
) -> None:
    target = Path(target_dir).resolve()
    home_path = home or Path.home()
    maika_root = Path(__file__).resolve().parent.parent.parent
    try:
        status = build_doctor_status(target, home_path, maika_root=maika_root)
    except ValueError as exc:
        print(f"\n  {exc}")
        print("  Run `maika init` first, or point --target at an Maika project.")
        return
    report = write_report(target, status)
    print(f"\n  MCP doctor report: {report}")
    print(f"  native: {status.native_state} | bridge: {status.bridge_state}")
    if fix:
        fixed = apply_fix(target, home_path, assume_yes)
        if fixed is None:
            print("  no safe automatic fix available")
        else:
            print(f"  fixed config: {fixed}")
            status = build_doctor_status(target, home_path, maika_root=maika_root)
            report = write_report(target, status)
            print(f"  refreshed report: {report}")
```

- [ ] **Step 4: Run test to verify it passes**

Run: `/usr/bin/python3 -m pytest cli/tests/test_mcp_doctor.py -q`
Expected: PASS (all, including the 2 new).

- [ ] **Step 5: Commit**

```bash
git add cli/mcp/doctor.py cli/commands/doctor.py cli/tests/test_mcp_doctor.py
git commit -m "feat(cli): doctor mcp verifies engine + both UA graphs"
```

---

## Task 9: Full suite + snapshot refresh

**Files:**
- Possibly Modify: `cli/tests/test_snapshots.py` fixtures (if init output snapshots changed)

- [ ] **Step 1: Run the whole CLI suite**

Run: `/usr/bin/python3 -m pytest cli/ -q`
Expected: PASS. If `test_snapshots.py` fails because the resolved scaffold tree changed, inspect the diff — the only intended change is the new `MCP_SETUP.md` under selected-UA snapshots and the manifest `setup` block.

- [ ] **Step 2: If a snapshot legitimately changed, update it**

Inspect first: `/usr/bin/python3 -m pytest cli/tests/test_snapshots.py -q`. Only regenerate the snapshot if the diff is exactly the intended `setup`/`MCP_SETUP.md` addition (follow the regeneration mechanism already documented in `test_snapshots.py`). Do not blanket-accept.

- [ ] **Step 3: Commit (only if snapshots changed)**

```bash
git add cli/tests/test_snapshots.py cli/tests/__snapshots__ 2>/dev/null
git commit -m "test(cli): refresh snapshots for UA setup block"
```

---

## Self-Review notes

- **Spec coverage:** §4.1 manifest → Task 1; §4.2 ua_mcp_dir + emit → Tasks 6-7; §4.3 Next steps → Task 7; §4.5 doctor 3-tier (engine/2 graphs/wired) → Tasks 2,5,8; §6 degrade (placeholder, missing/unparseable graph, missing registry) → Tasks 4,5,6; §7 platform matrix → Task 1 manifest + Task 2 tests; §9 testing items → Tasks 1-8.
- **Out of scope (spec §10):** `update --reconfigure` re-emitting `MCP_SETUP.md` is NOT covered here (init-only); flag if needed as a follow-up.
- **Type consistency:** `ua_setup` public API — `expand`, `has_setup`, `resolve_engine_check`, `engine_status_line`, `render_server_snippet`, `render_mcp_setup_md`, `graph_status_lines` — used with identical signatures in Tasks 6-8. `DoctorStatus.setup_reports: dict[str, list[str]]`. `UA_MCP_KEY = "understand-anything"`, `UA_MCP_PLACEHOLDER = "<PATH_TO_Understand-Anything-MCP>"`.
