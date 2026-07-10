# RULES.md — Agent Rules Manifest

> Entry point cho toàn bộ rule system.
> Bootstrap đọc file này trước, sau đó load các sub-file theo thứ tự.

---

## 1. Scope & Priority

- **Scope**: áp dụng cho tất cả agent, tool, skill, workflow trong repo này.
- **Ưu tiên** (chuỗi canonical — R-Flow-3 tham chiếu về đây):
  1. Policy tổ chức / luật pháp (nếu có).
  2. Rules trong `RULES.md`.
  3. Workflow trong `{{ platform.framework_root }}/workflows/*.md` (đặc biệt `[CRITICAL]` block).
  4. Hướng dẫn trong `{{ platform.config_entry_point }}`.
  5. Hướng dẫn trong từng `SKILL.md`.
  6. Chat trực tiếp với user.
  (Agent runtime defaults — planning mode, artifact convention của runtime — luôn xếp cuối.)

## Importance Markers

Để tối ưu hóa sự chú ý (attention) của agent, các rule được đánh dấu:
- `[CRITICAL]`: Core constraint, **không được vi phạm** trong bất kỳ hoàn cảnh nào.
- `[REFERENCE]`: Context/Background, chỉ dùng để đọc lướt và tham khảo khi cần, không ép buộc hành vi tức thời.

---

## Rule Index — Sub-files

| File | Nội dung | Sections |
|------|----------|---------|
| `rules/rules-flow.md` | Flow bắt buộc, Spec/Apply, Bootstrap | §2, §6, §11 |
| `rules/rules-tool.md` | Provider Doctrine (preferred provider, use-when-healthy, probe, freshness, degradation) | §3 |
| `rules/rules-exec.md` | Data, Architecture, Cost, Observability | §4, §5, §7, §8 |
| `rules/rules-knowledge.md` | Hiến pháp tri thức (nguồn, thẩm quyền, freshness, reconcile, promotion, supersession) | §10 |
| `rules/rules-guard.md` | Pre-invoke Guards, R-DNA-7, R-KI-1 | §14 |

> Path Convention: quy ước path knowledge nay ở `knowledge/README.md` (nguồn canonical); `rules-knowledge.md` §10 trỏ về đó.

---

## Load Order (bootstrap)

```
READ: RULES.md                    ← manifest + §1 Scope/Priority
READ: rules/rules-flow.md         ← critical: flow constraints
READ: rules/rules-tool.md         ← tool permissions
READ: rules/rules-exec.md         ← data/arch/cost/obs
READ: rules/rules-knowledge.md    ← knowledge lifecycle + path
READ: rules/rules-guard.md        ← pre-invoke guards (đọc SAU cùng để override)
```

**Quan trọng**: Phải đọc đủ 6 file. Thiếu bất kỳ file nào = guardrails không đầy đủ.
