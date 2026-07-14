from pathlib import Path

import yaml

from cli.knowledge_control import apply_project_learning


def test_learning_promotes_supersedes_and_records_runtime_results(tmp_path):
    root = tmp_path
    long_term = root / ".maika" / "knowledge" / "long-term"
    long_term.mkdir(parents=True)
    old = long_term / "project-knowledge" / "OLD.yaml"
    old.parent.mkdir()
    old.write_text("id: OLD\nstatus: active\nstatement: old rule\napplies_to: [Service]\n")
    ws = root / ".maika" / "changes" / "A"
    (ws / "reviews").mkdir(parents=True)
    (ws / "verification").mkdir()
    (ws / "verification" / "VERIFICATION_REPORT.md").write_text("VERDICT: VERIFIED\n")
    (ws / "reviews" / "SKILL_FEEDBACK.yaml").write_text(
        "version: 1\nchange_id: A\nverified: true\nobservations: []\n"
    )
    (ws / "reviews" / "KNOWLEDGE_IMPACT.yaml").write_text(
        yaml.safe_dump({
            "stale_entries": ["OLD"],
            "superseded_decisions": [{"id": "OLD", "superseded_by": "NEW"}],
            "new_candidates": [{
                "id": "NEW", "statement": "new rule", "applies_to": ["Service"],
                "evidence_ids": ["SRC-1"], "confidence": "high",
            }],
            "graph_refresh_required": True,
            "memory_updates": [{"id": "MEM-1", "lesson": "prefer the new rule"}],
        }, sort_keys=False),
        encoding="utf-8",
    )

    result = apply_project_learning(
        root, ".maika", ws,
        memory_saver=lambda item: {"ok": True, "id": item["id"]},
        graph_refresher=lambda item: {"verified": True, "status": "refreshed"},
    )

    assert result["verified"] is True
    assert Path(result["promoted"][0]["path"]).exists()
    assert yaml.safe_load(old.read_text())["status"] == "superseded"
    assert result["memory_saved"][0]["ok"] is True
    assert Path(result["graph_refresh"]["request_path"]).exists()
    assert len(result["knowledge_index_sha256"]) == 64
