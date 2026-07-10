"""Architecture guard: STATE.yaml writes belong to vnext_state.py only."""

import ast
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
CANONICAL = ROOT / ".maika" / "tools" / "microloop-orchestrator" / "vnext_state.py"


def test_only_canonical_state_service_writes_state_yaml():
    offenders = []
    production = [ROOT / "cli", ROOT / ".maika" / "tools", ROOT / ".maika" / "hooks"]
    for base in production:
        for path in base.rglob("*.py"):
            if "tests" in path.parts or path == CANONICAL:
                continue
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            state_names = set()
            for node in ast.walk(tree):
                if not isinstance(node, (ast.Assign, ast.AnnAssign)):
                    continue
                value = node.value
                if value is None or "STATE.yaml" not in ast.unparse(value):
                    continue
                targets = node.targets if isinstance(node, ast.Assign) else [node.target]
                state_names.update(target.id for target in targets if isinstance(target, ast.Name))
            for node in ast.walk(tree):
                if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Attribute):
                    continue
                if node.func.attr not in {"write_text", "write_bytes", "open"}:
                    continue
                rendered = ast.unparse(node.func.value)
                if "STATE.yaml" in rendered or rendered in state_names:
                    offenders.append(f"{path.relative_to(ROOT)}:{node.lineno}")
    assert offenders == []
