---
name: lightweight-change
version: '1.0'
description: 'Dùng khi apply một change class trivial/small: đọc micro-plan trong TASK.yaml,
  inspect đúng source anchor, implement trong scope khai báo, chạy focused verification
  và trả RESULT.yaml — không tạo SPEC/IMPLEMENTATION_PLAN/TASK_QUEUE; escalate khi risk
  signal xuất hiện.'
routing:
  mode: workflow
  actions:
  - apply
  states:
  - INTAKE
  - EXECUTING
  classes:
  - trivial
  - small
capabilities:
  required:
  - exact_source_inspection
  - runtime_verification
outputs:
  required:
  - RESULT.yaml
  optional:
  - EVIDENCE.yaml
gates:
- result-contract
---
# Lightweight Change

## Mục tiêu
Thực thi change trivial/small theo micro-plan trong `TASK.yaml` với chi phí tối thiểu:
đúng scope, focused verification, structured result — không full ceremony.

## Khi nào sử dụng
Dùng khi `CHANGE.yaml` class là `trivial` hoặc `small` và action là `apply`
(state `INTAKE` fast-path hoặc `EXECUTING`).

## Khi nào KHÔNG sử dụng
- Class `standard`/`architectural` → `executing-task` (theo router).
- KHÔNG tạo `SPEC.md`, `IMPLEMENTATION_PLAN.md`, `TASK_QUEUE.json`, `briefs/` —
  xuất hiện nhu cầu đó nghĩa là class sai, phải escalate.
- Không dùng để sửa knowledge, skill, rule hay framework artifact.

## Đầu vào
- `TASK.yaml` (micro-plan: objective, scope.files, verification.commands,
  escalation_triggers).
- `EVIDENCE.yaml` (small; tạo focused evidence nếu thiếu).

## Câu hỏi tri thức
- Source anchor trong scope có đúng như micro-plan mô tả không?
- Blast radius có đúng là ≤ scope khai báo không? Nghi ngờ → cần
  `dependency_analysis` (conditional) hoặc escalate.

## Loại evidence bắt buộc
- `file_symbol`, `exact_code_fact` (inspect anchor trước khi sửa).
- `command_result`/`test_result` (focused verification).

## Chính sách capability
Capability IDs: `exact_source_inspection`, `runtime_verification`.
Conditional: `dependency_analysis` khi blast radius không chắc chắn.

## Quy trình truy xuất
1. Đọc `TASK.yaml`; xác nhận risk classification còn đúng.
2. Inspect exact source anchor của từng file trong scope.
3. Small: ghi focused evidence vào `EVIDENCE.yaml` nếu chưa có.

## Thứ tự authority và precedence
current source > micro-plan. Source khác mô tả trong TASK.yaml → cập nhật evidence
hoặc escalate, không im lặng làm tiếp.

## Kết quả bắt buộc
- Change implemented trong đúng `scope.files` HOẶC escalation tường minh.
- `RESULT.yaml` (status, changes, runtime_metrics) — result contract pass.
- Focused static check/test đã chạy thật và ghi lại.

## Bất biến
- Không viết file ngoài `scope.files` (write gate enforce).
- Không nâng cấp lặng lẽ thành full workflow; escalate qua `escalation_triggers`.

## Yêu cầu evidence
Ghi command + expected + observed + exit code trong RESULT/verification declare.

## Freshness và confidence
Repository commit đổi so với lúc lập micro-plan → re-inspect anchor trước khi sửa.

## Quy trình degradation
Thiếu context material → block với lý do cụ thể (không assumption ngầm);
provider phụ trợ absent → ghi degradation, tiếp tục bằng current source.

## Quy trình
1. Đọc task objective + scope.
2. Inspect exact source anchor.
3. Validate risk classification (trivial/small còn đúng?).
4. Small: tạo focused evidence nếu thiếu.
5. Implement CHỈ trong allowed scope.
6. Chạy focused test/static check.
7. Ghi structured result vào `RESULT.yaml`.
8. Risk signal xuất hiện (public contract, persistence, security, blast radius lớn)
   → escalate class qua `escalation_triggers`, dừng lightweight path.

## Điều kiện dừng
- Escalation trigger khớp (đổi class → full workflow).
- Scope thực tế vượt `scope.files`.
- Verification fail lặp lại cùng lý do.

## Tác động lên knowledge
Không ghi durable knowledge; deviation/discovery ghi vào RESULT.yaml cho verification.

## Đầu ra
`RESULT.yaml` (+ `EVIDENCE.yaml` cập nhật với small).

## Handoff tiếp theo
`verification-before-completion` (router: apply → VERIFYING cho trivial/small).
