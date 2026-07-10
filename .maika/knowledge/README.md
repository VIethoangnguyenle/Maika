# {{ platform.framework_root }}/knowledge — Working Memory cho Agent

## Mục đích

`{{ platform.framework_root }}/knowledge` là **bộ nhớ phân tầng (memory hierarchy)** của agent trong flow:

> **Ideation → Requirement → Architecture → Spec → Apply**

Mọi skill và workflow trong `{{ platform.framework_root }}/` đọc/ghi context thông qua thư mục này.

Bộ nhớ được chia làm 4 tầng:

- **`active/`** — *working memory*: context cho task đang xử lý (reset mỗi task).
- **`long-term/`** — *long-term memory*: judgment sống + bản đồ kiến trúc, **source-of-truth** (tích luỹ, không reset).
- **`archive/`** — *episodic memory*: snapshot các task đã hoàn thành theo ticket-id.
- **`templates/`** — *skeleton tĩnh*: chỉ chứa template để clone khi bootstrap, **không chứa knowledge sống**.
- **`skill-evolution/`** — feedback cluster và candidate lifecycle; candidates chỉ từ
  verified evidence, accepted/rejected giữ provenance và promotion result.

---

## Cấu trúc

```
{{ platform.framework_root }}/knowledge/
├── README.md                 ← File này
├── active/                   ← Working memory — context ĐANG DÙNG cho task hiện tại
│   ├── REQUIREMENT.md         ← Yêu cầu chuẩn hoá
│   ├── EXPLORE_CONTEXT.md     ← Kết quả khám phá DB + code + kiến trúc
│   ├── AGENT_TRANSPARENCY.md  ← Audit: nguồn đã đọc, tool đã gọi, cảnh báo
│   ├── TOKEN_LOG.md           ← Theo dõi token theo từng pha
│   └── ideation/              ← File ideation cho ý tưởng thô
├── long-term/                ← Long-term memory — judgment sống + source-of-truth (không reset)
│   ├── knowledge-snapshot.md  ← Bản đồ kiến trúc hệ thống (tích luỹ qua nhiều task)
│   ├── knowledge-index.yaml   ← Entry list cho JIT slice tại decision-gate (generated)
│   ├── conventions.yaml       ← Convention đặt tên + design pattern (approved)
│   ├── author-dna.yaml        ← Triết lý code của tác giả (judgment layer)
│   ├── persona.yaml           ← Phong cách tương tác (local, gitignored)
│   └── persona.template.yaml  ← Template persona (committed)
├── archive/                  ← Episodic memory — context task đã hoàn thành (theo ticket-id)
│   └── {ticket-id}/
├── skill-evolution/          ← candidates/accepted/rejected + canonical index
└── templates/                ← skeleton .tpl.md để clone khi bootstrap (CHỈ template):
                                context (REQUIREMENT, EXPLORE_CONTEXT, AGENT_TRANSPARENCY, TOKEN_LOG,
                                ARCHIVE_META), ticket-type (feature, fixbug, refactor, changerequest,
                                SESSION_OVERRIDE)
```

---

## Quy ước path

Tất cả path knowledge được quy ước tại chính README này (bảng dưới) — nguồn canonical; `rules/rules-knowledge.md` §10 trỏ về đây.

Tóm tắt nhanh:

| File | Path đầy đủ |
|------|-------------|
| REQUIREMENT | `{{ platform.framework_root }}/knowledge/active/REQUIREMENT.md` |
| EXPLORE_CONTEXT | `{{ platform.framework_root }}/knowledge/active/EXPLORE_CONTEXT.md` |
| AGENT_TRANSPARENCY | `{{ platform.framework_root }}/knowledge/active/AGENT_TRANSPARENCY.md` |
| Knowledge Snapshot | `{{ platform.framework_root }}/knowledge/long-term/knowledge-snapshot.md` |
| Ideation | `{{ platform.framework_root }}/knowledge/active/ideation/ideation-*.md` |

---

## Lifecycle

1. **Bootstrap**: Workflow `/task` tạo/reset file trong `active/` từ template khi bắt đầu task mới.
2. **Tích luỹ**: Các skill ghi dần vào `active/` qua từng pha.
3. **Kết thúc**: Sau khi apply xong, context trong `active/` có thể được archive hoặc reset.

---

## Git strategy

- `templates/` + `README.md`: **COMMIT** vào git (skeleton cố định).
- `long-term/`: **COMMIT** (source-of-truth chung của team) — riêng `persona.yaml` được **GITIGNORE** (config per-user).
- `archive/`: **COMMIT** (lịch sử episodic theo ticket).
- `active/`: **GITIGNORE** (context tạm, per-session, không nên commit).
