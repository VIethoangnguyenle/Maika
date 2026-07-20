# core/write-boundary.md — Write Boundary & Pre-invoke Guards (CORE)

> Core rule — luôn load. Teaching moment / external KI: `jit/teaching-moment.md`.

---

## 14. Guard Rules — Pre-invoke Guardrails

### [CRITICAL] R-Guard-1: Kiểm tra pre_conditions trước khi gọi skill

- Mỗi skill có thể khai báo block `pre_conditions:` trong frontmatter.
- Trước khi thực thi bất kỳ skill nào có `pre_conditions:`, agent **PHẢI**:
  1. Đọc từng condition trong list.
  2. Kiểm tra điều kiện (`not_empty`, `not_skeleton`, `exists`, `phase_done`).
  3. Nếu **tất cả** pass → thực thi skill bình thường.
  4. Nếu **bất kỳ** condition fail → thực hiện `on_fail` action và **ABORT** skill đó.
- `on_fail`: `ABORT — <hướng dẫn>` (dừng, báo user) hoặc `WARN — <hướng dẫn>`
  (tiếp tục, ghi cảnh báo vào artifact result/review của phase hiện tại).
- Không được bypass `pre_conditions` dù context có vẻ đủ — guard phải chạy deterministically.
- Precondition guards phải chạy trước skill để lỗi không lan sang downstream skills.

### [CRITICAL] R-Guard-2: vNext write gate

Trước khi tạo/sửa bất kỳ application-code artifact nào, agent PHẢI có đúng một
workspace vNext ở trạng thái `EXECUTING`:

- `{{ platform.framework_root }}/changes/<id>/STATE.yaml`
- `{{ platform.framework_root }}/changes/<id>/generated/PLAN_VALIDATION.json`
- `{{ platform.framework_root }}/changes/<id>/generated/PLAN_MANIFEST.json`
- `{{ platform.framework_root }}/changes/<id>/generated/TASK_QUEUE.json`

Write-gate chỉ cho phép file nằm trong `files.create`, `files.modify`,
`files.delete`, hoặc `files.test` của task `in_progress` hiện tại. Gate FAIL →
**ABORT**, không được viết code. Chi tiết: `procedures/decision-gate.md`. Explicit preference ngoài task chỉ ghi qua `maika remember` vào preference store, không tạo change hay sửa rule/skill/durable knowledge; lesson trong task vẫn candidate-first. Write-gate cũng quét secret high-precision trong nội dung ghi vào artifact-Maika (R-Guard-3, cơ học) → DENY + record đã mask; policy `profiles/secret-gate.yaml`.
