from pathlib import Path

from cli.agent_content.external_workflows import load_external_workflows
from cli.agent_content.interaction_router import load_interaction_router
from cli.commands.content import run_content
from cli.commands.memory import remember

ROOT = Path(__file__).resolve().parents[2]
FRAMEWORK = ROOT / ".maika"


def test_explicit_understand_chat_is_native_query_not_task():
    router = load_interaction_router(FRAMEWORK)
    chat = load_external_workflows(FRAMEWORK)["workflows"]["understand-chat"]
    assert router["precedence"][0] == "explicit_native_command"
    assert chat["invocation_type"] == "native_passthrough"
    assert chat["kind"] == "knowledge_query"
    assert chat["task_workspace"] == "not_required"


def test_graph_generation_is_maintenance_not_task():
    workflows = load_external_workflows(FRAMEWORK)["workflows"]
    for name in ("understand", "understand-domain"):
        assert workflows[name]["kind"] == "knowledge_maintenance"
        assert workflows[name]["task_workspace"] == "forbidden"
        assert workflows[name]["allowed_writes"]
        assert workflows[name]["produces"]


def test_natural_language_application_change_has_explicit_task_route():
    task = load_interaction_router(FRAMEWORK)["routes"]["task_change"]
    assert task == {
        "handler": "task-workflow",
        "creates_change_workspace": True,
        "mutability": "task_scoped",
    }


def test_validation_and_remember_do_not_create_task_artifacts(tmp_path):
    assert run_content("validate-interactions", target_dir=str(ROOT)) == 0
    assert run_content("validate-external-workflows", target_dir=str(ROOT)) == 0
    code, _ = remember("Prefer Processor suffix.", target_dir=str(tmp_path))
    assert code == 0
    assert not list(tmp_path.glob(".maika/changes/*/CHANGE.yaml"))
    assert not list(tmp_path.glob(".maika/changes/*/STATE.yaml"))


def test_kernel_limits_task_and_restricts_isolated_workers():
    kernel = (FRAMEWORK / "agent/KERNEL.md").read_text(encoding="utf-8")
    assert "`/task` chỉ quản lý lifecycle của application change" in kernel
    assert "Explicit native slash workflow không tự động route" in kernel
    assert "Isolated task worker không được gọi side-effecting external workflow" in kernel
