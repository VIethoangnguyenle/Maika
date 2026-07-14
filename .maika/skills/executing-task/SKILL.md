---
name: executing-task
version: '3.0'
description: 'Dùng khi một task PENDING trong TASK_QUEUE.json sẵn sàng chạy: đọc brief
  + knowledge capsule, verify freshness, re-read source anchor, chỉ implement scope
  đã khai, và request re-grounding khi source khác evidence.'
routing:
  mode: workflow
  actions:
  - apply
  states:
  - EXECUTING
  classes:
  - standard
  - architectural
capabilities:
  required:
  - exact_source_inspection
  - runtime_verification
  - version_control
outputs:
  required:
  - results/
gates:
- result-contract
---
# Executing Task

## Mục tiêu
Implement đúng một task brief bất biến trong context cô lập, tiêu thụ Task Knowledge
Capsule, và trả `results/TASK-NNN.yaml` theo result contract — không tự suy diễn strategy.

## Khi nào sử dụng
Dùng cho task `PENDING` trong `TASK_QUEUE.json` sau khi plan approved và brief-integrity pass.

## Khi nào KHÔNG sử dụng
- Chưa có brief/capsule hợp lệ.
- Để sửa plan/queue/state/knowledge (không được phép).

## Đầu vào
- `briefs/TASK-NNN.md` + `briefs/TASK-NNN.knowledge.yaml` (capsule).
- Allowed files từ brief header; output của dependency.

## Câu hỏi tri thức
- Source anchor thật sự khớp evidence trong capsule không?
- Forbidden pattern nào capsule cấm? Assumption nào còn hiệu lực?

## Loại evidence bắt buộc
- `file_symbol`, `exact_code_fact` (re-read anchor).
- `command_result`, `test_result` (focused verification).

## Chính sách capability
Capability IDs: `exact_source_inspection`, `runtime_verification`, `version_control`.
Chỉ dùng capsule đã biên dịch; không recall thêm ngoài scope task.

## Quy trình truy xuất
1. Đọc `TASK-NNN.md` + `TASK-NNN.knowledge.yaml`.
2. Re-read exact source anchor được capsule trỏ tới.
3. So khớp source ↔ evidence trong capsule.

## Thứ tự authority và precedence
current source > capsule evidence. Nếu source khác evidence → không tự "sửa cho khớp",
mà escalate.

## Kết quả bắt buộc
- Một task implemented hoặc blocked.
- `results/TASK-NNN.yaml` theo result contract; focused test chạy + ghi lại.
- Commit SHA ghi khi có code change.
- Nếu source ≠ evidence: trả một trong `NEEDS_REGROUNDING`, `EVIDENCE_CONFLICT`, `STALE_KNOWLEDGE`.

## Bất biến
- Không sửa file ngoài allowed scope.
- Không đổi plan/queue/state/knowledge capsule.
- Không complete chỉ bằng exit code.

## Yêu cầu evidence
Ghi command, expected, observed, exit code, changed/deleted files, changed symbols,
deviations, concerns, commit SHA.

## Freshness và confidence
Verify capsule hash + freshness (repository_commit, evidence_manifest_hash) trước khi
làm. Lệch → `STALE_KNOWLEDGE`.

## Quy trình degradation
Thiếu context/anchor undeclared → phát `results/TASK-NNN.EVIDENCE_UPDATE_REQUEST.yaml`
qua orchestrator, không tự đoán.

## Quy trình
1. Đọc brief + capsule; verify freshness.
2. Re-read anchor; so khớp source ↔ evidence.
3. TDD khi brief đổi behavior; chỉ implement declared work.
4. Chạy focused verification; ghi structured result.

## Điều kiện dừng
- Brief hash mismatch; plan stale.
- File bắt buộc chưa khai.
- Verification fail lặp lại cùng lý do.

## Tác động lên knowledge
Không ghi durable knowledge; chỉ ghi discovery/deviation vào result cho reviewer/curator.

## Đầu ra
`results/TASK-NNN.yaml` (+ `EVIDENCE_UPDATE_REQUEST.yaml` khi cần re-grounding).

## Handoff tiếp theo
`reviewing-task`.
