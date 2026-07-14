# core/flow.md — Flow, Spec/Apply & Bootstrap Rules

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
- Residual đã biết: write-idiom phổ biến bị chặn bởi write-gate hook; residual còn
  lại là write qua shell dựng động/`eval` (accepted theo threat model —
  chi tiết `core/write-boundary.md`).

### [CRITICAL] R-Flow-3: User workflow rules > agent system defaults

- Chỉ thị rõ ràng trong `{{ platform.framework_root }}/workflows/*.md` (đặc biệt
  `[CRITICAL]` block) thắng mọi default của agent runtime (planning mode, artifact
  convention — Claude/Cursor/Gemini/Antigravity...): task.md đòi workspace/plan/queue
  vNext → không planning mode ad hoc; task.md đòi confirm → không skip.
- Chuỗi precedence canonical: `agent/KERNEL.md` §2; runtime defaults luôn xếp cuối.

### [CRITICAL] R-Flow-4: Over-verification hardstop — assumption phân loại theo risk

- Khi agent gặp dữ liệu/cấu hình thiếu từ DB hoặc external system:
  - **Không được** quét lại DB/codebase quá **2 lần** để tìm cùng một thông tin.
  - Sau lần thứ 2 không tìm thấy → **hardstop**: ghi một assumption record ĐÚNG
    taxonomy tại `config/assumption-policy.yaml` (id, type, statement, evidence_gap,
    expiry_condition + field theo type) vào artifact của workspace — section
    "Giả định & Rủi ro" trong `INTENT.md` (standard/architectural) hoặc `TASK.yaml`
    (trivial/small) và trong Knowledge Trace của decision bị ảnh hưởng.
  - Hành vi theo `action` của type (KHÔNG còn generic "ghi assumption và tiếp tục"):
    - `continue` (non_material): tiếp tục flow; confidence bị cap `medium`.
    - `degrade` (operational_environment): ghi failed_probe + fallback +
      affected_claims rồi tiếp tục với degradation.
    - `block_spec` / `human_gate` / `block` (behavior_changing, public_contract,
      persistence_destructive, security, migration): gate `knowledge-trace` sẽ CHẶN
      cho tới khi record có `human_decision: approved`; chuyển workspace sang
      **BLOCKED** (reason `user_input`) và đề xuất action cụ thể (vd câu SQL backfill).
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

### [CRITICAL] R-Spec-1: Spec chỉ dựa trên intent + grounding

- Khi sinh spec, chỉ được dùng thông tin từ workspace hiện tại:
  - `changes/<id>/INTENT.md`, `changes/<id>/exploration/` (GROUNDING/EVIDENCE_MANIFEST),
    `changes/<id>/RECONCILIATION.md`, `{{ platform.framework_root }}/knowledge/long-term/knowledge-snapshot.md`, code/DB đã explore.

### [CRITICAL] R-Spec-2: Không tự động “fix” requirement

- Nếu requirement mâu thuẫn/thiếu:
  - Phải ghi rõ vào phần "Vấn đề yêu cầu" và hỏi user/BA trước khi chỉnh.

### [CRITICAL] R-Apply-1: Human in the loop

- `/task apply` luôn phải:
  - Tóm tắt file/module sẽ bị chạm.
  - Hỏi user confirm trước khi gọi `maika task apply --id <change-id>`.

---

## 11. Bootstrap Rules

- R-Boot-1/2: bootstrap + greeting — luật ở `agent/KERNEL.md` §8 và
  `procedures/bootstrap.md` (không lặp lại ở đây).
- **[CRITICAL] R-Boot-3**: conflict active change A vs user yêu cầu task B →
  PHẢI hỏi user trước khi archive/discard; không tự quyết.

---
