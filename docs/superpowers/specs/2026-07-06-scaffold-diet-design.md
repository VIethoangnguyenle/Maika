# Scaffold Diet — chỉ mang sang downstream những gì có consumer

- **Ngày**: 2026-07-06
- **Trạng thái**: APPROVED (audit 2026-07-06, user chốt triển khai)
- **Nhánh**: `refactor/scaffold-diet`
- **Plan**: `docs/superpowers/plans/2026-07-06-scaffold-diet.md`

## 1. Bối cảnh — audit 2026-07-06

Rà soát toàn bộ tool được scaffold sang project downstream, đối chiếu từng entry manifest
với **consumer cơ học** (lệnh gọi thực trong rules/skills/workflows/procedures được scaffold).
Kết quả:

| Tool | Consumer downstream | Kích thước | Trong đó `tests/` |
|---|---|---|---|
| gate-check | >10 lệnh gọi (rules-guard/flow/tool, task.md, spec-validator, knowledge-curator, decision-gate, write-gate) | 300K | 228K |
| rule-projector | rules-guard.md:76, approve-dna.md, author-dna-builder, snapshot-promotion | 208K | 92K |
| microloop-orchestrator | task.md:56/397/421 | 536K | 336K |
| mcp-bridge | rules-tool.md §Bridge fallback | 40K | 0 |
| skill-lint | **chỉ** R-Skill-2 (rules-knowledge.md) + meta-prompt.md:252 — hoạt động authoring skill là việc **framework-dev**, không phải downstream | 168K | 100K |
| knowledge-index | **0 lệnh gọi** — mọi ref là tới *file* `knowledge-index.yaml`; WARN ở bootstrap/context-loader bảo "chạy generator" nhưng không có lệnh cụ thể | 52K | 28K |

Phát hiện thêm:

1. **`tests/` + fixtures của framework bị ship nguyên** (~784K/1.3M ≈ 60% payload tools),
   kèm `hooks/write-gate/tests/`. Không có file downstream nào chạy chúng — đây là CI
   của repo framework.
2. **Broken ref chiều thiếu**: `skills/skill-index.yaml` được `bootstrap.md:63` +
   `meta-prompt.md:88` READ ở downstream nhưng **không được scaffold** (manifest chỉ copy
   từng skill dir; file này nằm ở gốc `skills/`).
3. **Broken ref thiếu #2**: meta-prompt.md:61 trỏ "(xem tools/README.md)" nhưng
   `tools/README.md` không được scaffold.
4. Doctrine đã có sẵn hướng này: `2026-07-05-skill-lint-pilot-design.md` chốt
   "lint = pytest tại `cli/tests/`, KHÔNG scaffold xuống downstream (R7)".

## 2. Quyết định

### D1 — Exclude `tests` khỏi mọi `copy_dir` scaffold

Thêm `"tests"` vào **exclude list mặc định** của `copy_and_render_directory`
(`cli/renderer.py:112-119`) — mở rộng chốt chặn đang chạy (R5), không thêm field manifest
mới (R7). Đã verify: trong `.maika/` chỉ `tools/*/tests` và `hooks/write-gate/tests`
là dir tên `tests` — không có dir `tests` hợp lệ nào cần ship.

Hệ quả: `tools/README.md` phải sửa các dòng "**Test**: pytest {{ root }}/tools/…/tests/"
→ ghi rõ test chạy trong repo framework (`.maika/tools/…/tests/`).

### D2 — Cắt `skill-lint` khỏi manifest

Xóa entry `skill-lint` (manifest dòng 325-330). Tool ở lại `.maika/tools/skill-lint/`
cho framework-dev. Sửa các ref ship xuống downstream để khỏi thành broken ref:

- `rules-knowledge.md` R-Skill-2: đường dẫn đổi từ
  `{{ platform.framework_root }}/tools/skill-lint/…` → literal `.maika/tools/skill-lint/…`
  kèm chú thích "(repo framework — tool không scaffold sang downstream)".
- `meta-prompt.md:252`: tương tự.
- `meta-prompt.md:60-61` + `tools/README.md` §skill-lint, §skill-index: đánh dấu
  framework-repo-only.

Căn cứ: skills downstream là framework-owned (bị `maika update` ghi đè) → authoring/lint
là hoạt động repo framework; đồng hướng skill-lint-pilot design (R7).

### D3 — Giữ `knowledge-index` downstream, wire lệnh gọi tường minh

Không cắt, vì có failure mode thật (R3): `approve-dna` / `approve-conventions` thay đổi
`author-dna.yaml` / `conventions.yaml` **ở downstream** → `knowledge-index.yaml` stale
cho tới lần `maika update` kế (init/update đã generate framework-side từ commit `3587f02`).
Trạng thái "giữ tool nhưng không ai gọi" là nửa vời — chọn wire:

- `approve-dna.md` Bước 3 + `approve-conventions.md` Bước 3: thêm bước regenerate index
  sau khi promote draft → approved.
- WARN tại `bootstrap.md:133`, `context-loader.md:34`, `context-loader.md:38`: kèm lệnh
  chính xác thay vì "chạy knowledge-index generator" chung chung.

Lệnh chuẩn (đã verify `generate_index.py::main` nhận argv[0] = long-term dir):

```
python3 {{ platform.framework_root }}/tools/knowledge-index/generate_index.py {{ platform.framework_root }}/knowledge/long-term
```

### D4 — Ship `skills/skill-index.yaml`

Thêm entry manifest (type: `skill`, single-file, không `copy_dir`). Native skill export
tự skip vì file không có frontmatter `---` (đã verify `scaffold_native_skill_exports`
đọc dòng đầu). Consumer: `bootstrap.md:63` READ.

### D5 — Ship `tools/README.md`

Thêm entry manifest (type: `tool`, single-file). Consumer: meta-prompt.md:61.
File chứa `{{ platform.framework_root }}` → auto-render theo cơ chế sẵn có
(`scaffold_plugin`, `.md` + chứa `{{ `). Nội dung cập nhật theo D1/D2.

## 3. Ngoài scope (ghi nhận, không làm đợt này)

- **prune_orphans không dọn dir mồ côi**: sau D1/D2, project downstream *hiện hữu* chạy
  `maika update` vẫn giữ lại `tools/*/tests/` cũ và `tools/skill-lint/` nguyên dir —
  `prune_orphans` chỉ xóa *file* trong dir mà staging có ghi (`cli/scaffold.py:419-455`);
  dir không còn trong staging thì thoát scope. Theo R3, đợi quan sát thực tế trước khi
  mở rộng prune sang dir. Follow-up candidate.
- Full P2.1 capability-resolution (đang gate trên P1.1) — không liên quan.

## 4. Checklist DEVELOPMENT_RULES

- **R1**: mọi entry thêm (skill-index-data, tools-readme) có consumer dẫn chứng ở §2.
- **R3**: D3 wire theo failure mode stale-index có thật; không dựng gate mới.
- **R5**: D1 mở rộng exclude-list sẵn có, không thêm cơ chế song song.
- **R6**: `tools/README.md` + meta-prompt sửa ngay trong PR này (không để doc mô tả sai).
- **R7**: diff downstream âm mạnh (~880K, ~95 file bớt đi; thêm 2 file nhỏ).
