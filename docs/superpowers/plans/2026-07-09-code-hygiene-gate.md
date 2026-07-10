# Code-Hygiene Gate (Java import hygiene) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Compile bài học lặp lại "không import thừa" thành deterministic gate: `conventions.code_hygiene` → rule-projector (Checkstyle modules) → gate-check `code-hygiene` (pure Java-import parser trên changed files) → wire vào Pha 3 của `task.md`.

**Architecture:** Nối 3 seam có sẵn, không file/skill/tool mới. (1) Schema: section `code_hygiene` trong conventions (machine lane, như `naming_patterns`). (2) Projection: `projector.py` project section đó thành 3 IR rule mới; `backends/checkstyle.py` emit `UnusedImports`/`AvoidStarImport`/`RedundantImport`. (3) Gate: `gates.py::validate_code_hygiene` (PURE — nhận conventions text + `{path: source}`), `capability.py::changed_java_files` (IMPURE — git probe), `cli.py` nối hai bên theo đúng pattern `code-evidence`. Gate hậu-kiểm chạy như workflow command → không phụ thuộc hook/UA/cbm, sống trên mọi platform.

**Tech Stack:** Python 3 (stdlib `re`/`subprocess` + `pyyaml`), pytest (`/usr/bin/python3 -m pytest` — venv không có pytest), Checkstyle XML (chỉ generate config, KHÔNG chạy gradle).

**Nguồn:** spec = `research/maika-apply-phase-reconciliation.md` §4 + prompt GPT (2026-07-09). Litmus (R3): fixture `.java` bẩn (wildcard + unused import) → gate exit 1; sạch → exit 0.

**Deviations so với prompt GPT (repo-first, đã chốt với user):**
1. Không có flag `--changed-files` — gate **mặc định** tự resolve changed files qua git; thêm `--java-file <f>` (repeatable) để bypass git cho test/manual. CLI giữ pattern `gate <file>` hiện có: `<file>` = đường dẫn `conventions.yaml`.
2. Gradle/Checkstyle-runner **DEFERRED** (R3: repo này không có môi trường gradle/fixture tái hiện; `checkstyle.generated.xml` đã được target project's build tiêu thụ theo cơ chế sẵn có; pure parser phủ đúng lỗi đã quan sát).
3. Schema `code_hygiene` bỏ `applies_to` + `agent_action` (R1/R7: key `java` đã scope ngôn ngữ — gate filter `.java` theo key; `severity` là field duy nhất có consumer cơ học: projector map severity, gate block).

---

## File Structure

| File | Vai trò |
|---|---|
| Modify `.maika/tools/rule-projector/projector.py` | thêm `project_code_hygiene()`, gọi trong `build_ir()` |
| Modify `.maika/tools/rule-projector/ir_schema.json` | enum `ir_rule` += 3 kind mới |
| Modify `.maika/tools/rule-projector/backends/checkstyle.py` | emit 3 module import-hygiene |
| Modify `.maika/tools/rule-projector/tests/test_projector.py` | test projection |
| Modify `.maika/tools/rule-projector/tests/test_checkstyle.py` | test emit |
| Modify `.maika/tools/rule-projector/tests/fixtures/{sample-conventions.yaml, expected-ir.json, expected-checkstyle.xml}` | golden mới |
| Modify `.maika/tools/rule-projector/generated/{rules.json, checkstyle.generated.xml}` | regenerate từ live sources |
| Modify `.maika/tools/gate-check/gates.py` | `validate_code_hygiene` + `_java_import_violations` (pure) |
| Modify `.maika/tools/gate-check/capability.py` | `changed_java_files` (impure git probe) |
| Modify `.maika/tools/gate-check/cli.py` | register gate + `--java-file` + branch resolve sources |
| Create `.maika/tools/gate-check/tests/test_code_hygiene.py` | validator tests + CLI litmus e2e |
| Modify `.maika/tools/gate-check/tests/test_capability.py` | test `changed_java_files` (tmp git repo) |
| Modify `.maika/knowledge/long-term/conventions.yaml` | SECTION 1c skeleton (repo này Python → `{}`) |
| Modify `.maika/skills/convention-intelligence-builder/references/conventions-draft-template.md` | doc SECTION 1c + ví dụ java |
| Modify `.maika/workflows/task.md` | wire gate vào Pha 3 bước 6 + POST-PHASE SELF-CHECK |

Test runner (mọi task): `/usr/bin/python3 -m pytest` từ thư mục tool tương ứng.

---

### Task 0: Branch setup

- [ ] **Step 0.1: Tạo branch từ main**

```bash
cd /home/zane/Desktop/agent-memory-arch-v3
git checkout main && git pull
git checkout -b feat/code-hygiene-gate
```

Expected: branch `feat/code-hygiene-gate` sạch trên main.

---

### Task 1: Projector — `project_code_hygiene` + schema enum

**Files:**
- Modify: `.maika/tools/rule-projector/projector.py` (thêm hàm sau `project_naming`, ~dòng 71; gọi trong `build_ir` ~dòng 97)
- Modify: `.maika/tools/rule-projector/ir_schema.json:19`
- Test: `.maika/tools/rule-projector/tests/test_projector.py`

- [ ] **Step 1.1: Viết failing tests**

Mở `tests/test_projector.py`, xem cách file import `projector` (sys.path pattern như `test_checkstyle.py:5-8`) và append — dùng đúng biến module đã import sẵn trong file (nếu file import là `projector` thì giữ nguyên tên):

```python
def test_code_hygiene_projected_with_severity_mapping():
    conv = {"meta": {"status": "approved"},
            "code_hygiene": {"java": {
                "no_unused_imports": {"severity": "mandatory"},
                "no_wildcard_imports": {"severity": "mandatory"},
                "no_redundant_imports": {"severity": "recommended"}}}}
    rules = projector.project_code_hygiene(conv)
    assert [r["ir_rule"] for r in rules] == [
        "no_unused_imports", "no_wildcard_imports", "no_redundant_imports"]
    by_id = {r["id"]: r for r in rules}
    assert by_id["hygiene.java.no_unused_imports"]["severity"] == "error"
    assert by_id["hygiene.java.no_redundant_imports"]["severity"] == "warning"
    assert all(r["source_ref"] == "conventions.yaml#code_hygiene" for r in rules)

def test_code_hygiene_absent_or_empty_projects_nothing():
    assert projector.project_code_hygiene({}) == []
    assert projector.project_code_hygiene({"code_hygiene": {}}) == []
    assert projector.project_code_hygiene({"code_hygiene": {"java": {}}}) == []
```

- [ ] **Step 1.2: Chạy để thấy fail**

```bash
cd /home/zane/Desktop/agent-memory-arch-v3/.maika/tools/rule-projector
/usr/bin/python3 -m pytest tests/test_projector.py -v -k code_hygiene
```

Expected: FAIL — `AttributeError: module 'projector' has no attribute 'project_code_hygiene'`.

- [ ] **Step 1.3: Implement**

Trong `projector.py`, thêm sau `project_naming` (sau dòng 71):

```python
def project_code_hygiene(conventions):
    """code_hygiene.java (machine lane) -> IR. Key = ir_rule 1:1; backend/schema
    là chốt validate kind (như naming: projector không tự lọc)."""
    rules = []
    java = (conventions.get("code_hygiene") or {}).get("java") or {}
    for key, spec in java.items():
        sev = "error" if (spec or {}).get("severity") == "mandatory" else "warning"
        rules.append(_rule(f"hygiene.java.{key}", key, sev, {},
                           "conventions.yaml#code_hygiene"))
    return rules
```

Trong `build_ir()` (dòng 96-97), mở rộng block approved:

```python
    if _approved(conv):
        rules += project_naming(conv)
        rules += project_code_hygiene(conv)
```

Trong `ir_schema.json` dòng 19, thay enum:

```json
          "ir_rule": {"enum": ["max_if_nesting","max_for_nesting","max_method_lines","max_cyclomatic","forbid_else","naming_regex","require_javadoc_tag","no_unused_imports","no_wildcard_imports","no_redundant_imports"]},
```

- [ ] **Step 1.4: Chạy test pass**

```bash
/usr/bin/python3 -m pytest tests/test_projector.py tests/test_schema.py -v
```

Expected: PASS toàn bộ (schema tests vẫn xanh vì enum chỉ mở rộng).

- [ ] **Step 1.5: Commit**

```bash
git add .maika/tools/rule-projector/projector.py .maika/tools/rule-projector/ir_schema.json .maika/tools/rule-projector/tests/test_projector.py
git commit -m "feat(rule-projector): project conventions code_hygiene.java -> IR (3 import-hygiene kinds)"
```

---

### Task 2: Checkstyle backend — emit import modules

**Files:**
- Modify: `.maika/tools/rule-projector/backends/checkstyle.py:35-39` (thêm elif trước else-raise)
- Test: `.maika/tools/rule-projector/tests/test_checkstyle.py`

- [ ] **Step 2.1: Viết failing test** (append vào `test_checkstyle.py`):

```python
def test_hygiene_rules_emit_import_modules():
    ir = {"version":"1.0","source_hash":"0"*64,"sources":[],"rules":[
        {"id":"hygiene.java.no_unused_imports","ir_rule":"no_unused_imports","severity":"error","params":{},"source_ref":"conventions.yaml#code_hygiene"},
        {"id":"hygiene.java.no_wildcard_imports","ir_rule":"no_wildcard_imports","severity":"error","params":{},"source_ref":"conventions.yaml#code_hygiene"},
        {"id":"hygiene.java.no_redundant_imports","ir_rule":"no_redundant_imports","severity":"warning","params":{},"source_ref":"conventions.yaml#code_hygiene"}]}
    xml = checkstyle.ir_to_checkstyle(ir)
    for module in ("UnusedImports", "AvoidStarImport", "RedundantImport"):
        assert module in xml
    assert '<property name="severity" value="warning"/>' in _norm(xml)
```

- [ ] **Step 2.2: Chạy để thấy fail**

```bash
/usr/bin/python3 -m pytest tests/test_checkstyle.py -v -k hygiene
```

Expected: FAIL — `ValueError: Unsupported ir_rule for checkstyle backend: no_unused_imports`.

- [ ] **Step 2.3: Implement** — trong `_emit_rule` (`checkstyle.py`), thêm trước nhánh `else:` (dòng 38):

```python
    elif ir == "no_unused_imports":
        m = _module(tw, "UnusedImports"); _prop(m, "severity", sev)
    elif ir == "no_wildcard_imports":
        m = _module(tw, "AvoidStarImport"); _prop(m, "severity", sev)
    elif ir == "no_redundant_imports":
        m = _module(tw, "RedundantImport"); _prop(m, "severity", sev)
```

- [ ] **Step 2.4: Chạy test pass**

```bash
/usr/bin/python3 -m pytest tests/test_checkstyle.py -v
```

Expected: PASS (golden fixture test vẫn xanh — fixture chưa có hygiene rule, Task 3 mới thêm).

- [ ] **Step 2.5: Commit**

```bash
git add .maika/tools/rule-projector/backends/checkstyle.py .maika/tools/rule-projector/tests/test_checkstyle.py
git commit -m "feat(rule-projector): checkstyle backend emits UnusedImports/AvoidStarImport/RedundantImport"
```

---

### Task 3: Golden fixtures end-to-end

**Files:**
- Modify: `.maika/tools/rule-projector/tests/fixtures/sample-conventions.yaml`
- Modify: `.maika/tools/rule-projector/tests/fixtures/expected-ir.json`
- Modify: `.maika/tools/rule-projector/tests/fixtures/expected-checkstyle.xml`

- [ ] **Step 3.1: Thêm code_hygiene vào sample-conventions.yaml** (append cuối file):

```yaml
code_hygiene:
  java:
    no_unused_imports: {severity: mandatory}
    no_wildcard_imports: {severity: mandatory}
    no_redundant_imports: {severity: mandatory}
```

- [ ] **Step 3.2: Cập nhật expected-ir.json** — thêm 3 entry vào CUỐI mảng `rules` (sau `naming.MethodName` — thứ tự build_ir: principles → thresholds → naming → hygiene):

```json
    {"id": "hygiene.java.no_unused_imports", "ir_rule": "no_unused_imports", "severity": "error", "params": {}, "source_ref": "conventions.yaml#code_hygiene"},
    {"id": "hygiene.java.no_wildcard_imports", "ir_rule": "no_wildcard_imports", "severity": "error", "params": {}, "source_ref": "conventions.yaml#code_hygiene"},
    {"id": "hygiene.java.no_redundant_imports", "ir_rule": "no_redundant_imports", "severity": "error", "params": {}, "source_ref": "conventions.yaml#code_hygiene"}
```

- [ ] **Step 3.3: Cập nhật expected-checkstyle.xml** — thêm vào cuối `TreeWalker` (sau module `MethodName`, trước `</module></module>` đóng):

```xml
    <!-- from: conventions.yaml#code_hygiene (hygiene.java.no_unused_imports) -->
    <module name="UnusedImports">
      <property name="severity" value="error"/>
    </module>
    <!-- from: conventions.yaml#code_hygiene (hygiene.java.no_wildcard_imports) -->
    <module name="AvoidStarImport">
      <property name="severity" value="error"/>
    </module>
    <!-- from: conventions.yaml#code_hygiene (hygiene.java.no_redundant_imports) -->
    <module name="RedundantImport">
      <property name="severity" value="error"/>
    </module>
```

- [ ] **Step 3.4: Chạy toàn bộ rule-projector suite**

```bash
/usr/bin/python3 -m pytest tests/ -v
```

Expected: PASS toàn bộ (nếu golden lệch: chạy projector trên fixture để xem diff thực — `python3 -c "import json,sys; sys.path.insert(0,'.'); import projector; ir=projector.build_ir('tests/fixtures/sample-author-dna.yaml','tests/fixtures/sample-conventions.yaml'); ir['source_hash']='0'*64; ir.pop('generated_at',None); print(json.dumps(ir,indent=2))"` — LƯU Ý: nếu test golden so cả `source_hash`, giữ đúng cách test hiện xử lý; chỉ sửa fixture cho khớp behavior, KHÔNG sửa test golden semantics).

- [ ] **Step 3.5: Commit**

```bash
git add .maika/tools/rule-projector/tests/fixtures/
git commit -m "test(rule-projector): golden fixtures cover code_hygiene end-to-end"
```

---

### Task 4: Pure validator `validate_code_hygiene`

**Files:**
- Modify: `.maika/tools/gate-check/gates.py` (append cuối file)
- Create: `.maika/tools/gate-check/tests/test_code_hygiene.py`

- [ ] **Step 4.1: Viết failing tests** — tạo `tests/test_code_hygiene.py` (import pattern giống `test_gates.py:1-7`):

```python
import importlib.util
from pathlib import Path

MOD = Path(__file__).resolve().parents[1] / "gates.py"
spec = importlib.util.spec_from_file_location("gates", MOD)
g = importlib.util.module_from_spec(spec)
spec.loader.exec_module(g)

CONV = """
code_hygiene:
  java:
    no_unused_imports: {severity: mandatory}
    no_wildcard_imports: {severity: mandatory}
    no_redundant_imports: {severity: mandatory}
"""
NO_RULES = "naming: {}\n"

DIRTY = (
    "package com.example;\n"
    "import java.util.*;\n"
    "import java.io.File;\n"
    "import com.example.Used;\n"
    "class A { Used u; }\n"
)
CLEAN = (
    "package com.example;\n"
    "import com.example.Used;\n"
    "class A { Used u; }\n"
)


def test_dirty_java_fails_with_wildcard_and_unused():
    res = g.validate_code_hygiene(CONV, java_sources={"A.java": DIRTY})
    assert res.ok is False
    assert "wildcard" in res.reason and "unused" in res.reason


def test_clean_java_passes():
    assert g.validate_code_hygiene(CONV, java_sources={"A.java": CLEAN}).ok is True


def test_duplicate_import_fails():
    src = ("import com.example.Used;\n" "import com.example.Used;\n"
           "class A { Used u; }\n")
    res = g.validate_code_hygiene(CONV, java_sources={"A.java": src})
    assert res.ok is False and "duplicate" in res.reason


def test_direct_java_lang_import_is_redundant():
    src = "import java.lang.String;\nclass A { String s; }\n"
    res = g.validate_code_hygiene(CONV, java_sources={"A.java": src})
    assert res.ok is False and "redundant" in res.reason


def test_used_static_import_passes():
    src = ("import static org.junit.Assert.assertTrue;\n"
           "class T { void t() { assertTrue(true); } }\n")
    assert g.validate_code_hygiene(CONV, java_sources={"T.java": src}).ok is True


def test_no_rules_configured_passes():
    assert g.validate_code_hygiene(NO_RULES, java_sources={"A.java": DIRTY}).ok is True


def test_unknown_changed_files_fails_loudly():
    res = g.validate_code_hygiene(CONV, java_sources=None)
    assert res.ok is False and "changed files" in res.reason


def test_no_changed_java_files_passes():
    assert g.validate_code_hygiene(CONV, java_sources={}).ok is True
```

- [ ] **Step 4.2: Chạy để thấy fail**

```bash
cd /home/zane/Desktop/agent-memory-arch-v3/.maika/tools/gate-check
/usr/bin/python3 -m pytest tests/test_code_hygiene.py -v
```

Expected: FAIL — `AttributeError: ... no attribute 'validate_code_hygiene'`.

- [ ] **Step 4.3: Implement** — append cuối `gates.py`:

```python
_JAVA_IMPORT = re.compile(r"\s*import\s+(static\s+)?([\w.]+(?:\.\*)?)\s*;")
_JAVA_NONBODY = re.compile(r"\s*(import|package)\b")


def _java_import_violations(path, source, enabled):
    """Import-hygiene violations for one .java source (pure text analysis).
    enabled = set of rule keys from conventions code_hygiene.java."""
    lines = source.splitlines()
    imports = []                                   # (lineno, is_static, fqname)
    for i, line in enumerate(lines, 1):
        m = _JAVA_IMPORT.match(line)
        if m:
            imports.append((i, bool(m.group(1)), m.group(2)))
    body = "\n".join(l for l in lines if not _JAVA_NONBODY.match(l))
    out, seen = [], set()
    for lineno, is_static, fq in imports:
        if fq.endswith(".*"):
            if "no_wildcard_imports" in enabled:
                out.append(f"{path}:{lineno} wildcard import '{fq}'")
            continue
        if "no_redundant_imports" in enabled:
            key = (is_static, fq)
            if key in seen:
                out.append(f"{path}:{lineno} duplicate import '{fq}'")
                continue
            seen.add(key)
            if not is_static and fq.startswith("java.lang.") and fq.count(".") == 2:
                out.append(f"{path}:{lineno} redundant java.lang import '{fq}'")
                continue
        if "no_unused_imports" in enabled:
            simple = fq.rsplit(".", 1)[-1]
            if not re.search(rf"\b{re.escape(simple)}\b", body):
                out.append(f"{path}:{lineno} unused import '{fq}'")
    return out


def validate_code_hygiene(text, java_sources=None) -> Result:
    """Deterministic import-hygiene gate (post-edit, hook-independent).
    text = conventions.yaml content — code_hygiene.java keys = enabled rules.
    java_sources = {path: content} of changed .java files (resolved by cli.py);
    None = changed-file set undeterminable → degrade LOUDLY (không fail-open)."""
    try:
        conv = yaml.safe_load(text) or {}
    except yaml.YAMLError as exc:
        return Result(False, f"conventions.yaml unparseable: {exc}")
    enabled = set((conv.get("code_hygiene") or {}).get("java") or {})
    if not enabled:
        return Result(True)                        # no rules configured → nothing to enforce
    if java_sources is None:
        return Result(False,
                      "cannot determine changed files (git probe failed) — "
                      "pass --java-file <path> explicitly or run inside the git repo")
    if not java_sources:
        return Result(True)                        # no changed .java files
    violations = []
    for path in sorted(java_sources):
        violations += _java_import_violations(path, java_sources[path], enabled)
    if violations:
        shown = "; ".join(violations[:10])
        more = f" (+{len(violations) - 10} more)" if len(violations) > 10 else ""
        return Result(False, shown + more)
    return Result(True)
```

- [ ] **Step 4.4: Chạy test pass**

```bash
/usr/bin/python3 -m pytest tests/test_code_hygiene.py tests/test_gates.py -v
```

Expected: PASS toàn bộ.

- [ ] **Step 4.5: Commit**

```bash
git add .maika/tools/gate-check/gates.py .maika/tools/gate-check/tests/test_code_hygiene.py
git commit -m "feat(gate-check): validate_code_hygiene — pure Java import-hygiene validator"
```

---

### Task 5: Impure probe `changed_java_files`

**Files:**
- Modify: `.maika/tools/gate-check/capability.py` (append cuối file)
- Modify: `.maika/tools/gate-check/tests/test_capability.py` (append)

- [ ] **Step 5.1: Viết failing tests** — append vào `tests/test_capability.py` (xem import pattern đầu file hiện có, dùng đúng biến module `cap`/tương đương của file):

```python
def test_changed_java_files_in_tmp_git_repo(tmp_path):
    import subprocess
    def git(*a):
        subprocess.run(["git", "-c", "user.email=t@t", "-c", "user.name=t", *a],
                       cwd=tmp_path, check=True, capture_output=True)
    git("init", "-q")
    (tmp_path / "A.java").write_text("class A {}\n")
    (tmp_path / "x.py").write_text("pass\n")
    git("add", "."); git("commit", "-q", "-m", "init")
    (tmp_path / "A.java").write_text("class A { int x; }\n")   # modified
    (tmp_path / "B.java").write_text("class B {}\n")           # untracked
    (tmp_path / "x.py").write_text("pass  # changed\n")        # non-java: ignored
    files = cap.changed_java_files(str(tmp_path))
    names = sorted(p.rsplit("/", 1)[-1] for p in files)
    assert names == ["A.java", "B.java"]


def test_changed_java_files_none_outside_git(tmp_path):
    sub = tmp_path / "not-a-repo"; sub.mkdir()
    assert cap.changed_java_files(str(sub)) is None
```

LƯU Ý: nếu `test_capability.py` load module bằng importlib với tên khác `cap`, đổi theo tên đó. Test `outside_git` giả định `not-a-repo` không nằm trong git repo cha — `tmp_path` của pytest nằm ở `/tmp` nên đúng.

- [ ] **Step 5.2: Chạy để thấy fail**

```bash
/usr/bin/python3 -m pytest tests/test_capability.py -v -k changed_java
```

Expected: FAIL — `AttributeError: ... no attribute 'changed_java_files'`.

- [ ] **Step 5.3: Implement** — append cuối `capability.py`:

```python
def changed_java_files(repo_root, timeout: int = 8):
    """Changed .java files in repo_root (vs HEAD + untracked), absolute paths.
    Returns None when git cannot answer. DELIBERATELY not fail-open (khác các
    probe trên): code-hygiene gate phải degrade LOUDLY — validator FAILs on None."""
    collected = []
    for cmd in (["git", "diff", "--name-only", "HEAD"],
                ["git", "ls-files", "--others", "--exclude-standard"]):
        try:
            proc = subprocess.run(cmd, cwd=repo_root, capture_output=True,
                                  text=True, timeout=timeout)
        except (OSError, subprocess.SubprocessError):
            return None
        if proc.returncode != 0:
            return None
        collected += [ln.strip() for ln in proc.stdout.splitlines() if ln.strip()]
    return sorted({os.path.join(repo_root, f)
                   for f in collected if f.endswith(".java")})
```

- [ ] **Step 5.4: Chạy test pass**

```bash
/usr/bin/python3 -m pytest tests/test_capability.py -v
```

Expected: PASS toàn bộ.

- [ ] **Step 5.5: Commit**

```bash
git add .maika/tools/gate-check/capability.py .maika/tools/gate-check/tests/test_capability.py
git commit -m "feat(gate-check): changed_java_files git probe (loud-degrade, returns None on git failure)"
```

---

### Task 6: CLI wiring + LITMUS e2e

**Files:**
- Modify: `.maika/tools/gate-check/cli.py` (VALIDATORS dòng 9-25; args dòng 56-61; branch dòng 79-89)
- Modify: `.maika/tools/gate-check/tests/test_code_hygiene.py` (append litmus)

- [ ] **Step 6.1: Viết failing litmus test** — append vào `tests/test_code_hygiene.py`:

```python
CLI = Path(__file__).resolve().parents[1] / "cli.py"
cspec = importlib.util.spec_from_file_location("cli", CLI)
cli = importlib.util.module_from_spec(cspec)
cspec.loader.exec_module(cli)


def test_litmus_cli_dirty_fails_then_clean_passes(tmp_path):
    """R3 litmus: file .java bẩn (wildcard + unused) → exit != 0; sạch → exit 0."""
    conv = tmp_path / "conventions.yaml"
    conv.write_text(CONV)
    j = tmp_path / "Dirty.java"
    j.write_text(DIRTY)
    assert cli.main(["code-hygiene", str(conv), "--java-file", str(j)]) == 1
    j.write_text(CLEAN)
    assert cli.main(["code-hygiene", str(conv), "--java-file", str(j)]) == 0


def test_litmus_cli_no_rules_section_passes(tmp_path):
    conv = tmp_path / "conventions.yaml"
    conv.write_text(NO_RULES)
    j = tmp_path / "Dirty.java"
    j.write_text(DIRTY)
    assert cli.main(["code-hygiene", str(conv), "--java-file", str(j)]) == 0
```

- [ ] **Step 6.2: Chạy để thấy fail**

```bash
/usr/bin/python3 -m pytest tests/test_code_hygiene.py -v -k litmus
```

Expected: FAIL — argparse `invalid choice: 'code-hygiene'` (exit 2 ≠ 1).

- [ ] **Step 6.3: Implement** — trong `cli.py`:

(a) VALIDATORS (sau dòng 24 `"code-evidence": ...`):

```python
    "code-hygiene": "validate_code_hygiene",
```

(b) args (sau dòng 61 `--repo-root`):

```python
    parser.add_argument("--java-file", action="append",
                        help="code-hygiene: explicit changed .java file (bypass git probe)")
```

(c) branch — thêm sau block `elif args.gate == "code-evidence":` (sau dòng 89):

```python
    elif args.gate == "code-hygiene":
        repo_root = args.repo_root or os.getcwd()
        if args.java_file:
            files = [os.path.abspath(f) for f in args.java_file]
        else:
            cap = _load_module("capability")
            files = cap.changed_java_files(repo_root)
        if files is None:
            kwargs["java_sources"] = None
        else:
            kwargs["java_sources"] = {
                f: Path(f).read_text(encoding="utf-8")
                for f in files if f.endswith(".java")
            }
```

- [ ] **Step 6.4: Chạy test pass + toàn bộ gate-check suite**

```bash
/usr/bin/python3 -m pytest tests/ -v
```

Expected: PASS toàn bộ (không phá test hiện có — các gate khác không đụng `--java-file`).

- [ ] **Step 6.5: Verify bằng tay (evidence cho báo cáo)**

```bash
cd /home/zane/Desktop/agent-memory-arch-v3
printf 'code_hygiene:\n  java:\n    no_unused_imports: {severity: mandatory}\n    no_wildcard_imports: {severity: mandatory}\n' > /tmp/claude-1000/-home-zane-Desktop-agent-memory-arch-v3/f3172f17-f8b4-452f-9757-629245ac2561/scratchpad/conv.yaml
printf 'import java.util.*;\nimport java.io.File;\nclass A {}\n' > /tmp/claude-1000/-home-zane-Desktop-agent-memory-arch-v3/f3172f17-f8b4-452f-9757-629245ac2561/scratchpad/Dirty.java
python3 .maika/tools/gate-check/cli.py code-hygiene /tmp/claude-1000/-home-zane-Desktop-agent-memory-arch-v3/f3172f17-f8b4-452f-9757-629245ac2561/scratchpad/conv.yaml --java-file /tmp/claude-1000/-home-zane-Desktop-agent-memory-arch-v3/f3172f17-f8b4-452f-9757-629245ac2561/scratchpad/Dirty.java; echo "exit=$?"
```

Expected: `FAIL — ...wildcard import 'java.util.*'... unused import 'java.io.File'` và `exit=1`.

- [ ] **Step 6.6: Commit**

```bash
git add .maika/tools/gate-check/cli.py .maika/tools/gate-check/tests/test_code_hygiene.py
git commit -m "feat(gate-check): code-hygiene CLI gate + R3 litmus (dirty java FAIL, clean PASS)"
```

---

### Task 7: Schema surface — live conventions.yaml + template + regenerate generated/

**Files:**
- Modify: `.maika/knowledge/long-term/conventions.yaml` (sau SECTION 1b, dòng 34)
- Modify: `.maika/skills/convention-intelligence-builder/references/conventions-draft-template.md` (sau SECTION 1b, ~dòng 80)
- Modify: `.maika/tools/rule-projector/generated/{rules.json, checkstyle.generated.xml}` (regenerate)

- [ ] **Step 7.1: Thêm SECTION 1c vào conventions.yaml** — chèn sau dòng 34 (`naming_patterns: []`):

```yaml

# ─────────────────────────────────────────────
# SECTION 1c: Code Hygiene (machine lane — rule-projector + gate-check input)
# Key dưới mỗi ngôn ngữ = rule id (vd java: no_unused_imports | no_wildcard_imports
# | no_redundant_imports). severity: mandatory → checkstyle error + gate block.
# Consumers: rule-projector (project_code_hygiene) + gate-check `code-hygiene`.
# Repo này là Python → rỗng; project Java điền như ví dụ trong template.
# ─────────────────────────────────────────────
code_hygiene: {}
```

- [ ] **Step 7.2: Thêm SECTION 1c vào conventions-draft-template.md** — chèn sau block SECTION 1b (sau dòng `naming_patterns` ví dụ, ~dòng 80, giữ style comment hiện có):

```yaml
# ─────────────────────────────────────────────
# SECTION 1c: Code Hygiene (machine lane — rule-projector + gate-check input)
# Bài học lặp lại kiểm được bằng máy → khai ở đây, KHÔNG dựa trí nhớ agent.
# severity: mandatory → checkstyle error + gate-check block final (Pha 3).
# ─────────────────────────────────────────────
code_hygiene:
  java:
    no_unused_imports: {severity: mandatory}
    no_wildcard_imports: {severity: mandatory}
    no_redundant_imports: {severity: mandatory}
```

- [ ] **Step 7.3: Regenerate generated/ từ live sources** (source_hash đổi vì conventions.yaml đổi):

```bash
cd /home/zane/Desktop/agent-memory-arch-v3/.maika/tools/rule-projector
python3 projector.py --dna ../../knowledge/long-term/author-dna.yaml --conventions ../../knowledge/long-term/conventions.yaml --out generated
python3 backends/checkstyle.py --ir generated/rules.json --out generated/checkstyle.generated.xml
```

Expected: `IR written: generated/rules.json (N rules)` — N không đổi so với trước (live `code_hygiene: {}` rỗng), nhưng `source_hash` mới.

- [ ] **Step 7.4: Chạy lại cả hai suite**

```bash
/usr/bin/python3 -m pytest tests/ -v
cd ../gate-check && /usr/bin/python3 -m pytest tests/ -v
```

Expected: PASS toàn bộ.

- [ ] **Step 7.5: Commit**

```bash
git add .maika/knowledge/long-term/conventions.yaml .maika/skills/convention-intelligence-builder/references/conventions-draft-template.md .maika/tools/rule-projector/generated/
git commit -m "feat(conventions): code_hygiene machine-lane section (schema + template) + regen projector output"
```

---

### Task 8: Wire vào task.md Pha 3

**Files:**
- Modify: `.maika/workflows/task.md:448` (bước 6 — sau post_apply_verify) và `:479` (POST-PHASE SELF-CHECK)

- [ ] **Step 8.1: Thêm gate vào bước 6** — Edit `task.md`, old_string:

```text
6. Sau khi micro-loop xong:
   - Chạy `spec-validator.post_apply_verify(spec_path, changed_files)` — ghi kết quả vào AGENT_TRANSPARENCY.
```

new_string:

```text
6. Sau khi micro-loop xong:
   - Chạy `spec-validator.post_apply_verify(spec_path, changed_files)` — ghi kết quả vào AGENT_TRANSPARENCY.
   - Nếu changed files có `*.java`: chạy gate import-hygiene (deterministic, không phụ thuộc UA/cbm):
     `python3 {{ platform.framework_root }}/tools/gate-check/cli.py code-hygiene {{ platform.framework_root }}/knowledge/long-term/conventions.yaml`
     — FAIL ⇒ fix import trong changed files rồi chạy lại tới khi PASS. KHÔNG final khi gate FAIL.
```

- [ ] **Step 8.2: Thêm checklist item vào POST-PHASE SELF-CHECK** — Edit `task.md`, old_string:

```text
   - `[ ]` spec-validator DNA compliance check (gate #6) đã chạy.
```

new_string:

```text
   - `[ ]` spec-validator DNA compliance check (gate #6) đã chạy.
   - `[ ]` Gate `code-hygiene` PASS (exit 0) nếu có changed `*.java` — lệnh như bước 6.
```

- [ ] **Step 8.3: Full verification sweep (mọi suite bị đụng)**

```bash
cd /home/zane/Desktop/agent-memory-arch-v3
/usr/bin/python3 -m pytest .maika/tools/rule-projector/tests/ .maika/tools/gate-check/tests/ -v
```

Expected: PASS toàn bộ. Ghi lại số test pass để báo cáo.

- [ ] **Step 8.4: Commit**

```bash
git add .maika/workflows/task.md
git commit -m "feat(task): wire code-hygiene gate into Pha 3 apply/verify + self-check"
```

---

## Báo cáo cuối (format bắt buộc — theo yêu cầu user)

```text
Changed files:
- <liệt kê>

Implemented:
- conventions code_hygiene schema (SECTION 1c, machine lane)
- rule-projector -> Checkstyle import rules (UnusedImports/AvoidStarImport/RedundantImport)
- gate-check code-hygiene (pure validator + git probe + CLI, loud-degrade)
- task.md apply/verify wiring (bước 6 + POST-PHASE SELF-CHECK)
- litmus tests (dirty .java FAIL / clean PASS, validator + CLI e2e)

Verification:
- <lệnh pytest đã chạy + số pass/fail>
- <output lệnh verify tay Step 6.5>
- Deferred: gradle/checkstyle runner (R3 — không có môi trường/fixture gradle ở repo này)
```

## Out of scope (đã chốt)

- KHÔNG skill `code-hygiene`/`apply-runner`, KHÔNG `APPLY_TRACE.yaml`, KHÔNG Semgrep/OpenRewrite, KHÔNG đổi tên TOKEN_LOG, KHÔNG dashboard mới.
- KHÔNG sửa doctrine UA-first; UA graph missing là hạng mục khác.
- Gradle runner trong gate: DEFERRED (ghi lý do trong báo cáo).
