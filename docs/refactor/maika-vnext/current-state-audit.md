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

(Task 3 điền)

## 4. Retro-classification dogfood

(Task 9 điền)

## 5. Exit criteria

(Task 10 điền)
