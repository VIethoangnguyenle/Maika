# Maika Multi-Framework Upgrade Plan

## 1. Mục tiêu

Nâng cấp cơ chế multi-framework của Maika từ mô hình:

```text
Maika source
→ chọn một platform khi init
→ render toàn bộ runtime vào root của platform đó
→ project chỉ có một active platform
```

thành:

```text
Canonical Maika Core trong project
→ nhiều Host Adapter độc lập
→ Antigravity / Claude Code / Codex cùng dùng chung knowledge, state và workflow
→ setup, update, repair, migration và uninstall đều an toàn
```

Nguyên tắc kiến trúc trung tâm:

> **Maika core thuộc về project; host agent chỉ là adapter dùng Maika.**

Maika không phải một AI model độc lập. Nó chỉ hoạt động khi host agent:

- đọc entrypoint;
- load rules và skills;
- gọi hooks;
- dispatch worker;
- expose tools và MCP;
- thực thi workflow.

Vì vậy, installation, host integration và runtime verification là một phần của sản phẩm cốt lõi.

---

## 2. Vấn đề của cơ chế hiện tại

### 2.1 Multi-target lúc cài đặt, single-platform lúc runtime

Hiện tại mỗi platform quyết định:

- entrypoint;
- framework root;
- tool mapping;
- capability flags;
- MCP naming convention;
- hook config;
- worker command.

Ví dụ:

```text
Antigravity → AGENTS.md + .agents/
Codex       → AGENTS.md + .agents/
Claude Code → CLAUDE.md + .claude/
Generic     → AGENTS.md + .maika/
```

Điều này làm platform selection trở thành lựa chọn độc quyền.

Project muốn đổi host phải chạy reconfigure, tạo root mới và để root cũ tồn tại hoặc bị cleanup một phần.

---

### 2.2 Project knowledge bị gắn với host root

Knowledge hiện nằm dưới:

```text
.agents/knowledge/
.claude/knowledge/
.maika/knowledge/
```

Trong khi các artifact như:

- project knowledge;
- conventions;
- Author DNA;
- task state;
- archive;
- skill evolution;
- verification history;

là tài sản của project, không thuộc riêng Claude Code, Codex hay Antigravity.

Hệ quả:

- chuyển host có nguy cơ mất continuity;
- knowledge có thể bị duplicate;
- hai root có thể drift;
- khó dùng nhiều host trên cùng project.

---

### 2.3 CLI package chưa self-contained

CLI hiện phụ thuộc vào source checkout để lấy:

```text
.maika/rules
.maika/skills
.maika/workflows
.maika/procedures
.maika/tools
.maika/hooks
.maika/knowledge/templates
```

Do đó user thường phải:

```text
clone repository Maika
→ giữ clone
→ editable install
→ dùng clone làm source scaffold
```

Mô hình này chưa phù hợp với:

```text
pipx install maika-cli
uvx maika-cli init
pip install maika-cli
```

---

### 2.4 Config host có thể bị overwrite

Các file host có thể đã tồn tại:

```text
AGENTS.md
CLAUDE.md
.claude/settings.json
.codex/hooks.json
.agents/hooks.json
```

Nếu installer ghi đè toàn bộ file, nó có thể phá:

- instruction hiện hữu;
- hooks khác;
- permission settings;
- MCP settings;
- team-specific config.

Installer phải merge nội dung được quản lý bởi Maika, không sở hữu toàn bộ config của host.

---

### 2.5 Capability mới chỉ là static declaration

Platform adapter đang khai báo:

```text
subagent: true
fresh_session: true
task_dispatch: true
review_dispatch: true
model_selection: true
write_gate_hook: true
```

Nhưng setup chưa xác nhận:

- binary có trong PATH không;
- version có phù hợp không;
- user đã login không;
- host có hỗ trợ feature hiện tại không;
- hook có thật sự được gọi không;
- worker command có spawn được không;
- MCP tool có xuất hiện không.

Cần phân biệt:

```text
advertised capability
detected capability
verified capability
```

---

### 2.6 Worker launcher bị hard-code

Execution profile đang giả định:

```text
agy ...
claude -p ...
codex exec ...
```

Nhưng user có thể:

- chỉ dùng IDE, không có CLI;
- có CLI với version khác;
- không muốn dangerous permission flags;
- muốn native subagent thay fresh process;
- muốn inline fallback;
- cần command riêng theo environment.

Worker strategy phải được negotiate trong setup.

---

### 2.7 Hook phụ thuộc Python hệ thống

Một số hook gọi trực tiếp:

```text
/usr/bin/python3 <framework-root>/hooks/write-gate/write_gate.py
```

Trong khi dependencies có thể chỉ được cài trong Maika virtualenv.

Hook nên gọi một stable CLI entrypoint:

```text
maika hook write-gate
```

để không phụ thuộc Python interpreter bên ngoài.

---

### 2.8 Diagnostics chưa bao phủ full setup

Hiện có diagnostics cho MCP nhưng chưa có full doctor cho:

- host binary;
- entrypoint;
- managed blocks;
- hook invocation;
- worker spawn;
- root conflicts;
- version mismatch;
- package assets;
- runtime permissions.

---

## 3. Target architecture

### 3.1 Canonical project layout

```text
project/
├── .maika/
│   ├── config/
│   │   ├── project.yaml
│   │   ├── platforms.yaml
│   │   ├── capabilities.yaml
│   │   └── install-manifest.yaml
│   │
│   ├── knowledge/
│   ├── rules/
│   ├── workflows/
│   ├── skills/
│   ├── procedures/
│   ├── tools/
│   ├── hooks/
│   ├── changes/
│   ├── archive/
│   ├── loops/
│   └── runtime/
│
├── AGENTS.md
├── CLAUDE.md
│
├── .agents/
│   └── maika/
│       └── adapter.yaml
│
├── .claude/
│   ├── settings.json
│   └── maika/
│       └── adapter.yaml
│
└── .codex/
    ├── hooks.json
    └── maika/
        └── adapter.yaml
```

### 3.2 Ownership model

#### Project-owned

```text
.maika/knowledge/
.maika/changes/
.maika/archive/
.maika/loops/
.maika/config/project.local.yaml
```

Update không được overwrite.

#### Framework-owned

```text
.maika/rules/
.maika/workflows/
.maika/skills/
.maika/procedures/
.maika/tools/
.maika/hooks/
```

Update được phép replace theo manifest và version.

#### Shared host-owned

```text
AGENTS.md
CLAUDE.md
.claude/settings.json
.codex/hooks.json
.agents/hooks.json
```

Maika chỉ quản lý block hoặc JSON entries có namespace riêng.

---

## 4. Canonical configuration

### 4.1 `.maika/config/project.yaml`

```yaml
version: 1

framework:
  version: 4.0.0
  core_root: .maika

project:
  language: java
  repository_root: .

platforms:
  enabled:
    - antigravity
    - claude-code
    - codex

  primary: antigravity

providers:
  selected:
    - codebase-memory
    - understand-anything
    - agent-memory

installation:
  mode: managed
  installed_at:
  updated_at:
```

### 4.2 `.maika/config/platforms.yaml`

```yaml
version: 1

platforms:
  antigravity:
    enabled: true
    entrypoint: AGENTS.md
    adapter_root: .agents/maika
    worker_strategy: auto
    hook_strategy: native

  claude-code:
    enabled: true
    entrypoint: CLAUDE.md
    adapter_root: .claude/maika
    worker_strategy: native-subagent
    hook_strategy: native

  codex:
    enabled: true
    entrypoint: AGENTS.md
    adapter_root: .codex/maika
    worker_strategy: fresh-session
    hook_strategy: native
```

### 4.3 Resolved runtime state

```yaml
version: 1

platform: claude-code
detected:
  binary: /home/user/.local/bin/claude
  version: 1.x
  authenticated: true

capabilities:
  entrypoint:
    advertised: true
    detected: true
    verified: true

  hooks:
    advertised: true
    detected: true
    verified: true

  native_subagent:
    advertised: true
    detected: true
    verified: false

worker:
  selected_strategy: fresh-session
  executable:
  args: []

last_verified_at:
```

Resolved runtime data không được dùng thay canonical user configuration.

---

## 5. Platform Adapter v2

### 5.1 Interface mới

```python
class PlatformAdapter(ABC):

    def detect(self, environment) -> PlatformDetection:
        ...

    def inspect_project(self, project) -> PlatformProjectState:
        ...

    def plan_install(self, project, options) -> InstallActions:
        ...

    def apply_install(self, transaction, actions) -> None:
        ...

    def verify(self, project) -> PlatformVerification:
        ...

    def repair(self, project, findings) -> RepairPlan:
        ...

    def uninstall(self, transaction) -> None:
        ...

    def build_worker_profile(self, detection, preferences) -> WorkerProfile:
        ...

    def build_hook_profile(self, detection) -> HookProfile:
        ...
```

### 5.2 Detection contract

```yaml
platform: codex
detected: true

binary:
  found: true
  path:
  version:
  version_supported: true

authentication:
  state: authenticated | unauthenticated | unknown

features:
  entrypoint: supported
  hooks: supported
  fresh_session: supported
  native_subagent: unsupported
  mcp: unknown

problems: []
recommendations: []
```

### 5.3 Capability states

```text
unsupported
advertised
detected
verified
degraded
```

Runtime chỉ được dùng capability yêu cầu độ tin cậy cao khi state đạt `verified`.

---

## 6. Packaging và distribution

### Phase goal

User phải cài được Maika mà không cần clone source repo.

### 6.1 Bundle runtime assets

Đóng gói:

```text
maika_assets/
├── rules/
├── workflows/
├── skills/
├── procedures/
├── profiles/
├── tools/
├── hooks/
├── knowledge/
└── templates/
```

Dùng:

```python
importlib.resources.files("maika_assets")
```

Không resolve assets bằng đường dẫn tương đối tới source checkout.

### 6.2 Distribution paths

Hỗ trợ:

```bash
pipx install maika-cli
uv tool install maika-cli
uvx maika-cli init
pip install maika-cli
```

### 6.3 Version pinning

Project config ghi:

```yaml
framework:
  installed_version:
  required_cli_version:
```

CLI phải warn nếu:

```text
CLI version < project required version
CLI version quá mới so với schema project
```

### 6.4 Offline bundle

Optional follow-up:

```bash
maika package create
maika package install ./maika-bundle.zip
```

Dùng cho môi trường enterprise không có internet.

### Tests

- build wheel;
- install wheel vào clean venv;
- xóa source checkout;
- chạy `maika init`;
- verify tất cả assets có trong project;
- chạy update từ wheel version khác.

---

## 7. Installation planner

### 7.1 Preflight

`maika init` phải kiểm:

```text
Git project root
write permission
existing Maika installation
existing host configs
available platform binaries
Python/runtime requirement
existing MCP config
mixed-OS indicators
uncommitted changes
```

### 7.2 Install plan

Trước khi write:

```yaml
actions:
  create:
    - .maika/...

  merge:
    - CLAUDE.md
    - .claude/settings.json

  preserve:
    - existing user instructions
    - existing hooks

  backup:
    - CLAUDE.md
    - .claude/settings.json

  conflicts: []
```

CLI interactive phải hiển thị plan.

Non-interactive:

```bash
maika init --yes --config maika-install.yaml
```

### 7.3 Dry-run

```bash
maika init --dry-run
maika update --dry-run
maika repair --dry-run
maika uninstall --dry-run
```

Có output:

```text
human-readable
json
yaml
```

### 7.4 Transaction journal

```yaml
transaction_id:
operation: init
state: planned | applying | committed | rolled_back

backups: []
writes: []
merges: []
deletes: []
errors: []
```

Nếu bất kỳ action fail:

```text
rollback toàn bộ transaction
```

---

## 8. Safe host config integration

### 8.1 Managed block cho Markdown entrypoint

Ví dụ `CLAUDE.md`:

```markdown
Existing project instructions...

<!-- MAIKA:BEGIN entrypoint v1 -->
## Maika Runtime

Read `.maika/meta-prompt.md`.
Execute `.maika/procedures/bootstrap.md` before material work.
<!-- MAIKA:END entrypoint v1 -->

More user instructions...
```

Rules:

- chỉ update block Maika;
- không overwrite ngoài block;
- duplicate block là error;
- malformed marker cần repair;
- uninstall chỉ xóa managed block.

### 8.2 Structural JSON merge

Không replace toàn bộ:

```text
.claude/settings.json
.codex/hooks.json
.agents/hooks.json
```

Thay vào đó:

```text
parse JSON
→ locate namespaced Maika entry
→ insert/update only that entry
→ preserve unrelated keys
→ write atomically
```

Maika hook entry cần stable ID:

```json
{
  "id": "maika.write-gate.v1",
  "type": "command",
  "command": "maika hook write-gate --platform claude-code"
}
```

### 8.3 Conflict policy

```text
No existing Maika entry
→ add

Same ID, same schema
→ update

Same ID, unknown schema
→ block + repair advice

Duplicate entries
→ block + propose deduplication
```

### 8.4 Backup policy

Trước merge:

```text
.maika/runtime/backups/<transaction-id>/
```

Không lưu secrets vào report.

---

## 9. Hook runtime redesign

### 9.1 Stable CLI hook

Tạo:

```bash
maika hook write-gate
maika hook pre-command
maika hook post-task
```

Host config không gọi trực tiếp Python file.

### 9.2 Hook context

Host truyền:

```yaml
platform:
project_root:
tool_name:
target_path:
command:
session_id:
```

### 9.3 Runtime discovery

Hook CLI tự tìm:

```text
nearest project root
.maika/config/project.yaml
active change
write-gate policy
```

### 9.4 Cross-OS

Hook command không chứa:

```text
/usr/bin/python3
py -3
hard-coded repo path
shell-specific git command substitution
```

Chỉ chứa:

```text
maika hook write-gate ...
```

### Tests

- Linux;
- Windows;
- path có space;
- Unicode path;
- hook chạy ngoài source repo;
- hook chạy khi current working directory là subdirectory;
- Maika CLI không trong PATH → diagnostic rõ.

---

## 10. Worker strategy negotiation

### 10.1 Supported strategies

```text
native-subagent
fresh-session
inline-reload
disabled
```

### 10.2 Selection logic

```text
User explicit choice
> verified native capability
> verified fresh-session CLI
> inline fallback
```

### 10.3 Worker profile

```yaml
platform: claude-code
strategy: fresh-session

launcher:
  executable: claude
  args:
    - -p
    - --prompt-file
    - "{prompt_file}"

permissions:
  mode: normal
  allow_dangerous_skip: false

timeout_seconds: 900
```

### 10.4 No dangerous default

Không mặc định:

```text
--dangerously-skip-permissions
```

User phải opt in:

```bash
maika configure worker --allow-dangerous-permissions
```

### 10.5 Verification

Setup chạy smoke test:

```text
spawn worker
→ read a safe file
→ return structured response
→ no write
```

Nếu fail:

```text
capability = degraded
fallback strategy được chọn
```

---

## 11. MCP và provider setup

### 11.1 Provider Adapter

Mỗi provider khai báo:

```yaml
id:
display_name:
capability_ids:
platform_configs:
detection:
install_hint:
health_probe:
project_setup:
```

### 11.2 Setup modes

```text
already-configured
managed-config
manual-instructions
unavailable
```

### 11.3 Doctor behavior

```bash
maika doctor providers
maika doctor providers --fix
```

Phải báo:

- selected;
- configured;
- process/binary available;
- tool names visible;
- health state;
- graph/index state;
- safe fallback.

### 11.4 Secret handling

Không copy hoặc print:

- tokens;
- passwords;
- connection strings;
- API keys.

Reports chỉ chứa redacted config.

---

## 12. Multi-host coexistence

### 12.1 Enable nhiều host

```bash
maika platform enable antigravity
maika platform enable claude-code
maika platform enable codex
```

Không cần reconfigure toàn bộ project.

### 12.2 Shared state

Tất cả platform đọc chung:

```text
.maika/knowledge
.maika/changes
.maika/archive
.maika/loops
.maika/config
```

### 12.3 Host-specific state

Chỉ lưu trong adapter root:

```text
detected binary
verified capabilities
hook integration
worker strategy
host-specific MCP mapping
last verification
```

### 12.4 Concurrent host usage

Maika state và lock phải không phụ thuộc host.

Lock metadata:

```yaml
owner:
  platform:
  session_id:
  pid:
  hostname:
```

Hai host không được apply cùng task đồng thời.

### 12.5 Shared entrypoint

`AGENTS.md` có thể được Antigravity và Codex cùng đọc.

Managed block phải neutral:

```text
Read canonical Maika core in .maika/
Use the current host adapter under .maika/runtime/platforms/<platform>/
```

Không ghi instruction chỉ phù hợp một host vào shared block.

---

## 13. Migration từ layout hiện tại

### 13.1 Detect legacy roots

```text
.agents/resolved-config.yaml
.claude/resolved-config.yaml
.maika/resolved-config.yaml
```

### 13.2 Inventory

Phân loại:

```text
framework-owned
project-owned
host-owned
unknown
conflicting
```

### 13.3 Canonical knowledge selection

Nếu chỉ có một root:

```text
migrate project-owned data sang .maika/
```

Nếu có nhiều root:

```text
compare hashes
compare timestamps
compare IDs
detect conflicts
```

Không tự chọn file mới nhất cho knowledge conflict.

### 13.4 Migration plan

```yaml
source_roots:
  - .agents
  - .claude

canonical_target: .maika

moves: []
merges: []
conflicts: []
preserved_legacy: []
```

### 13.5 Compatibility mode

Trong một release:

```text
read canonical .maika first
fallback legacy roots read-only
warn user
```

Không tiếp tục write vào legacy roots.

### 13.6 Cleanup

Chỉ xóa legacy framework files sau:

- migration verified;
- backup created;
- user confirms;
- host adapters installed.

---

## 14. CLI experience

### 14.1 Commands mới

```text
maika init
maika update
maika status
maika doctor setup
maika doctor platform
maika doctor providers

maika platform list
maika platform detect
maika platform enable
maika platform disable
maika platform verify

maika configure worker
maika configure providers

maika migrate
maika repair
maika uninstall

maika hook write-gate
```

### 14.2 `maika status`

Output:

```text
Project core
Framework version
Schema version
Enabled platforms
Verified platforms
Worker strategy per platform
Hook state
Provider health
Knowledge root
Active task
Legacy root warnings
Pending repair
```

### 14.3 `maika doctor setup`

Checks:

```text
package assets
canonical config
entrypoint managed block
JSON hook merge
host binary
host version
authentication
worker smoke test
hook smoke test
provider setup
root conflicts
file ownership
mixed-OS compatibility
```

### 14.4 `maika repair`

Chỉ sửa finding được chọn.

Ví dụ:

```bash
maika repair --finding missing-claude-hook
maika repair --all-safe
```

Không tự sửa destructive conflict.

### 14.5 `maika uninstall`

Chỉ xóa:

- framework-owned core;
- Maika managed blocks;
- namespaced hook entries;
- adapter state.

Mặc định giữ:

```text
knowledge
archive
task history
backups
```

Có option:

```bash
maika uninstall --purge-project-data
```

yêu cầu xác nhận rõ.

---

## 15. File-level implementation map

### `pyproject.toml`

- bundle runtime assets;
- expose stable console entrypoint;
- add package validation tests;
- prepare pipx/uvx support.

### `cli/assets.py`

New canonical asset loader:

```python
load_asset_manifest()
asset_path(...)
materialize_assets(...)
```

### `cli/platforms/base.py`

Replace static-only platform interface with:

```text
detect
inspect
plan_install
verify
repair
uninstall
worker profile
hook profile
```

### `cli/platforms/antigravity.py`

Implement:

- IDE/CLI detection;
- AGENTS integration;
- native hook integration;
- agy worker detection;
- verified capability state.

### `cli/platforms/claude_code.py`

Implement:

- Claude binary/version/auth detection;
- CLAUDE managed block;
- `.claude/settings.json` merge;
- worker strategy selection.

### `cli/platforms/codex.py`

Implement:

- Codex binary/version detection;
- AGENTS managed block;
- `.codex/hooks.json` merge;
- explicit limitations for unverified internal tool mapping.

### `cli/install/`

New package:

```text
planner.py
transaction.py
backup.py
ownership.py
markdown_merge.py
json_merge.py
migration.py
uninstall.py
```

### `cli/commands/init.py`

Refactor to:

```text
detect
→ build plan
→ show plan
→ transaction apply
→ verify
```

### `cli/commands/update.py`

Update canonical core once.

Do not re-render project knowledge.

Update each enabled adapter independently.

### `cli/commands/status.py`

Use health model instead of inventory-only output.

### `cli/commands/doctor.py`

Add full setup diagnostics.

### `cli/commands/platform.py`

Enable, disable, detect and verify platform adapters.

### `cli/commands/repair.py`

Apply selected repair actions transactionally.

### `cli/commands/migrate.py`

Migrate legacy root layouts.

### `cli/commands/hook.py`

Stable hook entrypoints.

### `cli/config/`

Add schema loaders and migrations for:

```text
project.yaml
platforms.yaml
install-manifest.yaml
resolved platform state
```

---

## 16. Implementation phases

## Phase 0 — Architecture contract

### Tasks

1. Viết ADR:
   ```text
   docs/architecture/project-core-and-host-adapters.md
   ```
2. Chốt canonical core là `.maika/`.
3. Chốt ownership model.
4. Chốt enabled multi-platform model.
5. Chốt adapter interface v2.
6. Chốt migration compatibility window.
7. Chốt no-overwrite policy.

### Exit criteria

- Không còn ambiguity về core root.
- Knowledge không phụ thuộc platform.
- Host config được coi là shared ownership.

---

## Phase 1 — Self-contained package

### Tasks

1. Bundle runtime assets.
2. Refactor asset resolution.
3. Build wheel.
4. Test init khi source repo không tồn tại.
5. Publish dev package.
6. Add version compatibility check.

### Exit criteria

```bash
uvx maika-cli init
```

hoạt động trong clean project.

---

## Phase 2 — Canonical core scaffold

### Tasks

1. Luôn scaffold shared core vào `.maika/`.
2. Tách host adapter output khỏi core.
3. Generate canonical config.
4. Update task/runtime code dùng `.maika`.
5. Thêm legacy read fallback.
6. Không write vào legacy root.

### Exit criteria

- Claude, Codex và Antigravity cùng nhìn một knowledge root.
- Task state không phụ thuộc platform.

---

## Phase 3 — Transactional installer

### Tasks

1. Preflight.
2. Install planner.
3. Dry-run.
4. Backup.
5. Journal.
6. Atomic writes.
7. Rollback.
8. JSON/YAML output.

### Exit criteria

Mọi failed init/update để project trở lại trạng thái trước transaction.

---

## Phase 4 — Safe host config merge

### Tasks

1. Markdown managed blocks.
2. Structural JSON merge.
3. Namespaced hook IDs.
4. Conflict detection.
5. Uninstall cleanup.
6. Repair malformed blocks.

### Exit criteria

Existing user config được giữ nguyên byte-for-byte ngoài Maika managed area.

---

## Phase 5 — Platform detection và verification

### Tasks

1. Detect binary.
2. Detect version.
3. Detect auth khi safe.
4. Detect entrypoint support.
5. Verify hook integration.
6. Verify worker launch.
7. Store capability state.
8. Expose status/doctor.

### Exit criteria

Không platform nào được gọi là fully supported nếu chưa có verified integration path.

---

## Phase 6 — Worker strategy

### Tasks

1. Worker strategy negotiation.
2. Prompt file.
3. Structured argv.
4. `shell=False`.
5. No dangerous default.
6. Smoke test.
7. Fallback selection.
8. Per-platform override.

### Exit criteria

Setup tự chọn strategy khả dụng và giải thích lý do.

---

## Phase 7 — Stable hooks

### Tasks

1. Add `maika hook`.
2. Replace direct Python script invocation.
3. Cross-OS hook command.
4. Hook doctor.
5. Hook smoke tests.
6. Graceful diagnostic nếu CLI missing.

### Exit criteria

Hook không phụ thuộc system Python package state.

---

## Phase 8 — Multi-host enablement

### Tasks

1. Add enabled platform list.
2. Install multiple adapters.
3. Shared AGENTS block.
4. Per-host resolved state.
5. Cross-host locking.
6. Platform enable/disable commands.

### Exit criteria

Một project có thể dùng Claude Code và Codex luân phiên mà không migrate hoặc duplicate knowledge.

---

## Phase 9 — Legacy migration

### Tasks

1. Detect old roots.
2. Inventory ownership.
3. Generate migration plan.
4. Merge project-owned data.
5. Handle conflicts.
6. Install adapters.
7. Verify.
8. Optional cleanup.

### Exit criteria

Không mất knowledge, archive hoặc skill history trong platform switch.

---

## Phase 10 — Doctor, repair và uninstall

### Tasks

1. Full setup doctor.
2. Safe repair actions.
3. Transactional uninstall.
4. Preserve project data by default.
5. Machine-readable reports.

### Exit criteria

User có thể tự chẩn đoán và sửa setup mà không cần đọc source Maika.

---

## Phase 11 — Documentation và onboarding

### Tasks

1. Rewrite Quickstart:
   ```text
   install CLI
   cd project
   maika init
   maika doctor setup
   ```
2. Add per-platform guides.
3. Add existing-config examples.
4. Add migration guide.
5. Add enterprise/offline guide.
6. Add troubleshooting matrix.
7. Add uninstall and rollback guide.

---

## 17. Test strategy

### 17.1 Packaging tests

- wheel contains assets;
- init without source repo;
- pipx/uvx-style environment;
- version mismatch.

### 17.2 Scaffold tests

- clean project;
- existing AGENTS;
- existing CLAUDE;
- existing settings/hooks;
- unresolved template abort;
- user-owned preservation.

### 17.3 Merge tests

- managed block add/update/remove;
- duplicate marker;
- malformed marker;
- JSON unrelated keys preserved;
- duplicate hook ID;
- invalid JSON recovery.

### 17.4 Platform tests

Per platform:

```text
detect
install adapter
verify entrypoint
verify hook
verify worker
disable
re-enable
uninstall
```

### 17.5 Multi-host tests

```text
enable Claude + Codex
create task with Claude
continue task with Codex
verify same state and knowledge
```

### 17.6 Migration tests

```text
.agents legacy only
.claude legacy only
multiple identical roots
multiple conflicting roots
partial install
failed migration rollback
```

### 17.7 Cross-platform OS tests

- Ubuntu;
- Windows;
- mixed path separators;
- Unicode;
- spaces;
- CRLF;
- hook invocation from nested directory.

### 17.8 Real host smoke tests

Khi CI secret/environment cho phép:

- Claude Code CLI;
- Codex CLI;
- Antigravity CLI.

Nếu binary không khả dụng:

```text
mark integration test skipped
không claim verified support
```

---

## 18. Observability

### Install metrics

```yaml
installation_metrics:
  operation:
  duration:
  files_created:
  managed_blocks_updated:
  configs_merged:
  backups_created:
  repairs_required:
  rollback_occurred:
```

### Platform health

```yaml
platform_health:
  detected:
  entrypoint_verified:
  hook_verified:
  worker_verified:
  providers_verified:
  last_checked_at:
```

### UX metrics

```text
time-to-first-working-task
install success rate
repair rate
rollback rate
manual-step count
false-positive support claims
platform-switch success rate
```

---

## 19. Rollout strategy

### Stage 1 — Experimental package

- self-contained wheel;
- canonical `.maika`;
- single enabled platform;
- legacy compatibility.

### Stage 2 — Safe merge

- managed blocks;
- structural JSON merge;
- doctor setup;
- stable hooks.

### Stage 3 — Multi-host preview

- multiple enabled adapters;
- shared knowledge/state;
- platform verify.

### Stage 4 — Migration default

- legacy roots migrated;
- compatibility warnings;
- cleanup optional.

### Stage 5 — Stable multi-framework

- package distribution;
- full repair/uninstall;
- verified platform matrix;
- documented support tiers.

---

## 20. Support tiers

Không dùng một boolean `supported`.

```text
Tier 0 — Scaffold only
Files can be rendered, no host integration proof.

Tier 1 — Config integrated
Entrypoint and hooks are merged safely.

Tier 2 — Runtime verified
Host loads Maika, hook runs, worker spawns.

Tier 3 — Full capability verified
MCP, subagents, review dispatch and recovery pass E2E.
```

Status example:

```text
Claude Code: Tier 3
Codex: Tier 2
Antigravity IDE: Tier 1
Antigravity CLI: unavailable
```

---

## 21. Acceptance criteria

Upgrade chỉ hoàn thành khi:

1. CLI package tự chứa toàn bộ runtime assets.
2. User không cần giữ Maika source clone.
3. Canonical project core luôn nằm ở `.maika/`.
4. Knowledge và task state không nằm trong platform root.
5. Nhiều host có thể được enable đồng thời.
6. Existing AGENTS/CLAUDE content không bị overwrite.
7. Existing JSON settings/hooks được structural merge.
8. Installer có dry-run.
9. Installer có backup và rollback.
10. Init/update/migrate/uninstall đều transactional.
11. Hook gọi stable Maika CLI entrypoint.
12. Hook không phụ thuộc system Python dependencies.
13. Worker strategy được detect hoặc user chọn.
14. Dangerous permissions không bật mặc định.
15. Platform capability có advertised/detected/verified state.
16. `maika doctor setup` kiểm full integration.
17. `maika repair` sửa safe findings có chọn lọc.
18. Platform switch không làm mất knowledge.
19. Legacy migration có conflict handling.
20. Uninstall giữ project data mặc định.
21. Ubuntu tests pass.
22. Windows tests pass.
23. Multi-host E2E pass.
24. Wheel install E2E pass.
25. Support documentation phản ánh đúng verified tier.

---

## 22. Thứ tự ưu tiên

### P0 — Product correctness

- Self-contained package.
- Canonical `.maika` core.
- Safe config merge.
- Stable hook CLI.
- Transactional install.

### P1 — True multi-framework

- Multi-host enabled platforms.
- Runtime capability detection.
- Worker strategy negotiation.
- Full setup doctor.

### P2 — Migration và lifecycle

- Legacy migration.
- Repair.
- Safe uninstall.
- Project version pin.

### P3 — Enterprise UX

- Offline bundle.
- Central policy.
- Fleet diagnostics.
- Automated support matrix.
- Signed package/update artifacts.

---

## 23. Trạng thái đích

Maika hiện tại gần với:

```text
Một framework được render riêng cho từng agent platform.
```

Sau upgrade, Maika phải trở thành:

```text
Một project-native cognitive runtime có core dùng chung,
được nhiều coding agent host thông qua adapter an toàn và được verify.
```

Câu chốt:

> **Không phải “cài Maika cho Claude hoặc Codex”.  
> Mà là “cài Maika vào project, rồi kết nối những agent có thể sử dụng nó”.**
