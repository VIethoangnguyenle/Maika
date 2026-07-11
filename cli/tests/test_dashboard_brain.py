"""Tests for dashboard IDE brain sync adapters."""
import json

from cli.dashboard import brain


def _make_antigravity_project(tmp_path):
    proj = tmp_path / "proj"
    active = proj / ".maika" / "knowledge" / "active"
    active.mkdir(parents=True)
    (proj / ".maika" / "resolved-config.yaml").write_text(
        "resolved:\n"
        "  platform: antigravity\n"
        "  framework_root: .maika\n"
        "  language: python\n"
        "  framework_version: '3.0'\n",
        encoding="utf-8",
    )
    return proj, active


def _write_last_conversation(home, project, conversation_id):
    cache = home / ".gemini" / "antigravity-cli" / "cache"
    cache.mkdir(parents=True)
    (cache / "last_conversations.json").write_text(
        json.dumps({str(project.resolve()): conversation_id}),
        encoding="utf-8",
    )


def test_sync_antigravity_parent_brain_writes_mirror_and_event(tmp_path):
    proj, active = _make_antigravity_project(tmp_path)
    home = tmp_path / "home"
    conversation_id = "conv-123"
    _write_last_conversation(home, proj, conversation_id)
    artifacts = home / ".gemini" / "antigravity" / "brain" / conversation_id / "artifacts"
    artifacts.mkdir(parents=True)
    (artifacts / "decision.md").write_text(
        "# Decision\n\nMirror parent IDE brain into dashboard.\n",
        encoding="utf-8",
    )

    result = brain.sync_antigravity_parent_brain(proj, home=home)

    out = active / "PARENT_BRAIN.md"
    log = active / "microloop" / "ACTIVITY_LOG.jsonl"
    content = out.read_text(encoding="utf-8")
    events = [json.loads(line) for line in log.read_text(encoding="utf-8").splitlines()]
    assert result.written is True
    assert result.source == "antigravity-brain"
    assert result.conversation_id == conversation_id
    assert "source: antigravity-brain" in content
    assert "Mirror parent IDE brain into dashboard" in content
    assert events[-1]["event"] == "parent_brain_updated"
    assert events[-1]["actor"] == "parent"
    assert events[-1]["conversation_id"] == conversation_id


def test_sync_antigravity_parent_brain_without_mapping_does_not_write(tmp_path):
    proj, active = _make_antigravity_project(tmp_path)

    result = brain.sync_antigravity_parent_brain(proj, home=tmp_path / "home")

    assert result.written is False
    assert "conversation mapping" in result.reason
    assert not (active / "PARENT_BRAIN.md").exists()


def test_sync_antigravity_parent_brain_without_text_artifacts_does_not_overwrite(tmp_path):
    proj, active = _make_antigravity_project(tmp_path)
    existing = active / "PARENT_BRAIN.md"
    existing.write_text("manual mirror\n", encoding="utf-8")
    home = tmp_path / "home"
    conversation_id = "conv-123"
    _write_last_conversation(home, proj, conversation_id)
    (home / ".gemini" / "antigravity" / "brain" / conversation_id).mkdir(parents=True)

    result = brain.sync_antigravity_parent_brain(proj, home=home)

    assert result.written is False
    assert "no text brain artifacts" in result.reason
    assert existing.read_text(encoding="utf-8") == "manual mirror\n"
