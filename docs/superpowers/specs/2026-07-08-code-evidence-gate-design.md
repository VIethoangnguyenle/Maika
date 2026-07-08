# code-evidence gate — Design

> Ngày 2026-07-08. Tiến hóa `grep-honesty` thành gate positive `code-evidence` — chặn
> thật việc agent "trace code = grep" thay vì cbm/UA.

## Vấn đề

Gate `grep-honesty` (PR #36, chưa merge) dùng **logic phủ định + hậu kiểm text**: chỉ FAIL khi
artifact **thú nhận** một cụm "grep fallback / `<tool>` unavailable" cho file thuộc project đã-index.
Demo 2026-07-08 cho thấy nó chỉ đóng đúng một lỗ:

- **A. Cớ grep có khai** (file đã-index) → FAIL ✅
- **B. Grep lặng lẽ** — agent grep rồi ghi kết quả, không nhắc "grep"/"unavailable" → **PASS** ❌
- **C. Bịa evidence cbm** — ghi `node_id` không tồn tại trong graph → **PASS** ❌

Nguyên nhân: gate chỉ kích hoạt trên một *lời thú nhận*, và không kiểm evidence dương có thật.
Agent lười không khai, hoặc bịa "via cbm", đều lọt.

## Mục tiêu

Đảo sang **logic khẳng định + verify**: mọi code-fact section-scoped về file thuộc project
đã-index PHẢI được back bằng một `node_id` ở EXPLORE_CONTEXT §2.3 mà **cbm xác nhận tồn tại**.
`node_id` trở thành forcing-function — grep không đẻ ra node graph hợp lệ (bắt B), node bịa probe
không ra (bắt C), cớ-grep không có node (bắt A).

## Non-goals

- **UA node-verify:** UA graph chưa được sinh cho repo nào (`.understand-anything/knowledge-graph.json`
  không tồn tại ở đâu, verify 2026-07-08), nên node-verify hiện **chỉ cbm**. Interface để ngỏ cho UA
  khi có graph; không build UA-verify trong spec này.
- **Runtime block:** agy CLI không có hook (đã verify) → không chặn grep ở tool-level. Gate là hậu
  kiểm artifact; chốt un-gameable cuối vẫn là orchestrator (Claude re-probe khi review). Ngoài scope.
- **Đổi format artifact:** dùng nguyên §2.2/§2.3/§4 của `EXPLORE_CONTEXT.tpl.md` hiện có; không thêm
  section mới.

## Quyết định (từ brainstorm 2026-07-08)

1. **Enforcement = require + verify** (bắt cả B và C), không chỉ verify-present.
2. **Trigger = section-scoped**: chỉ enforce trong §2.2 Entry Points, §2.3 Key Components, §4 Phát
   hiện. Prose ngoài các section này (§1 DB, §5 notes…) không bị bắt → tránh over-fire trên nhắc-file
   thoáng qua.
3. **Probe-fail = fail-open + embed lỗi thật**: cbm unreachable → PASS chỉ khi artifact nhúng output
   lỗi cbm thật; prose "cbm down" suông → FAIL (đúng tenet gate-by-evidence).

## Thiết kế

### Contract (pass/fail)

- **§2.3 table:** mỗi `node_id` phải tồn tại thật trong graph cbm (probe). Node không có → FAIL (C).
- **§2.2 + §4:** file thuộc project đã-index nhắc ở đây phải có một §2.3 node đã-verify **trỏ đúng
  file đó**. Thiếu → FAIL (B).
- File **không** thuộc project đã-index nào → không enforce (grep hợp lệ cho upstream chưa index;
  map file→`root_path` như grep-honesty, cover upstream/downstream).
- Không project index nào (probe rỗng) → PASS (không có gì để verify — nhất quán grep-honesty).
- Probe lỗi (cbm down) → fail-open CHỈ KHI text nhúng chữ ký lỗi cbm thật; else FAIL.

### Components (tách bạch pure/impure)

- **`gates.py::validate_code_evidence(text, indexed_projects, verified_node_files, repo_root, probe_ok)`**
  — PURE, tất định. Thay `validate_grep_honesty`.
- **`gates.py` helper thuần:** `_parse_node_table(text)` → list node_id ở §2.3; `_section_files(text,
  sections)` → file-path trong §2.2/§4.
- **`capability.py::verify_nodes(project, node_ids) -> (dict[node_id, file], ok: bool)`** — IMPURE.
  Probe cbm (`get_code_snippet` hoặc `search_graph`): node tồn tại → `{node_id: file}`; node không có
  → vắng trong dict. `ok=True` khi probe chạy được (kể cả 0 node khớp); `ok=False` khi binary
  vắng/exception → caller set `probe_ok=False`.
- **`cli.py`** — caller: parse node table → `verify_nodes(project, ids)` → truyền `verified_node_files`
  + `probe_ok` vào validator. Gate `grep-honesty` đổi tên **`code-evidence`** (retire tên cũ; giữ
  `--repo-root`).

### Data flow

```
text
  → cli._parse_node_table(text)                → [node_id...]
  → capability.verify_nodes(project, ids)      → {node_id: file}  (probe cbm, impure)
  → gates.validate_code_evidence(
        text, indexed_projects, verified_node_files, repo_root, probe_ok)
      (a) mọi node §2.3 ∈ verified_node_files?      (không → FAIL: C)
      (b) mọi file §2.2/§4 ⊂ indexed project
          có node verified trỏ đúng file?           (không → FAIL: B)
  → PASS / FAIL(reason)
```

`indexed_projects` lấy từ `capability.indexed_projects(repo_root)` (đã có từ grep-honesty).
`project` để verify = project phủ file đang xét (map file→`root_path`), cover upstream/downstream.

### Error handling

- cbm binary vắng / probe exception → `probe_ok=False`. Validator: PASS chỉ khi text match chữ ký
  lỗi cbm thật (vd `"project is required"`, `"connection refused"`, `index_status` error); else FAIL.
- Không project index → PASS.
- Bảng §2.3 hỏng/rỗng nhưng §2.2/§4 có file-fact indexed → node phủ thiếu → FAIL (ép có bảng thật).

### Testing (TDD)

Pure validator (hermetic, `verified_node_files` truyền tay):
- C: §2.3 node giả (không ∈ verified) → FAIL.
- B: §4 nhắc file indexed, không §2.3 node phủ → FAIL.
- A: cớ grep, §2.3 rỗng → FAIL.
- PASS: §2.3 node verified + §4 file được node đó phủ.
- File chưa-index ở §4 → PASS.
- probe_ok=False + text nhúng lỗi cbm thật → PASS; prose "cbm down" suông → FAIL.
- Helper thuần: `_parse_node_table`, `_section_files` test riêng.

Impure probe:
- `verify_nodes` test bằng sample output cbm (parse), theo pattern `_parse_list_projects` đã có.

## Edge cases / giả định

- **node_id format:** giả định agent điền `node_id` = định danh cbm trả về (qualified_name/name).
  `verify_nodes` khớp bằng cách hỏi cbm trực tiếp; không tự chế thuật toán khớp mờ.
- **File-path trong §2.2:** cột `Path` của bảng Entry Points; trong §4: regex path như grep-honesty.
- **Nhiều project (upstream/downstream):** mỗi file map tới project theo `root_path`; verify node theo
  đúng project đó.
- **Migration/R6:** đóng dấu framing "grep-honesty chỉ bắt confessed" là superseded bởi spec này. PR:
  rework #36 thành gate đầy đủ HAY merge #36 rồi follow-up — quyết ở writing-plans.

## DEVELOPMENT_RULES

- **R3** (lỗi quan sát): B và C demo được 2026-07-08 (fixtures thật), không phải giả định.
- **R5** (mở rộng chốt): tiến hóa gate đang chạy đúng artifact (EXPLORE_CONTEXT), không dựng song song;
  `grep-honesty` (chỉ bắt A) bị hấp thụ.
- **R7** (net-negative): một gate làm nhiều hơn + xóa check thừa; interface UA để ngỏ nhưng không build.
