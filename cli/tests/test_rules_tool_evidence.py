"""Guard: R-Tool-5 grants architecture-facts a parallel UA evidence path."""

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
RULES = REPO_ROOT / ".maika" / "rules" / "jit/providers.md"


def _text():
    return RULES.read_text(encoding="utf-8")


def test_rtool5_has_architecture_facts_evidence_path():
    text = _text()
    assert "architecture-facts" in text, "R-Tool-5 thiếu đường evidence cho architecture-facts"
    # UA identifier counts as valid evidence without forcing node_id
    assert "UA identifier" in text or "identifier kiểu UA" in text


def test_rtool5_keeps_codefacts_kg_path():
    text = _text()
    # code-facts still require node_id + blast-radius via KG tools (unchanged)
    assert "code-facts" in text and "node_id" in text
