from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import vnext_dispatch as vd


def test_all_dispatch_paths_include_canonical_kernel(tmp_path):
    expected = {
        "intent", "grounding", "reconciliation", "brainstorming", "spec",
        "planning", "plan_review", "implementation", "fix", "task_review",
        "final_review", "verification", "knowledge_curator",
        "skill_evolution_curator", "skill_evolution_implementer",
        "skill_evolution_reviewer",
    }
    assert expected <= vd.DISPATCH_TYPES
    for role in expected:
        prompt = vd.build_prompt(role, tmp_path, "input.md", "output.yaml")
        assert vd.DISPATCH_KERNEL_ID in prompt
        assert "You are an isolated Maika worker." in prompt
        assert "EVIDENCE_UPDATE_REQUEST" in prompt
        assert "Return structured result only." in prompt


def test_dispatch_kernel_procedure_is_canonical_source():
    kernel = Path(vd.__file__).resolve().parents[2] / "procedures" / "dispatch-kernel.md"
    assert kernel.exists()
    assert vd.DISPATCH_KERNEL_ID in kernel.read_text(encoding="utf-8")
