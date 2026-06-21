# Decision: codebase-memory-mcp vs SocratiCode (semantic backend sau UA)

**Date:** 2026-06-22
**Status:** Decided — adopt `codebase-memory-mcp`, replace SocratiCode
**Branch:** `feat/codebase-memory-backend`
**Type:** Tooling decision (chọn 1 trong 2 engine code-intelligence)

---

## 1. Bối cảnh & vai trò thật

Maika dùng một **lớp tool trừu tượng** (`{{ tools.* }}`) cho code-intelligence. Skills/rules
KHÔNG gọi thẳng tên MCP cụ thể — chúng gọi abstract op (`search_code`, `find_blast_radius`,
`trace_flow`, …), và mỗi platform adapter (`cli/platforms/*.py`) map abstract op → tên tool MCP
thật qua `tool_mapping`.

- **UA (`understand-anything`)** là engine knowledge-graph code-intelligence **chính**.
- **SocratiCode** hiện chỉ đóng vai **backend semantic-search đứng sau UA** — vớt lại những
  function/quan hệ mà detection của UA bỏ sót. Vai trò hẹp, không phải engine trung tâm.
- `tool_mapping` đang **hardcode** tên tool `mcp__socraticode__codebase_*` trong
  `cli/platforms/claude_code.py` và `cli/platforms/antigravity.py`.
  `TODOS.md:73` đã tự nhận diện đây là điểm hardcode cần sửa.

→ Câu hỏi quyết định: **với đúng vai trò "semantic backend sau UA", engine nào tốt hơn?**

## 2. Hai ứng viên

| | codebase-memory-mcp (DeusData) | SocratiCode (giancarloerra) |
|---|---|---|
| Ngôn ngữ / runtime | Pure C, **1 static binary**, zero-dep | Node/TS |
| Hạ tầng bắt buộc | Không | **Docker + Qdrant** chạy nền |
| Search | Hybrid: `semantic_query` (embeddings `nomic-embed-code` **bundled trong binary**) + BM25 (FTS5) + structural + Cypher | Hybrid: Qdrant HNSW + BM25, RRF fusion; embeddings ollama/openai/google |
| Knowledge graph | Có (tree-sitter + Hybrid LSP type resolution, 9 ngôn ngữ) | Có (ast-grep, 18+ ngôn ngữ) |
| License | **MIT** | **AGPL-3.0** + bản commercial |
| Cài đặt | `npx` / `uvx` stdio | `npx` stdio (nhưng kéo theo Docker+Qdrant) |
| Số MCP tool | 14 | 21 |

## 3. Phát hiện sửa giả định ban đầu

Giả định "phải giữ SocratiCode vì chỉ nó có semantic search" **SAI**.
cb-mem nhúng sẵn embeddings `nomic-embed-code` (768d int8) **compile thẳng vào binary** —
không API key, không Ollama, **không Docker** — cộng BM25 + structural + Cypher.
Tức cb-mem có **hybrid search tương đương**, nhưng zero-config local.

## 4. So sánh theo 4 tiêu chí đã chọn

| Tiêu chí | cb-mem | SocratiCode | Thắng |
|---|---|---|---|
| **No-Docker / vận hành đơn giản** | 1 binary, zero-dep, stdio | Bắt buộc Docker + Qdrant nền | **cb-mem** (cách biệt) |
| **Chất lượng semantic search** | bundled embeddings + BM25 + structural | Qdrant HNSW + BM25 (RRF) | ~Hòa (SocratiCode nhỉnh ở scale ~40M LOC; cb-mem thắng ở zero-config) |
| **License (ship được trong Maika)** | MIT | AGPL-3.0 + commercial | **cb-mem** (cách biệt) |
| **Hợp Maika / agent flow** | stdio thuần, không daemon → templatize + doctor verify sạch | npx stdio nhưng kéo Docker+Qdrant; có CC plugin+skills chồng lớp agent Maika tự sinh | **cb-mem** |

**Điểm mạnh riêng của SocratiCode (ghi nhận công bằng):**
- **Multi-agent shared index** trên cùng 1 repo (cross-process locking) — đúng mô hình worker-fleet.
- **Branch-aware indexing** (index riêng mỗi git branch).
- Context artifacts (DB schema / API spec) là first-class searchable.

Nhưng với **vai trò hẹp "semantic backend sau UA"**, các điểm mạnh này **không cần thiết**:
fallback semantic cho UA không yêu cầu shared-index đa-agent hay branch-aware.

## 5. Quyết định

**Chọn `codebase-memory-mcp`, thay SocratiCode.**

Lý do: trên 3/4 tiêu chí ưu tiên nó thắng cách biệt (no-Docker, MIT, hợp Maika); tiêu chí thứ 4
(semantic) **hòa** chứ không phải lợi thế của SocratiCode như giả định ban đầu.
**AGPL-3.0 + bắt buộc Docker là hai deal-breaker** cho một framework muốn redistribute như Maika.
Vì SocratiCode chưa được dùng thực chiến (mới đang tích hợp), đổi bây giờ rẻ hơn đổi sau.

**Lợi ích phụ:** knowledge graph của cb-mem (call edges + Hybrid LSP type resolution) có thể giúp
UA detect tốt hơn ngay từ đầu → giảm chính cái "function UA miss" mà ta đang phải vá bằng semantic
fallback. cb-mem do đó có tiềm năng phục vụ **cả 2 vai** (cải thiện detection + làm fallback).

**Điều kiện đảo ngược (revisit):** nếu sau này **bắt buộc cứng** multi-agent shared-index trên cùng
1 repo (nhiều worker đọc/ghi chung 1 index có coordination) hoặc branch-aware index cho CI/PR, và
cb-mem không đáp ứng → cân nhắc lại SocratiCode (chấp nhận Docker + AGPL/commercial).

## 6. Tác động swap (phạm vi, không phải implementation plan)

Vì có lớp `{{ tools.* }}`, **đổi backend = re-point binding**, KHÔNG đụng skills/rules/workflows.

**File phải sửa:**
- `cli/platforms/claude_code.py` — block "Code Exploration (Socraticode)"
- `cli/platforms/antigravity.py` — block "Code Exploration (Socraticode)"
- (tham chiếu prose) `.maika/**` nhắc tên "Socraticode" trong skills/rules/meta-prompt —
  đổi nhãn hiển thị, không đổi abstract op.

**Mapping abstract op → tool cb-mem:**

| Abstract op (Maika) | SocratiCode (hiện tại) | cb-mem (mới) |
|---|---|---|
| `search_code` | `codebase_search` | `search_code` (trùng tên) |
| `index_code` | `codebase_index` | `index_repository` |
| `code_status` | `codebase_status` | `index_status` |
| `get_dependencies` | `codebase_graph_query` | `query_graph` (Cypher read-only) |
| `trace_flow` | `codebase_flow` | `trace_path` |
| `find_blast_radius` | `codebase_impact` | `detect_changes` |
| `get_symbol` | `codebase_symbol` | `get_code_snippet` |
| `list_symbols` | `codebase_symbols` | `search_graph` |
| `graph_stats` | `codebase_graph_stats` | `get_graph_schema` |
| `graph_build` | `codebase_graph_build` | `index_repository` (graph auto-build khi index) |
| semantic (`codebase_context_search` trong skills) | hybrid search | `semantic_query` |

cb-mem có thêm tool không nằm trong abstract set hiện tại: `list_projects`, `get_architecture`,
`manage_adr` — có thể thêm abstract op sau nếu cần (YAGNI: chưa thêm bây giờ).

**Cần verify ở bước plan:**
- Tên tool MCP thật khi chạy qua Claude Code (`mcp__codebase-memory-mcp__<tool>` hay tên server
  khác) — pin server name như đã làm với agent-memory (`agent-memory` vs default `agentmemory`).
- `doctor mcp` verify engine cb-mem (binary present + indexed) song song UA.
- Test `cli/tests/test_platforms.py` vẫn pass (REQUIRED_TOOL_KEYS đầy đủ sau remap).

## 7. Bước tiếp theo

Decision này → implementation plan riêng (qua writing-plans) cho việc swap binding + doctor + tests.
