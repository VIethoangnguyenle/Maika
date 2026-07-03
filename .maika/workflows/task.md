---
description: Orchestrator /task (đa pha) cho ideation + ticket + OpenSpec.
---

# /task — Orchestrator chính

`/task` là cổng vào duy nhất cho mọi công việc liên quan đến task trong repo này.

Các chế độ sử dụng:

- `/task <ý-tưởng-hoặc-link>`      → Pha 1: ideation / requirement / explore.
- `/task spec <ticket-id-or-link>` → Pha 2: sinh spec (propose).
- `/task apply <ticket-id>`        → Pha 3: apply spec vào code.

Trước khi kết thúc mỗi pha quan trọng, hãy cập nhật `{{ platform.framework_root }}/knowledge/active/AGENT_TRANSPARENCY.md`.

> **Path convention**: Tất cả file context tuân theo quy ước trong `{{ platform.framework_root }}/rules/RULES.md` section "Path Convention".

---

## 0. Bootstrap context (bắt buộc)

Trước khi bắt đầu bất kỳ nhánh nào, luôn chạy bước bootstrap:

1. Kiểm tra `{{ platform.framework_root }}/knowledge/active/REQUIREMENT.md`:
   - Nếu file có nội dung thật (không chỉ là template trống) → hỏi user:
     > "Active context đang có dữ liệu từ task trước. Reset cho task mới hay giữ lại?"
   - Nếu user chọn reset hoặc file là template trống → giữ nguyên skeleton.
2. Tương tự cho `{{ platform.framework_root }}/knowledge/active/EXPLORE_CONTEXT.md`.
3. Reset `{{ platform.framework_root }}/knowledge/active/AGENT_TRANSPARENCY.md`:
   - Ghi mới với task/ticket ID hiện tại.
   - Đánh dấu `[x] {{ platform.config_entry_point }}` và `[x] {{ platform.framework_root }}/rules/RULES.md` nếu đã đọc.
   - Ghi vào "Lịch sử pha": `Bootstrap | <thời điểm> | Task: <input>`.
   - Bao gồm section `## Teaching Moment Check` ở trạng thái non-passing (status rỗng) như template `AGENT_TRANSPARENCY.tpl.md`. KHÔNG pre-fill `status: none`.

4. Tạo hoặc reset `{{ platform.framework_root }}/knowledge/active/TOKEN_LOG.md`:
   - Nếu chưa tồn tại: tạo từ template `{{ platform.framework_root }}/knowledge/templates/TOKEN_LOG.tpl.md`.
   - Điền: ticket-id (hoặc "unknown" nếu IDEA_ONLY), timestamp bắt đầu, model name (nếu biết).
   - Ghi bootstrap token estimate vào section "Bootstrap".

---

## 1. `/task <ý-tưởng-hoặc-link>` — Pha 1: Hiểu vấn đề

### 1.1 Nhận diện loại input

Từ giá trị `<ý-tưởng-hoặc-link>`, phân loại:

- Chuỗi chứa URL hoặc key của ticket (ví dụ: `ABC-123`) → `HAS_TICKET`.
- Chuỗi chứa URL tài liệu (wiki/Confluence/PRD/...) nhưng không có ticket → `HAS_DOC_ONLY`.
- Còn lại → `IDEA_ONLY`.

Sau khi nhận diện:

- Cập nhật `{{ platform.framework_root }}/knowledge/active/AGENT_TRANSPARENCY.md` mục "Nguồn đã đọc" với loại input tương ứng.
- Ghi lại raw input (ý tưởng, link) để trace.

---

### 1.2 Nhánh IDEA_ONLY — Ideation

1. Tạo file `ideation-*.md` trong `{{ platform.framework_root }}/knowledge/active/ideation/` theo template:
   - Ghi:
     - Tóm tắt ý tưởng.
     - Động lực (tại sao muốn làm).
     - Bối cảnh sơ bộ (hệ thống nào, đối tượng chính là ai).
2. Hỏi–đáp với user để:
   - Làm rõ mục tiêu business.
   - Gợi ý phạm vi (in-scope / out-of-scope).
   - Gợi ý các Acceptance Criteria ở mức high-level.
3. (Tuỳ chọn) Gọi `codebase-explorer`:
   - Để hiểu codebase hiện tại đang có module/service nào *có thể* liên quan.
   - Ghi lại vào `ideation-*.md` phần “Liên hệ với hệ thống hiện tại”.
4. Cập nhật lại `ideation-*.md` với:
   - Scope đề xuất.
   - AC đề xuất (chưa phải commit cuối cùng).
5. Cập nhật `{{ platform.framework_root }}/knowledge/active/AGENT_TRANSPARENCY.md`:
   - Đánh dấu đã tạo/ cập nhật file ideation.
6. Gợi ý user:
   - Tạo ticket chính thức (Jira/…).
   - Sau khi có ticket, dùng `/task <ticket-link-or-id>` để đi tiếp Pha 1 cho `HAS_TICKET`.

---

### 1.3 Nhánh HAS_DOC_ONLY — Có tài liệu, chưa có ticket

1. Gọi skill `spec-extract`:
   - Trích nội dung có cấu trúc từ tài liệu vào `{{ platform.framework_root }}/knowledge/active/REQUIREMENT.md`.
   - Ghi rõ nguồn tài liệu (URL, tên trang).
2. Kiểm tra Độ tin cậy do `spec-extract` gán:
   - Nếu **THẤP**:
     - Ghi cảnh báo vào `{{ platform.framework_root }}/knowledge/active/AGENT_TRANSPARENCY.md`.
     - Thông báo cho user rằng tài liệu chưa đủ tin cậy để đi tiếp (architecture/spec/implementation).
     - Dừng pipeline tại đây cho tới khi tài liệu được cập nhật.
   - Nếu **CAO/TRUNG BÌNH**:
     - Có thể dùng `/opsx:explore` để thảo luận thêm với user dựa trên REQUIREMENT vừa tạo.
3. Gợi ý user:
   - Tạo ticket từ `REQUIREMENT`.
   - Sau đó quay lại `/task <ticket-link-or-id>` để đi qua luồng `HAS_TICKET`.

---

### 1.4 Nhánh HAS_TICKET — Task cụ thể

1. Gọi `requirement-analyst`:
   - Đọc toàn bộ ticket + tài liệu liên kết.
   - Chuẩn hoá `{{ platform.framework_root }}/knowledge/active/REQUIREMENT.md` với context, As-is/To-be, scope, AC, giả định, vấn đề yêu cầu.
2. Nếu requirement chạm tới dữ liệu:
   - Gọi `db-explorer`:
     - Khám phá tầng database liên quan (schema, constraint, trigger/procedure…).
     - Cập nhật section "Tầng Database (db-explorer)" trong `{{ platform.framework_root }}/knowledge/active/EXPLORE_CONTEXT.md`.
3. Gọi `codebase-explorer`:
   - **UA-first** (xem `codebase-explorer` SKILL §Quy tắc cốt lõi): `{{ tools.domain_overview }}` →
     `{{ tools.domain_flow }}` để map domain/flow/entry-point/ranh giới async TRƯỚC.
   - Đọc `{{ platform.framework_root }}/knowledge/active/REQUIREMENT.md`, map yêu cầu → domain/module/service.
   - **Codebase Memory hỗ trợ SAU**: `{{ tools.search_code }}` định vị symbol, `{{ tools.read_file }}`
     extract logic trong hàm tại node UA đã chỉ. Lỗi Codebase MCP ≠ UA chết — vẫn dùng UA.
   - KG/UA vắng → gợi ý `/understand` rebuild; tạm grep với Độ tin cậy thấp hơn (không bịa).
   - Cập nhật section "Kiến trúc code hiện tại (codebase-explorer)" trong EXPLORE_CONTEXT.
   - **Ghi kèm identifier** (UA domain/flow/entry-point hoặc node_id) cho mỗi component quan trọng.
4. Gọi `architecture-reviewer`:
   - Đối chiếu `{{ platform.framework_root }}/knowledge/active/REQUIREMENT.md` + `{{ platform.framework_root }}/knowledge/active/EXPLORE_CONTEXT.md` + `{{ platform.framework_root }}/knowledge/long-term/knowledge-snapshot.md`.
   - Nếu EXPLORE_CONTEXT có node IDs → dùng KG tools (`{{ tools.find_blast_radius }}`, `{{ tools.read_file }}`, `{{ tools.get_dependencies }}`) để verify.
   - Đánh giá:
     - Điểm align với kiến trúc hiện tại.
     - Điểm xung đột/rủi ro (boundary, ownership, coupling, DB, non-functional…).
   - Ghi mức độ nghiêm trọng (LOW/MEDIUM/HIGH/BLOCKER) và Độ tin cậy kiến trúc (CAO/TRUNG BÌNH/THẤP).
4a. **[H1 — BLOCKER Recovery]** Nếu `architecture-reviewer` đánh dấu mức **BLOCKER**:
   - Cập nhật `phase_state: blocked-by-arch` trong AGENT_TRANSPARENCY.md.
   - Ghi rõ vào AGENT_TRANSPARENCY.md:
     ```
     [BLOCKER-ARCH] {mô tả blocker}
     Cần action: {gợi ý cụ thể — workshop kiến trúc / làm rõ requirement / bổ sung khám phá}
     Unblock khi: {điều kiện để tiếp tục — vd: "user xác nhận approach"}
     ```
   - **Dừng pipeline** — không tiếp tục sang Pha 2 khi còn BLOCKER chưa resolve.
   - Hiển thị cho user:
     - Tóm tắt blocker (1-3 câu).
     - Gợi ý action cụ thể để unblock.
     - Câu hỏi rõ ràng để user quyết định.
   - **Khi user đã resolve** (xác nhận approach hoặc điều chỉnh requirement):
     - Cập nhật `phase_state: phase-1-done` (xoá blocked state).
     - Ghi vào AGENT_TRANSPARENCY: `[BLOCKER-ARCH RESOLVED] {timestamp} — {cách resolve}`
     - Tiếp tục flow bình thường.

   Tương tự cho **BLOCKED-DATA** (từ R-Flow-4):
   - Cập nhật `phase_state: blocked-by-data`.
   - Ghi `[BLOCKED-DATA] {mô tả} — tiếp tục với assumption đã ghi.`
   - Tiếp tục flow dựa trên assumption (không chờ data — theo R-Flow-4).

5. Gọi `/opsx:explore` — **[H2] BẮT BUỘC** trong các trường hợp sau, tuỳ chọn còn lại:
   - **BẮT BUỘC khi**:
     - Độ tin cậy kiến trúc từ `architecture-reviewer` = **THẤP** hoặc **TRUNG BÌNH**, HOẶC
     - `task_type` = `changerequest` (thay đổi behaviour hiện tại, không phải feature mới).
   - **Tuỳ chọn khi**: Độ tin cậy = CAO và task_type = feature / fixbug / refactor.
   - Nội dung explore:
     - Tóm tắt lại hiểu biết hiện tại cho user:
       - `{{ platform.framework_root }}/knowledge/active/REQUIREMENT.md`.
       - Bối cảnh code + DB từ `{{ platform.framework_root }}/knowledge/active/EXPLORE_CONTEXT.md`.
       - Các rủi ro kiến trúc chính.
     - Cho phép user đặt câu hỏi, refine thêm trước khi sang Pha 2.
   - Ghi vào AGENT_TRANSPARENCY: `[H2] opsx-explore: {required|optional} — lý do: {confidence level hoặc task_type}`
6. Cập nhật `{{ platform.framework_root }}/knowledge/active/AGENT_TRANSPARENCY.md`:
   - Nguồn đã đọc (ticket, tài liệu, code/DB).
   - Skill/tool đã gọi thành công:
     - requirement-analyst, db-explorer, codebase-explorer, architecture-reviewer.
     - Knowledge Graph MCP (chi tiết):
       - `[ ] {{ tools.graph_stats }}`
       - `[ ] {{ tools.search_code }}`
       - `[ ] {{ tools.read_file }}`
       - `[ ] {{ tools.get_dependencies }} / {{ tools.trace_flow }}`
       - `[ ] {{ tools.get_symbol }}`
       - `[ ] {{ tools.find_blast_radius }} / find_entry_points`
     - UA domain tools (nếu có):
       - `[ ] {{ tools.domain_overview }}`
       - `[ ] {{ tools.domain_flow }}`
       - `[ ] {{ tools.domain_relationships }}`
     - Codebase Memory (nếu có).
   - Cảnh báo:
     - Thiếu KG graph / thiếu quyền DB / thiếu codebase-access.
   - Độ tin cậy tổng quan sau Pha 1.

7. Ghi token checkpoint vào `{{ platform.framework_root }}/knowledge/active/TOKEN_LOG.md`:
   - Điền timestamp kết thúc Pha 1.
   - Estimate token Pha 1: input (files đọc + tool calls) + output (REQUIREMENT + EXPLORE_CONTEXT + AGENT_TRANSPARENCY).
   - Liệt kê tool calls đáng chú ý ({{ tools.read_file }} nhiều lần, tài liệu dài...).
   - Cập nhật dòng "Pha 1" trong bảng Tóm tắt.
   - Nếu tổng Pha 1 > 50,000 tokens estimate: ghi cảnh báo vào section "Cảnh báo".
   - Tham chiếu protocol đầy đủ: `{{ platform.framework_root }}/procedures/token-tracking.md`.

8. **Đánh dấu Pha 1 hoàn thành** vào `{{ platform.framework_root }}/knowledge/active/AGENT_TRANSPARENCY.md`:
   - Thêm dòng vào section "Lịch sử pha": `Pha 1 DONE | <timestamp> | REQUIREMENT + EXPLORE_CONTEXT đã ghi`
   - Cập nhật `phase_state: phase-1-done` trong block `## Phase State`.
   - Ghi rõ ticket_id (hoặc "HAS_DOC_ONLY / IDEA_ONLY" nếu không có ticket).
   - **Mục đích**: Khi phiên bị truncate và resume, agent đọc được marker này để biết Pha 1 đã xong
     → **không được re-trigger Pha 1** dù active context có vẻ thiếu ticket ID.
   > **Resume rule**: Nếu `phase_state` = `phase-1-done` hoặc cao hơn → coi Pha 1 đã hoàn thành.
   > Không hỏi lại, không re-run exploration. Chuyển thẳng sang hướng dẫn user chạy `/task spec`.

9. **[POST-PHASE SELF-CHECK — Pha 1]** Trước khi báo "Pha 1 xong" với user:
   - `[ ]` REQUIREMENT.md không còn là skeleton (có nội dung thực).
   - `[ ]` EXPLORE_CONTEXT.md đã được ghi (db-explorer và/hoặc codebase-explorer đã chạy).
   - `[ ]` AGENT_TRANSPARENCY.md có `phase_state: phase-1-done`.
   - `[ ]` TOKEN_LOG.md đã ghi checkpoint Pha 1.
   - `[ ]` architecture-reviewer đã chạy và ghi độ tin cậy.
   Nếu bất kỳ ô nào chưa tick: hoàn thành trước khi tiếp tục.

10. **[SESSION-BOUNDARY — Pha 1]** Sau khi POST-PHASE SELF-CHECK pass:
    - Thông báo user:
      > "Pha 1 hoàn thành. **Vui lòng mở session mới** để chạy `/task spec`.
      > Context đã lưu đầy đủ vào `{{ platform.framework_root }}/knowledge/active/`.
      > Session mới sẽ Bootstrap fresh — rule/DNA ở top-of-mind, tránh Context Dilution."
    - Nếu user tiếp tục trong cùng session (gọi `/task spec` ngay):
      - Ghi WARN vào AGENT_TRANSPARENCY: `[SESSION-BOUNDARY] Tiếp tục cùng session sau Pha 1 — rủi ro Context Dilution.`
      - **Không block** — vẫn cho phép tiếp tục, nhưng ghi vào Violation Log.


---

## 2. `/task spec <ticket-id-or-link>` — Pha 2: Sinh spec (propose)

Mục tiêu: dùng OpenSpec để sinh **spec kỹ thuật** dựa trên REQUIREMENT + bối cảnh hệ thống đã hiểu ở Pha 1.

> **[CRITICAL / BẮT BUỘC]**: 
> - **KHÔNG ĐƯỢC** dùng thói quen mặc định của Agent (như tự ý sinh file `implementation_plan.md` hay `plan.md` ở ngoài thư mục repo).
> - **BẮT BUỘC** phải gọi quy trình OpenSpec (`/opsx-propose` hoặc sử dụng skill `openspec-propose`) để sinh bộ artifact chuẩn (`proposal.md`, `design.md`, `spec.md`, `tasks.md`) lưu vào `openspec/changes/<change-id>/`.

1. Định vị context theo ticket:
   - Đọc `{{ platform.framework_root }}/knowledge/active/REQUIREMENT.md` tương ứng ticket.
   - Đọc `{{ platform.framework_root }}/knowledge/active/EXPLORE_CONTEXT.md` (tầng DB + code liên quan).
2. Tóm tắt nhanh cho user:
   - Bối cảnh business.
   - Kiến trúc hiện tại chạm tới yêu cầu.
   - Rủi ro chính (nếu có) từ architecture-reviewer.
3. Cập nhật `{{ platform.framework_root }}/knowledge/active/AGENT_TRANSPARENCY.md`:
   - Đánh dấu đã vào Pha 2 (`/task spec`).
   - Ghi nguồn đã đọc.
4. Hỏi user confirm — **bắt buộc, không được skip**:
   - Hỏi rõ: “Dùng bộ REQUIREMENT + context hiện tại để sinh spec nhé?”
   - Nếu user yêu cầu điều chỉnh nhỏ (scope, AC, approach…), cập nhật trước khi tiếp tục.
   > **[HARDBLOCK]**: Không được suy luận “user đã đồng ý” từ message trước đó, dù message có vẻ
   > rõ ràng (ví dụ: _“triển khai spec để coding”_ không có nghĩa đã confirm OpenSpec flow).
   > Đây là checkpoint kiểm soát duy nhất trước khi thực thi — nếu bỏ qua, mọi lỗi sau đều
   > không phát hiện được sớm.
5. Khi user xác nhận rõ ràng:
   - Cập nhật `phase_state: phase-2-in-progress` trong AGENT_TRANSPARENCY.md.
   - Gọi OpenSpec:
     - Thường là `/opsx:propose` (hoặc `/opsx:new` tuỳ convention).
   - **Không được** dùng planning mode mặc định của agent (sinh `implementation_plan.md`, `plan.md`,
     hoặc bất kỳ file nào ra ngoài `openspec/changes/<change-id>/`) — kể cả khi agent
     runtime có planning mode nằm ngoài workflow này (vd Cursor, Antigravity, v.v.).
   - Chờ spec được sinh ra (file spec riêng, ví dụ trong thư mục `spec/`).
   - **Integration coverage**: nếu REQUIREMENT có section "Integrations & Field Mapping" với
     integration mới → `tasks.md` sinh ra PHẢI có task mapper/adapter tương ứng cho từng
     integration (DTO + mapping thuộc contract node trong CONTRACT_DAG ở Pha 3).
   - Xác nhận output path là `openspec/changes/<change-id>/` trước khi báo cáo hoàn thành.
   - **[H5 — State Invalidation]** Sau khi `/opsx:propose` thành công:
     - Ghi `OPENSPEC_STATE: propose_done` vào AGENT_TRANSPARENCY.md (section Cảnh báo / Hạn chế).
     - Cập nhật `phase_state: phase-2-done`.
     - Ý nghĩa: bất kỳ thay đổi requirement nào SAU điểm này đều làm OpenSpec spec hiện tại
       **stale** — phải chạy lại `/opsx:propose` nếu REQUIREMENT bị sửa.
6. Thông báo:
   - Đường dẫn hoặc tên file spec.
   - Nhắc user review, cho feedback (có thể lặp lại `/opsx:propose` nếu cần refine).
7. Cập nhật `{{ platform.framework_root }}/knowledge/active/AGENT_TRANSPARENCY.md`:
   - Ghi rõ:
     - Đã sinh spec cho ticket nào.
     - File spec tương ứng.
     - Độ tin cậy (dựa trên chất lượng REQUIREMENT + context).

8. Ghi token checkpoint vào `{{ platform.framework_root }}/knowledge/active/TOKEN_LOG.md`:
   - Điền timestamp kết thúc Pha 2.
   - Estimate token Pha 2: input (REQUIREMENT + EXPLORE_CONTEXT + OpenSpec instructions) + output (spec file).
   - Cập nhật dòng "Pha 2" trong bảng Tóm tắt.
   - Tham chiếu protocol đầy đủ: `{{ platform.framework_root }}/procedures/token-tracking.md`.

9. **[POST-PHASE SELF-CHECK — Pha 2]** Trước khi báo "Pha 2 xong" với user:
   - `[ ]` spec file tồn tại trong `openspec/changes/<change-id>/`.
   - `[ ]` AGENT_TRANSPARENCY.md có `phase_state: phase-2-done`.
   - `[ ]` `OPENSPEC_STATE: propose_done` đã ghi vào AGENT_TRANSPARENCY.md.
   - `[ ]` TOKEN_LOG.md đã ghi checkpoint Pha 2.
   Nếu bất kỳ ô nào chưa tick: hoàn thành trước khi tiếp tục.

10. **[SESSION-BOUNDARY — Pha 2]** Sau khi POST-PHASE SELF-CHECK pass:
    - Thông báo user:
      > "Pha 2 hoàn thành. **Vui lòng mở session mới** để chạy `/task apply`.
      > Spec đã lưu tại `openspec/changes/<change-id>/`.
      > Session mới sẽ Bootstrap fresh — DNA/conventions ở top-of-mind khi code."
    - Nếu user tiếp tục trong cùng session:
      - Ghi WARN vào AGENT_TRANSPARENCY: `[SESSION-BOUNDARY] Tiếp tục cùng session sau Pha 2 — rủi ro Context Dilution khi code.`
      - **Chỉ được code khi implementation preflight pass** — micro-loop Pha 3 (SP1b)
        phải ghi `TASK_HANDOFF.<node>.md` chứa `## Applicable DNA/Conventions`,
        `## Evidence`, và `## Allowed Files`; `write-gate` sẽ block code write nếu
        handoff/context thiếu, stale, hoặc không match target file.

---

## 3. `/task apply <ticket-id>` — Pha 3: Apply spec vào code

Mục tiêu: dùng OpenSpec để áp dụng spec đã được chấp thuận vào codebase một cách có kiểm soát.

1. Định vị spec & context:
   - Tìm spec tương ứng ticket (tên file hoặc metadata trong spec).
   - Đọc spec để nắm:
     - File/module sẽ bị chạm.
     - Thay đổi chính (API, logic, DB migration… nếu có).
2. Tóm tắt cho user:
   - “Spec này dự kiến sẽ chạm vào: …”
   - “Các loại thay đổi chính: …”

2a. **[DNA-RELOAD — NGHỈ HƯU ở SP1b]** Nghi thức re-read DNA cho cả pha trước khi code đã được
    thay bằng **cấu trúc**: micro-loop (bước 5) lắp `dna_slice` (HP liên quan + `complexity_thresholds`
    + style liên quan) vào `TASK_HANDOFF` của **từng task**, nên DNA luôn ở recency window của executor
    khi sinh code — đúng task, đúng lúc, không phụ thuộc agent tự nhớ reload.
    > "Sandwich defense" vẫn còn nhưng đổi dạng: rule ở đầu (bootstrap) + rule trong handoff mỗi task (cấu trúc).
    > R-Guard-2 (gate per-artifact) vẫn áp dụng cho executor; rule cơ học giờ do mechanical gate SP1a chặn deterministic.

3. **[M1 — Spec Validation]** Chạy `spec-validator` trước khi apply:
   - Gọi `spec-validator.pre_apply_gate(spec_path, requirement_path)`:
     - Nếu **BLOCK**: dừng apply, hiển thị issues, hỏi user fix spec rồi chạy lại `/task spec`.
     - Nếu **PASS**: tiếp tục.
   - Gọi `spec-validator.check_ac_coverage(spec_path, requirement_path)`:
     - Nếu có AC chưa cover: hiển thị danh sách, hỏi user có muốn tiếp không.
   - Gọi `spec-validator.check_integration_coverage(spec_path, requirement_path)`:
     - Nếu có integration chưa có task mapper/adapter: hiển thị danh sách, hỏi user có muốn tiếp không.

4. Hỏi **xác nhận cuối cùng**:
   - Nêu rõ đây là bước sẽ đề nghị thay đổi code theo spec.
   - Nếu user muốn, có thể giới hạn phạm vi (chỉ generate patch, không apply; hoặc chỉ apply một phần).
5. Khi user đồng ý — **Orchestrate Hybrid Contract DAG micro-loop (SP1d)**:
   - **Dashboard runtime contract bắt buộc (P5):**
     - Log cả vòng đời của agent cha vào `{{ platform.framework_root }}/knowledge/active/microloop/ACTIVITY_LOG.jsonl`,
       không chỉ subagent. Dùng `actor: parent` cho các event như `phase_changed`,
       `parent_note`, `spec_started`, `spec_done`, `apply_started`, `archive_started`, `archive_done`.
     - Mirror context trực quan của agent cha từ IDE brain/cuộc trò chuyện với human vào
       `{{ platform.framework_root }}/knowledge/active/PARENT_BRAIN.md` khi bắt đầu apply và khi có quyết định mới.
       Nếu dùng helper Python, gọi `write_parent_brain(...)`; event tương ứng là `parent_brain_updated`.
     - Trước khi dispatch executor/subagent đầu tiên, tạo `{{ platform.framework_root }}/knowledge/active/microloop/TASK_QUEUE.md`
       từ danh sách node/task sẽ chạy, với `status: pending`, `handoff_path`, `result_path`, và `depends_on`.
     - Append `task_queue_created` vào `{{ platform.framework_root }}/knowledge/active/microloop/ACTIVITY_LOG.jsonl`.
     - Khi ghi `TASK_HANDOFF.<node-id>.md`, append `subagent_spawned` với `task_id`, label, và path.
     - Ngay trước khi giao việc cho executor/subagent, update task trong `TASK_QUEUE.md` thành `in_progress`
       và append `subagent_started`.
     - Khi executor/subagent hoàn tất, ghi `microloop/TASK_RESULT.<node-id>.md`, update task thành `done`,
       append `result_written` và `subagent_done`.
     - Nếu executor/subagent không thể hoàn tất, update task thành `blocked`, ghi lý do vào
       `TASK_RESULT.<node-id>.md`, append `subagent_blocked`, rồi dừng để user quyết định.
     - Có thể dùng helpers trong `{{ platform.framework_root }}/tools/microloop-orchestrator/orchestrator.py`:
       `initialize_runtime_queue`, `write_task_handoff`, `update_task_status`, `write_task_result`,
       `append_activity_event`, `record_parent_event`, `write_parent_brain`.
   a. Build `KNOWLEDGE_PACK.md` from REQUIREMENT, EXPLORE_CONTEXT, knowledge-snapshot,
      conventions, author-dna, OpenSpec artifacts, UA/KG evidence, db-explorer evidence, and relevant archive/memory.
      - Section "Integrations & Field Mapping" của REQUIREMENT là nguồn BẮT BUỘC của
        Knowledge Pack khi task có integration mới.
      - If task complexity = `complex` and KG graph is unavailable/stale: BLOCK unless user explicitly overrides.
      - If task touches DB and db-explorer evidence is missing: BLOCK and request db-explorer.
      - Record confidence and overrides in AGENT_TRANSPARENCY.
   b. Build `CONTRACT_DAG.md` from OpenSpec `tasks.md`:
      - `contract` nodes: base/interface/abstract class/DTO/schema/public contract.
      - `leaf` nodes: child classes/adapters/mappers/repository implementations.
      - `integration` nodes: DI/wiring/registry/config/migration registration.
      - `test` nodes: unit/integration/spec tests.
      - `review` nodes: extraction/verification.
   c. Run Contract Lane sequentially:
      - Assemble `TASK_HANDOFF.<node-id>.md` with Knowledge Pack slice, DNA slice, convention slice,
        architecture boundary, allowed/read-only files, and feedback if retrying.
      - Node mapper/adapter: nhúng NGUYÊN bảng field mapping của integration tương ứng vào
        `## Evidence` / `## Constraints` của handoff — executor không tự tra lại tài liệu;
        cú pháp serialize cụ thể resolve từ dna_slice/convention_slice.
      - After writing each handoff, record `subagent_spawned` in `ACTIVITY_LOG.jsonl`.
      - Dispatch executor by `{{ platform.framework_root }}/profiles/execution-mode.yaml`.
      - Before dispatch, mark that node `in_progress`; after result, mark it `done` or `blocked`.
      - Run mechanical gate + semantic surface-check.
      - On PASS, generate/freeze `CONTRACT_SNAPSHOT.<node-id>.md` with contract_version.
      - On FAIL after max retries, mark node `blocked` and stop for user decision.
   d. Run Implementation Lane in safe parallel batches:
      - Only nodes with dependencies done and no write conflicts can share a batch.
      - Leaf nodes receive `contract_snapshot` and `contract_version`.
      - Leaf nodes cannot edit frozen contract/base files or shared wiring files.
      - Missing context produces `CONTEXT_REQUEST.<node-id>.md`; orchestrator enriches Knowledge Pack and resumes.
      - Missing contract hook produces `CONTRACT_CHANGE_REQUEST.<node-id>.md`; if accepted, rerun Contract Lane,
        increment contract_version, and mark downstream nodes stale.
      - Wiring needs produce `INTEGRATION_REQUEST.<node-id>.md`.
   e. Run Integration Lane:
      - Integration Agent is the only executor allowed to edit shared registry/config/wiring files.
      - It consumes all `INTEGRATION_REQUEST.*.md` files and applies deterministic, grouped changes.
   f. Run Verification Lane:
      - Ensure no nodes remain `pending`, `in_progress`, `blocked`, or `stale`.
      - Run compile/typecheck/tests when available.
      - Run spec-validator post checks, including contract_version and allowed-file checks.
      - Run extraction review against all changed files and present `EXTRACTION_REPORT.md` to user.
   g. Persist state in `{{ platform.framework_root }}/knowledge/active/microloop/` so Pha 3 can resume after session truncation.
6. Sau khi micro-loop xong:
   - Chạy `spec-validator.post_apply_verify(spec_path, changed_files)` — ghi kết quả vào AGENT_TRANSPARENCY.
   - Nếu có diff/PR, thông báo lại link hoặc danh sách file thay đổi.
   - Đề nghị bước tiếp theo:
     - Review code.
     - Update test.
     - Triển khai / release, v.v. (ở mức gợi ý, không ép).
7. Cập nhật `{{ platform.framework_root }}/knowledge/active/AGENT_TRANSPARENCY.md`:
   - Đánh dấu:
     - Đã chạy `/task apply`.
     - Code đã được chỉnh theo spec (ở mức đề xuất/patch/PR).
   - Ghi:
     - Spec nào đã apply.
     - Bất kỳ hạn chế nào (ví dụ: apply một phần, lỗi khi apply, cần manual follow-up).

7. Ghi token checkpoint CUỐI TASK vào `{{ platform.framework_root }}/knowledge/active/TOKEN_LOG.md`:
   - Điền timestamp kết thúc Pha 3.
   - Estimate token Pha 3: input (spec + codebase context) + output (code changes).
   - Cập nhật dòng "Pha 3" và dòng **TỔNG TASK** trong bảng Tóm tắt.
   - Đây là lần ghi cuối trước khi `knowledge-curator` archive TOKEN_LOG.md.
   - Tham chiếu protocol đầy đủ: `{{ platform.framework_root }}/procedures/token-tracking.md`.

8. **[POST-PHASE SELF-CHECK — Pha 3]** Trước khi gọi knowledge-curator archive:
   - `[ ]` Micro-loop hoàn tất: mọi task trong `TASK_QUEUE` = `done` (không còn `pending`/`blocked`).
   - `[ ]` Extraction review đã chạy, `EXTRACTION_REPORT` đã trình user.
   - `[ ]` Code changes / diff / PR đã được tóm tắt cho user.
   - `[ ]` AGENT_TRANSPARENCY.md có `phase_state: applying` → đã cập nhật thành `completed`.
   - `[ ]` TOKEN_LOG.md đã ghi TỔNG TASK.
   - `[ ]` Không có BLOCKER chưa resolve trong AGENT_TRANSPARENCY.md.
   - `[ ]` spec-validator.post_apply_dna_check đã chạy (xem spec-validator §3.4).
   - `[ ]` KNOWLEDGE_PACK.md exists and confidence/override status is recorded.
   - `[ ]` CONTRACT_DAG.md has no `pending` / `in_progress` / `blocked` / `stale` nodes.
   - `[ ]` Every leaf node with `contract_ref` uses the current `contract_version`.
   - `[ ]` All `CONTEXT_REQUEST`, `CONTRACT_CHANGE_REQUEST`, and `INTEGRATION_REQUEST` files are resolved or explicitly documented.
   - `[ ]` Teaching Moment Check trong AGENT_TRANSPARENCY.md đã resolved — chạy `python3 {{ platform.framework_root }}/tools/gate-check/cli.py teaching-moment {{ platform.framework_root }}/knowledge/active/AGENT_TRANSPARENCY.md` và pass (exit 0) trước khi gọi knowledge-curator.
   Nếu bất kỳ ô nào chưa tick: hoàn thành trước khi gọi knowledge-curator.

9. **[SESSION-BOUNDARY — Pha 3]** Sau khi archive hoàn thành:
    - Thông báo user:
      > "Task hoàn thành và đã archive. **Vui lòng mở session mới** cho task tiếp theo.
      > Session mới sẽ Bootstrap fresh với knowledge-snapshot đã cập nhật."
    - Đây là kết thúc tự nhiên của task — session mới là best practice, không chỉ là gợi ý.

---

## 4. Lưu ý chung cho `/task`

- `/task` chỉ là **orchestrator**:
  - Không thay thế logic chi tiết của từng skill (requirement-analyst, db-explorer, codebase-explorer, architecture-reviewer, spec-extract, OpenSpec).
  - Chỉ quyết định **thứ tự gọi** và **điều kiện dừng/tiếp tục** giữa các pha.
- Ngôn ngữ và xử lý luôn generic:
  - Không encode domain nghiệp vụ cụ thể vào workflow.
  - Chỉ nói về ticket, tài liệu, DB, codebase, spec, kiến trúc.
- Luôn trung thực về trạng thái:
  - Nếu thiếu UA, thiếu DB access, thiếu code access → phải được phản ánh rõ trong `{{ platform.framework_root }}/knowledge/active/AGENT_TRANSPARENCY.md` và trong Độ tin cậy của mọi kết luận.

---

## 5. Tích hợp Knowledge Curator (v2.0)

Sau khi `/task apply` Pha 3 hoàn thành thành công:

```
1. Gọi knowledge-curator.archive_active_context(ticket_id):
   - Lưu toàn bộ active/ vào {{ platform.framework_root }}/knowledge/archive/{ticket_id}/

2. Gọi knowledge-curator.update_knowledge_snapshot(discoveries):
   - Trích discoveries từ EXPLORE_CONTEXT.md:
     - Các table/column mới phát hiện
     - Modules/services đã map
     - Business rules đã xác nhận
   - Cập nhật {{ platform.framework_root }}/knowledge/long-term/knowledge-snapshot.md

3. Gọi knowledge-curator.reset_active_context():
   - Reset active/ về skeleton sạch

4. Cập nhật {{ platform.framework_root }}/knowledge/active/AGENT_TRANSPARENCY.md (mới, sau reset):
   - Ghi: "Task {ticket_id} completed and archived at {timestamp}"
   - Mark: [x] knowledge-curator: archive + update_snapshot + reset

5. Thông báo user:
   "Task {ticket_id} đã hoàn thành. Context đã được archive.
    Knowledge snapshot đã cập nhật với {n} phát hiện mới.
    Sẵn sàng nhận task mới!"
```

---

## 6. Path Convention

> Path canonical cho tất cả file context được định nghĩa tại một nơi duy nhất:
> **`{{ platform.framework_root }}/rules/RULES.md` — Section 12, R-Path-1**
>
> Không duplicate bảng path ở đây. Khi cần tra cứu path, đọc RULES.md.
