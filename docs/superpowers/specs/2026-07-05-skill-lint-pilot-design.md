# Design: skill-lint — enforce cơ học rubric BP cho skill + pilot 2 skill nặng nhất

> Trạng thái: design đã chốt với user (2026-07-05)
> Branch: `feat/skill-standard-lint` (stack trên `docs/anthropic-bp-audit-design` — PHỤ THUỘC rubric của audit; merge audit branch trước hoặc cùng đợt)
> Chuẩn nguồn: `docs/superpowers/specs/2026-07-04-anthropic-bp-rubric.md` (BP-01..BP-09, citation-grounded) — spec này KHÔNG định nghĩa chuẩn mới, chỉ enforce + áp dụng chuẩn đó.
> Liên quan: `2026-07-04-anthropic-bp-audit-report.md` (A-2/A-3/A-7); TODOS §BP-A*. Đợt driver trước: `2026-07-04-phase3-driver-thin-orchestrator-design.md` (cùng triết lý structure-thay-rule).

---

## 1. Vấn đề & bằng chứng

- 14 skill, ~193KB/~4.400 dòng; nặng nhất `infra-tdd` 481 dòng, `spec-extract` 459 — cả hai trong vùng cảnh báo BP-03 (400–500).
- Audit 2026-07-04 đã ra rubric BP-01..BP-22 citation-grounded, nhưng rubric hiện là **doc thuần** — không có consumer cơ học nào (đúng loại "rule trên giấy" mà audit A-1 tự chỉ ra). Nếu không enforce, skill mới/sửa sẽ lại trượt chuẩn như 14 skill cũ.
- Pattern `references/` + `skill-index.yaml` (generate_index.py) đã tồn tại — 3 skill dùng; scaffold đã copy references/ (18 dòng trong snapshot). Progressive disclosure là tổng quát hóa pattern đang chạy (R5), không phải kiến trúc mới.
- User chốt (2026-07-05): làm cả 3 hướng (cấu trúc+token, chuẩn nội dung, lint cơ học), chia 2 đợt — đợt 1: lint + pilot; đợt 2: migrate phần còn lại.

## 2. Quyết định scope (đã chốt với user)

1. **2 đợt**: đợt 1 (spec này) = lint + pilot migrate 2 skill nặng nhất làm bằng chứng (R3 litmus); đợt 2 = migrate 6 skill còn lại >300 dòng, allowlist về 0.
2. **Lint = pytest tại `cli/tests/test_skill_standard.py`** — zero hạ tầng mới, CI matrix chạy sẵn, KHÔNG scaffold xuống downstream (R7; precedent: test_snapshots.py đã đọc nội dung `.maika/`).
3. **Không viết SKILL_STANDARD.md mới** — chuẩn là rubric BP (điều chỉnh so với design nói miệng ban đầu, sau khi phát hiện audit; tránh 2 nguồn chuẩn song song — R6/R7).
4. **Giữ naming style hiện tại** (`spec-extract`…) — canon chấp nhận action-oriented/noun miễn nhất quán nội bộ; đổi tên 14 skill gãy reference khắp nơi, không đáng (R7).

## 3. Thiết kế

### 3.1 skill-lint — check cơ học, mỗi check gắn mã BP

File: `cli/tests/test_skill_standard.py`. Đối tượng: mọi thư mục con của `.maika/skills/` có `SKILL.md`. Checks:

| # | Check | BP | Ghi chú cơ học |
|---|---|---|---|
| L1 | Frontmatter parse được; `name` == tên thư mục; `name` ≤ 64 ký tự, chỉ `[a-z0-9-]` | BP-01 (nền) | yaml.safe_load phần giữa `---` |
| L2 | `description` non-empty, ≥ 80 và ≤ 1024 ký tự | BP-01/BP-02 (proxy cơ học — chất lượng trigger là việc review) | |
| L3 | Body SKILL.md ≤ **300 dòng** (house budget, gắt hơn trần 500 của BP-03 vì skill Maika chạy trong worker context mỏng) — trừ allowlist grandfather tường minh | BP-03 | allowlist chỉ được RÚT NGẮN; comment ghi rõ |
| L4 | References hai chiều: mọi file trong `references/` được SKILL.md nhắc tên; mọi `references/<f>` được nhắc phải tồn tại | BP-04 + R1 | orphan/dangling đều fail |
| L5 | References một cấp: file trong `references/` không link tới `references/` khác | BP-04 | grep link markdown trong references/*.md |
| L6 | Reference file > 100 dòng phải có mục lục ở đầu (heading `Mục lục`/`Contents` trong 30 dòng đầu) | BP-04 (TOC guidance, docs canon) | |
| L7 | Không `TODO`/`TBD`/`FIXME` trong SKILL.md + references | vệ sinh chung | trừ trong code-fence ví dụ có chủ đích? — KHÔNG ngoại lệ, giữ đơn giản |
| L8 | `skill-index.yaml` sync: mỗi thư mục skill có entry, mỗi entry có thư mục | BP-01 (index là nơi description sống lúc bootstrap) | |

Grandfather allowlist khởi điểm (skill > 300 dòng chưa migrate, sau pilot): `architecture-reviewer` (414), `knowledge-curator` (406), `requirement-analyst` (378), `spec-validator` (360), `openspec-explore` (360), `db-explorer` (311) — **6 skill**, là backlog tường minh của đợt 2.

**Chỉ L3 có grandfather.** Vi phạm L1/L2/L4–L8 ở 12 skill ngoài pilot (description ngắn, ref gãy/orphan, thiếu mục lục, TODO sót, index lệch) phát hiện khi lint chạy lần đầu → **sửa ngay trong đợt 1**: đây là fix nhỏ, cơ học, không đổi ngữ nghĩa skill (plan dành một task riêng cho việc này, danh sách vi phạm lấy từ output lần chạy lint đầu tiên).

Các BP không lint cơ học nổi (BP-05 không dạy điều model biết, BP-06 degrees-of-freedom, BP-07 script-hóa, BP-08 execution intent, BP-09 eval-first) → thuộc review checklist khi migrate (đợt này áp cho 2 pilot) + đã có đường riêng trong TODOS (A-2, A-7). Lint KHÔNG ôm — scope discipline.

Lint có **fixture test cho chính nó**: dựng skill giả trong tmp_path vi phạm từng check (L1..L8) → lint phải fail đúng check đó (R3 litmus của lint).

### 3.2 Pilot migrate 2 skill nặng nhất

`infra-tdd` (481 → nhắm ≤ 200) và `spec-extract` (459 → nhắm ≤ 200):

- SKILL.md giữ: mục tiêu, mô tả trigger (đồng bộ với description), quy trình checklist đánh số với lệnh/điều kiện cụ thể, đầu ra, self-check.
- Tách sang `references/` (một chủ đề một file, nhắc từ SKILL.md kèm **điều kiện đọc** "đọc khi…"): template mẫu dài, format standards, ví dụ chi tiết, hướng dẫn sâu từng tầng (infra-tdd T0–T4), bảng phân loại dài.
- **Không đổi ngữ nghĩa**: nội dung chỉ DI CHUYỂN, không viết lại ý; mọi đoạn xóa hẳn phải liệt kê trong report với lý do (trùng lặp/dạy điều model biết — BP-05).
- Đồng bộ `skill-index.yaml` (chạy lại generate_index.py nếu cần — plan verify vị trí/cách chạy script này, R4).
- Review ngữ nghĩa từng dòng bởi Claude (diff cũ↔mới đối chiếu thủ công).

### 3.3 Điều kiện nền (R4 — verify khi viết plan, trước khi code)

1. Vị trí + cách chạy `generate_index.py` (comment đầu skill-index.yaml nhắc nó) — tồn tại ở đâu, chạy thế nào, có check CI chưa.
2. Cơ chế khiến `DEVELOPMENT_RULES.md` không bị scaffold (exclude list trong cli/scaffold.py?) — chỉ để biết, đợt này không thêm doc mới vào `.maika/`.
3. pytest matrix hiện có (ubuntu+windows) chạy `cli/tests/` — lint phải cross-OS (đọc file bằng pathlib, không lệnh POSIX).

## 4. Testing & tiêu chí thành công đợt 1

- Lint fixture tests: mỗi check L1..L8 có case fail đúng + case pass.
- 2 skill pilot pass toàn bộ lint KHÔNG cần grandfather; 6 skill allowlist; 6 skill còn lại pass sẵn.
- Full suite xanh (`/usr/bin/python3 -m pytest .maika/ cli/ -q`), số test tăng đúng số test lint mới.
- Diff dòng của 2 SKILL.md pilot: giảm ≥ 50% mỗi file (phần dời sang references/ không tính là giảm tổng — tiêu chí là *file chính* mỏng để worker cold-start rẻ).
- Ngữ nghĩa 2 skill không đổi — Claude review đối chiếu, deviation ghi rõ.

## 5. Đối chiếu DEVELOPMENT_RULES

- **R1**: rubric BP có consumer cơ học đầu tiên (lint); mọi check gắn mã BP. Allowlist có consumer là chính lint.
- **R3**: pilot migrate là litmus sống của chuẩn; lint có fixture tái hiện từng vi phạm.
- **R4**: §3.3 verify trước khi code.
- **R5**: không dựng hệ chuẩn song song — enforce rubric có sẵn; mở rộng pattern references/ + skill-index đang chạy.
- **R6**: spec này ghi rõ thay thế ý định "SKILL_STANDARD.md mới" bằng rubric (không có doc cũ nào cần đóng dấu — ý định đó chưa từng thành file).
- **R7**: đợt 1 thêm 1 file test + fixture; 2 SKILL.md giảm ≥ 50% dòng; không dependency mới, không scaffold thêm.

## 6. Non-goals

- Không migrate 6 skill allowlist (đợt 2 — spec riêng khi pilot đã chứng minh chuẩn).
- Không đổi tên skill theo gerund.
- Không lint BP-05..BP-09 (không cơ học được — review checklist + TODOS A-2/A-7 lo).
- Không thêm `pre_conditions:`/`outputs:` frontmatter (gap #4 — đường riêng trong TODOS, tránh phình scope).
- Không xây eval harness per-skill (BP-09/A-7 — cần design riêng).
