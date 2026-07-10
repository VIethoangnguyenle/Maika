from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]


def test_context_loader_defines_freshness_checks():
    text = (ROOT / "procedures" / "context-loader.md").read_text(encoding="utf-8")
    for marker in (
        "repository commit", "file hash", "indexed commit", "knowledge status",
        "memory relevance", "DB probe timestamp", "capsule hash",
    ):
        assert marker.lower() in text.lower()

