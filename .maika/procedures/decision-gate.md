# decision-gate.md — Quy trình gate dùng chung (5 điểm cắm)

> Mọi gate cùng một hình dạng. Gate kiểm BẰNG CHỨNG trong artifact, không kiểm "đã gọi tool chưa".

## Hình dạng chung
1. Tại điểm quyết định → đọc artifact canonical trong `changes/<id>/`.
2. Chạy validator deterministic bằng `gate-check` hoặc orchestrator vNext.
3. Ghi verdict vào `generated/*.json`, `results/*.yaml`, hoặc `reviews/*.md`.
4. Exit khác 0 hoặc verdict khác `APPROVED` → on_fail (ABORT/degrade).

## Điểm cắm vNext
| Gate | file kiểm | validator |
|------|-----------|-----------|
| intent | `CHANGE.yaml`, `INTENT.md` | `intent` |
| exploration evidence | `exploration/GROUNDING.yaml`, `exploration/EVIDENCE_MANIFEST.yaml` | `exploration-evidence` |
| spec | `SPEC.md` | `spec` |
| plan | `IMPLEMENTATION_PLAN.md` | `vnext-plan` |
| brief | `briefs/TASK-*.md` | `vnext-brief` |
| task result | `results/TASK-*.yaml` | `vnext-result` |
| task review | `reviews/TASK-*.md` | `task-review` |
| final review | `reviews/FINAL_REVIEW.md` | `final-review` |
| MCP-probe | dòng MCP-status (bootstrap report / transparency) | `mcp-status` |
| meta prompt | platform entry point | `meta-prompt-constitution` |
| bootstrap | `knowledge/active/BOOTSTRAP_REPORT.yaml` | `bootstrap-complete` |
| context package | `generated/CONTEXT_PACKAGE.<role>.yaml` | `context-package` |
| dispatch prompt | dispatch log/prompt | `dispatch-kernel` |
| material decision | trace block/artifact | `knowledge-trace` |
| skill feedback | `reviews/SKILL_FEEDBACK.yaml` | `skill-feedback` |
| skill candidate | `knowledge/skill-evolution/candidates/*.yaml` | `skill-evolution-candidate` |
| skill review | candidate review artifact | `skill-evolution-review` |
| skill promotion | promotion record | `skill-evolution-promotion` |
- **mcp-status:** số probe thật (`nodes=…`/`edges=…`) **hoặc** dòng degrade `KG unavailable — … MEDIUM`. "Runtime Ready" rỗng = FAIL.

## Knowledge Trace blocking law

`reconciliation`, `spec`, `plan`, `task review`, `final review` và `verification`
phải validate mọi material decision bằng `knowledge-trace`. Chỉ kiểm heading/evidence
reference là chưa đủ. Trace thiếu evidence ID, freshness, authority, confidence,
assumption hoặc có unresolved conflict phải fail và không transition state.
