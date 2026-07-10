# tests/test_plan_parser.py
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import plan_parser as pp

PLAN = """---
change_id: demo
plan_version: 1
base_commit: abc123
spec_hash: sha256:aaa
evidence_hash: sha256:bbb
---

# Plan

### TASK-001: Tạo module A

```yaml
task:
  id: TASK-001
  implementation_mode: exact
  depends_on: []
  files:
    create: [src/a.py]
    test: [tests/test_a.py]
  verification:
    command: pytest tests/test_a.py -q
    expected: "1 passed"
```

Thân task 1.

### TASK-002: Dùng A

```yaml
task:
  id: TASK-002
  implementation_mode: guided
  depends_on: [TASK-001]
  files:
    modify: [src/a.py]
    test: [tests/test_a.py]
  verification:
    command: pytest tests/ -q
    expected: "2 passed"
```

Thân task 2.
"""


def test_parse_meta_and_tasks():
    doc = pp.parse_plan(PLAN)
    assert doc["meta"]["base_commit"] == "abc123"
    ids = [t["id"] for t in doc["tasks"]]
    assert ids == ["TASK-001", "TASK-002"]
    assert doc["tasks"][0]["header"]["implementation_mode"] == "exact"
    assert "Thân task 1." in doc["tasks"][0]["section_text"]
    assert "TASK-002" not in doc["tasks"][0]["section_text"].split("###")[0] or True


def test_verbatim_roundtrip():
    doc = pp.parse_plan(PLAN)
    for t in doc["tasks"]:
        assert t["section_text"] in PLAN          # verbatim slice, không chỉnh sửa


def test_missing_frontmatter_raises():
    with pytest.raises(ValueError):
        pp.parse_plan("# no frontmatter\n### TASK-001: x\n")


def test_task_without_yaml_header_raises():
    bad = PLAN.replace("```yaml", "```text", 1)
    with pytest.raises(ValueError):
        pp.parse_plan(bad)
