from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
RULES = ROOT / "rules"


def test_guard2_is_evidence_gate_and_generic():
    text = (RULES / "core/write-boundary.md").read_text(encoding="utf-8")
    assert "TASK_QUEUE.json" in text
    assert "decision-gate" in text
    # generic-ised: no hard-coded artifact-type enum in the rule
    assert "Chứa `Factory`" not in text
    assert "Chứa `Service`" not in text


def test_rtool8_dispatch_gate():
    text = (RULES / "jit/providers.md").read_text(encoding="utf-8")
    assert "handoff-slice" in text                     # references the gate validator
    assert "Applicable DNA/Conventions" in text         # required slice section


def test_rflow_phase_gate():
    text = (RULES / "core/flow.md").read_text(encoding="utf-8")
    assert "maika task apply" in text                    # public W5 entry point
    assert "PLAN_VALIDATION.json" in text                # plan gate validator
    assert "reviews/plan-review.md" in text              # review gate artifact
    assert "TASK_QUEUE.json" in text                     # canonical queue contract
    assert "final review" in text                        # completion review gate


def test_rtool_mcp_probe_collapse():
    text = (RULES / "jit/providers.md").read_text(encoding="utf-8")
    # M11: probe evidence is typed — tool-health + hash-bound invocation records.
    assert "tool-health" in text
    assert "provider-invocations" in text
    assert "mcp-status" not in text                      # legacy prose gate removed
    assert "Runtime Ready" not in text or "rỗng = invalid" in text
    assert "secondary" not in text                       # removed skippable preference prose


def test_rules_tool_mentions_bridge_fallback_and_node_checkpoint():
    text = (ROOT / "rules" / "jit/providers.md").read_text(encoding="utf-8")
    assert "mcp-bridge" in text
    assert "NODE_CHECKPOINT.<node-id>.md" in text
    assert "CONTEXT_REQUEST.<node-id>.md" in text
    assert "node-checkpoint" in text


def test_bootstrap_points_mcp_failures_to_doctor():
    text = (ROOT / "procedures" / "bootstrap.md").read_text(encoding="utf-8")
    assert "maika doctor mcp" in text
    assert "bridge fallback" in text
