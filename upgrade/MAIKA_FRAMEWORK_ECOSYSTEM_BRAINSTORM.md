
> **Revision:** Cập nhật theo kiến trúc thực tế: `Egonex-AI/Understand-Anything` build JSON graph; `VIethoangnguyenle/Understand-Anything-MCP` load và trace graph đó; `DeusData/codebase-memory-mcp` là một graph engine độc lập tự index source vào SQLite. Đã bổ sung findings M–T cho cross-provider compatibility, mutability và evidence freshness.

# Maika Framework Ecosystem — Critical Bug & Integration Brainstorm

## 1. Mục tiêu

Rà soát chéo sáu repository/layer dưới đây để xác định các **critical bug có thể gây ảnh hưởng thực tế đến source code, database, workflow state, security boundary, graph correctness hoặc tính toàn vẹn audit**:

1. **Workflow/governance runtime**<br>
   `https://github.com/VIethoangnguyenle/Maika/tree/master-v2`
2. **Graph producer**<br>
   `https://github.com/Egonex-AI/Understand-Anything`
3. **Graph query/trace MCP do project tự xây dựng**<br>
   `https://github.com/VIethoangnguyenle/Understand-Anything-MCP`
4. **Independent source index + structural graph MCP**<br>
   `https://github.com/DeusData/codebase-memory-mcp`
5. **Persistent episodic/semantic memory MCP**<br>
   `https://github.com/rohitg00/agentmemory`
6. **Custom database MCP**<br>
   `https://github.com/VIethoangnguyenle/Db-Access`

> Quan trọng:
>
> - `Understand-Anything-MCP` **không build graph**. Graph JSON được tạo bởi `Egonex-AI/Understand-Anything`; custom MCP chỉ load artifact và cung cấp search/trace/traverse.
> - `DeusData/codebase-memory-mcp` **không dùng graph của Understand Anything**. Nó tự parse/index source thành graph SQLite riêng.
> - `rohitg00/agentmemory` không phải code graph authority. Nó lưu observation/session/fact/pattern và phục vụ historical context, recall, handoff và coordination.
> - `Db-Access` là custom runtime-data provider, có side effects thật ở database.
> - Maika là **control plane** chịu trách nhiệm chọn provider, giới hạn tool, chuẩn hóa evidence, xử lý conflict, enforce workflow và ghi audit.
> - Vì vậy không được merge output của các provider thành một “knowledge truth” chung nếu thiếu authority, freshness, provenance và mutability policy.

Đây là một phiên **brainstorm + adversarial review**, chưa implement ngay.

Mục tiêu cuối cùng:

- Xác minh bug nào là bug thật, bug nào chỉ là architectural risk.
- Xác định blast radius.
- Đề xuất reproduction scenario.
- Đề xuất patch strategy ít phá vỡ hệ thống nhất.
- Đề xuất test bắt buộc để ngăn regression.
- Phân loại `P0 / P1 / P2`.
- Nêu rõ bug nào chặn việc dùng Maika trong môi trường banking/enterprise.

---

## 2. Nguyên tắc rà soát

Không kết luận chỉ dựa trên README hoặc intended behavior.

Mỗi finding phải có:

- Exact file path.
- Function/class liên quan.
- Đường chạy cụ thể.
- Điều kiện để bug xảy ra.
- Side effect thực tế.
- Mức độ chắc chắn:
  - `CONFIRMED`
  - `HIGH_CONFIDENCE`
  - `NEEDS_E2E`
  - `THEORETICAL`
- Proposed reproduction test.
- Proposed fix.
- Regression tests.

Ưu tiên kiểm tra code hiện tại trên branch:

```text
Maika: master-v2
Understand-Anything-MCP: main
Db-Access: main
```

Không assume rằng registry, prompt, gate prose hoặc README là security boundary. Chỉ xem là security boundary nếu enforcement nằm ở runtime/server/OS/database layer.

---


# 2.1. Kiến trúc thực tế cần dùng làm authority

```text
                              ┌──────────────────────────────┐
                              │            MAIKA             │
                              │ Workflow + governance runtime │
                              │ Provider router               │
                              │ Evidence compiler             │
                              │ Gates + audit + write control │
                              └──────────────┬───────────────┘
                                             │
          ┌──────────────────────┬────────────┼───────────────┬──────────────────┐
          │                      │            │               │                  │
          ▼                      ▼            ▼               ▼                  ▼
Understand Anything       Codebase Memory  AgentMemory    DB Access        Current Source
semantic/domain graph     structural graph historical     runtime data     exact authority
          │                      │            memory          │                  │
          ▼                      │            │               │                  │
Custom UA MCP             independent MCP    MCP/REST        custom MCP          │
trace/search/impact       query/index         recall/save     read/write/script  │
          │                      │            │               │                  │
          └──────────────────────┴────────────┴───────────────┴──────────────────┘
                                             │
                                             ▼
                                Normalized provider evidence
```

Phải kiểm tra contract tại các boundary:

```text
UA producer → persisted JSON graph files
Persisted JSON graph files → custom Understand-Anything-MCP
Source repository → Codebase Memory SQLite index
Agent/tool hooks → AgentMemory observations and memories
AgentMemory MCP/shim → Maika memory adapter
Database credentials/session → custom Db-Access MCP
Every MCP response → Maika normalization/audit/gates

Cross-provider reconciliation:
UA evidence ↔ Codebase Memory evidence
Graph evidence ↔ AgentMemory historical claims
Graph/memory claims ↔ current source
Planned behavior ↔ runtime database facts
```

Một bug ở producer không mặc nhiên là bug của MCP; một bug ở MCP loader không nên sửa bằng cách thay đổi Maika prose; một schema mismatch phải được giải quyết bằng versioned contract test.

# 3. Các finding cần Codex xác minh


# 3.1. Framework provider taxonomy

Codex phải dùng taxonomy này thay vì coi tất cả provider là tương đương:

| Provider | Primary purpose | Default mutability | Authority |
|---|---|---:|---|
| Current source | Exact source inspection | Read-only | Highest cho current code |
| Understand Anything | Semantic architecture/domain graph producer | Writes graph artifacts khi rebuild | Supporting/inferred |
| Custom UA MCP | Query/trace UA artifacts | Read-only | Supporting |
| Codebase Memory MCP | Deterministic structural index/trace | Read + local index mutation | Supporting; mạnh cho structure |
| AgentMemory | Historical/episodic recall | Read + memory/coordination writes | Historical only |
| Db-Access | Runtime schema/data | Read/write/script | Runtime authority trong scope credential |
| Maika | Routing, governance, evidence, workflow | Framework state + controlled source writes | Policy/control-plane authority |

Mỗi provider record phải khai:

```yaml
provider_id:
implementation_repo:
implementation_version:
integration_mode:
instance_id:
store_or_index_id:
capabilities:
tool_contract_hash:
mutability_lanes:
authoritative_for:
not_authoritative_for:
freshness_model:
identity_model:
failure_mode:
fallback_policy:
```



## Finding A — Db-Access cross-session authorization

### Hypothesis

HTTP transport session được tạo với `source A`, nhưng request tiếp theo chỉ resolve bằng `mcp-session-id` và reuse transport mà không kiểm tra API key hiện tại có thuộc source A hay không.

### Evidence paths

```text
Db-Access/src/index.ts
Db-Access/src/auth/resolve-source.ts
Db-Access/src/auth/http.ts
Db-Access/src/server.ts
```

### Luồng cần kiểm tra

```text
Request 1:
API key A
→ create StreamableHTTP transport
→ createServer(sourceA)
→ sessionId = X

Request 2:
API key B
mcp-session-id = X
→ transport X được reuse
→ server instance có thể vẫn giữ sourceA
```

SSE cần kiểm tra tương tự:

```text
GET /sse bằng source A
POST /messages?sessionId=X bằng source B
```

### Rủi ro

Nếu source A có quyền `write/script` và source B chỉ có `read`, B có thể dùng session của A để thực thi tool với quyền A.

### Codex cần trả lời

1. Transport có bind source/session identity không?
2. Session ID có thể bị lộ qua log, proxy, tracing hoặc client state không?
3. MCP SDK có tự enforce ownership không?
4. Có thể viết integration test chứng minh source B reuse session A không?
5. Fix tốt nhất:
   - map `sessionId -> {transport, sourceId}`;
   - bind API-key fingerprint;
   - hay tạo transport registry per source?

### Acceptance test mong đợi

```text
sourceA creates session
sourceB calls same session
→ HTTP 403 hoặc JSON-RPC authorization error
→ tool handler không được chạy
```

---

## Finding B — Db-Access shadow preview fail-open

### Hypothesis

`UPDATE/DELETE` vẫn được cấp confirmation token ngay cả khi không tạo được shadow preview an toàn.

### Evidence paths

```text
Db-Access/src/tools/sql-write.ts
Db-Access/src/safety/shadow.ts
Db-Access/src/drivers/oracle/executor.ts
Db-Access/src/drivers/postgres/executor.ts
```

### Luồng nghi ngờ

```text
sql_write without token
→ parse UPDATE/DELETE
→ executePreview()
→ preview returns success=false hoặc buildShadowQuery() returns null
→ tool vẫn createConfirmationToken()
→ second call executes DML
```

### Các câu SQL cần thử

```sql
UPDATE SCHEMA.TABLE_A
SET STATUS = 'X'
WHERE ID IN (
    SELECT ID FROM SCHEMA.TABLE_B WHERE FLAG = 1
);
```

```sql
DELETE FROM SCHEMA.TABLE_A;
```

```sql
UPDATE SCHEMA.TABLE_A A
SET A.STATUS = 'X'
WHERE EXISTS (
    SELECT 1 FROM SCHEMA.TABLE_B B
    WHERE B.ID = A.ID
);
```

### Rủi ro

- Không biết chính xác row nào bị thay đổi.
- Full-table update/delete vẫn có thể được confirm.
- Preview safety trở thành UX hint, không phải hard gate.

### Codex cần trả lời

1. Preview fail có thực sự vẫn trả token không?
2. Full-table UPDATE/DELETE có bị block không?
3. Preview result có kiểm tra `success` không?
4. Nên fail-closed ở tool layer hay driver layer?
5. Có cần:
   - `allow_full_table: true`;
   - row threshold;
   - explicit user approval;
   - affected-row estimate?

### Proposed invariant

```text
UPDATE/DELETE không có trusted preview
→ không cấp token
→ không được execute
```

---

## Finding C — Db-Access false success response

### Hypothesis

Oracle/PostgreSQL executor bắt exception rồi trả object có `success: false`, nhưng `sql_write` vẫn tạo response với message `Successfully executed ...` và không đặt `isError: true`.

### Evidence paths

```text
Db-Access/src/tools/sql-write.ts
Db-Access/src/drivers/oracle/executor.ts
Db-Access/src/drivers/postgres/executor.ts
```

### Rủi ro

- Agent nghĩ DB write thành công.
- Maika ghi provider invocation status `success`.
- Audit trail sai.
- Workflow tiếp tục dựa trên dữ liệu chưa được thay đổi.

### Codex cần trả lời

1. Error từ driver có được throw không?
2. Tool response có `isError: true` khi result.success=false không?
3. Maika provider recorder lấy status từ đâu?
4. Có scenario nào `rowsAffected=0` nhưng vẫn được coi là success hợp lệ?

### Proposed invariant

```text
driver result.success != true
→ MCP isError = true
→ không có success message
→ provider invocation status phải là error
```

---

## Finding D — Confirmation token không phải human approval

### Hypothesis

Agent có thể tự gọi:

```text
preview
→ nhận confirmation_token
→ gọi lại cùng tool với token
```

Không có human-in-the-loop thực sự.

### Evidence paths

```text
Db-Access/src/safety/token-manager.ts
Db-Access/src/tools/sql-write.ts
Db-Access/src/tools/sql-execute-script.ts
Db-Access/src/tools/mongo-write.ts

Maika/.maika/config/provider-registry.yaml
Maika/cli/commands/provider.py
```

### Cần phân biệt

Confirmation token hiện tại có thể bảo vệ:

- accidental one-shot execution;
- payload mutation;
- token replay sau TTL;
- token reuse.

Nhưng có thể không bảo vệ:

- agent tự confirm;
- wrong human/session/source;
- wrong environment;
- privilege escalation qua session reuse.

### Codex cần trả lời

1. Token có bind với:
   - source?
   - API key?
   - session?
   - operation type?
   - environment?
   - human approval ID?
2. Token entropy 32-bit có đủ không?
3. Token global in-memory map có collision/restart issue không?
4. Maika có runtime proof về `explicit_user_request` không, hay chỉ có registry prose?

### Proposed design

```yaml
approval:
  approval_id:
  approved_by:
  source_id:
  session_id:
  environment:
  database:
  tool:
  request_hash:
  expires_at:
```

---

## Finding E — DDL guard có thể bypass bằng dynamic SQL

### Hypothesis

Oracle/PostgreSQL script guard dựa trên regex raw text. Dynamic SQL hoặc string concatenation có thể tránh detection.

### Evidence paths

```text
Db-Access/src/drivers/oracle/plsql-parser.ts
Db-Access/src/drivers/oracle/plsql-executor.ts
Db-Access/src/drivers/postgres/script.ts
Db-Access/src/drivers/relational.ts
```

### Payload thử nghiệm

Oracle:

```sql
BEGIN
    EXECUTE IMMEDIATE 'DR' || 'OP TABLE SOME_SCHEMA.SOME_TABLE';
END;
```

PostgreSQL:

```sql
DO $$
DECLARE
    stmt text := 'DR' || 'OP TABLE public.some_table';
BEGIN
    EXECUTE stmt;
END $$;
```

### Rủi ro

Nếu database credential có DDL privilege, regex không phải security boundary đáng tin cậy.

### Codex cần trả lời

1. Parser có detect `EXECUTE IMMEDIATE`/dynamic `EXECUTE` không?
2. DB credential production có được kỳ vọng là least privilege không?
3. Có cách enforce ở DB role thay vì parser không?
4. Tool `script` có nên bị loại hoàn toàn khỏi Maika runtime?

### Proposed invariant

```text
Agent credential không có DDL privilege ở database level,
bất kể parser có bug hay không.
```

---

## Finding F — Maika ↔ Understand-Anything metadata schema mismatch

### Hypothesis

Understand-Anything trả metadata dạng nested:

```json
{
  "project": "...",
  "graph": {
    "graph_commit": "..."
  },
  "repository": {
    "head": "..."
  },
  "freshness": {
    "status": "FRESH"
  },
  "health": {
    "status": "HEALTHY"
  }
}
```

Nhưng Maika adapter tìm `graph_commit` và `repository_head` ở top-level.

### Evidence paths

```text
Understand-Anything-MCP/server.py
Understand-Anything-MCP/kg_loader.py

Maika/cli/mcp/integration/understand_anything.py
Maika/.maika/tools/gate-check/gates.py
Maika/.maika/config/provider-registry.yaml
```

### Rủi ro

- `graph_commit` bị mất.
- `repository_head` bị mất.
- `trace-evidence` fail dù UA hoạt động.
- Worker có thể tự điền metadata.
- Grounding bị degrade sai.

### Codex cần làm

1. So sánh exact JSON producer và consumer.
2. Viết contract fixture.
3. Xác minh trace gate yêu cầu field nào.
4. Xem `freshness` và `health` gate cần string hay object.
5. Đề xuất canonical contract versioning.

### Proposed normalized shape

```yaml
provider_id: understand-anything
tool: get_graph_metadata
response_hash: sha256:...
graph:
  contract_version: 1
  project:
  graph_commit:
  repository_head:
  freshness:
  health:
```

---

## Finding G — Understand-Anything báo FRESH dù working tree dirty

### Hypothesis

Freshness chỉ so sánh graph commit với `HEAD`, không bao phủ đầy đủ:

- unstaged changes;
- staged changes;
- untracked source files.

### Evidence paths

```text
Understand-Anything-MCP/kg_loader.py
```

### Các case cần test

```bash
# Graph commit == HEAD
echo "// dirty" >> src/App.java
```

```bash
git add src/App.java
```

```bash
touch src/NewClass.java
```

Sau mỗi case gọi `get_graph_metadata`.

### Rủi ro

Maika tin graph fresh trong khi source thực tế đã thay đổi.

### Proposed freshness union

```bash
git diff --name-only <graph_commit>..HEAD
git diff --name-only
git diff --cached --name-only
git ls-files --others --exclude-standard
```

### Codex cần cân nhắc

- Có nên bỏ qua generated/build dirs?
- Untracked file nào được tính?
- Nếu dirty file không nằm trong trace scope, confidence có cần giảm không?
- Có nên trả:
  - `repository_head`;
  - `working_tree_hash`;
  - `dirty_files`;
  - `relevant_dirty_files`?

---

## Finding H — Domain graph parse error bị degrade âm thầm

### Hypothesis

Malformed `domain-graph.json` bị catch rồi thay bằng `{}`, nhưng health vẫn có thể trả `HEALTHY`.

### Evidence paths

```text
Understand-Anything-MCP/kg_loader.py
Understand-Anything-MCP/server.py
```

### Rủi ro

- Business/domain evidence biến mất.
- Maika nghĩ provider healthy.
- Grounding thiếu business lens nhưng không có degradation reason chính xác.

### Codex cần trả lời

1. Domain graph malformed có được log không?
2. Metadata health có phân biệt:
   - missing optional;
   - empty valid;
   - malformed invalid?
3. Maika có gate bắt domain graph khi business trace được yêu cầu không?

### Proposed metadata

```yaml
domain_graph:
  status: HEALTHY | MISSING | EMPTY | INVALID
  node_count:
  edge_count:
  parse_error:
```

---

## Finding I — Maika write-gate shell bypass

### Hypothesis

Write gate chỉ parse một tập command hữu hạn. Các interpreter hoặc mutating commands ngoài parser có thể sửa file ngoài scope.

### Evidence paths

```text
Maika/.maika/hooks/write-gate/write_gate.py
Maika/.maika/hooks/write-gate/tests/
```

### Payload cần thử

```bash
python -c "open('src/Outside.java','w').write('x')"
node -e "require('fs').writeFileSync('src/Outside.java','x')"
touch src/Outside.java
truncate -s 0 src/App.java
unzip payload.zip
tar -xf payload.tar
git reset --hard
mvn spotless:apply
```

Kiểm tra thêm file gitignored:

```bash
echo PASSWORD=x > .env
```

### Rủi ro

- Scope gate bị bypass.
- Framework artifact/source bị sửa ngoài manifest.
- Audit trail không phản ánh side effect thật.

### Codex cần trả lời

1. Command nào parser nhận diện?
2. Unknown mutating command fail-open hay fail-closed?
3. Gitignored target có bị loại khỏi enforcement không?
4. Có post-execution diff enforcement không?
5. Có rollback không?

### Proposed architecture

```text
pre-command gate
+ isolated worktree/container
+ before/after filesystem snapshot
+ scope diff validation
+ rollback on violation
```

---

## Finding J — Maika dispatch role không đồng nhất với write gate

### Hypothesis

Write gate chỉ cho phép khi có đúng một task `in_progress`, nhưng authoring/review worker ghi artifact ở các state/status khác:

- `EXPLORING`
- `RECONCILING`
- `BRAINSTORMING`
- `PLANNING`
- task `reviewing`
- final review khi tất cả task `done`

### Evidence paths

```text
Maika/.maika/hooks/write-gate/write_gate.py
Maika/.maika/tools/microloop-orchestrator/vnext_dispatch.py
Maika/.maika/tools/microloop-orchestrator/orchestrator.py
Maika/cli/commands/task.py
```

### Rủi ro

- Hook block chính worker hợp lệ.
- Behavior phụ thuộc worker dùng Write hay Bash.
- Cross-platform nondeterminism.
- Review flow không ổn định.

### Codex cần xác minh bằng E2E

```text
grounding worker writes GROUNDING.yaml
spec worker writes SPEC.md
task reviewer writes reviews/TASK-001.md
final reviewer writes FINAL_REVIEW.md
```

Khi native write hook được bật thật.

### Proposed fix

Tạo unified dispatch contract:

```yaml
execution_id:
change_id:
role:
state:
status: active
allowed_outputs:
allowed_source_scope:
lease_expires_at:
prompt_hash:
```

Write gate resolve active dispatch thay vì chỉ task `in_progress`.

---

## Finding K — Maika lightweight archive failure

### Hypothesis

`trivial/small` verify chuyển thẳng sang `COMPLETED`, nhưng archive bắt buộc `KNOWLEDGE_IMPACT.yaml` và `SKILL_FEEDBACK.yaml`, trong khi lightweight flow không tạo các artifact này.

### Evidence paths

```text
Maika/cli/commands/task.py
Maika/.maika/tools/microloop-orchestrator/
```

### E2E mong đợi

```text
maika task start --class small
maika task apply
maika task verify
maika task archive
```

### Codex cần trả lời

1. Có nhánh class-aware trong archive không?
2. Lightweight verify có generate zero-impact artifact không?
3. Existing tests có cover lifecycle đến archive không?

### Proposed fix

Generate zero-impact artifacts cho lightweight:

```yaml
stale_entries: []
superseded_decisions: []
new_candidates: []
graph_refresh_required: false
memory_updates: []
```

---

## Finding L — Maika workspace lock race

### Hypothesis

Lease timeout bằng worker timeout; không có heartbeat định kỳ; expired lock có thể bị owner khác takeover; owner cũ release có thể xóa lock của owner mới.

### Evidence paths

```text
Maika/.maika/tools/microloop-orchestrator/runtime_hardening.py
Maika/.maika/tools/microloop-orchestrator/orchestrator.py
Maika/.maika/tools/microloop-orchestrator/vnext_dispatch.py
```

### Timeline cần mô phỏng

```text
A acquire lock
A chạy > lease

B thấy expired
B remove lock A
B acquire lock

A finish
A release
→ có xóa lock B không?

C acquire
```

### Rủi ro

- Duplicate execution.
- Queue/result overwrite.
- Hai worker sửa cùng source.
- External command chạy nhiều lần.

### Proposed fix

```yaml
lock:
  owner_token:
  pid:
  host:
  generation:
  acquired_at:
  heartbeat_at:
  lease_expires_at:
```

- Compare-and-delete khi release.
- Heartbeat thread.
- Fencing generation trên mọi state mutation.
- Same-host PID còn sống thì không takeover.

---


## Finding M — Graph directory discovery mismatch: `.ua` vs `.understand-anything`

### Hypothesis

Egonex Understand-Anything hiện:

- dùng `.ua/` cho project mới;
- tiếp tục dùng `.understand-anything/` nếu legacy directory đã tồn tại.

Trong khi `Understand-Anything-MCP/kg_loader.py` đang hard-code:

```text
<project>/.understand-anything/knowledge-graph.json
<project>/.understand-anything/domain-graph.json
<project>/.understand-anything/meta.json
```

### Evidence paths

```text
Egonex-AI/Understand-Anything:
  README.md
  understand-anything-plugin/skills/understand/SKILL.md
  understand-anything-plugin/packages/core/src/persistence/*
  understand-anything-plugin/agents/knowledge-graph-guide.md

VIethoangnguyenle/Understand-Anything-MCP:
  kg_loader.py
  server.py
```

### Reproduction

```text
1. Dùng project mới, chưa có .understand-anything/
2. Chạy /understand
3. Xác nhận graph được ghi vào .ua/
4. Start Understand-Anything-MCP với PROJECT_ROOTS=<project>
5. Gọi list_projects hoặc get_graph_metadata
```

### Expected risk

MCP báo graph không tồn tại dù producer đã build thành công.

### Proposed fix

Dùng cùng resolver với upstream:

```python
def resolve_ua_dir(project_root: str) -> str:
    legacy = os.path.join(project_root, ".understand-anything")
    return legacy if os.path.isdir(legacy) else os.path.join(project_root, ".ua")
```

Không nên scan cả hai rồi chọn file mới nhất một cách âm thầm. Nếu cả hai cùng tồn tại, trả trạng thái conflict và yêu cầu cấu hình explicit hoặc áp dụng precedence contract.

---

## Finding N — Metadata field mismatch: `lastAnalyzedAt` vs `analyzedAt`

### Hypothesis

Upstream `AnalysisMeta` hiện dùng:

```json
{
  "lastAnalyzedAt": "...",
  "gitCommitHash": "...",
  "version": "...",
  "analyzedFiles": 42
}
```

Nhưng MCP loader đọc:

```python
analyzed_at = raw_meta.get("analyzedAt", "")
git_commit_hash = raw_meta.get("gitCommitHash", "")
```

### Evidence paths

```text
Egonex-AI/Understand-Anything:
  understand-anything-plugin/packages/core/src/types.ts
  understand-anything-plugin/packages/core/src/persistence/persistence.test.ts

VIethoangnguyenle/Understand-Anything-MCP:
  kg_loader.py
```

### Risk

- `analyzed_at` luôn rỗng với graph mới.
- `days_since_analysis` luôn `-1`.
- Freshness classification dựa trên thời gian bị sai.
- MCP health có thể vẫn báo `HEALTHY` nhưng kèm warning, khiến Maika tin provider khỏe hơn thực tế.
- Fallback `git log --since=<analyzedAt>` không hoạt động khi commit graph không còn tồn tại local.

### Proposed fix

Resolver backward-compatible:

```python
analyzed_at = (
    raw_meta.get("lastAnalyzedAt")
    or raw_meta.get("analyzedAt")
    or project_info.get("analyzedAt")
    or ""
)
git_commit_hash = (
    raw_meta.get("gitCommitHash")
    or project_info.get("gitCommitHash")
    or ""
)
```

Thêm `producer_schema_version` và fixture lấy trực tiếp từ upstream persistence tests.

---

## Finding O — Inheritance edge mismatch: `inherits` vs `extends`

### Hypothesis

Upstream `EdgeType` dùng:

```text
inherits
implements
```

Nhưng MCP query engine đang theo dõi:

```text
extends
implements
```

trong:

- `find_impact`;
- `get_class_hierarchy`;
- relation-filter documentation.

### Evidence paths

```text
Egonex-AI/Understand-Anything:
  understand-anything-plugin/packages/core/src/types.ts
  understand-anything-plugin/agents/knowledge-graph-guide.md
  understand-anything-plugin/agents/file-analyzer.md

VIethoangnguyenle/Understand-Anything-MCP:
  kg_loader.py
  server.py
```

### Risk

- Class hierarchy bỏ sót toàn bộ inheritance edge được producer sinh là `inherits`.
- Blast radius không lan qua quan hệ kế thừa.
- Maika có thể đánh giá thiếu consumer/subclass impact.
- Với Java/Spring Boot, đây có thể làm bỏ sót interface/base-class contract change.

### Proposed fix

Không sửa bằng prose mapping rời rạc. Chuẩn hóa khi load:

```python
EDGE_ALIASES = {
    "extends": "inherits",
    "inherits": "inherits",
}
```

Sau đó query engine chỉ dùng canonical `inherits`.

Thêm producer-consumer contract test chứa Java inheritance:

```java
interface PaymentHandler {}
class NapasPaymentHandler implements PaymentHandler {}
class BaseTransferService {}
class TransferService extends BaseTransferService {}
```

Xác minh:

- `get_class_hierarchy`;
- `find_impact`;
- `get_relationships`;
- Maika trace evidence.

---

## Finding P — Producer graph contract drift không được version-gate

### Hypothesis

Upstream graph schema đang phát triển:

- node types tăng;
- edge types tăng;
- default data directory đổi;
- metadata shape có legacy/new variants.

MCP loader hiện parse permissively bằng `data.get(...)`, có thể biến schema mới thành field rỗng thay vì fail/degrade rõ ràng.

### Risk

Silent semantic corruption nguy hiểm hơn parse failure:

```text
Graph load thành công
→ indexes được build
→ tool trả kết quả thiếu
→ Maika ghi evidence hợp lệ về mặt hash
→ reasoning dựa trên graph không đầy đủ
```

### Proposed contract

MCP metadata phải công bố:

```yaml
producer:
  name: Egonex-AI/Understand-Anything
  graph_version:
  meta_version:
  data_directory:
consumer:
  name: Understand-Anything-MCP
  supported_graph_versions:
compatibility:
  status: compatible | degraded | unsupported
  warnings: []
```

Unknown critical edge/node schema phải ít nhất tạo `DEGRADED`, không được im lặng coi là `HEALTHY`.

---


## Finding Q — Maika thiếu tool contract và mutability lanes cho Codebase Memory MCP

### Context

Repository authority:

```text
https://github.com/DeusData/codebase-memory-mcp
```

MCP này hiện công bố các nhóm tool gồm:

```text
index_repository
list_projects
delete_project
index_status

search_graph
trace_path
detect_changes
query_graph
get_graph_schema
get_code_snippet
get_architecture
search_code
manage_adr
ingest_traces
```

Trong khi Maika provider registry hiện chỉ khai capability:

```yaml
codebase-memory-mcp:
  kind: semantic_code_index
  capabilities:
    primary: [semantic_code_search]
    supporting:
      [architecture_discovery, call_chain_trace, impact_analysis]
```

và không có `tool_contract`/lane snapshot như Db-Access.

### Risk

Codebase Memory không phải provider thuần read-only:

- `index_repository` tạo/cập nhật persistent index và có thể refresh repository artifact;
- `delete_project` xóa index;
- `manage_adr` có CRUD và persist decision;
- `ingest_traces` thay đổi graph evidence;
- installer của upstream còn có thể sửa agent config/hook files, dù installer không phải MCP query tool.

Nếu Maika chỉ phân loại provider là semantic search, worker có thể gọi mutating tool mà không có lane/activation rule rõ ràng.

### Proposed lanes

```yaml
tool_contract:
  lanes:
    discovery:
      tools:
        - list_projects
        - index_status
        - get_graph_schema
        - search_graph
        - trace_path
        - detect_changes
        - query_graph
        - get_code_snippet
        - get_architecture
        - search_code
        - semantic_query
      mutability: read_only

    explicit_index:
      tools: [index_repository]
      activation: explicit_index_request
      mutability: local_index_write

    explicit_graph_mutation:
      tools: [manage_adr, ingest_traces]
      activation: explicit_user_request
      mutability: graph_write

    destructive_admin:
      tools: [delete_project]
      activation: explicit_user_request
      confirmation_required: true
      mutability: destructive
```

Codex phải xác minh tool list runtime bằng `tools/list`, không tin README đơn lẻ.

---

## Finding R — Tool-list drift quanh `semantic_query`

### Hypothesis

Upstream README mô tả `semantic_query` là semantic vector search, nhưng bảng “14 MCP tools” tại cùng revision không liệt kê tool này, trong khi source/document search vẫn có reference đến tên đó.

### Risk

- Maika khai `semantic_code_search` làm primary capability nhưng không pin tool thực tế.
- Worker có thể gọi tool không tồn tại trên binary/release đang cài.
- Provider được đánh dấu `ready` từ một probe khác, trong khi capability primary không usable.
- Tool names có thể khác nhau theo release.

### Codex cần làm

1. Chạy `tools/list` trên binary version thực tế đang dùng.
2. Ghi:
   - binary version;
   - tool names;
   - input schemas;
   - aliases;
   - build variant.
3. Xác định `semantic_query`:
   - là public MCP tool;
   - CLI-only;
   - feature chưa release;
   - hay README/tool table drift.
4. Không cho `semantic_code_search` pass health gate nếu probe không gọi đúng tool cung cấp capability đó.

### Proposed health record

```yaml
provider: codebase-memory-mcp
binary_version:
tool_contract_hash:
capability_probes:
  semantic_code_search:
    tool:
    status:
    response_hash:
```

---

## Finding S — Hai graph độc lập có thể trả evidence mâu thuẫn mà không có authority rule

### Context

Understand Anything path:

```text
Source → LLM-assisted JSON graph → Understand-Anything-MCP
```

Codebase Memory path:

```text
Source → tree-sitter + Hybrid LSP → SQLite graph → Codebase Memory MCP
```

Hai provider có thể khác nhau về:

- commit/index timestamp;
- dirty working tree coverage;
- call-edge resolution;
- inheritance relation;
- generated source;
- ignored files;
- cross-repo linking;
- semantic summaries;
- domain/business flow.

### Example conflicts

```text
UA: A calls B
CBM: no resolved CALLS edge

UA: class hierarchy contains X
CBM: X is not linked due unsupported/generated type

CBM detect_changes: high blast radius
UA graph: FRESH but built at committed HEAD and misses dirty file
```

### Risk

Maika có thể chọn kết quả thuận tiện hơn hoặc merge hai kết quả thành một claim “verified” dù chúng đại diện cho hai snapshots khác nhau.

### Proposed authority policy

```yaml
authority:
  exact_current_source:
    provider: current-source

  structured_graph_trace:
    preferred: understand-anything
    corroborating: [codebase-memory-mcp, current-source]
    conflict_action: verify_current_source

  semantic_index_structure:
    preferred: codebase-memory-mcp
    corroborating: understand-anything
    conflict_action: verify_current_source

  domain_semantics:
    preferred: understand-anything
    corroborating: current-source
    conflict_action: mark_inferred_or_conflicting

  dirty_diff_impact:
    preferred: codebase-memory-mcp.detect_changes
    corroborating: current-source
```

Không provider graph nào được authoritative cho exact code behavior nếu chưa verify source hash.

---

## Finding T — Codebase Memory evidence thiếu immutable index revision

### Hypothesis

Codebase Memory hỗ trợ:

- persistent SQLite index;
- auto-index;
- background watcher;
- incremental refresh;
- uncommitted-diff detection.

Một query response hash chỉ chứng minh nội dung response, không chứng minh graph snapshot nào đã tạo ra response đó nếu metadata không bind với index generation/source state.

### TOCTOU scenario

```text
Probe 1: get_architecture
Watcher re-indexes changed files
Probe 2: trace_path
Worker combines both into one TRACE_EVIDENCE
```

Hai observations có thể đến từ hai graph generations khác nhau.

### Required metadata

Mỗi result cần bind với:

```yaml
project:
repository_root_hash:
repository_head:
working_tree_state_hash:
index_generation:
index_updated_at:
index_mode: full | incremental | imported_artifact
binary_version:
schema_version:
```

### Codex cần xác minh

1. Tool responses hiện có trả index generation/version không?
2. `index_status` có đủ để bind query snapshot không?
3. Background watcher có thể update giữa các calls không?
4. Có transaction/snapshot read semantics trong SQLite không?
5. Maika có thể pin một generation cho toàn grounding session không?

### Proposed invariant

```text
Một TRACE_EVIDENCE package không được đánh dấu complete
nếu observations đến từ nhiều index_generation khác nhau,
trừ khi có explicit refresh boundary và re-validation.
```

---


## Finding U — AgentMemory integration mode chưa được đóng đinh

### Context

Repository authority:

```text
https://github.com/rohitg00/agentmemory
```

AgentMemory có nhiều integration mode rất khác nhau:

```text
MCP-only
MCP shim + remote/full server
native plugin + lifecycle hooks
REST API
skills
team/mesh mode
```

Full server công bố 53 tools; khi shim không kết nối được server, nó có thể fallback sang một local surface chỉ có 7 tools.

### Risk

Nếu Maika không pin integration mode, cùng một config có thể thay đổi behavior theo runtime availability:

```text
server reachable
→ 53-tool remote memory surface

server unavailable
→ local 7-tool fallback
```

Điều này có thể tạo:

- tool contract drift;
- memory split-brain;
- write vào local fallback nhưng recall từ remote server ở session sau;
- capability probe pass cho core search nhưng extended governance/coordination tools biến mất;
- evidence không xác định được memory store nào đã phục vụ request.

### Required decision

Maika nên chọn một mode rõ ràng:

```yaml
agentmemory:
  integration_mode: mcp_proxy_only
  fallback: disabled
  hooks: disabled
  expected_store_id:
  expected_server_url:
  required_tools:
    - memory_smart_search
    - memory_recall
    - memory_sessions
  optional_tools: []
```

Nếu remote server không reachable, provider phải `UNAVAILABLE`, không fallback âm thầm sang local memory.

---

## Finding V — AgentMemory thiếu mutability lanes trong Maika registry

### Context

Maika hiện mô tả AgentMemory chủ yếu như:

```yaml
kind: episodic_memory
primary: historical_context_retrieval
supporting: business_knowledge_retrieval
```

Nhưng AgentMemory có cả read và write/destructive/coordination tools.

### Suggested classification

```yaml
tool_contract:
  lanes:
    recall:
      tools:
        - memory_recall
        - memory_smart_search
        - memory_sessions
        - memory_timeline
        - memory_profile
        - memory_file_history
        - memory_relations
        - memory_graph_query
        - memory_verify
      mutability: read_only

    explicit_memory_write:
      tools:
        - memory_save
        - memory_facet_tag
      activation: explicit_framework_decision
      mutability: memory_write

    maintenance:
      tools:
        - memory_consolidate
        - memory_snapshot_create
        - memory_claude_bridge_sync
        - memory_heal
      activation: explicit_maintenance
      mutability: memory_state_write

    destructive:
      tools:
        - memory_governance_delete
      activation: explicit_user_request
      confirmation_required: true
      mutability: destructive

    coordination:
      tools:
        - memory_action_create
        - memory_action_update
        - memory_lease
        - memory_routine_run
        - memory_signal_send
        - memory_checkpoint
        - memory_sentinel_create
        - memory_sentinel_trigger
        - memory_sketch_create
        - memory_sketch_promote
        - memory_crystallize
      activation: explicitly_enabled_feature
      mutability: coordination_state_write

    team_or_mesh:
      tools:
        - memory_team_share
        - memory_mesh_sync
      activation: explicit_admin_enablement
      mutability: external_or_shared_write
```

Codex phải snapshot tool list từ runtime đang dùng; không assume README và installed package luôn đồng nhất.

---

## Finding W — Auto-capture hooks có thể phá governance và làm nhân đôi audit

### Context

AgentMemory hooks có thể tự động capture:

```text
UserPromptSubmit
PreToolUse
PostToolUse
PostToolUseFailure
Stop
SessionEnd
SubagentStart/Stop
```

Nó có thể lưu tool name, input, output, prompt và session summary.

Maika đồng thời đã có:

- provider invocation records;
- request/response hashes;
- workflow artifacts;
- audit/state transitions;
- context compilation.

### Risk

Nếu bật cả hai:

- cùng một provider call được lưu hai lần ở hai schema khác nhau;
- memory capture xảy ra ngoài Maika transaction;
- failed/rejected write vẫn có thể được nhớ như hành động đã thực hiện;
- hook capture không biết task scope/allowed files/gate verdict;
- output lớn hoặc nhạy cảm bị đưa vào memory;
- Stop/session hooks có thể chạy khi workflow chưa commit/archive;
- context injection từ memory làm agent dùng claim cũ trước khi grounding.

### Recommended framework posture

```yaml
agentmemory:
  mode: mcp_only
  hooks:
    auto_capture: false
    session_injection: false
    stop_summary: false
```

Maika chủ động gọi memory tools sau khi:

```text
artifact validated
→ final review passed
→ archive committed
→ memory candidate classified
→ explicit persistence policy allows write
```

Đây là integration policy của Maika, không nhất thiết là upstream AgentMemory bug.

---

## Finding X — AgentMemory claim không được trở thành code/business authority

### Context

AgentMemory lưu nhiều loại dữ liệu:

- raw observations;
- compressed observations;
- episodic summaries;
- semantic facts;
- patterns;
- graph entities;
- procedural workflows.

Các dữ liệu này có thể:

- được LLM compress;
- decay;
- supersede;
- contradict;
- originate từ failed experiment;
- originate từ user prompt thay vì verified source.

### Required authority rule

```yaml
authority:
  agentmemory:
    authoritative_for:
      - historical_session_fact
      - previous_decision_reference
      - prior_user_preference
      - prior_failure_or_attempt
    not_authoritative_for:
      - exact_current_code
      - current_architecture
      - current_database_state
      - current_business_rule
      - current_security_permission
```

Một memory claim dùng cho planning phải có:

```yaml
memory_id:
memory_type:
source_observation_ids:
project:
agent_id:
created_at:
last_verified_at:
source_revision:
confidence:
superseded_by:
```

Nếu claim ảnh hưởng code/spec hiện tại, Maika phải verify qua current source, graph hoặc runtime data.

---

## Finding Y — Agent scope là retrieval convenience, không phải security boundary

### Context

AgentMemory hỗ trợ:

```text
AGENT_ID
AGENTMEMORY_AGENT_SCOPE=shared|isolated
```

Nhưng API có thể cho phép per-request override, kể cả wildcard để bỏ filter, tùy endpoint/integration mode.

### Risk

Trong một server dùng chung cho architect/developer/reviewer:

- worker có thể đọc memory của role khác;
- agent tự chọn `agentId=*`;
- write có thể gắn nhãn role khác;
- role isolation bị hiểu nhầm là authorization.

### Required design

Không dùng `AGENTMEMORY_AGENT_SCOPE` làm security boundary chính.

Nếu cần isolation thật:

```text
separate secrets and server namespaces
hoặc separate AgentMemory instances/stores
hoặc Maika adapter strips agentId override and enforces caller identity
```

Maika phải bind:

```yaml
workflow_execution_id:
worker_role:
agentmemory_principal:
allowed_memory_namespaces:
```

---

## Finding Z — Memory lifecycle xung đột với Maika knowledge governance

### Context

AgentMemory có lifecycle riêng:

- consolidation;
- contradiction detection;
- decay;
- auto-eviction;
- supersession;
- graph extraction;
- snapshots;
- healing.

Maika cũng có knowledge governance riêng:

- ACTIVE/FADING/ARCHIVED;
- knowledge registry;
- conflict resolution;
- archive/update artifacts;
- canonical knowledge decisions.

### Risk

Hai lifecycle engines cùng sửa một khái niệm:

```text
AgentMemory auto-consolidates claim A
Maika archives or supersedes claim A
AgentMemory later recalls old compressed derivative B
Maika sees B as a new candidate
```

Điều này tạo feedback loop và resurrection của knowledge đã bị supersede.

### Proposed ownership

```yaml
Maika knowledge kernel:
  owns:
    - canonical project knowledge
    - durable architecture decisions
    - conventions
    - business rules
    - supersession lifecycle

AgentMemory:
  owns:
    - episodic history
    - session summaries
    - prior attempts
    - user/workflow preferences
    - non-canonical recall candidates
```

Persistence flow:

```text
AgentMemory recall
→ candidate context only

Maika validation/reconciliation
→ canonical decision

Canonical decision
→ Maika knowledge store

Optional short reference back to AgentMemory
→ never duplicate the full canonical knowledge lifecycle
```

---

## Finding AA — Remote AgentMemory auth/fallback misconfiguration

### Context

AgentMemory REST binds localhost by default, while remote/protected deployments use `AGENTMEMORY_SECRET`.

### Risk

- Remote deployment exposed without secret.
- Shim URL typo silently falls back local.
- Maika believes it is querying team memory but reads a new empty local store.
- Different workers use different URLs/secrets and appear as one logical provider.
- Health endpoint being public is mistaken for authorization success.

### Required probe

Provider readiness must verify:

```yaml
server_instance_id:
store_id:
auth_required:
authenticated_principal:
tool_surface_hash:
memory_count_or_generation:
runtime_version:
```

A public health response alone is not sufficient.

# 4. Cross-repository questions

Codex cần đánh giá toàn hệ thống, không chỉ từng repo riêng lẻ.

## 4.1 Authority boundary

Xác định enforcement nằm ở đâu:

| Concern | Maika | MCP server | OS/container | Database |
|---|---|---|---|---|
| Source write scope |  |  |  | N/A |
| DB read/write permission |  |  | N/A |  |
| Human approval |  |  |  |  |
| DDL prevention |  |  | N/A |  |
| Graph freshness |  |  |  | N/A |
| Provider evidence integrity |  |  |  | N/A |
| Session authorization | N/A |  |  | N/A |

Điền rõ boundary nào là:

- hard;
- soft;
- advisory;
- prose-only.

## 4.2 Failure propagation

Kiểm tra các lỗi MCP có được truyền đúng đến Maika không:

```text
MCP isError
→ host response
→ maika provider record status
→ TRACE_EVIDENCE
→ gate result
→ workflow state
```

Xác định nơi error có thể biến thành success.

## 4.3 Contract versioning

Đề xuất versioned contracts cho:

```text
UA graph metadata
DB provider response
provider invocation record
trace evidence
database context
dispatch execution
```

Mỗi contract cần:

```yaml
contract_version:
producer:
producer_version:
schema_hash:
```

---

# 5. Output Codex cần trả về

## 5.1 Severity matrix

| ID | Finding | Verdict | Severity | Confidence | Blast radius | Blocks production |
|---|---|---:|---:|---:|---|---:|
| A | Cross-session authorization |  |  |  |  |  |
| B | Preview fail-open |  |  |  |  |  |
| C | False success |  |  |  |  |  |
| D | No human approval |  |  |  |  |  |
| E | Dynamic DDL bypass |  |  |  |  |  |
| F | UA metadata mismatch |  |  |  |  |  |
| G | Dirty tree freshness |  |  |  |  |  |
| H | Domain graph silent failure |  |  |  |  |  |
| I | Shell write bypass |  |  |  |  |  |
| J | Dispatch/write-gate mismatch |  |  |  |  |  |
| K | Lightweight archive |  |  |  |  |  |
| L | Workspace lock race |  |  |  |  |  |
| M | `.ua` directory discovery mismatch |  |  |  |  |  |
| N | `lastAnalyzedAt` metadata mismatch |  |  |  |  |  |
| O | `inherits`/`extends` edge mismatch |  |  |  |  |  |
| P | Producer-consumer schema drift |  |  |  |  |  |
| Q | CBM missing tool/mutability lanes |  |  |  |  |  |
| R | CBM `semantic_query` tool drift |  |  |  |  |  |
| S | Dual-graph evidence conflicts |  |  |  |  |  |
| T | CBM index generation not evidence-bound |  |  |  |  |  |
| U | AgentMemory proxy/local fallback split-brain |  |  |  |  |  |
| V | AgentMemory missing mutability lanes |  |  |  |  |  |
| W | Auto-capture bypasses Maika governance |  |  |  |  |  |
| X | Memory claims treated as authority |  |  |  |  |  |
| Y | Agent scope mistaken for authorization |  |  |  |  |  |
| Z | Dual memory lifecycle conflict |  |  |  |  |  |
| AA | Remote auth/store identity ambiguity |  |  |  |  |  |

## 5.2 Với mỗi confirmed finding

Trả về format:

```markdown
### FINDING-X

**Verdict:** CONFIRMED<br>
**Severity:** P0<br>
**Confidence:** High

**Exact root cause**
...

**Execution path**
1. ...
2. ...
3. ...

**Real impact**
...

**Minimal reproduction**
...

**Recommended fix**
...

**Regression tests**
...

**Compatibility/migration risk**
...
```

## 5.3 Patch roadmap

Chia thành:

### Wave 0 — Emergency safety

Các fix cần làm trước khi dùng production credential.

### Wave 1 — Runtime correctness

State, lock, error propagation, contracts.

### Wave 2 — Hardening

Sandbox, audit replay, schema versioning, chaos/concurrency tests.

---

# 6. Production readiness gates

Không coi hệ thống production-ready cho banking cho tới khi đạt:

- [ ] Db-Access session bind đúng source.
- [ ] Maika chỉ dùng dedicated read-only DB source mặc định.
- [ ] Preview failure fail-closed.
- [ ] SQL/Mongo failure không thể ghi nhận thành success.
- [ ] Script/DDL không dựa vào regex làm security boundary duy nhất.
- [ ] Producer → MCP contract tests dùng artifact thật từ Egonex Understand-Anything.
- [ ] MCP resolve đúng `.ua/` và legacy `.understand-anything/`.
- [ ] Metadata hỗ trợ đúng `lastAnalyzedAt`/legacy aliases.
- [ ] Edge `inherits` được trace đúng trong hierarchy và blast radius.
- [ ] UA metadata → Maika adapter contract test pass.
- [ ] Codebase Memory runtime `tools/list` được snapshot và contract-test.
- [ ] Codebase Memory tools được tách read/index/write/destructive lanes.
- [ ] Semantic-search capability có probe trên đúng public tool của binary đang dùng.
- [ ] Mỗi CBM observation bind với binary version + project + index generation/source state.
- [ ] UA ↔ CBM conflict policy bắt buộc current-source verification cho exact code facts.
- [ ] UA freshness detect dirty/staged/untracked relevant source.
- [ ] AgentMemory integration mode được pin: proxy-only hoặc local-only; không fallback âm thầm.
- [ ] AgentMemory runtime `tools/list` và tool-surface hash được contract-test.
- [ ] AgentMemory tools được chia recall/write/maintenance/destructive/coordination/team lanes.
- [ ] Auto-capture và automatic context injection bị tắt nếu Maika dùng MCP-only governance.
- [ ] Memory claims không thể pass exact-code/business-rule gates nếu chưa verify.
- [ ] Agent identity/namespace được enforce ngoài query parameter.
- [ ] Maika là owner duy nhất của canonical knowledge lifecycle.
- [ ] Remote AgentMemory readiness bind đúng server/store/principal, không chỉ health endpoint.
- [ ] Domain graph malformed được đánh dấu invalid/degraded.
- [ ] Write gate có post-execution scope validation.
- [ ] Review/authoring worker chạy được khi native hooks bật.
- [ ] Trivial/small lifecycle archive E2E pass.
- [ ] Lock concurrency/lease takeover tests pass.
- [ ] Full lifecycle test pass trên Linux và Windows.
- [ ] Audit trail có thể giải thích provider, request hash, response hash, model/worker, state transition và source diff.

---

# 7. Yêu cầu phản biện

Đừng chỉ đồng ý với các hypothesis.

Hãy chủ động tìm:

- Finding nào sai.
- Existing guard nào đã giải quyết.
- Edge case nghiêm trọng hơn chưa được liệt kê.
- Bug chỉ xuất hiện trên Windows.
- Bug chỉ xuất hiện khi multiple IDE/agent cùng dùng.
- Bug do hot reload.
- Bug do process crash giữa hai bước.
- TOCTOU giữa preview và execute.
- State corruption khi disk full hoặc move/rename fail.
- Audit record được ghi trước khi downstream normalization fail.
- Provider response hash đúng nhưng semantic response sai.
- Dependency graph/impact result bị stale hoặc incomplete.
- Untrusted graph path/source extraction.
- Credential/session leakage qua logs.
- Codebase Memory background watcher đổi graph giữa hai evidence probes.
- `delete_project` hoặc `manage_adr` bị gọi trong exploration lane.
- Query nhầm project khi nhiều repository dùng chung cache.
- Imported `.codebase-memory/graph.db.zst` không khớp current source.
- UA và CBM cùng báo healthy nhưng đang trỏ tới hai source revisions khác nhau.

---

# 8. Điều Codex không nên làm trong bước này

- Không refactor toàn hệ thống.
- Không merge implementation.
- Không đổi public contract khi chưa liệt kê compatibility impact.
- Không coi prompt instruction là hard enforcement.
- Không giả định MCP client luôn trung thực.
- Không giả định một agent duy nhất chạy tại một thời điểm.
- Không giả định repository clean.
- Không giả định DB credential là read-only.
- Không đánh dấu finding là P0 nếu không mô tả được execution path và side effect.

---

# 9. Kết quả cuối cùng mong muốn

Một tài liệu kỹ thuật có thể dùng để quyết định:

1. Finding nào là upstream bug, custom-MCP bug hay Maika integration bug.
2. Bug nào fix ngay và repo nào sửa trước.
3. Contract nào phải đồng bộ giữa sáu repo/layer.
4. Provider nào được authoritative cho từng loại claim.
5. Tool nào read-only, local-state write, destructive hoặc external side effect.
6. Test nào phải đưa vào CI và E2E provider matrix.
7. Điều kiện nào đủ để pilot Maika trong một Java Spring Boot banking repository.
8. Điều kiện nào đủ để bật AgentMemory recall mà không làm ô nhiễm canonical knowledge.
9. Điều kiện nào đủ để cấp read-only DB access.
10. Điều kiện nào bắt buộc trước khi cân nhắc source write, DB write hoặc script access.
