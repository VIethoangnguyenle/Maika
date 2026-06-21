# UA (Understand-Anything) — Tích hợp vào `maika init` — Design

> **Status**: Draft
> **Ngày**: 2026-06-21
> **Phạm vi**: Thêm cơ chế *detect → wire → guide → verify* cho Understand-Anything vào CLI Maika (`cli/`, `cli/plugin-manifest.yaml`). Framework-dev → tuân `.maika/DEVELOPMENT_RULES.md`.
> **Liên quan**: [[amap-framework-generic-boundary]], [[amap-c27-memory-tool-templating]] (tiền lệ MCP-only boundary), [[amap-framework-dev-rules]].

---

## 1. Bối cảnh & vấn đề

Người dùng dùng Understand-Anything (UA) làm knowledge-graph backend cho repo. Quy trình thực tế:

1. **Cài engine** Understand-Anything (Egonex-AI) — plugin marketplace (claude-code) hoặc `install.sh <platform>` (codex/antigravity).
2. **Gen graph**: chạy `/understand` → sinh `.understand-anything/knowledge-graph.json` trong repo.
3. **Wire MCP**: chạy Understand-Anything-MCP (server `uv run server.py`) trỏ `PROJECT_ROOTS` vào repo để agent trace graph.

Hiện `maika init` mới có `understand-anything` như một **display string** chọn được (`plugin-manifest.yaml`); init **không** emit cấu hình MCP, **không** hướng dẫn, **không** verify graph/engine. Người dùng phải tự nhớ toàn bộ 3 bước trên mỗi dự án.

**Đòn bẩy với Maika:** UA-MCP có tool `find_impact` (= **blast-radius**, BFS ngược) và `get_node_detail` (= **node_id**) — đúng hai token mà `validate_knowledge_checkpoint` (`gates.py`) đòi để pass knowledge-before-code gate ở mức cao nhất (thay vì degrade "KG unavailable — grep fallback"). Wire UA tử tế nâng chất lượng gate, không chỉ là tiện ích.

## 2. Mục tiêu

- `maika init`: khi chọn UA → emit snippet `mcpServers` paste-ready (đã thay placeholder) + checklist 3 bước.
- `maika doctor mcp`: verify 3 tầng — engine đã cài? graph đã gen? MCP đã wire? — cho **claude-code, codex, antigravity**.
- Tất cả **data-driven qua manifest**, không hard-code path/giá trị trong Python.

### Non-goals (và vì sao)

| Không làm | Lý do |
|-----------|-------|
| init tự cài UA engine | `/understand` là agent-driven slash-command, không shell-out được; giữ boundary "reference, don't bundle". |
| init tự ghi vào MCP config của agent (`~/.claude.json`, codex toml) | Lệch pattern hiện tại (doctor chỉ diagnose); blast lớn, đa định dạng. Chỉ emit snippet paste-ready. |
| Hỗ trợ ngoài 3 platform claude-code/codex/antigravity | Phạm vi user yêu cầu; `default` engine_check phủ thêm install.sh-path nhưng không test riêng. |

## 3. Bằng chứng cơ chế đã verify (DEVELOPMENT_RULES R4)

Mọi trigger dưới đây đã được kiểm trên nguồn thật, không giả định:

| Cơ chế | Nguồn | Giá trị |
|--------|-------|---------|
| Graph artifact | README Understand-Anything | `.understand-anything/knowledge-graph.json` |
| Gen command | README | `/understand` (multi-agent, agent-driven) |
| MCP server recipe | README Understand-Anything-MCP | `uv --directory <dir> run server.py`, env `PROJECT_ROOTS` |
| Server name | README MCP (`mcpServers.understand-anything`) | khớp manifest key `understand-anything` (không lệch như tiền lệ agentmemory) |
| Engine marker — codex | `install.sh` platforms_table | symlink `~/.agents/skills/understand` |
| Engine marker — antigravity | `install.sh` platforms_table | symlink `~/.gemini/antigravity/skills/understand-anything` |
| Engine marker — default | `install.sh` (`REPO_DIR`) | `~/.understand-anything/repo` |
| Engine marker — claude-code | máy thật `~/.claude/plugins/installed_plugins.json` | file chứa key prefix `understand-anything@` |

> claude-code cài qua marketplace (KHÔNG qua install.sh) nên không tạo `~/.understand-anything/repo`; marker riêng là registry plugin của Claude.

## 4. Thiết kế

### 4.1 — Manifest: khối `setup` (generic, optional)

Mở rộng entry `understand-anything` trong `cli/plugin-manifest.yaml`. `setup` là field **optional dùng chung** cho mọi `mcp_capabilities`; chỉ UA khai trong PR này (R1: có consumer = emitter + doctor). Là *data*, không phải logic Python (tuân generic-boundary).

```yaml
mcp_capabilities:
  understand-anything:
    provides: code_exploration
    display: "Understand Anything — Knowledge Graph (alternative to Socraticode)"
    setup:
      graph_artifact: ".understand-anything/knowledge-graph.json"
      generate_cmd: "/understand"
      engine_check:
        claude-code: { kind: file_contains, path: "{home}/.claude/plugins/installed_plugins.json", needle: "understand-anything@" }
        codex:       { kind: path_exists,   path: "{home}/.agents/skills/understand" }
        antigravity: { kind: path_exists,   path: "{home}/.gemini/antigravity/skills/understand-anything" }
        default:     { kind: path_exists,   path: "{home}/.understand-anything/repo" }
      install_hint:
        claude-code: "/plugin marketplace add Egonex-AI/Understand-Anything → /plugin install understand-anything"
        default:     "curl -fsSL https://raw.githubusercontent.com/Egonex-AI/Understand-Anything/main/install.sh | bash -s {platform}"
      server:
        command: "uv"
        args: ["--directory", "{ua_mcp_dir}", "run", "server.py"]
        env: { PROJECT_ROOTS: "{project_root}" }
```

**Placeholder** (thay lúc render): `{home}`, `{platform}`, `{ua_mcp_dir}`, `{project_root}`.
**`engine_check.kind`** chỉ 2 loại: `path_exists` (file/symlink tồn tại) và `file_contains` (file tồn tại + chứa `needle`). Resolver chọn `engine_check[platform]`, fallback `default`.

### 4.2 — init: lấy `ua_mcp_dir` + emit `MCP_SETUP.md`

Khi `understand-anything ∈ selected_mcps`:

1. **Lấy `ua_mcp_dir`** theo thứ tự: flag `--ua-mcp-dir <path>` → prompt interactive ("Đường dẫn tuyệt đối tới clone Understand-Anything-MCP? (Enter để chèn placeholder)") → nếu `--yes` không cung cấp: placeholder `<PATH_TO_Understand-Anything-MCP>` + WARN.
2. **Render** `server` recipe: `{ua_mcp_dir}` ← trả lời, `{project_root}` ← abs path target.
3. **Ghi `<framework_root>/MCP_SETUP.md`** (chỉ tạo khi có mcp nào mang `setup`). Nội dung: §4.4.

`ua_mcp_dir` thêm vào chữ ký `resolve_init_choices` / `run_init` và CLI arg `--ua-mcp-dir` ở `cli/maika.py`.

### 4.3 — init: mở rộng "Next steps"

- "Next steps" print: nếu UA selected, thêm dòng trỏ `MCP_SETUP.md` + `maika doctor mcp`.
- `resolved-config.yaml` **không đổi schema**: doctor đã đọc `mcps` từ đó, và load manifest (§4.5) cho phần còn lại — không nhân đôi `graph_artifact` vào resolved-config (R7).

### 4.4 — `MCP_SETUP.md` (artifact sinh ra)

```markdown
# MCP Setup — understand-anything

## 1. Cài engine (nếu chưa)
<install_hint[platform]>

## 2. Gen knowledge graph
Chạy: /understand   → sinh .understand-anything/knowledge-graph.json

## 3. Wire MCP server (paste vào MCP config của <platform>)
```json
{
  "mcpServers": {
    "understand-anything": {
      "command": "uv",
      "args": ["--directory", "<ua_mcp_dir|placeholder>", "run", "server.py"],
      "env": { "PROJECT_ROOTS": "<abs target>" }
    }
  }
}
```

## 4. Verify
maika doctor mcp --target <abs target>
```

### 4.5 — `doctor mcp`: verify 3 tầng

`build_doctor_status` đã nhận `(target, home)`. Mở rộng: doctor đọc `mcps` từ resolved-config + load manifest (`setup.{engine_check, graph_artifact, install_hint}`) — cần thêm `maika_root` (auto-detect như init). Với mỗi selected mcp có `setup`:

```
1. engine?  engine_check[platform]→default  → "✓ installed" | "✗ chưa cài — <install_hint>"
2. graph?   <target>/.understand-anything/knowledge-graph.json
              tồn tại → đếm "nodes=N edges=M" | "✗ chạy /understand"
              parse lỗi → "present (unparseable)"
3. wired?   [LOGIC CŨ] server 'understand-anything' present trong mcp config | "✗ xem MCP_SETUP.md"
```

Mỗi tầng chỉ **report**, không fail cứng (đúng tinh thần doctor diagnose). Token `nodes=/edges=` đồng dạng `validate_mcp_status`. Thêm các dòng vào `render_report`.

> **Lưu ý**: doctor hiện chỉ nhận `target` từ command wrapper; cần truyền `maika_root` (auto-detect như init) để load manifest đọc `engine_check` + `install_hint`. Đây là consumer hợp lệ cho 2 field đó (R1).

## 5. Data flow

```
maika init (UA chọn)
  ├ resolve_init_choices(+ua_mcp_dir)
  ├ generate_resolved_config (schema không đổi)
  ├ emit_mcp_setup(MCP_SETUP.md, snippet đã thay placeholder)
  └ print Next steps (UA)
maika doctor mcp
  ├ load resolved-config (platform, mcps)
  ├ load manifest (setup.{engine_check, graph_artifact, install_hint})
  ├ tầng1 engine_check  tầng2 graph_artifact  tầng3 server-present (cũ)
  └ render_report (+3 dòng)
```

## 6. Error handling / degrade

| Tình huống | Hành vi |
|-----------|---------|
| `--yes` không có `ua_mcp_dir` | snippet dùng placeholder + WARN; init vẫn hoàn tất |
| graph json thiếu | doctor báo "✗ chạy /understand"; không lỗi |
| graph json hỏng | "present (unparseable)" |
| `installed_plugins.json` thiếu (claude-code) | engine_check = "✗ chưa cài" (file_contains trên file không tồn tại = false) |
| platform không có trong `engine_check` | dùng `default` |
| mcp chọn nhưng không có `setup` | bỏ qua 3-tầng cho mcp đó (giữ logic cũ) |

## 7. Ma trận platform

| | claude-code | codex | antigravity |
|---|---|---|---|
| engine_check | `installed_plugins.json` ∋ `understand-anything@` | symlink `~/.agents/skills/understand` | symlink `~/.gemini/antigravity/skills/understand-anything` |
| install_hint | marketplace | `install.sh codex` | `install.sh antigravity` |
| wire snippet | giống nhau (uv run server.py) | — | — |

## 8. Tuân DEVELOPMENT_RULES

- **R1** (consumer): `setup`/`engine_check`/`install_hint`/`mcp_setup` đều có consumer cơ học (emitter + doctor) trong cùng PR.
- **R3** (observed): nhu cầu là quy trình thật người dùng đang chạy, không giả định.
- **R4** (verified trigger): mọi marker/recipe đã verify ở §3.
- **R7** (net complexity): thêm tối thiểu — 1 field manifest, 1 emitter, 1 doctor resolver 2-kind; không shell-out, không hệ song song.

## 9. Testing (TDD — viết test trước)

1. **Manifest schema**: `understand-anything.setup` có đủ `graph_artifact/engine_check/install_hint/server`; `engine_check` mọi entry có `kind ∈ {path_exists, file_contains}`.
2. **Engine resolver**: `path_exists` (tmp symlink/dir) → true/false; `file_contains` (tmp file có/không `needle`) → true/false; platform thiếu → dùng `default`.
3. **Snippet emitter**: thay đúng 3 placeholder (`ua_mcp_dir`, `project_root` abs, `platform` trong install_hint); `--yes` không dir → placeholder.
4. **MCP_SETUP.md**: sinh khi UA chọn; KHÔNG sinh khi không chọn UA / không mcp nào có `setup`.
5. **doctor 3 tầng**: graph tmpfile (nodes/edges) → "nodes=N"; thiếu → "✗"; engine marker giả per-platform → "✓"/"✗".
6. **Regression**: init không chọn UA → không `MCP_SETUP.md`, `resolved-config.yaml` schema y nguyên, doctor report y như cũ.

## 10. Ngoài phạm vi

- Tự ghi MCP config agent (Non-goal §2).
- Probe runtime MCP (giữ `bridge: not-probed`).
- Domain graph artifact (`domain-graph.json`) — chỉ verify code graph; mở rộng sau nếu cần.
