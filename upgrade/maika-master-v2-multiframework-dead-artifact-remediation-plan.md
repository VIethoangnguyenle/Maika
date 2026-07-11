---
status: implemented
runtime_authority: false
baseline_commit: 2d3a1f887349b20cd6675703f546edf74bde40d6
implemented_on: 2026-07-11
superseded_by:
  - docs/architecture/project-core-and-host-adapters.md
  - .maika/config/artifact-registry.yaml
---

# Maika `master-v2` Remediation Plan

## Multi-Framework Runtime Completion & Dead Artifact Cleanup

---

## 1. Mục tiêu

Plan này xử lý đồng thời hai vấn đề còn lại trên branch `master-v2`:

### Vấn đề A — Multi-framework chưa hoàn tất ở runtime

Maika đã có canonical core tại `.maika/`, nhiều platform có thể được enable cùng lúc, managed entrypoint, native hook theo platform và project config dùng chung. Tuy nhiên execution runtime vẫn có thể bị ràng buộc bởi platform dùng lúc `init`, thay vì platform đang thực sự chạy session hiện tại.

```text
Multi-host setup
≠
Multi-host execution
```

### Vấn đề B — Dead files và shadow implementations

Repository vẫn có một số thành phần:

- có code và có test nhưng không nằm trong production execution path;
- config cũ không còn ảnh hưởng runtime;
- procedure/template đã không còn consumer;
- plan lịch sử vẫn nằm trong retrieval surface;
- hai module cùng implement một policy.

```text
Test xanh cho policy A
nhưng runtime thực chạy policy B
```

Mục tiêu cuối:

> **Mỗi capability chỉ có một implementation canonical, và mọi host phải resolve runtime từ host hiện tại thay vì từ platform đã dùng để scaffold project.**

---

## 2. Baseline và phạm vi

```text
Repository: VIethoangnguyenle/Maika
Branch: master-v2
Baseline head khi lập plan: 1e64570f294f580304ad459a32de5dbd511c5d45
```

### In scope

- runtime platform resolution;
- per-platform worker profile;
- capability detection và verification;
- update tất cả enabled host adapters;
- transactional lifecycle;
- legacy migration;
- dead production modules;
- dead config fields;
- orphan scaffold artifacts;
- completed-plan context debt;
- CI enforcement cho artifact ownership và consumer.

### Out of scope

- thay đổi business workflow của Spec/Plan/Dev Loop;
- mở rộng trigger cho Macro Learning;
- thêm platform mới;
- redesign toàn bộ knowledge model;
- thay đổi semantic của Author DNA hoặc conventions;
- tối ưu dashboard UI.

---

## 3. Nguyên tắc thiết kế

### R1 — Project core là canonical

`.maika/` là runtime core duy nhất. Platform adapter không được sở hữu project knowledge, task state, archive, learning history, execution state machine hoặc shared workflow semantics.

### R2 — Host hiện tại quyết định runtime profile

Runtime worker không được resolve từ platform đã dùng khi `maika init`, mà từ:

```text
host/session hiện tại
→ verified platform adapter
→ per-platform runtime profile
```

### R3 — Một policy chỉ có một implementation

Không chấp nhận nhiều lớp cùng tự quyết worker strategy:

```text
cli/workers.py
execution-mode.yaml
orchestrator.py
doctor.py
```

Phải có một canonical resolver được mọi caller dùng.

### R4 — Test-only consumer không làm production module trở thành live

Một module production bị coi là shadow/dead khi chỉ được test import, chỉ được doctor đọc, không có production execution consumer, hoặc output không ảnh hưởng runtime decision.

### R5 — Shared host config chỉ được merge theo namespace

Maika-managed node phải có stable identity, ví dụ:

```text
maika.write-gate.v1
```

### R6 — Lifecycle operation phải atomic

Các operation `init`, `update`, `platform enable`, `platform disable`, `migrate`, `repair`, `uninstall` phải là một transaction hoàn chỉnh, không chỉ transaction phần scaffold rồi ghi metadata sau.

### R7 — Historical documentation không phải runtime authority

Plan/spec đã hoàn thành phải được đánh dấu implemented, không nằm trong default retrieval và không được dùng làm runtime contract.

---

## 4. Target architecture

### 4.1 Canonical project layout

```text
project/
├── .maika/
│   ├── config/
│   │   ├── project.yaml
│   │   ├── platforms.yaml
│   │   ├── install-manifest.yaml
│   │   └── artifact-registry.yaml
│   ├── runtime/
│   │   ├── current-session.yaml
│   │   ├── platforms/
│   │   │   ├── antigravity.yaml
│   │   │   ├── claude-code.yaml
│   │   │   └── codex.yaml
│   │   ├── transactions/
│   │   └── backups/
│   ├── knowledge/
│   ├── changes/
│   ├── archive/
│   ├── loops/
│   ├── rules/
│   ├── skills/
│   ├── workflows/
│   ├── procedures/
│   ├── profiles/
│   ├── hooks/
│   └── tools/
├── AGENTS.md
├── CLAUDE.md
├── .agents/
├── .claude/
└── .codex/
```

### 4.2 Platform runtime profile

Mỗi enabled platform có một runtime profile riêng:

```yaml
version: 1
platform: claude-code

adapter:
  enabled: true
  entrypoint: CLAUDE.md
  native_config: .claude/settings.json

detection:
  binary:
    path:
    version:
    found: true
    version_supported: true
  authentication:
    state: authenticated
  last_detected_at:

capabilities:
  entrypoint:
    state: verified
  hooks:
    state: verified
  fresh_process:
    state: verified
  native_subagent:
    state: unavailable
  mcp:
    state: detected

worker:
  strategy: fresh_process
  executable: claude
  args:
    - -p
    - --prompt-file
    - "{prompt_file}"
  dangerous_permissions: false
  timeout_seconds: 900

verification:
  hook_smoke_test: pass
  worker_smoke_test: pass
  last_verified_at:
```

Capability states:

```text
unsupported
advertised
detected
verified
degraded
unavailable
```

### 4.3 Current session resolution

Host hook hoặc CLI phải truyền platform hiện tại:

```yaml
version: 1
session_id:
platform: claude-code
source: native-hook
started_at:
last_seen_at:
```

Resolution order:

```text
explicit CLI --platform
→ hook runtime argument
→ current-session.yaml
→ project primary platform
→ fail with diagnostic
```

`primary` chỉ là fallback và UX default, không phải runtime truth tuyệt đối.

### 4.4 Canonical worker resolver

Production API:

```python
def resolve_worker_profile(
    project_root: Path,
    platform_key: str,
    user_override: dict | None = None,
) -> WorkerProfile:
    ...
```

Tất cả caller phải dùng API này:

- orchestrator;
- task apply;
- plan review;
- final review;
- doctor smoke test;
- repair verification;
- loop specialist dispatch.

Không caller nào được tự build worker argv.

---

## 5. Workstream A — Multi-Framework Runtime Completion

## Phase A0 — Baseline và invariant tests

### Tasks

1. Tạo architecture tests cho các invariant:
   - canonical core luôn `.maika`;
   - project có thể enable nhiều platform;
   - worker profile resolve theo active platform;
   - primary switch không tự đổi session đang chạy;
   - runtime không đọc worker config được render từ init platform.

2. Thêm test fail trước fix:

```text
init codex
enable claude-code
set primary claude-code
run task under claude hook
expected worker = claude
```

3. Thêm inverse test:

```text
init claude-code
enable codex
run task under codex hook
expected worker = codex
```

4. Ghi failure inventory tại:

```text
docs/refactor/master-v2/multihost-runtime-failures.md
```

### Exit criteria

- Test chứng minh được mismatch hiện tại.
- Không sửa expectation để hợp thức hóa runtime cũ.
- Có mapping test → production impact.

---

## Phase A1 — Tách worker config khỏi shared execution profile

### Hiện trạng cần loại bỏ

Shared file `.maika/profiles/execution-mode.yaml` không được chứa worker executable/args phụ thuộc platform.

### Target

Giữ trong shared profile chỉ các policy chung:

```yaml
version: 2
workflow_engine: vnext

runtime_policy:
  max_retries: 2
  worker_timeout_seconds: 900
  token_budget: {}
  command_policy: {}
```

Chuyển platform-specific worker settings sang:

```text
.maika/runtime/platforms/<platform>.yaml
```

### Tasks

1. Tạo schema `PlatformRuntimeProfile`.
2. Tạo loader `load_platform_runtime_profile(project_root, platform_key)`.
3. Tạo validator cho platform key, worker executable, dangerous permission và capability state.
4. Migrate existing rendered worker config thành per-platform profile.
5. Bỏ platform Jinja branch khỏi `execution-mode.yaml`.
6. Update package assets và scaffold snapshots.

### Tests

- Shared execution profile byte-identical giữa Claude, Codex và Antigravity.
- Per-platform runtime profile khác nhau đúng ở worker/adapter data.
- Missing platform profile → block với remediation.
- Unknown strategy → fail closed.

### Exit criteria

Shared core không còn chứa platform-specific worker command.

---

## Phase A2 — Hợp nhất worker policy

### Quyết định

Giữ `cli/workers.py` nhưng chuyển nó thành canonical runtime module và bắt mọi execution path sử dụng.

Đề xuất:

```text
cli/workers.py
→ cli/runtime/worker_resolver.py
```

API:

```python
@dataclass(frozen=True)
class WorkerProfile:
    platform: str
    strategy: str
    executable: str | None
    args: tuple[str, ...]
    timeout_seconds: int
    dangerous_permissions: bool
    reason: str
```

Functions:

```python
resolve_worker_profile(...)
build_worker_argv(...)
validate_worker_profile(...)
run_worker_smoke_test(...)
```

Selection order:

```text
trusted explicit override
→ verified native subagent
→ verified fresh-process CLI
→ safe inline fallback
→ disabled/block
```

Rules:

- `detected` không đủ để chọn high-trust capability.
- Fresh process yêu cầu binary + supported version.
- Dangerous flag chỉ khi project config opt-in, current command explicit opt-in và audit event được ghi.
- Không append prompt text vào shell command.
- Prompt file luôn là một argv element.
- `shell=False`.

Consumers phải migrate:

- `.maika/tools/microloop-orchestrator/orchestrator.py`;
- `.maika/tools/microloop-orchestrator/vnext_dispatch.py`;
- CLI task apply/review paths;
- setup doctor;
- loop specialist dispatch;
- worker smoke test.

### Tests

- Orchestrator gọi canonical resolver.
- Doctor và runtime trả cùng strategy.
- Dangerous flag không xuất hiện mặc định.
- User override hợp lệ được bind đúng platform.
- Profile của Claude không thể được dùng cho Codex.
- Path có space và Unicode vẫn hoạt động.
- Windows và Linux dùng cùng structured argv semantics.

### Exit criteria

Repository chỉ còn một worker strategy implementation.

---

## Phase A3 — Session-aware platform resolution

### Tasks

1. Mở rộng hook CLI:

```bash
maika hook write-gate --runtime claude --platform claude-code
```

2. Hook ghi/update lightweight session record tại `.maika/runtime/current-session.yaml`.
3. CLI task command nhận `--platform`.
4. Runtime resolver sử dụng platform argument thay vì platform trong resolved config cũ.
5. Primary platform chỉ dùng khi không có current session/platform input.
6. Thêm stale session timeout.
7. Multi-process lock cho session record.

### Security

Agent-authored file không được tự đổi trusted current platform. Trusted sources gồm native hook invocation, explicit user CLI và verified launcher wrapper.

### Tests

- Claude hook → Claude worker.
- Codex hook → Codex worker.
- Session record stale → fallback primary.
- Conflicting active sessions → block hoặc yêu cầu explicit platform.
- Agent sửa current-session file trực tiếp → không được coi trusted nếu thiếu runtime source.

### Exit criteria

Worker selection phản ánh host hiện tại.

---

## Phase A4 — Capability verification

### Tasks

1. Refactor detection thành ba bước:

```text
advertise
→ detect
→ verify
```

2. Platform adapter implement:

```python
detect_binary()
detect_version()
detect_authentication()
verify_entrypoint()
verify_hook()
verify_worker()
verify_mcp()
```

3. Persist result vào per-platform runtime profile.
4. Thêm support tier:

```text
Tier 0 — scaffold only
Tier 1 — config integrated
Tier 2 — hook + worker verified
Tier 3 — full capability verified
```

5. `maika status` hiển thị tier thật.
6. `maika doctor platform --verify` chạy smoke test.

### Smoke tests

- Hook: feed safe payload, expect valid contract, confirm canonical evaluator found.
- Worker: spawn no-write prompt, read safe file, output structured response, cleanup timeout.
- MCP: verify provider/tool visibility, không log secret.

### Exit criteria

Không platform nào được claim “supported” chỉ vì binary tồn tại.

---

## Phase A5 — Update mọi enabled adapter

### Tasks

Refactor `maika update`:

```text
load canonical project config
→ stage core once
→ stage adapter cho từng enabled platform
→ stage metadata/version
→ verify all
→ commit one transaction
```

Update semantics:

- core framework-owned: update;
- project-owned knowledge/state: preserve;
- each enabled adapter: update;
- disabled adapter: không tạo lại;
- stale adapter: report;
- failed adapter: rollback toàn operation.

### Tests

- Enable Claude + Codex + Antigravity, update → cả ba adapter thay đổi.
- Một adapter merge lỗi → core và adapter khác rollback.
- Knowledge hash không đổi.
- Primary không bị đổi.
- Update idempotent.

### Exit criteria

Không enabled platform nào bị stale sau update thành công.

---

## Phase A6 — Transactional lifecycle hoàn chỉnh

### Operation transaction phải bao phủ

```text
core files
host entrypoints
host JSON config
project.yaml
platforms.yaml
install-manifest.yaml
runtime profiles
backup metadata
```

### Tasks

1. Mở rộng transaction action types: write YAML, managed Markdown merge, structural JSON merge, remove managed block, remove namespaced JSON node, create/delete directory, migrate file và metadata update.
2. Persist journal trước write đầu tiên tại `.maika/runtime/transactions/<transaction-id>.yaml`.
3. Commit marker sau operation thành công.
4. Thêm `maika repair --transaction <id>`.
5. Không xóa backup trước khi toàn operation committed.
6. Uninstall cũng dùng transaction.

### Tests

Inject failure sau từng boundary: core sync, entrypoint merge, hook merge, metadata write, uninstall và migration.

Expected:

```text
all committed
hoặc
state byte-equivalent trước operation
```

### Exit criteria

Không còn partial install/update/platform operation.

---

## Phase A7 — Migration thật từ legacy roots

### Tasks

1. Detect `.agents`, `.claude` và legacy `.maika` layout.
2. Inventory file ownership.
3. Hash project-owned artifacts.
4. Detect identical copies, divergent copies, canonical missing và unknown ownership.
5. Generate migration plan.
6. Apply move/merge project-owned data, install canonical core, install enabled adapters và preserve conflicts.
7. Không auto chọn “file mới nhất” cho knowledge conflict.
8. Legacy roots read-only trong compatibility window.
9. Cleanup chỉ sau verification + explicit confirmation.

Conflict artifact:

```yaml
version: 1
conflicts:
  - logical_artifact:
    candidates: []
    hashes: []
    decision_required: true
```

### Exit criteria

Platform switch hoặc upgrade không làm mất knowledge/history.

---

## 6. Workstream B — Dead Files, Dead Config & Shadow Implementation Cleanup

## Phase B0 — Artifact inventory

Tạo canonical artifact registry:

```text
.maika/config/artifact-registry.yaml
```

Schema:

```yaml
version: 1
artifacts:
  - path: cli/runtime/worker_resolver.py
    type: runtime
    ownership: framework
    producer: source
    consumers:
      - microloop-orchestrator
      - setup-doctor
    scaffolded: false
    runtime_authority: true
    status: active
```

Types:

```text
runtime
adapter
config
template
documentation
test
historical
migration
```

Status:

```text
active
compatibility
deprecated
historical
candidate-delete
```

Mỗi production artifact phải có producer, ít nhất một production consumer, ownership, runtime authority và lifecycle status. Test không được tính là production consumer.

Output audit:

```text
docs/refactor/master-v2/artifact-consumer-audit.yaml
```

### Exit criteria

Có danh sách evidence-backed cho live, shadow, dead, compatibility và historical artifacts.

---

## Phase B1 — Xử lý `cli/workers.py`

Được giải quyết cùng Phase A2.

Acceptance riêng:

- module mới có production imports;
- orchestrator không còn tự build worker command;
- test worker policy test actual runtime path;
- không còn duplicate strategy constants.

---

## Phase B2 — Xóa dead `hook_python` contract

### Candidate removal

- CLI option `--hook-python`;
- `run_init(...hook_python=...)`;
- `run_update(...hook_python=...)`;
- platform render context field;
- resolved-config field;
- persistence tests;
- Windows CI assertion;
- docs hướng dẫn.

### Pre-delete verification

```bash
rg -n "hook_python|--hook-python" .
```

Phân loại từng hit thành runtime consumer, test-only, historical doc hoặc installer.

### Migration

Existing project có field cũ thì config loader ignore có warning trong một compatibility release. Sau compatibility window, schema migration xóa key và repair command cleanup config.

### Tests

- Hook command vẫn hoạt động Windows/Linux.
- Init/update không nhận option cũ.
- Old config có field cũ không crash.
- Doctor báo deprecated field.
- Repair xóa field an toàn.

### Exit criteria

Không còn code/test bảo vệ launcher không được runtime sử dụng.

---

## Phase B3 — Xác định vai trò của platform detection

Detection phải trở thành input chính thức của platform enable, runtime profile generation, worker selection, support tier, repair và doctor.

### Tasks

1. Move `cli/platforms/detection.py` → `cli/platforms/probe.py`.
2. Return typed result.
3. Persist only verified/detected facts.
4. Remove duplicated detection trong doctor/platform adapters.
5. Wire vào `platform enable`.
6. Platform enable phải block khi canonical core thiếu.
7. Platform enable có thể cài adapter ở Tier 1, nhưng phải ghi rõ worker chưa verified.

### Exit criteria

Detection result ảnh hưởng production behavior có kiểm soát.

---

## Phase B4 — Xóa orphan scaffold artifacts

Candidate đầu tiên:

```text
.maika/procedures/token-tracking.md
```

Audit:

```bash
rg -n \
  "token-tracking\.md|TOKEN_LOG|Token Tracking" \
  .maika cli scripts \
  --glob '!**/tests/**'
```

Xóa nếu không có runtime consumer, không được bootstrap/workflow load, metrics đã có canonical implementation khác và manifest chỉ còn là consumer giả.

Khi xóa, cập nhật plugin manifest, snapshots, asset validation, docs, deletion manifest và stale reference tests.

Audit các candidate khác theo cùng rule: procedure chỉ còn pointer ngắn nhưng không được load, template không có producer/consumer, profile không được runtime đọc, README chỉ scaffold nhưng không có user-facing reference.

### Exit criteria

Manifest không scaffold artifact không có consumer.

---

## Phase B5 — Dọn completed plans khỏi runtime retrieval

Các file như `MaikaImprove.md`, `upgrade/*.md`, `MAIKA_VNEXT_MASTER_REFACTOR_PLAN.md`, `docs/superpowers/plans/*` và `docs/superpowers/specs/*` có giá trị lịch sử nhưng có thể gây retrieval noise.

### Tasks

1. Tạo `docs/archive/implemented/`.
2. Thêm frontmatter:

```yaml
status: implemented
runtime_authority: false
baseline_commit:
implemented_on:
superseded_by:
```

3. Di chuyển completed plans hoặc thêm index trạng thái.
4. Knowledge/index source loại `runtime_authority: false` khỏi default reasoning retrieval.
5. Chỉ truy xuất historical docs khi query yêu cầu history, rationale, migration hoặc regression analysis.
6. README developer docs vẫn link được tới archive.

### Tests

- Default knowledge slice không chứa implemented plan.
- Explicit history query vẫn tìm được.
- Current ADR/spec có runtime authority cao hơn archived plan.

### Exit criteria

Historical documents không cạnh tranh với current runtime contract.

---

## Phase B6 — Xóa duplicate policy và dead helper

### Audit targets

```text
cli/scaffold.py
cli/config/platforms.py
cli/commands/lifecycle.py
cli/commands/doctor.py
cli/commands/status.py
cli/platforms/*
.maika/tools/microloop-orchestrator/*
```

### Method

Với mỗi function/class:

1. tìm production import/call;
2. tìm dynamic import;
3. tìm CLI registration;
4. tìm template reference;
5. tìm test-only use;
6. phân loại.

Không xóa chỉ vì `rg function_name` ít kết quả nếu module được dynamic import. Cần kiểm `importlib`, file-based dispatch, manifest, string route names và CLI parser registration.

Output:

```text
docs/refactor/master-v2/dead-code-decisions.yaml
```

Schema:

```yaml
path:
symbol:
status: delete | keep | compatibility | wire
evidence:
replacement:
tests:
```

---

## Phase B7 — Dead artifact CI gate

### New script

```text
scripts/audit_artifacts.py
```

### Checks

1. Manifest source exists.
2. Manifest output có declared consumer.
3. Production module chỉ được test import → fail.
4. Duplicate policy owner → fail.
5. Deprecated config quá expiry → fail.
6. Historical plan có `runtime_authority: true` → fail.
7. Deleted path/name xuất hiện trong live runtime docs/code → fail.

Cho phép compatibility annotation:

```yaml
status: compatibility
expires_after:
```

CI integration:

```text
python scripts/audit_artifacts.py
```

chạy trước full test suite.

### Exit criteria

Dead artifact không thể tái xuất hiện âm thầm.

---

## 7. Structural JSON merge hardening

Target hook node:

```json
{
  "id": "maika.write-gate.v1",
  "type": "command",
  "command": "maika hook write-gate --runtime claude --platform claude-code"
}
```

### Tasks

1. Không detect ownership bằng substring toàn subtree.
2. Parse đúng host schema.
3. Locate node theo `id`.
4. Update/remove đúng leaf.
5. Preserve sibling hooks trong cùng matcher.
6. Duplicate ID → block và repair.
7. Unknown Maika schema version → block, không đoán.
8. Uninstall xóa đúng node.

### Tests

- Team hook và Maika hook cùng matcher.
- Two Maika IDs duplicate.
- Unknown Maika ID version.
- Nested unrelated command có chuỗi `.maika`.
- Disable một platform không xóa shared hook của platform khác.
- Byte preservation cho unrelated config.

---

## 8. Write-gate lifecycle hardening

### Tasks

1. Project root discovery: Git root, parent walk tìm `.maika/config/project.yaml`, explicit target fallback.
2. Policy:

```text
không phải Maika project
→ allow

canonical Maika project nhưng evaluator mất/hỏng
→ deny

Maika config malformed
→ deny + repair command
```

3. `maika hook` load active platform runtime profile.
4. Hook smoke test dùng actual installed path.
5. Missing CLI phải trả diagnostic rõ.
6. Không fail-open khi installation đã tồn tại nhưng incomplete.

### Tests

- non-Git nested directory;
- canonical config + missing evaluator;
- no Maika project;
- broken config;
- CLI outside PATH;
- Windows path.

---

## 9. CLI changes

```text
maika platform verify <platform>
maika platform status <platform>
maika runtime current
maika runtime set-platform <platform>
maika runtime worker-profile <platform>

maika doctor artifacts
maika doctor platform --verify
maika repair --all-safe
maika repair --transaction <id>

maika migrate --plan
maika migrate --apply
maika migrate --cleanup-legacy
```

Status output phải có core health, enabled platforms, support tier, current runtime platform, worker strategy, hook state và artifact hygiene.

---

## 10. File-level implementation map

### Multi-framework runtime

```text
cli/runtime/worker_resolver.py                       NEW/refactor
cli/runtime/session.py                               NEW
cli/runtime/platform_profile.py                      NEW
cli/platforms/probe.py                               REFACTOR
cli/platforms/base.py                                MODIFY
cli/platforms/antigravity.py                         MODIFY
cli/platforms/claude_code.py                         MODIFY
cli/platforms/codex.py                               MODIFY
cli/commands/platform.py                             MODIFY
cli/commands/task.py                                 MODIFY
cli/commands/doctor.py                               MODIFY
cli/commands/status.py                               MODIFY
cli/commands/update.py                               MODIFY
cli/commands/init.py                                 MODIFY
cli/commands/lifecycle.py                            MODIFY
cli/config/project.py                                MODIFY
cli/config/platforms.py                              MODIFY
cli/install/transaction.py                           MODIFY
cli/install/planner.py                               MODIFY
.maika/profiles/execution-mode.yaml                  MODIFY
.maika/tools/microloop-orchestrator/orchestrator.py  MODIFY
.maika/tools/microloop-orchestrator/vnext_dispatch.py MODIFY
```

### Dead artifact cleanup

```text
cli/workers.py                                  MOVE/DELETE after migration
cli/platforms/detection.py                      MOVE/DELETE after migration
.maika/procedures/token-tracking.md             DELETE if audit confirms
cli/plugin-manifest.yaml                        MODIFY
cli/tests/test_hook_python_persistence.py       DELETE/REPLACE
scripts/audit_artifacts.py                      NEW
.maika/config/artifact-registry.yaml            NEW template
docs/archive/implemented/                       NEW
docs/refactor/master-v2/artifact-consumer-audit.yaml NEW
docs/refactor/master-v2/dead-code-decisions.yaml NEW
```

### Hook/config hardening

```text
cli/scaffold.py                                 MODIFY
cli/install/json_merge.py                       NEW or extract
cli/install/markdown_merge.py                   NEW or extract
cli/commands/hook.py                            MODIFY
.maika/hooks/*                                  MODIFY
```

---

## 11. PR slicing đề xuất

1. **PR 1 — Runtime invariants and failing tests**: architecture tests, artifact inventory, chưa đổi production behavior.
2. **PR 2 — Per-platform runtime profiles**: shared profile cleanup, profile schema/loader, migration compatibility.
3. **PR 3 — Canonical worker resolver**: wire orchestrator, remove duplicate worker construction, remove dangerous default.
4. **PR 4 — Session-aware host resolution**: current session, hook platform propagation, active platform resolution.
5. **PR 5 — Capability verification**: probe API, smoke tests, support tiers, status/doctor.
6. **PR 6 — Full lifecycle transaction**: transaction boundary, metadata, host config, rollback/recovery.
7. **PR 7 — Multi-adapter update + migration**: update all enabled platforms, real legacy migration.
8. **PR 8 — Dead contract cleanup**: remove `hook_python`, compatibility migration, stale tests/docs.
9. **PR 9 — Orphan and historical cleanup**: token-tracking decision, archive completed plans, retrieval filtering.
10. **PR 10 — Dead artifact CI gate**: artifact registry, audit script, CI integration.

---

## 12. Test strategy

### Unit

- platform runtime profile schema;
- platform resolution order;
- worker profile selection;
- dangerous permission gate;
- capability state transition;
- JSON node identity;
- transaction actions;
- artifact registry validation;
- historical authority filtering.

### Integration

```text
init codex
enable claude
run as claude
→ claude worker
```

```text
init claude
enable codex
run as codex
→ codex worker
```

Các case khác:

- no session → primary fallback;
- two sessions conflict;
- update three platforms;
- rollback after injected failure;
- knowledge hash unchanged.

### E2E

- Claude Code hook + worker smoke;
- Codex hook + worker smoke;
- Antigravity adapter/hook;
- multi-host handoff trên cùng task state;
- wheel install khi source checkout bị xóa.

### Dead artifact tests

- production module chỉ test import → fail audit;
- manifest-only orphan → fail;
- compatibility artifact còn hạn → pass;
- compatibility artifact hết hạn → fail;
- historical plan bị indexed mặc định → fail;
- duplicate policy owner → fail;
- stale deleted path reference → fail.

### Cross-OS

- Ubuntu;
- Windows;
- CRLF;
- Unicode path;
- path có space;
- no Git repository;
- nested working directory.

---

## 13. Observability

Runtime metrics:

```yaml
platform_runtime:
  selected_platform:
  selection_source:
  worker_strategy:
  capability_tier:
  fallback_used:
  hook_verified:
  worker_verified:
```

Lifecycle metrics:

```yaml
lifecycle:
  operation:
  transaction_id:
  actions:
  duration:
  rollback:
  repair_required:
```

Artifact hygiene:

```yaml
artifact_hygiene:
  active:
  compatibility:
  deprecated:
  historical:
  shadow:
  dead_candidates:
  duplicate_policy_domains:
```

---

## 14. Rollout

### Stage 1 — Shadow resolution

Runtime vẫn dùng config cũ nhưng log legacy worker và canonical resolver would-select worker.

### Stage 2 — Canonical resolver opt-in

```yaml
runtime:
  platform_resolution: canonical
```

### Stage 3 — Canonical default

Legacy worker resolution chỉ còn compatibility fallback.

### Stage 4 — Remove legacy

Xóa shared platform-specific worker config, old resolver, dead options và stale tests.

### Stage 5 — Enforce artifact gate

Dead artifact audit trở thành required CI check.

---

## 15. Rollback strategy

### Runtime resolver

Giữ compatibility switch một release:

```yaml
runtime:
  worker_resolver: legacy | canonical
```

Không giữ hai implementation vô thời hạn.

### Config migration

Mỗi schema migration phải backup, atomic write, record migration ID và support rollback.

### Adapter update

Nếu một adapter fail, rollback core update, rollback adapter khác và giữ enabled platform list cũ.

### Artifact deletion

Trước xóa phải có consumer audit, stale reference scan, full CI và downstream scaffold snapshot.

---

## 16. Acceptance criteria

### Multi-framework

1. Shared `.maika` core không chứa worker command phụ thuộc platform.
2. Mỗi enabled platform có runtime profile riêng.
3. Host hiện tại quyết định worker profile.
4. `primary` chỉ là fallback.
5. Orchestrator dùng canonical worker resolver.
6. Doctor và runtime dùng cùng resolver.
7. Dangerous permission mặc định false.
8. Capability phân biệt advertised/detected/verified.
9. Hook và worker có smoke test thật.
10. Update xử lý tất cả enabled adapters.
11. Platform enable từ project thiếu core bị chặn.
12. Init/update/enable/disable/migrate/uninstall atomic.
13. Migration legacy thực sự copy/merge dữ liệu.
14. Multi-host E2E pass trên cùng task state.

### Dead artifacts

15. `cli/workers.py` không còn shadow.
16. Platform detection không còn diagnostic-only shadow.
17. `hook_python` contract bị loại bỏ.
18. Không test nào bảo vệ config không còn consumer.
19. `token-tracking.md` được wire thật hoặc xóa.
20. Manifest không scaffold artifact không có consumer.
21. Completed plans không còn runtime authority.
22. Default retrieval không nạp historical implemented plans.
23. Production module test-only consumer bị CI phát hiện.
24. Duplicate policy domains bị CI phát hiện.
25. Deprecated compatibility artifact có expiry.
26. Deletion manifest đồng bộ với tree thật.
27. Full CI xanh trên `master-v2`.
28. Windows install E2E dùng canonical `.maika` assertions.
29. Wheel install E2E pass khi source repo không tồn tại.
30. `maika doctor artifacts` không còn Critical/High finding.

---

## 17. Definition of Done

Một feature multi-framework chỉ hoàn thành khi:

```text
host được enable
→ config merge an toàn
→ capability được verify
→ worker profile được resolve đúng host
→ hook chạy thật
→ task chạy bằng shared project state
→ update/migrate/uninstall có rollback
```

Một artifact chỉ được coi live khi:

```text
có producer
→ có production consumer
→ có owner
→ có runtime authority rõ
→ có test trên actual path
```

---

## 18. Trạng thái đích

Trước remediation:

```text
Maika có nhiều host adapter,
nhưng runtime và policy vẫn có thể phụ thuộc init platform
và tồn tại code có test nhưng không được execution path dùng.
```

Sau remediation:

```text
Maika là một project-native runtime duy nhất,
mỗi host dùng adapter và runtime profile riêng,
mọi policy có một implementation canonical,
và CI ngăn dead/shadow artifacts quay trở lại.
```

> **Multi-framework chỉ thật sự hoàn thành khi cùng một project có thể chuyển host mà không đổi bộ não, không đổi state, không chạy nhầm worker và không mang theo những policy đã chết.**
