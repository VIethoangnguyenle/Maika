# Báo cáo Audit — Maika vs Best Practices Anthropic

> Ngày: 2026-07-05. Rubric: [2026-07-04-anthropic-bp-rubric.md](2026-07-04-anthropic-bp-rubric.md) (22 tiêu chí, 100% citation-grounded).
> Evidence: 2 batch worker codex (262 block, coverage 100% — 14 SKILL.md, 6 rule file, meta-prompt, 9 workflow); spot-check 7/7 khớp nguyên văn (BATCH A PASS, BATCH B PASS).
> Verdict lọc 2 tầng theo spec §8: chỉ gap khớp failure đã quan sát mới thành fix proposal; còn lại watchlist.
> Không sửa file nào trong vòng audit này (spec §10).

## Danh mục failure đã quan sát (bảng đối chiếu)

| F | Mô tả | Nguồn | Trạng thái |
| --- | --- | --- | --- |
| F-01 | Đa số rule `[CRITICAL]` chỉ "trên giấy", không hook cơ học; gap #4 (skill phá hủy thiếu `pre_conditions` máy đọc) và #6 còn TODO | TODOS.md §Enforcement hardening (audit 2026-06-20) | OPEN một phần (#1,#2,#3,#5 DONE) |
| F-02 | "Deterministic guardrail" nhưng chạy bằng prose — model có thể reason vượt qua | docs/Maika-v3-assessment.md §2 W1 | OPEN một phần |
| F-03 | Compliance theater — checkpoint tự khai "đã check" ≠ thật sự check | docs/Maika-v3-assessment.md §2 W2 | OPEN |
| F-04 | Workflow không phân tầng theo cỡ việc; "Pha 1 > 50.000 token" tự tố cáo | docs/Maika-v3-assessment.md §2 W3; TODOS UP5 | OPEN |
| F-05 | Context tràn/compact làm mất rules/DNA → agent code cảm tính (downstream Antigravity 2026-07-03); bookkeeping ăn budget | specs/2026-07-04-phase3-driver §1; assessment W4 | OPEN (driver fix vòng lặp Pha 3, chưa fix footprint) |
| F-06 | Không outcome loop — rule tích lũy không prune (48 heading), không biết rule nào đáng tiền | assessment §2 W6; TODOS UP1 + P1.1 | OPEN |
| F-07 | Gate/nội dung trùng lặp nhiều chỗ (4 điểm check DNA) → drift | assessment §2 W9 | OPEN |
| F-08 | Chất lượng run của worker kém do handoff/prompt mỏng — phải làm spec task-run-quality | specs/2026-07-03-task-run-quality (PR #17) | OPEN một phần |
| F-09 | codebase-explorer bị bỏ qua golden path khi explore (2026-06-24) | bao_cao_loi.md | **RESOLVED** (ua-first 2026-06-24) — chỉ dùng làm bằng chứng lớp lỗi enforcement-prose |

---

## Phần A — Fix proposals (gap khớp failure, xếp theo đòn bẩy giảm dần)

### A-1. Ba rule `[CRITICAL]` còn "trên giấy" — cần hook hoặc hạ cấp marker [BP-12]
- **Gap**: R-Data-1 (PII, rules-exec.md:9), R-KL-1 (archive bắt buộc sau Apply, rules-knowledge.md:9), R-Tool-1 (db-explorer chỉ đọc, rules-tool.md:9) đều `[CRITICAL]` nhưng không khớp hook cơ học nào trong `.maika/hooks/`.
- **Failure khớp**: F-01, F-02 (chính pattern audit 2026-06-20 đã xác nhận).
- **Đề xuất**: mỗi rule chọn một trong hai — (a) thêm matcher vào write-gate/hook sẵn có (R-KL-1 khớp apply-gate mở rộng; R-Tool-1 khớp matcher lệnh DB write), hoặc (b) nếu không hook được, ghi rõ lý do ngay tại rule (rubric BP-12 cho phép) — hết trạng thái lửng.
- **Đòn bẩy**: cao (pattern gate đã có sẵn từ C-22b/C-23, chi phí thấp) — confidence: cao.

### A-2. Việc deterministic dặn bằng prose trong 7 skill + 8 workflow — script hóa [BP-07]
- **Gap**: spec-validator `ALGORITHM:` (line 107) — thuật toán AC-coverage chạy bằng prose; knowledge-curator "Xoá toàn bộ file trong active/ideation/" (line 122) — thao tác phá hủy không exact command/precondition máy đọc; author-dna-builder VALIDATE yaml (line 207); các bước `CHECK:` đầu approve-dna/approve-conventions/convention-scan/dna-scan; `check_ideation_expiry()` pseudo-code trong idea-to-task (line 207).
- **Failure khớp**: F-01 (gap #4 nêu đích danh knowledge-curator), F-02, và bài học Pha 3 driver ("code không bao giờ quên" — trách nhiệm trình tự thuộc code).
- **Đề xuất**: mở rộng pattern driver/gate: (1) `pre_conditions:` máy đọc cho 8/14 skill còn thiếu + reset script cho knowledge-curator (đóng gap #4); (2) validator script cho spec-validator AC-coverage; (3) các bước CHECK đầu workflow chuyển thành precondition trong tool sẵn có. Prune prose tương ứng cùng PR (R7 diff âm).
- **Đòn bẩy**: cao — confidence: cao.

### A-3. "Rule diet" cho khối bootstrap: 1103 dòng, trùng lặp, nội dung hẹp, marker lạm phát [BP-15][BP-10][BP-20][BP-13][BP-14]
- **Gap**: tổng nạp mỗi phiên 1103 dòng (đo bởi worker, khớp wc -l độc lập); meta-prompt lặp load-order của RULES.md (meta-prompt:105 vs RULES.md:45) và lặp flow-prohibition của rules-flow (meta-prompt:256 vs rules-flow:11); nội dung tình huống hẹp nằm trong bootstrap (R-Skill-1 skill schema chi tiết rules-knowledge:104; bảng tool/budget agent-memory rules-tool:80); mật độ marker cao (rules-flow 12 `[CRITICAL]`, rules-exec 11) làm mất phân biệt; teaching-moment decision-tree từng bước trong rules-guard:47.
- **Failure khớp**: F-05 (context tràn 2026-07-03 — càng nạp nhiều càng compact sớm càng mất rule), F-04, F-07, F-06.
- **Đề xuất**: một pruning pass có chủ đích: (1) khử 2 cặp trùng meta-prompt↔rules; (2) dời skill-schema và tool-guide hẹp sang skill/reference load on-demand; (3) hạ marker theo phép thử "bỏ đi có gây lỗi không" — mỗi `[CRITICAL]` giữ lại phải kèm why hoặc hook (nối với A-1). Đo trước/sau bằng line-count + quan sát compact.
- **Đòn bẩy**: cao (đánh thẳng F-05 đang chảy máu) — confidence: cao (BP-10 là `[phiên dịch]` nhưng BP-15/BP-20 trực tiếp).

### A-4. Gate nhận lời khai thay evidence — bịt lỗ compliance theater [BP-21]
- **Gap**: RULES.md không có gate nào yêu cầu evidence cụ thể (ABSENT); tdd.md hoàn thành bằng "chạy checklist" tự khai (line 50) không đòi output lệnh/kết quả đính kèm.
- **Failure khớp**: F-03 (đúng định nghĩa W2: "viết 'tôi đã check DNA' ≠ thật sự check DNA").
- **Đề xuất**: chuẩn hóa theo mẫu teaching-moment checkpoint (C-24 — "deterministic acknowledgment"): gate nào giữ lại phải đòi evidence dán được (test output, lệnh + kết quả), gate không đòi được evidence thì bỏ (đỡ tốn dòng).
- **Đòn bẩy**: vừa-cao — confidence: cao.

### A-5. Worker handoff thiếu 4 thành phần chuẩn [BP-18]
- **Gap**: dispatch prompt Pha 1 trong task.md:50 chỉ có "Đọc SKILL.md, thực thi với input" — thiếu output format + task boundaries trong cùng template (chuẩn Anthropic: objective, output format, tools/sources, boundaries).
- **Failure khớp**: F-08 (task-run-quality 2026-07-03 — chất lượng run kém vì handoff mỏng; spec đó fix Pha 3, chỗ này là mảnh Pha 1 còn lại).
- **Đề xuất**: bổ sung 4 thành phần vào template dispatch Pha 1 (như đã làm cho fresh-session prompt Pha 3).
- **Đòn bẩy**: vừa (sửa 1 template, ~15′) — confidence: cao.

### A-6. Không nhánh theo cỡ việc — củng cố UP5 bằng trích dẫn [BP-19]
- **Gap**: task.md và các workflow không có đường tắt tiny/standard/complex — mọi ticket đi đủ pipeline (worker xác nhận trên 9 workflow).
- **Failure khớp**: F-04 (W3 + "Pha 1 > 50.000 token").
- **Đề xuất**: không việc mới — audit này bổ sung căn cứ trích dẫn ("Scale effort to query complexity") cho **UP5 đã có trong TODOS** (Bậc 2, cần brainstorm/office-hours trước, sau P1.1).
- **Đòn bẩy**: cao nhưng bị chặn bởi P1.1 — confidence: vừa (BP-19 là `[phiên dịch]`).

### A-7. 14/14 skill không có eval/baseline — củng cố P1.1 + UP1 bằng trích dẫn [BP-09]
- **Gap**: worker xác nhận ABSENT trên toàn bộ 14 skill (không eval scenario, không baseline).
- **Failure khớp**: F-06 (W6 không outcome loop — không biết skill/rule nào đáng tiền).
- **Đề xuất**: không việc mới — chuẩn Anthropic ("Create evaluations BEFORE writing extensive documentation", "Establish baseline") xác nhận **P1.1 baseline-arm litmus đúng là linchpin Bậc 0** và UP1 là bước kế tiếp đúng. Ưu tiên hiện tại trong TODOS giữ nguyên.
- **Đòn bẩy**: cao nhất về giá trị nhưng đã được track — confidence: cao.

---

## Phần B — Watchlist (có trích dẫn, chưa có failure quan sát)

### B-1. Format artifact phức tạp thiếu canonical example [BP-22]
- **Gap**: CONTRACT_DAG/TASK_HANDOFF/KNOWLEDGE_PACK (task.md), author-dna/conventions draft (5 skill + 4 workflow), checkpoint formats (rules) — chỉ mô tả field, không example đầy đủ.
- **Kích hoạt**: nếu quan sát thấy artifact sai schema (vd CONTRACT_DAG làm driver Pha 3 parse fail, REQUIREMENT thiếu section) → nâng lên fix, ưu tiên artifact máy đọc trước.

### B-2. Workflow phụ: trình tự cố định bằng prose, thiếu checklist copy được [BP-17][BP-16]
- **Gap**: approve-dna/approve-conventions (rename/backup sequence), convention-scan/dna-scan (chuỗi CHECK), index-source (poll 15s), tdd.md (COPY template) — prose thay vì code path; đa số không có checklist + validator loop.
- **Kích hoạt**: nếu quan sát agent bỏ bước/sai trình tự trong các workflow phụ này (như đã từng thấy ở task.md Pha 3 trước driver) → áp pattern driver, làm theo cụm.

### B-3. Skill dạy điều model đã biết [BP-05]
- **Gap**: document-writer §"Nguyên tắc viết tài liệu kỹ thuật" (line 187), infra-tdd giải thích giá trị format (line 254), openspec-explore dạy stance hội thoại (line 63).
- **Kích hoạt**: khi có đo token per-skill-load (sau UP1) cho thấy các section này chiếm đáng kể, hoặc quan sát agent lệch vì noise → prune.

### B-4. Bundled asset thiếu hướng dẫn khi nào đọc [BP-04]
- **Gap**: infra-tdd liệt kê `assets/ADR_TEMPLATE.md` (line 451) không kèm điều kiện đọc/chạy.
- **Kích hoạt**: quan sát agent không dùng hoặc dùng sai template khi viết ADR → thêm câu điều kiện đọc (fix 1 dòng).

### B-5. Tool reference mơ hồ trong spec-validator [BP-08]
- **Gap**: "có compile/không có syntax error? (nếu có tool hỗ trợ)" (line 173) — không nói tool nào, chạy hay đọc.
- **Kích hoạt**: quan sát agent lúng túng/chọn sai tool ở bước verify → chỉ định tool qua `{{ tools.* }}`.

### B-6. infra-tdd ép protocol cứng cho việc viết doc [BP-06][BP-13]
- **Gap**: "KHÔNG ĐƯỢC viết bất kỳ section TDD nào khi chưa chạy knowledge tools" (line 81) — high-freedom task bị ép low-freedom.
- **Kích hoạt**: quan sát TDD doc chất lượng kém/chậm vì bị chặn bởi protocol, hoặc agent phớt lờ marker này → nới về heuristic + why.

---

## Phần C — Đạt chuẩn (bằng chứng đã audit, không phải bỏ sót)

- **BP-01** description = what + when: **14/14 skill pass** — mẫu description "Dùng khi… KHÔNG dùng cho…" (vd requirement-analyst) đúng chuẩn trigger + anti-trigger.
- **BP-02** when-to-use ở description: 14/14 pass.
- **BP-03** ≤500 dòng: 14/14 pass (lưu ý: infra-tdd >451 dòng — vùng cảnh báo 400–500 của rubric, theo dõi khi mở rộng).
- **BP-11** không rule self-evident: 6/6 rule file pass — rule Maika sinh từ incident thật, không khẩu hiệu (khớp S5 assessment).
- **BP-06** degrees of freedom: 12/14 skill pass (2 fail đã nêu ở A-2/B-6).
- **BP-08** execution intent: 13/14 pass.
- **BP-13** với skill: 13/14 pass (marker inflation là vấn đề của rule files, không phải skills).
- **BP-14/BP-16/BP-17/BP-18/BP-21** pass ở phần lớn file còn lại không nêu trong A/B (chi tiết trong evidence).

## Kết luận

Điểm mạnh được xác nhận bằng chuẩn ngoài: lớp **skill description/trigger/kích thước đã đúng chuẩn Anthropic** — đầu tư SP2 skill-standardization trả quả. Cụm gap lớn nhất hội tụ về đúng một chủ đề mà framework đã tự chẩn đoán từ 2026-06-16: **enforcement và trình tự phải là code, prose phải teo lại** (A-1, A-2, A-3, A-4) — audit này biến chẩn đoán đó thành danh sách việc cụ thể, mỗi việc có trích dẫn chuẩn + failure thật làm căn cứ. Hai mục giá trị cao nhất (eval-first A-7, effort-scaling A-6) đã nằm đúng chỗ trong TODOS — không đổi ưu tiên, chỉ thêm căn cứ.
