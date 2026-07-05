# Agent Memory Activation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Kích hoạt thực sự capability `agent-memory` (backend rohitg00/agentmemory): doctor probe liveness daemon, bootstrap probe chống shim-fallback, hard gate recall trước spec, bỏ M7 staged rollout, dọn docs/manifest.

**Architecture:** Bốn workstream độc lập trên nền cơ chế sẵn có — mở rộng `maika doctor mcp` (Python, `cli/`), thêm validator vào `gate-check` (Python, `.maika/tools/`), siết wording các file procedure/workflow/rule (Markdown template, `.maika/`), và cập nhật manifest/profile. Không đổi provider boundary: framework chỉ phát hiện + báo to, không cài/chạy daemon.

**Tech Stack:** Python 3 (stdlib only — `urllib`, `re`), pytest, Jinja-rendered Markdown templates.

**Spec:** `docs/superpowers/specs/2026-07-05-agent-memory-activation-design.md`

## Global Constraints

- Interpreter test: **`/usr/bin/python3 -m pytest …`** (`.venv` của repo thiếu `jsonschema` — không dùng `.venv`). Chạy từ repo root `/home/zane/Desktop/Maika`. Đọc **full output** pytest, không tin one-line summary.
- **Không thêm dependency mới** — probe HTTP dùng stdlib `urllib`.
- **Provider boundary:** không cài, không khởi động, không quản lý daemon agentmemory. `maika doctor mcp --fix` KHÔNG được start daemon.
- Dòng canonical (copy đúng nguyên văn, kể cả `—` em-dash và `·` middle-dot):
  - Recall evidence: `agent-memory recall — query:"<query>" · results:<N> — ảnh hưởng reasoning`
  - Degrade: `agent-memory unavailable — skip recall/save`
  - Healthy (bootstrap): `agent-memory: healthy`
  - Default URL: `http://localhost:3111` (env override: `AGENTMEMORY_URL`)
- Docs trong `.maika/` viết **tiếng Việt**, identifier kỹ thuật giữ tiếng Anh. Code/comment trong `cli/` viết tiếng Anh theo style hiện có.
- KHÔNG hardcode tên tool memory của provider (`memory_recall`, `memory_save`…) trong `.maika/{rules,skills,procedures,workflows}` — luôn dùng `{{ tools.dynamic_memory_* }}`. Guard: `cli/tests/test_no_hardcoded_memory_tools.py`. (Các dòng canonical ở trên an toàn — không chứa tên tool dạng `memory_x`.)
- Tuân `.maika/DEVELOPMENT_RULES.md`: không thêm declaration không có consumer, net-negative complexity.
- File `.md` trong `.maika/` chứa `{{ ` được Jinja render lúc `maika init` bất kể `template: false` (`cli/scaffold.py:185-190`) — cứ dùng `{{ tools.* }}` / `{{ platform.* }}` như các file hiện có.

---

### Task 1: Doctor liveness probe cho agent-memory daemon

**Files:**
- Modify: `cli/mcp/doctor.py`
- Modify: `cli/commands/doctor.py`
- Test: `cli/tests/test_mcp_doctor.py`

**Interfaces:**
- Consumes: `DoctorStatus`, `build_doctor_status`, `render_report` hiện có; helper test `write_resolved(target, platform, mcps)` có sẵn trong `test_mcp_doctor.py`.
- Produces: `_probe_memory_daemon(url: str, timeout: float = 2.0) -> bool`; `_memory_daemon_state(selected: list) -> tuple[str, str]`; field mới `DoctorStatus.memory_daemon: str` (`"not-selected" | "running" | "down"`) và `DoctorStatus.memory_daemon_url: str`; hằng `AGENTMEMORY_DEFAULT_URL`, `MEMORY_DAEMON_HINT`. Dòng report: `- agent-memory daemon: RUNNING (<url>)` / `- agent-memory daemon: DOWN (<url>) — start: npm i -g @agentmemory/agentmemory && agentmemory (viewer :3113; deep check: agentmemory doctor)`.

- [ ] **Step 1: Viết failing tests**

Thêm vào cuối `cli/tests/test_mcp_doctor.py`:

```python
def test_probe_memory_daemon_connection_refused_is_down():
    from cli.mcp.doctor import _probe_memory_daemon
    # port 1: không có gì lắng nghe -> connection refused -> DOWN
    assert _probe_memory_daemon("http://127.0.0.1:1", timeout=0.3) is False


def test_probe_memory_daemon_any_http_response_is_up():
    import http.server
    import threading
    from cli.mcp.doctor import _probe_memory_daemon

    # BaseHTTPRequestHandler tra loi 501 cho moi request — van tinh la ALIVE
    # (khong phu thuoc endpoint /health cu the cua upstream)
    server = http.server.HTTPServer(("127.0.0.1", 0), http.server.BaseHTTPRequestHandler)
    thread = threading.Thread(target=server.handle_request, daemon=True)
    thread.start()
    try:
        port = server.server_address[1]
        assert _probe_memory_daemon(f"http://127.0.0.1:{port}", timeout=2.0) is True
    finally:
        server.server_close()


def test_doctor_reports_memory_daemon_down_with_start_hint(tmp_path, monkeypatch):
    target = tmp_path / "proj"
    home = tmp_path / "home"
    write_resolved(target, mcps=["agent-memory"])
    monkeypatch.delenv("AGENTMEMORY_URL", raising=False)
    monkeypatch.setattr("cli.mcp.doctor._probe_memory_daemon", lambda url, timeout=2.0: False)

    run_doctor_mcp(str(target), fix=False, assume_yes=False, home=home)

    text = (target / ".agents" / "knowledge" / "active" / "mcp-doctor-report.md").read_text(encoding="utf-8")
    assert "agent-memory daemon: DOWN (http://localhost:3111)" in text
    assert "npm i -g @agentmemory/agentmemory" in text
    assert "agentmemory doctor" in text


def test_doctor_reports_memory_daemon_running(tmp_path, monkeypatch):
    target = tmp_path / "proj"
    home = tmp_path / "home"
    write_resolved(target, mcps=["agent-memory"])
    monkeypatch.delenv("AGENTMEMORY_URL", raising=False)
    monkeypatch.setattr("cli.mcp.doctor._probe_memory_daemon", lambda url, timeout=2.0: True)

    run_doctor_mcp(str(target), fix=False, assume_yes=False, home=home)

    text = (target / ".agents" / "knowledge" / "active" / "mcp-doctor-report.md").read_text(encoding="utf-8")
    assert "agent-memory daemon: RUNNING (http://localhost:3111)" in text


def test_doctor_memory_daemon_respects_agentmemory_url_env(tmp_path, monkeypatch):
    target = tmp_path / "proj"
    home = tmp_path / "home"
    write_resolved(target, mcps=["agent-memory"])
    monkeypatch.setenv("AGENTMEMORY_URL", "http://127.0.0.1:4222")
    monkeypatch.setattr("cli.mcp.doctor._probe_memory_daemon", lambda url, timeout=2.0: True)

    run_doctor_mcp(str(target), fix=False, assume_yes=False, home=home)

    text = (target / ".agents" / "knowledge" / "active" / "mcp-doctor-report.md").read_text(encoding="utf-8")
    assert "agent-memory daemon: RUNNING (http://127.0.0.1:4222)" in text


def test_doctor_omits_memory_daemon_line_when_not_selected(tmp_path):
    target = tmp_path / "proj"
    home = tmp_path / "home"
    write_resolved(target)  # mcps mặc định: codebase-memory-mcp

    run_doctor_mcp(str(target), fix=False, assume_yes=False, home=home)

    text = (target / ".agents" / "knowledge" / "active" / "mcp-doctor-report.md").read_text(encoding="utf-8")
    assert "agent-memory daemon" not in text
```

- [ ] **Step 2: Chạy test xác nhận fail**

Run: `/usr/bin/python3 -m pytest cli/tests/test_mcp_doctor.py -v`
Expected: 6 test mới FAIL (`ImportError: cannot import name '_probe_memory_daemon'` hoặc assert fail); các test cũ PASS.

- [ ] **Step 3: Implement trong `cli/mcp/doctor.py`**

3a. Sửa block import đầu file:

```python
"""MCP doctor status and report generation."""

import json
import os
import shutil
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path

from cli.mcp.adapters import get_mcp_adapter
from cli.mcp.config import load_mcp_config, redact_mapping, selected_server_matches
from cli.mcp import ua_setup
from cli.scaffold import load_resolved_config, load_manifest

AGENTMEMORY_DEFAULT_URL = "http://localhost:3111"
# Hint shown when the daemon is down. Doctor never starts the daemon itself
# (provider boundary): the end project owns the agentmemory lifecycle.
MEMORY_DAEMON_HINT = (
    "start: npm i -g @agentmemory/agentmemory && agentmemory "
    "(viewer :3113; deep check: agentmemory doctor)"
)
```

3b. Thêm 2 field (có default) vào cuối `DoctorStatus` (sau `setup_reports`):

```python
    memory_daemon: str = "not-selected"   # not-selected | running | down
    memory_daemon_url: str = ""
```

3c. Thêm 2 hàm module-level (đặt sau `_setup_reports`):

```python
def _probe_memory_daemon(url: str, timeout: float = 2.0) -> bool:
    """Any HTTP response (even 4xx/5xx) counts as alive — no dependency on a
    specific /health route. Connection refused, timeout, or a malformed URL
    counts as down."""
    try:
        urllib.request.urlopen(url, timeout=timeout)
        return True
    except urllib.error.HTTPError:
        return True
    except Exception:
        return False


def _memory_daemon_state(selected: list) -> tuple[str, str]:
    if "agent-memory" not in selected:
        return "not-selected", ""
    url = os.environ.get("AGENTMEMORY_URL") or AGENTMEMORY_DEFAULT_URL
    return ("running" if _probe_memory_daemon(url) else "down"), url
```

3d. Trong `build_doctor_status`, sau dòng `adapter = get_mcp_adapter(platform)` thêm:

```python
    memory_daemon, memory_daemon_url = _memory_daemon_state(selected)
```

và thêm vào **cả hai** chỗ khởi tạo `DoctorStatus(...)` (nhánh `best_config is None` và nhánh cuối) hai kwarg:

```python
        memory_daemon=memory_daemon,
        memory_daemon_url=memory_daemon_url,
```

3e. Sửa `render_report` — chèn dòng memory daemon trước Recommendation (đổi cấu trúc return):

```python
def render_report(status: DoctorStatus) -> str:
    config_path = status.config_path.as_posix() if status.config_path else "none"
    matched = ", ".join(status.matched) if status.matched else "none"
    missing = ", ".join(status.missing) if status.missing else "none"
    selected = ", ".join(status.selected_mcps) if status.selected_mcps else "none"
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
        + _render_memory_daemon(status)
        + f"- Recommendation: {status.recommendation}\n"
        + _render_setup_reports(status.setup_reports)
        + _render_matched_config(status.redacted_servers)
    )


def _render_memory_daemon(status: DoctorStatus) -> str:
    if status.memory_daemon == "not-selected":
        return ""
    if status.memory_daemon == "running":
        return f"- agent-memory daemon: RUNNING ({status.memory_daemon_url})\n"
    return f"- agent-memory daemon: DOWN ({status.memory_daemon_url}) — {MEMORY_DAEMON_HINT}\n"
```

3f. Trong `cli/commands/doctor.py`, sau dòng `print(f"  native: {status.native_state} | bridge: {status.bridge_state}")` thêm:

```python
    if status.memory_daemon != "not-selected":
        print(f"  agent-memory daemon: {status.memory_daemon} ({status.memory_daemon_url})")
```

- [ ] **Step 4: Chạy test xác nhận pass**

Run: `/usr/bin/python3 -m pytest cli/tests/test_mcp_doctor.py -v`
Expected: PASS toàn bộ (test cũ + 6 test mới).

- [ ] **Step 5: Commit**

```bash
git add cli/mcp/doctor.py cli/commands/doctor.py cli/tests/test_mcp_doctor.py
git commit -m "feat(doctor): probe agent-memory daemon liveness with start hint"
```

---

### Task 2: Validator `memory-recall` trong gate-check

**Files:**
- Modify: `.maika/tools/gate-check/gates.py`
- Modify: `.maika/tools/gate-check/cli.py`
- Test: `.maika/tools/gate-check/tests/test_gates.py`

**Interfaces:**
- Consumes: `Result`, `_MEMORY_DEGRADE` (regex có sẵn trong `gates.py`), module-load pattern `g.` trong `test_gates.py`.
- Produces: `validate_memory_recall(text: str) -> Result`; regex `_MEMORY_RECALL`; gate CLI name `"memory-recall"` (Task 3 wire vào workflow).

- [ ] **Step 1: Viết failing tests**

Thêm vào `.maika/tools/gate-check/tests/test_gates.py` (sau `test_mcp_status_accepts_agent_memory_probe_and_degrade`):

```python
def test_memory_recall_accepts_canonical_recall_or_degrade():
    recall = ('agent-memory recall — query:"maika refund flow" · results:3 '
              "— ảnh hưởng reasoning")
    assert g.validate_memory_recall(recall).ok is True
    assert g.validate_memory_recall(
        "agent-memory unavailable — skip recall/save"
    ).ok is True


def test_memory_recall_rejects_missing_or_vague_evidence():
    assert g.validate_memory_recall("").ok is False
    assert g.validate_memory_recall("agent-memory recall was considered").ok is False
    # thiếu số kết quả -> fail
    assert g.validate_memory_recall(
        'agent-memory recall — query:"maika refund" · results:unknown'
    ).ok is False
    # prose lan man: anchor cách nhau quá bound -> fail
    rambling = ('agent-memory recall happened, after a long discussion about '
                'the query:"x" we think that maybe the results: 3 were fine')
    assert g.validate_memory_recall(rambling).ok is False
```

- [ ] **Step 2: Chạy test xác nhận fail**

Run: `/usr/bin/python3 -m pytest .maika/tools/gate-check/tests/test_gates.py -v -k memory_recall`
Expected: 2 test FAIL với `AttributeError: module 'gates' has no attribute 'validate_memory_recall'`.

- [ ] **Step 3: Implement**

3a. Trong `gates.py`, ngay sau định nghĩa `_MEMORY_DEGRADE` (dòng ~36), thêm:

```python
# Recall evidence (pre-spec hard gate): canonical line is
#   agent-memory recall — query:"<query>" · results:<N> — ảnh hưởng reasoning
# Anchors: the literal query:"..." and a numeric results:. The {0,10} bounds
# between anchors reject rambling prose (same technique as _DEGRADE).
_MEMORY_RECALL = re.compile(
    r'agent-memory recall.{0,10}query:"[^"]{1,200}".{0,10}results:\s*\d+',
    re.IGNORECASE,
)
```

3b. Sau `validate_mcp_status`, thêm:

```python
def validate_memory_recall(text: str) -> Result:
    """Pre-spec recall evidence (R-Tool-6): either a real recall line
    (query + numeric result count) or the canonical degrade line."""
    if _MEMORY_RECALL.search(text) or _MEMORY_DEGRADE.search(text):
        return Result(True)
    return Result(False, "no agent-memory recall evidence (query+results) or degrade line")
```

3c. Trong `cli.py`, thêm vào dict `VALIDATORS` (sau `"mcp-status"`):

```python
    "memory-recall": "validate_memory_recall",
```

- [ ] **Step 4: Chạy test xác nhận pass**

Run: `/usr/bin/python3 -m pytest .maika/tools/gate-check/tests/test_gates.py -v`
Expected: PASS toàn bộ.

- [ ] **Step 5: Smoke test CLI end-to-end**

```bash
SAMPLE=$(mktemp)
printf 'agent-memory recall — query:"demo payment refund" · results:2 — ảnh hưởng reasoning\n' > "$SAMPLE"
/usr/bin/python3 .maika/tools/gate-check/cli.py memory-recall "$SAMPLE"; echo "exit=$?"
printf 'no evidence here\n' > "$SAMPLE"
/usr/bin/python3 .maika/tools/gate-check/cli.py memory-recall "$SAMPLE"; echo "exit=$?"
rm -f "$SAMPLE"
```

Expected: lần 1 in `PASS`, `exit=0`; lần 2 in `FAIL — no agent-memory recall evidence (query+results) or degrade line`, `exit=1`.

- [ ] **Step 6: Commit**

```bash
git add .maika/tools/gate-check/gates.py .maika/tools/gate-check/cli.py .maika/tools/gate-check/tests/test_gates.py
git commit -m "feat(gate-check): add memory-recall validator for pre-spec recall evidence"
```

---

### Task 3: Wire gate memory-recall vào Pha 2 + rules-tool.md bắt buộc recall

**Files:**
- Modify: `.maika/workflows/task.md` (khoảng dòng 272-274, trong step 5 của Pha 2)
- Modify: `.maika/rules/rules-tool.md` (khoảng dòng 94-96, mục "Ngữ cảnh sử dụng được phép")

**Interfaces:**
- Consumes: gate CLI name `memory-recall` (Task 2); dòng canonical recall + degrade (Global Constraints).
- Produces: bước `[MEMORY-RECALL GATE — R-Tool-6]` trong Pha 2; wording BẮT BUỘC trong rules-tool.md.

- [ ] **Step 1: Sửa `.maika/workflows/task.md`**

Tìm đúng đoạn (trong `5. Khi user xác nhận rõ ràng:`):

```
   - Cập nhật `phase_state: phase-2-in-progress` trong AGENT_TRANSPARENCY.md.
   - Gọi OpenSpec:
```

Thay bằng:

```
   - Cập nhật `phase_state: phase-2-in-progress` trong AGENT_TRANSPARENCY.md.
   - **[MEMORY-RECALL GATE — R-Tool-6]** Trước khi gọi OpenSpec:
     - Nếu `resolved-config.yaml → mcps` chứa `agent-memory`: gọi `{{ tools.dynamic_memory_recall }}`
       (query prefix tên project từ REQUIREMENT.md) và ghi dòng evidence vào AGENT_TRANSPARENCY.md:
       `agent-memory recall — query:"<query>" · results:<N> — ảnh hưởng reasoning`
     - Nếu KHÔNG chứa `agent-memory` (hoặc backend chết): đảm bảo AGENT_TRANSPARENCY.md có dòng degrade
       `agent-memory unavailable — skip recall/save`.
     - Chạy gate: `python3 {{ platform.framework_root }}/tools/gate-check/cli.py memory-recall {{ platform.framework_root }}/knowledge/active/AGENT_TRANSPARENCY.md`
       — PHẢI pass (exit 0) rồi mới được gọi OpenSpec.
   - Gọi OpenSpec:
```

- [ ] **Step 2: Sửa `.maika/rules/rules-tool.md`**

Tìm bullet (mục "Ngữ cảnh sử dụng được phép"):

```
- **Trước spec (Pre-spec)**: `{{ tools.dynamic_memory_recall }}` để tra cứu quyết định kiến trúc trước đó.
```

Thay bằng:

```
- **Trước spec (Pre-spec) — BẮT BUỘC (hard gate `memory-recall`)**: `{{ tools.dynamic_memory_recall }}`
  để tra cứu quyết định kiến trúc trước đó (query prefix tên project). Ghi dòng evidence vào
  `AGENT_TRANSPARENCY.md`: `agent-memory recall — query:"<query>" · results:<N> — ảnh hưởng reasoning`.
  Gate-check `memory-recall` phải PASS trước khi gọi OpenSpec ở Pha 2 (xem `workflows/task.md`);
  không cấu hình / backend chết → dòng degrade chuẩn (mục Degrade bên dưới) cũng pass gate.
```

- [ ] **Step 3: Verify bằng test + grep**

```bash
/usr/bin/python3 -m pytest cli/tests/test_no_hardcoded_memory_tools.py cli/tests/test_rules_tool_evidence.py -v
grep -n "MEMORY-RECALL GATE" .maika/workflows/task.md
grep -n "memory-recall" .maika/rules/rules-tool.md
```

Expected: 2 test file PASS; mỗi grep ra ≥1 dòng.

- [ ] **Step 4: Commit**

```bash
git add .maika/workflows/task.md .maika/rules/rules-tool.md
git commit -m "feat(workflow): enforce memory-recall gate before OpenSpec propose in Pha 2"
```

---

### Task 4: Bootstrap probe hardening — chống shim-fallback giả sống

**Files:**
- Modify: `.maika/procedures/bootstrap.md` (khoảng dòng 173-175, PHASE 5)

**Interfaces:**
- Consumes: dòng canonical healthy/degrade (Global Constraints); gate `mcp-status` hiện có (không đổi).
- Produces: wording probe mới trong bootstrap; không có API mới.

- [ ] **Step 1: Sửa `.maika/procedures/bootstrap.md`**

Tìm đúng đoạn:

```
>   Nếu `resolved-config.yaml` khai báo `agent-memory` → probe `{{ tools.dynamic_memory_health }}` và ghi
>   `🔌 MCP: agent-memory: healthy` (hoặc trạng thái thật). Probe fail/absent → ghi dòng
>   degrade `agent-memory unavailable — skip recall/save`.
```

Thay bằng:

```
>   Nếu `resolved-config.yaml` khai báo `agent-memory` → probe `{{ tools.dynamic_memory_health }}` và CHỈ ghi
>   `🔌 MCP: agent-memory: healthy` khi response xác nhận **kết nối backend daemon thật**.
>   Shim `@agentmemory/mcp` có fallback tool cục bộ khi daemon chết — tool trả lời KHÔNG
>   đồng nghĩa healthy. Probe fail / fallback / absent → ghi dòng degrade
>   `agent-memory unavailable — skip recall/save` + gợi ý chạy `maika doctor mcp --target <repo>`.
```

- [ ] **Step 2: Verify gate mcp-status vẫn nhận dòng canonical + diet test**

```bash
SAMPLE=$(mktemp)
printf '🔌 MCP: agent-memory: healthy\n' > "$SAMPLE"
/usr/bin/python3 .maika/tools/gate-check/cli.py mcp-status "$SAMPLE"; echo "exit=$?"
printf 'agent-memory unavailable — skip recall/save\n' > "$SAMPLE"
/usr/bin/python3 .maika/tools/gate-check/cli.py mcp-status "$SAMPLE"; echo "exit=$?"
rm -f "$SAMPLE"
/usr/bin/python3 -m pytest .maika/tools/gate-check/tests/test_bootstrap_diet.py -v
```

Expected: cả hai lần `PASS`, `exit=0`; diet test PASS.

- [ ] **Step 3: Commit**

```bash
git add .maika/procedures/bootstrap.md
git commit -m "fix(bootstrap): treat agentmemory shim fallback as unhealthy in MCP probe"
```

---

### Task 5: Bỏ M7 staged rollout, giữ 4 tầng lọc

**Files:**
- Modify: `.maika/skills/knowledge-curator/references/m7-memory-push.md`

**Interfaces:**
- Consumes: nội dung file hiện tại (Mục lục dòng ~12, section "Triển khai theo giai đoạn (R-Tool-6)" dòng ~104-126).
- Produces: M7 không còn staged rollout; push tự động từ task đầu; 4 tầng lọc (Tầng 0→3) giữ nguyên.

- [ ] **Step 1: Xóa entry Mục lục**

Xóa dòng sau khỏi mục lục (giữ các dòng khác):

```
- Triển khai theo giai đoạn (R-Tool-6)
```

- [ ] **Step 2: Bổ sung hành vi auto-push vào section Trigger**

Tìm:

```
Gọi SAU `update_knowledge_snapshot` và TRƯỚC `reset_active_context`.
Chỉ khi `status == "completed"` (không push cho stashed/cancelled).
```

Thay bằng:

```
Gọi SAU `update_knowledge_snapshot` và TRƯỚC `reset_active_context`.
Chỉ khi `status == "completed"` (không push cho stashed/cancelled).
Push tự động ngay từ task hoàn thành đầu tiên — không có giai đoạn làm quen.
User có thể từ chối push trực tiếp trong phiên (nói rõ trước khi curator chạy).
```

- [ ] **Step 3: Xóa toàn bộ section staged rollout**

Xóa từ heading `## Triển khai theo giai đoạn (R-Tool-6)` đến hết code block `check_m7_graduation()` (ngay trước `## Ghi AGENT_TRANSPARENCY`) — bao gồm bảng Tuần 1/2/3, đoạn "Graduation trigger", và fenced block chứa `FUNCTION check_m7_graduation():`.

- [ ] **Step 4: Verify**

```bash
grep -n -i "tuần\|graduat\|M7-GRAD\|stage" .maika/skills/knowledge-curator/references/m7-memory-push.md
grep -rn -i "graduat\|M7-GRAD" .maika/ | grep -v ".worktrees"
/usr/bin/python3 -m pytest cli/tests/test_skill_standard.py cli/tests/test_no_hardcoded_memory_tools.py -v
```

Expected: grep 1 không ra dòng nào (exit 1); grep 2 không ra dòng nào; 2 test file PASS.

- [ ] **Step 5: Commit**

```bash
git add .maika/skills/knowledge-curator/references/m7-memory-push.md
git commit -m "feat(m7): remove staged rollout — auto-push from first completed task, keep 4 quality tiers"
```

---

### Task 6: Dọn docs/manifest — bỏ Qdrant stale, cập nhật profile theo upstream

**Files:**
- Modify: `cli/plugin-manifest.yaml` (dòng ~60, capability `agent-memory`)
- Modify: `.maika/rules/rules-tool.md` (dòng ~68-69, R-Tool-6)
- Modify: `.maika/profiles/agent-memory-mcp-only-setup.md`

**Interfaces:**
- Consumes: facts upstream đã xác minh 2026-07-05 (README rohitg00/agentmemory): daemon `npm install -g @agentmemory/agentmemory` → lệnh `agentmemory` (REST `:3111`, viewer `:3113`), `agentmemory doctor`, `agentmemory stop`, shim `npx -y @agentmemory/mcp` + env `AGENTMEMORY_URL`, shim fallback 7 core tools khi daemon chết.
- Produces: docs không còn "Qdrant"; profile có hướng dẫn daemon + cảnh báo shim fallback.

- [ ] **Step 1: Sửa `cli/plugin-manifest.yaml`**

Tìm:

```yaml
  agent-memory:
    provides: memory
    display: "Agent Memory — Kinh nghiệm dài hạn (Qdrant, tham khảo sau task)"
```

Thay bằng:

```yaml
  agent-memory:
    provides: memory
    display: "Agent Memory — Kinh nghiệm dài hạn (agentmemory, tham khảo sau task)"
```

- [ ] **Step 2: Sửa `.maika/rules/rules-tool.md` (R-Tool-6 mở đầu)**

Tìm:

```
`agent-memory` là **lớp kinh nghiệm dài hạn** — những gì agent đã đúc kết và lưu lên
Qdrant *sau* các task trước.
```

Thay bằng:

```
`agent-memory` là **lớp kinh nghiệm dài hạn** — những gì agent đã đúc kết và lưu qua
backend `agentmemory` *sau* các task trước.
```

- [ ] **Step 3: Cập nhật `.maika/profiles/agent-memory-mcp-only-setup.md`**

Thay section `## Setup (verify package/command against upstream before use — example)` (toàn bộ nội dung từ heading đó đến trước `## Do NOT`) bằng:

````markdown
## Setup (đã xác minh với upstream 2026-07-05)

1. Cài và chạy backend daemon (user tự vận hành — Maika không cài/chạy hộ):

   ```
   npm install -g @agentmemory/agentmemory
   agentmemory          # REST API :3111, viewer :3113
   ```

   Chẩn đoán sâu: `agentmemory doctor`. Dừng: `agentmemory stop`.

2. Register the MCP server manually — JSON key MUST be `agent-memory`:

   ```json
   {
     "mcpServers": {
       "agent-memory": {
         "command": "npx",
         "args": ["-y", "@agentmemory/mcp"],
         "env": { "AGENTMEMORY_URL": "http://localhost:3111" }
       }
     }
   }
   ```

## [WARNING] Shim fallback — tool trả lời KHÔNG có nghĩa daemon sống

`@agentmemory/mcp` fallback về 7 core tools cục bộ khi không kết nối được daemon —
tool vẫn xuất hiện trong tool list nhưng không có persistence thật. Kiểm tra thật:
`maika doctor mcp` (probe HTTP tới `AGENTMEMORY_URL`) hoặc `agentmemory doctor`.
Bootstrap probe chỉ được ghi `agent-memory: healthy` khi backend thật trả lời
(xem `procedures/bootstrap.md` PHASE 5).
````

Lưu ý: giữ nguyên các section `## Why MCP-only (hooks OFF)`, `## [CRITICAL] Register the server under the name agent-memory`, `## Do NOT`, `## Result`.

- [ ] **Step 4: Verify**

```bash
grep -rn -i "qdrant" .maika/ cli/ | grep -v ".worktrees"
/usr/bin/python3 -m pytest cli/tests/test_manifest_setup.py cli/tests/test_init.py -v
```

Expected: grep không ra dòng nào (exit 1); 2 test file PASS.

- [ ] **Step 5: Commit**

```bash
git add cli/plugin-manifest.yaml .maika/rules/rules-tool.md .maika/profiles/agent-memory-mcp-only-setup.md
git commit -m "docs(memory): drop stale Qdrant refs, refresh agentmemory setup profile with daemon + shim-fallback facts"
```

---

### Task 7: Verify toàn cục theo tiêu chí spec

**Files:**
- Không sửa file — chỉ chạy verify. Nếu có test fail thì fix trong task này.

**Interfaces:**
- Consumes: toàn bộ output Task 1-6; spec §5 (tiêu chí thành công).

- [ ] **Step 1: Chạy full test suite cả hai khu**

```bash
/usr/bin/python3 -m pytest cli/tests/ -q
/usr/bin/python3 -m pytest .maika/tools/gate-check/tests/ -q
```

Expected: PASS toàn bộ, 0 failed. Đọc full output — không tin summary một dòng.

- [ ] **Step 2: Checklist tiêu chí spec §5**

```bash
# (4) khong con Tuần/graduation/Qdrant
grep -rn -i "tuần\|graduat" .maika/skills/knowledge-curator/references/m7-memory-push.md; echo "m7=$?"
grep -rn -i "qdrant" .maika/ cli/ | grep -v ".worktrees"; echo "qdrant=$?"
# (3) gate memory-recall hoat dong
SAMPLE=$(mktemp); printf 'agent-memory unavailable — skip recall/save\n' > "$SAMPLE"
/usr/bin/python3 .maika/tools/gate-check/cli.py memory-recall "$SAMPLE"; echo "gate=$?"
rm -f "$SAMPLE"
```

Expected: `m7=1`, `qdrant=1` (không match), `gate=0` (PASS).

- [ ] **Step 3: Smoke thực tế trên máy đang có daemon tắt (optional nếu môi trường cho phép)**

Tạo project test bằng `maika init` với `--mcps agent-memory`, chạy `maika doctor mcp --target <dir>` → report phải có `agent-memory daemon: DOWN (http://localhost:3111)` + hint. (Tiêu chí spec §5.2 — nếu môi trường không cho phép init, ghi chú lại để user tự smoke.)

- [ ] **Step 4: Commit cuối (nếu có fix phát sinh)**

```bash
git status
# chỉ commit nếu Step 1-2 phát sinh sửa chữa:
git add -A && git commit -m "test: fix fallout from agent-memory activation changes"
```
