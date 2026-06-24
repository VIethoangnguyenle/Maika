# UA-First Business Analysis + Chuẩn viết skill SP3

> **Date:** 2026-06-24
> **Status:** Approved (design) — ready for implementation plan
> **Lineage:** giải sự cố `bao_cao_loi.md` (2026-06-24, phiên `727c1e4a…`) — agent skip
> Understand-Anything (UA) khi brainstorm luồng "Hủy lệnh" (SRS QLGD), hỏi user những
> câu code đã trả lời được. **Supersedes** một phần framing "đường evidence song song
> đồng cấp theo loại fact" trong `rules/rules-tool.md` R-Tool-5 (commit `458aba1`).
> **Tuân thủ:** `.maika/DEVELOPMENT_RULES.md` R1–R7.

---

## 1. Bối cảnh & vấn đề

`bao_cao_loi.md` ghi nhận: trong một phiên brainstorm tài liệu wiki (luồng Hủy lệnh,
cross-service approval-service ↔ transfer-service, Kafka + gRPC), agent **bỏ qua hoàn
toàn UA** trong lượt explore đầu, chỉ `grep` + `view_file`, và **đặt cho user nhiều câu
hỏi mà code đã trả lời được**. Chỉ khi user nhắc, agent mới gọi UA và nhận ra giá trị.

Phân rã hai lỗi bị gộp:

- **F1 — Trace code sai nguồn.** Khi *đã* quyết định đọc code, agent ưu tiên
  `grep` > Codebase Memory > UA. Đây là `codebase-explorer` violation (NC-2/NC-3/NC-4
  trong report).
- **F2 — Không trace, đi hỏi luôn.** Pha phân tích nghiệp vụ phản xạ mặc định là **hỏi
  user** thay vì đọc code. Lỗi này xảy ra *trước* khi `codebase-explorer` có cơ hội chạy.

**Yếu tố khuếch đại (gốc rễ tại sao prose không đổi hành vi):** `codebase-explorer/SKILL.md`
đã ghi đủ Cue Cards / Complexity Gate / Golden Path / anti-pattern §7 — nhưng là một
*bức tường prose* nơi quy tắc "UA-first" bị chôn trong §2 giữa hàng tá caveat. Linter
`tools/skill-lint/validate_skills.py` chỉ kiểm *sự hiện diện* của section (schema SP2),
không kiểm *chất lượng / vị trí rule* → skill pass lint trong khi rule không đập vào mắt.

**Bài học đã đóng cửa (DEVELOPMENT_RULES R4):** không thể enforce "đọc SKILL.md trước"
bằng hook — `native_skill_export = None` trên mọi platform, skill là markdown inline,
không có sự kiện runtime để hook. → Fix buộc phải là **chất lượng prose + gate theo
artifact** (mô hình write-gate), KHÔNG phải hook skill-dispatch.

## 2. Mục tiêu & phi mục tiêu

**Mục tiêu:**

1. **Doctrine thứ tự nguồn rõ ràng** khi trace code: UA + kinh nghiệm trước → Codebase
   Memory hỗ trợ (extract logic trong hàm) → grep fallback. Sửa tại nguồn-sự-thật, không
   sửa N bản sao.
2. **Pha phân tích nghiệp vụ đối chiếu code trước khi hỏi user** (đóng F2): câu hỏi
   code-trả-lời-được phải tự giải qua UA-first probe; chỉ unknown nghiệp vụ thật mới hỏi user.
3. **`codebase-explorer` UA-primary** (đóng F1): `domain_overview` là bước đầu vô điều
   kiện cho task flow; lỗi Codebase Memory MCP ≠ UA chết.
4. **Chuẩn viết skill SP3** + nâng linter để rule "đập vào mắt" (core gọn, doctrine lên
   đầu, flowchart), áp cho 4 skill đang chạm.

**Phi mục tiêu (ghi nhận):**

- **Không** hook skill-dispatch (R4 — không có trigger trên mọi platform).
- **Không** big-bang reformat cả 14 skill (R3/R7 — chỉ skill chạm bởi observed failure).
- **Không** rule SP3 nào không kiểm cơ học được mà vẫn nhét vào chuẩn — nếu không lint
  được thì giữ là guideline trong `writing-skills`, không vào `validate_skills.py`.
- Không đổi thẩm quyền-khi-mâu-thuẫn: knowledge chính (`knowledge-snapshot`) vẫn thắng
  agent-memory/UA/Codebase (R-KL-3 giữ nguyên). Doctrine này chỉ về *thứ tự dùng*.

## 3. Doctrine — UA-first khi trace code

### 3.1 Quy tắc chuẩn (đặt tại `rules/rules-tool.md` R-Tool-5, tóm tại `workflows/task.md:113`)

Khi trace code, thứ tự nguồn **bắt buộc**:

1. **UA + kinh nghiệm — LUÔN trước.** UA là bản đồ cấu trúc: node class / func / domain /
   flow / quan hệ / entry-point. "Kinh nghiệm" = `agent-memory` (R-Tool-6) +
   `knowledge-snapshot`. Dùng để **trace / định vị / map**.
2. **Codebase Memory — hỗ trợ UA, vào SAU.** Vai trò hẹp: **extract logic bên trong thân
   hàm** tại node UA đã định vị (đọc implementation, error-handling, threading).
3. **grep — fallback cuối** khi cả hai vắng.

**Why (lý do làm rule tự-dính, in-line trong doctrine):** *UA là các node — class, func,
quan hệ — hoàn toàn không chứa logic. Chỉ Codebase Memory mới đọc được logic trong thân
hàm.* Vì vậy trace/định vị là việc của UA; đọc-logic-chi-tiết là việc của Codebase. Hỏi
"luồng bắt đầu ở đâu / service nối nhau ra sao / impact tới đâu" → UA. Hỏi "hàm này thực
sự làm gì bên trong" → Codebase.

**Phân vai impact/blast-radius:** ở độ cao kiến trúc (quan hệ, impact, caller cross-service)
→ UA `domain_relationships` trước. Codebase Memory chỉ vào để đọc thân hàm liên quan.

### 3.2 Supersede (DEVELOPMENT_RULES R6)

R-Tool-5 hiện mô tả UA và Codebase là **hai đường evidence song song đồng cấp theo loại
fact** (architecture-facts↔UA, code-facts↔KG). Doctrine mới **giáng** Codebase xuống vai
hỗ trợ dưới UA. PR thực thi phải:

- Viết lại block "Đường evidence song song theo loại fact" trong R-Tool-5 thành thứ tự
  ưu tiên §3.1 (giữ phần phân biệt fact-type cho mục đích *identifier trong
  EXPLORE_CONTEXT*, bỏ hàm ý đồng cấp về *thứ tự dùng*).
- Đóng dấu `bao_cao_loi.md`: `Status: RESOLVED by docs/superpowers/specs/2026-06-24-ua-first-business-analysis-design.md`.

## 4. Thay đổi nội dung skill

### 4.1 `skills/codebase-explorer/SKILL.md` (đóng F1)

- Viết lại §2 (Altitude Routing / Cue Cards / Bản đồ năng lực / Golden Path / Bước 4–5)
  theo doctrine §3.1 UA-primary. Bỏ framing "đồng cấp, bổ trợ".
- `domain_overview` (UA) = **bước đầu vô điều kiện** cho task flow/cross-service. Agent
  phải *thấy* domain map rồi mới được tuyên bố "localized" — bỏ van escape
  "localized → skip UA" như quyết định a-priori (đây là lỗ hổng agent grep-biased lách).
- **Đóng NC-2:** ghi rõ "lỗi Codebase Memory MCP ≠ UA không khả dụng". Khi
  `code_status`/Codebase probe fail → **vẫn phải thử UA độc lập**, không fallback grep cả hai.
- Codebase Memory mô tả lại đúng vai: extract logic trong hàm (`get_symbol`/`read_file`),
  không phải nguồn định hình kiến trúc.

### 4.2 `skills/requirement-analyst/SKILL.md` (đóng F2)

- **Chèn bước mới "Đối chiếu codebase" (trước Bước 4 As-is):** chạy **UA-first
  reconnaissance probe** (`domain_overview` → `domain_flow`) trả lời: *luồng/use-case này
  đã tồn tại trong hệ thống chưa, và chạy ra sao*. Đây là probe nhẹ, **không** gọi full
  `codebase-explorer` (tránh phụ thuộc vòng với pre_condition `REQUIREMENT.md not_skeleton`).
  - Có trong code → As-is mô tả flow thực đã implement (kèm UA identifier); To-be là delta.
  - Chưa có → ghi rõ "luồng chưa tồn tại → feature mới".
- **Bộ lọc Open-Question (Bước 8):** trước khi một mục vào "Vấn đề yêu cầu":
  - **Code-trả-lời-được** (entry point? race/lock xử lý ra sao? flow đã tồn tại? approve/
    reject hiện làm gì?) → **PHẢI** giải qua UA-first probe, KHÔNG hỏi user. Câu trả lời đi
    vào As-is / Technical Design Contract.
  - **Unknown nghiệp vụ thật** (SLA? business rule? ai duyệt?) → mới hỏi user.
- Bổ sung `codebase` vào danh sách nguồn ở Bước 1 (hiện chỉ ticket/doc/chat).

### 4.3 `skills/openspec-explore/SKILL.md` + `skills/spec-extract/SKILL.md` (scope b)

- Áp cùng doctrine "đối chiếu code trước khi hỏi user, UA-first probe" ở entry-point
  brainstorm wiki/SRS/ideation — đây là nơi sự cố gốc xảy ra. Trước khi sinh clarifying
  questions cho user, chạy UA-first probe để tự-trả-lời phần code đã có.

## 5. Chuẩn viết skill SP3 + nâng `validate_skills.py`

Mục tiêu: rule "đập vào mắt", không bị chôn. Mỗi rule SP3 mới **bắt buộc có Cách kiểm cơ
học trong linter** (DEVELOPMENT_RULES R1 — consumer cùng PR). Rule không lint được →
không vào chuẩn, chỉ là guideline trong `writing-skills`.

| Rule SP3 | Nội dung | Cách kiểm cơ học (linter) |
|---|---|---|
| **S1 — Doctrine/Reflex lên đầu** | Block "quy tắc cốt lõi / reflex" ngay sau frontmatter, trước section dài | Regex: có heading/marker doctrine trong N dòng đầu của body |
| **S2 — Flowchart cho process-skill** | Section Quy trình của skill quy trình phải có sơ đồ | Có code block ```` ```dot ```` hoặc ```` ```mermaid ```` trong/ngay sau section Quy trình |
| **S3 — Ngân sách core (progressive disclosure)** | SKILL.md core ≤ ngưỡng dòng; chi tiết đẩy sang `references/` | Đếm dòng body; vượt ngưỡng → WARN (không FAIL, tránh chặn cứng) |

- **Phạm vi áp:** chỉ 4 skill đang chạm (`codebase-explorer`, `requirement-analyst`,
  `openspec-explore`, `spec-extract`) — R3/R7. Skill khác migrate khi được chạm sau.
- **Phương pháp khi rewrite:** mỗi skill dùng `writing-skills` (skill-creator) làm
  methodology — core gọn, doctrine + why lên đầu, flowchart, anti-pattern table,
  reference files cho chi tiết.
- Giữ SP2 hiện hành (frontmatter + 5 section) là tập con của SP3 — không phá skill cũ.
  S1/S2 thêm mới; S3 chỉ WARN.

## 6. Verify / Litmus (DEVELOPMENT_RULES R3)

Enforcement/standard mới phải link tới litmus tái hiện lỗi:

- **L1 — Lint SP3:** chạy `validate_skills.py` trên 4 skill sau rewrite → S1/S2 PASS, S3
  trong ngân sách; 10 skill còn lại không regress SP2.
- **L2 — Kịch bản UA-skip:** fixture mô phỏng task "Hủy lệnh" (cross-service + Kafka/gRPC).
  Đọc skill SP3 mới, kiểm: doctrine UA-first nằm trong N dòng đầu; Open-Question filter
  của `requirement-analyst` phân loại đúng "race/lock xử lý ra sao" = code-trả-lời-được
  (→ probe), "SLA bao nhiêu" = nghiệp vụ (→ hỏi user).
- **L3 — NC-2 regression:** giả lập Codebase Memory probe fail → skill text dẫn agent vẫn
  thử UA, không fallback grep cả hai.

## 7. Phạm vi file đụng

| File | Thay đổi | Rule liên quan |
|---|---|---|
| `rules/rules-tool.md` | Viết lại R-Tool-5 → doctrine thứ tự §3.1 | R6 (supersede) |
| `workflows/task.md` | Cập nhật tóm tắt altitude dòng ~113 | — |
| `skills/codebase-explorer/SKILL.md` | UA-primary rewrite + SP3 | §4.1, S1–S3 |
| `skills/requirement-analyst/SKILL.md` | Bước đối chiếu + Open-Q filter + SP3 | §4.2, S1–S3 |
| `skills/openspec-explore/SKILL.md` | Doctrine consult-before-ask + SP3 | §4.3, S1–S3 |
| `skills/spec-extract/SKILL.md` | Doctrine consult-before-ask + SP3 | §4.3, S1–S3 |
| `tools/skill-lint/validate_skills.py` | Thêm check S1/S2/S3 | R1 (consumer) |
| `tools/skill-lint/tests/` | Fixture L1/L2/L3 | R3 |
| `bao_cao_loi.md` | Đóng dấu RESOLVED | R6 |

## 8. Giả định & câu hỏi mở

- **GĐ1:** UA-first reconnaissance probe (`domain_overview`/`domain_flow`) khả dụng độc
  lập với REQUIREMENT.md — đúng vì là MCP top-down, không cần artifact tiền đề. (Verify ở plan.)
- **GĐ2:** Ngưỡng dòng S3 — đề xuất khởi điểm, chốt con số khi đo 4 skill thực tế ở plan.
- **CHM1:** `architecture-reviewer` cũng trace code; doctrine §3.1 áp cho nó *về nguyên
  tắc*, nhưng KHÔNG nằm trong scope rewrite lần này (chưa phải observed-failure surface).
  Nó đọc doctrine chung từ R-Tool-5 nên tự hưởng — xác nhận ở plan.
