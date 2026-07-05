---
schema: agent-transparency/v1
ticket_id: "<!-- ticket-id -->"
updated_at: "<!-- timestamp -->"
phase_state: bootstrapped
openspec_state: null
confidence_level: null
# phase_state values: bootstrapped | phase-1-in-progress | phase-1-done | phase-2-in-progress | phase-2-done | phase-3-in-progress | blocked-by-arch | blocked-by-data | applying | completed
# openspec_state values: null | propose_done | apply_done
# confidence_level values: null | CAO | TRUNG-BINH | THAP
---

# AGENT_TRANSPARENCY — Template
> Ticket: <!-- ticket-id -->
> Cập nhật lần cuối: <!-- timestamp -->

<!-- TODO: fill in — file này là template skeleton, không phải context thực -->

---

## Phase State

```
phase_state: bootstrapped
```

<!-- Values (chọn một):
  bootstrapped        ← mới khởi động, chưa vào pha nào
  phase-1-in-progress ← đang chạy Pha 1
  phase-1-done        ← Pha 1 hoàn thành (REQUIREMENT + EXPLORE_CONTEXT đã ghi)
  phase-2-in-progress ← đang chạy Pha 2 (spec)
  phase-2-done        ← Pha 2 hoàn thành (OpenSpec đã propose)
  blocked-by-arch     ← architecture-reviewer gửi BLOCKER, chờ user quyết định
  blocked-by-data     ← thiếu dữ liệu/DB, đang chờ backfill/seed
  applying            ← đang apply (Pha 3 — micro-loop / /opsx:apply đang chạy)
  completed           ← apply xong, knowledge-curator đã archive
-->

---

## Delta Context (Chỉ ghi thay đổi)

> LUẬT TỐI ƯU TOKEN (BOOKKEEPING DIET): Không liệt kê lại toàn bộ những gì đã đọc/đã gọi từ đầu. Chỉ ghi những thay đổi (delta) phát sinh trong pha/phiên hiện tại.

- **Nguồn mới đọc thêm:** <!-- Liệt kê file/doc mới đọc trong pha này -->
- **Tool/Skill mới gọi:** <!-- Liệt kê tool/skill mới sử dụng trong pha này -->

---

## Cảnh báo / Hạn chế

<!-- Ghi rõ các vấn đề: UA chưa chạy, thiếu quyền DB, tài liệu tin cậy thấp... -->

---

## Lịch sử pha

Bootstrap | <!-- time --> | Task: <!-- input -->

<!-- Quy tắc:
  - Kết thúc mỗi pha: thêm MỘT DÒNG THÔ dạng `Pha N DONE | <timestamp> | <mô tả>` vào section này.
    Marker literal `Pha N DONE` là input của write-gate (apply-gate) và gate phase-chain —
    đặt trong bảng markdown (`| Pha 1 | … |`) sẽ KHÔNG match regex và bị coi là pha chưa xong.
  - Mỗi khi phase_state thay đổi: cập nhật block `## Phase State` ở trên.
  - Resume check: đọc `phase_state` — nếu `phase-1-done` trở lên thì không re-trigger Pha 1.
-->

---

## DNA-RELOAD Checkpoint

<!-- Ghi bởi agent khi chạy bước 2a trong Pha 3 (/task apply).
     Nếu section này trống khi phase_state = phase-3-in-progress → DNA-RELOAD chưa chạy. -->

```
[DNA-RELOAD] <!-- Chưa chạy -->
```

---

## Violation Log

<!-- Ghi mỗi violation 1 dòng. Dùng để tracking data thực tế sau mỗi task.
     Escalation criteria: sau 5 tasks, nếu ≥2 tasks có DNA BLOCK violation → chuyển Multi-Agent. -->

| Pha | Loại | Rule | Severity | Đã fix? | Ghi chú |
|-----|------|------|----------|---------|---------|
<!-- | Pha 3 | DNA | HP-6 | BLOCK | ✅ | nested if trong XxxExecutor | -->
<!-- | Pha 1 | SESSION | SESSION-BOUNDARY | WARN | — | User tiếp tục cùng session | -->

---

## Teaching Moment Check

<!-- R-DNA-7: Resolve before archive. Do NOT pre-fill status: none.
     status: one of none | captured | declined | pending-confirmation
       none      → requires a real active-assertion note (not a placeholder)
       captured  → requires target_updates (which long-term files got the entry)
       declined / pending-confirmation → require a [R-DNA-7] warn line + reason -->
status:
note:
target_updates:
warn:
reason:

---

## Đánh giá Độ tin cậy tổng thể

**<!-- CAO / TRUNG BÌNH / THẤP -->** — <!-- 1-2 câu lý do -->
