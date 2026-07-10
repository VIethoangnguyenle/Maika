# rules-knowledge.md — Hiến pháp tri thức (Knowledge Constitution)

> Sub-file của `RULES.md`. Đọc qua manifest `RULES.md`.
> Định nghĩa cách Maika **truy hồi, xác thực, áp dụng và tiến hóa** tri thức dự án
> xuyên suốt vòng đời thay đổi phần mềm. Provider doctrine cụ thể: xem `rules-tool.md`.

---

## 10. Knowledge Rules — Hiến pháp tri thức

### [CRITICAL] R-Know-1: Nguồn tri thức (knowledge sources)

Maika công nhận đúng các nguồn sau, không nguồn nào khác được coi là source of truth:

1. **Understand-Anything (UA)** — graph kiến trúc/domain, quan hệ module, tài liệu.
2. **Codebase Memory (CBM)** — graph symbol/dependency, call path, phạm vi ảnh hưởng.
3. **Agent Memory** — episodic: incident, quyết định cũ, rejected approach, review pattern.
4. **Current source** — authority cho exact code fact (file, symbol, test, config hiện tại).
5. **Durable project knowledge** — Author DNA, conventions, `knowledge-snapshot.md`,
   approved business rule, known constraint (xem `knowledge/README.md` cho path canonical).
6. **Database Explorer (read-only)** — schema, object, dependency, live drift.

Không được tạo **hai nguồn cùng làm source of truth** cho cùng một loại tri thức.

### [CRITICAL] R-Know-2: Thứ tự thẩm quyền (authority hierarchy)

Khi các nguồn mâu thuẫn, giải quyết theo precedence:

```text
live runtime / database state
  > current source
  > current explicit business contract
  > fresh graph (UA/CBM)
  > approved durable knowledge
  > historical memory
  > inference của model
```

Suy đoán của model (inference) là **thấp nhất** và không bao giờ ghi đè một nguồn thật.

### [CRITICAL] R-Know-3: Provenance bắt buộc

Mỗi claim/entry tri thức phải ghi: **provider**, source anchor (file+symbol / node_id /
memory ref / DB object), `indexed_commit` (với graph), **freshness state**, và
**confidence**. Claim không có provenance = không dùng được cho decision.

### [CRITICAL] R-Know-4: Freshness

- Graph evidence phải so `indexed_commit` với repo HEAD; lệch → **stale**.
- Evidence stale phải **degrade hoặc block** high-risk decision (không dùng lặng lẽ).

### R-Know-5: Confidence

- `high` = ≥2 nguồn độc lập đồng thuận **và** exact fact đã verify bằng current source.
- `medium` = một nguồn, hoặc nhiều nguồn nhưng chưa verify source.
- `low` = chỉ inference / evidence stale / degradation.

### [CRITICAL] R-Know-6: Nghĩa vụ truy hồi (P1 + P2)

- **Câu hỏi tri thức trước retrieval** (P1): mỗi pha reasoning non-trivial mở đầu bằng
  việc định nghĩa nó phải biết gì, phát ra query plan.
- **Evidence trước design** (P2): architecture/spec/plan không được chốt từ request mơ
  hồ, graph summary, stale memory, đoán tên file, hay intuition.

### R-Know-7: Provider usage

Chính sách dùng provider (preferred provider, use-when-healthy, real probe, DB read-only,
memory recall) định nghĩa tại **`rules-tool.md`** — không lặp lại ở đây (một nguồn duy nhất).

### [CRITICAL] R-Know-8: Reconcile mâu thuẫn (conflict reconciliation)

Mọi mâu thuẫn material phải được **phân loại** rồi resolve theo R-Know-2:

```text
stale graph | stale memory | source drift | database drift |
business ambiguity | convention conflict | true architecture contradiction
```

Mâu thuẫn material **chưa resolve** thì **block design** (không được đi tiếp sang spec/plan).

### [CRITICAL] R-Know-9: Negative evidence là evidence

- Zero-result (vd recall rỗng, không tìm thấy incident) là **evidence hợp lệ** và phải
  được ghi lại, không phải lý do bỏ qua provider hay bỏ trống coverage.

### [CRITICAL] R-Know-10: Assumption tường minh

- Mọi giả định phải ghi kèm **confidence** và **expiry condition** (điều kiện khiến nó
  hết hiệu lực). Không được suy luận ngầm dựa trên giả định chưa ghi.

### [CRITICAL] R-Know-11: Invalidation

- Tri thức sai / lỗi thời phải được **invalidate** ngay khi phát hiện; doc/entry bị thay
  phải nhận header `Status: SUPERSEDED by <path> (<ngày>)` (đồng bộ dev-rule R6).

### R-Know-12: Promotion

- Tri thức đã **verified** mới được promote vào durable knowledge (Author DNA khi là
  thinking lens đã confirmed; conventions khi đủ repeated evidence; `knowledge-snapshot.md`
  khi là factual architecture). Extraction chỉ chạy **sau verified completion**.

### R-Know-13: Supersession

- Entry cũ khi bị thay ghi `superseded_by`, **không xóa lịch sử tri thức** — git + archive
  giữ lịch sử.

### R-Know-14: Knowledge slice (P8)

- Mỗi implementation task nhận **slice nhỏ nhất liên quan** (code evidence, business rule,
  convention, Author DNA, historical context, DB evidence, forbidden pattern, assumption,
  freshness, confidence) — chi tiết capsule ở skill `writing-plan` / `knowledge-curator`.

### R-Know-15: Memory save

- Sau verified completion, save episodic memory (bài học phòng incident, quyết định, rejected
  approach) vào Agent Memory để recall cho change tương lai.

### [CRITICAL] R-Know-16: Database evidence

- Persistence-sensitive change phải mang DB evidence vào knowledge (xem `rules-tool.md`
  R-Tool-9). Chênh lệch source ↔ live DB được ghi là conflict `database drift` và reconcile.

### R-Know-17: Graph / index refresh

- Change ảnh hưởng cấu trúc code/domain → trigger **graph refresh** (UA/CBM re-index) và
  **regenerate knowledge index** (`knowledge-index.yaml`) khi cần.

---

## Quy ước path knowledge

Bộ nhớ phân tầng (`active/`, `long-term/`, `archive/`, `templates/`) và path canonical của
từng file tri thức được quy ước tại **`knowledge/README.md`** (nguồn duy nhất). Artifact
grounding chính: `GROUNDING.yaml`, `EVIDENCE_MANIFEST.yaml` (chi tiết ở W2 exploration).
