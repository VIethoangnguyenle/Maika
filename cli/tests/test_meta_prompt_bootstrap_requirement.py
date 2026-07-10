from pathlib import Path
import importlib.util
from datetime import datetime, timezone

import yaml

from cli.commands.bootstrap import run_bootstrap
from cli.commands.init import run_init


META = Path(__file__).resolve().parents[2] / ".maika" / "meta-prompt.md"
GATES_PATH = META.parent / "tools" / "gate-check" / "gates.py"
SPEC = importlib.util.spec_from_file_location("gates_bootstrap", GATES_PATH)
GATES = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(GATES)


def test_meta_prompt_requires_bootstrap_report_before_work():
    text = META.read_text(encoding="utf-8")
    assert "procedures/bootstrap.md" in text
    assert "BOOTSTRAP_REPORT.yaml" in text
    assert "không được tiếp tục" in text.lower()


def test_bootstrap_complete_gate_requires_every_rule_and_completed_probe_report():
    report = {
        "version": 1, "completed": True, "timestamp": datetime.now(timezone.utc).isoformat(), "repository_commit": "unavailable",
        "entry_point": "AGENTS.md",
        "rules_loaded": ["RULES.md", "rules-flow.md", "rules-tool.md", "rules-exec.md",
                         "rules-knowledge.md", "rules-skill-evolution.md", "rules-guard.md"],
        "knowledge_index": {"status": "loaded", "entries": 1},
        "configured_providers": [], "provider_probes": [], "episodic_provider_health": "not-configured",
        "active_state": "empty", "resume_state": "new", "degradation": [],
    }
    assert GATES.validate_bootstrap_complete(yaml.safe_dump(report)).ok
    report["rules_loaded"].remove("rules-skill-evolution.md")
    assert not GATES.validate_bootstrap_complete(yaml.safe_dump(report)).ok


def test_bootstrap_command_produces_gate_valid_report(tmp_path, maika_root):
    target = tmp_path / "project"
    run_init(str(target), str(maika_root), "generic", [], "python", assume_yes=True)
    assert run_bootstrap(str(target), home=tmp_path / "home") == 0
    report = target / ".maika" / "knowledge" / "active" / "BOOTSTRAP_REPORT.yaml"
    assert GATES.validate_bootstrap_complete(report.read_text(encoding="utf-8")).ok
