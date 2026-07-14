"""Guard: R-Tool-5 pins source authority to the typed trace-evidence path (M11).

The pre-harness doctrine (code-facts via graph node prose) was removed with the
legacy provider-specific gates; this guard keeps the replacement doctrine from
drifting back to prose evidence.
"""

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
RULES = REPO_ROOT / ".maika" / "rules" / "jit/providers.md"


def _text():
    return RULES.read_text(encoding="utf-8")


def test_rtool5_pins_typed_trace_evidence_path():
    text = _text()
    assert "TRACE_EVIDENCE.yaml" in text
    assert "verify-source" in text
    assert "response hash" in text
    # Grep-honesty survives the migration: healthy provider -> no grep fallback.
    assert "Grep-honesty" in text


def test_rtool5_does_not_reintroduce_graph_node_prose():
    text = _text()
    section = text.split("R-Tool-5", 1)[1].split("### ", 1)[0]
    assert "node_id" not in section
    assert "blast-radius" not in section
