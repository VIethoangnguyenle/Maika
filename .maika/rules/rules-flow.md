# rules-flow.md — Flow, Spec/Apply & Bootstrap Rules

> Sub-file của RULES.md. Đọc qua manifest `RULES.md`.

---

## 2. Flow Rules — Luồng bắt buộc

### [CRITICAL] R-Flow-1: Không bỏ qua `/task`

- Mọi công việc **liên quan đến task thực tế** (ticket, spec, apply code) phải đi qua workflow `maika task`.
- Cấm:
  - Gọi worker/apply trực tiếp khi chưa có workspace vNext, plan đã validate, và review cần thiết.

### [CRITICAL] R-Flow-2: Phase gate (entry + completion)

- **Route theo class, không có chuỗi state cố định chung:** thứ tự action cho change
  hiện tại resolve từ `config/workflow-router.yaml` theo (class, current state).
  Trivial/small KHÔNG có spec/plan — micro-plan nằm trong `TASK.yaml`.
  Dry-run một quyết định route: `maika task route --id <id> --action <action>`.
- **Apply-entry (standard/architectural):** `maika task apply` yêu cầu `PLAN_VALIDATION.json` approved,
  `reviews/plan-review.md` approved, immutable briefs, và `TASK_QUEUE.json` khớp
  `PLAN_MANIFEST.json`.
- **Completion:** KHÔNG phát "Done" cho tới khi structured result, task review,
  final review, và verification artifacts pass theo state hiện tại.
- Residual đã biết: raw Edit/Write và các shell write-idiom phổ biến (redirect, tee, sed -i, cp/mv, dd, patch, formatter) đã bị chặn bởi runtime write-gate hook; residual còn lại là write qua shell dựng động/`eval`/sub-script (accepted theo threat model).

### [CRITICAL] R-Flow-3: User workflow rules > agent system defaults

- Khi workflow trong repo (`{{ platform.framework_root }}/workflows/*.md`) có chỉ thị rõ ràng (đặc biệt là `[CRITICAL]` block),
  **ưu tiên tuyệt đối hơn** mọi hành vi mặc định của agent runtime (planning mode, artifact generation,
  file output convention của agent runtime, vd Claude, Cursor, Gemini, Antigravity, v.v.).
- Cụ thể:
  - Khi `task.md` yêu cầu workspace/plan/queue vNext → **không được** dùng planning mode ad hoc.
  - Khi `task.md` yêu cầu confirm trước → **không được** skip dù context có vẻ đã đồng ý.
  - Agent runtime defaults (kể cả planning mode của các tool như Cursor, Antigravity, v.v.) là **secondary** — chỉ dùng
    khi workflow không có chỉ thị gì về hành động đó.
- Thứ tự ưu tiên: xem chuỗi canonical tại `agent/KERNEL.md` §2 (Canonical Authority); agent runtime defaults luôn xếp cuối.


### [CRITICAL] R-Flow-4: Over-verification hardstop — ghi Assumption, không loop

- Khi agent gặp dữ liệu/cấu hình thiếu từ DB hoặc external system (ví dụ: Provider Code không tồn tại,
  bảng trống, config chưa seed):
  - **Không được** quét lại DB/codebase quá **2 lần** để tìm cùng một thông tin.
  - Sau lần thứ 2 không tìm thấy → **hardstop**:
    1. Ghi nhận vào REQUIREMENT.md section "Giả định & Rủi ro":
       `[ASSUMPTION] <tên data> chưa tồn tại trong DB. Cần backfill/seed trước khi apply.`
    2. Ghi vào AGENT_TRANSPARENCY: `[BLOCKED-DATA] <mô tả> — tiếp tục với assumption đã ghi.`
    3. **Tiếp tục flow** dựa trên assumption, không chờ data được sửa.
  - Nếu lỗi cấu hình cần user/DBA xử lý: đề xuất rõ action (ví dụ: câu SQL backfill) và
    chuyển trạng thái task sang **PENDING-BACKFILL** trong AGENT_TRANSPARENCY.
- Sau hardstop, không tiếp tục scan cùng một dữ liệu/cấu hình trong phiên hiện tại.

### [CRITICAL] R-Flow-5: Orchestrator mỏng — việc nặng chạy trong worker

- Context của agent cha (orchestrator) CHỈ giữ: phase state, tóm tắt ngắn, đường dẫn file.
- Nội dung thô khối lượng lớn — trang tài liệu (Confluence/wiki/PRD), quét code diện rộng,
  log dài — phải được tiêu thụ trong worker context (subagent / worker_command theo
  `{{ platform.framework_root }}/profiles/execution-mode.yaml`) và persist kết quả ra file knowledge.
- Parent chỉ đọc lại file kết quả trong workspace (`results/*.yaml`, `reviews/*.md`), không đọc nguồn thô.
- Execution chạy qua `maika task apply --id <id>` và `generated/TASK_QUEUE.json`;
  parent không vận hành loop thủ công.
- Lý do: context tràn/compact làm mất rules/DNA đã đọc lúc bootstrap → agent code cảm tính
  (observed failure 2026-07-03, downstream Antigravity).

### [CRITICAL] R-Flow-6: Freeform "viết spec/code" phải route về /task

- Sau khi Pha 1/2 đã chạy, mọi yêu cầu freeform kiểu "viết spec đi", "code đi", "implement đi"
  PHẢI được route về `/task spec` / `/task apply` (nơi dispatch worker theo execution-mode).
- KHÔNG code inline từ trí nhớ hội thoại — write-gate SESSION-GATE chặn code write inline
  trong session đã hoàn thành Pha 1/2 (override tường minh: `SESSION_OVERRIDE.md`, có log violation).


---

## 6. Spec & Apply Rules

### [CRITICAL] R-Spec-1: Spec chỉ dựa trên REQUIREMENT + context

- Khi sinh spec, chỉ được dùng thông tin từ:
  - `{{ platform.framework_root }}/knowledge/active/REQUIREMENT.md`, `{{ platform.framework_root }}/knowledge/active/EXPLORE_CONTEXT.md`, `{{ platform.framework_root }}/knowledge/long-term/knowledge-snapshot.md`, code/DB đã explore.

### [CRITICAL] R-Spec-2: Không tự động “fix” requirement

- Nếu requirement mâu thuẫn/thiếu:
  - Phải ghi rõ vào phần "Vấn đề yêu cầu" và hỏi user/BA trước khi chỉnh.

### [CRITICAL] R-Apply-1: Human in the loop

- `/task apply` luôn phải:
  - Tóm tắt file/module sẽ bị chạm.
  - Hỏi user confirm trước khi gọi `maika task apply --id <change-id>`.

---

## 11. Bootstrap Rules

### [CRITICAL] R-Boot-1: Bootstrap bắt buộc mỗi phiên

- Agent PHẢI chạy toàn bộ script `bootstrap.md` mỗi khi bắt đầu phiên mới.
- Không được bỏ qua bất kỳ PHASE nào trong bootstrap (trừ khi file không tồn tại → graceful degrade).

### [REFERENCE] R-Boot-2: Xác nhận load bằng trigger phrase

- Câu đầu tiên trong phiên chứa greeting từ `persona.yaml` (field `greeting`, fallback `"Ready"`) —
  cơ chế định nghĩa tại `procedures/bootstrap.md` PHASE 5.
- Thiếu greeting → dấu hiệu chưa bootstrap đúng → chạy lại bootstrap.

### [CRITICAL] R-Boot-3: Context conflict resolution

- Khi phát hiện conflict (active context của task A, nhưng user yêu cầu task B):
  - PHẢI hỏi user trước khi archive hoặc discard context cũ.
  - Không tự ý quyết định.

---
