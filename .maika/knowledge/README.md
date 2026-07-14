# {{ platform.framework_root }}/knowledge — Durable Knowledge cho Agent

## Mục đích

`{{ platform.framework_root }}/knowledge` giữ **tri thức bền (durable knowledge)** của
project. Task-scoped context KHÔNG nằm ở đây — mọi artifact theo task sống trong
`{{ platform.framework_root }}/changes/<change-id>/` (authority map:
`config/artifact-authority.yaml`).

Các tầng:

- **`long-term/`** — *long-term memory*: judgment sống + bản đồ kiến trúc,
  **source-of-truth** (tích luỹ, không reset).
- **`active/`** — legacy landing zone, không còn artifact canonical nào (bootstrap
  runtime nay ở `{{ platform.framework_root }}/runtime/`); các file working-memory cũ
  đã được thay bằng `changes/<change-id>/` — xem mục `deprecated` trong
  `config/artifact-authority.yaml`; migrate target cũ bằng
  `maika content migrate-legacy --target <repo> --apply`.
- **`archive/`** — episodic memory legacy (đường archive canonical của change:
  `{{ platform.framework_root }}/archive/<change-id>/`).
- **`templates/`** — skeleton tĩnh để clone (ticket-type, archive metadata,
  session override, skill feedback/candidate), **không chứa knowledge sống**.
- **`skill-evolution/`** — feedback cluster và candidate lifecycle; candidates chỉ từ
  verified evidence, accepted/rejected giữ provenance và promotion result.

---

## Cấu trúc

```
{{ platform.framework_root }}/knowledge/
├── README.md                 ← File này
├── active/                   ← Legacy landing zone (runtime artifact nay ở ../runtime/)
├── long-term/                ← Long-term memory — judgment sống + source-of-truth (không reset)
│   ├── knowledge-snapshot.md  ← Bản đồ kiến trúc hệ thống (tích luỹ qua nhiều task)
│   ├── knowledge-index.yaml   ← Entry list cho JIT slice tại decision-gate (generated)
│   ├── conventions.yaml       ← Convention đặt tên + design pattern (approved)
│   ├── author-dna.yaml        ← Triết lý code của tác giả (judgment layer)
│   ├── persona.yaml           ← Phong cách tương tác (local, gitignored)
│   └── persona.template.yaml  ← Template persona (committed)
├── archive/                  ← Episodic memory legacy (change mới archive về ../archive/<id>/)
├── skill-evolution/          ← candidates/accepted/rejected + canonical index
└── templates/                ← skeleton để clone: ARCHIVE_META, ticket-type
                                (feature, fixbug, refactor, changerequest), SESSION_OVERRIDE,
                                SKILL_FEEDBACK, SKILL_CANDIDATE
```

---

## Quy ước path

Task-scoped path: xem `config/artifact-authority.yaml` (một decision — một source).
Durable path canonical:

| File | Path đầy đủ |
|------|-------------|
| Knowledge Snapshot | `{{ platform.framework_root }}/knowledge/long-term/knowledge-snapshot.md` |
| Knowledge Index | `{{ platform.framework_root }}/knowledge/long-term/knowledge-index.yaml` |
| Conventions | `{{ platform.framework_root }}/knowledge/long-term/conventions.yaml` |
| Author DNA | `{{ platform.framework_root }}/knowledge/long-term/author-dna.yaml` |

---

## Lifecycle

1. **Task**: workflow `/task` tạo workspace `changes/<change-id>/`; skill ghi artifact
   theo authority map qua từng phase.
2. **Verified**: sau `VERIFIED`, knowledge-promoter promote candidate vào `long-term/`.
3. **Archive**: `maika task archive` dời workspace sang
   `{{ platform.framework_root }}/archive/<change-id>/` + regenerate knowledge index.

---

## Git strategy

- `templates/` + `README.md`: **COMMIT** vào git (skeleton cố định).
- `long-term/`: **COMMIT** (source-of-truth chung của team) — riêng `persona.yaml` được **GITIGNORE** (config per-user).
- `archive/`: **COMMIT** (lịch sử episodic legacy).
- `active/`: **GITIGNORE** (runtime artifact, per-session).
