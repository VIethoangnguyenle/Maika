# Workflows — User-facing Shortcuts

Đây là thư mục tham chiếu nhanh cho các workflow chính. Logic đầy đủ nằm trong `{{ platform.framework_root }}/workflows/`.

---

## Danh sách Workflow

| Lệnh | File định nghĩa | Mô tả |
|------|----------------|-------|
| `/task <input>` | `{{ platform.framework_root }}/workflows/task.md` | Pha 1: Hiểu vấn đề, requirement, explore |
| `/task spec <ticket>` | `{{ platform.framework_root }}/workflows/task.md` | Pha 2: Sinh spec kỹ thuật |
| `/task apply <ticket>` | `{{ platform.framework_root }}/workflows/task.md` | Pha 3: Apply spec vào code |
| `/idea-to-task` | `{{ platform.framework_root }}/workflows/idea-to-task.md` | Chuyển ideation → draft ticket |
| `/index-source` | `{{ platform.framework_root }}/workflows/index-source.md` | Lập chỉ mục Codebase Memory |

---

## Quick Start

```
# Bắt đầu với ý tưởng mới
/task Thêm tính năng giới hạn số lệnh lập lệnh theo ngày cho từng nhân viên

# Bắt đầu với ticket có sẵn
/task https://jira.example.com/browse/ABC-123

# Chuyển ideation thành ticket
/idea-to-task

# Sinh spec sau khi đã có requirement + context
/task spec ABC-123

# Apply spec vào code
/task apply ABC-123
```
