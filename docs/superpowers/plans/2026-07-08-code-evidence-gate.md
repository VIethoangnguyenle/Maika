# code-evidence Gate Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Evolve the `grep-honesty` gate into a positive `code-evidence` gate that blocks silent grep (B) and fabricated cbm nodes (C), not just confessed grep excuses (A), by requiring every section-scoped code-fact about an indexed-project file to carry a `node_id` that cbm verifies exists.

**Architecture:** Deterministic pure validator in `gates.py` + impure cbm probe in `capability.py`; the CLI caller runs the probe and passes results into the pure validator (mirrors the existing `--index` pattern). Runs on `EXPLORE_CONTEXT.md` §2.2/§2.3/§4.

**Tech Stack:** Python 3.12, pytest (`/usr/bin/python3 -m pytest`), `codebase-memory-mcp` CLI (`get_code_snippet`, `list_projects`).

**Branch:** Build on `feat/grep-honesty-gate` (PR #36). This supersedes the confessed-only `grep-honesty` gate, so we evolve it in place rather than merging a soon-obsolete slice.

**Spec:** `docs/superpowers/specs/2026-07-08-code-evidence-gate-design.md`

---

## File Structure

- `.maika/tools/gate-check/capability.py` — add `_parse_snippet`, `verify_nodes` (impure cbm node probe). Keeps `_parse_list_projects`, `cbm_indexed_projects`, `indexed_projects`.
- `.maika/tools/gate-check/gates.py` — add pure helpers `_section`, `_parse_node_table`, `_section_files`, `_CBM_ERROR`; add `validate_code_evidence`; delete `validate_grep_honesty` (+ its `_GREP_DEGRADE` if unused elsewhere; keep `_FILE_PATH`, `_under`).
- `.maika/tools/gate-check/cli.py` — rename gate `grep-honesty` → `code-evidence`; wire the node probe.
- `.maika/tools/gate-check/tests/test_capability.py` — add `verify_nodes` parse test.
- `.maika/tools/gate-check/tests/test_code_evidence.py` — new; replaces `test_grep_honesty.py` (delete the latter).
- `.maika/rules/rules-tool.md` — update the R-Tool-5 reference from `grep-honesty` to `code-evidence`.

---

## Task 1: cbm node-verification probe (`capability.py`)

**Files:**
- Modify: `.maika/tools/gate-check/capability.py`
- Test: `.maika/tools/gate-check/tests/test_capability.py`

- [ ] **Step 1: Write the failing test** — append to `tests/test_capability.py`:

```python
def test_parse_snippet_real_node():
    out = (
        "level=info msg=x\n"
        '{"name":"scaffold_plugin","qualified_name":"proj.cli.scaffold.scaffold_plugin",'
        '"file_path":"/abs/cli/scaffold.py","start_line":167}\n'
    )
    d = cap._parse_snippet(out)
    assert d["qualified_name"] == "proj.cli.scaffold.scaffold_plugin"
    assert d["file_path"] == "/abs/cli/scaffold.py"


def test_parse_snippet_fabricated_returns_none():
    # cbm prints nothing (or a non-JSON log line) for a nonexistent node.
    assert cap._parse_snippet("level=info msg=x\n") is None
```

- [ ] **Step 2: Run to verify it fails**

Run: `cd .maika/tools/gate-check && /usr/bin/python3 -m pytest tests/test_capability.py -q`
Expected: FAIL — `AttributeError: module 'capability' has no attribute '_parse_snippet'`

- [ ] **Step 3: Implement `_parse_snippet` + `verify_nodes`** — append to `capability.py`:

```python
def _parse_snippet(stdout: str):
    """Last JSON object line from `get_code_snippet` output, or None."""
    for line in reversed(stdout.splitlines()):
        s = line.strip()
        if not s.startswith("{"):
            continue
        try:
            return json.loads(s)
        except json.JSONDecodeError:
            continue
    return None


def verify_nodes(node_ids, timeout: int = 8):
    """Verify each node_id (a cbm qualified_name) exists in cbm's graph.

    Returns (verified, ok). verified = {node_id: file_path(abs)} for nodes that
    exist. ok=False if the cbm binary is absent / a probe raises (caller then
    fail-opens only with an embedded real cbm error). The project for each node
    is its qualified_name prefix (path→'-' names contain no dots)."""
    verified = {}
    for nid in node_ids:
        project = nid.split(".", 1)[0]
        try:
            proc = subprocess.run(
                ["codebase-memory-mcp", "cli", "get_code_snippet",
                 json.dumps({"project": project, "qualified_name": nid})],
                capture_output=True, text=True, timeout=timeout,
            )
        except (OSError, subprocess.SubprocessError):
            return {}, False
        d = _parse_snippet(proc.stdout)
        if d and d.get("qualified_name") == nid and d.get("file_path"):
            verified[nid] = d["file_path"]
    return verified, True
```

- [ ] **Step 4: Run to verify it passes**

Run: `cd .maika/tools/gate-check && /usr/bin/python3 -m pytest tests/test_capability.py -q`
Expected: PASS (all capability tests)

- [ ] **Step 5: Commit**

```bash
git add .maika/tools/gate-check/capability.py .maika/tools/gate-check/tests/test_capability.py
git commit -m "feat(gate-check): add cbm node-verification probe (verify_nodes)"
```

---

## Task 2: pure section/table parsers (`gates.py`)

**Files:**
- Modify: `.maika/tools/gate-check/gates.py`
- Test: `.maika/tools/gate-check/tests/test_code_evidence.py` (new)

- [ ] **Step 1: Write the failing test** — create `tests/test_code_evidence.py`:

```python
import importlib.util
from pathlib import Path

MOD = Path(__file__).resolve().parents[1] / "gates.py"
spec = importlib.util.spec_from_file_location("gates", MOD)
g = importlib.util.module_from_spec(spec)
spec.loader.exec_module(g)


def test_parse_node_table_extracts_node_ids():
    text = (
        "### 2.3 Key Components\n"
        "| Component | node_id | Vai trò |\n"
        "|-----------|---------|---------|\n"
        "| capabilities | proj.cli.base.BasePlatform.capabilities | handler |\n"
        "| scaffold | proj.cli.scaffold.scaffold_plugin | builder |\n"
        "\n---\n## 3. Enum\n| x | proj.other.node | y |\n"
    )
    assert g._parse_node_table(text) == [
        "proj.cli.base.BasePlatform.capabilities",
        "proj.cli.scaffold.scaffold_plugin",
    ]  # stops at §3; skips header/separator


def test_parse_node_table_skips_placeholder_rows():
    text = "### 2.3 Key Components\n| Component | node_id | Vai trò |\n| ... | ... | ... |\n"
    assert g._parse_node_table(text) == []


def test_section_files_collects_only_named_sections():
    text = (
        "## 2.2 Entry Points\n| H | C | Path |\n| h | c | cli/a.py |\n"
        "## 3. Enum\nunrelated cli/z.py\n"
        "## 4. Phát hiện\nfound in cli/b.py:10\n"
    )
    got = g._section_files(text, ("Entry Points", "Phát hiện"))
    assert got == {"cli/a.py", "cli/b.py"}  # §3 not scanned
```

- [ ] **Step 2: Run to verify it fails**

Run: `cd .maika/tools/gate-check && /usr/bin/python3 -m pytest tests/test_code_evidence.py -q`
Expected: FAIL — `AttributeError: module 'gates' has no attribute '_parse_node_table'`

- [ ] **Step 3: Implement the parsers** — add to `gates.py` (after `_FILE_PATH` / `_under`, before `validate_memory_recall`):

```python
_CBM_ERROR = re.compile(
    r"project is required|no projects indexed|not indexed|connection refused|"
    r"index_status|ECONNREFUSED|codebase-memory-mcp.*error",
    re.IGNORECASE,
)


def _section(text: str, needle: str) -> str:
    """Body under the first heading (## / ### / ####) containing needle,
    up to the next heading. Case-insensitive substring match on the heading."""
    out, collecting = [], False
    for line in text.splitlines():
        s = line.strip()
        if re.match(r"^#{2,4}\s", s):
            if collecting:
                break
            collecting = needle.lower() in s.lower()
            continue
        if collecting:
            out.append(line)
    return "\n".join(out)


def _parse_node_table(text: str):
    """node_id (2nd column) of each real row in the §2.3 Key Components table."""
    ids = []
    for line in _section(text, "Key Components").splitlines():
        line = line.strip()
        if not line.startswith("|"):
            continue
        cells = [c.strip() for c in line.strip("|").split("|")]
        if len(cells) < 2:
            continue
        nid = cells[1]
        if not nid or nid == "node_id" or nid == "..." or set(nid) <= set("-"):
            continue
        ids.append(nid)
    return ids


def _section_files(text: str, needles):
    files = set()
    for needle in needles:
        files.update(_FILE_PATH.findall(_section(text, needle)))
    return files
```

- [ ] **Step 4: Run to verify it passes**

Run: `cd .maika/tools/gate-check && /usr/bin/python3 -m pytest tests/test_code_evidence.py -q`
Expected: PASS (3 parser tests)

- [ ] **Step 5: Commit**

```bash
git add .maika/tools/gate-check/gates.py .maika/tools/gate-check/tests/test_code_evidence.py
git commit -m "feat(gate-check): pure section/node-table parsers for code-evidence"
```

---

## Task 3: `validate_code_evidence` validator (`gates.py`)

**Files:**
- Modify: `.maika/tools/gate-check/gates.py` (add `validate_code_evidence`; delete `validate_grep_honesty`)
- Test: `.maika/tools/gate-check/tests/test_code_evidence.py`

- [ ] **Step 1: Write the failing test** — append to `tests/test_code_evidence.py`:

```python
IDX = [{"name": "proj", "root_path": "/repo"}]
# §2.3 with one node; verified map says that node exists at /repo/cli/base.py
NODE = "proj.cli.base.BasePlatform.capabilities"
V = {NODE: "/repo/cli/base.py"}


def _art(node_row="", section4="", entry_path=""):
    return (
        "## 2.2 Entry Points\n| H | C | Path |\n" + (f"| h | c | {entry_path} |\n" if entry_path else "")
        + "### 2.3 Key Components\n| Component | node_id | Vai trò |\n"
        + (node_row + "\n" if node_row else "")
        + "## 4. Phát hiện\n" + (section4 + "\n" if section4 else "")
    )


def test_C_fabricated_node_fails():
    art = _art(node_row=f"| cap | {NODE} | h |")
    res = g.validate_code_evidence(art, indexed_projects=IDX, verified_node_files={}, repo_root="/repo", probe_ok=True)
    assert res.ok is False and "not found in cbm graph" in res.reason


def test_B_silent_grep_indexed_file_without_node_fails():
    art = _art(section4="found handler in cli/base.py:100")  # §2.3 empty, §4 names an indexed file
    res = g.validate_code_evidence(art, indexed_projects=IDX, verified_node_files={}, repo_root="/repo", probe_ok=True)
    assert res.ok is False and "no verified" in res.reason.lower()


def test_pass_verified_node_covers_finding():
    art = _art(node_row=f"| cap | {NODE} | h |", section4="handler in cli/base.py:100")
    res = g.validate_code_evidence(art, indexed_projects=IDX, verified_node_files=V, repo_root="/repo", probe_ok=True)
    assert res.ok is True


def test_unindexed_file_in_finding_passes():
    art = _art(section4="seen in /other/x.py:7")  # not under /repo
    res = g.validate_code_evidence(art, indexed_projects=IDX, verified_node_files={}, repo_root="/repo", probe_ok=True)
    assert res.ok is True


def test_no_indexed_projects_passes():
    art = _art(section4="found in cli/base.py:100")
    res = g.validate_code_evidence(art, indexed_projects=[], verified_node_files={}, repo_root="/repo", probe_ok=True)
    assert res.ok is True


def test_probe_fail_needs_embedded_cbm_error():
    art = _art(section4="found in cli/base.py:100") + "\ncbm down\n"
    assert g.validate_code_evidence(art, indexed_projects=IDX, verified_node_files={}, repo_root="/repo", probe_ok=False).ok is False
    art2 = _art(section4="found in cli/base.py:100") + '\nprobe error: "project is required"\n'
    assert g.validate_code_evidence(art2, indexed_projects=IDX, verified_node_files={}, repo_root="/repo", probe_ok=False).ok is True
```

- [ ] **Step 2: Run to verify it fails**

Run: `cd .maika/tools/gate-check && /usr/bin/python3 -m pytest tests/test_code_evidence.py -q`
Expected: FAIL — `AttributeError: module 'gates' has no attribute 'validate_code_evidence'`

- [ ] **Step 3: Implement the validator** — add to `gates.py`, and DELETE `validate_grep_honesty` (and its `_GREP_DEGRADE` regex, now unused):

```python
def _abs(path: str, repo_root):
    return path if path.startswith("/") else (os.path.join(repo_root, path) if repo_root else path)


def _project_for(path, indexed_projects):
    for proj in indexed_projects:
        if _under(path, proj["root_path"]):
            return proj
    return None


def validate_code_evidence(text, indexed_projects=None, verified_node_files=None,
                           repo_root=None, probe_ok=True) -> Result:
    """Positive code-evidence gate (see R-Tool-5). Every section-scoped (§2.2/§2.3/§4)
    code-fact about a file in an indexed project must be backed by a §2.3 node_id that
    cbm verifies exists. Catches confessed grep (A), silent grep (B), fabricated node (C)."""
    verified_node_files = verified_node_files or {}
    if not indexed_projects:
        return Result(True)                      # nothing indexed → grep legit
    if not probe_ok:                             # cbm probe failed → fail-open only with real error
        if _CBM_ERROR.search(text):
            return Result(True)
        return Result(False, "cbm probe failed; embed the real cbm error output to justify degrade")
    for nid in _parse_node_table(text):          # (C) every §2.3 node must exist
        if nid not in verified_node_files:
            return Result(False, f"§2.3 node_id '{nid}' not found in cbm graph (fabricated or wrong project)")
    verified_abs = {os.path.normpath(_abs(f, repo_root)) for f in verified_node_files.values()}
    for raw in _section_files(text, ("Entry Points", "Phát hiện")):   # (B) indexed-file facts need a node
        path = os.path.normpath(_abs(raw, repo_root))
        proj = _project_for(path, indexed_projects)
        if not proj:
            continue                             # un-indexed file → grep legit
        if path not in verified_abs:
            return Result(False, f"'{raw}' (indexed project '{proj['name']}') has no verified §2.3 node — trace via cbm, don't grep")
    return Result(True)
```

- [ ] **Step 4: Run to verify it passes**

Run: `cd .maika/tools/gate-check && /usr/bin/python3 -m pytest tests/test_code_evidence.py -q`
Expected: PASS (all 9 code_evidence tests)

- [ ] **Step 5: Commit**

```bash
git add .maika/tools/gate-check/gates.py .maika/tools/gate-check/tests/test_code_evidence.py
git commit -m "feat(gate-check): validate_code_evidence (require+verify), retire grep-honesty validator"
```

---

## Task 4: rename CLI gate + wire the probe (`cli.py`)

**Files:**
- Modify: `.maika/tools/gate-check/cli.py`
- Delete: `.maika/tools/gate-check/tests/test_grep_honesty.py`

- [ ] **Step 1: Delete the obsolete test file**

```bash
git rm .maika/tools/gate-check/tests/test_grep_honesty.py
```

- [ ] **Step 2: Rename the gate + wire node verification** in `cli.py`.

In `VALIDATORS`, replace the line `"grep-honesty": "validate_grep_honesty",` with:

```python
    "code-evidence": "validate_code_evidence",
```

Replace the `elif args.gate == "grep-honesty":` block with:

```python
    elif args.gate == "code-evidence":
        repo_root = args.repo_root or os.getcwd()
        cap = _load_module("capability")
        indexed = cap.indexed_projects(repo_root)
        gates_mod = _load_module("gates")
        node_ids = gates_mod._parse_node_table(text)
        verified, ok = cap.verify_nodes(node_ids)
        kwargs["indexed_projects"] = indexed
        kwargs["verified_node_files"] = verified
        kwargs["repo_root"] = repo_root
        kwargs["probe_ok"] = ok
```

- [ ] **Step 3: Run the full gate-check suite**

Run: `cd .maika/tools/gate-check && /usr/bin/python3 -m pytest -q`
Expected: PASS — no `grep_honesty` references remain; `code_evidence` + `capability` tests pass.

- [ ] **Step 4: End-to-end smoke against real cbm** (this repo is indexed as `home-zane-Desktop-agent-memory-arch-v3`):

```bash
cd /home/zane/Desktop/agent-memory-arch-v3
printf '### 2.3 Key Components\n| C | node_id | R |\n| cap | home-zane-Desktop-agent-memory-arch-v3.cli.scaffold.scaffold_plugin | b |\n## 4. Phát hiện\nlogic in cli/scaffold.py:167\n' > /tmp/ce_ok.md
/usr/bin/python3 .maika/tools/gate-check/cli.py code-evidence /tmp/ce_ok.md --repo-root "$PWD"; echo "exit=$? (expect 0/PASS)"
printf '### 2.3 Key Components\n| C | node_id | R |\n| f | home-zane-Desktop-agent-memory-arch-v3.cli.Fake.nope | b |\n' > /tmp/ce_bad.md
/usr/bin/python3 .maika/tools/gate-check/cli.py code-evidence /tmp/ce_bad.md --repo-root "$PWD"; echo "exit=$? (expect 1/FAIL fabricated)"
rm -f /tmp/ce_ok.md /tmp/ce_bad.md
```
Expected: first PASS (exit 0), second FAIL (exit 1, "not found in cbm graph").

- [ ] **Step 5: Commit**

```bash
git add .maika/tools/gate-check/cli.py    # test_grep_honesty.py deletion already staged by git rm in Step 1
git commit -m "feat(gate-check): rename gate grep-honesty->code-evidence, wire node probe"
```

---

## Task 5: update rule reference + R6 stamp (`rules-tool.md`)

**Files:**
- Modify: `.maika/rules/rules-tool.md`

- [ ] **Step 1: Update the R-Tool-5 reference.** Replace the bullet added for grep-honesty (the `- **grep-fallback là capability-aware…**` block ending with the `grep-honesty` Pass line) with:

```markdown
- **Code-fact BẮT BUỘC có node đã-verify (positive gate, không tự khai)**: mọi component/phát hiện
  ở §2.2/§2.3/§4 về file thuộc project đã-index phải có `node_id` ở §2.3 mà cbm xác nhận TỒN TẠI.
  grep không đẻ ra node graph hợp lệ; node bịa probe không ra. Enforce cơ học (probe cbm thật):
  `python3 {{ platform.framework_root }}/tools/gate-check/cli.py code-evidence <EXPLORE_CONTEXT> --repo-root <repo>` phải PASS.
  cbm down → chỉ hợp lệ khi nhúng output lỗi cbm thật.
```

- [ ] **Step 2: Verify no stale `grep-honesty` reference remains**

Run: `cd /home/zane/Desktop/agent-memory-arch-v3 && /usr/bin/grep -rn "grep-honesty" .maika/ || echo "clean"`
Expected: `clean`

- [ ] **Step 3: Commit**

```bash
git add .maika/rules/rules-tool.md
git commit -m "docs(rules): R-Tool-5 references code-evidence gate (supersedes grep-honesty framing)"
```

---

## Task 6: full-suite + snapshot regression

**Files:** none (verification only)

- [ ] **Step 1: Run the full repo suite**

Run: `cd /home/zane/Desktop/agent-memory-arch-v3 && /usr/bin/python3 -m pytest cli/tests/ .maika/tools/gate-check/ -q`
Expected: all pass (snapshots unchanged — no new *scaffolded* source file was added; `verify_nodes` lives in the existing `capability.py` already present in the snapshots from PR #36).

- [ ] **Step 2: If snapshot tests fail** (only if a new gate-check source file was inadvertently added), regenerate:

```bash
cd /home/zane/Desktop/agent-memory-arch-v3
/usr/bin/python3 - <<'PY'
import sys, tempfile
from pathlib import Path
ROOT="/home/zane/Desktop/agent-memory-arch-v3"; sys.path.insert(0, ROOT)
from cli.commands.init import run_init
def tree(r):
    return "\n".join(p.relative_to(r).as_posix()+("/" if p.is_dir() else "")
        for p in sorted(r.rglob("*"), key=lambda p: p.relative_to(r).parts) if "__pycache__" not in p.as_posix())+"\n"
OPTS={"antigravity":(["codebase-memory-mcp","confluence","db-remote"],"python"),"codex":(["codebase-memory-mcp","confluence","db-remote"],"python"),"claude-code":(["codebase-memory-mcp","confluence","db-remote"],"python"),"generic":([],"other")}
snap=Path(ROOT)/"cli"/"tests"/"snapshots"
for pk,(m,l) in OPTS.items():
    with tempfile.TemporaryDirectory() as td:
        t=Path(td)/"proj"; run_init(target_dir=str(t),maika_root=ROOT,platform_key=pk,selected_mcps=m,language=l,assume_yes=True)
        (snap/f"{pk}.txt").write_text(tree(t),encoding="utf-8")
PY
git diff --stat cli/tests/snapshots/   # confirm only intended additions
```
Then commit only if the diff is the intended new file(s).

- [ ] **Step 3: Push and confirm CI green**

```bash
git push
gh run watch "$(gh run list --branch feat/grep-honesty-gate --limit 1 --json databaseId -q '.[0].databaseId')" --exit-status
```
Expected: CI green (tests ubuntu + windows, install-ps1-e2e).

---

## Notes

- **PR #36** becomes the full `code-evidence` gate (title/body should be updated to reflect the positive gate, not "grep-honesty"). Do this after Task 6 passes.
- **Follow-ups (not in this plan):** apply the same node-verify to UA once UA graphs exist; wire the gate call into the exploration phase of `task.md` so it runs at runtime (currently referenced in R-Tool-5 + invokable via `decision-gate.md`).
