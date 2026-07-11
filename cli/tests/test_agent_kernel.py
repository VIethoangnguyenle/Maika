"""Agent Kernel contract (agent-facing refactor PR 2, plan §7)."""

from pathlib import Path
import importlib.util

import pytest

from cli.commands.init import run_init
from cli.platforms import get_platform


ROOT = Path(__file__).resolve().parents[2]
KERNEL = ROOT / ".maika" / "agent" / "KERNEL.md"
SPEC = importlib.util.spec_from_file_location(
    "gates_kernel", ROOT / ".maika" / "tools" / "gate-check" / "gates.py"
)
GATES = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(GATES)


def test_kernel_satisfies_kernel_contract():
    text = KERNEL.read_text(encoding="utf-8")
    required = [
        "Identity", "Canonical Authority", "Workflow Routing", "Write Boundary",
        "Evidence Honesty", "Verification Honesty", "Learning Boundary",
        "Resume & Bootstrap", "Stop Conditions",
    ]
    assert len(text.splitlines()) <= 150
    assert all(heading in text for heading in required)
    assert "knowledge-grounded engineering agent" in text.lower()
    assert "Không có material decision" in text
    assert GATES.validate_agent_kernel(text).ok


def test_kernel_contains_no_legacy_or_provider_doctrine():
    text = KERNEL.read_text(encoding="utf-8")
    for forbidden in ("knowledge/active/", "REQUIREMENT.md", "AGENT_TRANSPARENCY",
                      "TOKEN_LOG", "Understand-Anything", "Codebase Memory"):
        assert forbidden not in text, f"kernel must not contain {forbidden!r}"
    assert "explore → spec → plan" not in text  # no global fixed phase chain


def test_gate_rejects_kernel_violations():
    text = KERNEL.read_text(encoding="utf-8")
    assert not GATES.validate_agent_kernel(text + "\nknowledge/active/REQUIREMENT.md\n").ok
    assert not GATES.validate_agent_kernel(text.replace("## 9. Stop Conditions", "## 9. Alt")).ok
    assert not GATES.validate_agent_kernel(text + ("\n" * 60) + "pad\n").ok


def test_kernel_requires_bootstrap_before_work():
    text = KERNEL.read_text(encoding="utf-8")
    assert "procedures/bootstrap.md" in text
    assert "BOOTSTRAP_REPORT.yaml" in text
    assert "không được reasoning" in text.lower() or "không được tiếp tục" in text.lower()


@pytest.mark.parametrize("platform_key", ["codex", "claude-code", "antigravity", "generic"])
def test_every_platform_entry_point_receives_kernel(tmp_path, maika_root, platform_key):
    target = tmp_path / platform_key
    run_init(str(target), str(maika_root), platform_key, [], "python", assume_yes=True)
    entry = target / get_platform(platform_key).config_entry_point
    text = entry.read_text(encoding="utf-8")
    assert "knowledge-grounded engineering agent" in text
    assert "KERNEL_ID: maika-agent-kernel-v1" in text
    assert "procedures/bootstrap.md" in text
    # Scaffolded canonical kernel file (hash/ack reference) must exist too.
    kernel_copy = target / ".maika" / "agent" / "KERNEL.md"
    assert kernel_copy.exists()
    assert GATES.validate_agent_kernel(kernel_copy.read_text(encoding="utf-8")).ok
