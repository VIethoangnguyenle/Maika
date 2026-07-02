# Windows Native Support Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Cho phép Maika bootstrap + chạy hook trên Windows native, tự phát hiện OS lúc `maika init/update`, mà không đổi hành vi bản Linux (byte-identical).

**Architecture:** Inject một cờ boolean `is_windows` (phát hiện qua `platform.system()`) vào render context tại `BasePlatform.build_render_context()`. Ba hook template thêm nhánh Jinja `{% if is_windows %}`: nhánh Windows dùng `python` + đường dẫn script **tương đối theo cwd** (bỏ `$(git rev-parse …)` và `$CLAUDE_PROJECT_DIR`); nhánh `{% else %}` giữ nguyên xi chuỗi Linux hiện tại. Bổ sung `install.ps1` mirror `install.sh`.

**Tech Stack:** Python 3.8+, Jinja2, PyYAML, PowerShell 5.1+, pytest.

## Global Constraints

- **Linux byte-identical:** chuỗi command của 3 hook khi render với `is_windows=False` phải **giống nguyên văn** bản hiện tại. (Spec D2)
- **`write_gate.py` KHÔNG đổi** — đã portable (dùng `Path.cwd()` + `pathlib`). (Spec D4)
- **Auto-detect scaffold-time:** OS phát hiện qua `platform.system()` tại `build_render_context()`, không cờ tay. (Spec D1)
- **Không thêm platform/interface mới:** chỉ một khóa boolean `is_windows` ở `BasePlatform` (áp cho mọi adapter con). (Spec D1)
- **Dependency floors:** `jinja2>=3.1`, `pyyaml>=6.0`, Python `>=3.8` (đối xứng `install.sh`).
- **Renderer đã cấu hình `trim_blocks=True, lstrip_blocks=True`** (`cli/renderer.py:33-34`) — đặt tag khối `{% %}` ở **đầu dòng riêng** để nội dung giữ nguyên indent (xem Task 2).
- **`framework_root` theo platform:** claude-code = `.claude`; codex & antigravity = `.agents`. Dùng đúng giá trị này trong chuỗi kỳ vọng của test.

---

### Task 1: Inject `is_windows` vào render context

**Files:**
- Modify: `cli/platforms/base.py` (thêm import `platform` + khóa `is_windows` trong `build_render_context`)
- Test: `cli/tests/test_platforms.py`

**Interfaces:**
- Consumes: `BasePlatform.build_render_context(mcps, language)` (hiện có).
- Produces: render context dict có khóa `"is_windows": bool` == `platform.system() == "Windows"`. Task 2 tiêu thụ khóa này trong template.

- [ ] **Step 1: Write the failing test**

Thêm vào cuối `cli/tests/test_platforms.py`:

```python
def test_build_render_context_includes_is_windows_flag():
    import platform as _platform
    ctx = get_platform("claude-code").build_render_context([], "python")
    assert "is_windows" in ctx
    assert ctx["is_windows"] == (_platform.system() == "Windows")
    assert isinstance(ctx["is_windows"], bool)


def test_is_windows_flag_present_for_every_platform():
    from cli.platforms import PLATFORMS
    for key in PLATFORMS:
        ctx = get_platform(key).build_render_context([], "python")
        assert "is_windows" in ctx, f"{key} missing is_windows"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/python -m pytest cli/tests/test_platforms.py::test_build_render_context_includes_is_windows_flag -v`
Expected: FAIL — `KeyError: 'is_windows'` / assert `"is_windows" in ctx` là False.

- [ ] **Step 3: Write minimal implementation**

Trong `cli/platforms/base.py`, thêm import ở đầu file (cạnh các import hiện có):

```python
import platform as _platform
```

Trong `build_render_context` (`base.py:183`), thêm khóa vào dict trả về (cạnh `"framework_version"`):

```python
        return {
            "platform": {
                "name": self.name,
                "display_name": self.display_name,
                "config_entry_point": self.config_entry_point,
                "framework_root": self.framework_root,
            },
            "tools": self.tool_mapping,
            "capabilities": self.capabilities,
            "mcps": mcps,
            "language": language,
            "framework_version": FRAMEWORK_VERSION,
            "is_windows": _platform.system() == "Windows",
        }
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv/bin/python -m pytest cli/tests/test_platforms.py -v`
Expected: PASS (cả 2 test mới + các test cũ).

- [ ] **Step 5: Commit**

```bash
git add cli/platforms/base.py cli/tests/test_platforms.py
git commit -m "feat(scaffold): inject is_windows into render context (scaffold-time OS detect)"
```

---

### Task 2: Nhánh OS trong 3 hook template

**Files:**
- Modify: `.maika/hooks/claude-code/settings.json`
- Modify: `.maika/hooks/codex/hooks.json`
- Modify: `.maika/hooks/antigravity/hooks.json`
- Test (create): `cli/tests/test_hook_os_rendering.py`

**Interfaces:**
- Consumes: khóa `is_windows` từ Task 1; `render_string(env, text, context)` (`cli/renderer.py:40`); fixtures `jinja_env`, `maika_root` (`cli/tests/conftest.py`).
- Produces: 3 file hook có nhánh Jinja; hành vi render:
  - `is_windows=False` → chuỗi Linux nguyên văn hiện tại.
  - `is_windows=True` → `python <framework_root>/hooks/write-gate/write_gate.py --framework-root <framework_root> --runtime <rt>` (không `$(…)`, không env var).

- [ ] **Step 1: Write the failing tests**

Tạo `cli/tests/test_hook_os_rendering.py`:

```python
"""Hook command strings must render OS-correctly and keep Linux byte-identical."""

import json
from pathlib import Path

import pytest

from cli.platforms import get_platform
from cli.renderer import render_string


# (template path relative to repo root, platform key, runtime, framework_root)
HOOKS = [
    (".maika/hooks/claude-code/settings.json", "claude-code", "claude", ".claude"),
    (".maika/hooks/codex/hooks.json", "codex", "codex", ".agents"),
    (".maika/hooks/antigravity/hooks.json", "antigravity", "antigravity", ".agents"),
]


def _context(platform_key, is_windows):
    ctx = get_platform(platform_key).build_render_context([], "python")
    ctx["is_windows"] = is_windows  # deterministic regardless of test host OS
    return ctx


def _command(jinja_env, maika_root, template_rel, platform_key, is_windows):
    text = (maika_root / template_rel).read_text(encoding="utf-8")
    rendered = render_string(jinja_env, text, _context(platform_key, is_windows))
    data = json.loads(rendered)  # must stay valid JSON on both branches
    return data["hooks"]["PreToolUse"][0]["hooks"][0]["command"]


# Exact Linux command strings (post-render). Byte-identical guard.
LINUX_EXPECTED = {
    "claude": 'python3 "$CLAUDE_PROJECT_DIR"/.claude/hooks/write-gate/write_gate.py --framework-root .claude --runtime claude',
    "codex": '/usr/bin/python3 "$(git rev-parse --show-toplevel)/.agents/hooks/write-gate/write_gate.py" --framework-root .agents --runtime codex',
    "antigravity": '/usr/bin/python3 "$(git rev-parse --show-toplevel)/.agents/hooks/write-gate/write_gate.py" --framework-root .agents --runtime antigravity',
}


@pytest.mark.parametrize("template_rel,platform_key,runtime,root", HOOKS)
def test_linux_command_byte_identical(jinja_env, maika_root, template_rel, platform_key, runtime, root):
    cmd = _command(jinja_env, maika_root, template_rel, platform_key, is_windows=False)
    assert cmd == LINUX_EXPECTED[runtime]


@pytest.mark.parametrize("template_rel,platform_key,runtime,root", HOOKS)
def test_windows_command_portable(jinja_env, maika_root, template_rel, platform_key, runtime, root):
    cmd = _command(jinja_env, maika_root, template_rel, platform_key, is_windows=True)
    expected = f"python {root}/hooks/write-gate/write_gate.py --framework-root {root} --runtime {runtime}"
    assert cmd == expected
    # No Unix-only shell tokens survive on Windows.
    assert "/usr/bin/python3" not in cmd
    assert "$(git rev-parse" not in cmd
    assert "$CLAUDE_PROJECT_DIR" not in cmd


@pytest.mark.parametrize("template_rel,platform_key,runtime,root", HOOKS)
def test_both_branches_valid_json(jinja_env, maika_root, template_rel, platform_key, runtime, root):
    for is_win in (True, False):
        text = (maika_root / template_rel).read_text(encoding="utf-8")
        rendered = render_string(jinja_env, text, _context(platform_key, is_win))
        json.loads(rendered)  # raises if invalid
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv/bin/python -m pytest cli/tests/test_hook_os_rendering.py -v`
Expected: `test_windows_command_portable` FAIL (nhánh Windows chưa tồn tại → hiện vẫn render chuỗi Linux, không khớp `python …`). Các test Linux/JSON PASS (chuỗi hiện tại đã đúng).

- [ ] **Step 3: Edit `.maika/hooks/claude-code/settings.json`**

Thay dòng `command` hiện tại bằng khối if/else. Đặt tag `{% %}` ở đầu dòng (do `lstrip_blocks/trim_blocks` sẽ nuốt whitespace trước tag và newline sau tag → dòng nội dung giữ nguyên indent 12 spaces và byte-identical trên nhánh else).

Từ:

```json
          {
            "type": "command",
            "command": "python3 \"$CLAUDE_PROJECT_DIR\"/{{ platform.framework_root }}/hooks/write-gate/write_gate.py --framework-root {{ platform.framework_root }} --runtime claude"
          }
```

Thành:

```json
          {
            "type": "command",
{% if is_windows %}
            "command": "python {{ platform.framework_root }}/hooks/write-gate/write_gate.py --framework-root {{ platform.framework_root }} --runtime claude"
{% else %}
            "command": "python3 \"$CLAUDE_PROJECT_DIR\"/{{ platform.framework_root }}/hooks/write-gate/write_gate.py --framework-root {{ platform.framework_root }} --runtime claude"
{% endif %}
          }
```

- [ ] **Step 4: Edit `.maika/hooks/codex/hooks.json`**

Giữ dấu phẩy cuối chuỗi command (vì sau nó là `"statusMessage"`). Từ:

```json
          {
            "type": "command",
            "command": "/usr/bin/python3 \"$(git rev-parse --show-toplevel)/{{ platform.framework_root }}/hooks/write-gate/write_gate.py\" --framework-root {{ platform.framework_root }} --runtime codex",
            "statusMessage": "Checking Maika write gate"
          }
```

Thành:

```json
          {
            "type": "command",
{% if is_windows %}
            "command": "python {{ platform.framework_root }}/hooks/write-gate/write_gate.py --framework-root {{ platform.framework_root }} --runtime codex",
{% else %}
            "command": "/usr/bin/python3 \"$(git rev-parse --show-toplevel)/{{ platform.framework_root }}/hooks/write-gate/write_gate.py\" --framework-root {{ platform.framework_root }} --runtime codex",
{% endif %}
            "statusMessage": "Checking Maika write gate"
          }
```

- [ ] **Step 5: Edit `.maika/hooks/antigravity/hooks.json`**

Giống Task 2 Step 4 nhưng `--runtime antigravity`. Từ:

```json
          {
            "type": "command",
            "command": "/usr/bin/python3 \"$(git rev-parse --show-toplevel)/{{ platform.framework_root }}/hooks/write-gate/write_gate.py\" --framework-root {{ platform.framework_root }} --runtime antigravity",
            "statusMessage": "Checking Maika write gate"
          }
```

Thành:

```json
          {
            "type": "command",
{% if is_windows %}
            "command": "python {{ platform.framework_root }}/hooks/write-gate/write_gate.py --framework-root {{ platform.framework_root }} --runtime antigravity",
{% else %}
            "command": "/usr/bin/python3 \"$(git rev-parse --show-toplevel)/{{ platform.framework_root }}/hooks/write-gate/write_gate.py\" --framework-root {{ platform.framework_root }} --runtime antigravity",
{% endif %}
            "statusMessage": "Checking Maika write gate"
          }
```

- [ ] **Step 6: Run tests to verify they pass**

Run: `.venv/bin/python -m pytest cli/tests/test_hook_os_rendering.py -v`
Expected: PASS toàn bộ (Linux byte-identical + Windows portable + JSON hợp lệ 2 nhánh).

- [ ] **Step 7: Run the full suite to confirm no regression (incl. snapshots)**

Run: `.venv/bin/python -m pytest cli/tests/ -q`
Expected: PASS. Nếu `test_snapshots.py` fail vì hook output đổi trên máy Windows-CI, đó là do host OS — nhưng test render ở trên đã ép `is_windows` tường minh nên độc lập host. Trên host Linux, snapshot không đổi (nhánh else byte-identical).

- [ ] **Step 8: Commit**

```bash
git add .maika/hooks/claude-code/settings.json .maika/hooks/codex/hooks.json .maika/hooks/antigravity/hooks.json cli/tests/test_hook_os_rendering.py
git commit -m "feat(hooks): OS-branch hook commands for Windows (Linux byte-identical)"
```

---

### Task 3: `install.ps1` bootstrap cho Windows

**Files:**
- Create: `install.ps1`
- Test (create): `cli/tests/test_install_ps1.py` (regression guard chạy được trên Linux; PowerShell thực thi verify thủ công trên Windows)

**Interfaces:**
- Consumes: `python -m cli.maika (init|update) --target <path>` (entry hiện có); cấu trúc venv Windows `.venv\Scripts\{python.exe,pip.exe,maika.exe}`.
- Produces: `install.ps1` ở repo root, mirror routing của `install.sh`.

- [ ] **Step 1: Write the failing regression test**

Tạo `cli/tests/test_install_ps1.py`:

```python
"""Static guards for the Windows bootstrap script (install.ps1)."""

from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
PS1 = REPO_ROOT / "install.ps1"


def test_install_ps1_exists():
    assert PS1.exists(), "install.ps1 missing at repo root"


@pytest.fixture
def ps1_text():
    return PS1.read_text(encoding="utf-8")


def test_uses_windows_venv_layout(ps1_text):
    # Windows venv puts executables under Scripts\, never bin/.
    assert r"Scripts\python.exe" in ps1_text
    assert "/bin/" not in ps1_text and r"\bin\python" not in ps1_text


def test_routes_init_and_update(ps1_text):
    assert "cli.maika init" in ps1_text
    assert "cli.maika update" in ps1_text


def test_checks_all_resolved_config_roots(ps1_text):
    # Mirror install.sh: .agents, .claude, .maika resolved-config.yaml
    for root in (".agents", ".claude", ".maika"):
        assert f"{root}\\resolved-config.yaml" in ps1_text


def test_installs_dependency_floors(ps1_text):
    assert "jinja2>=3.1" in ps1_text
    assert "pyyaml>=6.0" in ps1_text
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv/bin/python -m pytest cli/tests/test_install_ps1.py -v`
Expected: FAIL — `install.ps1 missing at repo root`.

- [ ] **Step 3: Create `install.ps1`**

```powershell
#Requires -Version 5.1
<#
.SYNOPSIS
  Maika installer for Windows — bootstrap a venv and scaffold/update Maika into a target project.
.EXAMPLE
  .\install.ps1 C:\path\to\your\project
#>
[CmdletBinding()]
param(
    [Parameter(Mandatory = $true, Position = 0)]
    [string]$Target
)

$ErrorActionPreference = 'Stop'

$MaikaRoot = $PSScriptRoot
$Venv = Join-Path $MaikaRoot '.venv'

if (-not (Test-Path -LiteralPath $Target -PathType Container)) {
    Write-Error "Target directory does not exist: $Target"
    exit 1
}
$Target = (Resolve-Path -LiteralPath $Target).Path

# Resolve a Python launcher (`python`, then `py -3`); require >= 3.8.
function Resolve-Python {
    if (Get-Command python -ErrorAction SilentlyContinue) {
        $v = & python -c 'import sys; print("%d.%d" % sys.version_info[:2])' 2>$null
        if ($LASTEXITCODE -eq 0 -and [version]$v -ge [version]'3.8') { return @{ Exe = 'python'; Args = @() } }
    }
    if (Get-Command py -ErrorAction SilentlyContinue) {
        $v = & py -3 -c 'import sys; print("%d.%d" % sys.version_info[:2])' 2>$null
        if ($LASTEXITCODE -eq 0 -and [version]$v -ge [version]'3.8') { return @{ Exe = 'py'; Args = @('-3') } }
    }
    return $null
}

$Py = Resolve-Python
if ($null -eq $Py) {
    Write-Error "Python 3.8+ not found. Install Python and ensure 'python' or 'py' is on PATH."
    exit 1
}

$VenvPy  = Join-Path $Venv 'Scripts\python.exe'
$VenvPip = Join-Path $Venv 'Scripts\pip.exe'

if (-not (Test-Path -LiteralPath $Venv)) {
    Write-Host "-> Creating virtualenv at $Venv"
    & $Py.Exe @($Py.Args) -m venv $Venv
    & $VenvPip install --quiet --upgrade pip
    & $VenvPip install --quiet "jinja2>=3.1" "pyyaml>=6.0"
}

# Install the maika CLI as an editable package (creates .venv\Scripts\maika.exe).
& $VenvPip install --quiet -e $MaikaRoot

# Expose `maika` on PATH via a shim (Windows symlinks need admin/dev-mode).
$BinDir = Join-Path $env:LOCALAPPDATA 'Maika\bin'
New-Item -ItemType Directory -Force -Path $BinDir | Out-Null
$MaikaExe = Join-Path $Venv 'Scripts\maika.exe'
$Shim = Join-Path $BinDir 'maika.cmd'
Set-Content -LiteralPath $Shim -Value "@echo off`r`n`"$MaikaExe`" %*" -Encoding ASCII
Write-Host "-> Installed 'maika' shim -> $Shim"

$UserPath = [Environment]::GetEnvironmentVariable('Path', 'User')
if ($UserPath -notlike "*$BinDir*") {
    [Environment]::SetEnvironmentVariable('Path', "$UserPath;$BinDir", 'User')
    Write-Host "-> Added $BinDir to your user PATH. Open a new terminal to use 'maika'."
}

# The write-gate hook runs OUTSIDE the venv via system `python`; warn if it lacks pyyaml.
& $Py.Exe @($Py.Args) -c "import yaml" 2>$null
if ($LASTEXITCODE -ne 0) {
    Write-Warning "System Python lacks 'pyyaml'; the write-gate hook needs it. Run: $($Py.Exe) -m pip install pyyaml"
}

# Route to update if Maika already installed, else init.
$Configs = @(
    (Join-Path $Target '.agents\resolved-config.yaml'),
    (Join-Path $Target '.claude\resolved-config.yaml'),
    (Join-Path $Target '.maika\resolved-config.yaml')
)
$Existing = $Configs | Where-Object { Test-Path -LiteralPath $_ }

Push-Location $MaikaRoot
try {
    if ($Existing) {
        Write-Host "-> Existing Maika install detected — updating."
        & $VenvPy -m cli.maika update --target $Target
    } else {
        Write-Host "-> Fresh install."
        & $VenvPy -m cli.maika init --target $Target
    }
} finally {
    Pop-Location
}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv/bin/python -m pytest cli/tests/test_install_ps1.py -v`
Expected: PASS toàn bộ.

- [ ] **Step 5: (Manual, Windows only) Smoke-test bootstrap**

Trên một máy Windows có Python 3.8+:

```powershell
mkdir C:\tmp\maika-demo
.\install.ps1 C:\tmp\maika-demo
# mở terminal mới
maika --help
```

Expected: venv tạo tại `.venv\Scripts\`, `maika` gọi được sau khi mở lại terminal, `C:\tmp\maika-demo` có `.claude\` (hoặc root đã chọn) + `settings.json` với command `python .claude/hooks/... --runtime claude` (không `$CLAUDE_PROJECT_DIR`).

- [ ] **Step 6: Commit**

```bash
git add install.ps1 cli/tests/test_install_ps1.py
git commit -m "feat(install): add install.ps1 Windows bootstrap mirroring install.sh"
```

---

## Notes for the implementer

- **Đừng chạm `write_gate.py`** — nó đã portable; mọi thay đổi ở đó là ngoài scope.
- **Đừng đổi nhánh `{% else %}`** của bất kỳ hook nào — test byte-identical (Task 2) sẽ chặn, và đó là ràng buộc cứng "không đụng Linux".
- Nếu test `test_linux_command_byte_identical` fail sau khi sửa template, nguyên nhân gần như chắc chắn là **whitespace do trim/lstrip_blocks**: kiểm tra tag `{% %}` có nằm ở đầu dòng riêng và dòng nội dung giữ đúng 12-space indent.
