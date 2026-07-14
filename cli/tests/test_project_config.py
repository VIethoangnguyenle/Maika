"""Tests for canonical project config (.maika/config/project.yaml)."""

from pathlib import Path

import pytest

from cli.config import project


def test_load_missing_returns_defaults(tmp_path):
    cfg = project.load(tmp_path)
    assert cfg["version"] == 1
    assert cfg["framework"]["core_root"] == ".maika"
    assert cfg["platforms"]["enabled"] == []
    assert cfg["platforms"]["primary"] is None


def test_enable_adds_and_sets_first_primary(tmp_path):
    cfg = project.enable(project.load(tmp_path), "codex")
    assert cfg["platforms"]["enabled"] == ["codex"]
    assert cfg["platforms"]["primary"] == "codex"


def test_enable_is_idempotent_and_keeps_primary(tmp_path):
    cfg = project.load(tmp_path)
    cfg = project.enable(cfg, "codex")
    cfg = project.enable(cfg, "claude-code")
    cfg = project.enable(cfg, "codex")  # again
    assert cfg["platforms"]["enabled"] == ["codex", "claude-code"]
    assert cfg["platforms"]["primary"] == "codex"  # unchanged


def test_disable_removes_and_reassigns_primary(tmp_path):
    cfg = project.load(tmp_path)
    cfg = project.enable(cfg, "codex")
    cfg = project.enable(cfg, "claude-code")
    cfg = project.disable(cfg, "codex")
    assert cfg["platforms"]["enabled"] == ["claude-code"]
    assert cfg["platforms"]["primary"] == "claude-code"


def test_disable_last_clears_primary(tmp_path):
    cfg = project.enable(project.load(tmp_path), "codex")
    cfg = project.disable(cfg, "codex")
    assert cfg["platforms"]["enabled"] == []
    assert cfg["platforms"]["primary"] is None


def test_set_primary_requires_enabled(tmp_path):
    cfg = project.load(tmp_path)
    with pytest.raises(ValueError):
        project.set_primary(cfg, "codex")
    cfg = project.enable(cfg, "codex")
    cfg = project.enable(cfg, "claude-code")
    cfg = project.set_primary(cfg, "claude-code")
    assert cfg["platforms"]["primary"] == "claude-code"


def test_save_load_round_trip(tmp_path):
    cfg = project.enable(project.load(tmp_path), "codex")
    project.save(tmp_path, cfg)
    assert project.config_path(tmp_path).exists()
    assert project.load(tmp_path)["platforms"]["enabled"] == ["codex"]
