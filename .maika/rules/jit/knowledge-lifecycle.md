# jit/knowledge-lifecycle.md — Vòng đời tri thức (JIT)

> JIT rule — load khi: planning (capsule/slice), archive/promotion, hoặc khi
> phát hiện knowledge stale. Evidence law core: `core/evidence.md`.

---

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
  freshness, confidence) — chi tiết capsule ở skill `writing-plan` / `knowledge-retriever`.

### R-Know-15: Memory save

- Sau verified completion, save episodic memory (bài học phòng incident, quyết định, rejected
  approach) vào Agent Memory để recall cho change tương lai.

### [CRITICAL] R-Know-16: Database evidence

- Persistence-sensitive change phải mang DB evidence vào knowledge (xem `jit/providers.md`
  R-Tool-9). Chênh lệch source ↔ live DB được ghi là conflict `database drift` và reconcile.

### R-Know-17: Graph / index refresh

- Change ảnh hưởng cấu trúc code/domain → trigger **graph refresh** (UA re-index) và
  **regenerate knowledge index** (`knowledge-index.yaml`) khi cần.

---

## Quy ước path knowledge

Durable knowledge (`long-term/`, `templates/`, `skill-evolution/`) quy ước tại
**`knowledge/README.md`**; task-scoped artifact quy ước tại
**`config/artifact-authority.yaml`** (một decision — một source). Artifact
grounding chính: `changes/<id>/exploration/GROUNDING.yaml`, `EVIDENCE_MANIFEST.yaml`.
