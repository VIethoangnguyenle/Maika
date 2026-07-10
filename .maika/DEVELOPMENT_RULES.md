# Quy tắc phát triển framework Maika

> Mục đích: chặn việc mở rộng framework không có mục đích — file chết, field rác, cơ chế xây cho rủi ro chưa quan sát.
> Đây là phần mở rộng vận hành của tenet chương trình: **"net-negative complexity"** và **"gate-by-evidence, not gate-by-instruction"**.
> Rút ra từ audit 2026-06-21 (xóa `cursor.py`, 2 capability thừa, dead schema `pre_conditions.tool/input`) và near-miss thiết kế `pre_conditions` runtime-gate.

Mỗi rule có **Cách kiểm** cơ học để không tự nó biến thành prose bị bỏ qua.

---

## R1 — Không khai báo nếu không có consumer

Mọi capability-flag, schema-field, `pre_conditions` target/condition, platform, hay config-key phải có **≥1 consumer cơ học** (scaffold / manifest / validator / template) **trong cùng PR** với lúc khai báo. Không có consumer → không thêm.

- **Vì sao:** audit thấy 5/6 capability-flag (`artifacts`/`browser`/`image_generation`/`persistent_terminal`/`subagent`) khai mà chỉ `write_gate_hook` được gate cơ học; `pre_conditions` chấp nhận target `tool`/`input` mà 0 skill dùng. Đầu cơ = rác.
- **Cách kiểm:** với mỗi field/flag mới, grep tên nó ngoài chỗ định nghĩa. 0 hit ⇒ reject PR.

## R2 — Không có trong cây mà không có trong registry

Một platform / target / variant không **chọn được** qua đường người dùng (vd `cli/platforms/__init__.py`, lựa chọn ở `init`) thì coi như không tồn tại → **xóa**, đừng nuôi. Git giữ lịch sử nếu sau cần.

- **Vì sao:** `cursor.py` không nằm trong registry, không chọn được, nhưng vẫn nhận commit mỗi lần thêm op toàn-platform → đóng thuế bảo trì cho code không ai chạm tới.
- **Cách kiểm:** mọi file `platforms/*.py` phải xuất hiện trong dict `PLATFORMS`. Lệch ⇒ xóa file hoặc wire vào registry, không để lửng.

## R3 — Xây cho lỗi đã quan sát, không cho lỗi giả định

Enforcement mới (gate / hook / rule / validator) chỉ được thêm khi có **một bypass đã log**, **một litmus tái hiện được** lỗi đó, **một yêu cầu bên ngoài bắt buộc** (external requirement), hoặc khi nó **bảo vệ safety / destructive-action boundary** (write boundary không chờ sự cố production). Không dựng cơ chế cho rủi ro chưa từng thấy fail.

- **Vì sao:** suýt xây hook+capability+bridge để enforce `pre_conditions` runtime cho một lỗi chưa có fixture nào chứng minh — trong khi litmus P1.1 (thứ sinh bằng chứng thật) đang hoãn. Hai ngoại lệ `external_requirement`/`safety_boundary` chuẩn hóa theo enforcement ledger của vNext (Master Plan v2 §5); safety boundary có tiền lệ write-gate.
- **Cách kiểm:** PR thêm enforcement phải link tới entry trong `docs/refactor/maika-vnext/enforcement-ledger.yaml` có evidence classification hợp lệ (`observed_failure` / `reproducible_litmus` / `external_requirement` / `safety_boundary`). Không có ⇒ defer.

## R4 — Kiểm trigger/cơ chế có thật trước khi thiết kế lên nó

Trước khi thiết kế dựa trên một sự kiện runtime / tool-call / hook-point, **xác nhận nó thật sự phát ra trên mọi platform mục tiêu**. Verify trước, design sau.

- **Vì sao:** thiết kế 3 phần quanh "PreToolUse trên Skill-dispatch" rồi mới phát hiện `native_skill_export = None` trên *mọi* platform → skill là markdown inline, không có sự kiện để hook. Cả hướng sụp.
- **Cách kiểm:** trong spec, một dòng "Trigger tồn tại ở: \<file:line / cơ chế\>" có dẫn chứng, cho từng platform claim hỗ trợ.

## R5 — Mở rộng chốt chặn đang chạy trước khi thêm chốt mới

Một mối quan tâm (vd "knowledge-before-code") chỉ có **một** đường enforcement. Ưu tiên tổng quát hoá cơ chế đang chạy (vd `write-gate`) hơn dựng hệ song song.

- **Vì sao:** `write_gate.evaluate_write` đã enforce phase ordering (`Pha 2 DONE`) cross-platform; định thêm một gate thứ hai cho cùng việc là trùng lặp.
- **Cách kiểm:** trước khi thêm hook/gate, grep xem chốt chặn cho cùng mối quan tâm đã tồn tại chưa. Có ⇒ mở rộng cái cũ.

## R6 — Đóng dấu doc bị thay thế

Spec / plan / design bị một quyết định sau ghi đè phải nhận header `Status: SUPERSEDED by <đường-dẫn> (ngày)` **ngay trong PR ghi đè**. Memory point-in-time tương tự: sửa khi biết nó sai.

- **Vì sao:** 33 spec / 29 plan, 0 cái đánh dấu superseded → memory + doc P0 vẫn khung "quyết định đang mở" dù write-gate đã ship, dẫn cả phiên đi vào ngõ cụt.
- **Cách kiểm:** khi một quyết định đảo/đóng một doc cũ, PR phải đụng cả doc cũ (thêm dấu) lẫn doc/memory mới.

## R7 — Net-negative/neutral complexity là mức mặc định

Thêm file / flag / abstraction phải **biện minh được so với việc xóa**. "Có thể hữu ích sau" là lý do **từ chối**, không phải lý do thêm. Diff lý tưởng cho một dọn dẹp là âm.

- **Vì sao:** đây là tenet gốc của chương trình retro-fix; các rule trên là cách thực thi nó.
- **Cách kiểm:** mỗi PV tự hỏi "xóa được gì khi thêm cái này?". Nếu chỉ cộng, phải có consumer (R1) + lỗi đã quan sát (R3).

---

## Checklist PR (rút gọn 7 rule)

- [ ] Mọi field/flag/target mới có consumer cơ học trong cùng PR (R1)
- [ ] Không file platform/variant nào ngoài registry (R2)
- [ ] Enforcement mới có ledger entry với evidence classification hợp lệ (R3)
- [ ] Trigger/cơ chế đã verify tồn tại trên mọi platform claim (R4)
- [ ] Đã check chốt chặn cũ trước khi thêm chốt mới (R5)
- [ ] Doc/memory bị ghi đè đã đóng dấu superseded (R6)
- [ ] Đã hỏi "xóa được gì?"; không thêm vì "biết đâu sau cần" (R7)
