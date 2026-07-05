# Rubric Best-Practice — Maika audit 2026-07-04

> Nguồn quote: fetch 2026-07-04 (bảng corpus dưới). Quy tắc cứng: không nguồn = không tiêu chí (spec §4, [2026-07-04-anthropic-bp-audit-design.md](2026-07-04-anthropic-bp-audit-design.md)).
> Marker: `[trực tiếp]` = áp nguyên văn; `[phiên dịch]` = có bước suy diễn (ghi kèm), finding hạ một bậc confidence.

## Bảng corpus

| Nguồn | URL | Fetch | Tầng |
| --- | --- | --- | --- |
| Building Effective Agents | <https://www.anthropic.com/engineering/building-effective-agents> | 2026-07-04 | 1 |
| Effective Context Engineering for AI Agents | <https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents> | 2026-07-04 | 1 |
| Writing Effective Tools for Agents | <https://www.anthropic.com/engineering/writing-tools-for-agents> | 2026-07-04 | 1 |
| Claude Code Best Practices | <https://code.claude.com/docs/en/best-practices> (redirect 308 từ anthropic.com/engineering/claude-code-best-practices) | 2026-07-04 | 1 |
| Equipping Agents for the Real World with Agent Skills | <https://www.anthropic.com/engineering/equipping-agents-for-the-real-world-with-agent-skills> | 2026-07-04 | 1 |
| How We Built Our Multi-Agent Research System | <https://www.anthropic.com/engineering/built-multi-agent-research-system> | 2026-07-04 | 1 |
| Skill Authoring Best Practices (docs) | <https://platform.claude.com/docs/en/agents-and-tools/agent-skills/best-practices> (redirect 302 từ docs.claude.com) | 2026-07-04 | 1 |
| anthropics/skills — README + skill-creator | <https://github.com/anthropics/skills> (skill-creator dời về `skills/skill-creator/`) | 2026-07-04 | 1 |

Tầng 2: chưa cần dùng — mọi chủ đề trong rubric đều có nguồn Anthropic.

---

## Tiêu chí — Skill

### BP-01 — Description = what + when (trigger cụ thể)
- **Phát biểu kiểm chứng được**: frontmatter `description` của mỗi SKILL.md phải nêu cả chức năng LẪN điều kiện kích hoạt cụ thể (từ khóa/ngữ cảnh "dùng khi…"); mô tả chức năng suông = trượt.
- **Nguồn**: "Be specific and include key terms. Include both what the Skill does and specific triggers/contexts for when to use it." — <https://platform.claude.com/docs/en/agents-and-tools/agent-skills/best-practices>, fetch 2026-07-04. `[trực tiếp]`
- **Cách kiểm**: đọc frontmatter 14 SKILL.md; đạt nếu description chứa điều kiện kích hoạt (và tốt hơn: anti-trigger "KHÔNG dùng cho…").
- **Applies-to**: skill.

### BP-02 — Toàn bộ when-to-use nằm ở description, không nằm trong body
- **Phát biểu kiểm chứng được**: thông tin "khi nào dùng skill" không được chỉ xuất hiện trong body (nơi chỉ được đọc SAU khi đã trigger) mà thiếu ở description.
- **Nguồn**: "All 'when to use' info goes here, not in the body." — <https://github.com/anthropics/skills> (skills/skill-creator/SKILL.md), fetch 2026-07-04. `[trực tiếp]`
- **Cách kiểm**: tìm section "khi nào dùng"/trigger trong body 14 SKILL.md; nếu nội dung đó không phản ánh trong description = trượt.
- **Applies-to**: skill.

### BP-03 — SKILL.md ≤ 500 dòng
- **Phát biểu kiểm chứng được**: body mỗi SKILL.md dưới 500 dòng; chạm trần phải tách file phụ.
- **Nguồn**: "Keep SKILL.md body under 500 lines for optimal performance" — <https://platform.claude.com/docs/en/agents-and-tools/agent-skills/best-practices>, fetch 2026-07-04. `[trực tiếp]`
- **Cách kiểm**: `wc -l .maika/skills/*/SKILL.md`; >500 = trượt, 400–500 = cảnh báo.
- **Applies-to**: skill.

### BP-04 — Progressive disclosure: file phụ link 1 tầng + guidance khi nào đọc
- **Phát biểu kiểm chứng được**: skill có file phụ thì mọi file phụ link trực tiếp từ SKILL.md (không lồng 2 tầng) và kèm câu điều kiện khi nào đọc.
- **Nguồn**: "Keep references one level deep from SKILL.md. All reference files should link directly from SKILL.md to ensure Claude reads complete files when needed." — <https://platform.claude.com/docs/en/agents-and-tools/agent-skills/best-practices>, fetch 2026-07-04; "Reference files clearly from SKILL.md with guidance on when to read them" — skills/skill-creator, fetch 2026-07-04. `[trực tiếp]`
- **Cách kiểm**: `ls .maika/skills/*/` tìm file ngoài SKILL.md; mỗi file phụ phải được SKILL.md nhắc tên + điều kiện đọc; ref lồng qua file trung gian = trượt.
- **Applies-to**: skill.

### BP-05 — Không dạy điều model đã biết
- **Phát biểu kiểm chứng được**: SKILL.md không chứa đoạn giải thích khái niệm phổ quát (git là gì, REST là gì, vì sao test quan trọng…).
- **Nguồn**: "Default assumption: Claude is already very smart. Only add context Claude doesn't already have." — <https://platform.claude.com/docs/en/agents-and-tools/agent-skills/best-practices>, fetch 2026-07-04. `[trực tiếp]`
- **Cách kiểm**: đọc body 14 SKILL.md; flag đoạn giải thích kiến thức nền phổ quát không đặc thù Maika/project.
- **Applies-to**: skill.

### BP-06 — Degrees of freedom khớp độ fragile của thao tác
- **Phát biểu kiểm chứng được**: thao tác phá hủy/fragile (reset, archive, migration) phải low-freedom: lệnh chính xác + guardrail; việc nhiều đường đúng (khám phá, review) không được ép trình tự cứng.
- **Nguồn**: "Match the level of specificity to the task's fragility and variability." — <https://platform.claude.com/docs/en/agents-and-tools/agent-skills/best-practices>, fetch 2026-07-04. `[trực tiếp]`
- **Cách kiểm**: skill phá hủy (vd knowledge-curator reset `active/`) có exact command + precondition máy đọc được? skill khám phá (codebase-explorer…) có bị ép bước cứng vô lý?
- **Applies-to**: skill.

### BP-07 — Script cho việc deterministic, không dặn LLM làm việc máy
- **Phát biểu kiểm chứng được**: bước deterministic (validate schema, đếm, emit event đúng thứ tự, so khớp format) phải giao cho script kèm sẵn, không mô tả bằng prose để LLM tự làm.
- **Nguồn**: "Prefer scripts for deterministic operations: Write `validate_form.py` rather than asking Claude to generate validation code" — <https://platform.claude.com/docs/en/agents-and-tools/agent-skills/best-practices>, fetch 2026-07-04; "Beyond efficiency concerns, many applications require the deterministic reliability that only code can provide." — <https://www.anthropic.com/engineering/equipping-agents-for-the-real-world-with-agent-skills>, fetch 2026-07-04. `[trực tiếp]`
- **Cách kiểm**: flag đoạn SKILL.md/workflow dặn LLM thao tác trình tự script-hóa được mà không có script trong `.maika/tools/`.
- **Applies-to**: skill, workflow.

### BP-08 — Execution intent rõ: chạy script hay đọc tham khảo
- **Phát biểu kiểm chứng được**: mỗi lần SKILL.md nhắc script/tool phải rõ là *chạy* (Run/`python …`) hay *đọc tham khảo* (See/Read).
- **Nguồn**: "It should be clear whether Claude should run scripts directly or read them into context as reference." — <https://www.anthropic.com/engineering/equipping-agents-for-the-real-world-with-agent-skills>, fetch 2026-07-04. `[trực tiếp]`
- **Cách kiểm**: grep các ref tool/script trong 14 SKILL.md; ref không có động từ chỉ định = trượt.
- **Applies-to**: skill.

### BP-09 — Eval-first: có evaluation + baseline trước khi viết dài
- **Phát biểu kiểm chứng được**: mỗi skill (ít nhất các skill lõi) có kịch bản eval đo được và baseline không-skill; không có = trượt.
- **Nguồn**: "Create evaluations BEFORE writing extensive documentation. This ensures your Skill solves real problems rather than documenting imagined ones." và "Establish baseline: Measure Claude's performance without the Skill" — <https://platform.claude.com/docs/en/agents-and-tools/agent-skills/best-practices>, fetch 2026-07-04. `[trực tiếp]`
- **Cách kiểm**: tìm eval scenario/harness trong repo (grep "eval" trong `.maika/`, `cli/tests/`); đối chiếu từng skill.
- **Applies-to**: skill.

## Tiêu chí — Rule

### BP-10 — Nội dung nạp mỗi phiên chỉ chứa điều áp dụng rộng
- **Phát biểu kiểm chứng được**: rule file bootstrap bắt buộc chỉ chứa quy tắc dùng thường xuyên ở mọi phiên; knowledge/workflow tình huống hẹp phải chuyển sang skill load on-demand.
- **Nguồn**: "CLAUDE.md is loaded every session, so only include things that apply broadly. For domain knowledge or workflows that are only relevant sometimes, use skills instead. Claude loads them on demand without bloating every conversation." — <https://code.claude.com/docs/en/best-practices>, fetch 2026-07-04. `[phiên dịch: bộ RULES.md + rules-*.md nạp bắt buộc lúc bootstrap giữ đúng vai trò CLAUDE.md]`
- **Cách kiểm**: đọc 6 rule file; flag section chỉ dùng trong 1 tình huống/1 pha/1 skill cụ thể (ứng viên: skill schema chi tiết, hướng dẫn thao tác một tool).
- **Applies-to**: rule.

### BP-11 — Mỗi dòng rule qua phép thử "bỏ đi có gây lỗi không"
- **Phát biểu kiểm chứng được**: không có rule self-evident (điều agent vốn làm đúng) hoặc generic vô hành động ("cẩn thận", "code sạch").
- **Nguồn**: "Keep it concise. For each line, ask: 'Would removing this cause Claude to make mistakes?' If not, cut it. Bloated CLAUDE.md files cause Claude to ignore your actual instructions!" — <https://code.claude.com/docs/en/best-practices>, fetch 2026-07-04. `[phiên dịch: rule file Maika = CLAUDE.md]`
- **Cách kiểm**: đọc 48 rule heading; flag rule mô tả hành vi mặc định của model hoặc khẩu hiệu không kiểm chứng được.
- **Applies-to**: rule.

### BP-12 — Rule bị vi phạm lặp lại → hook cơ học, không thêm text
- **Phát biểu kiểm chứng được**: rule `[CRITICAL]` (bất khả xâm phạm) phải có enforcement cơ học (hook/gate) hoặc lý do ghi rõ vì sao không thể; `[CRITICAL]` thuần prose = trượt.
- **Nguồn**: "Unlike CLAUDE.md instructions which are advisory, hooks are deterministic and guarantee the action happens." và "Ruthlessly prune. If Claude already does something correctly without the instruction, delete it or convert it to a hook." — <https://code.claude.com/docs/en/best-practices>, fetch 2026-07-04. `[trực tiếp]`
- **Cách kiểm**: liệt kê rule `[CRITICAL]` trong 6 file; đối chiếu `.maika/hooks/` + write-gate; không khớp hook nào = trượt. (Nền: audit enforcement 2026-06-20 đã xác nhận phần lớn "trên giấy".)
- **Applies-to**: rule.

### BP-13 — Emphasis tiết kiệm; giải thích why thay vì chồng MUST
- **Phát biểu kiểm chứng được**: marker nhấn mạnh (`[CRITICAL]`, MUST, KHÔNG ĐƯỢC) dùng chọn lọc và đi kèm lý do; mật độ marker cao đến mức mất phân biệt = trượt.
- **Nguồn**: "Try to explain to the model why things are important in lieu of heavy-handed musty MUSTs." — <https://github.com/anthropics/skills> (skills/skill-creator/SKILL.md), fetch 2026-07-04; "You can tune instructions by adding emphasis (e.g., 'IMPORTANT' or 'YOU MUST') to improve adherence." — <https://code.claude.com/docs/en/best-practices>, fetch 2026-07-04. `[trực tiếp]`
- **Cách kiểm**: đếm marker per rule file; đối chiếu tỉ lệ rule có kèm giải thích why.
- **Applies-to**: rule, skill.

### BP-14 — Altitude đúng: heuristic, không micro-script việc semantic
- **Phát biểu kiểm chứng được**: rule phát biểu ở tầng heuristic dẫn hướng; kịch bản từng-bước cứng cho việc có nhiều đường đúng = trượt (ngược lại, trình tự thật sự cố định thuộc BP-17).
- **Nguồn**: "specific enough to guide behavior effectively, yet flexible enough to provide the model with strong heuristics to guide behavior." — <https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents>, fetch 2026-07-04. `[trực tiếp]`
- **Cách kiểm**: flag rule dạng script hành vi chi li cho việc semantic (hiểu đề, review, đặt tên).
- **Applies-to**: rule, meta-prompt.

### BP-15 — Footprint bootstrap = tập tối thiểu high-signal
- **Phát biểu kiểm chứng được**: tổng nội dung nạp bắt buộc mỗi phiên (6 rule file + meta-prompt + entry point) không chứa trùng lặp giữa các file và không vượt quá mức "tối thiểu đủ" cho hành vi mong đợi.
- **Nguồn**: "good context engineering means finding the smallest possible set of high-signal tokens that maximize the likelihood of some desired outcome." — <https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents>, fetch 2026-07-04; "you should be striving for the minimal set of information that fully outlines your expected behavior." — cùng bài, fetch 2026-07-04. `[trực tiếp]`
- **Cách kiểm**: đo `wc -l` tổng khối bootstrap (hiện ~1100 dòng); liệt kê đoạn trùng nội dung giữa rules/meta-prompt/workflow.
- **Applies-to**: rule, meta-prompt.

## Tiêu chí — Workflow

### BP-16 — Workflow phức tạp có checklist copy được + validator loop
- **Phát biểu kiểm chứng được**: workflow nhiều bước phải có checklist agent chép được vào response + bước validate lặp (validator → fix → repeat).
- **Nguồn**: "Break complex operations into clear, sequential steps. For particularly complex workflows, provide a checklist that Claude can copy into its response and check off as it progresses." và "Common pattern: Run validator → fix errors → repeat. This pattern greatly improves output quality." — <https://platform.claude.com/docs/en/agents-and-tools/agent-skills/best-practices>, fetch 2026-07-04. `[trực tiếp]`
- **Cách kiểm**: 9 file `.maika/workflows/`; workflow ≥5 bước không checklist hoặc không có bước validate = trượt.
- **Applies-to**: workflow.

### BP-17 — Trình tự cố định chạy bằng predefined code path
- **Phát biểu kiểm chứng được**: đoạn workflow có thứ tự chốt sẵn (không cần phán đoán semantic) phải được code/driver cầm, không phải prose dặn LLM.
- **Nguồn**: "Workflows are systems where LLMs and tools are orchestrated through predefined code paths." và "Workflows offer predictability and consistency for well-defined tasks, whereas agents are the better option when flexibility and model-driven decision-making are needed at scale." — <https://www.anthropic.com/engineering/building-effective-agents>, fetch 2026-07-04. `[trực tiếp]`
- **Cách kiểm**: flag khối text trong workflows/ dặn LLM trình tự cứng script-hóa được (trừ phần Pha 3 driver 2026-07-04 đã code-hóa).
- **Applies-to**: workflow.

### BP-18 — Handoff subagent/worker đủ 4 thành phần
- **Phát biểu kiểm chứng được**: mỗi template/prompt giao việc cho worker phải đủ: objective, output format, guidance tool/source, task boundaries.
- **Nguồn**: "Each subagent needs an objective, an output format, guidance on the tools and sources to use, and clear task boundaries." — <https://www.anthropic.com/engineering/built-multi-agent-research-system>, fetch 2026-07-04. `[trực tiếp]`
- **Cách kiểm**: TASK_HANDOFF template + dispatch prompt (worker_command/fresh-session) đối chiếu đủ 4 mục; thiếu mục nào ghi rõ.
- **Applies-to**: workflow.

### BP-19 — Scale effort theo độ phức tạp task
- **Phát biểu kiểm chứng được**: pipeline phải có nhánh theo cỡ việc (tiny/standard/complex); ép full pipeline cho mọi cỡ = trượt.
- **Nguồn**: "Scale effort to query complexity." — <https://www.anthropic.com/engineering/built-multi-agent-research-system>, fetch 2026-07-04. `[phiên dịch: "query complexity" của hệ research ⇒ cỡ ticket của pipeline 5-pha]`
- **Cách kiểm**: đọc `task.md` + workflows; có đường tắt cho việc nhỏ không, hay mọi ticket đi đủ 5 pha?
- **Applies-to**: workflow.

## Tiêu chí — Meta-prompt & chung

### BP-20 — Meta-prompt không trùng lặp với rules/skills đã nạp
- **Phát biểu kiểm chứng được**: nội dung meta-prompt không lặp lại điều đã có trong rule file hoặc SKILL.md (mỗi fact một chỗ ở).
- **Nguồn**: "you should be striving for the minimal set of information that fully outlines your expected behavior." — <https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents>, fetch 2026-07-04. `[trực tiếp]`
- **Cách kiểm**: so meta-prompt.md (373 dòng) với 6 rule file; liệt kê đoạn trùng ngữ nghĩa.
- **Applies-to**: meta-prompt.

### BP-21 — Gate yêu cầu evidence, không nhận assertion
- **Phát biểu kiểm chứng được**: mọi gate/checkpoint (R4, DONE-check…) phải yêu cầu bằng chứng cụ thể (test output, lệnh + kết quả) thay vì lời khai "đã xong".
- **Nguồn**: "Have Claude show evidence rather than asserting success: the test output, the command it ran and what it returned, or a screenshot of the result." — <https://code.claude.com/docs/en/best-practices>, fetch 2026-07-04. `[trực tiếp]`
- **Cách kiểm**: grep các gate trong rules/workflows; gate nào chấp nhận tự khai không evidence = trượt.
- **Applies-to**: rule, workflow.

### BP-22 — Example canonical cho format phức tạp
- **Phát biểu kiểm chứng được**: mỗi format artifact phức tạp (CONTRACT_DAG, TASK_HANDOFF, REQUIREMENT…) có ít nhất một example đầy đủ, đúng chuẩn, thay vì chỉ mô tả field.
- **Nguồn**: "curate a set of diverse, canonical examples that effectively portray the expected behavior of the agent." và "For an LLM, examples are the 'pictures' worth a thousand words." — <https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents>, fetch 2026-07-04. `[trực tiếp]`
- **Cách kiểm**: với từng format artifact trong rules/workflows/skills, tìm example hoàn chỉnh; chỉ có bảng field = trượt.
- **Applies-to**: rule, workflow, skill.

---

## Phụ lục — Nguyên tắc bị loại vì không có nguồn

Cân nhắc nhưng KHÔNG đưa vào rubric (không tìm được căn cứ trong corpus — ghi lại để chứng minh đã xét, không phải bỏ sót):

- "Skill nên có field `version`/`standard` trong frontmatter" — không nguồn nào yêu cầu; chuẩn Anthropic chỉ bắt buộc `name` + `description`.
- "Rule nên đánh ID (R-xx) để tham chiếu" — hợp lý nội bộ nhưng không có trong corpus.
- "Meta-prompt phải dưới N token cụ thể" — corpus chỉ cho nguyên tắc tối thiểu high-signal (BP-15), không cho con số.
- "Description nên viết giọng 'pushy'" — có nguồn (skill-creator) nhưng xung đột một phần với khuyến nghị ngôi-thứ-ba trung tính của docs; giữ ngoài rubric, ghi chú tham khảo khi sửa BP-01.
