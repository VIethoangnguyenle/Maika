# plan_parser.py
"""Parse IMPLEMENTATION_PLAN.md (v2 §15): frontmatter + verbatim TASK sections."""
import re

import yaml

_TASK_HEAD = re.compile(r"^### (TASK-\d+):\s*(.+)$", re.MULTILINE)
_YAML_BLOCK = re.compile(r"```yaml\n(.*?)```", re.DOTALL)


def parse_plan(text):
    if not text.startswith("---"):
        raise ValueError("plan missing YAML frontmatter")
    end = text.index("\n---", 3)
    meta = yaml.safe_load(text[3:end]) or {}
    for key in ("change_id", "plan_version", "base_commit", "spec_hash", "evidence_hash"):
        if key not in meta:
            raise ValueError(f"plan frontmatter missing: {key}")
    heads = list(_TASK_HEAD.finditer(text))
    if not heads:
        raise ValueError("plan has no TASK sections")
    tasks = []
    for i, m in enumerate(heads):
        stop = heads[i + 1].start() if i + 1 < len(heads) else len(text)
        section = text[m.start():stop]
        block = _YAML_BLOCK.search(section)
        header = (yaml.safe_load(block.group(1)) or {}).get("task") if block else None
        if not header:
            raise ValueError(f"{m.group(1)}: missing ```yaml task:``` header")
        if header.get("id") != m.group(1):
            raise ValueError(f"heading {m.group(1)} != header id {header.get('id')}")
        tasks.append({"id": m.group(1), "title": m.group(2).strip(),
                      "header": header, "section_text": section})
    return {"meta": meta, "tasks": tasks}
