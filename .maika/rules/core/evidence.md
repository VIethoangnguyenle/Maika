# core/evidence.md — Hiến pháp evidence (CORE, always-on)

> Core rule — luôn load qua manifest `RULES.md`. Lifecycle/promotion: xem `jit/knowledge-lifecycle.md`.
> Định nghĩa cách Maika **truy hồi, xác thực, áp dụng và tiến hóa** tri thức dự án
> xuyên suốt vòng đời thay đổi phần mềm. Provider doctrine cụ thể: xem `jit/providers.md`.

---

## 10. Knowledge Rules — Hiến pháp tri thức

### [CRITICAL] R-Know-1: Nguồn tri thức (knowledge sources)

Maika công nhận đúng các nguồn sau — không nguồn nào khác là source of truth:

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

- `high` = ≥2 nguồn độc lập **và** exact fact đã verify bằng current source;
  `medium` = một nguồn / chưa verify source; `low` = inference / stale / degradation.

### [CRITICAL] R-Know-6: Nghĩa vụ truy hồi (P1 + P2)

- **Câu hỏi tri thức trước retrieval** (P1): mỗi pha reasoning non-trivial mở đầu bằng
  việc định nghĩa nó phải biết gì, phát ra query plan.
- **Evidence trước design** (P2): architecture/spec/plan không được chốt từ request mơ
  hồ, graph summary, stale memory, đoán tên file, hay intuition.

### R-Know-7: Provider usage

Chính sách provider (preferred, use-when-healthy, probe, DB read-only, recall):
**`jit/providers.md`** — một nguồn duy nhất.

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

### [CRITICAL] R-Know-10: Assumption tường minh + phân loại risk

- Mọi giả định là một **typed record** theo `config/assumption-policy.yaml`
  (id, type, statement, evidence_gap, expiry_condition). Không được suy luận ngầm
  dựa trên giả định chưa ghi; type rủi ro (public contract, persistence, security,
  migration, behavior-changing) bị gate chặn cho tới khi có human decision.
