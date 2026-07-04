# Plan triển khai: Pha 3 Driver — vòng lặp apply bằng code

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** `orchestrator.py apply` chạy vòng lặp node Pha 3 (fresh-session tier) bằng Python — LLM chỉ còn trong worker; text hướng dẫn vận hành loop trong task.md bị xóa/thu gọn (diff âm).

**Architecture:** Thêm `load_execution_config` + `check_apply_preconditions` + `apply_command` + `main` vào `orchestrator.py` — chỉ lắp ráp primitives đã có (`load_runtime_queue`, `next_task`, `update_task_status`, `dispatch_worker`, `make_worker_runner`, `tiers.get_dispatch`). Disk (TASK_QUEUE.md) là source of truth mỗi vòng — crash-safe, resume tự nhiên. Không gate mới; SESSION-GATE/write-gate giữ nguyên.

**Tech Stack:** Python 3.10+ (stdlib + PyYAML đã có), pytest, Jinja placeholder convention của Maika.

**Spec:** `docs/superpowers/specs/2026-07-04-phase3-driver-thin-orchestrator-design.md`

## Ràng buộc toàn cục

- **Tiếng Việt** cho văn bản mới (docstring, message, doc); identifier kỹ thuật tiếng Anh.
- **Không dependency mới**; giữ NGUYÊN VĂN placeholder `{{ platform.framework_root }}` / `{% if %}` trong file `.maika/`.
- **Backward compatible**: không đổi chữ ký hàm hiện có; test cũ không được sửa.
- **Tests pass trên ubuntu + windows**: fake worker bằng `sys.executable`, không lệnh POSIX-only, không `/proc`.
- **DEVELOPMENT_RULES.md**: R3 (litmus ship cùng PR), R4 (Task 1 verify trước khi Task 3 sửa yaml), R6 (đóng dấu superseded), R7 (Task 4 phải cho diff text hướng dẫn ÂM).
- **Máy dev này**: chạy pytest bằng `/usr/bin/python3` (venv `.venv` thiếu jsonschema). Trong doc/scaffold vẫn viết `python3`.
- Commit message convention repo + trailer co-author theo agent thực thi.
- Branch: `feat/phase3-driver` (đã checkout — KHÔNG đổi branch).

---

### Task 1: R4 verification — 3 worker CLI phải chứng minh chạy non-interactive + ghi được file

**Files:**
- Create: `.superpowers/sdd/r4-verification.md` (scratch, gitignored — evidence cho Task 3 và PR body)

**Interfaces:**
- Produces: verdict PASS/FAIL per CLI + **command template đã verify** (nguyên văn, có đủ flag) — Task 3 chép nguyên văn template này vào `execution-mode.yaml`.

- [ ] **Bước 1: Chuẩn bị sandbox test**

```bash
mkdir -p /tmp/r4-verify && cd /tmp/r4-verify && rm -f r4_*.txt
```

- [ ] **Bước 2: Verify `claude -p`**

```bash
claude --version
claude -p --help 2>&1 | head -40   # đọc flag permission thật, đừng đoán
# Thử lần 1 (mặc định):
claude -p 'Tạo file r4_claude.txt trong thư mục hiện tại, nội dung đúng một từ: ok' ; echo "exit=$?"
ls -la r4_claude.txt
# Nếu không ghi được vì permission: thử lại với flag bypass tìm thấy trong --help
# (ứng viên đã biết: --dangerously-skip-permissions hoặc --permission-mode acceptEdits)
```

PASS = file tồn tại nội dung `ok` + exit 0 + không chờ input. Ghi lại NGUYÊN VĂN command thành công dạng template, vd: `claude -p --dangerously-skip-permissions {prompt}`.

- [ ] **Bước 3: Verify `codex exec`**

```bash
codex --version
codex exec --help 2>&1 | head -40
rm -f r4_codex.txt
codex exec 'Tạo file r4_codex.txt trong thư mục hiện tại, nội dung đúng một từ: ok' ; echo "exit=$?"
ls -la r4_codex.txt
# Nếu sandbox chặn write: thử flag sandbox trong --help (ứng viên: --sandbox workspace-write / --full-auto)
```

PASS-tiêu-chí như Bước 2. Ghi template thành công.

- [ ] **Bước 4: Verify `agy -p`**

```bash
agy --version 2>&1 | head -2
rm -f r4_agy.txt
agy -p 'Tạo file r4_agy.txt trong thư mục hiện tại, nội dung đúng một từ: ok' ; echo "exit=$?"
ls -la r4_agy.txt
```

PASS-tiêu-chí như Bước 2. Ghi template thành công.

- [ ] **Bước 5: Ghi report**

Ghi `.superpowers/sdd/r4-verification.md`:

```markdown
# R4 verification — worker CLI non-interactive write (2026-07-04)

| CLI | Version | Exit | File ghi được? | Template đã verify |
|---|---|---|---|---|
| claude -p | <version> | <code> | yes/no | `<nguyên văn>` |
| codex exec | <version> | <code> | yes/no | `<nguyên văn>` |
| agy -p | <version> | <code> | yes/no | `<nguyên văn>` |

Output thô từng lệnh: (paste, không tóm tắt)
```

**Quy tắc rẽ nhánh cho Task 3:** CLI nào FAIL (không thể ghi file non-interactive với mọi flag trong --help) → platform đó GIỮ NGUYÊN block hiện tại trong execution-mode.yaml, ghi `DEVIATION (needs Claude review)` vào report + ledger. KHÔNG cố flag không có trong --help.

(Task này không commit gì — evidence nằm ở scratch + ledger.)

---

### Task 2: Driver `apply_command` + `main` trong orchestrator.py (TDD)

**Files:**
- Modify: `.maika/tools/microloop-orchestrator/orchestrator.py` (thêm `import argparse`, 4 hàm mới ở CUỐI file)
- Create: `.maika/tools/microloop-orchestrator/tests/test_apply_command.py`

**Interfaces:**
- Consumes (đã có trong orchestrator.py, KHÔNG sửa chúng): `load_runtime_queue(active_dir)`, `next_task(queue)`, `update_task_status(active_dir, task_id, status, event=None)`, `dispatch_worker(prompt, runner, *, retries, active_dir, task_id)`, `make_worker_runner(worker_command, timeout)`, `_queue_path(active_dir)`, `initialize_runtime_queue(...)` (test dùng); `tiers.get_dispatch("fresh-session")` → `dispatch(handoff_path, result_path) -> prompt`.
- Produces:
  - `load_execution_config(active_dir) -> dict | None`
  - `check_apply_preconditions(active_dir, config) -> list[str]`
  - `apply_command(active_dir, runner=None, config=None) -> dict` — trả `{"status": "done"|"blocked"|"refused", "done": int, "task_id": str|None, "reason": str|None}`
  - `main(argv=None) -> int` — exit 0 done / 2 refused / 3 blocked. Task 4 (task.md) tham chiếu lệnh `python3 .../orchestrator.py apply --active-dir ...`.

- [ ] **Bước 1: Viết test fail**

Tạo `.maika/tools/microloop-orchestrator/tests/test_apply_command.py`:

```python
import json
import sys
from pathlib import Path

import yaml

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT))
import orchestrator  # noqa: E402


def _scaffold(tmp_path, *, mode="fresh-session", worker_command="stub {prompt}",
              tasks=None, with_checkpoint=True, with_handoffs=True):
    """Dựng cây scaffold tối thiểu cho driver: profiles/ + knowledge/active/ + queue."""
    fw = tmp_path / ".maika"
    active = fw / "knowledge" / "active"
    active.mkdir(parents=True)
    (fw / "profiles").mkdir()
    (fw / "profiles" / "execution-mode.yaml").write_text(
        yaml.safe_dump({
            "execution_mode": mode,
            "worker_command": worker_command,
            "max_retries": 1,
            "worker_timeout_seconds": 60,
        }),
        encoding="utf-8",
    )
    if with_checkpoint:
        (active / "KNOWLEDGE_CHECKPOINT.md").write_text("ok", encoding="utf-8")
    if tasks is None:
        tasks = [
            {"id": "T1", "desc": "node 1", "depends_on": []},
            {"id": "T2", "desc": "node 2", "depends_on": ["T1"]},
        ]
    if tasks:
        orchestrator.initialize_runtime_queue(
            active, "TICKET-1", "spec.md", tasks,
            execution_mode=mode, framework_root=".maika",
        )
    if with_handoffs:
        for t in tasks:
            (active / f"TASK_HANDOFF.{t['id']}.md").write_text(
                f"handoff {t['id']}", encoding="utf-8"
            )
    return active


def _ok_runner(tmp_path):
    """Stub worker: trích result_path từ prompt và ghi TASK_RESULT như worker thật."""
    def runner(prompt):
        for token in prompt.split():
            if "TASK_RESULT" in token:
                path = tmp_path / token.rstrip(".")
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text("done", encoding="utf-8")
                return 0, "ok"
        return 1, "no result path in prompt"
    return runner


def test_apply_command_happy_two_nodes(tmp_path):
    active = _scaffold(tmp_path)
    summary = orchestrator.apply_command(active, runner=_ok_runner(tmp_path))
    assert summary["status"] == "done"
    assert summary["done"] == 2
    queue = orchestrator.load_runtime_queue(active)
    assert [t["status"] for t in queue["tasks"]] == ["done", "done"]
    log = (active / "microloop" / "ACTIVITY_LOG.jsonl").read_text(encoding="utf-8")
    events = [json.loads(line)["event"] for line in log.splitlines()]
    assert events.count("subagent_started") == 2


def test_apply_command_blocked_stops_at_failing_node(tmp_path):
    active = _scaffold(tmp_path)
    summary = orchestrator.apply_command(active, runner=lambda p: (1, "boom"))
    assert summary["status"] == "blocked"
    assert summary["task_id"] == "T1"
    queue = orchestrator.load_runtime_queue(active)
    by_id = {t["id"]: t["status"] for t in queue["tasks"]}
    assert by_id == {"T1": "blocked", "T2": "pending"}


def test_apply_command_resumes_after_unblock(tmp_path):
    active = _scaffold(tmp_path)
    orchestrator.apply_command(active, runner=lambda p: (1, "boom"))
    queue = orchestrator.load_runtime_queue(active)
    queue["tasks"][0]["status"] = "pending"
    orchestrator.save_runtime_queue(active, queue)
    summary = orchestrator.apply_command(active, runner=_ok_runner(tmp_path))
    assert summary["status"] == "done"
    assert summary["done"] == 2


def test_apply_command_refuses_without_queue(tmp_path):
    active = _scaffold(tmp_path)
    (active / "microloop" / "TASK_QUEUE.md").unlink()
    summary = orchestrator.apply_command(active, runner=_ok_runner(tmp_path))
    assert summary["status"] == "refused"
    assert "TASK_QUEUE" in summary["reason"]


def test_apply_command_refuses_missing_handoff(tmp_path):
    active = _scaffold(tmp_path, with_handoffs=False)
    summary = orchestrator.apply_command(active, runner=_ok_runner(tmp_path))
    assert summary["status"] == "refused"
    assert "TASK_HANDOFF" in summary["reason"]


def test_apply_command_refuses_wrong_mode(tmp_path):
    active = _scaffold(tmp_path, mode="subagent")
    summary = orchestrator.apply_command(active, runner=_ok_runner(tmp_path))
    assert summary["status"] == "refused"
    assert "fresh-session" in summary["reason"]


def test_apply_command_refuses_empty_worker_command(tmp_path):
    active = _scaffold(tmp_path, worker_command="")
    summary = orchestrator.apply_command(active, runner=_ok_runner(tmp_path))
    assert summary["status"] == "refused"
    assert "worker_command" in summary["reason"]


def test_apply_command_refuses_without_checkpoint(tmp_path):
    active = _scaffold(tmp_path, with_checkpoint=False)
    summary = orchestrator.apply_command(active, runner=_ok_runner(tmp_path))
    assert summary["status"] == "refused"
    assert "KNOWLEDGE_CHECKPOINT" in summary["reason"]


def test_apply_command_worker_ok_but_no_result_is_blocked(tmp_path):
    active = _scaffold(tmp_path)
    summary = orchestrator.apply_command(active, runner=lambda p: (0, "ok"))
    assert summary["status"] == "blocked"
    assert "TASK_RESULT" in summary["reason"]


def test_apply_command_litmus_real_subprocess(tmp_path):
    """Litmus R3: driver end-to-end với worker subprocess thật (fake worker python)."""
    active = _scaffold(tmp_path, tasks=[{"id": "T1", "desc": "node", "depends_on": []}])
    script = tmp_path / "fake_worker.py"
    script.write_text(
        "import sys, pathlib\n"
        f"base = pathlib.Path({str(tmp_path)!r})\n"
        "for token in sys.argv[1].split():\n"
        "    if 'TASK_RESULT' in token:\n"
        "        p = base / token\n"
        "        p.parent.mkdir(parents=True, exist_ok=True)\n"
        "        p.write_text('done', encoding='utf-8')\n",
        encoding="utf-8",
    )
    config = {
        "execution_mode": "fresh-session",
        "worker_command": f'"{sys.executable}" "{script}" {{prompt}}',
        "max_retries": 0,
        "worker_timeout_seconds": 60,
    }
    summary = orchestrator.apply_command(active, config=config)
    assert summary["status"] == "done"
    assert summary["done"] == 1


def test_main_apply_refused_exit_code(tmp_path, capsys):
    active = _scaffold(tmp_path, mode="subagent")
    code = orchestrator.main(["apply", "--active-dir", str(active)])
    assert code == 2
    assert "Từ chối" in capsys.readouterr().out
```

- [ ] **Bước 2: Chạy test, xác nhận fail**

Run: `python3 -m pytest .maika/tools/microloop-orchestrator/tests/test_apply_command.py -v`
Expected: FAIL — `AttributeError: module 'orchestrator' has no attribute 'apply_command'`

- [ ] **Bước 3: Implement trong orchestrator.py**

(a) Thêm import ở đầu file (sau `import importlib.util`, trước `import json`):

```python
import argparse
```

(b) Thêm 4 hàm + entry point ở CUỐI file (sau `build_contract_handoff`):

```python
def load_execution_config(active_dir):
    """Đọc profiles/execution-mode.yaml (bản ĐÃ render) của scaffold chứa active_dir.

    active_dir = <framework_root>/knowledge/active → config ở <framework_root>/profiles/.
    Trả None nếu file không tồn tại (precondition sẽ báo)."""
    path = Path(active_dir).resolve().parents[1] / "profiles" / "execution-mode.yaml"
    if not path.exists():
        return None
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def check_apply_preconditions(active_dir, config):
    """Preconditions cơ học của driver (thay rule text — spec §4.2).

    Trả list lý do từ chối (rỗng = chạy được); mỗi lý do một dòng chỉ thẳng cách sửa."""
    reasons = []
    active = Path(active_dir)
    if config is None:
        reasons.append(
            "Thiếu profiles/execution-mode.yaml — chạy `maika update` để render lại scaffold."
        )
        return reasons
    if config.get("execution_mode") != "fresh-session":
        reasons.append(
            f"Driver chỉ hỗ trợ execution_mode fresh-session (hiện tại: "
            f"{config.get('execution_mode')!r}) — tier subagent/inline-reload do parent "
            "agent vận hành theo workflows/task.md."
        )
    if not str(config.get("worker_command") or "").strip():
        reasons.append(
            "worker_command rỗng trong execution-mode.yaml — khai báo lệnh worker cho platform này."
        )
    if not (active / "KNOWLEDGE_CHECKPOINT.md").exists():
        reasons.append("Thiếu KNOWLEDGE_CHECKPOINT.md — hoàn thành Pha 1/2 trước khi apply.")
    if not _queue_path(active).exists():
        reasons.append(
            "Thiếu microloop/TASK_QUEUE.md — parent phải chạy initialize_runtime_queue trước."
        )
        return reasons
    tasks = (load_runtime_queue(active).get("tasks") or [])
    if not tasks:
        reasons.append("TASK_QUEUE.md không có task nào.")
        return reasons
    project_root = active.resolve().parents[2]
    for t in tasks:
        if t.get("status") == "done":
            continue
        handoff = t.get("handoff_path")
        if not handoff or not (project_root / handoff).exists():
            reasons.append(
                f"Node {t.get('id')}: thiếu TASK_HANDOFF ({handoff}) — parent phải ghi handoff trước."
            )
    return reasons


def apply_command(active_dir, runner=None, config=None):
    """Driver Pha 3 (fresh-session): vòng lặp node chạy bằng code — LLM chỉ còn trong worker.

    Disk (TASK_QUEUE.md) là source of truth mỗi vòng: crash-safe, resume tự nhiên
    (next_task resume-first, skip node done). runner inject được cho test; mặc định
    make_worker_runner từ execution-mode.yaml. Gate v1: worker exit 0 + TASK_RESULT
    tồn tại (executor procedure tự chạy gate dự án; write-gate vẫn chặn cơ học trong
    worker process). Trả dict {"status","done","task_id","reason"}."""
    active = Path(active_dir)
    if config is None:
        config = load_execution_config(active)
    reasons = check_apply_preconditions(active, config)
    if reasons:
        return {"status": "refused", "done": 0, "task_id": None,
                "reason": "\n".join(reasons)}
    from tiers import get_dispatch  # lazy: giữ loop protocol không biết tier (docstring module)
    dispatch = get_dispatch("fresh-session")
    if runner is None:
        runner = make_worker_runner(
            config["worker_command"], config.get("worker_timeout_seconds", 900)
        )
    max_retries = config.get("max_retries", 2)
    project_root = active.resolve().parents[2]
    done_count = 0
    while True:
        queue = load_runtime_queue(active)
        task = next_task(queue)
        if task is None:
            blocked = [t["id"] for t in queue["tasks"] if t["status"] == "blocked"]
            if blocked:
                return {"status": "blocked", "done": done_count, "task_id": blocked[0],
                        "reason": "node blocked từ lần chạy trước — sửa nguyên nhân rồi đặt lại pending"}
            return {"status": "done", "done": done_count, "task_id": None, "reason": None}
        task_id = task["id"]
        if task["status"] != "in_progress":
            update_task_status(active, task_id, "in_progress")
        prompt = dispatch(task["handoff_path"], task["result_path"])
        outcome = dispatch_worker(
            prompt, runner, retries=max_retries, active_dir=active, task_id=task_id,
        )
        if outcome["status"] == "done" and not (project_root / task["result_path"]).exists():
            outcome = {"status": "blocked", "attempts": outcome["attempts"],
                       "output": f"worker exit 0 nhưng thiếu {task['result_path']}"}
        current = next(
            t for t in load_runtime_queue(active)["tasks"] if t["id"] == task_id
        )
        if outcome["status"] == "done":
            if current["status"] != "done":  # worker dùng write_task_result thì đã done + emit
                update_task_status(active, task_id, "done", event="subagent_done")
            done_count += 1
        else:
            if current["status"] != "blocked":
                update_task_status(active, task_id, "blocked")
            return {"status": "blocked", "done": done_count, "task_id": task_id,
                    "reason": str(outcome["output"])[:500]}


def main(argv=None):
    parser = argparse.ArgumentParser(description="Micro-loop orchestrator CLI (Pha 3 driver)")
    sub = parser.add_subparsers(dest="command", required=True)
    apply_parser = sub.add_parser("apply", help="Chạy vòng lặp node Pha 3 (fresh-session)")
    apply_parser.add_argument(
        "--active-dir", required=True,
        help="Đường dẫn knowledge/active của scaffold (chạy từ project root)",
    )
    args = parser.parse_args(argv)
    summary = apply_command(args.active_dir)
    if summary["status"] == "refused":
        print(f"[DRIVER] Từ chối chạy:\n{summary['reason']}")
        return 2
    if summary["status"] == "blocked":
        print(
            f"[DRIVER] BLOCKED tại node {summary['task_id']} "
            f"(đã xong {summary['done']} node): {summary['reason']}"
        )
        print(
            "[DRIVER] Sửa nguyên nhân (handoff/feedback), đặt node về pending, "
            "chạy lại lệnh này — driver tự resume."
        )
        return 3
    print(
        f"[DRIVER] Hoàn thành {summary['done']} node. "
        "Parent tiếp tục §3 bước 6 (post_apply_verify)."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Bước 4: Chạy test, xác nhận pass**

Run: `python3 -m pytest .maika/tools/microloop-orchestrator/tests/test_apply_command.py -v`
Expected: PASS cả 11 test

- [ ] **Bước 5: Regression toàn bộ orchestrator**

Run: `python3 -m pytest .maika/tools/microloop-orchestrator/tests/ -v`
Expected: PASS toàn bộ (test cũ không đổi)

- [ ] **Bước 6: Commit**

```bash
git add .maika/tools/microloop-orchestrator/orchestrator.py .maika/tools/microloop-orchestrator/tests/test_apply_command.py
git commit -m "feat(orchestrator): apply_command — driver Pha 3 chạy vòng lặp node bằng code"
```

---

### Task 3: execution-mode.yaml — claude-code sang fresh-session (CÓ ĐIỀU KIỆN theo Task 1)

**Files:**
- Modify: `.maika/profiles/execution-mode.yaml`

**Interfaces:**
- Consumes: template đã verify từ `.superpowers/sdd/r4-verification.md` (Task 1).

**ĐIỀU KIỆN:** chỉ sửa block của CLI có verdict PASS ở Task 1. CLI FAIL → giữ nguyên block, ghi `DEVIATION (needs Claude review): <CLI> fail R4 — giữ tier cũ` vào ledger. Nếu template verify được KHÁC ví dụ dưới (thêm flag) → dùng NGUYÊN VĂN template từ report, thay `{prompt}` đúng vị trí.

- [ ] **Bước 1: Sửa block claude-code (nếu claude PASS)**

Edit `.maika/profiles/execution-mode.yaml`:

`old_string`:

```yaml
{% elif platform.name == "claude-code" %}
execution_mode: subagent
worker_command: ''
```

`new_string` (thay `claude -p {prompt}` bằng template verify được nếu khác):

```yaml
{% elif platform.name == "claude-code" %}
execution_mode: fresh-session
worker_command: 'claude -p {prompt}'
```

- [ ] **Bước 2: Cập nhật comment header cho khớp**

Edit `.maika/profiles/execution-mode.yaml`:

`old_string`:

```yaml
#   subagent      → Claude Code (Agent tool, full isolation)
```

`new_string`:

```yaml
#   subagent      → tier Agent-tool (tùy chọn cho Claude Code; đổi execution_mode nếu muốn)
```

- [ ] **Bước 3: Nếu Task 1 cho template khác cho agy/codex** (vd cần thêm flag sandbox): sửa `worker_command` của block tương ứng bằng template verify được. Không PASS → không sửa.

- [ ] **Bước 4: Verify render per-platform**

Run:

```bash
python3 - <<'PY'
from jinja2 import Environment, StrictUndefined
env = Environment(trim_blocks=True, lstrip_blocks=True, keep_trailing_newline=True, undefined=StrictUndefined)
content = open(".maika/profiles/execution-mode.yaml").read()
for name in ["antigravity", "codex", "claude-code", "cursor"]:
    ctx = {"platform": type("P", (), {"name": name, "framework_root": ".maika"})()}
    out = env.from_string(content).render(**ctx)
    mode = [l for l in out.splitlines() if l.startswith("execution_mode:")]
    print(name, mode, "leak:", "{%" in out)
PY
```

Expected: antigravity/codex/claude-code → `fresh-session` (claude-code chỉ khi PASS), cursor → `inline-reload`, leak: False cả 4.

- [ ] **Bước 5: Commit**

```bash
git add .maika/profiles/execution-mode.yaml
git commit -m "feat(execution-mode): claude-code sang fresh-session driver (R4-verified)"
```

---

### Task 4: Pruning task.md + rules-flow + đóng dấu R6 (diff text hướng dẫn PHẢI ÂM)

**Files:**
- Modify: `.maika/workflows/task.md` (2 chỗ: khối P5, §3 bước 5.c dispatch)
- Modify: `.maika/rules/rules-flow.md` (1 dòng thêm vào R-Flow-5)
- Modify: `docs/superpowers/specs/2026-07-03-task-run-quality-thin-orchestrator-design.md` (đóng dấu R6)
- Modify: `docs/superpowers/specs/2026-07-04-phase3-driver-thin-orchestrator-design.md` (chốt gate v1)

- [ ] **Bước 1: Đo baseline số dòng**

Run: `wc -l .maika/workflows/task.md .maika/rules/rules-flow.md`
Ghi lại 2 con số (so ở Bước 7).

- [ ] **Bước 2: Thu gọn khối P5 — driver tự quản lifecycle event**

Edit `.maika/workflows/task.md`:

`old_string`:

```markdown
     - Ngay trước khi giao việc cho executor/subagent, update task trong `TASK_QUEUE.md` thành `in_progress`
       và append `subagent_started`.
     - Khi executor/subagent hoàn tất, ghi `microloop/TASK_RESULT.<node-id>.md`, update task thành `done`,
       append `result_written` và `subagent_done`.
     - Nếu executor/subagent không thể hoàn tất, update task thành `blocked`, ghi lý do vào
       `TASK_RESULT.<node-id>.md`, append `subagent_blocked`, rồi dừng để user quyết định.
     - Có thể dùng helpers trong `{{ platform.framework_root }}/tools/microloop-orchestrator/orchestrator.py`:
       `initialize_runtime_queue`, `write_task_handoff`, `update_task_status`, `write_task_result`,
       `append_activity_event`, `record_parent_event`, `write_parent_brain`.
```

`new_string`:

```markdown
     - Đường fresh-session: driver (`orchestrator.py apply`) TỰ quản các event
       `in_progress`/`done`/`blocked`/`subagent_started`/`subagent_blocked` — KHÔNG emit thủ công.
     - Chỉ khi tier `subagent`/`inline-reload` (parent tự vận hành): dùng helpers
       `update_task_status`, `write_task_result`, `append_activity_event` trong
       `{{ platform.framework_root }}/tools/microloop-orchestrator/orchestrator.py` theo đúng
       vòng đời in_progress → done/blocked.
```

- [ ] **Bước 3: §3 bước 5.c — nhánh fresh-session gọi driver thay vì vận hành thủ công**

Edit `.maika/workflows/task.md`:

`old_string`:

```markdown
      - Dispatch executor theo `{{ platform.framework_root }}/profiles/execution-mode.yaml`:
        - `subagent`: Agent tool với prompt từ `tiers/subagent.py`.
        - `fresh-session`: gọi `dispatch_worker(prompt, make_worker_runner(worker_command, worker_timeout_seconds), retries=max_retries, active_dir=<knowledge/active>, task_id=<node-id>)`
          (orchestrator.py) với prompt từ `tiers/fresh_session.py` — worker context MỚI per node,
          KHÔNG yêu cầu user mở session; `dispatch_worker` tự emit `subagent_started`/`subagent_blocked`
          (không emit thủ công 2 event này cho node đó).
        - `inline-reload`: prompt từ `tiers/inline_reload.py`, chạy trong session hiện tại (LCD).
      - Before dispatch, mark that node `in_progress`; after result, mark it `done` or `blocked`.
      - Run mechanical gate + semantic surface-check.
```

`new_string`:

```markdown
      - Dispatch executor theo `{{ platform.framework_root }}/profiles/execution-mode.yaml`:
        - `fresh-session` (đường chính): sau khi ghi XONG toàn bộ handoff, chạy MỘT lệnh từ project root:
          `python3 {{ platform.framework_root }}/tools/microloop-orchestrator/orchestrator.py apply --active-dir {{ platform.framework_root }}/knowledge/active`
          Driver tự chạy vòng lặp node (dispatch worker, retry, event, resume). Exit 0 → sang bước 6;
          exit ≠ 0 → đọc message, sửa nguyên nhân (handoff/feedback), đặt node về `pending`, chạy lại.
        - `subagent`: Agent tool với prompt từ `tiers/subagent.py`, parent tự vận hành vòng lặp per node.
        - `inline-reload`: prompt từ `tiers/inline_reload.py`, chạy trong session hiện tại (LCD).
      - Tier subagent/inline-reload: mark node `in_progress` trước dispatch, `done`/`blocked` sau result;
        run mechanical gate + semantic surface-check per node.
```

- [ ] **Bước 4: R-Flow-5 — trỏ Pha 3 về driver**

Edit `.maika/rules/rules-flow.md`:

`old_string`:

```markdown
- Parent chỉ đọc lại file kết quả (REQUIREMENT, EXPLORE_CONTEXT, TASK_RESULT…), không đọc nguồn thô.
```

`new_string`:

```markdown
- Parent chỉ đọc lại file kết quả (REQUIREMENT, EXPLORE_CONTEXT, TASK_RESULT…), không đọc nguồn thô.
- Pha 3 tier fresh-session: vòng lặp node do driver `orchestrator.py apply` chạy (task.md §3 bước 5.c) — parent không vận hành loop thủ công.
```

- [ ] **Bước 5: Đóng dấu R6 lên spec 2026-07-03**

Edit `docs/superpowers/specs/2026-07-03-task-run-quality-thin-orchestrator-design.md`:

`old_string`:

```markdown
> Ngày: 2026-07-03
> Trạng thái: draft-for-review
```

`new_string`:

```markdown
> Ngày: 2026-07-03
> Trạng thái: draft-for-review
> Cập nhật 2026-07-04: đường vận hành Pha 3 fresh-session (LLM gọi dispatch_worker thủ công, §B)
> được code-hóa bởi docs/superpowers/specs/2026-07-04-phase3-driver-thin-orchestrator-design.md —
> mô tả LLM-driven trong §B là lịch sử; cơ chế dispatch_worker/worker_command giữ nguyên hiệu lực.
```

- [ ] **Bước 6: Chốt gate v1 trong spec 2026-07-04**

Edit `docs/superpowers/specs/2026-07-04-phase3-driver-thin-orchestrator-design.md`:

`old_string`:

```markdown
                    │    gate_fn     = make_gate_fn(runner) (checkstyle nếu cấu hình; else PASS)
```

`new_string`:

```markdown
                    │    gate v1    = worker exit 0 + TASK_RESULT tồn tại (executor tự chạy
                    │                 gate dự án; checkstyle driver-side chờ evidence — R3)
```

- [ ] **Bước 7: Verify diff âm**

Run: `wc -l .maika/workflows/task.md .maika/rules/rules-flow.md`
Expected: tổng 2 file GIẢM so với Bước 1 (tiêu chí cứng của spec là TỔNG ÂM; thực tế 646→644).
Run thêm: `grep -c "orchestrator.py apply" .maika/workflows/task.md` → Expected: `2` (mô tả P5 ở Bước 2 + lệnh driver ở Bước 3).

> Hiệu chỉnh 2026-07-04 (Claude review): bản đầu của Bước 7 ghi "task.md giảm ≥ 5" và grep `1` — lỗi số học của PLAN (Bước 3 old/new đều 9 dòng nên net 0; cụm "orchestrator.py apply" xuất hiện ở cả 2 new_string). Codex BLOCKED đúng kỷ luật tại đây; edit Bước 2–6 đã đối chiếu khớp plan nguyên văn — ACCEPTED DEVIATION, không phải lỗi implementer.

- [ ] **Bước 8: Commit**

```bash
git add .maika/workflows/task.md .maika/rules/rules-flow.md docs/superpowers/specs/2026-07-03-task-run-quality-thin-orchestrator-design.md docs/superpowers/specs/2026-07-04-phase3-driver-thin-orchestrator-design.md
git commit -m "docs(workflow): Pha 3 fresh-session chạy qua driver — prune text vận hành loop (diff âm)"
```

---

### Task 5: Snapshot refresh + regression toàn repo

**Files:**
- Modify: `cli/tests/snapshots/antigravity.txt`, `cli/tests/snapshots/claude-code.txt`, `cli/tests/snapshots/codex.txt`, `cli/tests/snapshots/generic.txt`

- [ ] **Bước 1: Chạy snapshot test, xem fail**

Run: `python3 -m pytest cli/tests/test_snapshots.py -v`
Expected: FAIL 4 platform — cây scaffold thiếu dòng `test_apply_command.py`.

- [ ] **Bước 2: Thêm dòng mới vào 4 snapshot (đúng vị trí sort)**

Với mỗi file trong `cli/tests/snapshots/{antigravity,codex,generic,claude-code}.txt`: thêm dòng
`<root>/tools/microloop-orchestrator/tests/test_apply_command.py`
NGAY TRƯỚC dòng `<root>/tools/microloop-orchestrator/tests/test_degradation.py`
(`<root>` = `.agents` cho antigravity/codex, `.claude` cho claude-code, `.maika` cho generic — nhìn dòng test_degradation có sẵn trong từng file để lấy đúng prefix).

- [ ] **Bước 3: Chạy lại snapshot test**

Run: `python3 -m pytest cli/tests/test_snapshots.py -v`
Expected: PASS cả 4.

- [ ] **Bước 4: Full regression**

Run: `python3 -m pytest .maika/ cli/ -q`
Expected: **535 passed, 1 skipped** (524 baseline + 11 test_apply_command), 0 failed.

- [ ] **Bước 5: Commit**

```bash
git add cli/tests/snapshots/
git commit -m "test(snapshots): refresh scaffold tree cho test_apply_command"
```

---

## Ghi chú deviation so với spec

1. **Gate v1** = worker exit 0 + TASK_RESULT tồn tại (không chạy checkstyle trong driver): executor procedure đã bắt worker tuân gate dự án; write-gate vẫn chặn cơ học trong worker process; driver-side checkstyle cần TASK_RESULT schema parse — chờ observed failure (R3). Spec được chốt lại ở Task 4 Bước 6.
2. **§2 bước 10 / §3 bước 9 của task.md không sửa** (spec §4.4 dự kiến "thu gọn"): kiểm tra thực tế sau Task 9 của plan trước — text đã tối giản và vẫn đúng với driver (driver chính là đường "§3 bước 5.c" được tham chiếu). Sửa thêm = churn không giảm dòng.
3. **Task 1 không có commit** — evidence ở scratch + ledger; verdict chép vào PR body.
