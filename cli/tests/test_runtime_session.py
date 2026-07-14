"""Trusted, session-aware active-platform resolution (A3, F8 registry redesign)."""

from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
import yaml

from cli.config import project
from cli.runtime.session import (
    SessionError,
    record_session,
    resolve_active_platform,
    set_active_platform,
)
from cli.runtime.session_registry import SESSIONS_RELATIVE_DIR


def _project(root: Path, primary: str = "claude-code") -> None:
    cfg = project.enable(project.enable(project._default(), "claude-code"), "codex")
    cfg = project.set_primary(cfg, primary)
    project.save(root, cfg)


def test_explicit_platform_wins_without_mutating_existing_session(tmp_path):
    _project(tmp_path)
    record_session(tmp_path, "claude-code", source="native-hook", session_id="claude-1")
    assert resolve_active_platform(tmp_path, explicit_platform="codex") == ("codex", "explicit-cli")
    # The per-session file for claude-code must still exist
    session_file = tmp_path / SESSIONS_RELATIVE_DIR / "claude-code" / "claude-1.yaml"
    current = yaml.safe_load(session_file.read_text())
    assert current["platform"] == "claude-code"


def test_fresh_trusted_session_wins_over_primary(tmp_path):
    _project(tmp_path, primary="claude-code")
    record_session(tmp_path, "codex", source="native-hook", session_id="codex-1")
    assert resolve_active_platform(tmp_path) == ("codex", "current-session")


def test_stale_session_falls_back_to_primary(tmp_path):
    _project(tmp_path, primary="claude-code")
    record_session(tmp_path, "codex", source="native-hook", session_id="codex-1")
    path = tmp_path / SESSIONS_RELATIVE_DIR / "codex" / "codex-1.yaml"
    data = yaml.safe_load(path.read_text())
    data["last_seen_at"] = (datetime.now(timezone.utc) - timedelta(hours=2)).isoformat()
    path.write_text(yaml.safe_dump(data), encoding="utf-8")
    assert resolve_active_platform(tmp_path, stale_after_seconds=60) == ("claude-code", "primary")


def test_active_platform_selection_wins_over_fresh_sessions(tmp_path):
    """An explicitly set active-platform beats any fresh session."""
    _project(tmp_path, primary="claude-code")
    record_session(tmp_path, "codex", source="native-hook", session_id="codex-1")
    set_active_platform(tmp_path, "claude-code")
    assert resolve_active_platform(tmp_path) == ("claude-code", "active-platform")


def test_agent_authored_record_without_trusted_source_is_ignored(tmp_path):
    _project(tmp_path, primary="claude-code")
    path = tmp_path / SESSIONS_RELATIVE_DIR / "codex" / "forged.yaml"
    path.parent.mkdir(parents=True)
    path.write_text(yaml.safe_dump({
        "version": 1, "session_id": "forged", "platform": "codex",
        "source": "agent-file-edit", "started_at": datetime.now(timezone.utc).isoformat(),
        "last_seen_at": datetime.now(timezone.utc).isoformat(),
    }), encoding="utf-8")
    assert resolve_active_platform(tmp_path) == ("claude-code", "primary")
