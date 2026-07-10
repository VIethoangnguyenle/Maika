# Maika vNext W0 — Current-State Audit

- **Ngày:** 2026-07-10
- **Baseline commit:** a31dc30

## 1. Branch inventory

| Branch | Đụng vùng | Quyết định (resolve / stack / ignore) | Lý do |
|---|---|---|---|
| enforcement-followups-preconditions | không | ignore | Không đụng vùng nhạy cảm |
| feat/r-ki-2-doctrine-override-guard | có | resolve | Đụng cli và rules, cần merge trước W1 |
| fix/agy-native-mcp | không | ignore | Không đụng vùng nhạy cảm |
| fix/antigravity-hooks-20-format | không | ignore | Không đụng vùng nhạy cảm |
| fix/ua-first-restore | có | resolve | Đụng cli/platforms, cần merge trước W1 |

## 2. Baseline test record

Baseline commit: `a31dc30` — chạy ngày 2026-07-10 bằng /usr/bin/python3.

| Suite | Lệnh | Kết quả |
|---|---|---|
| cli | `pytest cli/tests/ -q` | `295 passed, 1 skipped in 8.30s` |
| gate-check | `pytest .maika/tools/gate-check/tests/ -q` | `95 passed in 0.09s` |
| microloop-orchestrator | `pytest .maika/tools/microloop-orchestrator/tests/ -q` | `81 passed in 1.20s` |
| write-gate | `pytest .maika/hooks/write-gate/tests/ -q` | `69 passed in 0.23s` |
| knowledge-index | `pytest .maika/tools/knowledge-index/tests/ -q` | `5 passed in 0.02s` |
| rule-projector | `pytest .maika/tools/rule-projector/tests/ -q` | `13 passed in 0.12s` |
| skill-lint | `pytest .maika/tools/skill-lint/tests/ -q` | `50 passed in 0.05s` |

Ghi chú CI: `.github/workflows/ci.yml` hiện chỉ chạy `cli/tests/` — 6 suite còn lại chạy tay (khớp nhận định v2 §28).

## 3. Inventory

### 3.1 Workflows (.maika/workflows/)
| File | Vai trò | vNext direction |
|---|---|---|
| approve-conventions.md | workflow phê duyệt conventions | retain |
| approve-dna.md | workflow phê duyệt dna | retain |
| convention-scan.md | workflow quét convention | retain |
| dna-scan.md | workflow quét dna | retain |
| idea-to-task.md | workflow chuyển ý tưởng thành task | retain |
| index-source.md | workflow index source code | retain |
| README.md | tài liệu hướng dẫn | retain |
| task.md | workflow chính, OpenSpec lifecycle | migrate (W6) |
| tdd.md | workflow TDD | retain |

### 3.2 Skills (.maika/skills/) — chi tiết phân loại ở skill-migration-map.yaml (Task 6)

### 3.3 Rules (.maika/rules/)
| File | Vai trò | vNext direction |
|---|---|---|
| rules-exec.md | luật execution | retain |
| rules-flow.md | luật flow | retain |
| rules-guard.md | luật guard | retain |
| rules-knowledge.md | luật knowledge | retain |
| rules-tool.md | luật tool | retain |
| RULES.md | luật chính | retain |

### 3.4 Procedures (.maika/procedures/)
| File | Vai trò | vNext direction |
|---|---|---|
| bootstrap.md | thủ tục bootstrap | retain |
| context-compressor.md | thủ tục nén context | retain |
| context-loader.md | thủ tục nạp context | retain |
| decision-gate.md | thủ tục decision gate | retain |
| executor.md | thủ tục executor | retain |
| reviewer.md | thủ tục reviewer | retain |
| token-tracking.md | thủ tục tracking token | retain |

### 3.5 Tools (.maika/tools/)
| File | Vai trò | vNext direction |
|---|---|---|
| gate-check | tool kiểm tra gate | retain |
| knowledge-index | tool index knowledge | retain |
| mcp-bridge | tool mcp bridge | retain |
| microloop-orchestrator | tool điều phối microloop | retain |
| README.md | tài liệu hướng dẫn | retain |
| rule-projector | tool luật projector | retain |
| skill-index | tool index skill | retain |
| skill-lint | tool lint skill | retain |

### 3.6 Hooks (.maika/hooks/)
| File | Vai trò | vNext direction |
|---|---|---|
| antigravity | hook cho antigravity | retain |
| claude-code | hook cho claude-code | retain |
| codex | hook cho codex | retain |
| write-gate | hook write gate | retain |

### 3.7 Templates (.maika/knowledge/templates/)
| File | Vai trò | vNext direction |
|---|---|---|
| SESSION_OVERRIDE.tpl.md | template session override | retain |
| CONTEXT_REQUEST.tpl.md | template context request | retain |
| NODE_CHECKPOINT.tpl.md | template node checkpoint | retain |
| TASK_HANDOFF.tpl.md | template task handoff | retain |
| EXPLORE_CONTEXT.tpl.md | template explore context | retain |
| TOKEN_LOG.tpl.md | template token log | retain |
| INTEGRATION_REQUEST.tpl.md | template integration request | retain |
| fixbug.tpl.md | template fixbug | retain |
| KNOWLEDGE_PACK.tpl.md | template knowledge pack | retain |
| CONTRACT_DAG.tpl.md | template contract dag | retain |
| AGENT_TRANSPARENCY.tpl.md | template agent transparency | retain |
| CONTRACT_CHANGE_REQUEST.tpl.md | template contract change request | retain |
| KNOWLEDGE_CHECKPOINT.tpl.md | template knowledge checkpoint | retain |
| feature.tpl.md | template feature | retain |
| ideation.tpl.md | template ideation | retain |
| changerequest.tpl.md | template changerequest | retain |
| REQUIREMENT.tpl.md | template requirement | retain |
| refactor.tpl.md | template refactor | retain |
| ARCHIVE_META.tpl.md | template archive meta | retain |
| CONTRACT_SNAPSHOT.tpl.md | template contract snapshot | retain |

### 3.8 CLI manifest (cli/plugin-manifest.yaml)
- File có 412 dòng, vNext direction: retain

### 3.9 Platform adapters (cli/platforms/) + kết quả kiểm R2
| File | Vai trò | vNext direction |
|---|---|---|
| antigravity.py | adapter cho antigravity | retain |
| claude_code.py | adapter cho claude-code | retain |
| codex.py | adapter cho codex | retain |
| generic.py | adapter cho generic | retain |

- **Kết quả kiểm R2**: Mọi file `cli/platforms/*.py` (trừ `base.py`, `__init__.py`) đều xuất hiện trong dict `PLATFORMS`. Không có finding lệch.

## 4. Retro-classification dogfood

| PR / merge | Files đụng | Class theo §6 | Lý do | Misfit? |
|---|---|---|---|---|
| #39 docs(vnext): W0 plan | 4 files: docs | trivial | Thay đổi thuần docs, không thay đổi behavior (đúng định nghĩa `trivial` - typo, docs, no behavior change). | Không |
| #37 code-evidence gate | 10 files: gate-check, rules, docs | standard | Multi-file, multi-module (chạm rules, tools, template). Không phải public contract. | Không |
| #36 grep-honesty gate | 10 files: cli, gate-check, rules | standard | Multi-file, multi-module (chạm cli adapters, tools, rules). | Không |

### Misfit findings
- 0 misfit — §6 phủ được 3 change gần nhất.

## 5. Exit criteria (v2 §26 W0)

- [x] Baseline commit recorded: `a31dc30` (§2)
- [x] Conflicting branches resolved/stacked: quyết định tại §1 (chờ user duyệt)
- [x] Every planned deletion has known consumers: skill-migration-map.yaml + artifact-consumer-map.yaml
- [ ] Current-state audit approved: **chờ user**
- [x] Ledger + matrix exist and validate: `pytest cli/tests/test_vnext_w0_artifacts.py` → 4 passed
