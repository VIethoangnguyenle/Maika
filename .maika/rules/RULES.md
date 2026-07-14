# RULES.md — Agent Rules Manifest

> Entry point cho toàn bộ rule system.
> Bootstrap đọc file này trước, load CORE luôn-luôn; JIT load theo điều kiện.

---

## 1. Scope & Priority

- **Scope**: áp dụng cho tất cả agent, tool, skill, workflow trong repo này.
- **Ưu tiên**: chuỗi precedence canonical nằm DUY NHẤT ở `agent/KERNEL.md` §2
  (Canonical Authority) — không lặp lại ở đây. Agent runtime defaults (planning
  mode, artifact convention của runtime) luôn xếp cuối chuỗi đó.

## Importance Markers

- `[CRITICAL]`: Core constraint, **không được vi phạm** trong bất kỳ hoàn cảnh nào.
- `[REFERENCE]`: Context/Background, chỉ tham khảo khi cần, không ép buộc hành vi tức thời.

---

## CORE — luôn load (bootstrap PHASE 0)

| File | Nội dung |
|------|----------|
| `rules/core/flow.md` | Flow bắt buộc, route theo router, orchestrator mỏng, spec/apply |
| `rules/core/evidence.md` | Nguồn tri thức, thẩm quyền, provenance, freshness, reconcile, assumption |
| `rules/core/write-boundary.md` | Pre-invoke guards + vNext write gate |
| `rules/core/verification.md` | Execution + verification honesty |

**Quan trọng**: Phải đọc đủ RULES.md + 4 file core. Thiếu bất kỳ file nào = guardrails không đầy đủ.

## JIT — load theo điều kiện (không preload)

| File | Load khi |
|------|----------|
| `rules/jit/providers.md` | grounding/exploration, planning, review, persistence-sensitive change |
| `rules/jit/knowledge-lifecycle.md` | planning (capsule/slice), archive/promotion, knowledge stale |
| `rules/jit/skill-evolution.md` | sau VERIFIED (skill feedback / candidate) |
| `rules/jit/teaching-moment.md` | user correction detected, external KI detected |

> Load Order chi tiết + resume: `procedures/bootstrap.md`; path knowledge:
> `knowledge/README.md` + `config/artifact-authority.yaml`.
