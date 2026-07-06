---
description: Approve conventions.draft.yaml → commit thành conventions.yaml chính thức sau khi user đã review và edit trực tiếp trong IDE.
---

# /approve-conventions — Workflow Commit Convention

Workflow này chỉ chạy khi user đã:
1. Có `conventions.draft.yaml` (sinh bởi `/convention-scan`)
2. Đã review và edit trực tiếp trong IDE
3. Sẵn sàng commit thành `conventions.yaml` chính thức

---

## Bước 1 — Validate file

```
CHECK: {{ platform.framework_root }}/knowledge/long-term/conventions.draft.yaml tồn tại?
  → Không tồn tại: ABORT
    "conventions.draft.yaml không tìm thấy. Chạy /convention-scan trước."

PARSE: YAML hợp lệ?
  → Parse error: ABORT, báo dòng lỗi cụ thể.

CHECK: meta.status == "draft"?
  → Nếu "approved": ABORT "File này đã được approve rồi (conventions.yaml)."
  → Nếu field thiếu: WARN, tiếp tục.

CHECK: Các section bắt buộc còn đủ?
  Bắt buộc: meta, naming, package_structure, upstream_constraints
  → Thiếu section: WARN từng section thiếu, hỏi user có muốn tiếp tục không.
```

---

## Bước 2 — Cross-check với knowledge-snapshot.md

```
READ: {{ platform.framework_root }}/knowledge/long-term/knowledge-snapshot.md
  → Nếu không tồn tại: SKIP bước này, ghi WARN vào AGENT_TRANSPARENCY.

FOR EACH entry trong conventions.draft.yaml:
  IF có thông tin mâu thuẫn rõ ràng với snapshot:
    VÍ DỤ:
      conventions: "Không dùng JpaRepository trực tiếp"
      snapshot:    "TransactionRepository extends JpaRepository<...>"
    → LIST ra tất cả conflict.
    → HỎI user: "Phát hiện {n} conflict giữa conventions và knowledge-snapshot.
                  Source of truth là file nào?"
      [C] Conventions là đúng → cập nhật snapshot tương ứng
      [S] Snapshot là đúng    → cập nhật conventions tương ứng
      [K] Giữ cả 2, đánh dấu cần review sau

  IF không có conflict rõ ràng: tiếp tục.
```

---

## Bước 3 — Promote draft → approved

```
1. Cập nhật metadata trong conventions.draft.yaml:
   meta.status: approved
   meta.approved_at: {ISO timestamp}

2. Rename:
   conventions.draft.yaml → conventions.yaml

3. Backup draft:
   Tạo conventions.draft.{YYYYMMDD-HHMMSS}.yaml.bak
   (copy từ conventions.draft.yaml trước khi rename)
   → Giữ trong {{ platform.framework_root }}/knowledge/long-term/ làm audit trail
   → Không vào context (context-loader chỉ nạp knowledge-index.yaml từ long-term/, không nạp *.bak)

4. Regenerate knowledge index (bootstrap/context-loader P3 nạp entry list từ đây):
   python3 {{ platform.framework_root }}/tools/knowledge-index/generate_index.py {{ platform.framework_root }}/knowledge/long-term
```

---

## Bước 4 — Cập nhật AGENT_TRANSPARENCY

```
APPEND vào {{ platform.framework_root }}/knowledge/active/AGENT_TRANSPARENCY.md:

  [x] /approve-conventions: conventions.yaml committed
  - Approved at: {timestamp}
  - Patterns approved:
    - Naming suffixes: {n} (high: {n}, medium: {n}, low: {n})
    - Design patterns: {n}
    - Upstream constraints: {n} mandatory rules từ {upstream_library}
  - Conflicts resolved: {n} (hoặc "none")
  - conventions.yaml status: active tại P3 context từ phiên tiếp theo
```

---

## Bước 5 — Thông báo user

```
"✅ conventions.yaml đã được commit chính thức.

 Tóm tắt:
 • {n} naming conventions ({n} high, {n} medium confidence)
 • {n} upstream constraints từ {upstream_library} (mandatory)
 • {n} design patterns detected
 • conventions.draft.{timestamp}.yaml.bak đã được lưu

 Hiệu lực: Từ phiên làm việc tiếp theo, agent sẽ tự động nạp
 conventions.yaml vào context P3 (cùng với knowledge-snapshot.md).

 Nếu cần cập nhật convention sau này: /convention-scan → [U] Update"
```

---

## Error Cases

| Tình huống | Hành động |
|-----------|-----------|
| conventions.draft.yaml không tồn tại | ABORT, hướng dẫn chạy /convention-scan |
| YAML parse error | ABORT, báo dòng lỗi |
| Conflict với snapshot, user chọn [K] | Ghi cả 2 entry, thêm marker `# REVIEW NEEDED` |
| conventions.yaml đã tồn tại (approve lần 2) | Hỏi: overwrite hay merge? |
