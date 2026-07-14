import importlib.util
import json
from pathlib import Path


MOD = Path(__file__).resolve().parents[1] / "write_gate.py"
spec = importlib.util.spec_from_file_location("write_gate_skill_permissions", MOD)
wg = importlib.util.module_from_spec(spec)
spec.loader.exec_module(wg)


def _write_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data), encoding="utf-8")


def _setup_vnext_workspace(root):
    framework = root / ".maika"
    (framework / "profiles").mkdir(parents=True)
    (framework / "profiles" / "execution-mode.local.yaml").write_text("workflow_engine: vnext\n")
    ws = framework / "changes" / "demo"
    ws.mkdir(parents=True)
    (ws / "STATE.yaml").write_text("change_id: demo\nstate: EXECUTING\n")
    _write_json(ws / "generated" / "PLAN_VALIDATION.json", {"verdict": "APPROVED"})
    _write_json(ws / "generated" / "PLAN_MANIFEST.json", {"plan_sha256": "sha"})
    _write_json(ws / "generated" / "TASK_QUEUE.json", {
        "plan_sha256": "sha",
        "tasks": [{"id": "TASK-001", "status": "in_progress", "files": {}}],
    })
    return ws


def _set_role(ws, role, allowed):
    queue = json.loads((ws / "generated" / "TASK_QUEUE.json").read_text())
    queue["tasks"][0]["role"] = role
    queue["tasks"][0]["files"] = allowed
    (ws / "generated" / "TASK_QUEUE.json").write_text(json.dumps(queue))


def test_application_implementer_cannot_write_framework_even_if_brief_claims_it(tmp_path):
    ws = _setup_vnext_workspace(tmp_path)
    _set_role(ws, "application-implementer", {"modify": [".maika/skills/writing-plan/SKILL.md"]})
    decision = wg.evaluate_write(tmp_path, tmp_path / ".maika/skills/writing-plan/SKILL.md")
    assert not decision.ok


def test_skill_roles_have_narrow_permissions(tmp_path):
    ws = _setup_vnext_workspace(tmp_path)
    _set_role(ws, "skill-evolution-curator", {"create": [".maika/knowledge/skill-evolution/candidates/SC-1.yaml"]})
    assert wg.evaluate_write(
        tmp_path, tmp_path / ".maika/knowledge/skill-evolution/candidates/SC-1.yaml"
    ).ok
    assert not wg.evaluate_write(
        tmp_path, tmp_path / ".maika/skills/writing-plan/SKILL.md"
    ).ok


def test_dynamic_framework_write_fails_closed():
    paths, unresolved = wg.parse_shell_writes("target=.maika/meta-prompt.md; printf x > $target")
    assert paths == []
    assert unresolved is True


def test_skill_implementer_is_bound_to_candidate_target_skill(tmp_path):
    ws = _setup_vnext_workspace(tmp_path)
    candidate = tmp_path / ".maika/knowledge/skill-evolution/candidates/SC-1.yaml"
    candidate.parent.mkdir(parents=True)
    candidate.write_text("candidate_id: SC-1\ntarget_skill: writing-plan\n")
    queue = json.loads((ws / "generated" / "TASK_QUEUE.json").read_text())
    queue["tasks"][0].update({
        "role": "skill-evolution-implementer", "candidate_id": "SC-1",
        "target_skill": "writing-plan",
        "files": {"modify": [".maika/skills/writing-plan/SKILL.md", ".maika/skills/executing-task/SKILL.md"]},
    })
    (ws / "generated" / "TASK_QUEUE.json").write_text(json.dumps(queue))
    assert wg.evaluate_write(tmp_path, tmp_path / ".maika/skills/writing-plan/SKILL.md").ok
    assert not wg.evaluate_write(tmp_path, tmp_path / ".maika/skills/executing-task/SKILL.md").ok
