# Maika `master-v2` Runtime Stabilization Plan

## Baseline

```text
Repository: VIethoangnguyenle/Maika
Branch: master-v2
Reviewed HEAD: 8b9448b4d5ed6bf8abefa402c933410a2071ff0c
```

---

# 1. Mục tiêu

Plan này xử lý các vấn đề còn lại sau đợt multi-framework và dead-artifact remediation:

1. CI phải xanh trên Ubuntu, Windows và PowerShell install E2E.
2. Fresh install phải tạo ra runtime có thể sử dụng được hoặc hướng dẫn verify rõ ràng.
3. `maika update` không được làm mất detection/verification state của platform.
4. Shared runtime policy phải được mọi consumer đọc đúng.
5. Multi-host phải được chứng minh bằng actual process dispatch, không chỉ profile metadata.
6. Capability verification không được overclaim.
7. Không tồn tại strategy được resolver trả về nhưng không có executor.
8. Session resolution phải hỗ trợ nhiều host/session thực tế.
9. Artifact audit phải phát hiện dead code trong cả `.maika/tools`.
10. Migration/uninstall phải có semantics atomic và rõ ràng.

Nguyên tắc:

> Không thêm feature mới trước khi runtime hiện tại trở nên deterministic, verifiable và CI-green.

---

# 2. Findings cần xử lý

## F1 — CI đỏ

Hiện tại:

```text
Ubuntu test suite: pass
Windows test suite: fail
PowerShell install E2E: fail
```

Một stale assertion vẫn tìm:

```text
write_gate.py
```

trong host hook, trong khi contract mới là:

```text
maika hook write-gate --runtime <runtime> --platform <platform>
```

Ngoài ra Windows test suite còn ít nhất một lỗi chưa được inventory đầy đủ.

---

## F2 — Fresh install tạo runtime profile chưa verified

Fresh profile mặc định có:

```yaml
binary:
  found: false
  version_supported: false

capabilities:
  fresh_session: advertised

verification:
  worker_smoke_test: not-run
```

Resolver fallback về `inline`, nhưng orchestrator chỉ chấp nhận `fresh_process`.

Kết quả:

```text
maika init thành công
→ task dispatch có thể bị từ chối ngay lập tức
```

---

## F3 — Update reset detection/verification state

`maika update` regenerate profile mới cho tất cả enabled platform.

Điều này làm mất:

- binary detection;
- supported-version result;
- verified capabilities;
- worker smoke result;
- hook smoke result;
- support tier;
- verification timestamps.

---

## F4 — `runtime_policy` nesting bị consumer bỏ qua

Shared config đã chuyển sang:

```yaml
runtime_policy:
  max_retries:
  worker_timeout_seconds:
  token_budget:
  command_policy:
```

Nhưng nhiều consumer vẫn đọc:

```python
config.get("token_budget")
config.get("command_policy")
```

thay vì đọc dưới `runtime_policy`.

Hệ quả: config trở thành decorative hoặc chỉ một phần runtime nhận được.

---

## F5 — Capability verification overclaim

Các claim hiện còn yếu:

- `--version` exit 0 được coi version supported;
- binary tồn tại được coi authentication detected;
- mọi advertised capability có thể thành detected;
- hook verify import evaluator trực tiếp thay vì gọi actual hook command;
- MCP mới chỉ detected từ config.

---

## F6 — Native subagent không có executor

Resolver có thể trả:

```text
native_subagent
```

nhưng orchestrator chỉ thực thi:

```text
fresh_process
```

Đây là shadow strategy.

---

## F7 — Multi-host test chưa chứng minh actual dispatch

Test hiện chủ yếu kiểm:

```text
profile.platform
profile.executable
```

chưa chứng minh process đúng host được spawn.

---

## F8 — Session model chỉ có một global session file

```text
.maika/runtime/current-session.yaml
```

Một host có thể block host khác trong 30 phút.

Hook dùng session ID cố định, không phản ánh session thật.

---

## F9 — Artifact audit chưa phủ `.maika/tools` thật sự

Blanket registry groups có thể khiến dead module dưới `.maika/tools` được coi active mà không có production consumer.

---

## F10 — Lifecycle edge cases còn ngoài transaction

- purge uninstall còn `shutil.rmtree()` ngoài transaction;
- migration conflict có thể mutate safe files rồi return blocked;
- failed command semantics chưa phân biệt no-op, partial-safe và full commit.

---

# 3. Target architecture

## 3.1 Canonical runtime policy loader

Tạo duy nhất:

```text
cli/runtime/policy.py
```

API:

```python
@dataclass(frozen=True)
class RuntimePolicy:
    max_retries: int
    worker_timeout_seconds: int
    token_budget: dict
    command_policy: dict

def load_runtime_policy(config: dict) -> RuntimePolicy:
    ...
```

Compatibility:

```text
config["runtime_policy"]
→ canonical

top-level legacy keys
→ compatibility fallback + warning
```

Mọi consumer phải gọi loader này.

---

## 3.2 Runtime profile ownership model

Mỗi field trong platform runtime profile phải có ownership rõ:

### Framework-owned

```yaml
version:
platform:
adapter:
worker:
  strategy:
  executable:
  args:
  dangerous_permissions:
  timeout_seconds:
```

### Runtime-observed

```yaml
detection:
capabilities:
verification:
```

### Derived

```yaml
support_tier:
profile_fingerprint:
```

Update chỉ được regenerate framework-owned fields.

Runtime-observed fields chỉ bị invalidate khi fingerprint thay đổi.

---

## 3.3 Verification state machine

```text
advertised
→ detected
→ verified
→ degraded
→ unavailable
```

Không được nhảy:

```text
advertised → verified
```

chỉ vì binary tồn tại.

---

## 3.4 Worker execution contract

Resolver chỉ được trả strategy có executor thật:

```text
fresh_process
inline
disabled
```

`native_subagent` chỉ được enable khi platform adapter implement:

```python
execute_native_subagent(...)
```

Nếu chưa có executor:

```text
capability có thể advertised
nhưng resolver không được chọn
```

---

## 3.5 Session registry

Thay:

```text
current-session.yaml
```

bằng:

```text
.maika/runtime/sessions/
├── claude-code/
│   └── <session-id>.yaml
├── codex/
│   └── <session-id>.yaml
└── antigravity/
    └── <session-id>.yaml
```

Có thêm:

```text
.maika/runtime/active-platform.yaml
```

chỉ dùng cho explicit user selection.

Resolution order:

```text
explicit --platform
→ hook platform + session-id
→ explicit active-platform
→ exactly one fresh session
→ project primary
→ block on ambiguity
```

---

# 4. Phase 0 — CI failure inventory

## Tasks

1. Tải full logs của:
   - Windows test job;
   - PowerShell install E2E.

2. Tạo:

```text
docs/refactor/master-v2/runtime-stabilization-failures.md
```

Schema:

```yaml
job:
test:
platform:
failure:
root_cause:
production_impact:
fix:
regression_test:
```

3. Sửa stale PowerShell assertion:

Thay:

```powershell
write_gate\.py
```

bằng kiểm:

```text
maika.write-gate.v1
maika hook write-gate
--platform claude-code
```

4. Đảm bảo workflow chạy trên:
   - PR;
   - `main`;
   - `master-v2` trong giai đoạn stabilization.

5. Không đổi test expectation chỉ để CI xanh.

## Exit criteria

- Có failure inventory đầy đủ.
- Ubuntu, Windows, install E2E đều được reproduce.
- Không còn unknown failure.

---

# 5. Phase 1 — Canonical runtime policy loader

## Tasks

1. Tạo `cli/runtime/policy.py`.
2. Move `RuntimePolicy` khỏi `adaptive_runtime.py` hoặc biến module đó thành consumer.
3. Implement:

```python
def runtime_policy_mapping(config):
    return config.get("runtime_policy", config)
```

4. Validate:
   - positive integer timeout/retry;
   - token budget có đủ class;
   - command policy đúng schema;
   - unknown keys fail hoặc warning theo compatibility policy.

5. Migrate consumers:

```text
adaptive_runtime.py
orchestrator.py
task verification runner
worker resolver
doctor
write-gate nếu có đọc policy
```

6. Xóa direct `config.get("command_policy")` ngoài canonical loader.

## Tests

- Nested config được đọc đúng.
- Legacy top-level config vẫn đọc trong compatibility window.
- Project override thay đổi behavior thật.
- Invalid nested config fail closed.
- Default config và loaded policy đồng nhất.

## Exit criteria

Không consumer nào tự parse runtime policy.

---

# 6. Phase 2 — Runtime profile merge/preserve

## Tasks

1. Tạo:

```python
def merge_platform_runtime_profile(
    existing: dict | None,
    generated: dict,
) -> dict:
    ...
```

2. Preserve runtime-observed fields khi profile fingerprint không đổi.

Fingerprint gồm:

```text
platform
worker strategy
worker executable
worker args
adapter entrypoint
native config path
profile schema version
```

3. Khi fingerprint đổi:
   - preserve detection path/version để diagnostics;
   - reset worker verification;
   - mark capabilities `degraded` hoặc `detected`;
   - require reverify.

4. `maika update`:
   - load existing profile;
   - generate framework fields;
   - merge;
   - write staged profile.

5. `platform enable`:
   - nếu profile cũ tồn tại và adapter re-enable;
   - merge thay vì overwrite.

6. Persist:

```yaml
profile_fingerprint:
verification_invalidated_reason:
```

## Tests

- Verified profile survives normal update.
- Worker args change invalidates worker verification.
- Schema bump invalidates safely.
- Re-enable preserves valid facts.
- Disabled profile không tự trở thành verified.

## Exit criteria

`maika update` không làm runtime đang hoạt động trở thành unusable.

---

# 7. Phase 3 — Install and verify lifecycle

## Quyết định UX

Fresh install phải chọn một trong hai mode:

### Mode A — Verify during install

```text
maika init --verify-platform
```

### Mode B — Safe unverified install

```text
maika init
→ scaffold success
→ platform state Tier 1
→ next step bắt buộc: maika platform verify <platform>
```

Default khuyến nghị:

```text
headless CI: verify=false
interactive install: hỏi verify
```

## Tasks

1. Sau `init`, chạy binary detection.
2. Persist detection result.
3. Không claim worker usable nếu chưa verify.
4. Next steps phải in:

```text
maika platform verify <platform>
```

5. `task apply/review`:
   - nếu worker chưa verified;
   - trả clear remediation;
   - không nói chung chung “inline fallback” nếu inline executor chưa có.

6. Thêm optional:

```bash
maika init --verify-platform
```

7. `platform enable` cũng theo contract tương tự.

## Tests

- Fresh install status Tier 1.
- Verify pass → Tier 2.
- Task trước verify → block với remediation.
- Task sau verify → dispatch.
- Missing binary → clear diagnostic.
- Verify timeout → degraded, không corrupt profile.

## Exit criteria

Không còn tình trạng init báo sẵn sàng nhưng first task chắc chắn fail mơ hồ.

---

# 8. Phase 4 — Worker strategy truthfulness

## Tasks

1. Inventory các strategy:

```text
fresh_process
inline
native_subagent
disabled
```

2. Quyết định cho release hiện tại:

```text
fresh_process: supported
inline: supported chỉ nếu có actual inline executor
native_subagent: advertised-only
disabled: supported
```

3. Nếu chưa có inline executor:
   - resolver không trả inline cho task execution;
   - trả `disabled` hoặc raise `WorkerResolutionError`;
   - remediation yêu cầu verify platform.

4. Nếu giữ inline:
   - implement `InlineWorkerExecutor`;
   - define input/output contract;
   - enforce same execution contract/write-gate;
   - test actual path.

5. Native subagent:
   - bỏ khỏi selection order;
   - chỉ enable khi adapter cung cấp executor callback.

6. Introduce executor interface:

```python
class WorkerExecutor(Protocol):
    def run(self, profile, prompt_file, context) -> WorkerResult:
        ...
```

Implement:

```text
FreshProcessExecutor
InlineExecutor          optional
NativeSubagentExecutor  future
```

## Tests

- Resolver không trả strategy không có executor.
- Executor registry và strategy registry đồng bộ.
- Unknown strategy fail closed.
- Doctor không claim strategy usable nếu executor thiếu.

## Exit criteria

Không còn shadow strategy.

---

# 9. Phase 5 — Actual multi-host dispatch E2E

## Test harness

Tạo fake executables:

```text
fake-claude
fake-codex
fake-agy
```

Mỗi executable:

- ghi argv vào log;
- đọc prompt file;
- emit structured success;
- không sửa application files.

## Scenarios

### Scenario 1

```text
init codex
enable claude-code
verify fake claude
run review/apply với --platform claude-code
```

Assert:

```text
fake-claude được spawn
fake-codex không được spawn
prompt file đúng
```

### Scenario 2

```text
init claude-code
enable codex
verify fake codex
run dưới codex
```

### Scenario 3

```text
same task state
switch host
state bytes không đổi
worker binary đổi đúng host
```

### Scenario 4

```text
primary = claude
explicit --platform codex
→ codex wins
```

### Scenario 5

```text
fresh session claude
fresh session codex
no explicit platform
→ ambiguity block
```

## Exit criteria

Multi-host được chứng minh bằng process invocation thật.

---

# 10. Phase 6 — Capability verification hardening

## Binary/version

1. Platform adapter khai báo version parser và supported range:

```python
version_command = ["--version"]
supported_version = ">=x.y"
```

2. Parse semver hoặc adapter-specific version.
3. Unknown format:
   - `detected`;
   - không `version_supported`.

## Authentication

Không đánh dấu authenticated từ binary existence.

States:

```text
not-probed
authenticated
unauthenticated
unknown
```

Adapter-specific probe:

```text
claude auth/status command
codex login/status command
agy status command
```

Nếu host không expose:
- `unknown`;
- không claim authenticated.

## Hook verification

Actual smoke test phải chạy:

```text
maika hook write-gate --runtime ... --platform ...
```

với stdin payload an toàn.

Assert:

- CLI resolve được;
- platform profile load được;
- evaluator load được;
- output contract đúng;
- exit code đúng.

## Worker verification

Smoke test:

- no-write prompt;
- bounded timeout;
- structured output;
- no worktree diff;
- process cleanup.

## MCP

States:

```text
configured
detected
verified
degraded
```

Không nâng verified nếu không gọi provider/tool thật.

## Support tier

```text
Tier 0: no adapter
Tier 1: entrypoint/config installed
Tier 2: hook + worker verified
Tier 3: MCP/provider verified
```

## Exit criteria

Support tier chỉ phản ánh bằng chứng thực.

---

# 11. Phase 7 — Session registry redesign

## Tasks

1. Hook nhận session ID từ payload/environment nếu platform cung cấp.
2. Nếu không có, generate ephemeral ID theo:
   - process ID;
   - parent process;
   - timestamp;
   - runtime.
3. Store per-session file.
4. Add cleanup:

```bash
maika runtime sessions --prune
```

5. Add:

```bash
maika runtime sessions
maika runtime current
maika runtime set-platform
maika runtime clear-platform
```

6. Ambiguity rules:
   - one fresh platform → select;
   - multiple fresh same platform → select platform;
   - multiple fresh different platform → require explicit;
   - explicit selection expires hoặc clear được.

7. Lock per session file, không global lock toàn registry.

## Tests

- Two Claude sessions coexist.
- Claude + Codex coexist.
- Explicit platform wins.
- Stale session ignored.
- Hook refreshes existing session.
- Malformed session ignored và doctor warning.
- Concurrent hooks không corrupt registry.

## Exit criteria

Host switching không bị block giả trong 30 phút.

---

# 12. Phase 8 — Artifact audit expansion

## Tasks

1. Registry không được dùng blanket group như bằng chứng consumer cuối cùng cho runtime Python.
2. Với `.maika/tools/**/*.py`, xác minh một trong:
   - imported by production module;
   - loaded by explicit file dispatch;
   - referenced by plugin manifest;
   - registered CLI/tool entry;
   - declared compatibility artifact.

3. Tạo file-dispatch registry:

```yaml
dynamic_consumers:
  - loader:
    pattern:
    reason:
```

4. Audit dynamic import paths:
   - `importlib.util.spec_from_file_location`;
   - string module path;
   - manifest references;
   - CLI route mapping.

5. Fail khi:
   - test-only consumer;
   - docs-only consumer cho runtime module;
   - duplicate policy owner;
   - scaffolded artifact không có workflow consumer.

6. Generate report:

```text
docs/refactor/master-v2/artifact-consumer-audit-v2.yaml
```

## Tests

- Dead module dưới `.maika/tools` → fail.
- File-dispatched module → pass.
- Manifest module → pass.
- Test-only module → fail.
- Compatibility module có expiry → pass.
- Expired compatibility → fail.

## Exit criteria

Dead artifact gate có giá trị mechanical, không chỉ registry declaration.

---

# 13. Phase 9 — Lifecycle semantics hardening

## Uninstall purge

Không được:

```python
Transaction.apply(...)
shutil.rmtree(.maika)
```

ngoài transaction.

Thay bằng:

```text
explicit delete_directory actions
```

bao phủ toàn bộ purge scope.

Unknown files:

- inventory trước;
- require `--purge-project-data`;
- print exact paths;
- include in transaction journal.

## Migration conflict

Chọn contract:

### Recommended

```text
preflight all conflicts
→ if conflict exists: write report only
→ no project-data mutation
```

Conflict report có thể được ghi transactionally như diagnostic artifact.

Sau decision:

```bash
maika migrate --resolve <decision-file>
```

mới apply.

## Command result semantics

Return object:

```yaml
status: no-op | committed | blocked | partial-safe
mutation: true|false
transaction_id:
```

CLI exit code phải align với mutation semantics.

## Tests

- Conflict migration không copy data.
- Purge failure rollback toàn `.maika`.
- Unknown file được inventory.
- Interrupt repair restore đúng.
- Command báo blocked và mutation=false.

## Exit criteria

Không command nào báo blocked nhưng âm thầm mutate project data.

---

# 14. Phase 10 — CI and release gate

## Required CI jobs

```text
tests-ubuntu
tests-windows
install-linux-e2e
install-windows-e2e
wheel-isolation-e2e
multihost-dispatch-e2e
artifact-audit
transaction-fault-injection
```

## Windows assertions

Kiểm:

```text
maika.write-gate.v1
maika hook write-gate
--platform
canonical runtime profile
no Unix tokens
```

Không kiểm implementation cũ.

## Release gate

PR chỉ merge khi:

- tất cả required jobs pass;
- no Critical/High doctor finding;
- `maika doctor artifacts` pass;
- `git diff --check` pass;
- actual dispatch E2E pass;
- update-preserves-verification test pass.

---

# 15. File-level implementation map

## New

```text
cli/runtime/policy.py
cli/runtime/executor.py
cli/runtime/session_registry.py
cli/runtime/profile_merge.py
cli/tests/test_runtime_policy.py
cli/tests/test_profile_merge.py
cli/tests/test_multihost_dispatch_e2e.py
cli/tests/test_session_registry.py
cli/tests/test_capability_verification.py
docs/refactor/master-v2/runtime-stabilization-failures.md
docs/refactor/master-v2/artifact-consumer-audit-v2.yaml
```

## Modify

```text
.maika/profiles/execution-mode.yaml
.maika/tools/microloop-orchestrator/adaptive_runtime.py
.maika/tools/microloop-orchestrator/orchestrator.py
cli/runtime/worker_resolver.py
cli/runtime/platform_profile.py
cli/runtime/session.py
cli/platforms/probe.py
cli/platforms/base.py
cli/commands/init.py
cli/commands/update.py
cli/commands/platform.py
cli/commands/task.py
cli/commands/runtime.py
cli/commands/doctor.py
cli/commands/lifecycle.py
cli/install/transaction.py
cli/artifact_audit.py
scripts/run_ci.py
.github/workflows/ci.yml
```

## Remove or deprecate

```text
native_subagent selection until executor exists
legacy direct runtime-policy parsing
single global current-session semantics
post-transaction purge rmtree
blanket runtime consumer assumptions
```

---

# 16. PR slicing

## PR 1 — CI inventory and stale assertions

- fix Windows E2E assertion;
- document all failures;
- no architecture change.

## PR 2 — Runtime policy loader

- canonical config parsing;
- migrate consumers;
- compatibility tests.

## PR 3 — Profile merge/preserve

- ownership model;
- fingerprint;
- update preservation.

## PR 4 — Install/verify lifecycle

- detect during init;
- clear verify UX;
- block with remediation.

## PR 5 — Worker executor truthfulness

- executor interface;
- remove unsupported strategies;
- no silent inline fallback.

## PR 6 — Actual multi-host dispatch E2E

- fake executables;
- process-level assertions.

## PR 7 — Capability verification

- semver;
- auth;
- actual hook smoke;
- worker smoke;
- support tier.

## PR 8 — Session registry

- per-session files;
- ambiguity handling;
- cleanup CLI.

## PR 9 — Artifact audit v2

- `.maika/tools` consumer detection;
- dynamic dispatch registry.

## PR 10 — Lifecycle edge cases

- transactional purge;
- no-mutation conflict migration;
- result semantics.

## PR 11 — Final CI/release gate

- full matrix;
- branch protection-ready checks;
- cleanup compatibility code.

---

# 17. Acceptance criteria

Plan hoàn tất khi:

1. Ubuntu CI pass.
2. Windows CI pass.
3. PowerShell install E2E pass.
4. Linux install E2E pass.
5. Wheel isolation E2E pass.
6. Runtime policy nested config được đọc đúng.
7. Không consumer nào parse runtime config riêng.
8. Fresh install persist binary detection.
9. Fresh install không claim verified khi chưa verify.
10. First task trước verify có remediation rõ.
11. Verify pass cho phép dispatch.
12. Update giữ nguyên valid verification.
13. Worker config change invalidate verification.
14. Resolver không trả strategy thiếu executor.
15. Native subagent không được chọn khi chưa implement.
16. Dangerous permission mặc định false.
17. Actual Claude fake worker được spawn dưới Claude.
18. Actual Codex fake worker được spawn dưới Codex.
19. Primary không override explicit host.
20. Multi-host handoff giữ nguyên task state.
21. Version support dùng parser/range thật.
22. Authentication không suy ra từ binary existence.
23. Hook smoke gọi actual CLI.
24. Worker smoke không tạo worktree diff.
25. Support tier phản ánh verified evidence.
26. Multiple sessions cùng host coexist.
27. Multiple platforms tạo ambiguity rõ.
28. Stale sessions được prune.
29. Dead `.maika/tools` module bị CI phát hiện.
30. Test-only production module bị CI phát hiện.
31. Uninstall purge nằm hoàn toàn trong transaction.
32. Migration conflict không mutate project data.
33. Transaction repair pass fault injection.
34. Doctor setup không còn Critical/High.
35. Doctor artifacts không còn Critical/High.
36. `python scripts/run_ci.py` pass trên Ubuntu và Windows.
37. `git diff --check` pass.
38. PR #48 có required checks xanh.
39. Không còn compatibility code không có expiry.
40. Runtime có thể chuyển host mà không đổi shared core/state.

---

# 18. Definition of Done

Runtime chỉ được coi stable khi:

```text
init
→ detect
→ verify
→ dispatch đúng host
→ update không mất verification
→ switch host không mất state
→ CI chứng minh behavior trên Windows/Linux
```

Multi-framework chỉ được coi hoàn thành khi:

```text
profile metadata đúng
+
process thực tế đúng
+
capability claim có bằng chứng
+
lifecycle rollback được
```

Câu chốt:

> **Đợt fix này không thêm thêm một lớp abstraction mới; nó biến các abstraction đã có thành runtime behavior thật, có bằng chứng và không bị reset bởi lifecycle command.**
