from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[2]


def test_implemented_document_index_is_excluded_by_default():
    index = yaml.safe_load(
        (ROOT / "docs/archive/implemented/index.yaml").read_text(encoding="utf-8")
    )
    assert index["status"] == "implemented"
    assert index["runtime_authority"] is False
    assert index["default_retrieval"] == "exclude"
    assert all(item["runtime_authority"] is False for item in index["documents"])


def test_explicit_history_queries_remain_discoverable():
    index = yaml.safe_load(
        (ROOT / "docs/archive/implemented/index.yaml").read_text(encoding="utf-8")
    )
    assert {"history", "rationale", "migration", "regression"} <= set(index["history_query_terms"])
    assert any((ROOT / "docs/superpowers/plans").glob("*.md"))
