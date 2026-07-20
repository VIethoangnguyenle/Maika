# Secret-Gate — Mechanical secret protection for Maika-owned artifacts

- **Date:** 2026-07-20
- **Status:** Design — pending review
- **Scope:** P0, write-side MVP. Học từ ClaudeKit `privacy-block`, thích ứng vào `write-gate` sẵn có.
- **Related:** `rules/core/write-boundary.md`, `hooks/write-gate/write_gate.py`, R-Data-1/R-Data-2 (prose data rules)

---

## 1. Context & Problem

Luận đề của Maika: **biến chỉ dẫn thành gate cơ học, không dựa vào prompt**. Nhưng lớp bảo vệ dữ liệu nhạy cảm hiện tại — `R-Data-1`/`R-Data-2` ("không log PII/credential/token vào context files") — **chỉ là prose**. Đã xác minh: không có tool nào dưới `.maika/tools/` hay hook nào quét secret; `write-gate` hiện chỉ kiểm phase/scope/hash, không kiểm *nội dung* secret.

**Threat model.** Một worker (sau khi đã thấy secret thật từ `.env`, DB creds, hay response của MCP) **vô tình ghi secret đó vào một artifact do Maika sở hữu** — `AGENT_TRANSPARENCY.md`, `EXPLORE_CONTEXT.md`, `knowledge-snapshot.md`, `changes/<id>/briefs|results|reviews`. Các artifact này **được commit vào repo** → secret rò rỉ, lại còn kèm audit trail bền vững (mỉa mai với một framework lấy audit làm điểm mạnh).

**Điểm mỉa mai cần vá:** framework xây để cưỡng chế bằng máy, nhưng để lớp chống rò rỉ dữ liệu ở dạng chữ. ClaudeKit đã chứng minh khuôn mẫu cưỡng chế (`privacy-block`, một PreToolUse hook chặn cơ học). Spec này **mượn khuôn mẫu đó, thích ứng write-side, nhét vào `write-gate` sẵn có** — không tạo hạ tầng mới.

---

## 2. Goals / Non-goals

### Goals
1. **Chặn cơ học** việc ghi secret high-precision vào artifact do Maika sở hữu, trên **mọi platform**, qua đường PreToolUse của `write-gate` đã có.
2. Trên detection: **block + ghi degradation record** (kiểu R-Tool-7), **không bao giờ log secret thô**.
3. Rule là **data** (`profiles/secret-gate.yaml`) + **allowlist per-repo** có `reason`.
4. Wire vào CI (`scripts/run_ci.py`) với fixture true-positive và false-positive.

### Non-goals (chốt theo quyết định thiết kế)
- ❌ **Read-side** (chặn đọc `.env`) — hoãn sang phase sau; R-Data prose vẫn là backstop.
- ❌ **PII heuristics / entropy scan** — hoãn; v1 chỉ format secret high-precision.
- ❌ **Pre-commit scan source ứng dụng nói chung** — ngoài phạm vi; gate **chỉ** nhắm bề mặt artifact-của-Maika.
- ❌ **Redaction / auto-mutate output** — bị loại; hành động là *block*, không sửa lén.

---

## 3. Design decisions

| Quyết định | Chọn | Vì sao | Hoãn (alternative) |
|---|---|---|---|
| Phạm vi | **Write-side only** | Enforce cơ học trên MỌI nền qua write-gate; không có điểm mù nền tảng | Read-side (CC-only mechanical, degrade nơi khác) |
| Hành động khi phát hiện | **Block + degradation record** | Khớp mô hình gate của Maika (write-gate vốn block); minh bạch, không mutate lén | Redact-and-continue; Block+human-confirm |
| Detection corpus | **Secrets high-precision** | False-positive thấp → gate được tin & không cản flow | +PII heuristics; +entropy scan |
| Fail mode khi scanner lỗi | **Fail-closed (block) mặc định, configurable** | Bề mặt nhỏ & quan trọng; lỗi scanner không được biến thành lỗ rò | `on_error: allow` cho pipeline không chịu được stall |

---

## 4. Scope of enforcement — *chỉ* artifact-của-Maika

Gate **chỉ** quét write có target là artifact do framework sở hữu dưới `framework_root`:

- `knowledge/active/**` (`AGENT_TRANSPARENCY.md`, `EXPLORE_CONTEXT.md`, `REQUIREMENT.md`, `ideation/**`, `TOKEN_LOG.md`)
- `knowledge/long-term/**` (`knowledge-snapshot.md`, `conventions.yaml`, `author-dna.yaml`)
- `changes/<id>/{briefs,results,reviews,generated}/**`, `changes/<id>/*.md|*.yaml`

Write vào **source ứng dụng** (ngoài artifact-Maika) **đi thẳng, không đụng** — đó là việc của developer/pre-commit, không phải của Maika. Điều này (a) giữ false-positive thấp (không chặn `.env.example` hay code load secret hợp lệ), và (b) nhắm đúng bề mặt rò rỉ thật (artifact được commit).

**Tái dùng phân loại path sẵn có:** `write_gate.py` đã biết `framework_root` và vai trò artifact (xem `_framework_role_allows`). Secret-gate gọi sau khi path đã được phân loại là artifact-Maika **và** các gate phase/scope hiện tại đã pass.

---

## 5. Architecture & integration

### Module mới
`hooks/write-gate/secret_scan.py` — hàm thuần, không side-effect:

```python
def scan(content: str, rules: list[Rule]) -> list[Match]: ...
# Match = (rule_id, label, line, masked_preview)   # KHÔNG BAO GIỜ chứa giá trị thô
```

### Điểm cắm trong `write_gate.py`
Sau khi path được xác định là artifact-Maika và gate hiện tại cho phép, *trước khi* allow:

```
matches = secret_scan.scan(content, load_secret_rules())
if matches:
    return ("deny", build_reason(matches, record_path))   # dùng ĐÚNG pattern deny-tuple sẵn có
```

`write_gate.py` **đã có** phần phát-quyết đa-runtime (đã xác minh):
- Claude Code: `exit 2` + reason ra stderr.
- Codex: stdout JSON `hookSpecificOutput.permissionDecision = deny`.
- Antigravity: stdout JSON `decision = deny`.

→ **Không viết code phát-quyết mới.** Secret-gate chỉ đóng góp thêm một nhánh `("deny", reason)`.

### Config
`profiles/secret-gate.yaml` (đặt cạnh `execution-mode.yaml`, `capability-registry.yaml`). `write-gate` vốn "reads canonical config" → nạp thêm profile này.

### Flow

```
PreToolUse(Write|Edit)
   │  stdin JSON {file_path, content|new_string, ...}
   ▼
maika hook write-gate --runtime <cc|codex|antigravity>
   │  locate root · load canonical config · delegate write_gate.main
   ▼
path ∈ artifact-Maika ? ──no──▶ [gate hiện tại] ──▶ allow / deny (như cũ)
   │ yes
   ▼
[gate phase/scope/hash hiện tại] ──deny──▶ (như cũ)
   │ pass
   ▼
secret_scan(content) ── match? ──yes──▶ DENY + ghi degradation record ─▶ emit deny (đa-runtime)
   │ no
   ▼
allow
```

---

## 6. Detection corpus (high-precision, v1)

Rule là **data** trong `secret-gate.yaml` (versioned, đổi không cần sửa code). v1 ưu tiên **token có prefix biết trước** (FP cực thấp) + **assignment có ngữ cảnh**:

| rule_id | Bắt gì | Mẫu đại diện |
|---|---|---|
| `private-key` | PEM private key | `-----BEGIN (RSA\|EC\|OPENSSH\|PGP) PRIVATE KEY-----` |
| `aws-access-key` | AWS access key id | `AKIA[0-9A-Z]{16}` |
| `gcp-sa-key` | GCP service-account json | `"private_key"\s*:\s*"-----BEGIN` |
| `jwt` | JSON Web Token | `eyJ[A-Za-z0-9_-]+\.eyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+` |
| `github-token` | GitHub PAT | `gh[pousr]_[A-Za-z0-9]{36,}` |
| `slack-token` | Slack token | `xox[baprs]-[A-Za-z0-9-]{10,}` |
| `stripe-live` | Stripe live key | `sk_live_[A-Za-z0-9]{24,}` |
| `generic-assignment` | gán secret có ngữ cảnh | `(?i)(api[_-]?key\|secret\|token\|password)\s*[:=]\s*['"][^'"]{16,}` |
| `dotenv-dump` | ghi nguyên khối `KEY=VALUE` trông như `.env` | heuristic: ≥3 dòng `[A-Z_]+=…` với value entropy-cao |

Cố ý **không** dùng bare-entropy scan ở v1 (nhiều FP → hoãn).

---

## 7. Decision output & degradation record

**Reason string** (con người + máy đọc được, **không** chứa secret thô):

```
[R-Data-3] secret-gate: blocked write to knowledge/active/AGENT_TRANSPARENCY.md
— 1 match: aws-access-key@L42 (masked: AKIA****NM7Q); record: changes/<id>/generated/DEGRADATION.jsonl
```

**Degradation record** — append JSONL (kiểu R-Tool-7):

```json
{"ts":"2026-07-20T…","gate":"secret-gate","severity":"high","action":"blocked",
 "rule_id":"aws-access-key","artifact":"knowledge/active/AGENT_TRANSPARENCY.md",
 "line":42,"masked_preview":"AKIA****NM7Q","runtime":"claude"}
```

- **Masked preview** = first4 + `****` + last2. **Giá trị thô KHÔNG BAO GIỜ được ghi** vào record, reason, hay stderr.
- Nếu không có change-id context (write ngoài một change): fallback ghi vào `{framework_root}/logs/secret-gate.jsonl`.

---

## 8. Config & allowlist

```yaml
# profiles/secret-gate.yaml
version: 1
enabled: true
on_error: block          # fail-closed; đổi 'allow' nếu pipeline không chịu được stall (đánh đổi được ghi rõ)
rules:
  private-key:        {enabled: true}
  aws-access-key:     {enabled: true}
  gcp-sa-key:         {enabled: true}
  jwt:                {enabled: true}
  github-token:       {enabled: true}
  slack-token:        {enabled: true}
  stripe-live:        {enabled: true}
  generic-assignment: {enabled: true}
  dotenv-dump:        {enabled: true}
allowlist:
  - path_glob: "docs/**/examples/**"
    rule_ids: [generic-assignment]
    reason: "documented example tokens in guide fixtures, not real credentials"
  - fingerprint: "sha256:…"           # hash của một chuỗi false-positive đã biết
    reason: "vendor sample key in provider integration doc, verified non-live"
```

- Allowlist entry **bắt buộc `reason`** (mượn kỷ luật allowlist-reason của CK: tối thiểu 20 ký tự, cấm placeholder `ok`/`tbd`).
- Cả `path_glob`+`rule_ids` (miễn theo path/rule) lẫn `fingerprint` (miễn một chuỗi cụ thể) đều hỗ trợ.

---

## 9. Testing

**Unit — `secret_scan`:** mỗi rule có 1 fixture true-positive + 1 false-positive:
- FP ví dụ: chữ `AKIA` trong prose; `.env.example` với placeholder `xxx`; biến tên `token` không có value.
- Assert: `masked_preview` **không** chứa giá trị thô; `scan()` deterministic.

**Integration — `write_gate`:** dựng stdin payload PreToolUse:
- brief chứa AWS key → `deny` + record ghi ra + reason có `[R-Data-3]`.
- brief sạch → `allow`.
- secret ở path **ngoài** artifact-Maika → `allow` (ngoài scope).
- match nhưng nằm allowlist → `allow`.
- scanner raise (mô phỏng) + `on_error: block` → `deny`; `on_error: allow` → `allow` + record cảnh báo.

**Record hygiene:** regex-assert record + reason + stderr **không** chứa bất kỳ secret thô nào của fixture.

**CI:** thêm `{"name": "secret-gate", "paths": [".maika/hooks/write-gate/tests"]}` (hoặc path test riêng) vào list trong `scripts/run_ci.py`, cùng cụm với `write-gate`/`gate-check`.

---

## 10. Rollout & migration

- **Phase 1 (spec này):** write-side MVP, high-precision, block+record, CI-wired.
- **Hoãn (spec riêng sau):** read-side (CC PreToolUse matcher `Read|Bash|Grep` → `maika hook secret-gate --side read` → human-confirm); PII heuristics; entropy scan.
- **Migration:** `secret-gate.yaml` là **framework-owned** → scaffold render lúc `init`, `maika update` re-render (ownership model xử lý, không cần `deletions[]`). Đăng ký **`R-Data-3 [CRITICAL]`** (secret-gate cơ học) trong rules manifest; R-Data-1/2 giữ vai **backstop prose** cho bề mặt gate chưa phủ (vd read-side).

---

## 11. Open questions

1. **Edit payload:** `Edit`/`MultiEdit` gửi `new_string` chứ không phải full file — scan `new_string` là đủ (secret nằm trong phần thêm mới). Cần xác nhận shape payload từng runtime (CC vs Codex vs Antigravity).
2. **Nơi ghi record khi không có change-id:** chốt fallback `{framework_root}/logs/secret-gate.jsonl` — cần xác nhận đường này không tự nó bị gate chặn (loại trừ path log khỏi scope).
3. **`on_error` mặc định:** `block` (fail-closed) — xác nhận maintainer chấp nhận rủi ro stall pipeline khi scanner có bug, đổi lấy an toàn.
4. **`dotenv-dump` heuristic:** ngưỡng entropy/số-dòng cần tune trên corpus thật để không chặn nhầm config mẫu.
