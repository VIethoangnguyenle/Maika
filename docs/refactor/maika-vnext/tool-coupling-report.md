# W0 — Tool Coupling Report

## 1. OpenSpec dependencies (phải gỡ ở W6)
| File:line | Trích dẫn | Ghi chú |
|---|---|---|
| .maika/hooks/write-gate/README.md:17 | `Framework artifacts, OpenSpec artifacts, and Maika planning/spec docs are allowed` | openspec reference |
| .maika/hooks/write-gate/tests/test_write_gate.py:66 | `def test_allows_framework_and_openspec_artifact_writes(tmp_path):` | openspec reference |
| .maika/hooks/write-gate/tests/test_write_gate.py:68 | `    assert wg.evaluate_write(tmp_path, Path("openspec/changes/x/specs/foo/spec.md")).ok is True` | openspec reference |
| .maika/hooks/write-gate/write_gate.py:384 | `        or parts.startswith("openspec/")` | openspec reference |
| .maika/knowledge/templates/AGENT_TRANSPARENCY.tpl.md:6 | `openspec_state: null` | openspec reference |
| .maika/knowledge/templates/AGENT_TRANSPARENCY.tpl.md:9 | `# openspec_state values: null | propose_done | apply_done` | openspec reference |
| .maika/knowledge/templates/AGENT_TRANSPARENCY.tpl.md:32 | `  phase-2-done        ← Pha 2 hoàn thành (OpenSpec đã propose)` | openspec reference |
| .maika/knowledge/templates/CONTRACT_DAG.tpl.md:2 | `spec_path: "openspec/changes/<change-id>/"` | openspec reference |
| .maika/knowledge/templates/KNOWLEDGE_PACK.tpl.md:11 | `  openspec: "openspec/changes/<change-id>/"` | openspec reference |
| .maika/meta-prompt.md:245 | `| `openspec-explore`                | Thinking Partner — brainstorm, khám phá ý tưởng         | `/op` | openspec reference |
| .maika/meta-prompt.md:246 | `| `openspec-propose`                | Spec Generator — sinh change proposal + artifacts       | `/op` | openspec reference |
| .maika/procedures/bootstrap.md:102 | `     (đặc biệt: CRITICAL block ở đầu Section 2 — OpenSpec requirement)` | openspec reference |
| .maika/procedures/bootstrap.md:105 | `       → CRITICAL: phải dùng OpenSpec. **Không re-trigger Pha 1** dù ticket ID có vẻ thiếu.` | openspec reference |
| .maika/procedures/bootstrap.md:107 | `       → CRITICAL: phải xác nhận spec path là `openspec/changes/<id>/`.` | openspec reference |
| .maika/procedures/context-loader.md:39 | `- Được dùng bởi: `codebase-explorer`, `architecture-reviewer`, `openspec-propose`, `/task apply` — c` | openspec reference |
| .maika/rules/rules-flow.md:13 | `  - Gọi trực tiếp OpenSpec `/opsx:propose` hoặc `/opsx:apply` khi chưa có REQUIREMENT và context tươ` | openspec reference |
| .maika/rules/rules-flow.md:19 | `  `openspec/changes/<id>/` AND không còn `[BLOCKER-ARCH]` chưa resolve trong AGENT_TRANSPARENCY.md` | openspec reference |
| .maika/rules/rules-flow.md:34 | `  - Khi `task.md` yêu cầu dùng OpenSpec → **không được** dùng planning mode sinh `implementation_pla` | openspec reference |
| .maika/rules/rules-knowledge.md:47 | `| REQUIREMENT | `{{ platform.framework_root }}/knowledge/active/REQUIREMENT.md` | requirement-analys` | openspec reference |
| .maika/rules/rules-knowledge.md:48 | `| EXPLORE_CONTEXT | `{{ platform.framework_root }}/knowledge/active/EXPLORE_CONTEXT.md` | db-explore` | openspec reference |
| .maika/rules/rules-tool.md:25 | `### [CRITICAL] R-Tool-3: OpenSpec apply có kiểm soát` | openspec reference |
| .maika/rules/rules-tool.md:106 | `  Gate-check `memory-recall` phải PASS trước khi gọi OpenSpec ở Pha 2 (xem `workflows/task.md`);` | openspec reference |
| .maika/skills/architecture-reviewer/SKILL.md:40 | `- Trước OpenSpec `/opsx:propose` hoặc trước khi giao implementation.` | openspec reference |
| .maika/skills/codebase-explorer/SKILL.md:9 | `  review kiến trúc/rủi ro (→ architecture-reviewer), sinh spec (→ openspec-propose).` | openspec reference |
| .maika/skills/codebase-explorer/SKILL.md:37 | `  - OpenSpec / propose` | openspec reference |
| .maika/skills/codebase-explorer/SKILL.md:52 | `  - OpenSpec `/opsx:propose`` | openspec reference |
| .maika/skills/codebase-explorer/SKILL.md:115 | `- Khi cần sinh spec kỹ thuật chi tiết (→ openspec-propose).` | openspec reference |
| .maika/skills/codebase-explorer/SKILL.md:247 | `- Mọi đề xuất thay đổi kiến trúc hay implement chi tiết thuộc về `architecture-reviewer` và OpenSpec` | openspec reference |
| .maika/skills/codebase-explorer/references/altitude-routing.md:85 | `nên kèm `node_id`/file-path để `architecture-reviewer` và OpenSpec gọi `{{ tools.read_file }}(identi` | openspec reference |
| .maika/skills/db-explorer/SKILL.md:25 | `- Biến các phát hiện này thành **bức tranh dễ đọc trong `EXPLORE_CONTEXT`** để các skill khác (archi` | openspec reference |
| .maika/skills/db-explorer/SKILL.md:57 | `- Khi cần sinh spec kỹ thuật chi tiết (→ openspec-propose).` | openspec reference |
| .maika/skills/document-writer/SKILL.md:8 | `  KHÔNG dùng cho: viết TDD 5 tầng (→ infra-tdd), sinh spec OpenSpec (→ openspec-propose),` | openspec reference |
| .maika/skills/document-writer/SKILL.md:38 | `- Khi cần sinh spec kỹ thuật OpenSpec (→ openspec-propose).` | openspec reference |
| .maika/skills/infra-tdd/SKILL.md:9 | `  spec OpenSpec (→ openspec-propose), review kiến trúc (→ architecture-reviewer).` | openspec reference |
| .maika/skills/infra-tdd/SKILL.md:46 | `- Khi cần sinh spec kỹ thuật OpenSpec (→ openspec-propose).` | openspec reference |
| .maika/skills/knowledge-curator/SKILL.md:8 | `  sinh/validate spec (→ openspec-propose, spec-validator), viết tài liệu (→ document-writer).` | openspec reference |
| .maika/skills/knowledge-curator/references/token-calibration.md:48 | `| Sinh spec (openspec-propose) | ~3,000–8,000 |` | openspec reference |
| .maika/skills/openspec-explore/SKILL.md:2 | `name: openspec-explore` | openspec reference |
| .maika/skills/openspec-explore/SKILL.md:9 | `  sinh spec/artifact (→ openspec-propose), review kiến trúc (→ architecture-reviewer).` | openspec reference |
| .maika/skills/openspec-explore/SKILL.md:11 | `compatibility: Requires openspec CLI.` | openspec reference |
| .maika/skills/openspec-explore/SKILL.md:13 | `  author: openspec` | openspec reference |
| .maika/skills/openspec-explore/SKILL.md:18 | `# OpenSpec Explore — Đối tác suy nghĩ` | openspec reference |
| .maika/skills/openspec-explore/SKILL.md:30 | `- Có thể tạo OpenSpec artifact khi user yêu cầu; đó là ghi lại suy nghĩ, không phải implement.` | openspec reference |
| .maika/skills/openspec-explore/SKILL.md:50 | `- Cần sinh technical spec/artifact (→ openspec-propose).` | openspec reference |
| .maika/skills/openspec-explore/SKILL.md:61 | `- Capture có kỷ luật: khi một insight quan trọng đã được diagram làm rõ, offer capture insight đó và` | openspec reference |
| .maika/skills/openspec-explore/SKILL.md:64 | `Đọc [references/openspec-awareness.md](references/openspec-awareness.md) khi trạng thái OpenSpec hoặ` | openspec reference |
| .maika/skills/openspec-explore/references/examples.md:3 | `> Tài liệu tham khảo cho `openspec-explore`. Đọc chỉ khi cần ví dụ về cách dẫn dắt hội thoại explore` | openspec reference |
| .maika/skills/openspec-explore/references/explore-patterns.md:3 | `> Tài liệu tham khảo cho `openspec-explore`. Đọc khi cuộc trò chuyện cần khám phá sâu, so sánh optio` | openspec reference |
| .maika/skills/openspec-explore/references/explore-patterns.md:46 | `Insight này đã rõ hơn sau diagram. Capture vào EXPLORE_CONTEXT.md hoặc artifact OpenSpec liên quan k` | openspec reference |
| .maika/skills/openspec-explore/references/openspec-awareness.md:1 | `# Nhận biết OpenSpec` | openspec reference |
| .maika/skills/openspec-explore/references/openspec-awareness.md:3 | `> Tài liệu tham khảo cho `openspec-explore`. Đọc khi cuộc trao đổi chạm tới active OpenSpec change h` | openspec reference |
| .maika/skills/openspec-explore/references/openspec-awareness.md:14 | `Chạy `openspec list --json` khi trạng thái OpenSpec có ảnh hưởng tới cuộc trao đổi.` | openspec reference |
| .maika/skills/openspec-propose/SKILL.md:2 | `name: openspec-propose` | openspec reference |
| .maika/skills/openspec-propose/SKILL.md:7 | `  NOT for: exploring ideas/brainstorming (→ openspec-explore),` | openspec reference |
| .maika/skills/openspec-propose/SKILL.md:10 | `compatibility: Requires openspec CLI.` | openspec reference |
| .maika/skills/openspec-propose/SKILL.md:12 | `  author: openspec` | openspec reference |
| .maika/skills/openspec-propose/SKILL.md:55 | `- Khi cần brainstorm, khám phá ý tưởng (→ openspec-explore).` | openspec reference |
| .maika/skills/openspec-propose/SKILL.md:93 | `   openspec new change "<name>"` | openspec reference |
| .maika/skills/openspec-propose/SKILL.md:95 | `   This creates a scaffolded change at `openspec/changes/<name>/` with `.openspec.yaml`.` | openspec reference |
| .maika/skills/openspec-propose/SKILL.md:99 | `   openspec status --change "<name>" --json` | openspec reference |
| .maika/skills/openspec-propose/SKILL.md:114 | `        openspec instructions <artifact-id> --change "<name>" --json` | openspec reference |
| .maika/skills/openspec-propose/SKILL.md:129 | `      - After creating each artifact, re-run `openspec status --change "<name>" --json`` | openspec reference |
| .maika/skills/openspec-propose/SKILL.md:139 | `   openspec status --change "<name>"` | openspec reference |
| .maika/skills/openspec-propose/SKILL.md:152 | `- Follow the `instruction` field from `openspec instructions` for each artifact type` | openspec reference |
| .maika/skills/requirement-analyst/SKILL.md:8 | `  KHÔNG dùng cho: ideation thô chưa thành ticket (→ openspec-explore),` | openspec reference |
| .maika/skills/requirement-analyst/SKILL.md:37 | `- Ideation thô (→ openspec-explore).` | openspec reference |
| .maika/skills/requirement-analyst/SKILL.md:40 | `- Technical spec generation (→ openspec-propose).` | openspec reference |
| .maika/skills/skill-index.yaml:46 | `      review kiến trúc/rủi ro (→ architecture-reviewer), sinh spec (→ openspec-propose).` | openspec reference |
| .maika/skills/skill-index.yaml:82 | `      KHÔNG dùng cho: viết TDD 5 tầng (→ infra-tdd), sinh spec OpenSpec (→ openspec-propose),` | openspec reference |
| .maika/skills/skill-index.yaml:92 | `      spec OpenSpec (→ openspec-propose), review kiến trúc (→ architecture-reviewer).` | openspec reference |
| .maika/skills/skill-index.yaml:106 | `      sinh/validate spec (→ openspec-propose, spec-validator), viết tài liệu (→ document-writer).` | openspec reference |
| .maika/skills/skill-index.yaml:115 | `    compatibility: Requires openspec CLI.` | openspec reference |
| .maika/skills/skill-index.yaml:117 | `      author: openspec` | openspec reference |
| .maika/skills/skill-index.yaml:121 | `    name: openspec-explore` | openspec reference |
| .maika/skills/skill-index.yaml:128 | `      sinh spec/artifact (→ openspec-propose), review kiến trúc (→ architecture-reviewer).` | openspec reference |
| .maika/skills/skill-index.yaml:130 | `    compatibility: Requires openspec CLI.` | openspec reference |
| .maika/skills/skill-index.yaml:132 | `      author: openspec` | openspec reference |
| .maika/skills/skill-index.yaml:136 | `    name: openspec-propose` | openspec reference |
| .maika/skills/skill-index.yaml:141 | `      NOT for: exploring ideas/brainstorming (→ openspec-explore),` | openspec reference |
| .maika/skills/skill-index.yaml:144 | `    compatibility: Requires openspec CLI.` | openspec reference |
| .maika/skills/skill-index.yaml:146 | `      author: openspec` | openspec reference |
| .maika/skills/skill-index.yaml:166 | `      KHÔNG dùng cho: ideation thô chưa thành ticket (→ openspec-explore),` | openspec reference |
| .maika/skills/skill-index.yaml:181 | `      ideation/brainstorm (→ openspec-explore), khám phá DB schema (→ db-explorer).` | openspec reference |
| .maika/skills/skill-index.yaml:190 | `      Kiểm tra spec (OpenSpec artifacts) trước và sau khi apply — pre-apply gate, AC coverage check,` | openspec reference |
| .maika/skills/skill-index.yaml:192 | `      KHÔNG dùng cho: sinh spec mới (→ openspec-propose),` | openspec reference |
| .maika/skills/spec-extract/SKILL.md:9 | `  ideation/brainstorm (→ openspec-explore), khám phá DB schema (→ db-explorer).` | openspec reference |
| .maika/skills/spec-extract/SKILL.md:68 | `- Việc sinh spec kỹ thuật chi tiết cho implementation (đó là job của OpenSpec `/opsx:propose`).` | openspec reference |
| .maika/skills/spec-extract/SKILL.md:75 | `- Khi cần ideation/brainstorm ý tưởng thô (→ openspec-explore).` | openspec reference |
| .maika/skills/spec-extract/SKILL.md:77 | `- Khi cần sinh spec kỹ thuật chi tiết cho implementation (→ openspec-propose).` | openspec reference |
| .maika/skills/spec-validator/SKILL.md:5 | `  Kiểm tra spec (OpenSpec artifacts) trước và sau khi apply — pre-apply gate, AC coverage check, pos` | openspec reference |
| .maika/skills/spec-validator/SKILL.md:7 | `  KHÔNG dùng cho: sinh spec mới (→ openspec-propose),` | openspec reference |
| .maika/skills/spec-validator/SKILL.md:38 | `- Cần sinh spec mới (→ openspec-propose).` | openspec reference |
| .maika/skills/spec-validator/SKILL.md:48 | `CHANGE_ID="${CHANGE_ID:?set CHANGE_ID to the OpenSpec change folder name}"` | openspec reference |
| .maika/skills/spec-validator/SKILL.md:49 | `python3 {{ platform.framework_root }}/tools/gate-check/cli.py ac-coverage {{ platform.framework_root` | openspec reference |
| .maika/skills/spec-validator/SKILL.md:55 | `CHANGE_ID="${CHANGE_ID:?set CHANGE_ID to the OpenSpec change folder name}"` | openspec reference |
| .maika/skills/spec-validator/SKILL.md:56 | `python3 {{ platform.framework_root }}/tools/gate-check/cli.py integration-coverage {{ platform.frame` | openspec reference |
| .maika/skills/spec-validator/references/coverage-checks.md:10 | `CHANGE_ID="${CHANGE_ID:?set CHANGE_ID to the OpenSpec change folder name}"` | openspec reference |
| .maika/skills/spec-validator/references/coverage-checks.md:11 | `python3 {{ platform.framework_root }}/tools/gate-check/cli.py ac-coverage {{ platform.framework_root` | openspec reference |
| .maika/skills/spec-validator/references/coverage-checks.md:12 | `python3 {{ platform.framework_root }}/tools/gate-check/cli.py integration-coverage {{ platform.frame` | openspec reference |
| .maika/skills/spec-validator/references/gotchas.md:7 | `- OpenSpec artifact path có thể đổi; verify file tồn tại trước khi đọc.` | openspec reference |
| .maika/skills/spec-validator/references/pre-apply-gate.md:11 | `- OPENSPEC_STATE là propose_done.` | openspec reference |
| .maika/tools/gate-check/tests/test_gates.py:146 | `    done = "Pha 1 DONE\nPha 2 DONE (spec: openspec/changes/x/)\nPha 3 DONE"` | openspec reference |
| .maika/tools/microloop-orchestrator/tests/test_contract.py:11 | `        "spec_path": "openspec/changes/abc-1/",` | openspec reference |
| .maika/tools/microloop-orchestrator/tests/test_contract.py:76 | `        "spec_path": "openspec/changes/add-payment-processor/",` | openspec reference |
| .maika/tools/microloop-orchestrator/tests/test_contract.py:163 | `        "spec_path": "openspec/changes/x/",` | openspec reference |
| .maika/tools/microloop-orchestrator/tests/test_contract.py:175 | `        "spec_path": "openspec/changes/x/",` | openspec reference |
| .maika/tools/microloop-orchestrator/tests/test_contract.py:190 | `        "spec_path": "openspec/changes/x/",` | openspec reference |
| .maika/tools/microloop-orchestrator/tests/test_runtime_contract.py:32 | `        spec_path="openspec/changes/sme-transfer-002/tasks.md",` | openspec reference |
| .maika/tools/skill-lint/tests/test_sp3_doctrine_litmus.py:25 | `    for name in ("openspec-explore", "spec-extract"):` | openspec reference |
| .maika/workflows/task.md:2 | `description: Orchestrator /task (đa pha) cho ideation + ticket + OpenSpec.` | openspec reference |
| .maika/workflows/task.md:252 | `Mục tiêu: dùng OpenSpec để sinh **spec kỹ thuật** dựa trên REQUIREMENT + bối cảnh hệ thống đã hiểu ở` | openspec reference |
| .maika/workflows/task.md:256 | `> - **BẮT BUỘC** phải gọi quy trình OpenSpec (`/opsx:propose` hoặc sử dụng skill `openspec-propose`)` | openspec reference |
| .maika/workflows/task.md:272 | `   > rõ ràng (ví dụ: _“triển khai spec để coding”_ không có nghĩa đã confirm OpenSpec flow).` | openspec reference |
| .maika/workflows/task.md:277 | `   - **[MEMORY-RECALL GATE — R-Tool-6]** Trước khi gọi OpenSpec:` | openspec reference |
| .maika/workflows/task.md:284 | `       — PHẢI pass (exit 0) rồi mới được gọi OpenSpec.` | openspec reference |
| .maika/workflows/task.md:285 | `   - Gọi OpenSpec:` | openspec reference |
| .maika/workflows/task.md:288 | `     hoặc bất kỳ file nào ra ngoài `openspec/changes/<change-id>/`) — kể cả khi agent` | openspec reference |
| .maika/workflows/task.md:290 | `   - Chờ spec được sinh ra (bộ artifact trong `openspec/changes/<change-id>/`).` | openspec reference |
| .maika/workflows/task.md:294 | `   - Xác nhận output path là `openspec/changes/<change-id>/` trước khi báo cáo hoàn thành.` | openspec reference |
| .maika/workflows/task.md:296 | `     - Ghi `OPENSPEC_STATE: propose_done` vào AGENT_TRANSPARENCY.md (section Cảnh báo / Hạn chế).` | openspec reference |
| .maika/workflows/task.md:298 | `     - Thêm dòng vào section "Lịch sử pha": `Pha 2 DONE | <timestamp> | spec tại openspec/changes/<c` | openspec reference |
| .maika/workflows/task.md:301 | `     - Ý nghĩa: bất kỳ thay đổi requirement nào SAU điểm này đều làm OpenSpec spec hiện tại` | openspec reference |
| .maika/workflows/task.md:314 | `   - Estimate token Pha 2: input (REQUIREMENT + EXPLORE_CONTEXT + OpenSpec instructions) + output (s` | openspec reference |
| .maika/workflows/task.md:319 | `   - `[ ]` spec file tồn tại trong `openspec/changes/<change-id>/`.` | openspec reference |
| .maika/workflows/task.md:322 | `   - `[ ]` `OPENSPEC_STATE: propose_done` đã ghi vào AGENT_TRANSPARENCY.md.` | openspec reference |
| .maika/workflows/task.md:332 | `      > Spec đã lưu tại `openspec/changes/<change-id>/`.` | openspec reference |
| .maika/workflows/task.md:350 | `Mục tiêu: dùng OpenSpec để áp dụng spec đã được chấp thuận vào codebase một cách có kiểm soát.` | openspec reference |
| .maika/workflows/task.md:406 | `   b. Build `CONTRACT_DAG.md` from OpenSpec `tasks.md`:` | openspec reference |
| .maika/workflows/task.md:500 | `  - Không thay thế logic chi tiết của từng skill (requirement-analyst, db-explorer, codebase-explore` | openspec reference |
| README.md:160 | `- `workflows/*.md`: `/task`, `/idea-to-task`, `/convention-scan`, `/dna-scan`, OpenSpec flows.` | openspec reference |
| README.md:194 | ` ideation     REQUIREMENT   EXPLORE     OpenSpec  code` | openspec reference |
| README.md:206 | `| Spec | Sinh spec kỹ thuật và OpenSpec change | `openspec/changes/<id>/` |` | openspec reference |
| README.md:300 | `| `/opsx-explore` | OpenSpec explore mode |` | openspec reference |
| README.md:302 | `| `/opsx-apply` | Implement từ OpenSpec change |` | openspec reference |
| README.md:577 | `### Maika có bắt buộc dùng OpenSpec không?` | openspec reference |
| cli/plugin-manifest.yaml:202 | `  - name: openspec-explore` | openspec reference |
| cli/plugin-manifest.yaml:204 | `    source: skills/openspec-explore/` | openspec reference |
| cli/plugin-manifest.yaml:206 | `    output: "{{ platform.framework_root }}/skills/openspec-explore/"` | openspec reference |
| cli/plugin-manifest.yaml:209 | `  - name: openspec-propose` | openspec reference |
| cli/plugin-manifest.yaml:211 | `    source: skills/openspec-propose/` | openspec reference |
| cli/plugin-manifest.yaml:213 | `    output: "{{ platform.framework_root }}/skills/openspec-propose/"` | openspec reference |
| cli/tests/test_ascii_diagram_guidance.py:39 | `def test_openspec_explore_uses_visual_stance_and_capture():` | openspec reference |
| cli/tests/test_ascii_diagram_guidance.py:40 | `    skill = read_text(".maika/skills/openspec-explore/SKILL.md")` | openspec reference |
| cli/tests/test_ascii_diagram_guidance.py:41 | `    patterns = read_text(".maika/skills/openspec-explore/references/explore-patterns.md")` | openspec reference |

## 2. Concrete MCP names trong canonical docs (phải capability-hóa ở W1–W4)
| File:line | Provider name | Vùng đích (mappings/adapter/tool-doc) |
|---|---|---|
| .maika/procedures/bootstrap.md:174 | understand-anything | need capability mapping |
| .maika/procedures/bootstrap.md:179 | agent-memory | need capability mapping |
| .maika/procedures/bootstrap.md:180 | agent-memory | need capability mapping |
| .maika/procedures/bootstrap.md:183 | agent-memory | need capability mapping |
| .maika/procedures/executor.md:16 | agent-memory | need capability mapping |
| .maika/rules/rules-exec.md:71 | agent-memory | need capability mapping |
| .maika/rules/rules-tool.md:42 | agent-memory | need capability mapping |
| .maika/rules/rules-tool.md:76 | agent-memory | need capability mapping |
| .maika/rules/rules-tool.md:105 | agent-memory | need capability mapping |
| .maika/rules/rules-tool.md:116 | agent-memory | need capability mapping |
| .maika/rules/rules-tool.md:126 | agent-memory | need capability mapping |
| .maika/rules/rules-tool.md:128 | agent-memory | need capability mapping |
| .maika/rules/rules-tool.md:130 | agent-memory | need capability mapping |
| .maika/rules/rules-tool.md:132 | agent-memory | need capability mapping |
| .maika/rules/rules-tool.md:184 | agent-memory | need capability mapping |
| .maika/skills/codebase-explorer/SKILL.md:24 | agent-memory | need capability mapping |
| .maika/skills/codebase-explorer/SKILL.md:148 | codebase-memory | need capability mapping |
| .maika/skills/knowledge-curator/references/m7-memory-push.md:25 | agent-memory | need capability mapping |
| .maika/skills/knowledge-curator/references/m7-memory-push.md:27 | agent-memory | need capability mapping |
| .maika/skills/knowledge-curator/references/m7-memory-push.md:28 | agent-memory | need capability mapping |
| .maika/skills/knowledge-curator/references/m7-memory-push.md:31 | agent-memory | need capability mapping |
| .maika/skills/requirement-analyst/references/ua-open-question-filter.md:16 | agent-memory | need capability mapping |
| .maika/skills/spec-extract/SKILL.md:21 | agent-memory | need capability mapping |
| .maika/workflows/index-source.md:14 | understand-anything | need capability mapping |
| .maika/workflows/task.md:278 | agent-memory | need capability mapping |
| .maika/workflows/task.md:280 | agent-memory | need capability mapping |
| .maika/workflows/task.md:281 | agent-memory | need capability mapping |
| .maika/workflows/task.md:282 | agent-memory | need capability mapping |
| .maika/workflows/task.md:526 | agent-memory | need capability mapping |
| .maika/workflows/task.md:528 | agent-memory | need capability mapping |

## 3. Kết luận
- Số điểm coupling OpenSpec: 144
- Số canonical doc chứa provider name: 30
- Input cho W1 (vocabulary) và W6 (cutover).
