# {{ platform.framework_root }}/tools/

Executable tooling cho Maika.

## rule-projector/ (SP1a — Mechanical Enforcement Layer)

Chiếu phần **kiểm-tra-được-bằng-máy** của `author-dna.yaml` + `conventions.yaml` thành
ruleset Checkstyle, enforce ở git pre-commit của dự án Java đích.

```
author-dna.yaml + conventions.yaml
   → projector.py            → IR (generated/rules.json, neutral JSON)
   → backends/checkstyle.py  → generated/checkstyle.generated.xml
   → hooks/pre-commit.sh (sync-check + checkstyle), cài bằng install.sh
```

- **Run**: `python3 {{ platform.framework_root }}/tools/rule-projector/projector.py --dna <dna> --conventions <conv> --out <dir>`
  rồi `python3 {{ platform.framework_root }}/tools/rule-projector/backends/checkstyle.py --ir <dir>/rules.json --out <dir>/checkstyle.generated.xml`
- **Test**: `python3 -m pytest {{ platform.framework_root }}/tools/rule-projector/tests/ -v`
- **Cài vào dự án Java**: `{{ platform.framework_root }}/tools/rule-projector/install.sh <project_root> <dna_path> <conv_path>`

Chi tiết (repo framework): [docs/superpowers/specs/2026-06-17-sp1a-mechanical-enforcement-design.md](../../docs/superpowers/specs/2026-06-17-sp1a-mechanical-enforcement-design.md)

## microloop-orchestrator/ (SP1b — Coding Micro-loop + Extraction Review)

Viết lại Pha 3 thành vòng lặp subagent tuần tự context-sạch + extraction review (HP-10/11).
Lõi portable: **contract trung lập trên filesystem** + 3 execution tier; orchestrator
platform-agnostic, chỉ `dispatch` là điểm tier-specific.

```
tasks.md → topo-sort → TASK_QUEUE → per-task: TASK_HANDOFF → executor → mechanical gate (SP1a)
   → semantic surface-check → mark done → next ; hết task → extraction review → EXTRACTION_REPORT
```

- **Tier** khai báo ở `{{ platform.framework_root }}/profiles/execution-mode.yaml`: `subagent` (Claude) ·
  `fresh-session` (Cursor/Antigravity) · `inline-reload` (fallback, luôn chạy được).
- **Test**: `python3 -m pytest {{ platform.framework_root }}/tools/microloop-orchestrator/tests/ -v`

Chi tiết (repo framework): [docs/superpowers/specs/2026-06-17-sp1b-coding-microloop-design.md](../../docs/superpowers/specs/2026-06-17-sp1b-coding-microloop-design.md)

## gate-check/ — Evidence gate validators

Kiểm checkpoint artifact bằng token bằng chứng (xem `procedures/decision-gate.md`).
- **Run**: `python3 {{ platform.framework_root }}/tools/gate-check/cli.py <gate> <file>` — gates: knowledge-checkpoint, handoff-slice, implementation-context, phase-chain, mcp-status, memory-recall, teaching-moment, archive-ready, ac-coverage, integration-coverage…
- **Test**: `python3 -m pytest {{ platform.framework_root }}/tools/gate-check/tests/ -v`

## skill-lint/ — Skill schema validator (SP2) — chỉ repo framework

Lint mọi `skills/*/SKILL.md` theo Hybrid Schema (R-Skill-1/2). Không scaffold sang
downstream — skill authoring là hoạt động repo framework.
- **Run** (source repo framework): `python3 .maika/tools/skill-lint/validate_skills.py`

## knowledge-index/ — Knowledge index generator

Sinh `knowledge/long-term/knowledge-index.yaml` (entry list cho JIT slice tại decision-gate).
- **Run**: `python3 {{ platform.framework_root }}/tools/knowledge-index/generate_index.py {{ platform.framework_root }}/knowledge/long-term`

## skill-index/ — Skill index generator — chỉ repo framework

Sinh `skills/skill-index.yaml` từ frontmatter các SKILL.md. Tool không scaffold sang
downstream; file output `skills/skill-index.yaml` thì được ship (bootstrap READ nó).

## mcp-bridge/ — MCP bridge fallback

`mcp_client.py` — chỉ dùng khi native MCP fail và `maika doctor mcp` đã ghi bridge evidence (xem R-Tool-5 §Bridge fallback).
