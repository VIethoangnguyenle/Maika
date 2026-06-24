# UA-First Business Analysis + SP3 Skill Standard — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking. Mỗi lần rewrite skill **dùng `superpowers:writing-skills`** làm methodology.

**Goal:** Buộc pha phân tích nghiệp vụ đối chiếu code (UA-first) trước khi hỏi user, và chuẩn hoá 4 skill liên quan theo SP3 (rule đập-vào-mắt + kiểm cơ học).

**Architecture:** Sửa doctrine tại nguồn-sự-thật (`rules-tool.md` + `task.md`) trước; nâng `validate_skills.py` thành gate cơ học SP3 (opt-in qua frontmatter `standard: SP3`); rồi rewrite 4 skill bằng `writing-skills` để pass gate. Skill prose không có sự kiện runtime để hook (DEVELOPMENT_RULES R4) → enforcement = chất lượng prose + linter gate.

**Tech Stack:** Python 3.10+ (`validate_skills.py`, pytest), Markdown skills với `{{ tools.* }}` / `{{ platform.* }}` templating (resolve tại `maika init` — KHÔNG sửa tên tool thủ công, R-Adapter-3).

## Global Constraints

- DEVELOPMENT_RULES R1: mọi field/flag mới (`standard: SP3`) phải có consumer cơ học trong cùng PR = `validate_skills.py`.
- DEVELOPMENT_RULES R3: enforcement mới phải có fixture/litmus tái hiện lỗi.
- DEVELOPMENT_RULES R6: doc bị ghi đè phải đóng dấu (`bao_cao_loi.md`, framing R-Tool-5 cũ).
- DEVELOPMENT_RULES R7: net-negative/neutral — chỉ 4 skill, không big-bang 14.
- KHÔNG sửa tên tool thủ công trong skill (R-Adapter-3); giữ nguyên `{{ tools.* }}` placeholders.
- Thẩm quyền-khi-mâu-thuẫn KHÔNG đổi: knowledge chính thắng (R-KL-3). Doctrine chỉ về *thứ tự dùng*.
- Doctrine canonical (copy verbatim khi cần): *UA + kinh nghiệm trước → Codebase Memory hỗ trợ (extract logic trong hàm) → grep fallback. Lỗi Codebase MCP ≠ UA chết.*

---

## File Structure

| File | Trách nhiệm | Task |
|---|---|---|
| `rules/rules-tool.md` | Doctrine canonical (R-Tool-5 priority order) | 1 |
| `workflows/task.md` | Bỏ KG-first GATE, theo UA-first | 1 |
| `bao_cao_loi.md` | Đóng dấu RESOLVED | 1 |
| `tools/skill-lint/validate_skills.py` | Gate cơ học S1/S2/S3 (opt-in SP3) | 2,3,4 |
| `tools/skill-lint/tests/test_validate_skills.py` | Test S1/S2/S3 | 2,3,4 |
| `skills/codebase-explorer/SKILL.md` | UA-primary + SP3 | 5 |
| `skills/requirement-analyst/SKILL.md` | Đối chiếu codebase + Open-Q filter + SP3 | 6 |
| `skills/openspec-explore/SKILL.md` | consult-before-ask + SP3 | 7 |
| `skills/spec-extract/SKILL.md` | consult-before-ask + SP3 | 7 |

**Canonical reflex block** (dùng cho S1 — chèn ngay sau frontmatter mỗi skill SP3, tinh chỉnh wording theo vai skill):

```markdown
## Quy tắc cốt lõi (reflex)

> **UA-first khi trace code.** Thứ tự nguồn BẮT BUỘC:
> 1. **UA + kinh nghiệm** (agent-memory, knowledge-snapshot) — LUÔN trước. UA là bản đồ node (class/func/domain/flow/quan hệ/entry-point), KHÔNG chứa logic → dùng để trace/định vị.
> 2. **Codebase Memory** — hỗ trợ, vào SAU: extract logic trong thân hàm tại node UA đã định vị.
> 3. **grep** — fallback cuối.
>
> Lỗi Codebase Memory MCP ≠ UA không khả dụng: lỗi một cái → vẫn thử cái kia, KHÔNG fallback grep cả hai.
```

---

## Task 1: Doctrine source-of-truth + supersede stamps

**Files:**
- Modify: `.maika/rules/rules-tool.md` (block "Đường evidence song song theo loại fact" trong R-Tool-5)
- Modify: `.maika/workflows/task.md:110-128` (bước "Gọi codebase-explorer")
- Modify: `bao_cao_loi.md` (thêm header RESOLVED)

**Interfaces:**
- Produces: doctrine canonical mà Task 5–7 trích dẫn (reflex block); marker text `UA-first` + `Codebase Memory hỗ trợ` để litmus Task 8 grep.

- [ ] **Step 1: Viết litmus đỏ — grep doctrine chưa tồn tại**

Run:
```bash
cd /home/zane/Desktop/Maika
grep -c "Codebase Memory hỗ trợ\|UA + kinh nghiệm" .maika/rules/rules-tool.md
```
Expected: `0` (doctrine mới chưa có) — xác nhận điểm xuất phát.

- [ ] **Step 2: Viết lại R-Tool-5 block "Đường evidence song song"**

Trong `.maika/rules/rules-tool.md`, thay bullet `**Đường evidence song song theo loại fact**` (và sub-bullets architecture-facts/code-facts về *thứ tự dùng*) bằng:

```markdown
- **Thứ tự nguồn khi trace code (UA-first):**
  1. **UA + kinh nghiệm** (`agent-memory` R-Tool-6, `knowledge-snapshot`) — LUÔN trước.
     UA là bản đồ node (class/func/domain/flow/quan hệ/entry-point), **không chứa logic** →
     dùng để trace/định vị/map. Blast-radius độ cao kiến trúc: UA (`find_impact`/`domain_relationships`) trước.
  2. **Codebase Memory** — hỗ trợ UA, vào SAU: extract **logic trong thân hàm**
     (`get_node_source`) tại node UA đã định vị.
  3. **grep** — fallback cuối; KG/UA vắng → dòng degrade + hạ confidence.
  - Lỗi Codebase Memory MCP ≠ UA không khả dụng → vẫn thử UA độc lập, không fallback grep cả hai.
  - *Identifier trong EXPLORE_CONTEXT* vẫn phân theo fact-type: architecture-facts → UA identifier
    (domain/flow/entry-point); code-facts → `node_id`. (Đây là phân loại *nhãn lưu*, không phải *thứ tự dùng*.)
  - Mâu thuẫn ở code-fact: surface vào `AGENT_TRANSPARENCY`, knowledge chính thắng (R-KL-3), không suppress.
```

- [ ] **Step 3: Viết lại bước codebase-explorer trong task.md (bỏ KG-first GATE)**

Trong `.maika/workflows/task.md`, mục `3. Gọi codebase-explorer` (dòng ~112–128): thay sub-bullet altitude (dòng 113) và block `[GATE] Kiểm tra trạng thái KG graph trước bất kỳ tool nào khác` bằng:

```markdown
   - **UA-first** (xem `codebase-explorer` SKILL §Quy tắc cốt lõi): `{{ tools.domain_overview }}` →
     `{{ tools.domain_flow }}` để map domain/flow/entry-point/ranh giới async TRƯỚC.
   - Đọc `{{ platform.framework_root }}/knowledge/active/REQUIREMENT.md`, map yêu cầu → domain/module/service.
   - **Codebase Memory hỗ trợ SAU**: `{{ tools.search_code }}` định vị symbol, `{{ tools.read_file }}`
     extract logic trong hàm tại node UA đã chỉ. Lỗi Codebase MCP ≠ UA chết — vẫn dùng UA.
   - KG/UA vắng → gợi ý `/understand` rebuild; tạm grep với Độ tin cậy thấp hơn (không bịa).
   - Cập nhật section "Kiến trúc code hiện tại (codebase-explorer)" trong EXPLORE_CONTEXT.
   - **Ghi kèm identifier** (UA domain/flow/entry-point hoặc node_id) cho mỗi component quan trọng.
```

- [ ] **Step 4: Đóng dấu RESOLVED lên bao_cao_loi.md**

Thêm ngay dưới dòng tiêu đề `# Báo cáo sự cố — Bỏ qua UA khi Explore Codebase`:

```markdown
> **Status:** RESOLVED by `docs/superpowers/specs/2026-06-24-ua-first-business-analysis-design.md` (2026-06-24).
```

- [ ] **Step 5: Verify litmus xanh**

Run:
```bash
grep -c "Codebase Memory hỗ trợ\|UA + kinh nghiệm" .maika/rules/rules-tool.md
grep -c "Kiểm tra trạng thái KG graph trước bất kỳ tool" .maika/workflows/task.md
grep -c "RESOLVED by" bao_cao_loi.md
```
Expected: dòng 1 ≥ `1`; dòng 2 = `0` (GATE cũ đã xoá); dòng 3 = `1`.

- [ ] **Step 6: Commit**

```bash
rtk git add .maika/rules/rules-tool.md .maika/workflows/task.md bao_cao_loi.md
rtk git commit -m "feat(doctrine): UA-first source-of-truth in R-Tool-5 + task.md"
```

---

## Task 2: Linter S1 — doctrine/reflex lên đầu (opt-in SP3)

**Files:**
- Modify: `.maika/tools/skill-lint/validate_skills.py`
- Test: `.maika/tools/skill-lint/tests/test_validate_skills.py`

**Interfaces:**
- Consumes: `parse_frontmatter` (có sẵn).
- Produces: `check_s1_reflex_upfront(fm, body) -> tuple[bool|None, str]` (None nếu `standard != "SP3"`); hằng `SP3_DOCTRINE_HEADING`; field frontmatter `standard`.

- [ ] **Step 1: Viết test thất bại cho S1**

Thêm vào `test_validate_skills.py`:

```python
from validate_skills import check_s1_reflex_upfront

class TestS1ReflexUpfront:
    def test_sp3_with_reflex_upfront_passes(self):
        fm = {"standard": "SP3"}
        body = "## Quy tắc cốt lõi (reflex)\n\n> UA-first...\n\n## Mục tiêu\n"
        passed, _ = check_s1_reflex_upfront(fm, body)
        assert passed is True

    def test_sp3_without_reflex_fails(self):
        fm = {"standard": "SP3"}
        body = "## Mục tiêu\n\nNội dung dài...\n" + "x\n" * 50
        passed, _ = check_s1_reflex_upfront(fm, body)
        assert passed is False

    def test_sp3_reflex_too_deep_fails(self):
        fm = {"standard": "SP3"}
        body = "filler\n" * 40 + "## Quy tắc cốt lõi (reflex)\n"
        passed, _ = check_s1_reflex_upfront(fm, body)
        assert passed is False

    def test_non_sp3_skipped(self):
        fm = {"standard": None}
        body = "## Mục tiêu\n"
        passed, _ = check_s1_reflex_upfront(fm, body)
        assert passed is None
```

- [ ] **Step 2: Chạy test — xác nhận FAIL**

Run: `cd .maika/tools/skill-lint && python3 -m pytest tests/test_validate_skills.py::TestS1ReflexUpfront -v`
Expected: FAIL — `ImportError: cannot import name 'check_s1_reflex_upfront'`.

- [ ] **Step 3: Implement S1**

Thêm vào `validate_skills.py` (sau `check_f5_outputs`):

```python
SP3_DOCTRINE_HEADING = re.compile(
    r"^\s*##\s+(Quy tắc cốt lõi|Core [Rr]ule|Reflex)", re.MULTILINE
)
SP3_REFLEX_MAX_LINE = 30  # heading reflex phải nằm trong N dòng đầu body


def check_s1_reflex_upfront(fm: dict, body: str) -> tuple[bool | None, str]:
    """[S1] SP3: heading 'Quy tắc cốt lõi/Reflex' nằm trong N dòng đầu body."""
    if fm.get("standard") != "SP3":
        return None, ""  # opt-in — chỉ áp SP3
    head = "\n".join(body.splitlines()[:SP3_REFLEX_MAX_LINE])
    if not SP3_DOCTRINE_HEADING.search(head):
        return False, (
            f"SP3 thiếu '## Quy tắc cốt lõi' trong {SP3_REFLEX_MAX_LINE} dòng đầu body"
        )
    return True, ""
```

- [ ] **Step 4: Wire S1 vào validate_skill + report**

Trong `validate_skill`, sau khi tính F1–F5 (nhánh `fm is not None`), thêm:
```python
        results["S1"] = check_s1_reflex_upfront(fm, body)
```
Và trong nhánh `fm is None` thêm `"S1"` vào vòng lặp set `(False, "không parse được frontmatter YAML")`.
Cập nhật hằng: `CHECK_IDS = ["F1", "F2", "F3", "F4", "F5", "S1", "B1", "B2", "B3", "B4", "B5"]`.

- [ ] **Step 5: Chạy test — xác nhận PASS + không regress**

Run: `cd .maika/tools/skill-lint && python3 -m pytest tests/test_validate_skills.py -v`
Expected: PASS toàn bộ (S1 mới + SP2 cũ).

- [ ] **Step 6: Commit**

```bash
rtk git add .maika/tools/skill-lint/validate_skills.py .maika/tools/skill-lint/tests/test_validate_skills.py
rtk git commit -m "feat(skill-lint): S1 reflex-upfront check (opt-in SP3)"
```

---

## Task 3: Linter S2 — flowchart bắt buộc cho process-skill SP3

**Files:**
- Modify: `.maika/tools/skill-lint/validate_skills.py`
- Test: `.maika/tools/skill-lint/tests/test_validate_skills.py`

**Interfaces:**
- Produces: `check_s2_flowchart(fm, body) -> tuple[bool|None, str]` (None nếu `standard != "SP3"`).

- [ ] **Step 1: Viết test thất bại cho S2**

```python
from validate_skills import check_s2_flowchart

class TestS2Flowchart:
    def test_sp3_with_dot_passes(self):
        fm = {"standard": "SP3"}
        body = "## Quy trình\n\n```dot\ndigraph{a->b}\n```\n"
        assert check_s2_flowchart(fm, body)[0] is True

    def test_sp3_with_mermaid_passes(self):
        fm = {"standard": "SP3"}
        body = "## Quy trình\n\n```mermaid\nflowchart TD\n```\n"
        assert check_s2_flowchart(fm, body)[0] is True

    def test_sp3_no_flowchart_fails(self):
        fm = {"standard": "SP3"}
        body = "## Quy trình\n\nBước 1...\n"
        assert check_s2_flowchart(fm, body)[0] is False

    def test_non_sp3_skipped(self):
        assert check_s2_flowchart({}, "## Quy trình\n")[0] is None
```

- [ ] **Step 2: Chạy test — xác nhận FAIL**

Run: `cd .maika/tools/skill-lint && python3 -m pytest tests/test_validate_skills.py::TestS2Flowchart -v`
Expected: FAIL — ImportError.

- [ ] **Step 3: Implement S2**

```python
SP3_FLOWCHART = re.compile(r"```(dot|mermaid)\b")


def check_s2_flowchart(fm: dict, body: str) -> tuple[bool | None, str]:
    """[S2] SP3: phải có ít nhất 1 sơ đồ ```dot hoặc ```mermaid (cho process-skill)."""
    if fm.get("standard") != "SP3":
        return None, ""
    if not SP3_FLOWCHART.search(body):
        return False, "SP3 thiếu flowchart (```dot hoặc ```mermaid)"
    return True, ""
```

- [ ] **Step 4: Wire S2**

Trong `validate_skill` thêm `results["S2"] = check_s2_flowchart(fm, body)` (và `"S2"` vào nhánh `fm is None`). `CHECK_IDS`: chèn `"S2"` sau `"S1"`.

- [ ] **Step 5: Chạy test — PASS**

Run: `cd .maika/tools/skill-lint && python3 -m pytest tests/test_validate_skills.py -v`
Expected: PASS toàn bộ.

- [ ] **Step 6: Commit**

```bash
rtk git add .maika/tools/skill-lint/validate_skills.py .maika/tools/skill-lint/tests/test_validate_skills.py
rtk git commit -m "feat(skill-lint): S2 flowchart check (opt-in SP3)"
```

---

## Task 4: Linter S3 — ngân sách core (WARN, không FAIL)

**Files:**
- Modify: `.maika/tools/skill-lint/validate_skills.py`
- Test: `.maika/tools/skill-lint/tests/test_validate_skills.py`

**Interfaces:**
- Produces: `check_s3_core_budget(fm, body) -> tuple[str, str]` trả status chuỗi `"PASS"|"WARN"|"SKIP"`; hằng `SP3_CORE_MAX_LINES = 200`. WARN KHÔNG ảnh hưởng exit code (chỉ in cảnh báo).

- [ ] **Step 1: Viết test thất bại cho S3**

```python
from validate_skills import check_s3_core_budget, SP3_CORE_MAX_LINES

class TestS3CoreBudget:
    def test_sp3_within_budget_pass(self):
        fm = {"standard": "SP3"}
        body = "x\n" * (SP3_CORE_MAX_LINES - 1)
        assert check_s3_core_budget(fm, body)[0] == "PASS"

    def test_sp3_over_budget_warn(self):
        fm = {"standard": "SP3"}
        body = "x\n" * (SP3_CORE_MAX_LINES + 5)
        assert check_s3_core_budget(fm, body)[0] == "WARN"

    def test_non_sp3_skip(self):
        body = "x\n" * (SP3_CORE_MAX_LINES + 5)
        assert check_s3_core_budget({}, body)[0] == "SKIP"
```

- [ ] **Step 2: Chạy test — FAIL**

Run: `cd .maika/tools/skill-lint && python3 -m pytest tests/test_validate_skills.py::TestS3CoreBudget -v`
Expected: FAIL — ImportError.

- [ ] **Step 3: Implement S3**

```python
SP3_CORE_MAX_LINES = 200


def check_s3_core_budget(fm: dict, body: str) -> tuple[str, str]:
    """[S3] SP3: core SKILL.md ≤ ngưỡng dòng (progressive disclosure). WARN, không FAIL."""
    if fm.get("standard") != "SP3":
        return "SKIP", ""
    n = len(body.splitlines())
    if n > SP3_CORE_MAX_LINES:
        return "WARN", f"SP3 core {n} dòng > {SP3_CORE_MAX_LINES} — đẩy chi tiết sang references/"
    return "PASS", ""
```

- [ ] **Step 4: Wire S3 vào report (không tính total_fail)**

Trong `validate_skill` thêm: `results["S3"] = check_s3_core_budget(fm, body)` (trong nhánh `fm is None` đặt `results["S3"] = ("SKIP", "")`).
Trong `print_report`, sau vòng tính fail, thu thập WARN riêng:
```python
        s3 = results.get("S3", ("SKIP", ""))
        if s3[0] == "WARN":
            details.append(f"\n  {skill_name}: [S3 WARN] {s3[1]}")
```
S3 KHÔNG được cộng vào `total_fail` (chỉ FAIL của F*/S1/S2/B* mới ảnh hưởng exit code). KHÔNG thêm `"S3"` vào `CHECK_IDS` (giữ bảng status binary; S3 báo ở phần CHI TIẾT).

- [ ] **Step 5: Chạy test + full lint hiện trạng**

Run: `cd .maika/tools/skill-lint && python3 -m pytest tests/test_validate_skills.py -v && python3 validate_skills.py`
Expected: pytest PASS toàn bộ; `validate_skills.py` exit 0 (10 skill SP2 hiện tại không có `standard: SP3` nên S1/S2/S3 = SKIP/`--`).

- [ ] **Step 6: Commit**

```bash
rtk git add .maika/tools/skill-lint/validate_skills.py .maika/tools/skill-lint/tests/test_validate_skills.py
rtk git commit -m "feat(skill-lint): S3 core-budget warning (opt-in SP3)"
```

---

## Task 5: Rewrite `codebase-explorer` → UA-primary + SP3

**Files:**
- Modify: `.maika/skills/codebase-explorer/SKILL.md`
- (Tuỳ) Create: `.maika/skills/codebase-explorer/references/altitude-routing.md` (chi tiết đẩy ra nếu vượt ngân sách S3)

**Interfaces:**
- Consumes: doctrine canonical (Task 1), reflex block (header plan).
- Produces: skill với `standard: SP3` pass S1/S2; doctrine UA-first; `domain_overview` vô điều kiện; NC-2 đóng.

**Methodology:** dùng `superpowers:writing-skills` — core gọn, reflex lên đầu, flowchart Golden Path, đẩy bảng chi tiết sang `references/`.

- [ ] **Step 1: Thêm `standard: SP3` + reflex block**

Trong frontmatter thêm dòng `standard: SP3`. Ngay sau `---` đóng frontmatter, chèn **canonical reflex block** (header plan), tinh chỉnh: bổ sung câu *"Chỉ tuyên 'localized' SAU khi đã thấy `{{ tools.domain_overview }}` — không skip UA như quyết định a-priori."*

- [ ] **Step 2: Viết lại §2 Altitude Routing theo UA-primary**

Thay framing "UA và Codebase bổ trợ nhau, không thay thế" + bảng "Codebase là chính cho static-trace" bằng thứ tự ưu tiên §3.1 của spec. Cập nhật Cue Cards: cột ROUTINE luôn dẫn về UA-first cho flow/abstract/gRPC; chỉ "đã có symbol cụ thể, sửa 1 hàm" mới dùng Codebase (đọc logic), KHÔNG để Codebase định hình kiến trúc. Bản đồ năng lực: Codebase chỉ còn cột "extract logic trong hàm" + "đọc code"; blast-radius/quan hệ chuyển UA `{{ tools.domain_relationships }}` trước.

- [ ] **Step 3: `domain_overview` vô điều kiện + đóng NC-2**

Trong "Cổng độ phức tạp": `{{ tools.domain_overview }}` là **bước đầu vô điều kiện** cho task flow/cross-service; bỏ nhánh "task localized → bỏ qua UA top-down" như quyết định trước-khi-thấy-map. Trong "Degradation": thêm dòng *"Lỗi Codebase Memory MCP (`code_status` fail / project-not-found) ≠ UA không khả dụng — thử UA độc lập, KHÔNG fallback grep cả hai."*

- [ ] **Step 4: Thêm flowchart Golden Path (S2)**

Chèn vào section Quy trình một `dot` graph thể hiện B1 `domain_overview`(UA) → B2 `search_code`(CB) → B3 `domain_flow`(UA) → B4 `read_file`(CB) → B5 verify, với nhãn UA/Codebase rõ vai.

- [ ] **Step 5: Verify lint**

Run: `cd .maika/tools/skill-lint && python3 validate_skills.py`
Expected: `codebase-explorer` PASS S1+S2 (S3 có thể WARN — nếu WARN, Step 6 đẩy chi tiết sang `references/`).

- [ ] **Step 6: (Nếu S3 WARN) đẩy chi tiết sang references + re-lint**

Tạo `references/altitude-routing.md` chứa bảng chi tiết/ví dụ; trong SKILL.md để con trỏ `Xem references/altitude-routing.md`. Re-run linter → S3 PASS hoặc WARN chấp nhận được (WARN không chặn).

- [ ] **Step 7: Commit**

```bash
rtk git add .maika/skills/codebase-explorer/
rtk git commit -m "feat(codebase-explorer): UA-primary doctrine + SP3 standard"
```

---

## Task 6: Rewrite `requirement-analyst` → đối chiếu codebase + Open-Q filter + SP3

**Files:**
- Modify: `.maika/skills/requirement-analyst/SKILL.md`

**Interfaces:**
- Consumes: doctrine canonical; reflex block.
- Produces: skill `standard: SP3` pass S1/S2; bước "Đối chiếu codebase" (UA-first probe) trước As-is; bộ lọc Open-Question.

**Methodology:** `superpowers:writing-skills`.

- [ ] **Step 1: `standard: SP3` + reflex block (biến thể nghiệp vụ)**

Thêm `standard: SP3` vào frontmatter. Chèn reflex block sau frontmatter, thêm câu chốt: *"Trước khi hỏi user: câu hỏi code-trả-lời-được → tự giải bằng UA-first probe; chỉ unknown nghiệp vụ thật mới hỏi."*

- [ ] **Step 2: Chèn bước "Đối chiếu codebase" trước Bước 4 (As-is)**

Thêm bước mới (đánh số lại Bước 4→5…), nội dung:

```markdown
### Bước 4 — Đối chiếu codebase (UA-first reconnaissance probe)

Trước khi viết As-is và trước khi ghi BẤT KỲ Open Question nào, chạy **probe nhẹ** (KHÔNG
gọi full `codebase-explorer` — tránh phụ thuộc vòng với pre_condition REQUIREMENT.md):

1. `{{ tools.domain_overview }}` → luồng/use-case này có domain tương ứng trong hệ thống không?
2. `{{ tools.domain_flow }}` → nếu có, entry point (REST/gRPC/Kafka) + các step hiện tại.

Kết quả nuôi As-is/To-be:
- **Có trong code** → As-is = flow thực đã implement (kèm UA identifier); To-be = delta.
- **Chưa có** → ghi rõ "luồng chưa tồn tại trong codebase → feature mới".

Probe vắng UA → ghi hạn chế vào AGENT_TRANSPARENCY, hạ Độ tin cậy As-is; không bịa.
```

- [ ] **Step 3: Thêm bộ lọc Open-Question vào bước "Giả định & Vấn đề yêu cầu"**

Chèn trước khi liệt kê Open Questions:

```markdown
> [!IMPORTANT]
> **Bộ lọc trước khi hỏi user.** Phân loại mỗi câu:
> - **Code-trả-lời-được** (entry point? race/lock xử lý ra sao? flow đã tồn tại? approve/reject
>   hiện làm gì?) → PHẢI giải qua UA-first probe (Bước 4), KHÔNG đưa vào Open Question. Câu trả
>   lời đi vào As-is / Technical Design Contract.
> - **Unknown nghiệp vụ thật** (SLA? business rule? ai duyệt? ưu tiên?) → mới ghi Open Question cho user.
```

- [ ] **Step 4: Thêm `codebase` vào nguồn Bước 1 + flowchart (S2)**

Bước 1 (Thu thập nguồn): thêm mục `- **Codebase** (qua UA-first probe, Bước 4)`. Chèn `dot` flowchart quy trình: Thu thập → Đối chiếu codebase (UA probe) → As-is/To-be → Scope → AC → lọc Open-Q → finalise.

- [ ] **Step 5: Verify lint**

Run: `cd .maika/tools/skill-lint && python3 validate_skills.py`
Expected: `requirement-analyst` PASS S1+S2.

- [ ] **Step 6: Commit**

```bash
rtk git add .maika/skills/requirement-analyst/
rtk git commit -m "feat(requirement-analyst): codebase reconnaissance + open-question filter + SP3"
```

---

## Task 7: `openspec-explore` + `spec-extract` → consult-before-ask + SP3

**Files:**
- Modify: `.maika/skills/openspec-explore/SKILL.md`
- Modify: `.maika/skills/spec-extract/SKILL.md`

**Interfaces:**
- Consumes: doctrine canonical; reflex block.
- Produces: cả hai `standard: SP3` pass S1/S2; doctrine "đối chiếu code (UA-first) trước khi hỏi user" tại entry-point brainstorm/extract.

**Methodology:** `superpowers:writing-skills`. Lưu ý `openspec-explore` là skill OpenSpec vanilla — chỉ chèn vào phần augmentation tiếng Việt, giữ phần vanilla phía trên nguyên (portability).

- [ ] **Step 1: openspec-explore — `standard: SP3` + reflex (biến thể thinking-partner)**

Thêm `standard: SP3` vào `metadata`/frontmatter (không phá field OpenSpec hiện có). Trong phần augmentation tiếng Việt (sau "## Mục tiêu"), chèn reflex block, biến thể: *"Khi brainstorm chạm code: UA-first probe (`domain_overview`/`domain_flow`) để tự-trả-lời trước khi hỏi user — đừng đẩy câu hỏi code-trả-lời-được sang user."*

- [ ] **Step 2: openspec-explore — bổ sung "Grounded" thành hành động cụ thể + flowchart (S2)**

Mục "Grounded" của The Stance: nâng từ "explore actual codebase" thành *"UA-first probe trước khi hỏi user; code-trả-lời-được → tự giải"*. Chèn `dot` flowchart nhỏ: câu hỏi nảy sinh → code-trả-lời-được? → (có) UA probe / (không) hỏi user.

- [ ] **Step 3: spec-extract — `standard: SP3` + reflex block**

Thêm `standard: SP3`. Sau frontmatter chèn reflex block, biến thể: *"Khi tài liệu mô tả luồng đã/đang tồn tại: UA-first probe verify trong code trước khi ghi gap hoặc hỏi user."*

- [ ] **Step 4: spec-extract — chèn đối chiếu code vào Bước 10 (Ghi lỗ hổng) + flowchart (S2)**

Tại "Bước 10 — Ghi lỗ hổng & câu hỏi cần làm rõ": thêm — *"Trước khi ghi lỗ hổng/câu hỏi: chạy UA-first probe; nếu code đã trả lời (luồng tồn tại, entry point rõ) → ghi vào nội dung extract, KHÔNG thành câu hỏi cho user."* Chèn `dot` flowchart quy trình extract có nhánh UA probe.

- [ ] **Step 5: Verify lint**

Run: `cd .maika/tools/skill-lint && python3 validate_skills.py`
Expected: `openspec-explore` + `spec-extract` PASS S1+S2.

- [ ] **Step 6: Commit**

```bash
rtk git add .maika/skills/openspec-explore/ .maika/skills/spec-extract/
rtk git commit -m "feat(openspec-explore,spec-extract): consult-code-before-ask UA-first + SP3"
```

---

## Task 8: Litmus tổng + full lint xanh

**Files:**
- Create: `.maika/tools/skill-lint/tests/test_sp3_doctrine_litmus.py`

**Interfaces:**
- Consumes: 4 skill SP3 (Task 5–7), doctrine (Task 1).

- [ ] **Step 1: Viết litmus L2/L3 (content assertions tái hiện sự cố)**

```python
#!/usr/bin/env python3
"""L2/L3 — litmus tái hiện sự cố bao_cao_loi.md (UA-skip)."""
from pathlib import Path

SKILLS = Path(__file__).resolve().parents[2] / "skills"
RULES = Path(__file__).resolve().parents[2] / "rules" / "rules-tool.md"

def _read(p): return p.read_text(encoding="utf-8")

def test_l3_nc2_codebase_error_not_ua_down():
    # Lỗi Codebase MCP ≠ UA chết — phải có trong codebase-explorer + doctrine
    ce = _read(SKILLS / "codebase-explorer" / "SKILL.md")
    assert "≠ UA" in ce or "không khả dụng" in ce
    assert "≠ UA" in _read(RULES) or "không fallback grep cả hai" in _read(RULES)

def test_l2_requirement_analyst_has_probe_and_filter():
    ra = _read(SKILLS / "requirement-analyst" / "SKILL.md")
    assert "Đối chiếu codebase" in ra            # bước probe
    assert "Code-trả-lời-được" in ra              # bộ lọc Open-Q
    assert "domain_overview" in ra

def test_l2_explore_paths_consult_before_ask():
    for name in ("openspec-explore", "spec-extract"):
        body = _read(SKILLS / name / "SKILL.md")
        assert "standard: SP3" in body
        assert "UA-first" in body or "UA probe" in body
```

- [ ] **Step 2: Chạy litmus**

Run: `cd .maika/tools/skill-lint && python3 -m pytest tests/test_sp3_doctrine_litmus.py -v`
Expected: 3 test PASS (nếu fail → quay lại task tương ứng sửa nội dung skill).

- [ ] **Step 3: Full lint + full test xanh**

Run: `cd .maika/tools/skill-lint && python3 validate_skills.py && python3 -m pytest tests/ -v`
Expected: `validate_skills.py` exit 0 (4 skill SP3 PASS S1/S2; 10 skill SP2 không regress); pytest toàn bộ PASS.

- [ ] **Step 4: Commit**

```bash
rtk git add .maika/tools/skill-lint/tests/test_sp3_doctrine_litmus.py
rtk git commit -m "test(skill-lint): SP3 doctrine litmus reproducing bao_cao_loi.md scenario"
```

---

## Self-Review

**Spec coverage:**
- §3 doctrine → Task 1 ✅ | §4.1 codebase-explorer → Task 5 ✅ | §4.2 requirement-analyst → Task 6 ✅ | §4.3 openspec-explore/spec-extract → Task 7 ✅ | §5 SP3 + linter → Task 2–4 ✅ | §6 litmus L1/L2/L3 → Task 2–4 (L1 lint) + Task 8 (L2/L3) ✅ | §7 file table → File Structure ✅ | §3.2 supersede stamps → Task 1 Step 4 + Step 2 ✅
- Bổ sung ngoài spec (đã ghi rõ): field `standard: SP3` làm cơ chế opt-in cho S1/S2/S3 — đúng DEVELOPMENT_RULES R1 (consumer = linter), nằm trong intent §5.

**Placeholder scan:** không có TBD/TODO; mọi step code có code thật; nội dung skill insert verbatim. Phần "rewrite §2 theo writing-skills" là delegation có chủ đích với gate cơ học (linter S1/S2) làm tiêu chí pass — không phải placeholder.

**Type consistency:** `check_s1_reflex_upfront`/`check_s2_flowchart` trả `tuple[bool|None,str]` (đồng dạng F4/F5, vào bảng status `--`/✅/❌); `check_s3_core_budget` trả `tuple[str,str]` (`PASS|WARN|SKIP`) — cố ý khác để không tính vào exit code, xử lý riêng trong report. `CHECK_IDS` thêm `S1`,`S2` (không thêm `S3`). Nhất quán giữa Task 2/3/4 và Task 8.

---

## Execution Handoff
(Điền sau khi user chọn cách thực thi.)
