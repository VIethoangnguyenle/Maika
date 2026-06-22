---
name: convention-intelligence-builder
version: '1.0'
description: >
  Scan codebase qua UA + Codebase Memory để extract naming conventions, class suffix patterns,
  và layer-specific design principles. Sinh conventions.draft.yaml để user review trước khi approve.
  Dùng khi onboard project mới hoặc sau refactor lớn cần cập nhật conventions.
  KHÔNG dùng cho: viết convention thủ công (→ edit trực tiếp conventions.yaml),
  review kiến trúc/rủi ro (→ architecture-reviewer), infer coding philosophy (→ author-dna-builder).
---

# Convention Intelligence Builder

## 1. Mục tiêu

Extract **implicit conventions** từ codebase thực tế — không phải generic best practice — và đưa chúng vào `{{ platform.framework_root }}/knowledge/long-term/conventions.yaml` để agent dùng khi sinh spec và code.

Hai nguồn được scan đồng thời qua UA Knowledge Graph:
- **Project codebase** (`PROJECT_ROOTS`) — convention project-native, có thể có exception có lý do.
- **Upstream shared library** (`UPSTREAM_ROOTS`) — convention từ shared library bắt buộc tuân theo, không override.

Output cuối là `conventions.draft.yaml` → user review + edit trong IDE → chạy `/approve-conventions` để commit chính thức.

---

## 2. Khi nào dùng

Trigger skill này khi:
- Bắt đầu onboard một project mới vào hệ thống Agent Memory.
- Sau refactor lớn (rename package, đổi layer architecture).
- User cảm thấy agent đang đề xuất tên class/file không khớp với convention thực tế.
- `conventions.yaml` chưa tồn tại hoặc `status: stale` trong metadata.

---

## Khi nào KHÔNG sử dụng

- Khi chỉ muốn tra cứu convention — đọc `conventions.yaml` trực tiếp.
- Khi task đang ở Pha 2/3 — không nên scan convention giữa chừng spec.
- Khi cần viết convention thủ công (→ edit trực tiếp conventions.yaml).
- Khi cần review kiến trúc/rủi ro (→ architecture-reviewer).
- Khi cần infer coding philosophy (→ author-dna-builder).

---

## 3. Nguồn dữ liệu

| Nguồn | Abstract Operation | Ghi chú |
|-------|------|---------|
| Code exploration (structured) | `{{ tools.search_code }}`, `{{ tools.get_symbol }}`, `{{ tools.read_file }}` | Nguồn chính cho naming pattern |
| Code exploration (upstream) | Cùng operations, filter theo `UPSTREAM_ROOTS` path | Tag `origin: upstream` |
| Code exploration (semantic) | `{{ tools.search_code }}` (semantic mode) | Làm giàu pattern khi structured fuzzy |
| Code exploration (domain) | `{{ tools.get_symbol }}` | Hiểu layer boundaries |

---

## 4. Quy trình chi tiết

### Bước 1 — Kiểm tra trạng thái công cụ

```
CALL: {{ tools.code_status }}()
  IF provider không tồn tại hoặc dữ liệu quá cũ:
    → WARN: "Code exploration chưa sẵn sàng. Cần setup provider trước."
    → ABORT
  IF provider OK:
    → Ghi nhận: project_root path, upstream_root path (nếu có upstream library)
    → Dùng path prefix để phân biệt origin sau này
```

---

### Bước 2 — Structural Audit (5 chiều)

Chạy song song 5 chiều scan qua adapter operations:

| Chiều | Nội dung | Operation chính |
|-------|----------|------------|
| **2A** | File & Class Naming Patterns (suffix grouping) | `{{ tools.search_code }}(type="class")` |
| **2B** | Package / Layer Structure | `{{ tools.get_symbol }}()` |
| **2C** | Architecture Core Patterns & Dispatch | `{{ tools.get_dependencies }}()` |
| **2D** | Upstream Conventions từ shared library | `{{ tools.search_code }}(upstream)` |
| **2E** | Test & Config Conventions | `{{ tools.search_code }}()` |

> **Chi tiết đầy đủ (scan queries per dimension)**: Xem [references/structural-audit-scan.md](references/structural-audit-scan.md)

### Bước 3 — Pattern Consolidation

Sau khi có raw data từ 5 chiều, consolidate thành structured findings:

```
FOR EACH pattern category:
  1. Tính confidence score:
     - HIGH   : count >= 10, consistent across layers
     - MEDIUM : count 3-9, hoặc có exception nhỏ
     - LOW    : count < 3, hoặc contradicted by other evidence

  2. Phân biệt origin:
     - project-native : source_path trong PROJECT_ROOTS
     - upstream       : source_path trong UPSTREAM_ROOTS

  3. Detect exceptions (nếu có):
     - Pattern X xuất hiện 15 lần nhưng có 2 file vi phạm
     → Ghi nhận exception, không bỏ qua

  4. Ghi evidence:
     - Ít nhất 2-3 ví dụ cụ thể (class name, file path) cho mỗi pattern
```

---

### Bước 4 — Sinh conventions.draft.yaml

Ghi ra `{{ platform.framework_root }}/knowledge/long-term/conventions.draft.yaml` với 7 sections:
Naming Conventions, Package Structure, Design Patterns, Upstream Constraints,
Test Conventions, Exceptions & Inconsistencies, Needs Review.

### Bước 5 — Summary Report cho User

Xuất bảng tóm tắt: HIGH/MEDIUM/LOW patterns, upstream constraints, exceptions, needs review.

### Bước 6 — /approve-conventions Workflow

Validate draft → Cross-check với snapshot → Promote to approved → Update context-loader.

> **Chi tiết đầy đủ (YAML template + report format + approve workflow)**: Xem [references/conventions-draft-template.md](references/conventions-draft-template.md)

---

## 5. Re-scan Policy & Agent Usage

- **Re-scan modes**: [U] Update, [R] Rebuild, [S] Skip
- **Agent usage sau approve**: enforce naming ở Pha 2, warn ở architecture review, KHÔNG override upstream constraints

## [L4] Delta Scan Mode

Scan chỉ files changed since last scan. Fallback to full scan nếu >20% files thay đổi.

> **Chi tiết đầy đủ (re-scan, usage, delta algorithm)**: Xem [references/rescan-usage-guide.md](references/rescan-usage-guide.md)

---

## Đầu ra

- **File chính**: `{{ platform.framework_root }}/knowledge/long-term/conventions.draft.yaml` — bản nháp chờ user review.
- **Sau `/approve-conventions`**: `{{ platform.framework_root }}/knowledge/long-term/conventions.yaml` — bản chính thức (approved).
- **Cập nhật**: `{{ platform.framework_root }}/knowledge/active/AGENT_TRANSPARENCY.md` — ghi lại kết quả scan.

---

## 7. Cập nhật AGENT_TRANSPARENCY

```
- [x] convention-intelligence-builder
- Scanned: {n} project nodes, {n} upstream nodes
- Patterns extracted: {n} high, {n} medium, {n} low confidence
- Upstream constraints: {n} mandatory rules từ {upstream_library}
- conventions.yaml status: draft | approved
- Warnings: {list nếu có conflict với snapshot}
```
