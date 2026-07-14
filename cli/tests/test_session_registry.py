"""Session registry tests (Phase 7, F8 redesign).

Covers: coexistence, explicit-wins, stale-ignored, hook-refresh,
malformed-ignored, ambiguity, set/clear active-platform, prune.
"""

from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
import yaml

from cli.config import project
from cli.runtime.session_registry import (
    DEFAULT_STALE_AFTER_SECONDS,
    SESSIONS_RELATIVE_DIR,
    SessionError,
    clear_active_platform,
    fresh_platforms,
    list_sessions,
    load_active_platform,
    prune_sessions,
    record_session,
    resolve_active_platform,
    set_active_platform,
)


def _project(root: Path, primary: str = "claude-code") -> None:
    cfg = project.enable(project.enable(project._default(), "claude-code"), "codex")
    cfg = project.set_primary(cfg, primary)
    project.save(root, cfg)


# ── Coexistence ───────────────────────────────────────────────────────────

def test_two_claude_sessions_coexist(tmp_path):
    _project(tmp_path)
    r1 = record_session(tmp_path, "claude-code", source="native-hook", session_id="claude-1")
    r2 = record_session(tmp_path, "claude-code", source="native-hook", session_id="claude-2")
    assert r1["session_id"] == "claude-1"
    assert r2["session_id"] == "claude-2"
    sessions = list_sessions(tmp_path)
    ids = {s["session_id"] for s in sessions}
    assert ids == {"claude-1", "claude-2"}


def test_claude_and_codex_coexist(tmp_path):
    _project(tmp_path)
    record_session(tmp_path, "claude-code", source="native-hook", session_id="c1")
    record_session(tmp_path, "codex", source="native-hook", session_id="x1")
    sessions = list_sessions(tmp_path)
    platforms = {s["platform"] for s in sessions}
    assert platforms == {"claude-code", "codex"}


# ── Resolution ────────────────────────────────────────────────────────────

def test_explicit_platform_wins(tmp_path):
    _project(tmp_path)
    record_session(tmp_path, "codex", source="native-hook", session_id="x1")
    assert resolve_active_platform(tmp_path, explicit_platform="claude-code") == (
        "claude-code", "explicit-cli",
    )


def test_stale_session_ignored(tmp_path):
    _project(tmp_path, primary="claude-code")
    record_session(tmp_path, "codex", source="native-hook", session_id="x1")
    path = tmp_path / SESSIONS_RELATIVE_DIR / "codex" / "x1.yaml"
    data = yaml.safe_load(path.read_text())
    data["last_seen_at"] = (datetime.now(timezone.utc) - timedelta(hours=2)).isoformat()
    path.write_text(yaml.safe_dump(data), encoding="utf-8")
    assert resolve_active_platform(tmp_path, stale_after_seconds=60) == ("claude-code", "primary")


def test_hook_refresh_preserves_started_at(tmp_path):
    _project(tmp_path)
    r1 = record_session(tmp_path, "claude-code", source="native-hook", session_id="h1")
    started = r1["started_at"]
    r2 = record_session(tmp_path, "claude-code", source="native-hook", session_id="h1")
    assert r2["started_at"] == started
    assert r2["last_seen_at"] >= r1["last_seen_at"]


def test_malformed_session_ignored(tmp_path):
    _project(tmp_path, primary="claude-code")
    bad_dir = tmp_path / SESSIONS_RELATIVE_DIR / "codex"
    bad_dir.mkdir(parents=True)
    (bad_dir / "bad.yaml").write_text("not: valid: yaml: [", encoding="utf-8")
    sessions = list_sessions(tmp_path)
    assert all(s["session_id"] != "bad" for s in sessions)
    assert resolve_active_platform(tmp_path) == ("claude-code", "primary")


def test_ambiguity_raises(tmp_path):
    _project(tmp_path)
    record_session(tmp_path, "claude-code", source="native-hook", session_id="c1")
    record_session(tmp_path, "codex", source="native-hook", session_id="x1")
    with pytest.raises(SessionError, match="ambiguous"):
        resolve_active_platform(tmp_path)


# ── Active platform ──────────────────────────────────────────────────────

def test_set_and_load_active_platform(tmp_path):
    _project(tmp_path)
    result = set_active_platform(tmp_path, "codex")
    assert result["platform"] == "codex"
    assert load_active_platform(tmp_path) == "codex"


def test_clear_active_platform(tmp_path):
    _project(tmp_path)
    set_active_platform(tmp_path, "codex")
    assert clear_active_platform(tmp_path) is True
    assert load_active_platform(tmp_path) is None
    assert clear_active_platform(tmp_path) is False


def test_active_platform_wins_over_fresh(tmp_path):
    _project(tmp_path)
    record_session(tmp_path, "codex", source="native-hook", session_id="x1")
    set_active_platform(tmp_path, "claude-code")
    assert resolve_active_platform(tmp_path) == ("claude-code", "active-platform")


# ── Prune ─────────────────────────────────────────────────────────────────

def test_prune_removes_stale_and_malformed(tmp_path):
    _project(tmp_path)
    # fresh session — should survive
    record_session(tmp_path, "claude-code", source="native-hook", session_id="fresh1")

    # stale session
    record_session(tmp_path, "codex", source="native-hook", session_id="stale1")
    stale_path = tmp_path / SESSIONS_RELATIVE_DIR / "codex" / "stale1.yaml"
    data = yaml.safe_load(stale_path.read_text())
    data["last_seen_at"] = (datetime.now(timezone.utc) - timedelta(hours=2)).isoformat()
    stale_path.write_text(yaml.safe_dump(data), encoding="utf-8")

    # malformed session
    bad_dir = tmp_path / SESSIONS_RELATIVE_DIR / "codex"
    (bad_dir / "malformed.yaml").write_text("{{bad", encoding="utf-8")

    removed = prune_sessions(tmp_path, stale_after_seconds=60)
    assert len(removed) == 2
    assert any("stale1" in r for r in removed)
    assert any("malformed" in r for r in removed)
    # fresh one still present
    assert (tmp_path / SESSIONS_RELATIVE_DIR / "claude-code" / "fresh1.yaml").is_file()


# ── Validation ────────────────────────────────────────────────────────────

def test_untrusted_source_raises(tmp_path):
    _project(tmp_path)
    with pytest.raises(SessionError, match="untrusted"):
        record_session(tmp_path, "claude-code", source="agent-file-edit", session_id="x")


def test_disabled_platform_raises(tmp_path):
    _project(tmp_path)
    with pytest.raises(SessionError, match="not enabled"):
        record_session(tmp_path, "nonexistent", source="native-hook", session_id="x")


def test_invalid_session_id_raises(tmp_path):
    _project(tmp_path)
    with pytest.raises(SessionError, match="session_id"):
        record_session(tmp_path, "claude-code", source="native-hook",
                       session_id="bad/id")
