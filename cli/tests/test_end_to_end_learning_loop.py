from pathlib import Path

import yaml

from cli.knowledge_control import (
    LearningStore,
    apply_project_learning,
    promote_skill_candidate,
    rollback_skill_promotion,
    validate_markdown_knowledge_trace,
)


def test_task_a_knowledge_is_retrieved_by_task_b_and_feedback_clusters(tmp_path):
    store = LearningStore(tmp_path)
    store.promote({"id": "PK-1", "statement": "Use idempotency key", "applies_to": ["payment"], "status": "active"})
    package = store.retrieve(["payment"], ["How are duplicates prevented?"])
    assert [item["id"] for item in package["knowledge_slice"]] == ["PK-1"]

    for change in ("A", "A", "B"):
        store.record_feedback({
            "change_id": change, "verified": True, "recurrence_key": "missing-idempotency",
            "skill": "writing-plan", "reproducible": True, "impact": "measurable",
            "evaluation_ready": True,
        })
    candidate = store.cluster_candidate("missing-idempotency")
    assert candidate["status"] == "proposed"
    assert candidate["problem"]["occurrences"] == 3


def test_reproducible_control_plane_dogfood(tmp_path):
    framework = tmp_path / ".maika"
    long_term = framework / "knowledge" / "long-term"
    long_term.mkdir(parents=True)
    ws = framework / "changes" / "TASK-A"
    (ws / "reviews").mkdir(parents=True)
    (ws / "verification").mkdir()
    (ws / "verification" / "VERIFICATION_REPORT.md").write_text(
        "VERDICT: VERIFIED\n", encoding="utf-8"
    )
    (ws / "reviews" / "KNOWLEDGE_IMPACT.yaml").write_text(yaml.safe_dump({
        "stale_entries": [], "superseded_decisions": [],
        "new_candidates": [{
            "id": "PK-IDEMPOTENCY", "statement": "payment uses idempotency key",
            "applies_to": ["payment"], "evidence_ids": ["UA-1", "CBM-1", "SRC-1", "MEM-1", "DB-1"],
            "confidence": "high",
        }],
        "graph_refresh_required": True,
        "memory_updates": [{"id": "MEM-A", "lesson": "keep payment idempotent"}],
    }, sort_keys=False), encoding="utf-8")
    (ws / "reviews" / "SKILL_FEEDBACK.yaml").write_text(
        "version: 1\nchange_id: TASK-A\nverified: true\nobservations: []\n",
        encoding="utf-8",
    )
    trace = """# Decision
## Knowledge Trace
```yaml
decision:
  id: DEC-A
  statement: Keep payment creation idempotent.
  type: business_behavior
  knowledge_questions: ["How are duplicate payments prevented?"]
  evidence_ids: [UA-1, CBM-1, SRC-1, MEM-1, DB-1]
  authority: current source
  conflicts: []
  assumptions: []
  confidence: high
  freshness: verified
  verdict: accepted
```
"""
    assert validate_markdown_knowledge_trace(trace).ok
    memory_calls = []
    learning = apply_project_learning(
        tmp_path, ".maika", ws,
        memory_saver=lambda item: memory_calls.append(item) or {"ok": True, "provider_id": "agent-memory"},
        graph_refresher=lambda item: {"verified": True, "status": "refreshed"},
    )
    assert learning["promoted"][0]["verified"]
    assert learning["graph_refresh"]["verified"]
    assert memory_calls and learning["memory_saved"][0]["ok"]

    store = LearningStore(long_term)
    task_b = store.retrieve(["payment"], ["How are duplicates prevented?"])
    assert task_b["knowledge_slice"][0]["id"] == "PK-IDEMPOTENCY"

    for change in ("TASK-A", "TASK-A", "TASK-B"):
        store.record_feedback({
            "change_id": change, "verified": True, "recurrence_key": "capsule-idempotency",
            "skill": "writing-plan", "category": "behavioral", "severity": "important",
            "statement": "capsule omitted idempotency", "recommendation": "require idempotency evidence",
            "reproducible": True, "impact": "measurable", "evaluation_ready": True,
        })
    candidate = store.cluster_candidate("capsule-idempotency")
    candidate["proposed_change"] = {
        "sections": ["Output"], "summary": "require evidence",
        "before": "## Output\nold\n", "after": "## Output\nnew control\n",
    }
    candidate["skill_evaluation"].update({
        "evaluation_tasks": ["TASK-A", "TASK-B"],
        "before_metrics": {"retry_count": 2},
        "after_metrics": {"retry_count": 0},
        "verdict": "PROMOTE",
    })
    candidate_path = framework / "knowledge" / "skill-evolution" / "candidates" / "SC-capsule-idempotency.yaml"
    candidate_path.parent.mkdir(parents=True)
    candidate_path.write_text(yaml.safe_dump(candidate, sort_keys=False), encoding="utf-8")
    skill = framework / "skills" / "writing-plan" / "SKILL.md"
    skill.parent.mkdir(parents=True)
    skill.write_text(
        "---\nname: writing-plan\nversion: '2.0'\n---\n"
        "current source authority; evidence; verification; write gate; knowledge-native; capability IDs\n"
        "## Output\nold\n",
        encoding="utf-8",
    )
    promoted = promote_skill_candidate(
        tmp_path, ".maika", candidate_path,
        {"independent": True, "verdict": "approved", "guardrails_preserved": True},
        {"old_version": "2.0", "new_version": "2.1", "independent_review": "approved",
         "tests_passed": True, "dogfood_passed": True, "canary_passed": True,
         "canary_results": [{"task": "TASK-B", "passed": True}], "human_approval": False},
    )
    assert promoted["status"] == "accepted"
    assert "new control" in Path(promoted["skill_path"]).read_text(encoding="utf-8")
    rolled_back = rollback_skill_promotion(
        tmp_path, ".maika", Path(promoted["candidate_path"]),
        [{"task": "CANARY-1", "passed": False, "reason": "regression"}],
    )
    assert rolled_back["status"] == "rolled_back"
    assert "## Output\nold\n" in Path(rolled_back["skill_path"]).read_text(encoding="utf-8")
