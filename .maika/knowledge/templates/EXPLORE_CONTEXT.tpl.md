# EXPLORE_CONTEXT — Template
> Ticket: <!-- ticket-id -->
> Ngày khảo sát: <!-- date -->
> Nguồn: <!-- Codebase Memory / Understand-Anything / DB Explorer / ... -->

<!-- TODO: fill in — file này là template skeleton, không phải context thực -->

---

## 1. Database Schema

### 1.1 Bảng/Collection liên quan

| Column | Type | Nullable | Comment |
|--------|------|----------|---------|
| ... | ... | ... | ... |

---

## 2. Codebase Mapping

### 2.1 Module/Service liên quan

```
ASCII diagram bắt buộc khi có flow/state/data path.

<!-- Ví dụ:
actor/system
  -> entry point
  -> service/module
  -> database / external system
  -> result / event
-->
```

Danh sách module chỉ đủ khi không có sequence hoặc boundary đáng kể.

### 2.2 Entry Points

| Handler/Endpoint | Class | Path |
|-----------------|-------|------|
| ... | ... | ... |

### 2.3 Key Components (với node_id để downstream skill dùng)

<!-- node_id = qualified_name ĐẦY ĐỦ do cbm trả về (vd
     home-zane-Desktop-project.cli.scaffold.scaffold_plugin), KHÔNG dùng tên ngắn.
     gate code-evidence probe cbm verify node tồn tại — tên ngắn/sai/bịa sẽ FAIL. -->

| Component | node_id | Vai trò |
|-----------|---------|---------|
| ... | ... | ... |

---

## 3. Enum & Constants quan trọng

<!-- Enum, error code, constant liên quan -->

---

## 4. Phát hiện quan trọng

1. <!-- phát hiện 1 -->
2. <!-- phát hiện 2 -->
