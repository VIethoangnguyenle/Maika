# Reconciliation: 2 bài research GPT ↔ trạng thái thật của Maika

**Chủ đề:** Đối chiếu `maika-antigravity-apply-phase-review.md` và `maika-vnext-opensource-blueprint.md` với code thật trong `.maika/`, lọc qua `DEVELOPMENT_RULES.md`, chốt việc đáng làm.
**Ngày:** 2026-07-09
**Phương pháp:** Mọi tuyên bố "đã có / chưa có" bên dưới đều kèm `path:line` đã verify tại commit `69f0427`.

---

## 1. Verdict

Hai bài GPT **chẩn đoán đúng bệnh** nhưng **kê đơn cho một bệnh nhân khác** — chúng được viết mà không nhìn được repo thật.

- Luận điểm cốt lõi của cả hai — *"đừng bắt agent nhớ bài học bằng niềm tin; hãy compile knowledge thành coding-time gate mà agent không bỏ qua được"* — **trùng khớp tenet gốc của Maika**: `gate-by-evidence, not gate-by-instruction` ([`.maika/DEVELOPMENT_RULES.md:4`](../.maika/DEVELOPMENT_RULES.md)). Hướng đúng.
- Nhưng trong ~11 hạng mục hai bài đề xuất, **10 đã tồn tại và phần lớn đã được wire làm runtime command**. Chỉ **1 gap thật** sống sót qua DEVELOPMENT_RULES: một **deterministic code-hygiene / import check**.

> **Kết luận:** Việc đúng không phải build lại blueprint của GPT. Việc đúng là đóng đúng **một** khe hở hẹp — qua các seam đã có sẵn, không thêm file/skill/tool mới.

Hai đính chính thực tế (bài GPT sai/thiếu, đã verify live):

1. **cbm ĐÃ index repo này** — `codebase-memory-mcp cli list_projects` trả `nodes:4267, edges:8080`. Nên `validate_code_evidence` **đang live**, không dormant. (Bài GPT không biết cbm hoạt động.)
2. **UA graph vẫn chưa sinh** — `.understand-anything/knowledge-graph.json` absent. Nên lời khen của bài review ("UA-first Golden Path là điểm mạnh", §2.3–2.4) hiện là **aspirational**, không phải thành tựu đã có. Xem [§6](#6-ghi-chú-ua-first-vẫn-aspirational).

---

## 2. Bảng reconciliation (cả hai bài)

Cột trạng thái: **ĐÃ CÓ** = build rồi, đừng làm lại · **GAP** = thật sự thiếu · **LỆCH** = research mô tả sai thực tế.

### Từ `maika-antigravity-apply-phase-review.md`

| Đề xuất GPT | Trạng thái | Ở đâu trong repo |
|---|---|---|
| §5.1 `APPLY_TRACE.yaml` (black box recorder) | **ĐÃ CÓ** | `microloop-orchestrator`: `TASK_QUEUE.md`/`TASK_HANDOFF.md`/`TASK_RESULT.md` ([`README`](../.maika/tools/microloop-orchestrator/README.md)) |
| §5.2 `changed_files` edit ledger | **ĐÃ CÓ** | `TASK_RESULT.md` + `ACTIVITY_LOG.jsonl` (`result_written`, `subagent_done`) |
| §5.3 `code_hygiene` trong `conventions.yaml` | **GAP** | `conventions.yaml` chỉ có `naming/naming_patterns/package_structure/design_patterns/upstream_constraints/exceptions/resolved` — không có `code_hygiene` |
| §5.4 skill `code-hygiene` | **GAP (nhưng đừng làm skill)** | Không tồn tại. Xem [§5](#5-từ-chối-có-lý-do) — fold vào gate/projector, không dựng skill |
| §5.5 skill `apply-runner` (microloop) | **ĐÃ CÓ** | `microloop-orchestrator` chính là nó (READ→PATCH→TRACE, 3 tier) |
| §5.6 gate deterministic (`apply-trace-ready`, `apply-final`) | **ĐÃ CÓ một phần** | `gate-check` có 16 validator gồm `apply-gate`, `implementation-context`, `handoff-slice`, `code-evidence`… `apply-final`/`hygiene` là phần thiếu |
| §6 fresh session cho apply | **ĐÃ CÓ** | `.maika/profiles/execution-mode.yaml`: `subagent`/`fresh-session`/`inline-reload` |
| §7 `TOKEN_LOG`→`CONTEXT_BUDGET` | **ĐÃ CÓ (đừng đổi tên)** | `procedures/token-tracking.md`, `context-loader.md`, `context-compressor.md` đã làm context-budget; đổi tên là cosmetic |
| §2.3–2.4 UA-first / Golden Path là điểm mạnh | **LỆCH** | Doctrine đúng, nhưng UA graph chưa sinh → hiện aspirational. Xem [§6](#6-ghi-chú-ua-first-vẫn-aspirational) |
| P2.1 `AGENT_TRANSPARENCY.yaml` structured | **ĐÃ CÓ** | `knowledge/templates/AGENT_TRANSPARENCY.tpl.md` + gate `teaching-moment`/`memory-recall` consume nó |
| P2.2 skill `memory-recaller` | **ĐÃ CÓ (dạng gate)** | `validate_memory_recall` ([`gates.py:210`](../.maika/tools/gate-check/gates.py)) + agent-memory MCP |
| P2.3 Dashboard Control Tower | **ĐÃ SHIP** | `maika dashboard serve` (PR #10); helper trong `orchestrator.py` (`append_activity_event`, `record_parent_event`) |

### Từ `maika-vnext-opensource-blueprint.md`

| Pattern / tool GPT | Trạng thái | Ở đâu trong repo |
|---|---|---|
| Aider — Edit→lint/test→fix loop | **ĐÃ CÓ** | microloop (READ→PATCH→TRACE→VERIFY) |
| Gemini CLI — event stream / `stream-json` | **ĐÃ CÓ** | `ACTIVITY_LOG.jsonl` (append-only timeline) |
| OpenHands — Control Tower / runtime | **ĐÃ SHIP** | `maika dashboard serve` |
| SWE-agent — trajectory archive | **ĐÃ CÓ** | `EXTRACTION_INPUT/REPORT.md` + `knowledge-curator` + `knowledge/archive/` |
| Cline — headless CLI + JSON output | **ĐÃ CÓ một phần** | `gate-check/cli.py` (exit-code + message); JSON output là polish, không phải gap chức năng |
| Roo Code — mode separation | **ĐÃ CÓ** | `execution-mode.yaml` + phase-chain gate (`Pha 1/2/3 DONE`) |
| Goose — capability registry | **ĐÃ CÓ** | `rule-projector` + `gate-check/capability.py` (probe cbm/UA) |
| **Spotless / Checkstyle — import hygiene** | **GAP** | `rule-projector/backends/checkstyle.py` emit NestedIfDepth/MethodLength/Cyclomatic/naming/TODO — **KHÔNG emit `UnusedImports`/`AvoidStarImport`/`RedundantImport`** |
| OpenRewrite — codemod | **TỪ CHỐI (chưa)** | Không có fixture/lỗi quan sát yêu cầu codemod → R3 defer |
| Semgrep — custom static rules | **TỪ CHỐI (chưa)** | Tương tự; note để sau nếu có litmus PII/token thật |

---

## 3. Gap thật duy nhất

Xâu chuỗi cả hai bảng: mọi hạng mục apply-phase machinery đều đã có, **trừ một chuỗi**:

```
conventions.yaml (không có chỗ cho hygiene)
   → rule-projector/checkstyle (không emit import rule)
      → gate-check (không có command code-hygiene)
         → task.md (không gọi hygiene ở pha apply)
```

Đây chính xác là lỗi *"không import thừa"* bạn gặp lặp lại. Nó lọt vì **chưa được compile thành gate** — đúng như luận điểm GPT, nhưng lời giải nằm ở việc **nối 3 seam đã tồn tại**, không phải dựng blueprint.

Điểm mấu chốt về thiết kế: **hygiene check này KHÔNG phụ thuộc index** (thuần filesystem / checkstyle). Nên nó diệt được lỗi import thừa **ngay cả khi UA/cbm vắng** — khác hẳn `code-evidence` gate vốn phụ thuộc cbm. Đây là lý do nó đáng ưu tiên P0: leverage cao, không chờ substrate.

---

## 4. Đề xuất phát triển (how-level + litmus)

Đóng gap qua **3 seam có sẵn**. Không file/skill/tool mới. Thỏa R1 (consumer cùng change), R3 (lỗi đã quan sát), R5 (mở rộng cơ chế đang chạy), R7 (diff nhỏ).

### Seam 1 — chỗ ở cho hygiene trong schema

- **File:** [`.maika/knowledge/long-term/conventions.yaml`](../.maika/knowledge/long-term/conventions.yaml) + doc schema tại `convention-intelligence-builder/references/conventions-draft-template.md`.
- **Sửa:** thêm section top-level `code_hygiene:` per-language, mỗi rule có `severity` / `agent_action` / `applies_to`:

```yaml
code_hygiene:
  java:
    no_unused_imports:   { severity: mandatory, agent_action: fix_before_continue, applies_to: ["**/*.java"] }
    no_wildcard_imports: { severity: mandatory, agent_action: fix_before_continue, applies_to: ["**/*.java"] }
    no_redundant_imports:{ severity: mandatory, agent_action: fix_before_continue, applies_to: ["**/*.java"] }
```

- **Consumer cùng change (R1):** rule-projector (Seam 2) đọc section này. Không có Seam 2 thì **không** thêm section (nếu không sẽ là field rác).

### Seam 2 — projection sang Checkstyle

- **File:** [`.maika/tools/rule-projector/projector.py`](../.maika/tools/rule-projector/projector.py) (core `conventions → IR`) + [`backends/checkstyle.py`](../.maika/tools/rule-projector/backends/checkstyle.py) + schema `ir_schema.json`.
- **Sửa:**
  1. `projector.py`: thêm `project_code_hygiene(conventions)` — sao pattern `project_naming()` (`projector.py:64`) — và gọi trong `build_ir()` (`projector.py:89`); cập nhật `ir_schema.json` chấp nhận rule-kind mới (ví dụ `import_hygiene`).
  2. `checkstyle.py::_emit_rule` (`checkstyle.py:14`): với rule-kind đó, emit dưới `TreeWalker`:
     ```xml
     <module name="UnusedImports"/>
     <module name="RedundantImport"/>
     <module name="AvoidStarImport"/>
     ```
- **Verify:** cập nhật `tests/test_checkstyle.py` + fixture `tests/fixtures/expected-checkstyle.xml`; regenerate `generated/checkstyle.generated.xml`.

### Seam 3 — gate + wiring runtime

- **File:** [`.maika/tools/gate-check/gates.py`](../.maika/tools/gate-check/gates.py) + `cli.py`; wiring tại [`.maika/workflows/task.md`](../.maika/workflows/task.md) (cạnh chỗ đã gọi gate ở `task.md:283` memory-recall và `:484` teaching-moment).
- **Sửa:** thêm `validate_code_hygiene`, đăng ký vào `VALIDATORS` + subcommand `code-hygiene`. Theo đúng kiến trúc pure/impure đang có (`gates.py` tất định, `capability.py` probe bẩn):
  - **Deterministic-when-available:** nếu project có gradle/checkstyle → chạy checkstyle đã project ở Seam 2; parse report.
  - **Pure fallback (cross-env):** parse import block của changed `.java` vs sử dụng trong body → phát hiện unused/wildcard. Cần cho môi trường không có gradle (Maika tự thân là Python).
  - **Degrade sạch:** không chạy được checkstyle **và** không đủ tín hiệu → nêu lý do rõ (như `code-evidence` yêu cầu embed lỗi thật), không fail-open lặng.
- **Wire:** gọi `code-hygiene --changed-files` ở pha apply/verify của `task.md`, block final nếu FAIL.

### Litmus tái hiện lỗi (R3 — bắt buộc)

Fixture dưới `gate-check/tests/`: một `.java` có `import java.util.*;` (wildcard) + một unused import.

```
gate code-hygiene (file bẩn)   → exit != 0  (FAIL)
sau khi bỏ import              → exit 0      (PASS)
```

Không có litmus này thì PR thêm gate bị chính R3 bác.

---

## 5. Từ chối có lý do

| GPT đề xuất | Từ chối vì | Rule |
|---|---|---|
| File `APPLY_TRACE.yaml` mới | Trùng `TASK_QUEUE/HANDOFF/RESULT` của microloop | R5, R7 |
| Skill `apply-runner` mới | microloop-orchestrator đã là nó | R5 |
| Skill `code-hygiene` mới | Cả một skill cho việc parse import là over-build; fold vào gate + projector | R7 |
| CLI `maika status` / event-stream mới | `ACTIVITY_LOG.jsonl` + dashboard đã có | R5 |
| Đổi tên `TOKEN_LOG`→`CONTEXT_BUDGET` | Cosmetic; procedures đã làm context-budget | R7 |
| Semgrep / OpenRewrite làm dependency | Chưa có lỗi/fixture quan sát yêu cầu | R3 |

Cả bảng này là hiện thân của R7: *"có thể hữu ích sau" là lý do từ chối, không phải lý do thêm.*

---

## 6. Ghi chú: UA-first vẫn aspirational

Bài review khen UA-first Golden Path như điểm mạnh đã có. Thực tế đã verify:

- **cbm:** index rồi cho repo này (4267 nodes) → tốt.
- **UA:** `.understand-anything/knowledge-graph.json` **chưa sinh** → bước "UA step 1 ALWAYS" trong `codebase-explorer` hiện **không thỏa được**; chỉ cbm + grep chạy thật.

Doctrine bạn đã chốt (2026-07-08): **UA-first tuyệt đối, KHÔNG demote xuống cbm-first; UA vắng = "lỗi, phải build UA graph", không tụt grep lặng lẽ.** Vì vậy đây **không** phải đề xuất "làm mềm UA" — mà là ghi nhận: việc *sinh UA graph* là hạng mục riêng, **ngoài scope apply-phase này**. Chính vì UA còn vắng, đề xuất §4 cố ý chọn hygiene gate **không phụ thuộc index** để có giá trị ngay hôm nay.

---

## 7. Chốt

```
Maika không thiếu apply-phase machinery.
Nó đã có ~10/11 thứ GPT đề xuất (microloop, ledger, event-log, dashboard, 16 gate, projector).
Cái thiếu thật: MỘT deterministic hygiene check mà projector chưa emit.
→ Đừng build blueprint. Nối 3 seam. Kèm litmus. Xong.
```
