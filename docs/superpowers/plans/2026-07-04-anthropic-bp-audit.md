# Audit "Maika vs Best Practices Anthropic" — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ra được rubric citation-grounded + báo cáo audit (fix proposals xếp hạng / watchlist / đạt chuẩn) đối chiếu 14 skill + 6 rule file + meta-prompt + workflows của Maika với best practices Anthropic.

**Architecture:** 3 lớp theo spec ([2026-07-04-anthropic-bp-audit-design.md](../specs/2026-07-04-anthropic-bp-audit-design.md)): orchestrator fetch corpus & chưng cất rubric (reasoning) → worker codex/agy quét framework thu evidence thô (token-nặng, chạy detach) → orchestrator verdict lọc 2 tầng đối chiếu kho failure đã quan sát.

**Tech Stack:** WebFetch (corpus), codex exec / agy -p (worker sweep, detach nohup), bash/grep (verification), markdown (deliverables).

## Global Constraints

- **Citation cứng** (spec §4): mọi tiêu chí rubric = quote nguyên văn (tiếng Anh gốc) + URL + ngày fetch; không nguồn → loại. Mọi finding trỏ về BP-ID.
- **Không sửa** bất kỳ skill/rule/meta-prompt/workflow nào trong vòng audit (spec §10) — audit tách khỏi thực thi sửa.
- **Tầng 2 corpus** (OpenAI v.v.) chỉ dùng khi Anthropic im lặng về chủ đề; finding tầng 2 ghi rõ tầng nguồn (spec §3).
- **Rubric 15–25 tiêu chí**, 100% có "Cách kiểm" trên file, đánh dấu `[trực tiếp]`/`[phiên dịch]` (spec §5, §7).
- **Spot-check ≥3 evidence/batch** trước khi tin batch (spec §6).
- **Ngôn ngữ**: docs tiếng Việt, identifier + quote tiếng Anh giữ nguyên (quy tắc user).
- **Artifact tạm** (fetch notes, worker prompt, evidence, log) vào `.superpowers/bp-audit/` — gitignored, KHÔNG commit.
- **Branch**: làm trên `docs/anthropic-bp-audit-design` (đã có, chứa spec).
- **Worker detach**: run dài dùng `nohup … > log 2>&1 &`, không dùng background Bash của harness (trần 10 phút từng giết run — bài học đã ghi nhớ).

---

### Task 1: Fetch corpus tầng 1 → notes có quote

**Files:**
- Create: `.superpowers/bp-audit/sources/building-effective-agents.md`
- Create: `.superpowers/bp-audit/sources/effective-context-engineering.md`
- Create: `.superpowers/bp-audit/sources/writing-tools-for-agents.md`
- Create: `.superpowers/bp-audit/sources/claude-code-best-practices.md`
- Create: `.superpowers/bp-audit/sources/agent-skills.md`
- Create: `.superpowers/bp-audit/sources/multi-agent-research-system.md`
- Create: `.superpowers/bp-audit/sources/skill-authoring-docs.md`

**Interfaces:**
- Produces: mỗi file notes có header `URL:`, `Fetch: 2026-07-04` (ngày chạy thật), và ≥5 quote nguyên văn dạng blockquote `> "..."` kèm chủ đề — Task 2 chỉ được lấy quote từ các file này.

- [ ] **Step 1: Tạo thư mục làm việc**

```bash
mkdir -p /home/zane/Desktop/Maika/.superpowers/bp-audit/sources
```

- [ ] **Step 2: Fetch 6 bài engineering Anthropic** (tool WebFetch, từng URL)

| URL | File notes |
| --- | --- |
| <https://www.anthropic.com/engineering/building-effective-agents> | building-effective-agents.md |
| <https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents> | effective-context-engineering.md |
| <https://www.anthropic.com/engineering/writing-tools-for-agents> | writing-tools-for-agents.md |
| <https://www.anthropic.com/engineering/claude-code-best-practices> | claude-code-best-practices.md |
| <https://www.anthropic.com/engineering/equipping-agents-for-the-real-world-with-agent-skills> | agent-skills.md |
| <https://www.anthropic.com/engineering/built-multi-agent-research-system> | multi-agent-research-system.md |

Prompt WebFetch cho mỗi URL: *"Extract verbatim (word-for-word, in English) every principle, recommendation, or rule of thumb about designing skills, rules/instructions, prompts, workflows, tools, or context management. For each: the exact quote + one line stating the topic. Do not paraphrase."*

Ghi mỗi kết quả vào file notes tương ứng, format:

```markdown
URL: <url>
Fetch: <YYYY-MM-DD>

## Quotes
> "exact quote 1"
— topic: <chủ đề>
```

Nếu URL chết/redirect: ghi vào file notes `STATUS: dead/redirect → <url mới nếu có>`, fetch URL mới, và ghi chú vào bảng corpus của rubric ở Task 2.

- [ ] **Step 3: Fetch chuẩn kỹ thuật skill authoring** (docs + repo)

WebFetch các URL sau, gộp vào `skill-authoring-docs.md` (cùng format Step 2, mỗi nguồn một section `## Source: <url>`):

- <https://docs.claude.com/en/docs/agents-and-tools/agent-skills/best-practices> (nếu 404: tìm đường dẫn hiện hành qua <https://docs.claude.com/en/docs/agents-and-tools/agent-skills/overview>)
- <https://raw.githubusercontent.com/anthropics/skills/main/README.md>
- <https://raw.githubusercontent.com/anthropics/skills/main/skill-creator/SKILL.md> (nếu 404: duyệt cây repo tìm vị trí skill-creator hiện hành)

- [ ] **Step 4: Verify coverage notes**

```bash
cd /home/zane/Desktop/Maika
ls .superpowers/bp-audit/sources/ | wc -l        # Expected: 7
grep -L "^Fetch: " .superpowers/bp-audit/sources/*.md   # Expected: rỗng (file nào thiếu ngày fetch sẽ hiện tên)
for f in .superpowers/bp-audit/sources/*.md; do echo "$f: $(grep -c '^> ' "$f") quotes"; done
# Expected: mỗi file ≥5 quotes; file nào <5 → fetch lại với prompt cụ thể hơn
```

Không commit (thư mục gitignored).

---

### Task 2: Chưng cất rubric citation-grounded

**Files:**
- Create: `docs/superpowers/specs/2026-07-04-anthropic-bp-rubric.md`

**Interfaces:**
- Consumes: quotes từ `.superpowers/bp-audit/sources/*.md` (Task 1) — KHÔNG dùng quote từ trí nhớ.
- Produces: 15–25 tiêu chí `### BP-NN — <tên>`, mỗi tiêu chí đủ 4 trường (`Phát biểu kiểm chứng được`, `Nguồn`, `Cách kiểm`, `Applies-to`) — Task 4 nhúng nguyên văn rubric vào prompt worker; Task 6 trỏ finding về BP-ID.

- [ ] **Step 1: Viết rubric**

Cấu trúc file:

```markdown
# Rubric Best-Practice — Maika audit 2026-07-04

> Nguồn quote: fetch 2026-07-04 (xem bảng corpus). Quy tắc: không nguồn = không tiêu chí (spec §4).

## Bảng corpus
| Nguồn | URL | Fetch | Tầng |
| --- | --- | --- | --- |
(liệt kê đủ các nguồn đã fetch ở Task 1, kèm ghi chú URL chết/redirect nếu có)

## Tiêu chí — Skill
### BP-01 — <tên ngắn>
- **Phát biểu kiểm chứng được**: <điều kiện đạt/trượt đọc được trên file, không mơ hồ>
- **Nguồn**: "<quote nguyên văn>" — <URL>, fetch <ngày>. `[trực tiếp]` | `[phiên dịch: <bước suy diễn 1 câu>]`
- **Cách kiểm**: <đọc gì / grep gì / đạt nếu gì>
- **Applies-to**: skill | rule | workflow | meta-prompt (một hoặc nhiều)

## Tiêu chí — Rule
...
## Tiêu chí — Workflow & Meta-prompt
...
## Phụ lục — Nguyên tắc bị loại vì không có nguồn
(liệt kê để chứng minh "đã cân nhắc, không phải bỏ sót")
```

Ràng buộc khi viết (từ spec §5): phát biểu kiểm chứng được trên file; nhóm theo applies-to; >30 tiêu chí = đang chép bài báo, phải chưng cất lại.

Tầng 2 (spec §3): nếu trong lúc viết thấy chủ đề quan trọng mà cả 7 nguồn tầng 1 im lặng → WebFetch nguồn tầng 2 (vd OpenAI *A Practical Guide to Building Agents*), lưu notes vào `.superpowers/bp-audit/sources/tier2-<slug>.md` cùng format Task 1, và ghi rõ `Tầng: 2` trong bảng corpus + trong dòng **Nguồn** của tiêu chí đó.

- [ ] **Step 2: Verify cấu trúc rubric bằng lệnh**

```bash
cd /home/zane/Desktop/Maika
R=docs/superpowers/specs/2026-07-04-anthropic-bp-rubric.md
N=$(grep -c '^### BP-' $R); echo "criteria: $N"          # Expected: 15 ≤ N ≤ 25
test $N -eq $(grep -c '\*\*Nguồn\*\*' $R) && echo OK-nguon      # Expected: OK-nguon
test $N -eq $(grep -c '\*\*Cách kiểm\*\*' $R) && echo OK-kiem   # Expected: OK-kiem
test $N -eq $(grep -c '\*\*Applies-to\*\*' $R) && echo OK-applies # Expected: OK-applies
test $N -eq $(grep -cE '\[trực tiếp\]|\[phiên dịch' $R) && echo OK-mark # Expected: OK-mark
grep -c 'fetch 2026' $R    # Expected: ≥ N (mỗi Nguồn có ngày fetch)
```

Lệnh nào trượt → sửa rubric rồi chạy lại đủ bộ.

- [ ] **Step 3: Commit**

```bash
git add docs/superpowers/specs/2026-07-04-anthropic-bp-rubric.md
git commit -m "docs(audit): rubric best-practice citation-grounded từ corpus Anthropic"
```

---

### Task 3: Citation self-check rubric

**Files:**
- Modify: `docs/superpowers/specs/2026-07-04-anthropic-bp-rubric.md` (chỉ khi phát hiện lỗi)

**Interfaces:**
- Consumes: rubric (Task 2) + notes (Task 1).
- Produces: rubric đã xác minh — mọi quote truy được về notes fetch; đây là điều kiện để Task 4 được phép chạy.

- [ ] **Step 1: Đối chiếu từng quote với notes**

Với từng dòng `**Nguồn**` trong rubric, lấy ~6 từ đầu của quote và grep trong notes:

```bash
cd /home/zane/Desktop/Maika
grep -oP '(?<=\*\*Nguồn\*\*: ")[^"]{20,60}' docs/superpowers/specs/2026-07-04-anthropic-bp-rubric.md \
| while IFS= read -r q; do
    grep -rqF "${q:0:40}" .superpowers/bp-audit/sources/ && echo "OK  | ${q:0:50}" || echo "MISS| ${q:0:50}"
  done
# Expected: toàn bộ OK. Dòng MISS = quote không có trong notes → quote bịa hoặc notes thiếu:
# fetch lại nguồn để xác minh; không xác minh được → XÓA tiêu chí đó (quy tắc cứng spec §4).
```

- [ ] **Step 2: Kiểm phát biểu kiểm chứng được** (đọc tay, nhanh)

Đọc lại từng `Phát biểu kiểm chứng được`: nếu không trả lời được "file nào đạt, file nào trượt, dựa vào dòng nào" → viết lại hoặc loại. Cấm giữ tiêu chí kiểu "nên rõ ràng".

- [ ] **Step 3: Commit nếu có sửa**

```bash
git add docs/superpowers/specs/2026-07-04-anthropic-bp-rubric.md
git commit -m "docs(audit): self-check citation rubric — sửa/loại tiêu chí không truy được nguồn"
# Nếu Step 1-2 sạch không sửa gì: bỏ qua, không commit rỗng
```

---

### Task 4: Worker sweep — 2 batch detach

**Files:**
- Create: `.superpowers/bp-audit/sweep-prompt-A.md` (batch A: 14 SKILL.md)
- Create: `.superpowers/bp-audit/sweep-prompt-B.md` (batch B: 6 rule file + meta-prompt.md + workflows/)

**Interfaces:**
- Consumes: rubric đã self-check (Task 3).
- Produces: `.superpowers/bp-audit/evidence-A.md`, `.superpowers/bp-audit/evidence-B.md` — evidence thô format cố định (dưới), Task 5 spot-check, Task 6 tiêu thụ.

- [ ] **Step 1: Viết prompt worker**

Nội dung `sweep-prompt-A.md` (B tương tự, đổi danh sách file đích và tên file output):

```markdown
Bạn là worker thu evidence cho audit. KHÔNG kết luận, KHÔNG đề xuất sửa, KHÔNG sửa file nào.

Rubric: đọc docs/superpowers/specs/2026-07-04-anthropic-bp-rubric.md.
File đích (batch A): toàn bộ .maika/skills/*/SKILL.md (14 file).

Với TỪNG tiêu chí BP có Applies-to chứa "skill" × TỪNG file đích, ghi một block:

## <BP-ID> | <đường dẫn file>
- status: pass | fail | n/a
- evidence: "<quote nguyên văn dòng liên quan>" (line <số dòng>)
- note: <tối đa 1 câu nếu cần>

Quy tắc: status là nhận định SƠ BỘ; evidence bắt buộc quote đúng dòng thật (sẽ bị spot-check,
sai quote/line = loại cả batch). n/a chỉ khi tiêu chí không áp được cho file đó, phải ghi lý do ở note.

Ghi TOÀN BỘ output vào file .superpowers/bp-audit/evidence-A.md (ghi đè nếu có).
```

Batch B: file đích = `.maika/rules/RULES.md`, `.maika/rules/rules-*.md` (5 file), `.maika/meta-prompt.md`, toàn bộ `.maika/workflows/`; lọc BP theo Applies-to chứa "rule", "workflow" hoặc "meta-prompt"; output `evidence-B.md`.

- [ ] **Step 2: Dispatch detach (codex chính, agy fallback)**

```bash
cd /home/zane/Desktop/Maika
nohup codex exec "$(cat .superpowers/bp-audit/sweep-prompt-A.md)" > .superpowers/bp-audit/sweep-A.log 2>&1 &
nohup codex exec "$(cat .superpowers/bp-audit/sweep-prompt-B.md)" > .superpowers/bp-audit/sweep-B.log 2>&1 &
```

Nếu codex báo quota/lỗi trong log → fallback: `nohup agy -p "$(cat .superpowers/bp-audit/sweep-prompt-A.md)" > .superpowers/bp-audit/sweep-A.log 2>&1 &` (agy tự xoay account qua hagy).

- [ ] **Step 3: Chờ và verify coverage evidence**

Poll bằng `tail -5 .superpowers/bp-audit/sweep-*.log` (không dùng foreground sleep dài). Khi cả hai xong:

```bash
cd /home/zane/Desktop/Maika
grep -c '^## BP-' .superpowers/bp-audit/evidence-A.md   # Expected: ≈ (số BP applies-to skill) × 14
grep -c '^## BP-' .superpowers/bp-audit/evidence-B.md   # Expected: ≈ (số BP rule/workflow/meta) × (7 + số workflow file)
# Coverage per-file: mỗi file đích xuất hiện ≥1 lần
for f in .maika/skills/*/SKILL.md; do grep -q "$f" .superpowers/bp-audit/evidence-A.md || echo "MISSING $f"; done
# Expected: không có MISSING. Thiếu file nào → re-dispatch batch với prompt nhấn mạnh file thiếu.
```

Không commit (gitignored).

---

### Task 5: Spot-check evidence

**Files:**
- Create: `.superpowers/bp-audit/spotcheck.md`

**Interfaces:**
- Consumes: evidence-A/B (Task 4).
- Produces: verdict PASS/FAIL per batch trong `spotcheck.md` — điều kiện Task 6 được phép tiêu thụ evidence (spec §6: ≥3 evidence/batch).

- [ ] **Step 1: Chọn và kiểm 3 evidence/batch**

Mỗi batch chọn 3 block đa dạng (khác BP, khác file, ưu tiên status=fail vì fail sẽ thành finding). Với mỗi block: mở file gốc tại line ghi trong evidence, so quote.

```bash
# ví dụ kiểm 1 block: evidence ghi 'line 42' của .maika/skills/db-explorer/SKILL.md
sed -n '40,44p' .maika/skills/db-explorer/SKILL.md   # quote phải khớp dòng thật
```

- [ ] **Step 2: Ghi kết quả + xử lý fail**

`spotcheck.md`: bảng 6 dòng (batch, BP-ID, file, line, khớp?/lệch gì), chốt `BATCH A: PASS|FAIL`, `BATCH B: PASS|FAIL`.

Batch FAIL (≥1/3 sai quote hoặc sai line) → quay lại Task 4 Step 2 re-dispatch batch đó với prompt bổ sung lỗi cụ thể đã bắt được; spot-check lại 3 block MỚI. Tối đa 2 vòng re-dispatch; vẫn fail → orchestrator tự quét phần batch đó (chấp nhận tốn context, ghi chú vào báo cáo).

---

### Task 6: Verdict 2 tầng + báo cáo

**Files:**
- Create: `docs/superpowers/specs/2026-07-04-anthropic-bp-audit-report.md`

**Interfaces:**
- Consumes: evidence-A/B đã spot-check PASS (Task 5); rubric (Task 3); kho failure: `bao_cao_loi.md`, `TODOS.md` §"Enforcement hardening", `Maika-v3-assessment.md`, observed-failures trong specs gần đây (vd `2026-07-04-phase3-driver-…` §1).
- Produces: báo cáo 3 phần A/B/C — Task 7 chép phần A vào TODOS.md.

- [ ] **Step 1: Đọc kho failure, lập danh mục failure đã quan sát**

Mỗi failure một dòng: `F-nn | mô tả 1 câu | nguồn (file + section)`. Đặt ở đầu báo cáo làm bảng đối chiếu.

- [ ] **Step 2: Verdict từng gap**

Với mỗi BP có ≥1 evidence fail: khớp được F-nn → **phần A (fix proposal)**; không khớp → **phần B (watchlist)**. BP toàn pass → **phần C (đạt chuẩn)**, một dòng.

Format phần A (mỗi finding):

```markdown
### A-1. <tên gap> [BP-xx]
- **Gap**: <1-2 câu, evidence trích từ evidence file>
- **Failure khớp**: F-nn (<nguồn>)
- **Đề xuất**: <hướng sửa 1-2 câu — KHÔNG sửa trong vòng audit này>
- **Đòn bẩy**: <cao|vừa|thấp> (failure nặng × chi phí sửa thấp) — confidence: <cao|vừa (phiên dịch)>
```

Format phần B: như A nhưng thay `Failure khớp` bằng `**Kích hoạt**: nếu quan sát thấy <X> → nâng lên fix`.

Ràng buộc (spec §7-8): finding từ tiêu chí `[phiên dịch]` hạ confidence một bậc; xếp phần A theo đòn bẩy giảm dần.

- [ ] **Step 3: Verify báo cáo bằng lệnh**

```bash
cd /home/zane/Desktop/Maika
RP=docs/superpowers/specs/2026-07-04-anthropic-bp-audit-report.md
test $(grep -c '^### A-' $RP) -eq $(grep -c '\*\*Failure khớp\*\*' $RP) && echo OK-A   # Expected: OK-A
test $(grep -c '^### B-' $RP) -eq $(grep -c '\*\*Kích hoạt\*\*' $RP) && echo OK-B      # Expected: OK-B
grep -cE '^### [AB]-[0-9]+\..*\[BP-' $RP  # Expected: = tổng số finding A+B (mọi finding có BP-ID)
```

- [ ] **Step 4: Commit**

```bash
git add docs/superpowers/specs/2026-07-04-anthropic-bp-audit-report.md
git commit -m "docs(audit): báo cáo audit Maika vs best-practice Anthropic — fix proposals + watchlist"
```

---

### Task 7: TODOS.md + PR

**Files:**
- Modify: `TODOS.md` (thêm section mới, không sửa entry cũ)

**Interfaces:**
- Consumes: phần A của báo cáo (Task 6).

- [ ] **Step 1: Thêm section vào TODOS.md**

Sau section "Enforcement hardening", thêm:

```markdown
## Best-practice gaps (audit 2026-07-04)

> Track riêng. Nguồn: docs/superpowers/specs/2026-07-04-anthropic-bp-audit-report.md
> (rubric: 2026-07-04-anthropic-bp-rubric.md). Chỉ liệt kê phần A (đã khớp observed failure);
> watchlist xem phần B của báo cáo.

- **BP-A1 — <tên>** ⬜ TODO — <What 1 câu>. <Why: failure F-nn>. Effort: <ước lượng>. [BP-xx]
(một dòng mỗi fix proposal, giữ đúng giọng các entry hiện có)
```

- [ ] **Step 2: Commit, push, PR**

```bash
cd /home/zane/Desktop/Maika
git add TODOS.md
git commit -m "docs(todos): nạp fix proposals từ audit best-practice 2026-07-04"
git push -u origin docs/anthropic-bp-audit-design
gh pr create --title "docs: audit Maika vs best-practice Anthropic (rubric + report + TODOS)" \
  --body "$(cat <<'EOF'
## Summary
- Spec + rubric citation-grounded (quote nguyên văn + URL + ngày fetch từ corpus Anthropic)
- Báo cáo audit: fix proposals khớp observed failure (phần A) / watchlist (phần B) / đạt chuẩn (phần C)
- TODOS.md nhận phần A. Không sửa skill/rule/meta-prompt/workflow nào trong PR này (audit tách khỏi sửa).

🤖 Generated with [Claude Code](https://claude.com/claude-code)
EOF
)"
```

Expected: PR mở thành công, diff chỉ gồm 4 file docs (spec, rubric, report, plan) + TODOS.md.
