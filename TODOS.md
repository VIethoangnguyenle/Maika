# TODOS — Maika

> Tổng hợp từ review 3 góc (Sản phẩm / Kiến trúc / DX) ngày 2026-06-18.
> Sợi chỉ xuyên suốt: Maika đang đầu tư vào *độ thuần kiến trúc* (portability, generic, 5-pha)
> trước khi *chứng minh giá trị* và *hạ thuế adoption*. Thứ tự dưới đây de-risk theo chi phí thấp nhất.

---

## Ưu tiên brainstorm / thực thi (next)

> Xếp theo dependency + đòn bẩy. `[BRAINSTORM]` = cần `/brainstorm` hoặc office-hours trước khi build (còn ambiguity thiết kế); `[EXEC]` = đã specced hoặc cơ học, làm thẳng.

**Bậc 0 — Linchpin (chặn mọi thứ về giá trị):**
1. **P1.1** `[EXEC]` — chạy baseline-arm litmus. UP1 / UP5 / UP6 / P2.1-validate đều phụ thuộc. *(tốn time của bạn ~2-3 ngày chạy ticket thật — không thay thế được bằng CC)*

**Bậc 1 — Guard rẻ:** ✅ **DONE** — UP3 (`test_snapshots.py` golden-snapshot có sẵn) + P3.1 (DRY `framework_version`, branch `platform-hardening`).

**Bậc 2 — Đặt cược chiến lược, CHỈ sau khi P1.1 validate (cần brainstorm):**
2. **UP1** `[BRAINSTORM]` — eval harness liên tục + wire SP1c substrate.
3. **P2.1 + UP2** `[BRAINSTORM]` — capability-based portability + registry-as-data.
4. **UP6** `[BRAINSTORM]` — OpenSpec first-class (đo bypass trước, hạ friction sau).
5. **UP5** `[BRAINSTORM]` — phase collapse theo knowledge state (office-hours trước).

**Bậc 3 — Dọn cấu trúc, độc lập validation (làm được NGAY mà không cần P1.1):**
6. **P2.5** `[EXEC]` — dashboard contract single-source (~30-45′ CC, an toàn).
7. **P3.6** `[EXEC]` — tách orchestrator pure-vs-emit (sau P2.5).
8. **P2.3** `[BRAINSTORM-lite]` — gom resolved-config canonical. **Không mechanical:** chicken-and-egg (platform nằm TRONG config → không biết `framework_root` trước khi đọc). Chốt approach trước. Win nhỏ an toàn riêng: chỉ fix default `.maika`≠`.agents`.

**Bậc 4 — Dashboard correctness (frozen ở P6; sau khi quay từ P1.1):**
9. **P3.4** `[EXEC]` — archive `active/` trọn vẹn (root cause overlap bug đã quan sát live).
10. **P3.5** `[EXEC]` — dashboard ticket-aware (sau P3.4).

**Bậc 5 — Hệ quả / phụ thuộc:**
11. **UP4** `[EXEC]` — `--dry-run` + drift detection.
12. **P3.3** `[EXEC]` — update roadmap SP3 framing (sau P2.1).

> Chưa có time cho P1.1 mà muốn tiến: cụm **P2.5 → P3.6** là EXEC an toàn, độc lập, làm được ngay. P2.3 cần brainstorm trước (chicken-and-egg).

---

## Enforcement hardening (audit 2026-06-20)

> Track riêng, ngoài roadmap P/UP. Nguồn: audit RULES/SKILLS/WORKFLOWS 2026-06-20 — phát hiện enforcement 2 tầng, phần lớn `[CRITICAL]` rule chỉ "trên giấy" (chỉ `knowledge-checkpoint` được hook chặn cơ học). 6 gap xếp theo đòn bẩy. Handoff tạm thời của audit đã được dọn khỏi source; specs/plans tương ứng là nguồn tham chiếu lâu dài.

- **#1 — Bash-write bypass** ✅ **DONE** (C-22b, PR #12, branch `bash-write-gate`). Hook chỉ match `Edit|Write|MultiEdit`; ghi code qua Bash né gate. `parse_shell_writes` heuristic + matcher 3 runtime. Spec/plan: `2026-06-20-bash-write-gate-*`.
- **#2 — `/opsx:apply` cửa sau** ✅ **DONE** (C-23, PR #13, branch `apply-gate`, stacked trên #12).
- **#3 — gate chưa wired vào workflow** ✅ **DONE** (C-23, cùng PR #13). Mở rộng write-gate thành apply-gate: `validate_apply_gate` (Pha 2 DONE + no open `[BLOCKER-ARCH]`) cắm vào `evaluate_write`. Spec/plan: `2026-06-20-apply-gate-*`.
- **#4 — skill phá hủy thiếu `pre_conditions:` máy đọc** ⬜ TODO (codex). knowledge-curator (reset `active/`) + spec-extract guard chỉ là prose; 8/14 skill không có `pre_conditions`, 0/14 khai báo `outputs:`.
- **#5 — R-DNA-7 teaching-moment không có hook** ✅ **DONE** (C-24, branch `teaching-moment-checkpoint`). "Deterministic acknowledgment, not detection": validator `gate-check teaching-moment` (section `## Teaching Moment Check` với status none|captured|declined|pending-confirmation), template seed non-passing, knowledge-curator PRE-CHECK ABORT trước archive. Spec/plan: `2026-06-20-teaching-moment-checkpoint-*`. Giới hạn: archive không bị runtime-hook chặn → call site honor-code.
- **#6 — `db-remote` hard-coded + orphan `document-writer`** ⬜ TODO (codex). db-explorer/codebase-explorer hard-code `db-remote` trong khi KG tools template `{{ tools.* }}`; `document-writer` không workflow nào gọi.
- **C-27 — memory-tool capability templating** ✅ **DONE** (branch `memory-tool-capability-templating`). Follow-on của #6/C-26: mở rộng pattern `{{ tools.* }}` sang memory. 7 abstract op `dynamic_memory_*` thêm vào `REQUIRED_TOOL_KEYS` + map 5 platform; de-hardcode 5 operational template (rules-tool, rules-exec, m7-memory-push, knowledge-curator SKILL, bootstrap); guard test `cli/tests/test_no_hardcoded_memory_tools.py` chống re-hardcode. Quyết định nền: agentmemory **KHÔNG bundle** — project cuối cài **MCP-only** (auto-capture hooks off), Maika giữ memory governance qua M7; recipe `.maika/profiles/agent-memory-mcp-only-setup.md`. Authority/config (spec 2026-06-19) không đổi. Spec/plan: `2026-06-21-memory-tool-capability-templating-*`.

> Residual đã chấp nhận trong #1–#3: `eval`/dynamic-shell writes (threat model); R-Apply-1 confirm + spec-validator pre-apply (concern riêng, có thể spec sau).

---

## Best-practice gaps (audit 2026-07-05)

> Track riêng. Nguồn: [docs/superpowers/specs/2026-07-04-anthropic-bp-audit-report.md](docs/superpowers/specs/2026-07-04-anthropic-bp-audit-report.md)
> (rubric citation-grounded: [2026-07-04-anthropic-bp-rubric.md](docs/superpowers/specs/2026-07-04-anthropic-bp-rubric.md)). Chỉ liệt kê phần A (đã khớp observed failure);
> watchlist xem phần B của báo cáo. A-6/A-7 không tạo entry mới — chỉ bổ sung căn cứ trích dẫn cho UP5 và P1.1/UP1 sẵn có.

- **BP-A1 — Hook 3 rule `[CRITICAL]` còn giấy** ⬜ TODO — R-Data-1/R-KL-1/R-Tool-1 không khớp hook nào; thêm matcher vào gate sẵn có hoặc ghi lý do không hook được ngay tại rule. Why: F-01/F-02 (audit 2026-06-20, assessment W1). Effort: CC ~30-45′. [BP-12]
- **BP-A2 — Script hóa việc deterministic trong 7 skill + 8 workflow** ⬜ TODO — spec-validator ALGORITHM, knowledge-curator reset `active/` (đóng luôn gap #4 pre_conditions), các bước CHECK đầu approve-*/scan; prune prose cùng PR (diff âm). Why: F-01 gap #4, F-02, bài học Pha 3 driver. Effort: CC ~1-2h, làm theo cụm. [BP-07]
- **BP-A3 — Rule diet khối bootstrap (1103 dòng)** ⬜ TODO — khử 2 cặp trùng meta-prompt↔rules (load-order, flow-prohibition); dời R-Skill-1 schema + bảng tool agent-memory khỏi bootstrap; hạ marker theo phép thử "bỏ đi có gây lỗi không". Why: F-05 (context tràn 2026-07-03), F-04/F-06/F-07. Effort: CC ~1h + review kỹ (đụng bề mặt nhạy). [BP-15, BP-10, BP-20, BP-13]
- **BP-A4 — Gate đòi evidence thay lời khai** ⬜ TODO — RULES.md + tdd.md theo mẫu teaching-moment checkpoint (C-24); gate không đòi được evidence thì bỏ. Why: F-03 (W2 compliance theater). Effort: CC ~30′. [BP-21]
- **BP-A5 — Dispatch prompt Pha 1 đủ 4 thành phần** ⬜ TODO — bổ sung output format + task boundaries vào template task.md:50 (như fresh-session Pha 3 đã làm). Why: F-08 (task-run-quality 2026-07-03, mảnh còn lại). Effort: CC ~15′. [BP-18]

---

## P1 — Làm trước (đòn bẩy cao, chi phí thấp)

### P1.1 — U0 litmus phải có baseline arm (đo outcome, không đo process)
- **What:** Sửa spec U0 để chạy A/B trên cùng ticket: (1) Maika full 5-pha; (2) cùng agent chỉ với CLAUDE.md + ad hoc. Đo **outcome**: rework (review comment / vòng sửa / bug lọt), convention adherence, blast-radius bắt đúng, số lần can thiệp tay, token + wall-clock mỗi arm.
- **Why:** North Star hiện tại (Generic, Knowledge-first, Long-term memory, IDE-independent) đều là *means*. Không phép đo nào chạm tới giá trị thật (diff đúng hơn, ít rework hơn). U0 đang đo "process chạy E2E được không", không đo "Maika có đáng so với baseline không". Đây là phép đo quyết định cả thesis.
- **Context:** [docs/superpowers/specs/2026-06-17-upgrade-roadmap-design.md](docs/superpowers/specs/2026-06-17-upgrade-roadmap-design.md) §4 (U0), §6 (R1). R1 fix (Vietbank + `active/` rỗng) đo được cold-start accumulation nhưng (a) agent có thể đã thấy codebase Vietbank từ trước → vẫn nhiễm, (b) "accumulation" vẫn là process metric. Baseline arm là mảnh còn thiếu.
- **Exit:** litmus-report chứa so sánh Maika-arm vs baseline-arm trên **≥3 ticket** (tiny/standard/complex), verdict định lượng: giảm rework X%, tốn thêm Y% token.
- **Effort:** human ~2-3 ngày / CC: thiết kế protocol ~30 phút (chạy ticket thật vẫn tốn thời gian thật).
- **Priority:** P1. **Depends on:** U2-min (repo sạch) như roadmap.

---

## P2 — Quan trọng (sau khi P1 mở khoá)

### P2.1 — Resolve portability theo trục MCP/capability (mở rộng adapter scaffold-time)
- **What:** `tool_mapping` value chuyển thành (hoặc thêm tầng) **abstract-op → required-capability → MCP đã chọn cung cấp capability đó** (tái dùng `provides` trong manifest), fallback về tool native của platform / generic khi không MCP nào cung cấp. Route ~16 chỗ hardcode trong body qua render context `tools`.
- **Why:** Hiện `tool_mapping` map abstract-op → **một MCP cụ thể** (`codebase-memory-mcp`, `confluence` hardcode). Hai user cùng Claude Code nhưng MCP code-search khác nhau đều nhận `mcp__codebase-memory-mcp__...`. Lớp "portable" không portable đúng trên trục quan trọng nhất. **Đây là hiện thân thật của SP3-portability — và rẻ hơn nhiều so với "build mới" roadmap đang frame**, vì adapter đã tồn tại. (2026-06-22: socraticode đã được thay bằng codebase-memory-mcp, nhưng vấn đề hardcode-per-platform vẫn còn — chỉ đổi MCP đích.)
- **Context:** [cli/platforms/base.py:37-102](cli/platforms/base.py#L37-L102), [cli/platforms/claude_code.py:28-44](cli/platforms/claude_code.py#L28-L44), [cli/scaffold.py:48-53](cli/scaffold.py#L48-L53) (`has_capability` đã có notion `provides` nhưng chỉ dùng gate plugin). Roadmap SP3: [docs/superpowers/specs/2026-06-17-upgrade-roadmap-design.md](docs/superpowers/specs/2026-06-17-upgrade-roadmap-design.md) §4.
- **Effort:** human ~3-5 ngày / CC ~1-2 giờ.
- **Priority:** P2. **Depends on:** P1.1 (validate trước khi đổ công vào portability), P1.2.

### P2.3 — Gom resolved-config về một vị trí canonical
- **What:** Hiện config có thể ở 3 nơi (`.agents`/`.claude`/`.maika`) với preference-order + fallback. Gom về **một** vị trí theo `platform.framework_root`, bỏ multi-candidate scan, thay bằng một migration cho layout cũ.
- **Why:** 6 commit gần nhất toàn về path resolution (platform-native-root, meta-prompt-relocation, templatize-paths, neutral-rename) = cùng một bề mặt bị sửa đi sửa lại = smell kiến trúc. Bề mặt 3-vị-trí × platform-root sinh bug lặp.
- **Context:** [cli/scaffold.py:61-132](cli/scaffold.py#L61-L132) (`resolved_config_candidates`, `load_resolved_config`).
- **Effort:** human ~1 ngày / CC ~30 phút.
- **Priority:** P2.
- **Bundle (S2, từ dashboard review 2026-06-20):** `framework_root` default **lệch nhau** giữa các module — dashboard reader default `.maika` ([cli/dashboard/reader.py:68](cli/dashboard/reader.py#L68)), orchestrator default `.agents` ([.maika/tools/microloop-orchestrator/orchestrator.py:103](.maika/tools/microloop-orchestrator/orchestrator.py#L103)). Chưa nổ vì resolved-config luôn ghi rõ key, nhưng là bẫy. Gom về **một** default canonical khi làm P2.3.

### P2.5 — Nâng dashboard runtime contract thành interface có single-source (chống drift)
- **What:** Tạo một module hằng số contract dùng chung (tên event: `subagent_spawned/started/done/blocked`, `task_*`, `parent_brain_updated`, ...; và `VALID_RUNTIME_STATUS`) import bởi **cả** orchestrator (writer, ship sang target) **lẫn** dashboard reader (cli/). Cân nhắc thêm version field vào `ACTIVITY_LOG`/contract.
- **Why:** Phát hiện 2026-06-20 (architect review tính năng dashboard): orchestrator và reader cùng phụ thuộc một bộ event/status nhưng mỗi bên **hard-code string riêng**. Reader xử unknown-event generic nên không crash, nhưng **không gì chống drift ngữ nghĩa** giữa hai lớp — đây là bề mặt coupling xuyên-lớp duy nhất của tính năng. `ACTIVITY_LOG.jsonl` giờ là interface runtime first-class, nên đáng được đối xử như interface (single source + version) thay vì spec markdown + literal rải rác.
- **Context:** [.maika/tools/microloop-orchestrator/orchestrator.py](.maika/tools/microloop-orchestrator/orchestrator.py) (writer), [cli/dashboard/server.py](cli/dashboard/server.py) `read_runtime` (reader); spec [docs/superpowers/specs/2026-06-19-dashboard-runtime-contract-design.md](docs/superpowers/specs/2026-06-19-dashboard-runtime-contract-design.md) §6.
- **Effort:** CC ~30-45 phút. **Priority:** P2 (interface drift). **KHÔNG làm trong PR #10** (freeze dashboard ở P6).

---

## P3 — Nice to have

### P3.3 — Cập nhật framing chi phí SP3 trong roadmap
- **What:** Sau khi xác nhận P2.1 (SP3 = mở rộng adapter, không phải greenfield), cập nhật §2/§4 roadmap: SP3 từ "spec mới, đòn bẩy build lớn nhất" → "mở rộng adapter + migrate ~16 ref + test". Điều này dịch lại bài toán "portability có đáng không".
- **Context:** [docs/superpowers/specs/2026-06-17-upgrade-roadmap-design.md](docs/superpowers/specs/2026-06-17-upgrade-roadmap-design.md) §2, §4.
- **Effort:** CC ~15 phút. **Priority:** P3. **Depends on:** P2.1.

### P3.4 — Archive `active/` TRỌN VẸN theo ticket (root cause: archive một phần)
- **What:** Khi sang ticket mới, archive/reset toàn bộ artifacts ticket cũ khỏi `knowledge/active/`: `TASK_QUEUE.md`, `TASK_HANDOFF.*.md`, `TASK_RESULT.*.md`, **và `PARENT_BRAIN.md`** (mirror cuộc trò chuyện). Dùng event `archive_started`/`archive_done` đã có. Hiện tại reset **một phần**: chỉ `AGENT_TRANSPARENCY` được reset sang ticket mới, các file còn lại bị bỏ lại → overlap.
- **Why:** Phát hiện 2026-06-20 soi BA-Framework live, 3 nguồn 2 ticket cùng lúc: `AGENT_TRANSPARENCY` = `SME-TRANSFER-003` (đang `applying`), nhưng `TASK_QUEUE`+results = `SME-TRANSFER-002` (00:09 hôm trước), `PARENT_BRAIN` = cuộc trò chuyện `SME-TRANSFER-002` (17:29 hôm trước). Chính `PARENT_BRAIN` thú nhận "SME-TRANSFER-002 was already archived/reset in AGENT_TRANSPARENCY.md" → archive không trọn vẹn. Dashboard hiện phase ticket mới đè lên queue + conversation ticket cũ ("overlap"). Lỗi vòng đời artifact, không phải lỗi dashboard.
- **Context:** orchestrator emit ([.maika/tools/microloop-orchestrator/orchestrator.py](.maika/tools/microloop-orchestrator/orchestrator.py)); contract [docs/superpowers/specs/2026-06-19-dashboard-runtime-contract-design.md](docs/superpowers/specs/2026-06-19-dashboard-runtime-contract-design.md) §6 (event `archive_*`). Liên quan P5 roadmap.
- **Effort:** CC ~30-45 phút. **Priority:** P3 (gốc của P3.5).

### P3.5 — Dashboard: ticket-aware, tách artifacts ticket-trước khỏi ticket hiện tại (symptom mitigation)
- **What:** Trong `read_runtime`, lấy `current_ticket` từ `AGENT_TRANSPARENCY`; với `TASK_QUEUE` và `PARENT_BRAIN`, nếu `ticket_id` của chúng `≠ current_ticket` (hoặc mtime ≪ phase mtime) thì đánh dấu "từ ticket trước" thay vì gộp vào progress/parent-panel hiện tại. UI: không khoe `2/2 100%` và không hiện parent-brain cũ dưới ticket mới.
- **Why:** Giảm overlap khi P3.4 chưa làm. Use case thật đã quan sát: queue=002, parent_brain=002, phase=003. **KHÔNG làm trong PR #10** — CEO verdict freeze dashboard ở P6; việc sau, sau khi quay lại từ P1.1.
- **Context:** [cli/dashboard/server.py](cli/dashboard/server.py) `read_runtime`, [cli/dashboard/reader.py](cli/dashboard/reader.py) `read_run`.
- **Effort:** CC ~30 phút. **Priority:** P3. **Depends on:** ưu tiên P3.4 trước (sửa gốc).

### P3.6 — Tách orchestrator: pure loop-protocol vs dashboard emit (SRP nhẹ)
- **What:** `orchestrator.py` đang gánh 2 vai trong một file: pure loop-protocol (`run_loop`/`next_task`/`apply_result`/`topo_sort` — DI, không I/O, unit-test được) và dashboard emit (`append_activity_event`/`write_parent_brain`/`initialize_runtime_queue` — I/O filesystem). Tách phần emit ra module riêng (vd `runtime_emit.py`) khi thuận tiện.
- **Why:** SRP nhẹ; emit đặt cạnh nơi sở hữu lifecycle queue/handoff là hợp lý nên không gấp. Tách giúp test pure-protocol khỏi đụng filesystem rõ ràng hơn.
- **Context:** [.maika/tools/microloop-orchestrator/orchestrator.py](.maika/tools/microloop-orchestrator/orchestrator.py).
- **Effort:** CC ~20 phút. **Priority:** P3 (nhẹ nhất). **Depends on:** nên làm cùng/sau P2.5 (single-source constants).

---

## Upgrades — nâng cấp/đổi hướng cấu trúc (net-new, không phải fix)

> Khác với P1–P3 (sửa lỗi). Đây là thay đổi cấu trúc/chiến lược. Đặt tên UP để tránh nhầm với U0–U3/SP của roadmap.
> Thứ tự đề xuất: UP1 + UP3 trước (rẻ, bảo vệ mọi thay đổi sau), rồi UP2, UP4, UP5 sau cùng.

### UP1 — Eval harness: biến validate-first thành tín hiệu liên tục
- **What:** Harness lặp lại được: vài fixture ticket trong repo mẫu + scorer (rubric, có thể LLM-judge) → chạy Maika-arm vs baseline-arm → xuất delta chất lượng. Cắm vào CI mỗi khi đổi rules/skills/meta-prompt.
- **Why:** Gap lớn nhất của dự án — có test cho CLI (scaffold đúng không) nhưng **zero test cho giá trị cốt lõi** (protocol có làm agent ra output tốt hơn không). Mỗi lần refactor rule/skill hiện không có gì bắt được "vừa làm agent tệ đi". Harness biến chất lượng thành regression test, hiện thực hoá toàn bộ finding CEO.
- **Context:** Mở rộng P1.1 từ litmus một-lần thành signal liên tục. Tái dùng instrumentation ở [.maika/procedures/token-tracking.md](.maika/procedures/token-tracking.md).
- **Effort:** CC ~1-2 giờ dựng khung; chạy ticket thật vẫn tốn thời gian thật.
- **Priority:** cao nhất trong Upgrades. **Depends on:** P1.1 (baseline arm).
- **SP1c substrate (eng-review 2026-06-20):** `outcome.py`/`stats.py` (rule_effectiveness + prune_candidates + first_pass trend) hiện **orphan** — chỉ `test_outcome.py` gọi, `task.md` Pha 3 KHÔNG gọi, `outcome-log.yaml` chưa từng được ghi; không spec/plan nào coi nó là substrate. **Quyết định: resurrect làm 1 signal của UP1** (không xóa, không cắm ngay — wiring thuộc UP1, sau P1.1). Khi làm UP1: wire `build_record`/`append_to_log` vào `task.md` Pha 3, **bắt buộc append TRƯỚC `knowledge-curator.archive()`** (sai thứ tự = mất data âm thầm → **regression test bắt buộc**); reconcile path spec `.knowledge-layer/` → `{{ platform.framework_root }}/knowledge/long-term/`. Trục SP1c (rule-prune, bài W6) **bổ sung** chứ không trùng trục Maika-vs-baseline của P1.1. Context: [.maika/tools/microloop-orchestrator/outcome.py](.maika/tools/microloop-orchestrator/outcome.py), [stats.py](.maika/tools/microloop-orchestrator/stats.py), [SP1c spec](docs/superpowers/specs/2026-06-17-sp1c-outcome-loop-design.md).

### UP2 — Platform/MCP registry dạng data, không phải code
- **What:** Chuyển mỗi platform từ class Python (`tool_mapping` hardcode) sang YAML khai báo (một file/platform hoặc một registry). Thêm platform/MCP = thêm data.
- **Why:** (a) biến FAQ "thêm platform custom" thành thật (không cần viết Python); (b) abstract-op keyset validate schema ở một chỗ → diệt nguyên lớp silent-failure **về cấu trúc**, không chỉ bằng test (gộp với P1.2); (c) P2.1 capability-resolution thành data-driven. Phép đơn giản hoá làm portability rẻ thật.
- **Context:** [cli/platforms/base.py](cli/platforms/base.py), [cli/platforms/claude_code.py](cli/platforms/claude_code.py) và các platform khác.
- **Effort:** human ~2-3 ngày / CC ~1 giờ.
- **Priority:** sau UP1. **Depends on:** P2.1. *(P1.2 + UP3 đã done — keyset validation + golden-snapshot có sẵn.)*

### UP4 — `maika init/update --dry-run` + drift detection
- **What:** `--dry-run` hiện diff trước khi ghi; `maika status --check-drift` cảnh báo khi file framework-owned bị sửa tay (sẽ bị overwrite khi update).
- **Why:** `update` re-render file framework → user sợ bị ghi đè (chính nỗi sợ này sinh ra file-ownership policy). Dry-run + drift xây niềm tin cho mô hình idempotent-update.
- **Context:** [cli/commands/update.py](cli/commands/update.py), [cli/commands/status.py](cli/commands/status.py), [docs/maika-file-ownership-policy.md](docs/maika-file-ownership-policy.md).
- **Effort:** human ~1 ngày / CC ~30 phút.
- **Priority:** trung bình.

### UP5 — (Tham vọng) Phase collapse theo knowledge state
- **What:** Phase trở nên collapsible theo trạng thái tri thức — nếu output của một phase đã cached/ổn định trong knowledge layer (vd kiến trúc module này vừa explore), thì short-circuit nó. Thuế 5-pha giảm dần khi tri thức chín.
- **Why:** Câu trả lời cấu trúc cho bài toán thuế adoption, hiện thực dream-state "Maika vô hình". Tham vọng hơn U1 tiering (vốn chỉ phân loại theo kích thước task).
- **Context:** Liên quan U1 ([roadmap §4](docs/superpowers/specs/2026-06-17-upgrade-roadmap-design.md)), memory hierarchy active/long-term.
- **Effort:** human ~1 tuần+ / CC ~vài giờ. **Direction — nên qua office-hours/spec trước khi build.**
- **Priority:** sau khi validate xong (UP1 + P1.1). **Depends on:** P1.1, UP1.

### UP6 — OpenSpec first-class, ít friction (đo bypass TRƯỚC, hạ thuế SAU)
- **What:** Hai bước. (1) **Instrument**: thêm provenance `spec_path` vào record outcome (hoặc telemetry tương đương) để đo **% task Pha 2 thực sự đi qua opsx vs bypass**. (2) Sau khi có số: tách vai trò **format-of-record vs authoring-engine** → rule `R-Spec-3` (artifact bắt buộc, authoring-path linh hoạt) và cân nhắc skill `spec-orchestrator` bọc opsx (1 lệnh → 4 artifact + `openspec validate`, bỏ loop tay).
- **Why:** `task.md` Pha 2 HARDBLOCK opsx nhưng thực tế bị bypass vì authoring-tax cao ([opsx-propose.md](.maika/workflows/opsx-propose.md): loop `openspec instructions --json` từng artifact, 4 artifact kể cả task nhỏ). Luật bị bypass làm hỏng chuỗi phase-gate. Adoption-tax đã quan sát nhưng chưa được track ở đâu trong backlog.
- **Context:** [.maika/workflows/task.md](.maika/workflows/task.md) Pha 2, [.maika/workflows/opsx-propose.md](.maika/workflows/opsx-propose.md). Giao với U1/UP5 tiering: task tiny có cần đủ 4 artifact không.
- **Effort:** instrument CC ~30 phút; R-Spec-3 + spec-orchestrator human ~1-2 ngày / CC ~1 giờ.
- **Priority:** P2. **Depends on:** substrate telemetry (UP1/SP1c) để đo bypass TRƯỚC khi hạ friction. **Direction — đo trước, đừng build UX dựa trên phỏng đoán.**
