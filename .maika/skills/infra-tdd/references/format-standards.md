# Format Standards

> Tài liệu tham khảo cho skill `infra-tdd`. Load khi cần quy tắc attribution, navigation, hub/sub-doc, PDF compatibility, ADR list, và Mermaid.

## Mục lục

- Format Standards

---

## Format Standards

> Các quy tắc format dưới đây đảm bảo tính nhất quán, dễ đọc, và dễ bảo trì cho toàn bộ bộ TDD.
> Kết hợp cùng hybrid 5-layer (T0-T4) để tạo trải nghiệm đọc liền mạch.

### FS-1: Attribution Header

Mỗi TDD file **PHẢI** có attribution block ở đầu file, ngay sau tiêu đề. Dùng format **single-line blockquote** để đảm bảo PDF render đúng:

```markdown
> **Attribution** - **Author**: {tên} - **Domain**: {module} - **Date**: {YYYY-MM} - **Security Level**: Internal
```

⚠️ **KHÔNG** dùng bullet list (`> -`) trong blockquote — mkdocs-with-pdf sẽ gộp thành 1 dòng mất format.

### FS-2: Navigation Footer

Mỗi TDD file **PHẢI** có navigation footer ở cuối file:

```markdown
---
**[← TDD trước](./prev-TDD.md)** | **[Mục lục](./00-index.md)** | **[TDD tiếp theo →](./next-TDD.md)**
```

Thứ tự navigation theo dependency graph trong `00-index.md` (Foundation → Transaction → Approval → ...).

### FS-3: Hub + Sub-doc Pattern

Khi TDD **vượt quá 500 dòng**, PHẢI tách thành hub + sub-docs:

```
docs/tdd/
├── <module>-TDD.md              ← Hub file (mục lục + tổng quan)
└── <module>/
    ├── <module>-01-overview.md   ← Sub-doc chi tiết
    ├── <module>-02-architecture.md
    └── <module>-03-operations.md
```

Hub file chỉ chứa: mục lục, Design Patterns Summary Table, dependency map. Chi tiết T0-T4 nằm trong sub-docs.



### FS-4: Design Patterns Summary Table

Mỗi TDD **PHẢI** có bảng tổng hợp Design Patterns ở đầu T2 Architecture:

```markdown
| Pattern | Áp dụng tại | Vai trò |
|---------|-------------|---------|
| Template Method | BaseHandler (pre → around → post) | Khung xử lý cố định, subclass override từng bước |
| Strategy | ConfirmType routing | Chọn luồng xử lý tại runtime |
```



### FS-5: Code Examples (NÊN / KHÔNG NÊN)

T2 Architecture **NÊN** có ít nhất 1 code example theo format:

```markdown
#### ✅ NÊN
```java
// Code đúng pattern
```

#### ❌ KHÔNG NÊN
```java
// Anti-pattern
```
```



### FS-6: Configuration Reference trong T4

T4 Vận hành **PHẢI** có bảng Configuration Reference:

```markdown
### Configuration Reference

| Config | Mô tả | Default |
|--------|-------|---------|
| {config key} | {mô tả chức năng} | {giá trị mặc định hoặc file tham chiếu} |
```

> **Lưu ý**: Troubleshooting Runbook **KHÔNG** nằm trong TDD. Đối tượng đọc chính của TDD là Trưởng phòng và Tech Leads — nội dung vận hành chi tiết (symptom/cause/fix) thuộc tài liệu ops riêng.



### FS-7: Developer Checklist (tùy chọn)

Nếu TDD mô tả pattern mà developer cần follow (tạo Handler mới, tạo Factory mới...), bổ sung:

```markdown
### Checklist: Thêm {feature} mới

| Bước | Tạo | Kế thừa | Ví dụ |
|------|-----|---------|-------|
| 1 | ... | ... | ... |
```

### FS-8: Blank Line trước Bullet List (PDF compatibility)

mkdocs-with-pdf gộp text thành 1 dòng inline nếu thiếu dòng trống trước bullet list. **BẮT BUỘC** có blank line trong 3 trường hợp:

**Trường hợp 1 — Bold header + bullet list** (ADR Consequences, Contract...):

```markdown
<!-- ✅ ĐÚNG -->
**Consequences**:

- Item 1
- Item 2

<!-- ❌ SAI — PDF render thành 1 dòng -->
**Consequences**:
- Item 1
```

**Trường hợp 2 — Mô tả text + bullet link** (Hub files):

```markdown
<!-- ✅ ĐÚNG -->
### 1. Tầng Nghiệp vụ (T0)
Bối cảnh nghiệp vụ, quy tắc kinh doanh chung.

- 📖 **[T0 Bối cảnh Nghiệp vụ](./pf-01-business.md)**

<!-- ❌ SAI — mô tả và link dính 1 dòng -->
### 1. Tầng Nghiệp vụ (T0)
Bối cảnh nghiệp vụ, quy tắc kinh doanh chung.
- 📖 **[T0 Bối cảnh Nghiệp vụ](./pf-01-business.md)**
```

**Trường hợp 3 — Plain text + bullet list** (Architecture bài toán, yêu cầu...):

```markdown
<!-- ✅ ĐÚNG -->
Các yêu cầu chính:

- **Multi-stage flexible** — 1-3 cấp duyệt
- **Race-free** — concurrent actions

<!-- ❌ SAI — bullets dính vào text -->
Các yêu cầu chính:
- **Multi-stage flexible** — 1-3 cấp duyệt
```

**Quy tắc chung**: Bất kỳ dòng text nào ngay trước `- ` (bullet) đều **phải** có 1 blank line xen giữa.

### FS-9: Không dùng Numbered List trong ADR (PDF indentation bug)

mkdocs-with-pdf (WeasyPrint) coi mọi text sau numbered list (`1. 2. 3.`) vẫn là continuation của list item cuối cùng → các phần **Decision**, **Consequences** bị thụt lề sai.

**Quy tắc**: Trong ADR, phần **Alternatives** phải dùng **bullet list** (`- `), KHÔNG dùng numbered list (`1. 2. 3.`). Ghi số option vào tên:

```markdown
<!-- ✅ ĐÚNG — bullet list, Decision/Consequences không bị thụt -->
**Alternatives**:

- **Option 1: Template Method** — Base class skeleton → Type-safe, dễ debug
- **Option 2: AOP** — Annotations → Khó debug, ẩn side-effects
- **Option 3: Middleware** — Filter chain → Thiếu type safety

**Decision**: Option 1 — Template Method.

**Consequences**:

- ✅ Consistent codebase
- ⚠️ Inheritance depth cần kiểm soát

<!-- ❌ SAI — numbered list khiến Decision/Consequences thụt lề -->
**Alternatives**:

1. **Template Method** — ...
2. **AOP** — ...
3. **Middleware** — ...

**Decision**: Option 1   ← BỊ THỤT VÀO DƯỚI ITEM 3!
```

### FS-10: Mermaid Line Break — dùng `<br/>`, KHÔNG dùng `\n`

Kroki (mermaid renderer trong mkdocs) render `\n` thành **literal text** `\n` thay vì xuống dòng. **BẮT BUỘC** dùng `<br/>`:

```markdown
<!-- ✅ ĐÚNG -->
A["Người dùng chọn<br/>phương thức xác thực"]

<!-- ❌ SAI — hiển thị literal \n -->
A["Người dùng chọn\nphương thức xác thực"]
```

Ngoài ra, nếu diagram có nhiều node ngang (>4), ưu tiên layout `LR` (left-right) thay vì `TB` (top-bottom) để tránh diagram quá rộng bị tràn/che nội dung trong PDF.
