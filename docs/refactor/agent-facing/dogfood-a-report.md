# Báo cáo Dogfood A — lightweight task với worker thật

Ngày chạy: 2026-07-12  
Framework: `master-v2` tại `ad37ecd`  
Target: repo Python `shopcart` độc lập trong scratchpad của phiên dogfood

## 1. Setup

Target là một package giỏ hàng nhỏ có pytest suite thật, được init Maika và cấu
hình verification profile chạy `/usr/bin/python3 -m pytest tests`. T1–T7 chạy
bằng fresh Claude Sonnet session qua trusted execution-mode override. Khi Claude
hết quota trong lúc khôi phục T8, user cho phép tiếp tục cross-host: T8 được
Codex hoàn tất trên worktree mà Claude đã sửa, còn T9–T10 chạy bằng fresh Codex
session. Codex adapter được enable bằng `maika platform enable codex`; cùng task
contract, scope inspector, verification và archive gate vẫn được giữ nguyên.

Write-gate hook thật đã chạy trong worker. Evidence rõ nhất là lần đầu T1 sinh
`.maika/hooks/write-gate/__pycache__/write_gate.cpython-312.pyc`; chính file này
cùng hai bytecode khác đã kích hoạt scope inspector và friction loop.

## 2. Kết quả 10 task

`Dispatch` dưới đây ghi số lần quan sát thực tế. Số trong `STATE.yaml` archive là
metric canonical của lần thành công cuối và được bàn riêng ở DF-4.

| ID | Class yêu cầu → hiệu lực | Task | Dispatch quan sát | Verify | SPEC/PLAN/QUEUE | Ghi chú |
|---|---|---|---:|---|---|---|
| T1 | trivial → small | Rename `Cart._calc` thành `_compute_subtotal` | 2 Claude | VERIFIED (8 pass) | Không | Lần đầu bị block bởi 3 file `.pyc`, lần hai archive thành công. |
| T2 | trivial → small | Rename `GREETING_MSG` thành `ORDER_CONFIRMATION_SUBJECT` | 1 Claude | VERIFIED (8 pass) | Không | Đúng scope. |
| T3 | small → small | Guard `None` trong `Cart.apply_discount` | 1 Claude | VERIFIED (9 pass) | Không | Đúng scope. |
| T4 | small → small | `order_summary` chịu được thiếu key `note` | 1 Claude | VERIFIED (10 pass) | Không | Đúng scope. |
| T5 | small → small | Validate quantity và price trong `Cart.add_item` | 1 Claude | VERIFIED (12 pass) | Không | Đúng scope. |
| T6 | small → small | Validate email trong `customer.register` | 1 Claude | VERIFIED (13 pass) | Không | Đúng scope. |
| T7 | trivial → small | Log lỗi `export_orders` | 1 Claude | VERIFIED (13 pass) | Không | Đúng scope. |
| T8 | small → small | Thêm operational logging cho module ops | 3 attempt | VERIFIED (14 pass) | Không | Claude sửa code rồi orchestration bị ngắt; lần retry Claude bị quota reject; Codex hoàn tất RESULT, verify và archive. |
| T9 | trivial → small | Sửa `DEFAULT_TAX_RATE` thành 8% | 1 Codex | VERIFIED (14 pass) | Không | Cross-host continuation, đúng scope. |
| T10 | small → small | `MAX_ITEMS` phải là int và được enforce | 1 Codex | VERIFIED (15 pass) | Không | Cross-host continuation, đúng scope. |

T8 có hai model session chạm task: Claude tạo thay đổi code/test, Codex đọc lại,
hoàn thiện structured result và xác nhận bằng test thật. Attempt Claude ở giữa bị
từ chối trước inference do session quota. Không có thay đổi framework source để
làm cho Codex pass.

## 3. Đối chiếu target SSOT §30 Dogfood A

| Target | Kết quả | Evidence |
|---|---|---|
| Không full spec | Đạt | Cả 10 archive không có `SPEC.md`, `IMPLEMENTATION_PLAN.md`, `generated/TASK_QUEUE.json` hay `briefs/`. |
| ≤1 implementation worker/task | Đạt 8/10 theo quan sát thực tế | T1 có 2 dispatch do lỗi setup `.gitignore`; T8 có 2 model session do interruption và cross-host recovery, cộng 1 quota rejection không inference. Canonical archive báo 1 worker call cho cả 10 task. |
| ≤1 review worker/task | Đạt | 0 review worker dispatch; lightweight dùng focused verification và author review artifact, không gọi reviewer riêng. |
| 0 scope escape thật | Đạt | Không worker nào sửa file ứng dụng ngoài scope. Block T1 chỉ gồm bytecode/cache do môi trường sinh ra. |

Tổng canonical archive: 10 implementation worker call, 10 real verification
command, 10 task `ARCHIVED`/`VERIFIED`. Theo timeline vận hành có 13 worker
process attempt: 12 attempt tới model và 1 Claude quota rejection. Final suite
chạy từ target cwd bằng `/usr/bin/python3 -m pytest tests -q`: 15 pass.

## 4. Findings

### DF-1 — Verification profile registry không được scaffold

`verification-profiles.yaml` không xuất hiện ở target sau scaffold, nên runtime
rơi về defaults nhúng. Máy này có wrapper `pytest` trên PATH không dùng được cho
run; dogfood phải tự tạo registry và pin `/usr/bin/python3`. Đề xuất thêm profile
registry vào plugin/install manifest và snapshot coverage.

### DF-2 — Scope inspector tính cả bytecode untracked

T1 bị `BLOCKED` vì ba file `__pycache__/*.pyc`, gồm bytecode của chính write-gate.
`LOOP-T1-001` chứng minh W6 friction hook hoạt động, nhưng root cause bị phân loại
như implementation scope escape dù đây là artifact môi trường. Đề xuất bỏ qua
path gitignored và Python bytecode/cache trong `inspect_lightweight_changes`.

### DF-3 — `task resume` không enforce loop approval

Trong T1, `active_loop_id: LOOP-T1-001` vẫn còn khi task được resume/archive;
decision `LOOP-T1-001-D1` thuộc loại cần approval, nhưng public `task resume` chỉ
kiểm `STATE.yaml == BLOCKED` và không kiểm loop governance như `loop resume`.
Đề xuất bind `task resume` với `active_loop_id` và trusted loop approval.

### DF-4 — Runtime metrics bị overwrite sau BLOCKED/resume

T1 có 2 dispatch quan sát và T8 có nhiều recovery attempt, nhưng archive của cả
hai đều ghi `worker_calls: 1`, `retry_count: 0`. Metrics hiện mô tả attempt cuối,
không mô tả lifecycle của task, khiến báo cáo budget/reliability thấp hơn thực tế.
Đề xuất lưu append-only attempt history và cộng dồn worker/tool/retry counters qua
mọi transition, kể cả worker exit trước RESULT và quota rejection.

### DF-5 — Orphaned `EXECUTING` không recovery được qua public CLI

T8 bị ngắt sau khi worker sửa code nhưng trước khi orchestration ghi RESULT/state.
Lease và owner PID đã chết. `task force-unlock` chỉ xóa lock; `task resume` từ
chối vì state vẫn là `EXECUTING`, còn `task apply` cũng từ chối vì lightweight
apply yêu cầu `INTAKE`. Recovery phải gọi trực tiếp canonical state service để
chuyển `EXECUTING → BLOCKED → INTAKE`. Đề xuất public `task recover` hoặc
`force-unlock --reconcile-state`, chỉ cho phép khi owner chết/lease hết hạn và
phải ghi audit record.

## 5. Đánh giá lại Wave E gate

### PR 8 — Evidence Broker: gate đóng

Dogfood không cấu hình MCP/provider retrieval, không sinh provider call và không
có duplicate query trace. Không có observed failure để biện minh Evidence Broker.

### PR 9 — Context package v2/token budget: gate đóng

Mỗi archive ghi estimate khoảng 159 token bằng `chars_div_4`, thấp xa budget
trivial 8K/small 20K và không có overflow. Đây vẫn là estimate, không phải token
usage do host cung cấp (`total_tokens: unavailable`). Không có evidence ngược lại
để build context package v2 hoặc overflow machinery.

### PR 15 — Cross-host matrix: feasibility đã có, release gate vẫn đóng

Cùng lightweight pipeline đã chạy end-to-end bằng Claude và Codex; Codex hoàn tất
T8–T10 với scope/verify/archive pass. Điều này gỡ rủi ro kỹ thuật cơ bản và cung
cấp seed evidence cho matrix. Tuy nhiên chưa chạy cùng fixture trên mọi host,
chưa có Antigravity run, consistency report hay stability window hai tuần. PR 15
có thể được lên lịch khi user muốn, nhưng chưa đủ điều kiện làm release gate.

### PR 16 — Legacy removal: gate đóng

Compatibility window N+2 chưa hết; dogfood này không thay đổi điều kiện thời gian
hay legacy consumer inventory.

## 6. Kết luận

Lightweight pipeline hoạt động end-to-end với worker thật trên hai host: 10/10
task archive và verify, final suite 15 pass, không có full spec và không có scope
escape ứng dụng thật. Mục tiêu strict “mỗi task chỉ một implementation worker” bị
miss ở T1 và T8 do hai failure mode môi trường/recovery; chính chúng tạo evidence
cụ thể cho DF-2, DF-4 và DF-5. Wave E vẫn không được build trong run này.
