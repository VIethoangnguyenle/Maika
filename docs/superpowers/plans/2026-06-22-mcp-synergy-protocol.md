# UA ↔ Codebase Memory Synergy Protocol — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Dạy agent dùng UA MCP + Codebase Memory MCP bổ trợ nhau (altitude routing, golden path handoff, adaptive theo độ phức tạp, degrade mềm) khi khám phá code ở Pha 1.

**Architecture:** Thêm 3 abstract op OPTIONAL cho UA domain tool ở `cli/platforms/` (binding Option A — vì skill render per-platform, raw tool name sẽ sai trên non-claude). Viết lại protocol trong `.maika/skills/codebase-explorer/SKILL.md` (nhà chính) dùng `{{ tools.* }}`. Cập nhật mỏng `.maika/workflows/task.md`. Mọi tên tool cụ thể chỉ sống ở `cli/platforms/`; operational templates chỉ dùng `{{ tools.* }}` (guard bằng test, mirror `test_no_hardcoded_memory_tools.py`).

**Tech Stack:** Python 3.10, pytest (`--import-mode=importlib`), Jinja2 templating, Markdown skills/workflows.

## Global Constraints

- Abstract op mapping: bất kỳ key nào trong `tool_mapping` phải thuộc `REQUIRED_TOOL_KEYS ∪ OPTIONAL_TOOL_KEYS`, nếu không `validate_tool_mapping` ném `PlatformToolMappingError` (`cli/platforms/base.py:158-177`).
- UA ops là **OPTIONAL** (UA luôn có thể vắng) — KHÔNG thêm vào `REQUIRED_TOOL_KEYS`.
- Operational templates (`.maika/{rules,skills,procedures,workflows}`) KHÔNG hardcode tên tool provider — chỉ `{{ tools.* }}`.
- Tên tool UA MCP dùng tạm theo báo cáo: `get_domain_overview`, `get_domain_flow_detail`, `get_relationships` — xác minh lại bằng cách liệt kê tool của MCP `understand-anything` lúc runtime nếu lệch (KHÔNG fetch repo).
- Per-platform MCP tool naming: claude-code = `mcp__<server>__<tool>` (double underscore); antigravity = `mcp_<server>_<tool>` (single underscore); codex + generic = bare `<tool>`.
- Manifest key của UA MCP server là `understand-anything` (`cli/plugin-manifest.yaml:38`).
- Giữ `.maika/workflows/task.md` mỏng (orchestrator) — không duplicate chi tiết protocol, không viết lại GATE check graph freshness hiện có.
- Snapshot test chỉ so cây thư mục (`cli/tests/test_snapshots.py`) — sửa prose không ảnh hưởng; vẫn phải pass.
- Spec nguồn: `docs/superpowers/specs/2026-06-22-mcp-synergy-protocol-design.md`.

---

## File Structure

- `cli/platforms/base.py` — thêm 3 op vào `OPTIONAL_TOOL_KEYS`.
- `cli/platforms/claude_code.py` — map 3 op → `mcp__understand-anything__*`.
- `cli/platforms/codex.py` — map 3 op → bare names.
- `cli/platforms/antigravity.py` — map 3 op → `mcp_understand-anything_*`.
- `cli/platforms/generic.py` — map 3 op → bare names.
- `cli/tests/test_platforms.py` — test 3 op resolvable + nằm trong OPTIONAL.
- `cli/tests/test_codebase_explorer_protocol.py` — **mới**: guard skill/workflow dùng `{{ tools.domain_* }}`, không hardcode raw UA name; assert các section protocol tồn tại.
- `.maika/skills/codebase-explorer/SKILL.md` — nhà chính của protocol.
- `.maika/workflows/task.md` — cập nhật mỏng Pha 1 §1.4 + §6.

---

## Task 1: UA domain abstract ops trong platform layer

**Files:**
- Modify: `cli/platforms/base.py` (`OPTIONAL_TOOL_KEYS`, ~line 47-50)
- Modify: `cli/platforms/claude_code.py` (tool_mapping, sau block code-exploration ~line 39)
- Modify: `cli/platforms/codex.py` (tool_mapping)
- Modify: `cli/platforms/antigravity.py` (tool_mapping, sau ~line 39)
- Modify: `cli/platforms/generic.py` (tool_mapping)
- Test: `cli/tests/test_platforms.py`

**Interfaces:**
- Produces: 3 abstract ops resolvable qua `get_platform(key).get_tool(op)`:
  - `domain_overview`, `domain_flow`, `domain_relationships`
  - Có mặt trong `OPTIONAL_TOOL_KEYS` (import từ `cli.platforms.base`).

- [ ] **Step 1: Write the failing test**

Thêm vào cuối `cli/tests/test_platforms.py`:

```python
UA_DOMAIN_OPS = ("domain_overview", "domain_flow", "domain_relationships")


def test_ua_domain_ops_are_optional_keys():
    from cli.platforms.base import OPTIONAL_TOOL_KEYS
    for op in UA_DOMAIN_OPS:
        assert op in OPTIONAL_TOOL_KEYS, f"{op} must be an OPTIONAL tool key"


def test_every_platform_resolves_ua_domain_ops():
    for key, cls in PLATFORMS.items():
        platform = cls()
        for op in UA_DOMAIN_OPS:
            resolved = platform.get_tool(op)
            assert resolved, f"{key} did not resolve {op}"


def test_ua_domain_ops_use_understand_anything_server_where_prefixed():
    # claude-code uses mcp__<server>__<tool>; antigravity uses mcp_<server>_<tool>
    assert get_platform("claude-code").get_tool("domain_overview") == (
        "mcp__understand-anything__get_domain_overview"
    )
    assert get_platform("antigravity").get_tool("domain_flow") == (
        "mcp_understand-anything_get_domain_flow_detail"
    )
    # codex + generic use bare tool names
    assert get_platform("codex").get_tool("domain_relationships") == "get_relationships"
    assert get_platform("generic").get_tool("domain_overview") == "get_domain_overview"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest cli/tests/test_platforms.py -k ua_domain -v`
Expected: FAIL — `domain_overview` not in `OPTIONAL_TOOL_KEYS` / `PlatformToolMappingError: ... has no mapping for abstract tool operation: domain_overview`.

- [ ] **Step 3: Add the ops to OPTIONAL_TOOL_KEYS**

Trong `cli/platforms/base.py`, sửa `OPTIONAL_TOOL_KEYS`:

```python
OPTIONAL_TOOL_KEYS = frozenset({
    "browser_agent",
    "generate_image",
    # ── Understand-Anything MCP — domain/top-down (runtime-optional) ──
    "domain_overview",
    "domain_flow",
    "domain_relationships",
})
```

- [ ] **Step 4: Map the ops in each platform adapter**

`cli/platforms/claude_code.py` — thêm vào dict `tool_mapping` (sau block codebase-memory-mcp):

```python
        # ── Domain / top-down (understand-anything MCP) ──
        "domain_overview":      "mcp__understand-anything__get_domain_overview",
        "domain_flow":          "mcp__understand-anything__get_domain_flow_detail",
        "domain_relationships": "mcp__understand-anything__get_relationships",
```

`cli/platforms/antigravity.py` — thêm:

```python
        # ── Domain / top-down (understand-anything MCP) ──
        "domain_overview":      "mcp_understand-anything_get_domain_overview",
        "domain_flow":          "mcp_understand-anything_get_domain_flow_detail",
        "domain_relationships": "mcp_understand-anything_get_relationships",
```

`cli/platforms/codex.py` — thêm:

```python
        # ── Domain / top-down (understand-anything MCP) ──
        "domain_overview":      "get_domain_overview",
        "domain_flow":          "get_domain_flow_detail",
        "domain_relationships": "get_relationships",
```

`cli/platforms/generic.py` — thêm:

```python
        # ── Domain / top-down (understand-anything MCP) ──
        "domain_overview":      "get_domain_overview",
        "domain_flow":          "get_domain_flow_detail",
        "domain_relationships": "get_relationships",
```

- [ ] **Step 5: Run the new test + the existing platform contract test**

Run: `python -m pytest cli/tests/test_platforms.py -v`
Expected: PASS — gồm `test_all_platforms_define_required_tool_keyset` (xác nhận `extra` rỗng: 3 op mới đã nằm trong OPTIONAL nên không bị coi là "unknown tool mappings").

- [ ] **Step 6: Commit**

```bash
git add cli/platforms/base.py cli/platforms/claude_code.py cli/platforms/codex.py cli/platforms/antigravity.py cli/platforms/generic.py cli/tests/test_platforms.py
git commit -m "feat(cli): add UA domain abstract ops (domain_overview/flow/relationships)"
```

---

## Task 2: Viết lại protocol trong codebase-explorer SKILL.md

**Files:**
- Modify: `.maika/skills/codebase-explorer/SKILL.md` (section "Structured-first cases" + insert sau nó; section "5. Công cụ")
- Test: `cli/tests/test_codebase_explorer_protocol.py` (mới)

**Interfaces:**
- Consumes: abstract ops từ Task 1 (`{{ tools.domain_overview }}`, `{{ tools.domain_flow }}`, `{{ tools.domain_relationships }}`) + ops Codebase sẵn có (`{{ tools.search_code }}`, `{{ tools.get_symbol }}`, `{{ tools.read_file }}`, `{{ tools.trace_flow }}`, `{{ tools.find_blast_radius }}`, `{{ tools.list_symbols }}`, `{{ tools.graph_stats }}`, `{{ tools.code_status }}`).
- Produces: skill chứa các marker section: `## Định tuyến theo độ cao`, `## Cổng độ phức tạp`, `## Golden Path`, `## Bản đồ năng lực`, `## Degradation`, `## Source attribution`.

- [ ] **Step 1: Write the failing guard test**

Tạo `cli/tests/test_codebase_explorer_protocol.py`:

```python
"""Guard: codebase-explorer protocol uses abstract ops, never raw UA tool names."""

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SKILL = REPO_ROOT / ".maika" / "skills" / "codebase-explorer" / "SKILL.md"

# Raw provider tool names must NOT appear in operational skill prose.
RAW_UA = re.compile(r"mcp__understand-anything__|mcp_understand-anything_")


def _text():
    return SKILL.read_text(encoding="utf-8")


def test_skill_references_ua_domain_ops_via_template():
    text = _text()
    for op in ("domain_overview", "domain_flow", "domain_relationships"):
        assert "{{ tools.%s }}" % op in text, f"missing {{{{ tools.{op} }}}}"


def test_skill_has_no_raw_ua_tool_names():
    assert RAW_UA.search(_text()) is None, "skill hardcodes raw UA MCP tool name"


def test_skill_has_protocol_sections():
    text = _text()
    for marker in (
        "Định tuyến theo độ cao",
        "Cổng độ phức tạp",
        "Golden Path",
        "Bản đồ năng lực",
        "Degradation",
        "Source attribution",
    ):
        assert marker in text, f"missing section: {marker}"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest cli/tests/test_codebase_explorer_protocol.py -v`
Expected: FAIL — skill chưa có `{{ tools.domain_overview }}` và chưa có các section marker.

- [ ] **Step 3: Replace "Structured-first cases" với "Định tuyến theo độ cao"**

Trong `.maika/skills/codebase-explorer/SKILL.md`, thay nguyên block `### Structured-first cases` (từ tiêu đề tới hết câu "Agent không được tự ý bỏ qua structured provider chỉ vì grep/search cho cảm giác nhanh hơn.") bằng:

```markdown
### Định tuyến theo độ cao (Altitude Routing)

UA và Codebase Memory **bổ trợ nhau, không thay thế** — mỗi tool mạnh ở một độ cao:

- **Độ cao domain / business flow / entry point / ranh giới async (Kafka/gRPC)** → **UA** là chính (top-down map): `{{ tools.domain_overview }}`, `{{ tools.domain_flow }}`, `{{ tools.domain_relationships }}`.
- **Độ cao symbol / đọc code / static call-chain / blast radius theo file** → **Codebase Memory** là chính (bottom-up lens): `{{ tools.search_code }}`, `{{ tools.get_symbol }}`, `{{ tools.read_file }}`, `{{ tools.trace_flow }}`, `{{ tools.find_blast_radius }}`.

Quy tắc tinh chỉnh "structured-first": static call-chain vẫn dùng `{{ tools.trace_flow }}` (Codebase) làm chính; **nhưng** khi luồng đứt ở ranh giới async → leo thang sang `{{ tools.domain_flow }}` (UA). Agent không bỏ qua provider có cấu trúc chỉ vì grep cho cảm giác nhanh hơn.
```

- [ ] **Step 4: Insert "Cổng độ phức tạp" + "Golden Path" ngay sau section trên**

Chèn tiếp:

```markdown
### Cổng độ phức tạp (Adaptive)

Chạy **full Golden Path 5 bước** khi task chạm BẤT KỲ điều kiện nào: flow nghiệp vụ end-to-end chưa rõ; cross-module / cross-service; nghi async/event-driven (Kafka/gRPC/queue); requirement mơ hồ / chưa biết vị trí code.

Ngược lại (task localized, đã biết file/symbol, sửa 1 hàm) → bỏ qua UA top-down, dùng Codebase trực tiếp (`{{ tools.search_code }}` → `{{ tools.get_symbol }}`).

Ghi nhánh đã chọn + lý do (1 dòng) vào `{{ platform.framework_root }}/knowledge/active/AGENT_TRANSPARENCY.md`.

### Golden Path (5 bước handoff — mỗi bước seed cho bước sau)

1. **Định vị bối cảnh** — `{{ tools.domain_overview }}` (UA): từ tên feature/requirement → ra **tên domain**.
2. **Tìm diện rộng** — `{{ tools.search_code }}` / `{{ tools.list_symbols }}` (Codebase): từ domain+keyword → **danh sách class/method + file** ứng viên.
3. **Chiết xuất luồng** — `{{ tools.domain_flow }}` (UA): từ domain + class names → **entry point** (REST/gRPC/Kafka) + các step.
4. **Đọc mã** — `{{ tools.get_symbol }}` / `{{ tools.read_file }}` (Codebase): đọc logic chi tiết (lib, error-handling, threading).
5. **Verify liên kết** — `{{ tools.trace_flow }}` (Codebase) + `{{ tools.domain_relationships }}` (UA): bịt lỗ hổng interface→nhiều impl, điểm đứt async.

Liên kết chặt nằm ở B2↔B3 (Codebase tìm *cái gì tồn tại*, UA giải thích *nối nhau ra sao qua async*) và B5 (hai tool cross-check).
```

- [ ] **Step 5: Insert "Bản đồ năng lực" + "Degradation" + "Source attribution"**

Chèn tiếp:

```markdown
### Bản đồ năng lực (theo ý định — minh họa, KHÔNG whitelist)

| Ý định | UA (top-down) | Codebase Memory (bottom-up) |
|---|---|---|
| Map domain / business flow | `{{ tools.domain_overview }}`, `{{ tools.domain_flow }}` | — |
| Quan hệ / impact logic | `{{ tools.domain_relationships }}` | — |
| Tìm symbol (rộng) | — | `{{ tools.search_code }}`, `{{ tools.list_symbols }}` |
| Truy vấn cấu trúc tùy ý | — | `{{ tools.get_dependencies }}` + `{{ tools.graph_stats }}` |
| Đọc code | — | `{{ tools.get_symbol }}`, `{{ tools.read_file }}` |
| Trace / impact file | — | `{{ tools.trace_flow }}`, `{{ tools.find_blast_radius }}` |

> Golden Path là **sàn, không phải trần**. Bảng trên minh họa, KHÔNG đầy đủ — cả hai MCP tự expose danh sách tool đầy đủ lúc runtime. Ngoài Golden Path, chọn tool theo **ý định**; truy vấn lạ thì dùng `{{ tools.graph_stats }}` học schema rồi viết Cypher qua `{{ tools.get_dependencies }}`.

### Degradation (degrade mềm + ghi confidence)

- **UA vắng** (plugin chưa cài / `domain-graph.json` thiếu / UA MCP không chạy / op `domain_*` không resolve): bỏ bước 1, 3 (top-down), chạy Codebase-only (2, 4, 5 một phần). Ghi: "Thiếu domain map — rủi ro sót liên kết async, confidence ↓".
- **Graph Codebase stale/thiếu**: gợi ý `/understand` rebuild; tạm dùng UA + grep/read. Ghi confidence ↓.
- **Thiếu cả hai**: fallback grep/read; confidence THẤP; khuyến nghị index trước.

Luôn chạy được — không block. Không bịa kết quả cho tool không khả dụng.

### Source attribution

Ghi vào `AGENT_TRANSPARENCY.md` một dòng định tính (không ép số %): nguồn nào đóng góp gì — ví dụ *"Domain & flow async: từ UA; class/method, code logic, static trace: từ Codebase"*.
```

- [ ] **Step 6: Run the guard test**

Run: `python -m pytest cli/tests/test_codebase_explorer_protocol.py -v`
Expected: PASS — cả 3 test (template ops present, no raw UA names, all sections present).

- [ ] **Step 7: Verify skill still renders per-platform**

Run: `python -m pytest cli/tests/test_render.py cli/tests/test_snapshots.py -v`
Expected: PASS — render resolve `{{ tools.domain_* }}` không lỗi; cây thư mục snapshot không đổi.

- [ ] **Step 8: Commit**

```bash
git add .maika/skills/codebase-explorer/SKILL.md cli/tests/test_codebase_explorer_protocol.py
git commit -m "feat(skills): UA<->Codebase altitude-routing synergy protocol in codebase-explorer"
```

---

## Task 3: Cập nhật mỏng task.md Pha 1

**Files:**
- Modify: `.maika/workflows/task.md` (Pha 1 §1.4 bước 3; §6 checklist tool)
- Test: `cli/tests/test_codebase_explorer_protocol.py` (mở rộng)

**Interfaces:**
- Consumes: cùng abstract ops Task 1; protocol đã ở skill (Task 2) — task.md chỉ trỏ tới, không duplicate.

- [ ] **Step 1: Add failing assertions cho task.md**

Thêm vào `cli/tests/test_codebase_explorer_protocol.py`:

```python
TASK_WF = REPO_ROOT / ".maika" / "workflows" / "task.md"


def test_taskmd_phase1_points_to_altitude_protocol():
    text = TASK_WF.read_text(encoding="utf-8")
    assert "altitude" in text.lower() or "độ cao" in text.lower(), (
        "task.md Pha 1 chưa trỏ tới altitude-routing protocol"
    )


def test_taskmd_transparency_lists_ua_domain_ops():
    text = TASK_WF.read_text(encoding="utf-8")
    for op in ("domain_overview", "domain_flow", "domain_relationships"):
        assert "{{ tools.%s }}" % op in text, f"checklist thiếu {{{{ tools.{op} }}}}"


def test_taskmd_has_no_raw_ua_tool_names():
    assert RAW_UA.search(TASK_WF.read_text(encoding="utf-8")) is None
```

- [ ] **Step 2: Run to verify it fails**

Run: `python -m pytest cli/tests/test_codebase_explorer_protocol.py -k taskmd -v`
Expected: FAIL — task.md chưa có "altitude" và chưa list `{{ tools.domain_* }}`.

- [ ] **Step 3: Cập nhật §1.4 bước 3 (codebase-explorer call)**

Trong `.maika/workflows/task.md`, ngay đầu bước `3. Gọi codebase-explorer:` (trước dòng `- Đọc ... REQUIREMENT.md, map yêu cầu → ...`), chèn dòng:

```markdown
   - Theo **altitude routing** (xem `codebase-explorer` SKILL): UA top-down (`{{ tools.domain_overview }}`/`{{ tools.domain_flow }}`) cho domain/async; Codebase bottom-up cho symbol/đọc code. Adaptive theo độ phức tạp — task nhỏ dùng Codebase trực tiếp.
```

- [ ] **Step 4: Cập nhật §6 checklist transparency (UA domain tool)**

Trong `.maika/workflows/task.md` §6, thay dòng `- UA skills (nếu có).` bằng:

```markdown
     - UA domain tools (nếu có):
       - `[ ] {{ tools.domain_overview }}`
       - `[ ] {{ tools.domain_flow }}`
       - `[ ] {{ tools.domain_relationships }}`
```

- [ ] **Step 5: Run the full guard test**

Run: `python -m pytest cli/tests/test_codebase_explorer_protocol.py -v`
Expected: PASS — toàn bộ skill + task.md guard.

- [ ] **Step 6: Run full CLI suite (regression)**

Run: `python -m pytest cli/tests -q`
Expected: PASS — không regression (render, snapshots, platforms, update).

- [ ] **Step 7: Commit**

```bash
git add .maika/workflows/task.md cli/tests/test_codebase_explorer_protocol.py
git commit -m "feat(workflow): task.md Pha 1 points to altitude protocol + UA domain tool checklist"
```

---

## Self-Review

**Spec coverage (vs `2026-06-22-mcp-synergy-protocol-design.md`):**
- §2 phân biệt UA plugin/MCP → SKILL prose + Global Constraints (manifest key `understand-anything`).
- §3 altitude routing → Task 2 Step 3.
- §4 cổng độ phức tạp → Task 2 Step 4.
- §5 golden path handoff → Task 2 Step 4.
- §6 bản đồ năng lực (không whitelist) → Task 2 Step 5.
- §7 degradation → Task 2 Step 5.
- §8 source attribution → Task 2 Step 5; checklist UA tool → Task 3 Step 4.
- §9 binding Option A → Task 1 (toàn bộ).
- §10 nơi sửa → khớp file structure.
- §11 tiêu chí (validate_tool_mapping pass, snapshot pass) → Task 1 Step 5, Task 2 Step 7, Task 3 Step 6.

**Placeholder scan:** không có TODO/TBD; mọi step có code/lệnh cụ thể.

**Type consistency:** abstract op names (`domain_overview`/`domain_flow`/`domain_relationships`) thống nhất Task 1→2→3; tên tool concrete (`get_domain_overview`/`get_domain_flow_detail`/`get_relationships`) thống nhất mọi adapter; guard regex `RAW_UA` dùng lại ở Task 2 & 3.

**Open dependency:** tên tool UA MCP là giả định từ báo cáo. Nếu UA MCP thực tế đặt tên khác → chỉ cần sửa 4 dòng map trong `cli/platforms/*` (Task 1 Step 4) + test Step 1; skill/workflow KHÔNG đổi (đã trừu tượng qua `{{ tools.* }}`). Đây chính là lợi ích của Option A.
