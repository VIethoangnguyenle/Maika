from pathlib import Path

import yaml

from cli.mcp.pilot_readiness import assess_pilot_readiness, render_pilot_readiness


ROOT = Path(__file__).resolve().parents[2]


def _registry():
    return yaml.safe_load((ROOT / ".maika/config/provider-registry.yaml").read_text())


def test_safe_but_unverified_providers_are_conditional_not_production_ready():
    statuses = {
        "understand-anything": {"status": "ready", "unverified": ["index_generation"]},
        "agent-memory": {"status": "degraded", "unverified": ["store_identity"]},
        "db-access": {"status": "ready"},
    }
    report = assess_pilot_readiness(_registry(), statuses)
    assert report["decision"] == "conditional-pilot"
    assert report["production_ready"] is False
    assert "understand-anything.index_generation: unverified" in report["degraded_or_unverified"]
    assert "Production ready: no" in render_pilot_readiness(report)


def test_unsafe_agentmemory_hook_blocks_pilot():
    registry = _registry()
    registry["providers"]["agent-memory"]["hooks"]["auto_capture"] = True
    report = assess_pilot_readiness(registry, {})
    assert report["decision"] == "blocked"
    assert any("automatic capture" in item for item in report["blockers"])
