---
name: verification-before-completion
version: '2.0'
description: >
  Dùng khi sắp tuyên bố hoàn thành task/wave/change hoặc trước archive: chạy lệnh thật
  (build/test/static/contract/migration/smoke/deleted-scan/hash/freshness/DB), ghi
  command+expected+observed+exit+timestamp+interpretation, không complete bằng marker.
---

# Verification Before Completion

## Mục tiêu
Bắt buộc evidence thật trước mọi completion claim: chạy command thật và ghi kết quả
quan sát, không dựa file tồn tại hay marker.

## Khi nào sử dụng
Dùng trước khi đánh dấu task/wave/change hoàn thành, trước archive, và trước khi báo
test pass.

## Khi nào KHÔNG sử dụng
- Chưa có change để verify.
- Để sửa code (chỉ chạy + ghi evidence).

## Đầu vào
- `SPEC.md`, `IMPLEMENTATION_PLAN.md`, task results + reviews.
- `verification/COMMANDS.yaml` (lệnh cần chạy), `KNOWLEDGE_IMPACT.yaml`.

## Câu hỏi tri thức
- Lệnh nào chứng minh được claim hoàn thành?
- Có deleted reference / stale artifact còn sót không?
- Assumption DB/graph freshness còn đúng không?

## Loại evidence bắt buộc
- `command_result`, `test_result`, `runtime_probe`.
- Deleted-reference scan; evidence-hash validation; graph/index freshness.

## Chính sách capability
Capability IDs: `runtime_verification`, `version_control`, `exact_source_inspection`.
Chỉ báo cái gì evidence chứng minh.

## Quy trình truy xuất
1. Từ spec/plan, xác định command chứng minh mỗi claim.
2. Chạy fresh; đọc output + exit code.

## Thứ tự authority và precedence
observed command output > result claim > marker/file tồn tại. Marker không thay được
observed output.

## Kết quả bắt buộc
Chạy thật: build, unit test, integration test, static analysis, contract test,
migration test, runtime smoke, deleted-reference scan, evidence-hash validation,
graph/index freshness, DB assumption check (khi cần). Ghi mỗi lệnh: command, expected,
observed, exit code, timestamp, interpretation, evidence path.

## Bất biến
- Không completion claim thiếu lệnh fresh.
- Exit code đơn lẻ không đủ.
- Deleted-reference + stale-artifact scan bắt buộc khi có file bị xoá.

## Yêu cầu evidence
Mỗi claim gắn command + expected + observed + exit + timestamp + interpretation +
evidence path trong `VERIFICATION_REPORT.md`.

## Freshness và confidence
Command chạy trên HEAD hiện tại; evidence hash + graph/index freshness được kiểm.
Output cũ không dùng lại.

## Quy trình degradation
Lệnh không chạy được vì môi trường (vd không có DB) → ghi degradation record + fallback
check (source-level), hạ confidence; không tuyên bố VERIFIED cho phần không chạy được.

## Quy trình
1. Xác định command theo claim.
2. Chạy fresh; đọc output/exit.
3. Ghi evidence vào `COMMANDS.yaml` + `VERIFICATION_REPORT.md`.
4. Trả `VERIFIED` hoặc `FAILED_VERIFICATION`.

## Điều kiện dừng
- Lệnh bắt buộc fail.
- Output mơ hồ.
- Scan tìm thấy removed reference còn tham chiếu.

## Tác động lên knowledge
Xác nhận evidence để `knowledge-curator` promote; đánh dấu graph/index cần refresh.

## Đầu ra
`verification/COMMANDS.yaml`, `verification/VERIFICATION_REPORT.md` + verdict.

## Handoff tiếp theo
`knowledge-curator` và archive.
