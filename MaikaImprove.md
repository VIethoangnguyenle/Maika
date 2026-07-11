# Maika Adaptive Workflow Remediation Plan

## Trạng thái triển khai (cập nhật 2026-07-11)

| Phase | Trạng thái | Bằng chứng hiện tại |
|---|---|---|
| 0 — CI baseline | Hoàn tất | Failure inventory đã có; commit `347504d`; full local CI xanh. |
| 1 — Lightweight execution contract | Hoàn tất trong worktree | Contract trusted có task/evidence/scope hash, Git baseline, lease; state chuyển `EXECUTING` trước dispatch; write-gate hỗ trợ lightweight; actual diff bị đối chiếu scope; public small E2E sửa application file thật. |
| 2 — Deterministic risk classification | Hoàn tất trong worktree | Runtime derive file/module/path/content signals từ repo, hỗ trợ configurable rules, giữ requested/effective class riêng, monotonic escalation và tự nâng source code khỏi trivial. |
| 3 — Safe verification execution | Hoàn tất trong worktree | Verification dùng trusted profiles/compiler, structured argv `shell=False`, path/parameter validation, chống repo-local executable, config wiring và CLI approval hash-bound; agent-authored human confirmation bị ignore. |
| 4 — Exit code/BLOCKED/resume | Hoàn tất | Commit `588bba6`; blocked không còn trả 0 và resume có contract. |
| 5 — Runtime/token budget | Hoàn tất trong worktree | Có canonical `RuntimePolicy`, project override cho worker/retry/token policy, deterministic evidence trim, context gate và metrics tách actual/estimated tokens cùng prompt/evidence counts. |
| 6 — Knowledge slice/freshness | Hoàn tất trong worktree | Production dùng canonical `select_knowledge_slice`: status/supersession/scope/authority/digest/revalidation/ranking/budget; capsule có provenance/reuse decision và metrics reject/omit chính xác. |
| 7 — Cross-platform worker | Hoàn tất trong worktree | Prompt-file là default, worker/verification dùng process-group timeout đa nền tảng, CRLF review normalization và placeholder/path validation có regression tests. |
| 8 — Concurrency | Hoàn tất trong worktree | Lifecycle mutations dùng workspace lock; lock có lease/heartbeat/expiry/audit, remote policy và force-unlock; task queue dùng generation CAS. |
| 9 — Learning safety | Hoàn tất trong worktree | Candidate threshold cần verified recurrence/reproducibility/impact/readiness; promotion bắt buộc completed evaluation/canary; exact backup/hash rollback phục hồi canary regression và poisoning bị chặn. |

Verification gần nhất: `python3 scripts/run_ci.py` — 776 passed, 1 skipped.

## 1. Mục tiêu

Hoàn thiện Adaptive Workflow của Maika để đạt đồng thời bốn mục tiêu:

1. Task `trivial` và `small` thực sự dùng ít artifact, ít worker call và ít token.
2. Fast path vẫn chịu write-gate và verification gate như full path.
3. Runtime không tin mù quáng vào claim do agent tự khai báo.
4. Mọi config về token, command, retry và timeout thực sự điều khiển runtime.

Nguyên tắc kiến trúc:

> Lightweight workflow không được là workflow “ít kiểm soát hơn”.
> Nó phải là workflow có contract nhỏ hơn nhưng vẫn enforce cơ học.

---

# 2. Findings cần xử lý

## 2.1 Critical — Fast path không tương thích với write-gate

Hiện tại `trivial/small` chạy worker khi state vẫn là `INTAKE`, rồi mới chuyển sang `EXECUTING` và `VERIFYING`.

Trong khi write-gate chỉ cho phép write khi:

* có đúng một change `EXECUTING`;
* có `PLAN_VALIDATION.json`;
* có `PLAN_MANIFEST.json`;
* có `TASK_QUEUE.json`;
* có đúng một task `in_progress`.

Fast path lại chủ ý không có full-plan artifacts.

Kết quả: worker fast path không thể sửa application code thật qua write-gate.

---

## 2.2 Critical — Command policy vẫn cho phép arbitrary code execution

Runtime đã dùng `shell=False`, nhưng allowlist vẫn chứa:

* `python`
* `python3`
* `npm`
* `pnpm`
* `git`
* `mvn`
* `go`
* `cargo`

Ví dụ sau vẫn hợp lệ:

```yaml
executable: python
args:
  - -c
  - "import shutil; shutil.rmtree('src')"
```

Ngoài ra, basename allowlist có thể chấp nhận binary giả như `/tmp/python`, vì policy normalize bằng basename.

`human_confirmed` hiện được đọc trực tiếp từ artifact do agent có thể ghi.

---

## 2.3 High — Risk classifier chưa thực sự deterministic từ repo state

CLI mặc định:

```text
--class small
```

Fast workspace khởi tạo risk signal bằng zero:

```yaml
estimated_files: 0
affected_modules: 0
unknown_count: 0
```

Runtime chưa tự derive:

* file count từ scope;
* module count từ path;
* contract impact;
* DB/event/concurrency/security signal;
* actual touched files từ Git diff.

---

## 2.4 High — Token budget mới chủ yếu là cấu hình trang trí

Config có `max_context_tokens`, `max_worker_calls`, `max_evidence_items`.

Nhưng runtime:

* dùng constant hard-code;

* mới enforce worker-call budget;

* chưa enforce evidence count;

* chưa enforce prompt/context size;

* chưa đọc project override;

* chưa estimate token khi platform không trả usage.

---

## 2.5 High — Command policy config chưa nối vào runtime

`execution-mode.yaml` khai báo:

```yaml
command_policy:
  allowed_executables:
  requires_human_confirmation:
  timeout_seconds:
  output_cap_bytes:
```

Nhưng verification runner không truyền config vào `execute_command()`.

---

## 2.6 High — Evidence reuse production path chưa qua freshness validator

`can_reuse_evidence()` đã kiểm digest, authority và supersession.

Nhưng `plan_compiler._active_project_knowledge()` vẫn coi mọi entry active match keyword là reused.

Điều này có thể làm:

* stale knowledge đi vào capsule;
* `evidence_reuse_ratio` bị thổi phồng;
* worker reasoning dựa trên claim cũ.

---

## 2.7 High — `apply` trả exit code 0 khi task bị block

`run_queue()` có thể trả `blocked`, nhưng orchestrator vẫn return `0` nếu outcome không phải `done` hoặc `stale_plan`.

Test hiện còn hợp thức hóa behavior này.

---

## 2.8 High — Cross-platform worker/review handling chưa an toàn

Structured review parser yêu cầu literal newline `\n`, chưa normalize CRLF.

Worker command vẫn dùng:

```python
shlex.quote(prompt)
subprocess.run(..., shell=True)
```

Đây là POSIX-oriented và không ổn định trên Windows.

---

## 2.9 Merge blocker — CI đang đỏ

Head mới nhất có:

* Ubuntu test job fail;

* Windows test job fail;

* PowerShell install E2E pass.

CI phải xanh trước merge.

---

# 3. Target architecture

## 3.1 Unified execution contract

Thay vì write-gate chỉ hiểu full plan path, tạo một contract chung:

```text
Execution Contract
├── full
│   ├── PLAN_MANIFEST.json
│   ├── TASK_QUEUE.json
│   └── task in_progress
└── lightweight
    ├── TASK.yaml
    ├── LIGHTWEIGHT_EXECUTION.yaml
    └── state EXECUTING
```

Write-gate phải kiểm:

```text
Có đúng một active execution contract
→ contract còn fresh
→ target nằm trong declared scope
→ role được phép ghi target
```

Không phụ thuộc workflow có nhiều hay ít artifact.

---

## 3.2 Trusted runtime boundaries

Phân biệt rõ:

```text
Agent-authored artifact
Trusted runtime decision
Human approval
```

Agent-authored artifact không được tự quyết:

* human approval;
* executable permission;
* state transition;
* worker ownership;
* verification trust level;
* skill promotion.

---

## 3.3 Mechanical observation over self-report

Không tin tuyệt đối vào:

```yaml
touched_files:
  - src/a.py
```

do worker tự ghi.

Runtime phải tính actual diff:

```bash
git diff --name-only <base-revision>
git status --porcelain
```

Sau đó so sánh:

```text
declared scope
vs
actual touched files
```

Agent report chỉ là metadata bổ sung.

---

# 4. Phase 0 — Stabilize CI và baseline

## 4.1 Reproduce CI locally

Chạy đúng command GitHub Actions dùng:

```bash
python scripts/run_ci.py
```

Trên:

* Ubuntu hoặc Linux local;
* Windows hoặc GitHub runner;
* Python 3.11.

Không dùng subset test làm bằng chứng full pass.

## 4.2 Ghi failure inventory

Tạo:

```text
docs/refactor/maika-vnext/adaptive-remediation-failures.md
```

Cho mỗi failure:

```yaml
test:
platform:
failure:
root_cause:
production_impact:
fix:
regression_test:
```

## 4.3 Không đổi expectation để “làm xanh”

Không được sửa test từ:

```text
blocked → exit 1
```

thành:

```text
blocked → exit 0
```

chỉ để hợp thức hóa behavior cũ.

Test chỉ được đổi nếu contract mới đã được quyết định và document.

## Exit criteria Phase 0

* Biết chính xác từng failing test.
* Có mapping failure → production issue.
* Không còn failure không giải thích được.
* Baseline artifact được commit.

---

# 5. Phase 1 — Lightweight execution contract

## 5.1 Tạo schema `LIGHTWEIGHT_EXECUTION.yaml`

Đường dẫn:

```text
<workspace>/generated/LIGHTWEIGHT_EXECUTION.yaml
```

Schema:

```yaml
version: 1

change_id: small-task
task_class: small
execution_id: EXEC-small-task-001

state: EXECUTING

task_hash: sha256:...
evidence_hash: sha256:...
scope_hash: sha256:...

role: application-implementer

scope:
  create: []
  modify:
    - src/a.py
  delete: []
  test:
    - tests/test_a.py

base_revision:
  git_head: abc123
  worktree_digest: sha256:...

runtime:
  owner_pid: 1234
  owner_host: hostname
  started_at: ...
  lease_expires_at: ...

status: active
```

## 5.2 Canonical generator

Thêm vào:

```text
adaptive_runtime.py
```

API:

```python
def build_lightweight_execution_contract(
    workspace: Path,
    repo_root: Path,
    task: dict,
    state: dict,
    owner: RuntimeOwner,
) -> dict:
    ...
```

Nó phải:

* validate task class là trivial/small;
* derive scope từ `TASK.yaml`;
* reject empty application scope;
* hash `TASK.yaml`;
* hash `EVIDENCE.yaml` nếu small;
* lấy Git HEAD;
* tính worktree digest;
* tạo execution ID;
* ghi atomic;
* không cho agent tự tạo contract.

## 5.3 State transition đúng thứ tự

Flow mới:

```text
INTAKE
→ preflight
→ build lightweight contract
→ transition EXECUTING
→ dispatch worker
→ validate actual diff
→ VERIFYING
```

Không được dispatch worker trước `EXECUTING`.

## 5.4 Write-gate hỗ trợ lightweight path

Refactor `_vnext_active_task()` thành:

```python
def resolve_active_execution(...):
    return FullExecutionContract | LightweightExecutionContract | Deny
```

Full path giữ logic hiện tại.

Lightweight path kiểm:

* đúng một workspace `EXECUTING`;
* tồn tại `TASK.yaml`;
* tồn tại `LIGHTWEIGHT_EXECUTION.yaml`;
* contract status active;
* task hash khớp;
* scope hash khớp;
* execution lease còn hợp lệ;
* target thuộc scope;
* role phù hợp.

## 5.5 Không cho ghi arbitrary framework artifact

Lightweight worker chỉ được:

* sửa application scope;
* sửa declared test scope;
* ghi `RESULT.yaml`.

Không được:

* ghi `STATE.yaml`;
* sửa `TASK.yaml`;
* sửa execution contract;
* sửa knowledge store;
* sửa config;
* sửa skill.

## 5.6 Actual diff validation

Sau worker:

```python
actual = inspect_worktree_changes(base_revision)
```

Phân loại:

```text
allowed
outside_scope
untracked
deleted
renamed
binary
```

Nếu có file ngoài scope:

```text
block
→ mark contract invalid
→ transition BLOCKED
→ escalation target standard
```

Không tin `RESULT.yaml.touched_files` làm source of truth.

## Tests bắt buộc

### Unit

* Contract hash đúng.
* Empty scope bị reject.
* Task hash mismatch bị reject.
* Expired lease bị reject.
* Application file trong scope được allow.
* Application file ngoài scope bị deny.
* Framework file bị deny.
* `RESULT.yaml` được allow.

### Integration

Worker thật sửa:

```text
src/a.py
```

Write-gate phải allow.

Worker thử sửa:

```text
src/b.py
```

Write-gate phải deny.

### Public E2E

```text
task start small
→ fill TASK/EVIDENCE
→ task apply
→ worker sửa file thật
→ task verify
→ COMPLETED
```

Không được chỉ ghi `RESULT.yaml`.

## Exit criteria Phase 1

* Fast worker thực sự sửa application code qua write-gate.
* Không cần full plan artifacts.
* Scope escape bị block.
* State luôn `EXECUTING` trong lúc worker chạy.
* Contract được invalidate sau completion/block.

---

# 6. Phase 2 — Deterministic risk classification

## 6.1 Tách requested class và effective class

`CHANGE.yaml` nên có:

```yaml
requested_class: small
effective_class: standard
classification:
  source: runtime
  classified_at: ...
```

Không dùng một field `class` cho cả user intent và runtime truth.

## 6.2 Derive mechanical signals trước dispatch

Thêm:

```python
def derive_risk_signals(task: dict, repo_root: Path) -> dict:
    ...
```

Signals tối thiểu:

```yaml
estimated_files:
affected_modules:
public_contract_changed:
database_changed:
event_contract_changed:
transaction_changed:
concurrency_changed:
security_changed:
migration_required:
infrastructure_changed:
cross_service_architecture:
unknown_count:
```

## 6.3 Path-based classifiers

Ví dụ:

```yaml
risk_rules:
  public_contract:
    - "**/controller/**"
    - "**/api/**"
    - "**/*.proto"
    - "**/openapi/**"

  database:
    - "**/migration/**"
    - "**/repository/**"
    - "**/*.sql"

  event:
    - "**/kafka/**"
    - "**/event/**"
    - "**/consumer/**"
    - "**/producer/**"

  security:
    - "**/security/**"
    - "**/auth/**"
    - "**/permission/**"
```

Rules phải configurable nhưng có default.

## 6.4 Content-based escalation

Path alone không đủ.

Thêm scan nhẹ cho các pattern:

```text
@Transactional
@KafkaListener
acknowledgment
retry
timeout
permission
role
schema
ALTER TABLE
CREATE INDEX
public endpoint
protobuf message
```

Không cần LLM cho classifier baseline.

## 6.5 Module count

Dùng một trong:

* Gradle subproject;
* Maven module;
* top-level source root;
* configured module registry.

Không chỉ count folder đầu tiên một cách mù quáng.

## 6.6 Monotonic escalation

Rules:

* User có thể yêu cầu class cao hơn.
* Runtime có thể nâng class.
* Runtime không tự hạ class đã confirmed.
* Hạ class cần trusted human approval artifact ngoài agent scope.

## 6.7 Trivial restriction

Đề xuất mạnh:

```text
trivial = documentation-only hoặc metadata-only
```

Nếu trivial chạm `.java`, `.py`, `.ts`, `.go`, `.rs`, `.sql`, phải nâng tối thiểu `small`.

## Tests bắt buộc

* Một file docs → trivial.
* Một internal source file → small.
* Hai module → small hoặc standard theo config.
* Controller/proto → standard.
* DB migration → architectural hoặc standard theo policy.
* Security path → architectural.
* User chọn trivial nhưng scope có Java → auto-upgrade.
* User chọn standard nhưng signals low → vẫn standard.

## Exit criteria Phase 2

* Effective class không còn phụ thuộc hoàn toàn vào `--class`.
* Risk signals được derive trước worker.
* Trivial không thể sửa application code.
* Escalation reason có evidence cụ thể.

---

# 7. Phase 3 — Safe verification execution

## 7.1 Bỏ arbitrary executable model

Không để agent tự chọn:

```yaml
executable: python
args: [...]
```

Thay bằng `verification_profile`.

Ví dụ:

```yaml
verification:
  commands:
    - name: unit-tests
      profile: gradle-test
      parameters:
        tests:
          - StageMapperTest
```

## 7.2 Profile registry

Tạo:

```text
profiles/verification-profiles.yaml
```

Ví dụ:

```yaml
version: 1

profiles:
  gradle-test:
    executable: ./gradlew
    fixed_args:
      - test
    allowed_parameters:
      tests:
        flag: --tests
        type: list
        pattern: "^[A-Za-z0-9_.$*:-]+$"
    category: test

  gradle-build:
    executable: ./gradlew
    fixed_args:
      - build
      - --no-daemon
    category: build

  pytest-paths:
    executable: pytest
    allowed_parameters:
      paths:
        type: path-list
        must_be_inside_repo: true
    category: test
```

## 7.3 Command compiler

API:

```python
def compile_verification_command(
    proposal: dict,
    profile_registry: dict,
    repo_root: Path,
) -> CompiledCommand:
    ...
```

Phải:

* reject unknown profile;
* canonicalize executable;
* resolve executable từ trusted PATH;
* reject repo-local fake executable;
* validate arguments;
* reject command separators;
* reject path outside repo;
* return structured argv.

## 7.4 Python policy

Không cho generic:

```text
python -c
python script-from-workspace.py
```

Trừ khi profile trusted chỉ định script cố định thuộc Maika runtime.

Ví dụ có thể cho:

```yaml
profile: maika-ci
```

Runtime compile thành:

```text
python scripts/run_ci.py
```

nhưng `scripts/run_ci.py` phải hash-bound hoặc nằm trong trusted source.

## 7.5 Human approval

Human approval phải ở trusted channel.

Không đọc:

```yaml
human_confirmed: true
```

từ agent-authored artifact.

Tạo:

```text
<workspace>/approvals/<approval-id>.yaml
```

Artifact này phải được tạo bởi CLI command:

```bash
maika task approve-command --id X --command-id CMD-001
```

Schema:

```yaml
version: 1
approval_id:
change_id:
command_hash:
approved_by:
approved_at:
source: cli-user-action
```

Agent không có quyền ghi thư mục approvals.

## 7.6 Sandbox

Với command rủi ro:

* package install;
* migration;
* Docker;
* kubectl;
* Terraform;
* arbitrary build script;

phải:

```text
deny
hoặc
run trong sandbox/worktree disposable
hoặc
require trusted approval
```

## 7.7 Config wiring

`command_policy` phải được load từ resolved config và inject vào runtime.

Không dùng constant hard-code khi project config tồn tại.

## Tests bắt buộc

* `python -c` bị deny.
* `/tmp/python` bị deny.
* Unknown profile bị deny.
* Profile valid chạy `shell=False`.
* Path traversal bị deny.
* Human approval trong task artifact bị ignore.
* Trusted CLI approval được accept.
* Config override thay đổi allowed profile.
* Timeout/output cap lấy từ config.

## Exit criteria Phase 3

* Agent không thể chạy arbitrary Python.
* Không basename bypass.
* Human confirmation không self-asserted.
* Verification command luôn đến từ trusted profile.
* Command policy config thực sự điều khiển runtime.

---

# 8. Phase 4 — Exit codes và blocked semantics

## 8.1 Exit code contract

Định nghĩa:

```text
0 = success/completed phase
1 = runtime failure or blocked
2 = configuration or CLI usage error
3 = human input required
4 = budget exhausted
5 = stale artifact or contract
```

## 8.2 `vnext-run`

Mapping:

```python
if status == "done":
    return 0

if status == "human_required":
    transition(BLOCKED, ...)
    return 3

if status == "budget_exhausted":
    transition(BLOCKED, ...)
    return 4

if status == "stale_plan":
    transition(BLOCKED, ...)
    return 5

if status == "blocked":
    transition(BLOCKED, ...)
    return 1
```

Không return `0` cho blocked.

## 8.3 BLOCKED metadata

```yaml
blocked:
  reason:
  code:
  previous_state:
  resume_state:
  since:
  detail:
  recovery_actions:
```

## 8.4 Resume

`task resume` không chỉ print status.

Nó phải:

* đọc blocker;
* kiểm condition đã được giải quyết;
* transition về `resume_state`;
* không tự động bypass gate.

## Tests bắt buộc

* Worker result invalid → exit 1.
* Human approval thiếu → exit 3.
* Budget exhausted → exit 4.
* Stale contract → exit 5.
* Done → exit 0.
* BLOCKED chỉ resume về `resume_state`.

## Exit criteria Phase 4

* Shell automation đọc exit code chính xác.
* Mọi blocked outcome đều để lại state và remediation rõ.
* Test cũ hợp thức hóa exit 0 phải được sửa.

---

# 9. Phase 5 — Token budget thực sự

## 9.1 Canonical runtime config

Tạo:

```python
@dataclass(frozen=True)
class RuntimePolicy:
    token_budget: ...
    command_policy: ...
    worker_timeout_seconds: ...
    max_retries: ...
```

Load một lần từ:

```text
execution-mode.local.yaml
fallback execution-mode.yaml
```

Mọi module nhận policy qua dependency injection.

Không tự đọc config rải rác.

## 9.2 Prompt size measurement

Trước mỗi worker call:

```python
prompt_bytes = len(prompt.encode("utf-8"))
estimated_tokens = estimate_tokens(prompt)
```

Nếu platform trả actual usage thì lưu actual.

Nếu không:

```yaml
total_tokens: unavailable
estimated_tokens: 7412
estimation_method: chars_div_4
```

Không ghi số estimate vào `total_tokens`.

## 9.3 Evidence budget

Trước khi tạo capsule:

```text
selected evidence <= max_evidence_items
```

Nếu vượt:

1. rank evidence;
2. giữ highest relevance/authority/freshness;
3. ghi omitted count;
4. escalate hoặc block nếu evidence bắt buộc bị loại.

## 9.4 Context budget

Capsule builder phải tính:

```text
task brief
project knowledge
source anchors
memory
database slice
prior review
```

Nếu vượt:

* remove low-priority history;
* summarize;
* keep immutable IDs;
* preserve required evidence;
* warn;
* block nếu vẫn quá budget.

## 9.5 Worker-call budget

Budget phải lấy từ config, không từ constant.

Với full flow nên phân loại:

```yaml
worker_budget:
  implementation:
  fix:
  review:
  final_review:
```

Không để final review bị hết budget chỉ vì implementation dùng hết quota mà không có policy rõ.

## 9.6 Metrics

Ghi:

```yaml
runtime_metrics:
  task_class:
  actual_tokens:
  estimated_tokens:
  prompt_bytes:
  worker_calls:
  tool_calls:
  evidence_selected:
  evidence_omitted:
  evidence_reuse_ratio:
  retry_count:
```

## Tests bắt buộc

* Config override được runtime dùng.
* Evidence vượt budget bị trim deterministic.
* Required evidence không bị silently drop.
* Prompt vượt budget gây warning/block.
* Estimated token được ghi khi actual unavailable.
* Worker call budget theo project config.

## Exit criteria Phase 5

* Token budget không còn decorative.
* Task nhỏ có số liệu token/context thực tế hoặc estimate minh bạch.
* Không load quá nhiều evidence một cách vô thức.

---

# 10. Phase 6 — Canonical knowledge slice và evidence reuse

## 10.1 Xóa implementation song song

Giữ một API canonical:

```python
select_knowledge_slice(...)
```

Xóa hoặc chuyển:

```text
plan_compiler._active_project_knowledge
runtime_hardening.load_knowledge_slice
```

về cùng service.

## 10.2 Selection pipeline

```text
index match
→ status active
→ not superseded
→ applies_to match
→ affected_paths match
→ authority sufficient
→ digest valid
→ freshness valid
→ ranking
→ budget trim
```

## 10.3 Reuse metrics đúng nghĩa

```yaml
evidence_metrics:
  retrieved:
  eligible:
  reused:
  rejected_stale:
  rejected_authority:
  rejected_scope:
  revalidated:
  newly_created:
```

`reused` chỉ tăng khi digest/freshness pass.

## 10.4 Freshness policy

Theo class:

```text
trivial:
  active + scope match

small:
  digest-bound source required

standard:
  digest + authority standard

architectural:
  digest + high authority + explicit revalidation
```

## 10.5 Knowledge capsule provenance

Mỗi item trong capsule cần:

```yaml
id:
statement:
source:
source_digest:
source_commit:
authority:
freshness:
reuse_decision:
```

## Tests bắt buộc

* Stale digest không được reuse.
* Superseded entry không được load.
* Authority thấp không được dùng cho standard.
* Architectural task buộc revalidate.
* Metrics phản ánh chính xác reject reason.
* Budget trim deterministic.

## Exit criteria Phase 6

* Một canonical slice service.
* Không còn stale knowledge được tính reused.
* Evidence metrics có ý nghĩa thật.

---

# 11. Phase 7 — Cross-platform worker runtime

## 11.1 Prompt file thay command-line prompt

Không nhét prompt dài vào shell command.

Tạo temp file:

```text
generated/prompts/<dispatch-id>.txt
```

Worker config:

```yaml
worker:
  executable: codex
  args:
    - exec
    - --sandbox
    - workspace-write
    - --prompt-file
    - "{prompt_file}"
```

## 11.2 `shell=False`

Runner:

```python
subprocess.Popen(
    argv,
    shell=False,
    cwd=repo_root,
    start_new_session=True,
)
```

Windows cần process-group handling tương ứng.

## 11.3 Template validation

Allowed placeholders:

```text
{prompt_file}
{repo_root}
{workspace}
{task_id}
```

Reject unknown placeholders.

## 11.4 Review newline normalization

Trước parse:

```python
text = text.replace("\r\n", "\n").replace("\r", "\n")
```

## 11.5 Path normalization

Artifact paths phải:

* resolve trong workspace;
* không escape bằng `..`;
* hoạt động với Windows drive path;
* không so sánh raw POSIX string một cách mù quáng.

## Tests bắt buộc

* CRLF structured review pass.
* Prompt chứa quote/newline không làm vỡ worker command.
* Windows path có khoảng trắng pass.
* POSIX pass.
* Unknown placeholder bị reject.
* Prompt file cleanup sau worker.

## Exit criteria Phase 7

* Worker runner không dùng `shell=True`.
* Không dùng `shlex.quote` cho Windows.
* CRLF reviews được parse.
* CI Ubuntu và Windows đều pass.

---

# 12. Phase 8 — Concurrency hardening

## 12.1 Lock toàn workspace lifecycle

Dùng cùng một lock cho:

* apply;
* verify;
* archive;
* cancel;
* plan compile;
* review;
* transition.

Read-only status không cần lock exclusive.

## 12.2 Lock modes

```text
shared:
  status/read

exclusive:
  state mutation
  queue mutation
  verification
  archive
```

Nếu local implementation không hỗ trợ shared lock, status có thể optimistic read.

## 12.3 Queue generation

Thay `version: 1` static bằng:

```yaml
schema_version: 1
generation: 17
```

Mỗi write tăng generation.

## 12.4 Optimistic compare-and-swap

Writer đọc generation N.

Trước commit:

```text
current generation phải vẫn là N
```

Nếu không:

```text
WorkspaceConflict
```

## 12.5 Lease

```yaml
lease:
  owner:
  acquired_at:
  expires_at:
  heartbeat_at:
```

Không chỉ PID/host.

## 12.6 Cross-host policy

Nếu lock host khác:

* không tự delete;
* chỉ recover khi lease expired;
* ghi audit record;
* có explicit force unlock command.

## Tests bắt buộc

* Hai apply không dispatch cùng task.
* Verify và archive không chạy đồng thời.
* Generation mismatch bị reject.
* Expired lease recover.
* Non-expired remote lease không recover.
* Force unlock cần explicit command.

## Exit criteria Phase 8

* Không duplicate worker dispatch.
* Không concurrent verify/archive corruption.
* Lock recovery predictable.

---

# 13. Phase 9 — Learning safety

## 13.1 Không tạo candidate từ mọi feedback

Giữ threshold hiện tại nhưng bổ sung:

```text
verified evidence
reproducibility
cross-task recurrence
impact
evaluation readiness
```

## 13.2 Candidate không được promote nếu evaluation trống

Hiện candidate có thể chứa:

```yaml
evaluation_tasks: []
before_metrics: {}
after_metrics: {}
verdict: PENDING
```

Promotion phải yêu cầu:

```yaml
evaluation_tasks:
  - task-1
  - task-2

before_metrics:
after_metrics:

verdict: PROMOTE
```

## 13.3 Canary

Behavioral/contractual skill change:

```text
candidate
→ offline tests
→ dogfood task
→ canary
→ promote
```

## 13.4 Rollback

Promotion record cần:

```yaml
previous_version:
new_version:
promotion_commit:
rollback_commit:
```

Không chỉ ghi `"previous"`.

## Tests bắt buộc

* Candidate PENDING không promote.
* Empty evaluation không promote.
* Contractual change thiếu human approval bị reject.
* Canary regression rollback được.
* Poisoning text không đi vào skill.

## Exit criteria Phase 9

* Continuous improvement có benchmark và rollback.
* Agent không tự tiến hóa trực tiếp từ một observation.

---

# 14. File-level implementation map

## `.maika/tools/microloop-orchestrator/adaptive_runtime.py`

Thêm:

* mechanical risk derivation;
* requested/effective class;
* lightweight contract builder;
* budget policy injection;
* actual diff inspection;
* escalation from observed diff.

## `.maika/tools/microloop-orchestrator/runtime_hardening.py`

Refactor:

* verification profile compiler;
* trusted executable resolution;
* trusted approval validation;
* prompt-file worker runner helpers;
* CRLF normalization;
* canonical knowledge slice service;
* lock/lease primitives.

## `.maika/tools/microloop-orchestrator/vnext_state.py`

Thêm:

* execution contract metadata;
* BLOCKED reason code;
* resume validation;
* lock-aware transitions;
* completed/archived invariant hooks.

## `.maika/tools/microloop-orchestrator/orchestrator.py`

Refactor:

* load canonical runtime policy;
* lightweight preflight;
* transition EXECUTING trước worker;
* create/invalidate lightweight execution contract;
* correct exit codes;
* prompt-file runner;
* propagate blocked state.

## `.maika/tools/microloop-orchestrator/vnext_dispatch.py`

Refactor:

* config-driven budgets;
* queue generation CAS;
* worker-call categories;
* explicit budget outcome;
* no shell command runner dependency.

## `.maika/tools/microloop-orchestrator/plan_compiler.py`

Refactor:

* use canonical knowledge slice service;
* enforce evidence budget;
* correct reuse metrics;
* remove duplicate selection logic.

## `.maika/hooks/write-gate/write_gate.py`

Refactor:

* resolve full or lightweight execution contract;
* validate lightweight task hash/scope hash/lease;
* allow only declared application/test/result targets;
* no dependency on full plan artifacts for lightweight flow.

## `cli/commands/task.py`

Refactor:

* trusted approval command;
* exit-code mapping;
* lock verify/archive/cancel;
* effective class output;
* actual verification profiles.

## `.maika/profiles/execution-mode.yaml`

Replace raw command policy with:

```yaml
runtime_policy:
  worker:
  verification_profiles:
  token_budget:
  retry_policy:
  lock_policy:
```

## Tests

Thêm hoặc cập nhật:

```text
test_lightweight_write_gate_e2e.py
test_lightweight_execution_contract.py
test_effective_risk_classification.py
test_verification_profiles.py
test_trusted_command_approval.py
test_runtime_policy_wiring.py
test_actual_diff_escalation.py
test_exit_code_contract.py
test_cross_platform_worker.py
test_knowledge_slice_freshness.py
test_workspace_concurrency.py
```

---

# 15. Test matrix

## Unit

* risk classifier;
* command compiler;
* contract hashes;
* state transitions;
* knowledge freshness;
* token budget;
* lock behavior.

## Integration

* lightweight worker + write-gate;
* full worker + queue;
* verify + command profiles;
* archive + learning;
* blocked + resume.

## Public CLI E2E

### Small

```text
start
→ apply
→ actual code write
→ verify
→ completed
```

### Small escalation

```text
start small
→ worker touches out-of-scope API
→ blocked
→ effective class standard
→ full artifacts initialized
```

### Standard

```text
start
→ explore
→ validate-reasoning
→ reconcile
→ brainstorm
→ spec
→ plan
→ review
→ apply
→ verify
→ archive
```

### Command approval

```text
verify proposes protected profile
→ exit 3
→ approve-command
→ verify succeeds
```

## Cross-platform

* Ubuntu;
* Windows;
* Python 3.11;
* paths with spaces;
* CRLF;
* Unicode workspace path.

---

# 16. Acceptance criteria cuối

Implementation chỉ được coi là hoàn thành khi:

1. Small worker thực sự sửa application source qua write-gate.
2. Lightweight worker chạy khi state đã là `EXECUTING`.
3. Lightweight path không cần full plan artifacts.
4. File ngoài declared scope bị block.
5. Runtime so sánh actual Git diff, không chỉ tin `RESULT.yaml`.
6. Trivial bị giới hạn documentation-only.
7. Requested class và effective class được tách.
8. Risk signals được derive cơ học trước dispatch.
9. `python -c` và fake executable path bị deny.
10. Human confirmation không thể tự khai báo trong task artifact.
11. Verification command đến từ trusted profile.
12. `command_policy` và `token_budget` config thực sự điều khiển runtime.
13. `max_context_tokens` và `max_evidence_items` được enforce.
14. Evidence reuse phải qua digest, authority và supersession checks.
15. Blocked apply trả non-zero.
16. BLOCKED state có reason, code và resume state.
17. Worker runner dùng `shell=False`.
18. Prompt được truyền qua file hoặc argv structured.
19. CRLF review parse thành công.
20. Workspace lifecycle được lock.
21. Queue generation conflict bị detect.
22. Skill candidate không promote nếu evaluation chưa hoàn tất.
23. GitHub Actions Ubuntu xanh.
24. GitHub Actions Windows xanh.
25. PowerShell install E2E vẫn xanh.
26. `git diff --check` sạch.
27. `python -m compileall` sạch.
28. Final report ghi rõ:

    * files changed;
    * architecture decisions;
    * tests run;
    * CI result;
    * token metrics before/after;
    * known limitations;
    * follow-up.

---

# 17. Definition of done

```text
READY FOR DOGFOOD
```

khi:

* Phase 1–4 hoàn thành;
* CI xanh;
* fast path sửa code thật qua write-gate.

```text
READY FOR STABLE MERGE
```

khi:

* Phase 1–8 hoàn thành;
* token/config wiring hoàn chỉnh;
* cross-platform runner ổn định;
* knowledge freshness canonical;
* concurrency test pass.

```text
READY FOR CONTINUOUS IMPROVEMENT CLAIM
```

khi:

* Phase 9 hoàn thành;
* có evaluation/canary/rollback;
* chứng minh task tương tự dùng ít token hoặc ít retry hơn.
