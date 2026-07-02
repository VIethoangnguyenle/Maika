# Windows Native Support — Design

> **Date:** 2026-07-02
> **Status:** Approved (design) — ready for implementation plan
> **Scope:** Cho phép Maika bootstrap + chạy trên **Windows native** (PowerShell/cmd, Python
> native), phủ cả 3 platform hook (Claude Code, Codex, Antigravity). Ràng buộc cứng:
> **bản Linux không đổi hành vi (byte-identical).**

---

## 1. Bối cảnh & vấn đề

Maika hiện giả định môi trường Unix ở hai lớp:

1. **Bootstrap** — `install.sh` là bash thuần: tạo venv tại `.venv/bin`, `pip install -e`,
   rồi `ln -sf` symlink console-script vào `~/.local/bin`. Không chạy trên Windows.
2. **Hook command string** — 3 template hook nhúng cú pháp shell Unix:
   - `hooks/claude-code/settings.json`: `python3 "$CLAUDE_PROJECT_DIR"/…/write_gate.py …`
   - `hooks/codex/hooks.json`: `/usr/bin/python3 "$(git rev-parse --show-toplevel)/…/write_gate.py" …`
   - `hooks/antigravity/hooks.json`: giống Codex.

Phần lõi (`cli/` , `cli/scaffold.py`, `write_gate.py`) **đã portable**: dùng `pathlib`,
`as_posix()`, `Path.cwd()`, không hard-code separator. Rào cản chỉ nằm ở 2 lớp trên.

### Phát hiện then chốt

`write_gate.py` **không** nhận `$(git rev-parse …)` hay `$CLAUDE_PROJECT_DIR` làm tham số.
Nó lấy project root từ `Path.cwd()` (`write_gate.py:293`) và đọc mọi artifact
(`.maika/knowledge/…`) tương đối theo cwd. Hai biểu thức shell trong hook command **chỉ
dùng để dựng đường dẫn tới file script**.

Hệ quả: vì script đã dựa vào `cwd = project root` để hoạt động, **runtime chắc chắn chạy
hook với cwd = project root** (nếu không, gate hiện tại đã hỏng trên Linux). Do đó có thể
trỏ tới script bằng **đường dẫn tương đối theo cwd**, loại bỏ hoàn toàn `$(…)` và env var.
Đây là nền tảng của "Hướng B".

## 2. Quyết định thiết kế (locked)

| ID | Quyết định | Lý do |
|----|-----------|-------|
| **D1** | Auto-detect OS ở **scaffold-time** (`maika init/update`) qua `platform.system()`, không cờ tay. | User chạy init trên máy đích → OS phát hiện = OS đích. Không thêm platform/interface mới. |
| **D2** | Nhánh **Linux/Unix render byte-identical** chuỗi hook hiện tại. Chỉ thêm **nhánh Windows** mới. | Ràng buộc cứng: Linux không đổi hành vi. Test snapshot khoá cơ học điều này. |
| **D3** | Hook portable theo **Hướng B**: bỏ shell substitution, trỏ script bằng đường dẫn tương đối theo cwd; nhánh OS chỉ để chọn `python` (Windows) vs `python3`/`/usr/bin/python3` (Unix nguyên xi). | Biến "3 chuỗi × 2 OS × cú pháp shell" thành "1 chuỗi + 1 nhánh python nhỏ". Loại phụ thuộc vào shell runtime dùng trên Windows. Net-negative complexity. |
| **D4** | `write_gate.py` **không đổi**. | Đã portable (cwd + pathlib). |
| **D5** | Bootstrap Windows = `install.ps1` **song song** với `install.sh` (mirror logic init/update). | User đã chốt PowerShell script. |
| **D6** | Đưa `maika` lên PATH (Windows): tạo shim `maika.cmd` trong `%LOCALAPPDATA%\Maika\bin` trỏ tới `.venv\Scripts\maika.exe`, thêm thư mục đó vào **user PATH** qua `setx` nếu chưa có. | Đối xứng ý định symlink của `install.sh`; tránh symlink (Windows cần admin/dev-mode). |
| **D7** | Trên Windows, `python` hệ thống (cái runtime gọi trong hook) phải có `pyyaml`. `install.ps1` kiểm tra & cảnh báo. | Đối xứng giả định sẵn có trên Linux (hook gọi `python3` hệ thống, cũng cần pyyaml). Hook chạy ngoài venv. |

## 3. Kiến trúc & các thay đổi

### 3.1 Render context — inject cờ OS

`cli/platforms/base.py` → `build_render_context()`:

```python
import platform as _platform
...
return {
    ...
    "is_windows": _platform.system() == "Windows",
}
```

- Một khóa boolean duy nhất, có ở mọi platform (đặt ở `BasePlatform`, không đụng adapter con).
- Là điểm auto-detect duy nhất; không có input thủ công.

### 3.2 Ba hook template — nhánh Jinja `is_windows`

Khuôn chung (ví dụ `hooks/claude-code/settings.json`):

```jinja
{% if is_windows %}
"command": "python {{ platform.framework_root }}/hooks/write-gate/write_gate.py --framework-root {{ platform.framework_root }} --runtime claude"
{% else %}
"command": "python3 \"$CLAUDE_PROJECT_DIR\"/{{ platform.framework_root }}/hooks/write-gate/write_gate.py --framework-root {{ platform.framework_root }} --runtime claude"
{% endif %}
```

- Nhánh `{% else %}` = **chuỗi Linux hiện tại, nguyên xi** (Claude giữ `$CLAUDE_PROJECT_DIR`;
  Codex/Antigravity giữ `/usr/bin/python3 "$(git rev-parse --show-toplevel)/…"`).
- Nhánh Windows: `python` + đường dẫn **tương đối** `{{ platform.framework_root }}/hooks/write-gate/write_gate.py`
  (bỏ `$CLAUDE_PROJECT_DIR` / `$(git rev-parse …)`), giữ nguyên `--framework-root` và `--runtime`.
- Áp cùng khuôn cho cả 3 file, mỗi file giữ đúng `--runtime` tương ứng
  (`claude` / `codex` / `antigravity`) và matcher hiện có.

> **Lưu ý JSON hợp lệ:** vì file là `.json` render bằng Jinja, cần đảm bảo khối
> `{% if %}/{% else %}/{% endif %}` không phá cấu trúc JSON (chỉ thay giá trị chuỗi
> `command`). Test render + `json.loads` xác nhận cho cả hai nhánh.

### 3.3 Bootstrap — `install.ps1`

Mirror `install.sh`, cùng luồng route:

```powershell
# install.ps1 — Usage: .\install.ps1 C:\path\to\project
param([Parameter(Mandatory)][string]$Target)

$MaikaRoot = $PSScriptRoot
$Venv = Join-Path $MaikaRoot ".venv"

# 1. Resolve Python (thử `python`, fallback `py -3`); fail nếu < 3.8.
# 2. Nếu chưa có venv: `python -m venv .venv`;
#    `.venv\Scripts\pip install --upgrade pip`;
#    `.venv\Scripts\pip install "jinja2>=3.1" "pyyaml>=6.0"`.
# 3. `.venv\Scripts\pip install -e $MaikaRoot`  → tạo `.venv\Scripts\maika.exe`.
# 4. Expose `maika` (xem 3.4).
# 5. Cảnh báo nếu `python -c "import yaml"` fail (D7).
# 6. Route: nếu tồn tại resolved-config.yaml (native/legacy roots) → update, else init:
#    & "$Venv\Scripts\python.exe" -m cli.maika (init|update) --target $Target
```

Khác biệt so với bản bash: Python ở `.venv\Scripts\python.exe` (không phải `bin/`);
không `ln -sf`.

### 3.4 `maika` trên PATH (Windows) — D6

- Tạo `%LOCALAPPDATA%\Maika\bin\maika.cmd` (shim gọi `"<MaikaRoot>\.venv\Scripts\maika.exe" %*`).
- Nếu `%LOCALAPPDATA%\Maika\bin` chưa nằm trong user PATH → `setx PATH "…"` thêm vào,
  in nhắc mở lại terminal.
- In đường dẫn đã cài (đối xứng dòng thông báo của `install.sh`).

## 4. Data flow

```text
maika init/update  (chạy trên Windows)
   └─ Platform.build_render_context()  → is_windows = True
        └─ scaffold_plugins() render 3 hook template
             └─ nhánh {% if is_windows %} → command "python …/write_gate.py (đường dẫn tương đối)"
   ⇒ file hook trong project là cụ thể-theo-OS Windows

Runtime (agent) kích hoạt PreToolUse hook
   └─ chạy command với cwd = project root
        └─ `python .maika/hooks/write-gate/write_gate.py --framework-root .maika --runtime X`
             └─ write_gate.py dùng Path.cwd() = project root  (không đổi)
```

Trên Linux: `is_windows = False` → nhánh `else` → chuỗi hiện tại → hành vi không đổi.

## 5. Error handling

- **install.ps1**: thiếu `$Target` hoặc thư mục không tồn tại → in usage, exit 1
  (đối xứng `install.sh`). Python < 3.8 hoặc không tìm thấy → thông báo rõ, exit 1.
- **pyyaml thiếu ở system python (D7)**: cảnh báo (không fail bootstrap, vì CLI dùng venv;
  chỉ hook runtime cần system python có yaml).
- **Hook render**: nếu khối Jinja tạo JSON hỏng → test render bắt được trước khi ship.

## 6. Kế hoạch test

| Test | Mục đích |
|------|----------|
| **Linux byte-identical (quan trọng nhất)** | Render 3 hook template với `is_windows=False`, so **byte-for-byte** với chuỗi Linux hiện tại (snapshot). Khoá cơ học rằng nhánh `else` không trôi. |
| **Windows render** | Render với `is_windows=True`: khẳng định KHÔNG còn `/usr/bin/python3`, `$(git rev-parse`, `$CLAUDE_PROJECT_DIR`; CÓ `python ` + đường dẫn tương đối `…/hooks/write-gate/write_gate.py`; giữ đúng `--runtime` mỗi file. |
| **JSON hợp lệ 2 nhánh** | `json.loads` output render cho cả `is_windows` True/False, cả 3 file. |
| **Context** | `build_render_context()` có khóa `is_windows` khớp `platform.system()`. |
| **Snapshot** | Bổ sung biến thể `is_windows` vào `cli/tests/test_snapshots.py` nếu snapshot phủ hook. |

`write_gate.py`: không đổi → không thêm test.

## 7. Ngoài scope (lần này)

- Hook chạy **1-file-cross-OS** ở runtime (đã chốt scaffold-time thay vì runtime detect).
- Tài liệu/hỗ trợ **WSL**.
- Bất kỳ thay đổi nào lên **bản Linux** (chuỗi hook Linux giữ nguyên xi).
- `install.bat` cho cmd.exe (chỉ làm `install.ps1`).

## 8. Tiêu chí thành công

1. Trên Windows native: `.\install.ps1 <project>` bootstrap thành công, `maika` gọi được
   sau khi mở lại terminal.
2. 3 file hook sinh ra trên Windows không chứa cú pháp shell Unix, và write-gate chặn/cho
   qua đúng như trên Linux (dựa vào `cwd`).
3. Test Linux byte-identical PASS → chứng minh hành vi Linux không đổi.
4. `pytest` xanh trên cả hai nhánh render.
