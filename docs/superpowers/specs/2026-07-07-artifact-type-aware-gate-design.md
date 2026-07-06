# Artifact-type-aware gate cho handoff-slice / implementation-context

**Date:** 2026-07-07
**Status:** APPROVED (design)
**Scope:** `.maika/tools/gate-check/` (cli.py, gates.py, tests) + prose wiring trong `procedures/decision-gate.md`, microloop docs

## Problem

Gate `handoff-slice` và `implementation-context` hiện chỉ check *sự tồn tại của rule-id bất kỳ* (regex `_RULE_ID`) trong section `## Applicable DNA/Conventions`. Hệ quả:

- Rule-id **không tồn tại** trong `knowledge-index.yaml` vẫn pass (agent bịa `XX-99` là qua gate).
- Rule-id **có thật nhưng sai artifact_type** (ví dụ rule của `react-component` cite vào handoff của `java-service`) vẫn pass.

Đường index-aware đã tồn tại cho `knowledge-checkpoint` (cli.py nhận `--index` / `--artifact-type`, filter qua `_load_index_rule_ids`) nhưng chưa wire cho hai gate trên. Đây là follow-up "index-aware validator" đã ghi chú sẵn trong gates.py (comment cạnh `_NO_KNOWLEDGE`) và trùng gap "gate trigger là prose, chưa wired pre_conditions" trong decision-gates-followups.

**Bug sẵn có gộp vào cùng scope:** `_load_index_rule_ids` (cli.py:41) chỉ match `artifact_type in applies` — bỏ rơi entry global (`applies_to: []`), lệch semantics chuẩn đã chốt tại `procedures/context-loader.md` dòng 46–48 (`artifact_type in entry.applies_to OR not entry.applies_to`).

## Design

### 1. Filter slice (sửa `_load_index_rule_ids`, cli.py)

```python
valid = { entry.id for entry in index.entries
          if artifact_type is None
          or artifact_type in entry.applies_to
          or not entry.applies_to }          # global rule — áp dụng mọi artifact
```

- Entry có `applies_to: []` = **global**, luôn nằm trong slice (khớp context-loader.md).
- Node knowledge KHÔNG có key `applies_to` thì generate_index không index — nằm ngoài phạm vi gate (không validate được thứ không có trong index).
- Fix này thay đổi nhẹ behavior của `knowledge-checkpoint` theo hướng **lenient hơn** (thêm global rules vào valid set) — đúng doc, an toàn.

### 2. Validators (gates.py)

`validate_handoff_slice(text, valid_rule_ids=None)` và `validate_implementation_context(text, valid_rule_ids=None)`:

- `valid_rule_ids is None` (không truyền `--index`) → **behavior cũ giữ nguyên** (backward compatible).
- `valid_rule_ids` là set **không rỗng** → **STRICT trong section**: mọi rule-id xuất hiện trong section `## Applicable DNA/Conventions` phải thuộc `valid_rule_ids`. Một id lạ/sai type → FAIL với reason nêu rõ id vi phạm.
  - Chỉ quét section này, KHÔNG quét toàn file — prose chỗ khác nhắc "PR-33" không gây false-fail.
- Slice **rỗng** (không có entry nào match artifact_type — fresh project hoặc type chưa có rule): CLI **không truyền** `valid_rule_ids` (validator chạy đường legacy: chỉ cần section có ≥1 rule-id) và in WARN `slice empty for artifact_type=<t> — falling back to legacy check` ra stdout. Mirror pattern `allow_no_knowledge` của knowledge-checkpoint; validator không cần kwarg mới.

Fail messages (deterministic, actionable):

- `"handoff cites rule-ids not in knowledge-index slice for artifact_type=<t>: <ids>"`
- Giữ nguyên message cũ cho case thiếu section / không có rule-id.

### 3. CLI wiring (cli.py)

Mở rộng nhánh `--index` hiện có (đang chỉ phục vụ `knowledge-checkpoint`) cho `handoff-slice` và `implementation-context`:

```bash
python3 .maika/tools/gate-check/cli.py implementation-context \
  .maika/knowledge/active/TASK_HANDOFF.<node>.md \
  --index .maika/knowledge/long-term/knowledge-index.yaml \
  --artifact-type <type>
```

- Không truyền `--index` → validator chạy mode cũ (legacy PASS giữ nguyên).
- Truyền `--index` không kèm `--artifact-type` → slice = toàn bộ index (chỉ check tồn tại, không check type). Hợp lệ nhưng WARN khuyến nghị truyền type.

### 4. Prose wiring

- `procedures/decision-gate.md`: lệnh gọi gate tại decision-point implementation bổ sung `--index` + `--artifact-type <type do R-Guard-2 detect>`.
- `tools/microloop-orchestrator/README.md` (và chỗ nào ghi lệnh gate tương ứng trong `rules-tool.md`): cùng cập nhật.
- `hooks/write-gate/write_gate.py` **KHÔNG đổi** trong scope này — hook không biết artifact_type của node; nếu observed failure xuất hiện ở tầng hook thì làm follow-up (ghi vào followups, không build trước).

## Tests (`tests/test_gates.py` + coverage cho cli helper)

1. PASS — rule-id match artifact_type.
2. PASS — global rule (`applies_to: []`) với artifact_type bất kỳ.
3. FAIL — rule tồn tại nhưng `applies_to` không chứa artifact_type (strict: dù có kèm 1 rule đúng).
4. FAIL — rule-id không tồn tại trong index.
5. PASS — legacy mode (không truyền `valid_rule_ids`) giữ nguyên behavior cũ.
6. PASS (fallback) — slice rỗng cho artifact_type chưa có rule → legacy check.
7. `_load_index_rule_ids`: global entry được include khi có artifact_type (fix bug lệch doc).
8. Áp cho CẢ HAI gate: handoff-slice và implementation-context.

## Definition of Done

- [ ] `implementation-context` và `handoff-slice` support `--index` / `--artifact-type` qua cli.py.
- [ ] Strict-in-section semantics như §2; legacy mode không đổi khi thiếu `--index`.
- [ ] `_load_index_rule_ids` include global rules (khớp context-loader.md).
- [ ] Unit tests §Tests pass (`/usr/bin/python3 -m pytest .maika/tools/gate-check/tests/`).
- [ ] `decision-gate.md` + microloop docs gọi gate kèm artifact_type của node.
- [ ] KHÔNG đụng: dashboard, token-budget, stale-hash, write_gate.py.

## Out of scope (ghi nhận, không build)

- Hash/version stamp chống stale knowledge trong TASK_HANDOFF — chờ observed failure (R2: build for observed failures only).
- Write-gate hook artifact_type-aware — hook không có nguồn artifact_type tin cậy; theo dõi qua followups.
- Hard context-budget gate theo phase — không enforce được trên số tự khai.
