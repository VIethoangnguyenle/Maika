# Design: Audit "Maika vs Best Practices" — citation-grounded, lọc 2 tầng

> Trạng thái: design đã chốt với user (2026-07-04)
> Phạm vi: skills + rules + meta-prompt + workflows (chốt với user, không gồm hooks/tools/profiles)
> Nguyên tắc bao trùm (yêu cầu trực tiếp của user): **mọi tiêu chí và mọi finding đều phải có dẫn chứng nguyên văn** từ bài báo best-practice của Anthropic hoặc bài báo lớn tương đương — không tiêu chí nào vào rubric "từ trí nhớ".

---

## 1. Vấn đề & mục tiêu

Maika đã tích lũy 14 skill (`.maika/skills/`), 48 rule heading trong 5 sub-file `rules-*.md` + manifest `RULES.md` (`.maika/rules/`, 6 file tổng), meta-prompt 19K (`.maika/meta-prompt.md`) và bộ workflows — phần lớn viết trước khi đối chiếu hệ thống với các chuẩn Anthropic công bố. Các dấu hiệu lệch chuẩn đã lộ ra rời rạc:

- Bootstrap yêu cầu **đọc đủ 6 rule file** mỗi phiên (`RULES.md` §Load Order) — nghi ngờ ngược với nguyên tắc progressive disclosure / context economy.
- Audit enforcement 2026-06-20 (TODOS.md): phần lớn rule `[CRITICAL]` chỉ "trên giấy", không hook cơ học.
- Gap #4 còn TODO: 8/14 skill thiếu `pre_conditions:`, 0/14 khai báo `outputs:`.

Nhưng "dấu hiệu rời rạc" chưa phải audit. Mục tiêu: **một lần đối chiếu có hệ thống, có trích dẫn, có thứ hạng** — ra được (a) danh sách gap khớp failure thật để sửa, (b) watchlist chờ bằng chứng, (c) rubric tái dùng làm chuẩn authoring cho skill/rule mới.

## 2. Quyết định đã chốt với user

1. **Đích**: audit gap vs chuẩn Anthropic (không phải viết guideline trước — rubric là sản phẩm phụ tái dùng được).
2. **Phạm vi**: 14 skill + 6 rule file + `meta-prompt.md` + `workflows/`. Không mở rộng sang hooks/tools/profiles trong vòng này.
3. **Verdict lọc 2 tầng** (trung thành DEVELOPMENT_RULES "build for observed failures only"): mọi gap đều ghi nhận; chỉ gap **khớp failure đã quan sát** mới thành đề xuất sửa; còn lại vào **watchlist** kèm điều kiện kích hoạt.
4. **Approach B — rubric + worker**: orchestrator (Claude) chưng cất rubric và phán verdict; worker (codex/agy) quét file thu evidence thô. Đúng phân công ORCHESTRATION.md: reasoning ở orchestrator, token-nặng ở worker.
5. **Kỷ luật trích dẫn là quy tắc cứng số 1** (user nhấn mạnh 2026-07-04): chi tiết §4.

## 3. Corpus nguồn

Fetch **mới** tại thời điểm audit, ghi ngày fetch từng nguồn — không dựa training knowledge (knowledge cutoff có thể lệch bản cập nhật).

| Tầng | Nguồn | Vai trò |
| --- | --- | --- |
| 1 — Anthropic engineering | [Building Effective Agents](https://www.anthropic.com/engineering/building-effective-agents) | Ranh giới workflow/agent, các pattern orchestration |
| 1 | [Effective Context Engineering for AI Agents](https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents) | Context economy, progressive disclosure, just-in-time retrieval |
| 1 | [Writing Effective Tools for Agents](https://www.anthropic.com/engineering/writing-tools-for-agents) | Ergonomics tool/skill: naming, description, token efficiency |
| 1 | [Claude Code Best Practices](https://www.anthropic.com/engineering/claude-code-best-practices) | CLAUDE.md/rule content, workflow con người-agent |
| 1 | [Equipping Agents for the Real World with Agent Skills](https://www.anthropic.com/engineering/equipping-agents-for-the-real-world-with-agent-skills) | Triết lý skill: cấu trúc, khi nào skill vs tool |
| 1 | [How We Built Our Multi-Agent Research System](https://www.anthropic.com/engineering/built-multi-agent-research-system) | Prompt orchestrator-worker, phân công subagent |
| 1 — Anthropic docs/repo | docs.claude.com — Agent Skills authoring best practices; repo [`anthropics/skills`](https://github.com/anthropics/skills) (skill-creator) | Chuẩn kỹ thuật SKILL.md: frontmatter, description-as-trigger, progressive disclosure |
| 2 — vendor lớn khác | OpenAI *A Practical Guide to Building Agents* và tương đương | **Chỉ dùng khi Anthropic im lặng** về chủ đề; finding từ tầng 2 phải ghi rõ tầng nguồn |

Nguồn phát hiện thêm trong lúc fetch (bài mới, bài được link chéo): được phép bổ sung nếu là engineering blog chính chủ vendor lớn hoặc paper có peer-review; ghi vào bảng corpus của rubric khi dùng.

## 4. Kỷ luật trích dẫn (quy tắc cứng)

1. Mỗi tiêu chí rubric **bắt buộc** có: quote nguyên văn (tiếng Anh gốc) + URL + ngày fetch.
2. Mỗi finding trong báo cáo **bắt buộc** trỏ về ID tiêu chí — tức mọi kết luận truy ngược được tới quote gốc.
3. Nguyên tắc không tìm được nguồn → **loại khỏi rubric**, kể cả khi "ai cũng biết". Nếu tiếc, ghi vào phụ lục "không có nguồn — không dùng làm căn cứ".
4. Quote phải giữ ngữ cảnh đủ để không bị bẻ nghĩa; nếu bài báo nói về ngữ cảnh khác (vd tool cho MCP) mà tiêu chí áp cho skill, phải đánh dấu **[phiên dịch]** (§7).

Tiền lệ trong repo: design Pha 3 (`2026-07-04-phase3-driver-thin-orchestrator-design.md` §2) đã dùng đúng mô hình quote + fetch-date này và verdict trở nên khó cãi — audit này chuẩn hóa mô hình đó thành quy tắc.

## 5. Rubric

File riêng (deliverable b, §8). Mỗi tiêu chí:

```markdown
### BP-07 — Description là trigger, không phải mô tả nội dung
- **Phát biểu kiểm chứng được**: frontmatter `description` của SKILL.md phải nói rõ KHI NÀO dùng
  (điều kiện kích hoạt + anti-trigger), không chỉ tóm tắt skill làm gì.
- **Nguồn**: "..." (quote nguyên văn) — <URL>, fetch 2026-07-XX. [trực tiếp | phiên dịch]
- **Cách kiểm**: đọc frontmatter 14 SKILL.md; đạt nếu có điều kiện "dùng khi…/KHÔNG dùng cho…".
- **Applies-to**: skill.
```

Ràng buộc chất lượng rubric:

- Phát biểu phải **kiểm chứng được trên file** (đọc gì, grep gì, đạt/trượt ra sao) — cấm tiêu chí mơ hồ kiểu "nên rõ ràng".
- Mỗi tiêu chí gắn `applies-to`: skill / rule / workflow / meta-prompt (một hoặc nhiều).
- Đánh dấu `[trực tiếp]` vs `[phiên dịch]` (§7).
- Số lượng dự kiến 15–25 tiêu chí; quá 30 là dấu hiệu rubric đang chép bài báo thay vì chưng cất.

## 6. Worker sweep

- **Input cho worker**: rubric hoàn chỉnh + danh sách file đích (14 SKILL.md, 6 rule file, meta-prompt.md, workflows/).
- **Output từ worker**: evidence thô per tiêu chí per file — quote dòng + đường dẫn + nhận định đạt/trượt sơ bộ. **Không verdict cuối** — verdict là việc orchestrator.
- **Vận hành**: chạy detach (nohup + log file) theo bài học run dài đã ghi nhớ; chia batch theo `applies-to` nếu một run quá lớn (vd batch skills riêng, batch rules+meta-prompt riêng).
- **Kiểm tra chéo tối thiểu**: orchestrator spot-check ≥3 evidence/batch trước khi tin toàn bộ batch (worker có thể quote sai dòng).

## 7. Phiên dịch ngữ cảnh — rủi ro chính

Các bài Anthropic viết cho *agent dùng tool trực tiếp trong một phiên*; Maika là *framework sinh scaffold đa platform* (Claude Code + Codex + Antigravity). Một tiêu chí có thể đúng nguyên văn với agent nhưng cần phiên dịch khi áp cho template scaffold. Quy tắc:

- Tiêu chí `[trực tiếp]`: áp nguyên văn (vd cấu trúc SKILL.md — Maika skill chính là skill).
- Tiêu chí `[phiên dịch]`: rubric phải ghi rõ **bước suy diễn** (vd "token efficiency của tool response" → "token footprint của rule file nạp lúc bootstrap"). Finding dựa trên tiêu chí phiên dịch xếp confidence thấp hơn một bậc khi ranking.
- Không phiên dịch được sạch → tiêu chí bị loại, không cố ép.

## 8. Verdict 2 tầng & deliverables

**Kho failure đối chiếu (tầng 2):** `bao_cao_loi.md`, audit enforcement 2026-06-20 (TODOS.md §Enforcement hardening), `Maika-v3-assessment.md`, các observed-failure đã neo trong specs gần đây (vd context-tràn 2026-07-03 ở downstream Antigravity).

**Phân loại finding:**

| Loại | Điều kiện | Đầu ra |
| --- | --- | --- |
| **Fix proposal** | Gap khớp ≥1 failure đã quan sát (ghi rõ failure nào) | Vào báo cáo phần A, xếp hạng theo đòn bẩy (failure nặng × chi phí sửa thấp); feed vào TODOS.md đúng format hiện có |
| **Watchlist** | Gap có trích dẫn nhưng chưa có failure | Báo cáo phần B, kèm **điều kiện kích hoạt** ("nếu quan sát thấy X → nâng lên fix") |
| **Đạt chuẩn** | Không gap | Ghi một dòng — làm bằng chứng "đã audit, không phải bỏ sót" |

**Deliverables:**

1. Design doc này — `docs/superpowers/specs/2026-07-04-anthropic-bp-audit-design.md`.
2. Rubric — `docs/superpowers/specs/2026-07-04-anthropic-bp-rubric.md` (sống ở docs/ trước; chỉ chuyển vào `.maika/knowledge/` khi có consumer thật theo DEVELOPMENT_RULES "no declaration without a consumer" — consumer đầu tiên chính là audit này).
3. Báo cáo audit — `docs/superpowers/specs/2026-07-04-anthropic-bp-audit-report.md`: phần A fix proposals xếp hạng, phần B watchlist, phần C đạt chuẩn.
4. Cập nhật TODOS.md: các fix proposal thành entry P-x đúng format.

## 9. Exit criteria

- Rubric: 15–25 tiêu chí, 100% có quote + URL + ngày fetch, 100% có cách kiểm trên file.
- Evidence: phủ đủ 14 skill + 6 rule + meta-prompt + workflows; orchestrator đã spot-check ≥3 evidence/batch.
- Báo cáo: mọi finding trỏ về BP-ID; mọi fix proposal ghi rõ failure quan sát nào; watchlist có điều kiện kích hoạt.
- TODOS.md nhận các fix proposal; không sửa code/rule nào trong vòng audit này (audit tách khỏi thực thi sửa).

## 10. Điều cố ý KHÔNG làm

- Không sửa bất kỳ skill/rule/meta-prompt nào trong vòng audit (tách đo khỏi sửa — tránh churn khi verdict chưa đủ chín).
- Không đưa tiêu chí không nguồn vào rubric dù hợp lý đến đâu (quy tắc cứng §4).
- Không mở rộng phạm vi sang hooks/tools/profiles (chốt §2) — nếu evidence lộ ra vấn đề ở lớp đó, ghi chú sang một mục "ngoài phạm vi" chứ không audit.
- Không dùng tầng-2 corpus khi Anthropic đã có ý kiến về cùng chủ đề.
