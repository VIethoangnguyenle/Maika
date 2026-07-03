# Windows Hardening Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Đóng 11 finding đã chốt trong eng review 2026-07-03 của PR #13 (Windows native support): persist `hook_python`, anchor hook Claude-Windows, harden `install.ps1`, CI matrix chạy `install.ps1` thật trên windows-latest, fix test đỏ có sẵn trên main.

**Architecture:** Không thay đổi kiến trúc — chỉ hoàn thiện các lớp đã có. `resolved-config.yaml` trở thành nguồn round-trip cho MỌI render input (thêm khóa `hook_python`). Nhánh Windows của hook Claude neo qua `%CLAUDE_PROJECT_DIR%` (fix cwd-drift, claude-code#50960); Codex/Antigravity giữ đường dẫn tương đối cho tới khi runtime Windows của chúng được validate. `install.ps1` nhận guard exit-code, registry-safe PATH, 8.3 short-path shim, auto-remediate pyyaml, và flag passthrough để chạy headless — CI dùng chính đường headless đó.

**Tech Stack:** Python 3.9+, Jinja2, PyYAML, PowerShell 5.1+, pytest, GitHub Actions.

## Global Constraints

- **Linux KHÔNG đổi hành vi:** 3 chuỗi hook Linux giữ nguyên xi — test `test_linux_command_byte_identical` phải PASS nguyên trạng ở mọi task. (Review quyết định 2B chỉ đụng nhánh **Windows** của **claude-code**.)
- **`write_gate.py` KHÔNG đổi** — lỗ hổng parser verb Windows là TODOS **W1**, spec riêng, ngoài scope plan này.
- **Python floor = 3.9** (khớp `pyproject.toml:11` `requires-python = ">=3.9"`) — mọi chỗ nhắc floor (install.ps1, install.sh, message) dùng đúng `3.9`.
- **`hook_python` trong resolved-config là optional:** config cũ không có khóa này phải hoạt động y như trước (default `"python"` chỉ áp ở nhánh Windows).
- **Test command:** `.venv/bin/python -m pytest cli/tests/ -q` (Linux dev box). Sau Task 9, kỳ vọng **240 passed, 0 failed**.
- **Commit style:** conventional commits, tiếng Anh, như lịch sử repo (`feat(...)`, `fix(...)`, `test(...)`, `ci(...)`, `docs(...)`).

---

### Task 1: Persist `hook_python` vào resolved-config + update đọc lại (regression 1A + plumbing 8A)

**Files:**
- Modify: `cli/scaffold.py:77-97` (`generate_resolved_config`)
- Modify: `cli/commands/init.py:252` (truyền `hook_python`)
- Modify: `cli/commands/update.py:33-57` (đọc lại từ resolved; re-persist khi flag tường minh)
- Test (create): `cli/tests/test_hook_python_persistence.py`

**Interfaces:**
- Consumes: `run_init(target_dir, maika_root=None, platform_key=None, selected_mcps=None, language=None, assume_yes=False, ua_mcp_dir=None, hook_python=None)` (`cli/commands/init.py:193`); `run_update(target_dir, maika_root=None, reconfigure=False, hook_python=None)` (`cli/commands/update.py:33`); `load_resolved_config(target) -> Optional[dict]` (`cli/scaffold.py:128`).
- Produces: `generate_resolved_config(target_dir, platform, selected_mcps, language, hook_python=None)` — ghi khóa `hook_python` vào map `resolved:` khi truthy, bỏ qua khi None. `run_update` không flag → render bằng `resolved.get("hook_python")`. Task 10 (CI) và mọi update sau dựa vào round-trip này.

- [x] **Step 1: Viết failing tests**

Tạo `cli/tests/test_hook_python_persistence.py`:

```python
"""hook_python must round-trip through resolved-config (eng review 1A + 8A).

Regression: a `py -3`-only Windows box installs correctly, then a bare
`maika update` (no --hook-python) must NOT reset hooks to `python`.
"""

import yaml

import pytest

from cli.platforms import get_platform
from cli.scaffold import generate_resolved_config, load_resolved_config


def test_generate_resolved_config_persists_hook_python(tmp_path):
    platform = get_platform("claude-code")
    generate_resolved_config(tmp_path, platform, [], "python", hook_python="py -3")
    resolved = load_resolved_config(tmp_path)
    assert resolved["hook_python"] == "py -3"


def test_generate_resolved_config_omits_hook_python_when_none(tmp_path):
    platform = get_platform("claude-code")
    generate_resolved_config(tmp_path, platform, [], "python")
    raw = (tmp_path / ".claude" / "resolved-config.yaml").read_text(encoding="utf-8")
    assert "hook_python" not in raw  # Linux configs stay noise-free


@pytest.fixture
def windows_host(monkeypatch):
    """Force scaffold-time OS detection to Windows regardless of test host."""
    monkeypatch.setattr("cli.platforms.base._platform.system", lambda: "Windows")


def _init_project(tmp_path, hook_python):
    from cli.commands.init import run_init
    run_init(
        target_dir=str(tmp_path),
        platform_key="claude-code",
        selected_mcps=[],
        language="python",
        assume_yes=True,
        hook_python=hook_python,
    )


def test_init_renders_and_persists_launcher(tmp_path, windows_host):
    # Plumbing guard (8A): flag -> run_init -> context -> rendered command.
    _init_project(tmp_path, "py -3")
    settings = (tmp_path / ".claude" / "settings.json").read_text(encoding="utf-8")
    assert '"command": "py -3 ' in settings
    assert load_resolved_config(tmp_path)["hook_python"] == "py -3"


def test_bare_update_preserves_hook_python(tmp_path, windows_host):
    # THE regression (1A): update without the flag must keep `py -3`.
    from cli.commands.update import run_update
    _init_project(tmp_path, "py -3")
    run_update(target_dir=str(tmp_path))
    settings = (tmp_path / ".claude" / "settings.json").read_text(encoding="utf-8")
    assert '"command": "py -3 ' in settings
    assert '"command": "python ' not in settings


def test_update_with_flag_overrides_and_repersists(tmp_path, windows_host):
    from cli.commands.update import run_update
    _init_project(tmp_path, "py -3")
    run_update(target_dir=str(tmp_path), hook_python="python")
    settings = (tmp_path / ".claude" / "settings.json").read_text(encoding="utf-8")
    assert '"command": "python ' in settings
    # New choice becomes the persisted choice for the NEXT bare update.
    assert load_resolved_config(tmp_path)["hook_python"] == "python"
```

- [x] **Step 2: Chạy để xác nhận fail**

Run: `.venv/bin/python -m pytest cli/tests/test_hook_python_persistence.py -v`
Expected: `test_generate_resolved_config_persists_hook_python` FAIL (`TypeError: generate_resolved_config() got an unexpected keyword argument 'hook_python'`); `test_bare_update_preserves_hook_python` FAIL (settings chứa `"python "`).

- [x] **Step 3: Sửa `cli/scaffold.py`**

Thay signature + body của `generate_resolved_config` (dòng 77-97):

```python
def generate_resolved_config(
    target_dir: Path, platform, selected_mcps: List[str], language: str,
    hook_python: Optional[str] = None,
) -> None:
    """Write resolved-config.yaml under the platform's framework root."""
    config_path = target_dir / platform.framework_root / "resolved-config.yaml"
    config_path.parent.mkdir(parents=True, exist_ok=True)
    resolved = {
        "platform": platform.name,
        "framework_root": platform.framework_root,
        "mcps": selected_mcps,
        "language": language,
        "framework_version": FRAMEWORK_VERSION,
    }
    if hook_python:
        resolved["hook_python"] = hook_python
    with open(config_path, "w", encoding="utf-8") as f:
        f.write("# Maika Resolved Configuration\n")
        f.write("# Generated by: maika init / maika update --reconfigure\n")
        f.write("# The adapter layer is pre-resolved — no runtime lookup needed.\n\n")
        yaml.dump(
            {"resolved": resolved},
            f, default_flow_style=False, allow_unicode=True,
        )
    _sweep_stale_configs(target_dir, keep=config_path)
```

- [x] **Step 4: Sửa `cli/commands/init.py:252`**

Từ:

```python
    generate_resolved_config(target, platform, selected_mcps, language)
```

Thành:

```python
    generate_resolved_config(target, platform, selected_mcps, language, hook_python=hook_python)
```

- [x] **Step 5: Sửa `cli/commands/update.py`**

Trong `run_update`, sau khối `if reconfigure: ... else: ...` (dòng 46-53), thay dòng build context (dòng 57):

```python
    platform = get_platform(platform_key)
    framework_root = resolved.get("framework_root", platform.framework_root)
    effective_hook_python = hook_python or resolved.get("hook_python")
    context = platform.build_render_context(selected_mcps, language, hook_python=effective_hook_python)
```

Và ở cuối hàm, NGAY TRƯỚC `warn_legacy_maika(target, platform)` (dòng 107), thêm re-persist khi flag tường minh đổi lựa chọn (nhánh không-reconfigure; nhánh reconfigure đã gọi `generate_resolved_config` sẵn — cập nhật call đó luôn):

```python
    if not reconfigure and hook_python and hook_python != resolved.get("hook_python"):
        generate_resolved_config(target, platform, selected_mcps, language, hook_python=hook_python)
```

Và sửa call trong nhánh `if reconfigure:` (dòng 87):

```python
        generate_resolved_config(target, platform, selected_mcps, language, hook_python=effective_hook_python)
```

- [x] **Step 6: Chạy lại test file**

Run: `.venv/bin/python -m pytest cli/tests/test_hook_python_persistence.py -v`
Expected: PASS cả 5.

- [x] **Step 7: Chạy full suite (trừ test đỏ đã biết)**

Run: `.venv/bin/python -m pytest cli/tests/ -q`
Expected: chỉ còn 1 fail đã biết `test_snapshot_includes_subagent_handoff_prompts` (fix ở Task 9). Không fail mới.

- [x] **Step 8: Commit**

```bash
git add cli/scaffold.py cli/commands/init.py cli/commands/update.py cli/tests/test_hook_python_persistence.py
git commit -m "fix(config): persist hook_python in resolved-config; bare update no longer resets Windows hooks"
```

---

### Task 2: Anchor hook Claude-Windows qua `%CLAUDE_PROJECT_DIR%` (2B)

**Files:**
- Modify: `.maika/hooks/claude-code/settings.json` (chỉ nhánh `{% if is_windows %}`)
- Modify: `cli/tests/test_hook_os_rendering.py`

**Interfaces:**
- Consumes: fixtures `jinja_env`, `maika_root` (`cli/tests/conftest.py:11-19`); `render_string` (`cli/renderer.py`).
- Produces: command Windows-claude mới `{{ hook_python }} "%CLAUDE_PROJECT_DIR%/.claude/hooks/write-gate/write_gate.py" --framework-root .claude --runtime claude`. Codex/Antigravity Windows GIỮ NGUYÊN đường dẫn tương đối (scope 2B). Task 11 ghi chú residual này.

- [x] **Step 1: Cập nhật test kỳ vọng (failing trước)**

Trong `cli/tests/test_hook_os_rendering.py`, thay `test_windows_command_portable` và `test_windows_command_honors_hook_python` bằng bản dùng dict kỳ vọng theo runtime:

```python
# Exact Windows command strings (post-render). Claude anchors via
# %CLAUDE_PROJECT_DIR% (cwd-drift, claude-code#50960); codex/antigravity stay
# cwd-relative until their Windows runtimes are validated (review 2B).
WINDOWS_EXPECTED = {
    "claude": '{hp} "%CLAUDE_PROJECT_DIR%/.claude/hooks/write-gate/write_gate.py" --framework-root .claude --runtime claude',
    "codex": "{hp} .agents/hooks/write-gate/write_gate.py --framework-root .agents --runtime codex",
    "antigravity": "{hp} .agents/hooks/write-gate/write_gate.py --framework-root .agents --runtime antigravity",
}


@pytest.mark.parametrize("template_rel,platform_key,runtime,root", HOOKS)
def test_windows_command_portable(jinja_env, maika_root, template_rel, platform_key, runtime, root):
    cmd = _command(jinja_env, maika_root, template_rel, platform_key, is_windows=True)
    assert cmd == WINDOWS_EXPECTED[runtime].format(hp="python")
    # No Unix-only shell tokens survive on Windows.
    assert "/usr/bin/python3" not in cmd
    assert "$(git rev-parse" not in cmd
    assert "$CLAUDE_PROJECT_DIR" not in cmd  # %VAR% form is not the $VAR form


@pytest.mark.parametrize("template_rel,platform_key,runtime,root", HOOKS)
def test_windows_command_honors_hook_python(jinja_env, maika_root, template_rel, platform_key, runtime, root):
    ctx = get_platform(platform_key).build_render_context([], "python", hook_python="py -3")
    ctx["is_windows"] = True
    text = (maika_root / template_rel).read_text(encoding="utf-8")
    cmd = json.loads(render_string(jinja_env, text, ctx))["hooks"]["PreToolUse"][0]["hooks"][0]["command"]
    assert cmd == WINDOWS_EXPECTED[runtime].format(hp="py -3")
```

(Xóa biến `expected = f"python {root}/..."` cũ trong 2 test này; `LINUX_EXPECTED` và các test khác giữ nguyên.)

- [x] **Step 2: Chạy để xác nhận fail đúng chỗ**

Run: `.venv/bin/python -m pytest cli/tests/test_hook_os_rendering.py -v`
Expected: FAIL chỉ ở `claude` cases của 2 test Windows (command hiện là dạng tương đối); codex/antigravity + toàn bộ Linux PASS.

- [x] **Step 3: Sửa template `.maika/hooks/claude-code/settings.json`**

Chỉ đổi dòng command trong nhánh `{% if is_windows %}` (giữ tag `{% %}` ở đầu dòng riêng — renderer bật `trim_blocks`/`lstrip_blocks`, xem `cli/renderer.py:33-34`):

Từ:

```json
{% if is_windows %}
            "command": "{{ hook_python }} {{ platform.framework_root }}/hooks/write-gate/write_gate.py --framework-root {{ platform.framework_root }} --runtime claude"
{% else %}
```

Thành:

```json
{% if is_windows %}
            "command": "{{ hook_python }} \"%CLAUDE_PROJECT_DIR%/{{ platform.framework_root }}/hooks/write-gate/write_gate.py\" --framework-root {{ platform.framework_root }} --runtime claude"
{% else %}
```

- [x] **Step 4: Chạy lại**

Run: `.venv/bin/python -m pytest cli/tests/test_hook_os_rendering.py -v`
Expected: PASS toàn bộ (kể cả `test_linux_command_byte_identical` — nhánh else không đụng).

- [x] **Step 5: Commit**

```bash
git add .maika/hooks/claude-code/settings.json cli/tests/test_hook_os_rendering.py
git commit -m "fix(hooks): anchor Claude-Windows write-gate via %CLAUDE_PROJECT_DIR% (cwd-drift, claude-code#50960)"
```

- [ ] **Step 6: (Manual, Windows only — ghi vào PR description như checklist)**

Trên máy Windows thật, sau khi scaffold: mở Claude Code trong project, `cd` vào thư mục con giữa phiên, kích một tool-call ghi file → hook vẫn chạy (script tìm thấy qua `%CLAUDE_PROJECT_DIR%`). Nếu `%VAR%` KHÔNG expand (hook chạy qua shell khác cmd.exe): rollback template về đường dẫn tương đối + ghi kết quả vào TODOS W1 — đây là giả định duy nhất của plan cần verify trên hardware thật.

---

### Task 3: `install.ps1` — guard exit-code mọi lệnh native + dọn venv hỏng (4A)

**Files:**
- Modify: `install.ps1:53-63` (khối venv + pip)
- Modify: `cli/tests/test_install_ps1.py`

**Interfaces:**
- Consumes: nội dung `install.ps1` hiện tại (throw đã dùng cho scaffold calls, `bec0fc1`).
- Produces: helper PowerShell `Assert-NativeExit` mà Task 4/5/6/7/8 tái dùng khi thêm lệnh native mới.

- [ ] **Step 1: Viết failing static tests**

Thêm vào cuối `cli/tests/test_install_ps1.py`:

```python
def test_native_calls_are_exit_checked(ps1_text):
    # PS 5.1: $ErrorActionPreference='Stop' does NOT cover native exit codes.
    assert "function Assert-NativeExit" in ps1_text
    # venv creation + pip upgrade + pip floors + pip -e = 4 guarded call sites.
    assert ps1_text.count("Assert-NativeExit") >= 5  # 1 def + >=4 uses


def test_failed_venv_bootstrap_is_cleaned_up(ps1_text):
    # A half-built venv must not survive to poison the next run.
    assert "Remove-Item -Recurse -Force -LiteralPath $Venv" in ps1_text
```

- [ ] **Step 2: Chạy để xác nhận fail**

Run: `.venv/bin/python -m pytest cli/tests/test_install_ps1.py -v`
Expected: 2 test mới FAIL.

- [ ] **Step 3: Sửa `install.ps1`**

Thêm helper ngay sau `$ErrorActionPreference = 'Stop'`:

```powershell
function Assert-NativeExit([string]$What) {
    if ($LASTEXITCODE -ne 0) { throw "$What failed (exit $LASTEXITCODE)." }
}
```

Thay khối venv + pip (hiện tại dòng 53-63) bằng:

```powershell
if (-not (Test-Path -LiteralPath $Venv)) {
    Write-Host "-> Creating virtualenv at $Venv"
    try {
        & $Py.Exe @($Py.Args) -m venv $Venv
        Assert-NativeExit "venv creation"
        & $VenvPip install --quiet --upgrade pip
        Assert-NativeExit "pip upgrade"
        & $VenvPip install --quiet "jinja2>=3.1" "pyyaml>=6.0"
        Assert-NativeExit "dependency install"
    } catch {
        # A half-built venv makes every future run skip dependency install.
        if (Test-Path -LiteralPath $Venv) { Remove-Item -Recurse -Force -LiteralPath $Venv }
        throw
    }
}

# Install the maika CLI as an editable package (creates .venv\Scripts\maika.exe).
& $VenvPip install --quiet -e $MaikaRoot
Assert-NativeExit "maika editable install"
```

- [ ] **Step 4: Chạy lại**

Run: `.venv/bin/python -m pytest cli/tests/test_install_ps1.py -v`
Expected: PASS toàn bộ.

- [ ] **Step 5: Commit**

```bash
git add install.ps1 cli/tests/test_install_ps1.py
git commit -m "fix(install): abort install.ps1 on native command failure; clean up half-built venv"
```

---

### Task 4: Floor Python 3.9 đồng bộ + fix message remediation `py -3` (C2-A)

**Files:**
- Modify: `install.ps1` (2 chỗ `[version]'3.8'`, message lỗi, message pyyaml)
- Modify: `install.sh:21-25` (thêm check version thật)
- Modify: `cli/tests/test_install_ps1.py`

**Interfaces:**
- Consumes: `pyproject.toml:11` `requires-python = ">=3.9"` (nguồn chân lý).
- Produces: `$HookPython` được dùng trong message (Task 5 tái dùng pattern này).

- [ ] **Step 1: Viết failing drift-proof test**

Thêm vào cuối `cli/tests/test_install_ps1.py` (file đã import `Path`, thêm `import re` đầu file):

```python
def test_python_floor_matches_pyproject(ps1_text):
    pyproject = (REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8")
    floor = re.search(r'requires-python\s*=\s*">=(\d+\.\d+)"', pyproject).group(1)
    assert f"[version]'{floor}'" in ps1_text, f"install.ps1 floor must be {floor}"
    assert "[version]'3.8'" not in ps1_text
    sh_text = (REPO_ROOT / "install.sh").read_text(encoding="utf-8")
    assert floor in sh_text, f"install.sh must enforce Python >= {floor}"


def test_pyyaml_hint_uses_resolved_launcher(ps1_text):
    # `py -3` boxes must not be told to run bare `py -m pip ...`.
    assert "Run: $HookPython -m pip" in ps1_text
```

- [ ] **Step 2: Chạy để xác nhận fail**

Run: `.venv/bin/python -m pytest cli/tests/test_install_ps1.py -v`
Expected: 2 test mới FAIL.

- [ ] **Step 3: Sửa `install.ps1`**

- Cả 2 dòng trong `Resolve-Python`: `[version]'3.8'` → `[version]'3.9'`.
- Message throw: `"Python 3.8+ not found..."` → `"Python 3.9+ not found. Install Python and ensure 'python' or 'py' is on PATH."`
- Dòng warning pyyaml (dòng 77): thay `Run: $($Py.Exe) -m pip install pyyaml` → `Run: $HookPython -m pip install pyyaml`.

- [ ] **Step 4: Sửa `install.sh`**

Thay khối check python3 (dòng 21-25):

```bash
# Require python3 >= 3.9 (matches pyproject.toml requires-python).
if ! command -v python3 >/dev/null 2>&1; then
  echo "❌ python3 not found. Please install Python 3.9 or newer."
  exit 1
fi
PY_VER="$(python3 -c 'import sys; print("%d.%d" % sys.version_info[:2])')"
if [ "$(printf '%s\n' "3.9" "$PY_VER" | sort -V | head -1)" != "3.9" ]; then
  echo "❌ Python >= 3.9 required (found $PY_VER)."
  exit 1
fi
```

- [ ] **Step 5: Chạy lại + smoke install.sh cục bộ**

Run: `.venv/bin/python -m pytest cli/tests/test_install_ps1.py -v` → PASS.
Run: `bash -n install.sh` → exit 0 (syntax OK).

- [ ] **Step 6: Commit**

```bash
git add install.ps1 install.sh cli/tests/test_install_ps1.py
git commit -m "fix(install): align Python floor to 3.9 with pyproject; correct py -3 pyyaml hint"
```

---

### Task 5: Auto-remediate pyyaml cho hook interpreter (C7-A)

**Files:**
- Modify: `install.ps1` (khối pyyaml check, dòng ~75-78)
- Modify: `cli/tests/test_install_ps1.py`

**Interfaces:**
- Consumes: `Assert-NativeExit` KHÔNG dùng ở đây (fail được phép — degrade thành warning); `$HookPython` từ Task 4.
- Produces: hook interpreter có pyyaml trên clean box; Task 10 (CI E2E) đi qua path này thật.

- [ ] **Step 1: Viết failing static tests**

```python
def test_pyyaml_auto_remediation(ps1_text):
    # Clean boxes get pyyaml installed (announced, --user); warn only on failure.
    assert "pip install --user --quiet pyyaml" in ps1_text
    # Re-check after the attempted install (two import probes total).
    assert ps1_text.count('-c "import yaml"') >= 2
```

- [ ] **Step 2: Chạy để xác nhận fail**

Run: `.venv/bin/python -m pytest cli/tests/test_install_ps1.py::test_pyyaml_auto_remediation -v` → FAIL.

- [ ] **Step 3: Sửa `install.ps1`**

Thay khối:

```powershell
# The write-gate hook runs OUTSIDE the venv via system `python`; warn if it lacks pyyaml.
& $Py.Exe @($Py.Args) -c "import yaml" 2>$null
if ($LASTEXITCODE -ne 0) {
    Write-Warning "System Python lacks 'pyyaml'; the write-gate hook needs it. Run: $HookPython -m pip install pyyaml"
}
```

Bằng:

```powershell
# The write-gate hook runs OUTSIDE the venv via the resolved launcher; a clean
# Windows Python has no pyyaml, which would silently kill the gate at runtime.
& $Py.Exe @($Py.Args) -c "import yaml" 2>$null
if ($LASTEXITCODE -ne 0) {
    Write-Host "-> Hook interpreter ($HookPython) lacks 'pyyaml' — installing (pip --user)."
    & $Py.Exe @($Py.Args) -m pip install --user --quiet pyyaml
    & $Py.Exe @($Py.Args) -c "import yaml" 2>$null
    if ($LASTEXITCODE -ne 0) {
        Write-Warning "Could not install 'pyyaml' for $HookPython. The write-gate hook WILL FAIL until you run: $HookPython -m pip install --user pyyaml"
    }
}
```

- [ ] **Step 4: Chạy lại toàn file test**

Run: `.venv/bin/python -m pytest cli/tests/test_install_ps1.py -v` → PASS.

- [ ] **Step 5: Commit**

```bash
git add install.ps1 cli/tests/test_install_ps1.py
git commit -m "feat(install): auto-install pyyaml into the hook interpreter, warn only on failure"
```

---

### Task 6: Registry-safe PATH write — giữ REG_EXPAND_SZ (3A)

**Files:**
- Modify: `install.ps1` (khối PATH, dòng ~66-70)
- Modify: `cli/tests/test_install_ps1.py`

**Interfaces:**
- Consumes: `$BinDir` đã có.
- Produces: PATH ghi qua `Microsoft.Win32.Registry` giữ nguyên value-kind; dedup theo segment.

- [ ] **Step 1: Viết failing static tests**

```python
def test_path_write_is_registry_safe(ps1_text):
    # SetEnvironmentVariable flattens REG_EXPAND_SZ -> REG_SZ and writes back
    # the EXPANDED value, hardcoding other tools' %VAR% PATH entries.
    assert "SetEnvironmentVariable" not in ps1_text
    assert "GetEnvironmentVariable" not in ps1_text
    assert "DoNotExpandEnvironmentNames" in ps1_text
    assert "GetValueKind" in ps1_text
```

- [ ] **Step 2: Chạy để xác nhận fail**

Run: `.venv/bin/python -m pytest cli/tests/test_install_ps1.py::test_path_write_is_registry_safe -v` → FAIL.

- [ ] **Step 3: Sửa `install.ps1`**

Thay khối:

```powershell
$UserPath = [Environment]::GetEnvironmentVariable('Path', 'User')
if ($UserPath -notlike "*$BinDir*") {
    $NewPath = if ([string]::IsNullOrEmpty($UserPath)) { $BinDir } else { "$UserPath;$BinDir" }
    [Environment]::SetEnvironmentVariable('Path', $NewPath, 'User')
    Write-Host "-> Added $BinDir to your user PATH. Open a new terminal to use 'maika'."
}
```

Bằng:

```powershell
# Append to user PATH via the registry API: read RAW (unexpanded) value and
# preserve the value kind, so REG_EXPAND_SZ entries like %JAVA_HOME%\bin survive.
$EnvKey = [Microsoft.Win32.Registry]::CurrentUser.OpenSubKey('Environment', $true)
try {
    $RawPath = [string]$EnvKey.GetValue('Path', '', [Microsoft.Win32.RegistryValueOptions]::DoNotExpandEnvironmentNames)
    $Kind = if ($EnvKey.GetValueNames() -contains 'Path') { $EnvKey.GetValueKind('Path') } else { [Microsoft.Win32.RegistryValueKind]::ExpandString }
    $Segments = $RawPath -split ';' | Where-Object { $_ -ne '' }
    if ($Segments -notcontains $BinDir) {
        $NewPath = if ([string]::IsNullOrEmpty($RawPath)) { $BinDir } else { "$RawPath;$BinDir" }
        $EnvKey.SetValue('Path', $NewPath, $Kind)
        Write-Host "-> Added $BinDir to your user PATH. Open a new terminal to use 'maika'."
    }
} finally {
    $EnvKey.Close()
}
```

- [ ] **Step 4: Chạy lại toàn file test**

Run: `.venv/bin/python -m pytest cli/tests/test_install_ps1.py -v` → PASS.

- [ ] **Step 5: Commit**

```bash
git add install.ps1 cli/tests/test_install_ps1.py
git commit -m "fix(install): preserve REG_EXPAND_SZ user PATH via registry API; segment-based dedup"
```

---

### Task 7: Shim `maika.cmd` — 8.3 short-path fallback cho đường dẫn non-ASCII (5A)

**Files:**
- Modify: `install.ps1` (khối shim, dòng ~62-65)
- Modify: `cli/tests/test_install_ps1.py`

**Interfaces:**
- Consumes: `$MaikaExe` tồn tại thật (Task 3 đã guard pip install).
- Produces: shim luôn pure-ASCII khi 8.3 khả dụng; warning rõ khi không.

- [ ] **Step 1: Viết failing static tests**

```python
def test_shim_handles_non_ascii_paths(ps1_text):
    # -Encoding ASCII mangles paths like C:\Users\Việt\ into '?' — the shim
    # must fall back to the 8.3 short path (pure ASCII by construction).
    assert "ShortPath" in ps1_text
    assert "[^\\x00-\\x7F]" in ps1_text
```

- [ ] **Step 2: Chạy để xác nhận fail**

Run: `.venv/bin/python -m pytest cli/tests/test_install_ps1.py::test_shim_handles_non_ascii_paths -v` → FAIL.

- [ ] **Step 3: Sửa `install.ps1`**

Thay dòng:

```powershell
Set-Content -LiteralPath $Shim -Value "@echo off`r`n`"$MaikaExe`" %*" -Encoding ASCII
```

Bằng:

```powershell
# ASCII shim + non-ASCII clone path (e.g. C:\Users\Việt\) = corrupted target.
# Fall back to the DOS 8.3 short path, which is pure ASCII by construction.
$ShimTarget = $MaikaExe
if ($ShimTarget -match '[^\x00-\x7F]') {
    try {
        $Fso = New-Object -ComObject Scripting.FileSystemObject
        $ShimTarget = $Fso.GetFile($MaikaExe).ShortPath
    } catch {
        Write-Warning "Could not resolve an 8.3 short path for $MaikaExe."
    }
    if ($ShimTarget -match '[^\x00-\x7F]') {
        Write-Warning "Install path contains non-ASCII characters and 8.3 names are unavailable; the 'maika' shim may not work. Clone Maika under an ASCII-only path to fix."
    }
}
Set-Content -LiteralPath $Shim -Value "@echo off`r`n`"$ShimTarget`" %*" -Encoding ASCII
```

- [ ] **Step 4: Chạy lại toàn file test**

Run: `.venv/bin/python -m pytest cli/tests/test_install_ps1.py -v` → PASS.

- [ ] **Step 5: Commit**

```bash
git add install.ps1 cli/tests/test_install_ps1.py
git commit -m "fix(install): 8.3 short-path fallback so maika.cmd survives non-ASCII install paths"
```

---

### Task 8: Non-interactive passthrough cho cả 2 installer (C3-A)

**Files:**
- Modify: `install.ps1` (param block + scaffold calls)
- Modify: `install.sh` (forward args sau `$1`)
- Modify: `cli/tests/test_install_ps1.py`

**Interfaces:**
- Consumes: CLI flags có sẵn của `maika init`: `--yes` (đòi `--platform` + `--language`), `--platform`, `--language`, `--mcp` (repeatable) — `cli/maika.py:47-87`.
- Produces: `.\install.ps1 <target> -Yes -Platform claude-code -Language python` chạy headless. Task 10 (CI) gọi đúng dạng này.

- [ ] **Step 1: Viết failing static tests**

```python
def test_supports_non_interactive_install(ps1_text):
    # CI and scripted provisioning need a promptless fresh install.
    assert "[switch]$Yes" in ps1_text
    assert "'--yes'" in ps1_text
    assert "'--platform'" in ps1_text
    assert "'--language'" in ps1_text
    assert "'--mcp'" in ps1_text
```

- [ ] **Step 2: Chạy để xác nhận fail**

Run: `.venv/bin/python -m pytest cli/tests/test_install_ps1.py::test_supports_non_interactive_install -v` → FAIL.

- [ ] **Step 3: Sửa `install.ps1`**

Param block:

```powershell
[CmdletBinding()]
param(
    [Parameter(Mandatory = $true, Position = 0)]
    [string]$Target,
    [switch]$Yes,
    [string]$Platform,
    [string]$Language,
    [string[]]$Mcp = @()
)
```

Ngay trước khối `Push-Location $MaikaRoot`, dựng arg list dùng chung:

```powershell
$ScaffoldArgs = @('--target', $Target, '--hook-python', $HookPython)
if ($Yes) { $ScaffoldArgs += '--yes' }
if ($Platform) { $ScaffoldArgs += @('--platform', $Platform) }
if ($Language) { $ScaffoldArgs += @('--language', $Language) }
foreach ($m in $Mcp) { $ScaffoldArgs += @('--mcp', $m) }
```

Và 2 scaffold call thành (update không nhận --yes/--platform/--language nên giữ args riêng):

```powershell
    if ($Existing) {
        Write-Host "-> Existing Maika install detected — updating."
        & $VenvPy -m cli.maika update --target $Target --hook-python $HookPython
        if ($LASTEXITCODE -ne 0) { throw "cli.maika update failed (exit $LASTEXITCODE)." }
    } else {
        Write-Host "-> Fresh install."
        & $VenvPy -m cli.maika init @ScaffoldArgs
        if ($LASTEXITCODE -ne 0) { throw "cli.maika init failed (exit $LASTEXITCODE)." }
    }
```

- [ ] **Step 4: Sửa `install.sh`**

Sau `TARGET="${1:-}"` + validation, thêm forward mọi arg còn lại (chỉ áp cho init — update vốn non-interactive):

```bash
shift || true
EXTRA_INIT_ARGS=("$@")   # forwarded verbatim to `cli.maika init` (e.g. --yes --platform ... --language ...)
```

Và init call (dòng 53) thành:

```bash
  ( cd "$Maika_ROOT" && "$PY" -m cli.maika init --target "$TARGET" ${EXTRA_INIT_ARGS[@]+"${EXTRA_INIT_ARGS[@]}"} )
```

(Dạng `${arr[@]+...}` an toàn với `set -u` khi mảng rỗng.)

- [ ] **Step 5: Chạy lại + syntax check**

Run: `.venv/bin/python -m pytest cli/tests/test_install_ps1.py -v` → PASS.
Run: `bash -n install.sh` → exit 0.

- [ ] **Step 6: Commit**

```bash
git add install.ps1 install.sh cli/tests/test_install_ps1.py
git commit -m "feat(install): non-interactive passthrough (-Yes/-Platform/-Language/-Mcp) for headless installs"
```

---

### Task 9: Fix test đỏ có sẵn — mtime determinism (D16/W3)

**Files:**
- Modify: `cli/tests/test_dashboard_server.py:67-91`

**Interfaces:**
- Consumes: `_collect_artifacts` sort theo `(st_mtime, name)` (`cli/dashboard/server.py:196`) — hành vi product ĐÚNG (thứ tự thời gian), KHÔNG sửa product (dashboard freeze P6).
- Produces: suite xanh 240/240 — baseline cho Task 10.

- [x] **Step 1: Hiểu root cause (đã điều tra sẵn)**

Test ghi 2 file handoff cách nhau < 1 kernel tick → mtime bằng nhau → tiebreak theo tên → `napas-agent` xếp trước `napas-human`. Test flaky theo tốc độ máy, không phải bug product.

- [x] **Step 2: Sửa test — mtime tường minh**

Trong `test_snapshot_includes_subagent_handoff_prompts`, sau khi ghi 2 file và TRƯỚC `registry.register(...)`, thêm (file đã có import `textwrap`; thêm `import os`, `import time` đầu file nếu chưa có):

```python
    # Force distinct mtimes: both writes can land in the same kernel tick,
    # and _collect_artifacts orders by (mtime, name) — chronological intent.
    human = active / "TASK_HANDOFF.napas-human.md"
    agent = active / "TASK_HANDOFF.napas-agent.md"
    now = time.time()
    os.utime(human, (now - 10, now - 10))
    os.utime(agent, (now, now))
```

(Đổi 2 lệnh `(active / "TASK_HANDOFF....").write_text(...)` hiện tại sang gán biến `human`/`agent` trước rồi `.write_text(...)` để tái dùng.)

- [x] **Step 3: Chạy test — lặp để chắc deterministic**

Run: `.venv/bin/python -m pytest cli/tests/test_dashboard_server.py -q && for i in 1 2 3; do .venv/bin/python -m pytest cli/tests/test_dashboard_server.py::test_snapshot_includes_subagent_handoff_prompts -q; done`
Expected: PASS mọi lần.

- [x] **Step 4: Chạy full suite**

Run: `.venv/bin/python -m pytest cli/tests/ -q`
Expected: **0 failed** (toàn bộ xanh lần đầu tiên).

- [x] **Step 5: Commit**

```bash
git add cli/tests/test_dashboard_server.py
git commit -m "test(dashboard): pin handoff mtimes — snapshot ordering test was flaky by kernel-tick"
```

---

### Task 10: CI — pytest matrix + install.ps1 E2E thật trên windows-latest (7A)

**Files:**
- Create: `.github/workflows/ci.yml`

**Interfaces:**
- Consumes: passthrough flags từ Task 8; suite xanh từ Task 9; auto-pyyaml từ Task 5 (E2E đi qua path này thật vì runner sạch).
- Produces: mọi PR sau này chạy Linux byte-identical guard + Windows render + bootstrap E2E tự động.

- [ ] **Step 1: Tạo `.github/workflows/ci.yml`**

```yaml
name: CI

on:
  push:
    branches: [main]
  pull_request:

jobs:
  tests:
    strategy:
      fail-fast: false
      matrix:
        os: [ubuntu-latest, windows-latest]
    runs-on: ${{ matrix.os }}
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"
      - name: Install package + test deps
        run: python -m pip install -e . pytest
      - name: Run test suite
        run: python -m pytest cli/tests/ -q

  install-ps1-e2e:
    runs-on: windows-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"
      - name: Fresh install into temp project (headless)
        shell: pwsh
        run: |
          New-Item -ItemType Directory -Force -Path "$env:RUNNER_TEMP\demo" | Out-Null
          .\install.ps1 "$env:RUNNER_TEMP\demo" -Yes -Platform claude-code -Language python
      - name: Assert Windows-rendered artifacts
        shell: pwsh
        run: |
          if (-not (Test-Path ".venv\Scripts\maika.exe")) { throw "maika.exe missing — editable install broke" }
          $settings = Get-Content "$env:RUNNER_TEMP\demo\.claude\settings.json" -Raw
          if ($settings -match '/usr/bin/python3') { throw "Unix python path leaked into Windows hooks" }
          if ($settings -match '\$\(git rev-parse') { throw "Unix shell substitution leaked into Windows hooks" }
          if ($settings -notmatch 'write_gate\.py') { throw "write-gate hook command missing" }
          $resolved = Get-Content "$env:RUNNER_TEMP\demo\.claude\resolved-config.yaml" -Raw
          if ($resolved -notmatch 'hook_python') { throw "hook_python not persisted in resolved-config" }
      - name: Bare update preserves launcher (regression 1A, E2E)
        shell: pwsh
        run: |
          & .venv\Scripts\python.exe -m cli.maika update --target "$env:RUNNER_TEMP\demo"
          if ($LASTEXITCODE -ne 0) { throw "maika update failed" }
          $settings = Get-Content "$env:RUNNER_TEMP\demo\.claude\settings.json" -Raw
          if ($settings -match '/usr/bin/python3') { throw "update re-rendered Unix hooks on Windows" }
```

- [ ] **Step 2: Validate YAML cục bộ**

Run: `.venv/bin/python -c "import yaml; yaml.safe_load(open('.github/workflows/ci.yml')); print('yaml ok')"`
Expected: `yaml ok`

- [ ] **Step 3: Commit**

```bash
git add .github/workflows/ci.yml
git commit -m "ci: pytest matrix (ubuntu+windows) + install.ps1 fresh-install E2E on windows-latest"
```

- [ ] **Step 4: Sau khi push — xác nhận cả 3 job xanh trên GitHub Actions trước khi merge.**

---

### Task 11: Docs — limitation mixed-OS + residual write-gate (T10: C4-A + C1-B)

**Files:**
- Modify: `docs/superpowers/specs/2026-07-02-windows-native-support-design.md` (thêm §9)
- Modify: `README.md` (Quickstart: thêm Windows + limitation)

**Interfaces:**
- Consumes: quyết định C1-B, C4-A của review; TODOS W1/W2.
- Produces: giới hạn được ghi ở nơi user sẽ tìm.

- [ ] **Step 1: Thêm section residual vào design doc**

Cuối `docs/superpowers/specs/2026-07-02-windows-native-support-design.md` (sau §8), thêm:

```markdown
## 9. Residual risks (bổ sung từ eng review 2026-07-03)

| Residual | Trạng thái |
|----------|-----------|
| **Write-gate parser mù verb Windows** — `parse_shell_writes` chỉ nhận verb Unix (`tee/cp/mv/install/dd`, `/dev/null`); ghi qua `copy`/`xcopy`/`robocopy`/`Set-Content`/`Out-File` KHÔNG bị gate trên Windows. Success criterion #2 vì vậy chỉ đúng cho write qua tool `Edit/Write` và shell POSIX. | Chấp nhận tạm — spec follow-up tại TODOS **W1** (điều tra shell thực tế của 3 runtime trước khi mở rộng parser). |
| **Mixed-OS team churn** — hook files là framework-owned, committed, nhưng nội dung render theo OS máy chạy `maika init/update` gần nhất → team Windows+Linux sẽ flip command trong git; checkout từ OS khác cần re-run `maika update`. | Chấp nhận (user base hiện tại solo) — document tại README; thiết kế cross-OS tại TODOS **W2** khi có team adoption. |
| **Codex/Antigravity Windows: đường dẫn hook vẫn cwd-relative** — chỉ nhánh Claude được anchor `%CLAUDE_PROJECT_DIR%` (2B); hai runtime kia chưa validate hành vi hook trên Windows. | Chấp nhận — mở rộng anchor sau khi validate runtime. |
```

- [ ] **Step 2: Thêm Windows vào README Quickstart**

Trong `README.md`, sau khối cài đặt Linux (quanh dòng 46 `./install.sh /path/to/your-project`), thêm:

```markdown
**Windows (PowerShell):**

```powershell
.\install.ps1 C:\path\to\your-project
# Headless (CI/script): .\install.ps1 C:\path\to\project -Yes -Platform claude-code -Language python
```

> ⚠️ **Giới hạn mixed-OS:** file hook được render theo OS của máy chạy `maika init/update` gần nhất. Team dùng chung repo trên cả Windows lẫn Linux sẽ thấy hook command đổi qua lại trong git — mỗi máy cần chạy lại `maika update` sau khi checkout từ OS khác. Xem TODOS W2.
```

- [ ] **Step 3: Kiểm tra render markdown không vỡ**

Run: `.venv/bin/python -m pytest cli/tests/ -q` (đảm bảo không test nào snapshot README/design doc)
Expected: 0 failed.

- [ ] **Step 4: Commit**

```bash
git add docs/superpowers/specs/2026-07-02-windows-native-support-design.md README.md
git commit -m "docs: record Windows residual risks (write-gate verbs, mixed-OS churn) + Windows quickstart"
```

---

## Thứ tự & phụ thuộc

```
Task 1 (persist) ─┐
Task 2 (anchor)  ─┤  độc lập, chạy song song được
Task 9 (red test)─┤
                  │
Task 3 → 4 → 5 → 6 → 7 → 8   (tuần tự — cùng sửa install.ps1)
                  │
Task 10 (CI)  ← cần Task 8 (headless flags) + Task 9 (suite xanh) + Task 1 (assert resolved-config)
Task 11 (docs) — độc lập, làm cuối cùng để phản ánh trạng thái thật
```

## Notes for the implementer

- **Đừng đụng nhánh `{% else %}`** của bất kỳ hook template nào — `test_linux_command_byte_identical` sẽ chặn; đó là ràng buộc cứng.
- **Đừng đụng `write_gate.py`** — mọi thay đổi ở đó thuộc TODOS W1, ngoài scope.
- **Đừng đụng `cli/dashboard/server.py`** — dashboard freeze ở P6; Task 9 fix TEST, không fix product.
- Task 2 Step 6 (verify `%CLAUDE_PROJECT_DIR%` expand trên Windows thật) là giả định duy nhất chưa được verify bằng máy thật — nếu sai, rollback template + ghi vào TODOS W1, phần còn lại của plan không bị ảnh hưởng.
- Static test của `install.ps1` là guard chống drift, không thay được E2E — E2E thật nằm ở Task 10.
