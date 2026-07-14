from pathlib import Path
import importlib.util
from datetime import datetime, timezone

import yaml

from cli.commands.bootstrap import (
    ACK_REL,
    ENV_REPORT_REL,
    run_bootstrap,
    run_bootstrap_ack,
    verify_ack_freshness,
)
from cli.commands.init import run_init


FRAMEWORK = Path(__file__).resolve().parents[2] / ".maika"
KERNEL = FRAMEWORK / "agent" / "KERNEL.md"
GATES_PATH = FRAMEWORK / "tools" / "gate-check" / "gates.py"
SPEC = importlib.util.spec_from_file_location("gates_bootstrap", GATES_PATH)
GATES = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(GATES)


def test_kernel_requires_bootstrap_report_and_ack_before_work():
    text = KERNEL.read_text(encoding="utf-8")
    assert "procedures/bootstrap.md" in text
    assert "BOOTSTRAP_ENV_REPORT.yaml" in text
    assert "AGENT_BOOTSTRAP_ACK.yaml" in text
    assert "không được reasoning" in text.lower()


def _env_report():
    return {
        "version": 2, "completed": True,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "repository_commit": "unavailable", "entry_point": "AGENTS.md",
        "rules_present": ["RULES.md", "core/flow.md", "jit/providers.md", "core/verification.md",
                          "core/evidence.md", "jit/skill-evolution.md", "core/write-boundary.md"],
        "knowledge_index": {"status": "loaded", "entries": 1},
        "configured_providers": [], "provider_probes": [],
        "episodic_provider_health": "not-configured",
        "active_changes": [], "resume_state": "new", "degradation": [],
    }


def test_bootstrap_complete_gate_uses_rules_present_facts():
    report = _env_report()
    assert GATES.validate_bootstrap_complete(yaml.safe_dump(report)).ok
    report["rules_present"].remove("core/evidence.md")
    assert not GATES.validate_bootstrap_complete(yaml.safe_dump(report)).ok
    stale = _env_report()
    stale["rules_loaded"] = stale.pop("rules_present")  # legacy shape must fail
    assert not GATES.validate_bootstrap_complete(yaml.safe_dump(stale)).ok
    ambiguous = _env_report()
    ambiguous["resume_state"] = "maybe"
    assert not GATES.validate_bootstrap_complete(yaml.safe_dump(ambiguous)).ok


def test_bootstrap_command_produces_env_report_and_ack(tmp_path, maika_root):
    target = tmp_path / "project"
    run_init(str(target), str(maika_root), "generic", [], "python", assume_yes=True)
    assert run_bootstrap(str(target), home=tmp_path / "home") == 0
    report = target / ".maika" / ENV_REPORT_REL
    assert GATES.validate_bootstrap_complete(report.read_text(encoding="utf-8")).ok
    doc = yaml.safe_load(report.read_text(encoding="utf-8"))
    assert doc["version"] == 2
    assert "rules_loaded" not in doc

    assert run_bootstrap_ack(str(target)) == 0
    ack = target / ".maika" / ACK_REL
    assert GATES.validate_bootstrap_ack(ack.read_text(encoding="utf-8")).ok
    ok, reason = verify_ack_freshness(target / ".maika")
    assert ok, reason


def test_stale_ack_rejected_after_kernel_change(tmp_path, maika_root):
    target = tmp_path / "project"
    run_init(str(target), str(maika_root), "generic", [], "python", assume_yes=True)
    assert run_bootstrap(str(target), home=tmp_path / "home") == 0
    assert run_bootstrap_ack(str(target)) == 0
    kernel = target / ".maika" / "agent" / "KERNEL.md"
    kernel.write_text(kernel.read_text(encoding="utf-8") + "\n<!-- edited -->\n",
                      encoding="utf-8")
    ok, reason = verify_ack_freshness(target / ".maika")
    assert not ok
    assert "kernel_hash" in reason


def test_ack_requires_explicit_change_when_ambiguous(tmp_path, maika_root, capsys):
    target = tmp_path / "project"
    run_init(str(target), str(maika_root), "generic", [], "python", assume_yes=True)
    for change_id in ("C-1", "C-2"):
        ws = target / ".maika" / "changes" / change_id
        ws.mkdir(parents=True)
        (ws / "STATE.yaml").write_text(
            yaml.safe_dump({"version": 1, "change_id": change_id, "state": "INTAKE"}),
            encoding="utf-8",
        )
        (ws / "CHANGE.yaml").write_text(
            yaml.safe_dump({"version": 1, "change_id": change_id, "class": "small"}),
            encoding="utf-8",
        )
    assert run_bootstrap(str(target), home=tmp_path / "home") == 0
    report = yaml.safe_load(
        (target / ".maika" / ENV_REPORT_REL).read_text(encoding="utf-8")
    )
    assert report["resume_state"] == "ambiguous"
    assert run_bootstrap_ack(str(target)) == 1
    assert "--id" in capsys.readouterr().out
    assert run_bootstrap_ack(str(target), change_id="C-2") == 0
    ack = yaml.safe_load((target / ".maika" / ACK_REL).read_text(encoding="utf-8"))
    assert ack["selected_change"] == "C-2"
    assert ack["current_state"] == "INTAKE"
    assert "apply" in ack["selected_route"]


def test_stale_ack_rejected_after_provider_registry_change(tmp_path, maika_root):
    """Mutation #11 (harness plan §21): provider registry changes after ack."""
    target = tmp_path / "project"
    run_init(str(target), str(maika_root), "generic", [], "python", assume_yes=True)
    assert run_bootstrap(str(target), home=tmp_path / "home") == 0
    assert run_bootstrap_ack(str(target)) == 0
    registry = target / ".maika" / "config" / "provider-registry.yaml"
    registry.write_text(
        registry.read_text(encoding="utf-8") + "\n# edited after ack\n",
        encoding="utf-8",
    )
    ok, reason = verify_ack_freshness(target / ".maika")
    assert not ok
    assert "provider_registry_hash" in reason
