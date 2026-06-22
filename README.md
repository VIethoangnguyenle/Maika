<p align="center">
  <img src="docs/assets/maika-banner-new.png" alt="Maika — The OS for Your Coding Agent" width="900">
</p>

<div align="center">
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-MIT-b0e8ff?style=flat-square&labelColor=0a0e14" alt="license"></a>
  <img src="https://img.shields.io/badge/python-3.10+-b0e8ff?style=flat-square&labelColor=0a0e14&logo=python&logoColor=white" alt="python">
  <img src="https://img.shields.io/badge/PRs-welcome-b0e8ff?style=flat-square&labelColor=0a0e14" alt="PRs welcome">
  <img src="https://img.shields.io/badge/platforms-Antigravity%20·%20Codex%20·%20Claude%20Code-9d7bff?style=flat-square&labelColor=0a0e14" alt="platforms">
</div>
<br>

> **Maika v3.0** biến AI coding agent từ một cửa sổ chat biết viết code thành một worker có **bộ nhớ**, **workflow**, **guardrails**, và **audit trail**.

AI agent rất giỏi sinh code. Vấn đề là nó thường quên: requirement cũ, quyết định kiến trúc, naming convention, blast radius, và cả lý do vì sao hôm qua bạn bảo nó không được làm một điều gì đó.

Maika là một protocol runtime cho repo phần mềm: nó scaffold một bộ file hướng dẫn, skills, workflows, rules, tools và knowledge layer để agent làm việc theo pha, dựa trên bằng chứng, và tích lũy tri thức qua nhiều phiên.

```txt
Memory + Workflow + Guardrails = Agent làm việc có kỷ luật
```

---

## 🎁 Bạn nhận được gì?

- 💾 **Persistent memory**: requirement, explore context, architecture snapshot, conventions, author DNA và archive được lưu thành file trong repo.
- 🚦 **Phase-gated workflow**: agent đi qua `Ideation -> Requirement -> Architecture -> Spec -> Apply`, không nhảy thẳng vào code.
- 🔍 **Knowledge-first reasoning**: quyết định kỹ thuật dựa trên code, DB, docs và knowledge graph thay vì trí nhớ ngắn hạn.
- 🛡️ **Guardrails có cấu trúc**: rules về flow, tool permission, PII, cost budget, convention, teaching moments và human confirmation.
- 🧩 **Multi-platform runtime**: render vào root native cho Antigravity, Codex, Claude Code hoặc generic `AGENTS.md`.
- 🔄 **Update an toàn**: framework-owned files được re-render, còn project knowledge và persona của bạn được giữ lại.

Maika không thay thế Claude, Codex, Cursor, Gemini hay bất kỳ AI coding agent nào. Nó là **hệ điều hành làm việc** để các agent đó đọc và tuân theo trong repo của bạn.

---

## 🚀 Quickstart

### 1. Cài Maika vào một dự án

```bash
git clone https://github.com/VIethoangnguyenle/Maika.git maika
cd maika

./install.sh /path/to/your-project
```

Installer sẽ:

1. Tạo virtualenv riêng tại `.venv/`.
2. Hỏi platform: Antigravity, Claude Code, Codex CLI hoặc Generic.
3. Hỏi MCP servers: Codebase Memory, Confluence, DB Remote nếu bạn có.
4. Hỏi ngôn ngữ chính: Java, TypeScript, Python, Go, C# hoặc other.
5. Render Maika runtime vào framework root phù hợp với platform.

Nếu target project đã có Maika, cùng lệnh trên sẽ route sang `update` thay vì `init`.

```bash
./install.sh /path/to/your-project
```

Muốn đổi platform hoặc MCP sau này:

```bash
.venv/bin/python -m cli.maika update --target /path/to/your-project --reconfigure
```

Maika giữ nguyên các file user-owned trong `knowledge/long-term/` và `knowledge/active/`. Quy tắc sở hữu file đầy đủ nằm ở [docs/maika-file-ownership-policy.md](docs/maika-file-ownership-policy.md).

### 2. Tuỳ chỉnh persona

Chọn đúng framework root theo platform:

```bash
# Antigravity hoặc Codex
cp .agents/knowledge/long-term/persona.template.yaml .agents/knowledge/long-term/persona.yaml

# Claude Code
cp .claude/knowledge/long-term/persona.template.yaml .claude/knowledge/long-term/persona.yaml

# Generic
cp .maika/knowledge/long-term/persona.template.yaml .maika/knowledge/long-term/persona.yaml
```

Sau đó sửa `persona.yaml` theo phong cách tương tác mong muốn. File này là per-developer và được gitignore.

### 3. Onboard codebase hiện có

Trong AI agent đã đọc Maika runtime:

```txt
/convention-scan
/approve-conventions

/dna-scan
/approve-dna
```

Hai flow này tạo:

- `conventions.yaml`: naming, structure, upstream constraints và design patterns đã được approve.
- `author-dna.yaml`: judgment layer về triết lý code của tác giả hoặc team.

Muốn xem một `author-dna.yaml` đã điền đầy trông thế nào, xem [docs/examples/author-dna-cleancode.yaml](docs/examples/author-dna-cleancode.yaml).

### 4. Bắt đầu một task

```txt
/task Thêm giới hạn số lệnh giao dịch mỗi ngày theo nhân viên

/task https://jira.example.com/browse/ABC-123

/task spec ABC-123

/task apply ABC-123
```

Agent sẽ tạo hoặc cập nhật các artifact trong `knowledge/active/`, log assumption/tool call vào `AGENT_TRANSPARENCY.md`, rồi archive context khi task hoàn thành.

---

## 🤔 Vì sao Maika tồn tại?

AI coding agent thường fail không phải vì không biết syntax. Nó fail vì thiếu state.

| Failure mode | Khi không có Maika | Với Maika |
|---|---|---|
| Quên context phiên trước | Quyết định kiến trúc biến mất sau khi chat reset | `knowledge-snapshot.md` và archive giữ lại tri thức |
| Code quá sớm | Agent nhảy vào diff khi requirement còn mơ hồ | `/task` buộc đi qua requirement và exploration |
| Không nhớ convention | Naming và pattern phụ thuộc trí nhớ ngắn hạn | `conventions.yaml` và `author-dna.yaml` làm source of truth |
| Không biết blast radius | Sửa một file nhưng bỏ qua module phụ thuộc | `codebase-explorer`, KG/MCP và architecture review tạo evidence |
| Không audit được | Không rõ agent đã giả định gì | `AGENT_TRANSPARENCY.md` ghi tool call, confidence, blocker và decision |
| Dễ làm mất tri thức | Bài học từ review chỉ nằm trong chat | teaching moments được capture vào knowledge layer |

Thesis của Maika: **agent đáng tin hơn khi project knowledge sống trong repo, workflow có phase gate, và mọi hành động quan trọng để lại dấu vết.**

---

## 🧩 Mental Model

Maika có 3 lớp chính.

### 1. Runtime Protocol

Các file agent đọc để biết phải làm việc thế nào:

- `AGENTS.md`, `CLAUDE.md` hoặc entry point tương ứng platform.
- `rules/*.md`: flow, tool, data, cost, knowledge, guard rules.
- `workflows/*.md`: `/task`, `/idea-to-task`, `/convention-scan`, `/dna-scan`, OpenSpec flows.
- `skills/*/SKILL.md`: hướng dẫn theo vai trò.
- `procedures/*.md`: bootstrap, context-loader, context-compressor, token tracking.

### 2. Knowledge Layer

Tri thức sống cùng repo:

- `active/`: working memory cho task hiện tại.
- `long-term/`: knowledge snapshot, conventions, author DNA, persona.
- `archive/`: context đã hoàn thành theo ticket.
- `templates/`: skeleton chuẩn để reset hoặc tạo artifact mới.

### 3. Tooling Layer

Các công cụ hỗ trợ runtime:

- `skill-lint`: validate skill schema.
- `rule-projector`: project rule có thể check cơ học.
- `gate-check`: kiểm phase chain, knowledge checkpoint, handoff slice.
- `microloop-orchestrator`: điều phối contract DAG cho apply phase phức tạp.
- CLI `maika init/update/status`: scaffold, re-render, kiểm trạng thái install.

---

## 🔄 Workflow chính

Maika áp dụng một flow bắt buộc cho task thực tế:

```txt
Ideation -> Requirement -> Architecture -> Spec -> Apply
    |            |              |          |       |
 ideation     REQUIREMENT   EXPLORE     OpenSpec  code
 draft        .md           _CONTEXT    change    diff
                            .md
```

Mỗi pha có artifact riêng:

| Pha | Mục tiêu | Artifact |
|---|---|---|
| Ideation | Biến ý tưởng thô thành phạm vi task | `active/ideation/ideation-*.md` |
| Requirement | Chuẩn hoá yêu cầu, AC, risk, assumption | `active/REQUIREMENT.md` |
| Architecture | Khám phá DB/code/flow, phát hiện rủi ro | `active/EXPLORE_CONTEXT.md` |
| Spec | Sinh spec kỹ thuật và OpenSpec change | `openspec/changes/<id>/` |
| Apply | Apply spec vào code có checkpoint và review | code diff + transparency log |

Rule quan trọng: `/task apply` chỉ được đi tiếp khi spec đã có, architecture blocker đã resolve, và user đã confirm.

---

## 📂 Kiến trúc thư mục

Maika render runtime trực tiếp vào framework root của platform đã chọn:

| Platform | Framework root | Entry point |
|---|---|---|
| Antigravity | `.agents/` | `AGENTS.md` |
| Codex CLI | `.agents/` | `AGENTS.md` |
| Claude Code | `.claude/` | `CLAUDE.md` |
| Generic | `.maika/` | `AGENTS.md` |

Layout sau khi scaffold:

```txt
project-root/
|
├── AGENTS.md / CLAUDE.md              # Entry point agent đọc đầu tiên
|
└── {framework_root}/
    ├── knowledge/
    │   ├── active/
    │   │   ├── REQUIREMENT.md
    │   │   ├── EXPLORE_CONTEXT.md
    │   │   ├── AGENT_TRANSPARENCY.md
    │   │   ├── TOKEN_LOG.md
    │   │   └── ideation/
    │   ├── long-term/
    │   │   ├── knowledge-snapshot.md
    │   │   ├── conventions.yaml
    │   │   ├── author-dna.yaml
    │   │   ├── persona.template.yaml
    │   │   └── persona.yaml
    │   ├── archive/
    │   └── templates/
    ├── rules/
    ├── skills/
    ├── workflows/
    ├── procedures/
    ├── tools/
    ├── profiles/
    └── resolved-config.yaml
```

---

## 🛠️ Skills

Maika ship một bộ skill module hoá theo vai trò.

| Skill | Vai trò | Khi nào dùng |
|---|---|---|
| `requirement-analyst` | Chuẩn hoá yêu cầu | Khi nhận ticket/task mới |
| `spec-extract` | Trích xuất spec từ docs | Khi input là wiki, PRD, Confluence |
| `db-explorer` | Khám phá DB read-only | Khi task chạm schema, config, data |
| `codebase-explorer` | Map yêu cầu sang codebase | Sau requirement hoặc DB exploration |
| `architecture-reviewer` | Review boundary, coupling, risk | Trước khi sinh spec |
| `knowledge-curator` | Archive và cập nhật knowledge | Sau task hoặc khi có teaching moment |
| `convention-intelligence-builder` | Quét convention codebase | Khi onboard hoặc sau refactor lớn |
| `author-dna-builder` | Encode judgment layer | Khi cần style/philosophy của tác giả |
| `spec-validator` | Validate spec trước/sau apply | Trước và sau thay đổi code |
| `infra-tdd` | Technical Design Document 5 tầng | Khi thay đổi ảnh hưởng kiến trúc/hạ tầng |
| `document-writer` | Viết tài liệu kỹ thuật | README, ADR, architecture docs |
| `openspec-*` | Tích hợp OpenSpec | Explore, propose, archive change |

---

## ⚡ Workflows

| Command | Mục đích |
|---|---|
| `/task <input>` | Pha 1: hiểu vấn đề, chuẩn hoá requirement, explore context |
| `/task spec <ticket>` | Pha 2: sinh spec kỹ thuật |
| `/task apply <ticket>` | Pha 3: apply spec vào code |
| `/idea-to-task` | Chuyển ideation thành draft ticket |
| `/index-source` | Index codebase cho semantic search |
| `/convention-scan` | Quét convention codebase |
| `/approve-conventions` | Promote `conventions.draft.yaml` thành `conventions.yaml` |
| `/dna-scan` | Quét và encode author DNA |
| `/approve-dna` | Promote `author-dna.draft.yaml` thành `author-dna.yaml` |
| `/tdd <module>` | Sinh Technical Design Document |
| `/opsx-explore` | OpenSpec explore mode |
| `/opsx-propose` | Tạo proposal/design/tasks/spec delta |
| `/opsx-apply` | Implement từ OpenSpec change |
| `/opsx-archive` | Archive OpenSpec change đã xong |

---

## 🛡️ Rules và Guardrails

Maika không chỉ là một bộ prompt. Nó là rule system có manifest và sub-files:

| Rule group | Bảo vệ điều gì |
|---|---|
| Flow rules | Không bỏ qua `/task`, không apply khi chưa có spec |
| Tool rules | DB read-only, code write qua spec/apply, memory MCP có boundary |
| Data rules | Không log PII, credential, token vào context files |
| Architecture rules | Confidence kiến trúc phụ thuộc evidence từ code/DB/tools |
| Execution rules | Budget tool call theo phase, hardstop khi loop |
| Knowledge rules | Archive, source-of-truth priority, stale convention gates |
| Guard rules | Precondition check, knowledge-before-code checkpoint, teaching moment capture |

Các rule quan trọng được đánh dấu `[CRITICAL]`; rule nền hoặc tham khảo được đánh dấu `[REFERENCE]`.

---

## 🔌 MCP Integration

Maika resolve tool names tại scaffold time. Khi bạn chạy `maika init`, CLI render skill/workflow với tool name đúng cho platform và MCP bạn chọn.

| MCP server | Capability | Khi nào cần |
|---|---|---|
| Codebase Memory | Knowledge graph + semantic search, dependency graph, symbol analysis (single binary, MIT) | Hầu hết dự án có codebase lớn |
| Understand Anything | Knowledge graph code-exploration — **bổ trợ** Codebase Memory (semantic) | Dùng cùng Codebase Memory để hiểu codebase sâu hơn |
| Confluence | Wiki/document search | Dự án có docs trên Confluence |
| DB Remote | Database schema exploration read-only | Dự án có DB cần khám phá |

Nếu thêm hoặc bỏ MCP sau này:

```bash
.venv/bin/python -m cli.maika update --target /path/to/your-project --reconfigure
```

### MCP Doctor

Sau khi chọn MCP lúc `maika init` hoặc `maika update --reconfigure`, chạy:

```bash
.venv/bin/python -m cli.maika doctor mcp --target /path/to/your-project
```

Doctor kiểm tra config MCP native của Codex, Claude Code, hoặc Antigravity, ghi
`mcp-doctor-report.md`, và thử bridge fallback khi native MCP không khả dụng.
Doctor không sửa config trừ khi bạn chạy:

```bash
.venv/bin/python -m cli.maika doctor mcp --target /path/to/your-project --fix
```

---

## 📊 Dashboard Control Tower

Maika có dashboard local để quan sát agent chính, micro-loop và subagent theo thời gian thực.
Dashboard đọc các runtime artifact trong `knowledge/active/` và serve UI qua SSE, bind local
ở `127.0.0.1`.

### Chạy dashboard

Đăng ký project cần theo dõi:

```bash
.venv/bin/python -m cli.maika dashboard register --path /path/to/your-project
```

Mở dashboard:

```bash
.venv/bin/python -m cli.maika dashboard serve --target /path/to/your-project --port 7077
```

Mở trong browser:

```text
http://127.0.0.1:7077/
```

Không mở browser tự động:

```bash
.venv/bin/python -m cli.maika dashboard serve --target /path/to/your-project --no-browser
```

In snapshot một lần trong terminal:

```bash
.venv/bin/python -m cli.maika dashboard --target /path/to/your-project
```

### Parent brain

Dashboard hiển thị `parent brain` riêng với subagent prompt/result. Đây là mirror đọc được
của IDE brain hoặc cuộc trò chuyện với human, lưu tại:

```text
{framework_root}/knowledge/active/PARENT_BRAIN.md
```

Với Antigravity, có thể sync best-effort từ local brain artifacts:

```bash
.venv/bin/python -m cli.maika dashboard sync-brain --target /path/to/your-project --brain-platform antigravity
```

Nếu Antigravity chưa ghi text artifact cho conversation hiện tại, lệnh sẽ báo không sync và
không đè `PARENT_BRAIN.md` hiện có.

### Dashboard đọc gì?

| Artifact | Vai trò |
|---|---|
| `AGENT_TRANSPARENCY.md` | phase, ticket, confidence, trạng thái tổng |
| `PARENT_BRAIN.md` | context trực quan của agent cha từ IDE brain/conversation |
| `microloop/TASK_QUEUE.md` | task list, status, progress `x/N` |
| `TASK_HANDOFF.*.md` | prompt/handoff từng subagent nhận |
| `microloop/TASK_RESULT.*.md` | kết quả từng subagent hoặc node |
| `microloop/ACTIVITY_LOG.jsonl` | timeline append-only cho parent và subagent |

Dashboard chỉ đọc các file này khi serve. Việc sync parent brain là một command explicit riêng.

### Troubleshooting

**Vì sao progress là 0%?**

Nếu chưa có `microloop/TASK_QUEUE.md`, dashboard không có mẫu số `N` để tính progress. Trong
trạng thái này UI sẽ hiển thị phase-only hoặc `waiting for microloop TASK_QUEUE`.

**Vì sao thấy subagent nhưng không thấy progress?**

Có `TASK_HANDOFF.*.md` nhưng chưa có `TASK_QUEUE.md`. Đây là handoff-only transitional state.
Pha 3 chuẩn phải tạo queue trước khi dispatch subagent.

**Vì sao parent brain trống?**

Chưa có `PARENT_BRAIN.md`, hoặc IDE adapter chưa sync được conversation. Với Antigravity, chạy
`dashboard sync-brain`; nếu không có text artifacts, tạo mirror thủ công hoặc chờ runtime ghi
brain artifact.

**Vì sao dashboard đánh dấu stale?**

Một artifact bị malformed, ví dụ YAML lỗi trong `TASK_QUEUE.md` hoặc JSONL lỗi trong
`ACTIVITY_LOG.jsonl`. UI vẫn render project khác và hiển thị path lỗi.

**Làm sao verify SSE?**

Chạy dashboard rồi gọi endpoint:

```bash
curl -N http://127.0.0.1:7077/events
```

Message đầu tiên phải bắt đầu bằng `data: [` và chứa snapshot hiện tại.

### Manual acceptance checklist

- `maika dashboard serve` mở UI local.
- `/api/runs` trả JSON snapshot.
- `/events` gửi snapshot đầu tiên ngay khi connect.
- Project không có active run hiển thị idle.
- Project có `TASK_QUEUE.md` hiển thị progress thật `x/N`.
- Subagent card hiển thị prompt và result drawer khi artifact tồn tại.
- Parent brain panel hiển thị khi có `PARENT_BRAIN.md`.
- Malformed queue/log không làm sập dashboard; UI hiển thị stale/error.

---

## ♻️ Knowledge Lifecycle

```txt
Task active
|
|-- REQUIREMENT.md
|-- EXPLORE_CONTEXT.md
|-- AGENT_TRANSPARENCY.md
|-- TOKEN_LOG.md
|
|  /task spec
|  /task apply
v
Task complete
|
|-- knowledge-curator archives active context
|-- knowledge-snapshot.md gets new architecture facts
|-- conventions.yaml may be marked stale after refactor
|-- active/ resets to templates
v
Next task starts smarter
```

Long-term stores:

| Store | Chứa gì | Có commit không? |
|---|---|---|
| `knowledge-snapshot.md` | Bản đồ kiến trúc, module, table, rule, entry point | Có |
| `conventions.yaml` | Naming, structure, upstream constraints | Có |
| `author-dna.yaml` | Philosophy, preference, judgment principles | Có |
| `persona.yaml` | Tone và interaction preference của từng developer | Không, gitignored |
| `archive/{ticket-id}/` | Snapshot context của task đã xong | Tuỳ policy repo |

---

## 📋 Ví dụ Bootstrap Report

Khi agent bắt đầu một session trong repo có Maika, nó bootstrap context và báo trạng thái:

```txt
Core: AGENTS.md v3.0 + RULES (manifest + flow/tool/exec/knowledge/guard)
Skills: requirement-analyst | spec-extract | db-explorer | codebase-explorer | ...
Workflows: /task | /idea-to-task | /index-source | /convention-scan | /dna-scan
Platform: codex | MCPs: codebase-memory-mcp, db-remote
Active context: REQUIREMENT empty | EXPLORE_CONTEXT empty
Author DNA: approved
Archive: 3 tickets
Ready for task
```

---

## 🎯 Thiết kế đúng ở đâu?

Maika cam kết 4 thuộc tính:

1. **Generic**: framework ship protocol và skeleton, không ship business logic của dự án cụ thể.
2. **Knowledge-first**: reasoning đi qua memory hierarchy và evidence, không dựa vào short-term chat.
3. **Long-term memory**: tri thức sống và tiến hoá trong repo qua mỗi task.
4. **IDE/agent-independent**: workflow phụ thuộc capability trừu tượng, không khoá vào một agent duy nhất.

Nguyên tắc vận hành:

- **Flow trước tự do**: phase gate chặn code vội.
- **Evidence trước opinion**: DB/code/docs/KG đi trước kết luận.
- **Human-in-the-loop**: apply quan trọng cần user confirm.
- **Transparency by default**: assumption, blocker, tool call và confidence được log.
- **Convention as data**: naming và design preference được encode thành file.
- **Teaching moment capture**: bài học từ review được đưa vào persistent knowledge.

---

## ❓ FAQ

### Có dùng được cho repo private hoặc enterprise không?

Có. Maika là protocol layer; nó không cần chứa code ứng dụng. Bạn scaffold vào repo private, sau đó knowledge layer được tạo và quản lý trong chính repo đó.

### Maika có thay thế AI coding agent hiện tại không?

Không. Maika bổ sung memory, workflow và rules cho agent hiện có. Agent vẫn là Claude, Codex, Cursor, Gemini hoặc tool bạn chọn.

### Nếu tool của tôi không hỗ trợ `AGENTS.md` thì sao?

Dùng platform adapter nếu có. Nếu chưa có adapter, chọn `generic` để scaffold `AGENTS.md`, hoặc tạo pointer file cho tool của bạn trỏ về entry point đó.

### Làm sao tránh rò rỉ dữ liệu nhạy cảm?

Rules R-Data-1/R-Data-2 cấm log PII, credential, token vào context files. `db-explorer` chỉ được đọc schema/sample data giới hạn và không được thay đổi DB.

### Team nhiều người dùng chung được không?

Có. Knowledge chung như `knowledge-snapshot.md`, `conventions.yaml`, `author-dna.yaml` có thể version-controlled. `persona.yaml` là per-developer và được gitignore.

### Dự án mới tinh, chưa có code thì sao?

Vẫn dùng được. Chọn platform và MCP bạn có. Khi codebase bắt đầu hình thành, chạy `/index-source`, `/convention-scan`, và `/dna-scan` để enrich knowledge layer.

### Có thêm platform custom được không?

Có. Thêm platform trong `cli/platforms/`, implement `BasePlatform`, rồi đăng ký trong `cli/platforms/__init__.py`.

### Maika có bắt buộc dùng OpenSpec không?

Runtime hiện có tích hợp OpenSpec cho propose/apply/archive. Các workflow Maika vẫn tách rõ requirement, exploration, architecture review và knowledge lifecycle để giữ context trước khi đi vào OpenSpec change.

---

## 🔧 Development

Chạy test CLI:

```bash
python3 -m pytest cli/tests
```

Chạy skill lint:

```bash
python3 .maika/tools/skill-lint/validate_skills.py
```

Package metadata nằm trong [pyproject.toml](pyproject.toml). Manifest scaffold nằm trong [cli/plugin-manifest.yaml](cli/plugin-manifest.yaml).

---

## 🤝 Contributing

Đóng góp được chào đón:

1. Fork repository.
2. Tạo feature branch.
3. Chạy test liên quan.
4. Gửi pull request với mô tả rõ scope và validation.

Khi thay đổi runtime `.maika/`, ưu tiên giữ instruction ngắn, portable, action-oriented và tránh rationale lịch sử trong file clone sang dự án khác.

---

## 📄 License

MIT License. Xem [LICENSE](LICENSE).

---

<div align="center">

### 🧠 _Maika giúp agent không chỉ viết code, mà làm việc như một thành viên có trí nhớ của team._

<sub>Memory · Workflow · Guardrails · Audit trail</sub>

⭐ Thấy hữu ích? Star repo để ủng hộ Maika!

</div>
